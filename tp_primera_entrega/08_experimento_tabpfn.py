"""TabPFN vía API PriorLabs: marzo -> mayo; marzo+abril -> junio (exploratoria).

Envía features y etiquetas de train a PriorLabs, sin IDs ni mes ni etiquetas
de evaluación. Requiere TABPFN_TOKEN. No requiere GPU local.

No optimiza el umbral ni utiliza etiquetas de julio. Ejecución por etapas:
  --etapa validacion
  --etapa test --validacion-existente <carpeta de validación completa>
"""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
from copy import copy
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]

import duckdb
import numpy as np
import pandas as pd
from baseline import preparar, metricas


def ejecutar(args):
    if not os.environ.get('TABPFN_TOKEN'):
        raise RuntimeError('Falta TABPFN_TOKEN en esta terminal. Cargar la API key antes de ejecutar.')
    from tabpfn_client import TabPFNClassifier, estimate_cost, get_api_usage
    config = json.loads((ROOT / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    train_meses, evaluacion_mes = ([202103], 202105) if args.etapa == 'validacion' else ([202103, 202104], 202106)
    if args.etapa == 'test':
        if not args.validacion_existente:
            raise ValueError('Primero ejecutar y revisar la validación de mayo.')
        previo = json.loads((Path(args.validacion_existente) / 'manifest.json').read_text(encoding='utf-8'))
        if previo['estado'] != 'completo' or previo['etapa'] != 'validacion':
            raise ValueError('La validación referida no está completa.')
        if previo.get('backend') != 'priorlabs_api':
            raise ValueError('Se requiere una validación ejecutada con la API de PriorLabs.')
        if previo['batch_size'] != args.batch_size:
            raise ValueError('Tamaño de lote distinto de la validación congelada.')
        if previo['n_estimators'] != args.n_estimators or previo['seed'] != config['seed']:
            raise ValueError('Configuración distinta de la validación congelada.')
        if previo['model_version'] != args.model_version:
            raise ValueError('Modelo distinto de la validación congelada.')
        for paquete, version in previo['versiones'].items():
            if importlib.metadata.version(paquete) != version:
                raise ValueError('Versión distinta de la validación: ' + paquete)
        for archivo, digest in previo['codigo_sha256'].items():
            if hashlib.sha256((Path(__file__).parent / archivo).read_bytes()).hexdigest() != digest:
                raise ValueError('Código distinto de la validación: ' + archivo)
    out = ROOT / config['salidas'] / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('tabpfn_api_' + args.etapa + '_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(estado='iniciado', etapa=args.etapa, train_meses=train_meses,
                    evaluacion_mes=evaluacion_mes, config=config, seed=config['seed'],
                    n_estimators=args.n_estimators, batch_size=args.batch_size, umbral=0.025,
                    model_version=args.model_version,
                    validacion_existente=args.validacion_existente, variables='originales',
                    muestreo=False, backend='priorlabs_api',
                    versiones={p: importlib.metadata.version(p) for p in ['tabpfn-client', 'duckdb', 'lightgbm', 'numpy', 'pandas', 'scikit-learn']},
                    codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest() for p in ['08_experimento_tabpfn.py', 'baseline.py']},
                    notas='Junio previamente evaluado: comparación exploratoria. Sin tuning ni balanceo. Entrenamiento completo; no se presenta una muestra como el mes completo. Sin escalado ni one-hot. Sin predicciones de agosto.')
    def guardar():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    guardar()
    try:
        with duckdb.connect() as con:
            con.execute('SET threads=2')
            con.read_csv(str(ROOT / config['dataset'])).create_view('datos')
            meses = train_meses + [evaluacion_mes]
            datos = con.execute('SELECT * FROM datos WHERE foto_mes IN (' + ','.join('?' for _ in meses) + ') ORDER BY foto_mes,numero_de_cliente', meses).df()
        claves = [config['id_col'], config['mes_col']]
        target = config['target_col']
        if datos.duplicated(claves).any() or datos[target].isna().any() or not datos[target].isin(['BAJA+1','BAJA+2','CONTINUA']).all():
            raise ValueError('Etiquetas o claves inválidas.')
        train = datos.loc[datos.foto_mes.isin(train_meses)].copy()
        evaluacion = datos.loc[datos.foto_mes.eq(evaluacion_mes)].copy()
        if train.empty or evaluacion.empty:
            raise ValueError('Partición vacía.')
        columnas = [c for c in datos if c not in claves + [target]]
        xt, at = preparar(train, columnas)
        xv, av = preparar(evaluacion, columnas)
        yt = train[target].eq('BAJA+2').astype(int).to_numpy()
        yv = evaluacion[target].eq('BAJA+2').astype(int).to_numpy()
        assert len(np.unique(yt)) == len(np.unique(yv)) == 2
        if args.etapa == 'test' and previo['features'] != columnas:
            raise ValueError('Features distintas de las usadas en validación.')
        categorias = [columnas.index(c) for c in ['Visa_status','Master_status','tcuentas']]
        modelo = TabPFNClassifier.create_default_for_version(args.model_version,
                                  n_estimators=args.n_estimators,
                                  random_state=config['seed'], categorical_features_indices=categorias,
                                  fit_mode='fit_preprocessors', inference_precision='autocast',
                                  inference_config={'SUBSAMPLE_SAMPLES': None})
        manifest.update(features=columnas, filas_train=len(train), filas_evaluacion=len(evaluacion),
                        positivos_train=int(yt.sum()), positivos_evaluacion=int(yv.sum()),
                        auditoria_train=at, auditoria_evaluacion=av, parametros=modelo.get_params())
        guardar()
        # Cotizar los mismos lotes que se ejecutarán, sin subir valores.
        batch_size = args.batch_size or len(xv)
        manifest['cuota_antes'] = str(get_api_usage())
        cotizaciones = []
        for start in range(0, len(xv), batch_size):
            quote = estimate_cost(xt, xv.iloc[start:start + batch_size],
                                  model_version=args.model_version,
                                  n_estimators=args.n_estimators)
            cotizaciones.append(quote.model_dump(mode='json'))
        costo = sum(q['estimated_cost'] for q in cotizaciones)
        manifest.update(cotizaciones=cotizaciones, consumo_estimado=costo)
        guardar()
        print(f'Consumo estimado: {costo}; solicitudes: {len(cotizaciones)}', flush=True)
        if costo > args.max_creditos:
            raise ValueError(f'Consumo {costo} supera --max-creditos={args.max_creditos}; no se subieron datos.')
        inicio = time.perf_counter()
        print(f'TabPFN API: train={len(train)}, evaluación={len(evaluacion)}, variables={len(columnas)}', flush=True)
        modelo.fit(xt.to_numpy(dtype=np.float32), yt)
        print('Fit completo; iniciando predicciones.', flush=True)
        indice = list(modelo.classes_).index(1)
        prob = np.full(len(xv), np.nan)
        for start in range(0, len(xv), batch_size):
            end = min(start + batch_size, len(xv))
            prob[start:end] = modelo.predict_proba(xv.iloc[start:end].to_numpy(dtype=np.float32))[:, indice]
            np.save(out / 'probabilidades_parciales.npy', prob)
            manifest.update(filas_predichas=end, segundos_transcurridos=time.perf_counter()-inicio)
            guardar()
            print(f'Predicciones {end}/{len(xv)}', flush=True)
        assert np.isfinite(prob).all() and ((prob >= 0) & (prob <= 1)).all()
        pred = evaluacion[claves + [target]].copy()
        pred['p_tabpfn'] = prob
        pred.to_csv(out / 'predicciones.csv', index=False)
        resultado = metricas(yv, prob, config)
        resultado['segundos'] = time.perf_counter() - inicio
        csv = pd.read_csv(out / 'predicciones.csv')
        assert csv[claves + [target]].equals(pred[claves + [target]].reset_index(drop=True))
        sel = csv.p_tabpfn.gt(0.025)
        ganancia = int(np.where(csv[target].eq('BAJA+2'), config['ganancia']['acierto'], config['ganancia']['error'])[sel].sum())
        assert ganancia == resultado['ganancia']
        manifest.update(estado='completo', resultados=resultado, ganancia_recalculada=ganancia,
                        model_id=getattr(modelo, 'model_id_', None))
        guardar()
        # Un fallo de consulta de saldo no invalida predicciones completas.
        try:
            manifest['cuota_despues'] = str(get_api_usage())
        except Exception as exc:
            manifest['cuota_despues_error'] = type(exc).__name__
        guardar()
        print(resultado, flush=True)
        print('Resultados:', out, flush=True)
        return out
    except BaseException as exc:
        manifest.update(estado='error', error_tipo=type(exc).__name__, error=str(exc))
        guardar()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--etapa', choices=['validacion','test','secuencia'], default='validacion')
    parser.add_argument('--validacion-existente')
    parser.add_argument('--n-estimators', type=int, default=1)
    parser.add_argument('--batch-size', type=int, default=0,
                        help='0: predecir toda la etapa en una solicitud (predeterminado).')
    parser.add_argument('--max-creditos', type=int, default=100000,
                        help='Tope estimado por etapa antes de subir datos.')
    parser.add_argument('--model-version', choices=['v3.5','v3.5-fast'], default='v3.5-fast')
    args = parser.parse_args()
    if not 1 <= args.n_estimators <= 8 or args.batch_size < 0 or args.max_creditos < 1:
        parser.error('n-estimators debe ser 1..8; batch-size >= 0; max-creditos > 0.')
    if args.etapa == 'secuencia':
        validacion = copy(args)
        validacion.etapa = 'validacion'
        carpeta = ejecutar(validacion)
        test = copy(args)
        test.etapa = 'test'
        test.validacion_existente = str(carpeta)
        ejecutar(test)
    else:
        ejecutar(args)
