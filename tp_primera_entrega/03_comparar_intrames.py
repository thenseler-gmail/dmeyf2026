"""Compara LightGBM original vs tres bloques separados; no consulta junio.

Ejecutar desde la raíz: .venv/Scripts/python.exe tp_primera_entrega/03_comparar_intrames.py
Mismos parámetros, filas, semilla y umbral. No hace Optuna ni selecciona corte.
"""
# %%
from pathlib import Path
from datetime import datetime
import hashlib
import importlib.metadata
import json
import time

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from baseline import cargar_particiones, preparar, metricas, crear_lightgbm
from features import agregar_intrames, BLOQUES


def comparar(root, config):
    train, valid = cargar_particiones(root, config)
    excluidas = [config['id_col'], config['mes_col'], config['target_col']]
    originales = [c for c in train.columns if c not in excluidas]
    xt, audit_train = preparar(train, originales)
    xv, audit_valid = preparar(valid, originales)
    yt = train[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    yv = valid[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    if len(np.unique(yt)) != 2 or len(np.unique(yv)) != 2:
        raise ValueError('Ambas particiones deben contener las dos clases.')
    out = root / config['salidas'] / datetime.now().strftime('intrames_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True, exist_ok=False)
    resultados, detalles = {}, {}
    predicciones = valid[excluidas].copy()
    experimentos = [('base', []), *[(b, [b]) for b in BLOQUES]]

    def ejecutar(nombre, bloques):
        xtrain, xvalid = agregar_intrames(xt, bloques), agregar_intrames(xv, bloques)
        nuevas = [c for c in xtrain if c not in originales]
        for x in [xtrain, xvalid]:
            if np.isinf(x.to_numpy()).any():
                raise ValueError('Features con infinitos.')
        for c in ['Visa_status', 'Master_status', 'tcuentas']:
            if c in originales:
                categorias = sorted(xtrain[c].dropna().unique())
                xtrain[c] = pd.Categorical(xtrain[c], categories=categorias)
                xvalid[c] = pd.Categorical(xvalid[c], categories=categorias)
        print(f'{nombre}: {len(xtrain.columns)} variables', flush=True)
        modelo = crear_lightgbm(config)
        inicio = time.perf_counter()
        with threadpool_limits(limits=4):
            modelo.fit(xtrain, yt)
            prob = modelo.predict_proba(xvalid)[:, 1]
        if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
            raise ValueError('Probabilidades inválidas.')
        resultado = metricas(yv, prob, config)
        resultado.update(segundos=time.perf_counter() - inicio, variables=len(xtrain.columns))
        resultado['diferencia_vs_base'] = resultado['ganancia'] - (
            resultados['base']['ganancia'] if resultados else resultado['ganancia'])
        resultados[nombre] = resultado
        predicciones['p_' + nombre] = prob
        detalles[nombre] = dict(bloques=bloques, features=xtrain.columns.tolist(),
                               faltantes_train=xtrain[nuevas].isna().sum().to_dict(),
                               faltantes_validacion=xvalid[nuevas].isna().sum().to_dict())
        modelo.booster_.save_model(str(out / f'{nombre}.txt'))
        pd.DataFrame({'variable': xtrain.columns, 'ganancia_splits': modelo.feature_importances_}).sort_values(
            'ganancia_splits', ascending=False).to_csv(out / f'importancias_{nombre}.csv', index=False)
        print(nombre, resultado, flush=True)

    for nombre, bloques in experimentos:
        ejecutar(nombre, bloques)
    # Regla exploratoria explícita: combinar solo los bloques que mejoran solos.
    prometedores = [b for b in BLOQUES if resultados[b]['diferencia_vs_base'] > 0]
    if len(prometedores) >= 2:
        ejecutar('combinados', prometedores)
    tabla = pd.DataFrame(resultados).T
    tabla.to_csv(out / 'comparacion.csv', index_label='experimento')
    predicciones.to_csv(out / 'predicciones_validacion.csv', index=False)
    manifest = dict(config=config, parametros=crear_lightgbm(config).get_params(),
                    filas_train=len(train), filas_validacion=len(valid),
                    positivos_train=int(yt.sum()), positivos_validacion=int(yv.sum()),
                    auditoria_train=audit_train, auditoria_validacion=audit_valid,
                    experimentos=detalles, resultados=resultados,
                    versiones={k: importlib.metadata.version(k) for k in
                               ['lightgbm', 'numpy', 'pandas', 'scikit-learn', 'duckdb']},
                    codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest()
                                   for p in ['features.py', 'baseline.py', '03_comparar_intrames.py']},
                    notas='Una semilla; selección exploratoria en mayo. No prueba significación. '
                          'Los combinados dependen de los resultados de validación. Sin test de junio.')
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Resultados:', out, flush=True)
    return out


# %%
if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    comparar(root, config)
