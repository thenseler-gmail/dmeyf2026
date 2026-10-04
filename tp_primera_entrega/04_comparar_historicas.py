"""Experimento retrospectivo: entrenar abril y validar mayo, con/sin historia.

Marzo aporta historia para abril; abril aporta historia para mayo. Los targets
de abril requieren junio: esta comparación NO simula información disponible al
cierre de mayo. No consulta las filas de junio ni cambia config.json.

Ejecutar: .venv/Scripts/python.exe tp_primera_entrega/04_comparar_historicas.py
"""
# %%
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import hashlib
import importlib.metadata
import json
import time

import duckdb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from baseline import cargar_particiones, crear_lightgbm, preparar, metricas
from features import agregar_historicas, HISTORICAS


def cargar_historia(root, config):
    """Solo claves y cuatro predictores de marzo a mayo, nunca el target."""
    columnas = ['numero_de_cliente', 'foto_mes', *HISTORICAS]
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(root / config['dataset'])).create_view('datos')
        historia = con.sql(
            'SELECT ' + ', '.join(columnas) +
            ' FROM datos WHERE foto_mes IN (202103, 202104, 202105)'
            ' ORDER BY foto_mes, numero_de_cliente'
        ).df()
    historia[HISTORICAS] = historia[HISTORICAS].replace([np.inf, -np.inf], np.nan)
    return agregar_historicas(historia)


def comparar(root, config):
    # Copia aislada: no altera el protocolo principal marzo -> mayo -> junio.
    experimental = deepcopy(config)
    experimental['split'].update(
        confirmado=True, train_meses=[202104], validacion_meses=[202105],
        reentrenamiento_meses=[],
        tipo_evaluacion='Retrospectiva abril -> mayo; target de abril disponible en junio')
    train, valid = cargar_particiones(root, experimental)
    historia = cargar_historia(root, experimental)
    claves = [config['id_col'], config['mes_col']]
    excluidas = [*claves, config['target_col']]
    originales = [c for c in train if c not in excluidas]
    nuevas = [c for c in historia if c not in [*claves, *HISTORICAS]]
    # No eliminamos clientes sin historia: ambos modelos usan las mismas filas.
    train = train.merge(historia[claves + nuevas], on=claves, how='left',
                        sort=False, validate='one_to_one')
    valid = valid.merge(historia[claves + nuevas], on=claves, how='left',
                        sort=False, validate='one_to_one')
    indicador = 'historial_mes_anterior_disponible'
    if train[indicador].isna().any() or valid[indicador].isna().any():
        raise ValueError('No se pudo asociar el indicador de historia a cada fila.')
    xt, audit_train = preparar(train, originales + nuevas)
    xv, audit_valid = preparar(valid, originales + nuevas)
    yt = train[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    yv = valid[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    if len(np.unique(yt)) != 2 or len(np.unique(yv)) != 2:
        raise ValueError('Ambas particiones deben contener las dos clases.')
    categoricas = [c for c in ['Visa_status', 'Master_status', 'tcuentas'] if c in originales]
    for col in categoricas:
        cats = sorted(xt[col].dropna().unique())
        xt[col] = pd.Categorical(xt[col], categories=cats)
        xv[col] = pd.Categorical(xv[col], categories=cats)
    out = root / config['salidas'] / datetime.now().strftime('historicas_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True, exist_ok=False)
    resultados = {}
    predicciones = valid[excluidas].copy()
    for nombre, columnas in [('base_abril', originales),
                            ('abril_con_historia', originales + nuevas)]:
        print(f'{nombre}: train={len(train):,}, validación={len(valid):,}, '
              f'variables={len(columnas)}', flush=True)
        modelo = crear_lightgbm(experimental)
        inicio = time.perf_counter()
        with threadpool_limits(limits=4):
            modelo.fit(xt[columnas], yt)
            prob = modelo.predict_proba(xv[columnas])[:, 1]
        if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
            raise ValueError('Probabilidades inválidas.')
        resultado = metricas(yv, prob, experimental)
        resultado.update(variables=len(columnas), segundos=time.perf_counter() - inicio)
        resultado['diferencia_vs_base_abril'] = resultado['ganancia'] - (
            resultados['base_abril']['ganancia'] if resultados else resultado['ganancia'])
        resultados[nombre] = resultado
        predicciones['p_' + nombre] = prob
        modelo.booster_.save_model(str(out / f'{nombre}.txt'))
        pd.DataFrame({'variable': columnas, 'ganancia_splits': modelo.feature_importances_}).sort_values(
            'ganancia_splits', ascending=False).to_csv(out / f'importancias_{nombre}.csv', index=False)
        print(nombre, resultado, flush=True)
    manifest = dict(
        config_experimental=experimental, parametros=crear_lightgbm(experimental).get_params(),
        originales=originales, nuevas=nuevas, categoricas=categoricas,
        filas_train=len(train), filas_validacion=len(valid),
        positivos_train=int(yt.sum()), positivos_validacion=int(yv.sum()),
        clientes_sin_mes_anterior_train=int(train.historial_mes_anterior_disponible.eq(0).sum()),
        clientes_sin_mes_anterior_validacion=int(valid.historial_mes_anterior_disponible.eq(0).sum()),
        faltantes_historicas_train=xt[nuevas].isna().sum().to_dict(),
        faltantes_historicas_validacion=xv[nuevas].isna().sum().to_dict(),
        auditoria_train=audit_train, auditoria_validacion=audit_valid,
        resultados=resultados,
        versiones={k: importlib.metadata.version(k) for k in
                   ['lightgbm', 'numpy', 'pandas', 'scikit-learn', 'duckdb']},
        codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest()
                       for p in ['features.py', 'baseline.py', '04_comparar_historicas.py']},
        notas='Mismas filas, parámetros, semilla y umbral 0,025. Sin Optuna, sin intrames. '
              'Comparar con base_abril, no atribuir diferencias respecto del train marzo a las features. '
              'Una semilla; no prueba significación ni validez de una simulación en tiempo real. '
              'Junio permanece reservado, sin evaluación ni uso como fuente de features.')
    pd.DataFrame(resultados).T.to_csv(out / 'comparacion.csv', index_label='experimento')
    predicciones.to_csv(out / 'predicciones_validacion.csv', index=False)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Resultados:', out, flush=True)
    return out


# %%
if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    comparar(root, config)
