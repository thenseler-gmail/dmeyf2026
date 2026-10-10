"""Corrida opcional de TabPFN con key propia, y comparacion contra entrega 43."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas
from reproducir import ROOT, KEYS, verificar_archivos


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def matrix_sha(x):
    return hashlib.sha256(x.tobytes()).hexdigest()


def preparar(dataset, config):
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(dataset)).create_view('datos')
        raw = con.sql('SELECT * EXCLUDE(clase_ternaria), '
                      'CASE WHEN foto_mes IN (202104,202105) THEN clase_ternaria '
                      'ELSE NULL END AS clase_ternaria FROM datos '
                      'WHERE foto_mes IN (202104,202105,202108) '
                      'ORDER BY foto_mes,numero_de_cliente').df()
        sources = KEYS + HISTORICAS + HISTORICAS_EXTRA
        history = con.sql('SELECT ' + ','.join(sources) + ' FROM datos '
                          'WHERE foto_mes BETWEEN 202103 AND 202108 '
                          'ORDER BY foto_mes,numero_de_cliente').df()
    hist = agregar_historicas_ampliadas(history)
    derived = [c for c in hist if c not in sources]
    raw = raw.merge(hist[KEYS + derived], on=KEYS, validate='one_to_one', sort=False)
    train = raw.loc[raw.foto_mes.isin([202104, 202105])].reset_index(drop=True)
    august = raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    if len(train) != 327052 or len(august) != 164647:
        raise ValueError('Cantidad de filas diferente de la original')
    if not train.clase_ternaria.isin(['CONTINUA', 'BAJA+1', 'BAJA+2']).all():
        raise ValueError('Etiquetas de entrenamiento invalidas')
    if not august.clase_ternaria.isna().all():
        raise ValueError('Se extrajeron etiquetas de agosto')
    def matrix(frame):
        x = frame[config['features']].astype(float).replace([np.inf, -np.inf], np.nan)
        for c in ['Visa_Fvencimiento', 'Master_Fvencimiento']:
            x.loc[x[c] < -36500, c] = np.nan
        return x.to_numpy(dtype=np.float32)
    xt, xp = matrix(train), matrix(august)
    y = train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    for value, key in [(xt, 'matriz_train_sha256'), (xp, 'matriz_agosto_sha256'), (y, 'target_sha256')]:
        if matrix_sha(value) != config[key]:
            raise ValueError(f'No coincide el payload original: {key}')
    return xt, xp, y, august[KEYS]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset', required=True, type=Path)
    ap.add_argument('--salida', type=Path, default=Path('resultado_tabpfn'))
    ap.add_argument('--cotizar', action='store_true', help='Consulta solo dimensiones; no envia datos de clientes')
    ap.add_argument('--ejecutar-api', action='store_true', help='Envia matrices y target a Prior Labs y consume creditos')
    ap.add_argument('--max-creditos', type=int, help='Limite obligatorio para ejecutar la API')
    args = ap.parse_args()
    if args.ejecutar_api and (args.max_creditos is None or args.max_creditos <= 0):
        ap.error('--ejecutar-api requiere --max-creditos positivo')
    verificar_archivos()
    config = json.loads((ROOT / 'configuracion_tabpfn.json').read_text(encoding='utf-8'))
    for package, expected in config['versiones'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f'Instalar requirements-tabpfn.txt en un entorno separado: {package} debe ser {expected}')
    if args.salida.resolve().is_relative_to(ROOT) and args.salida.resolve() == ROOT:
        ap.error('Elegir otra carpeta de salida')
    args.salida.mkdir(parents=True, exist_ok=True)
    state_path = args.salida / 'ESTADO_API.json'
    if args.ejecutar_api and state_path.exists():
        raise ValueError('Esta carpeta registra un intento API; revisar consumo y usar otra salida para una nueva corrida')
    xt, xp, y, keys = preparar(args.dataset.resolve(), config)
    ref = pd.read_csv(ROOT / 'artefactos/predicciones_agosto.csv.gz', float_precision='round_trip')
    pd.testing.assert_frame_equal(keys, ref[KEYS])
    save(args.salida / 'PREPARACION.json', dict(estado='payload_original_verificado', filas_train=len(xt),
         filas_agosto=len(xp), variables=xt.shape[1], target='BAJA+2', datos_clientes_enviados=False))
    print('Matrices y target originales verificados. Sin envio de clientes.', flush=True)
    if not (args.cotizar or args.ejecutar_api):
        return
    if not os.environ.get('TABPFN_TOKEN'):
        raise RuntimeError('Configurar TABPFN_TOKEN con una key propia de la catedra')
    from tabpfn_client import TabPFNClassifier, estimate_cost
    # Para cotizar se envian dimensiones, no los datos reales.
    quote = estimate_cost(np.broadcast_to(np.float32(0), xt.shape),
                          np.broadcast_to(np.float32(0), xp.shape),
                          model_version=config['model_version'], n_estimators=config['n_estimators'])
    save(args.salida / 'COTIZACION.json', quote.model_dump(mode='json'))
    print('Cotizacion actual:', quote.estimated_cost, 'creditos', flush=True)
    if not args.ejecutar_api:
        return
    if quote.estimated_cost > args.max_creditos:
        raise ValueError('Cotizacion supera limite; no se enviaron datos de clientes')
    state = dict(estado='inicio_api', datos_clientes_enviados=True,
                 creditos_estimados=quote.estimated_cost, max_creditos=args.max_creditos)
    save(state_path, state)
    try:
        model = TabPFNClassifier.create_default_for_version(config['model_version'],
            n_estimators=config['n_estimators'], random_state=config['random_state'],
            fit_mode=config['fit_mode'], inference_precision=config['inference_precision'],
            categorical_features_indices=[config['features'].index(c) for c in config['categorical_features']],
            inference_config=config['inference_config'])
        model.fit(xt, y)
        p = model.predict_proba(xp)[:, list(model.classes_).index(1)]
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError('Probabilidades invalidas')
        pred = keys.copy()
        pred['p_tabpfn'] = p
        pred.to_csv(args.salida / 'tabpfn_recalculado.csv', index=False)
        # Promover float32 a float64 igual que el CSV archivado de la corrida original.
        p = np.asarray(p, dtype=np.float64)
        lgb = ref[[f'p_lgb_seed{s}' for s in [541440, 408476, 741961, 248865, 717444]]].to_numpy()
        score = .5 * lgb.mean(axis=1) + .5 * p
        ids = keys.numero_de_cliente.to_numpy()
        order = np.lexsort((ids, -score))
        order = order[score[order] > .0275]
        content = ''.join(f'{int(ids[i])}\n' for i in order).encode('ascii')
        final_hash = hashlib.sha256(content).hexdigest()
        expected_hash = hashlib.sha256((ROOT / 'prediccion_final.csv').read_bytes()).hexdigest()
        (args.salida / 'prediccion_final_api.csv').write_bytes(content)
        original = ref.p_tabpfn.to_numpy()
        report = dict(csv_identico_byte_por_byte=final_hash == expected_hash,
            probabilidades_identicas=bool(np.array_equal(p, original)),
            error_maximo_tabpfn=float(np.max(np.abs(p - original))),
            contactos=len(order), cambios_de_seleccion=int(np.count_nonzero((score > .0275) != (ref.score_promedio5 > .0275))),
            sha256=final_hash, sha256_original=expected_hash)
        save(args.salida / 'COMPARACION.json', report)
        state['estado'] = 'completo'
        save(state_path, state)
        print(json.dumps(report, indent=2), flush=True)
        if not report['csv_identico_byte_por_byte']:
            raise SystemExit('La nueva API no reproduce exactamente la lista 43. Consultar COMPARACION.json.')
    except Exception:
        state['estado'] = 'error_tras_inicio_revisar_consumo'
        save(state_path, state)
        raise


if __name__ == '__main__':
    main()
