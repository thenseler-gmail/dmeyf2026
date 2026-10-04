"""Evaluación congelada marzo+abril -> junio. No optimiza sobre el test."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import importlib.metadata
import time

import duckdb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from baseline import preparar, crear_lightgbm, metricas
from features import agregar_historicas, HISTORICAS


def ejecutar(root):
    config = json.loads((root / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    fuente = root / config['salidas'] / 'optuna_20261001_183546_498714/resultados.json'
    seleccion = json.loads(fuente.read_text(encoding='utf-8'))
    train_meses = config['split']['reentrenamiento_meses']
    test_meses = config['split']['test_meses']
    assert train_meses == [202103, 202104] and test_meses == [202106]
    claves = [config['id_col'], config['mes_col']]
    target = config['target_col']
    out = root / config['salidas'] / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('test_junio_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True, exist_ok=False)
    # Se escribe antes de consultar junio: candidato y referencia ya elegidos en mayo.
    congelado = dict(config=config, candidato='historicas', referencia='originales',
                     fuente=str(fuente.relative_to(root)),
                     fuente_sha256=hashlib.sha256(fuente.read_bytes()).hexdigest(),
                     umbral=0.025, variantes={v: seleccion[v]['parametros'] for v in ['originales', 'historicas']})
    (out / 'congelado.json').write_text(json.dumps(congelado, indent=2, ensure_ascii=False), encoding='utf-8')
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(root / config['dataset'])).create_view('datos')
        datos = con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202106) ORDER BY foto_mes,numero_de_cliente').df()
        # Mayo aporta solo predictores para el lag de junio, nunca etiquetas.
        historia = con.sql('SELECT ' + ','.join(claves + HISTORICAS) + ' FROM datos WHERE foto_mes IN (202103,202104,202105,202106) ORDER BY foto_mes,numero_de_cliente').df()
    if datos.duplicated(claves).any() or datos[target].isna().any() or not datos[target].isin(['BAJA+1', 'BAJA+2', 'CONTINUA']).all():
        raise ValueError('Claves o etiquetas inválidas.')
    originales = [c for c in datos if c not in claves + [target]]
    historia[HISTORICAS] = historia[HISTORICAS].replace([np.inf, -np.inf], np.nan)
    historia = agregar_historicas(historia)
    nuevas = [c for c in historia if c not in claves + HISTORICAS]
    datos = datos.merge(historia[claves + nuevas], on=claves, how='left', sort=False, validate='one_to_one')
    train = datos.loc[datos.foto_mes.isin(train_meses)].copy()
    test = datos.loc[datos.foto_mes.isin(test_meses)].copy()
    assert not train.empty and not test.empty
    assert datos.historial_mes_anterior_disponible.notna().all()
    assert train.loc[train.foto_mes.eq(202103), 'historial_mes_anterior_disponible'].eq(0).all()
    xt, at = preparar(train, originales + nuevas)
    xv, av = preparar(test, originales + nuevas)
    for c in ['Visa_status', 'Master_status', 'tcuentas']:
        cats = sorted(xt[c].dropna().unique())
        xt[c] = pd.Categorical(xt[c], categories=cats)
        xv[c] = pd.Categorical(xv[c], categories=cats)
    yt = train[target].eq(config['clase_positiva']).astype(int).to_numpy()
    yv = test[target].eq(config['clase_positiva']).astype(int).to_numpy()
    assert len(np.unique(yt)) == len(np.unique(yv)) == 2
    pred = test[claves + [target]].copy()
    resultados = {}
    parametros = {}
    for v in ['originales', 'historicas']:
        columnas = originales + (nuevas if v == 'historicas' else [])
        modelo = crear_lightgbm(config).set_params(**congelado['variantes'][v], subsample_freq=1)
        parametros[v] = modelo.get_params()
        inicio = time.perf_counter()
        print(f'Entrenando {v}: {len(train)} filas, {len(columnas)} variables', flush=True)
        with threadpool_limits(limits=4):
            modelo.fit(xt[columnas], yt)
            prob = modelo.predict_proba(xv[columnas])[:, 1]
        assert np.isfinite(prob).all() and ((prob >= 0) & (prob <= 1)).all()
        resultados[v] = metricas(yv, prob, config)
        resultados[v].update(segundos=time.perf_counter()-inicio, variables=len(columnas))
        pred['p_' + v] = prob
        modelo.booster_.save_model(str(out / (v + '.txt')))
        pd.DataFrame({'variable': columnas, 'ganancia_splits': modelo.feature_importances_}).to_csv(out / ('importancias_' + v + '.csv'), index=False)
        print(v, resultados[v], flush=True)
    pred.to_csv(out / 'predicciones_test.csv', index=False)
    # Verificación independiente desde el CSV exportado.
    guardado = pd.read_csv(out / 'predicciones_test.csv')
    assert len(guardado) == len(test) and not guardado.duplicated(claves).any()
    assert guardado[claves + [target]].equals(test[claves + [target]].reset_index(drop=True))
    verificacion = {}
    for v in resultados:
        sel = guardado['p_' + v].gt(0.025)
        ganancia = int(np.where(guardado[target].eq('BAJA+2'), 1072500, -27500)[sel].sum())
        assert ganancia == resultados[v]['ganancia']
        verificacion[v] = dict(ganancia_recalculada=ganancia, contactos=int(sel.sum()))
    manifest = dict(congelado=congelado, parametros=parametros, originales=originales, nuevas=nuevas,
                    filas_train=len(train), filas_test=len(test), positivos_train=int(yt.sum()), positivos_test=int(yv.sum()),
                    sin_historia_train=int(train.historial_mes_anterior_disponible.eq(0).sum()),
                    sin_historia_test=int(test.historial_mes_anterior_disponible.eq(0).sum()),
                    auditoria_train=at, auditoria_test=av, resultados=resultados, verificacion=verificacion,
                    versiones={k: importlib.metadata.version(k) for k in ['lightgbm', 'numpy', 'pandas', 'duckdb', 'scikit-learn']},
                    codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest() for p in ['07_evaluacion_junio.py','baseline.py','features.py']},
                    notas='Evaluación retrospectiva. Selección previa en mayo. Junio previamente explorado en EDA. Marzo sin febrero: lags y deltas faltantes, indicador cero. Sin ajuste de parámetros ni umbral con junio. No genera entrega de agosto.')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    pd.DataFrame(resultados).T.to_csv(out / 'comparacion.csv', index_label='variante')
    print('Resultados:', out, flush=True)
    return out


if __name__ == '__main__':
    ejecutar(Path(__file__).resolve().parents[1])
