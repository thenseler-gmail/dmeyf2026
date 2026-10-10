"""Primera prueba Zulip: mayo+junio -> agosto, Fast 2, historia ampliada.

Por defecto prepara localmente. --ejecutar-api cotiza y genera predicciones.
No envia mensajes a Zulip. CSV sin encabezado, IDs enteros.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
from baseline import preparar
from features import agregar_historicas_ampliadas, HISTORICAS, HISTORICAS_EXTRA

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ejecutar-api', action='store_true')
    parser.add_argument('--max-creditos', type=int, default=150000)
    args = parser.parse_args()
    config = json.loads((ROOT / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT / config['dataset'])).create_view('datos')
        datos = con.sql('SELECT * FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    claves = [config['id_col'], config['mes_col']]
    target = config['target_col']
    originales = [c for c in datos if c not in claves + [target]]
    fuentes = HISTORICAS + HISTORICAS_EXTRA
    historia = datos[claves + fuentes].copy()
    historia[fuentes] = historia[fuentes].replace([np.inf, -np.inf], np.nan)
    historia = agregar_historicas_ampliadas(historia)
    nuevas = [c for c in historia if c not in claves + fuentes]
    datos = datos.merge(historia[claves + nuevas], on=claves, validate='one_to_one', sort=False)
    train = datos.loc[datos.foto_mes.isin([202105, 202106])].copy()
    futuro = datos.loc[datos.foto_mes.eq(202108)].copy()
    if train.empty or futuro.empty or not train[target].isin(['BAJA+1','BAJA+2','CONTINUA']).all():
        raise ValueError('Particiones o etiquetas de entrenamiento invalidas.')
    columnas = originales + nuevas
    xt, _ = preparar(train, columnas)
    xp, _ = preparar(futuro, columnas)
    yt = train[target].eq('BAJA+2').astype(int).to_numpy()
    nombre = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('TabPFNHist_%Y%m%d_%H%M%S')
    out = ROOT / config['salidas'] / nombre
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(estado='preparado', train_meses=[202105,202106], prediccion_mes=202108,
                    model_version='v3.5-fast', n_estimators=2, seed=config['seed'], umbral=0.025,
                    filas_train=len(train), filas_futuro=len(futuro), features=columnas,
                    historial='Solo meses anteriores, sin targets auxiliares', submit=nombre,
                    codigo_sha256={p: hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest()
                                   for p in ['13_submit_tabpfn.py','features.py','baseline.py']})
    def guardar():
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    guardar()
    print(f'Train: {len(train)}; agosto: {len(futuro)}; variables: {len(columnas)}', flush=True)
    if not args.ejecutar_api:
        print('Preparado sin API:', out)
        return
    if not os.environ.get('TABPFN_TOKEN'):
        raise RuntimeError('Falta TABPFN_TOKEN.')
    from tabpfn_client import TabPFNClassifier, estimate_cost, get_api_usage
    manifest['cuota_antes'] = str(get_api_usage())
    quote = estimate_cost(xt, xp, model_version='v3.5-fast', n_estimators=2)
    manifest['cotizacion'] = quote.model_dump(mode='json')
    guardar()
    print('Consumo estimado:', quote.estimated_cost, flush=True)
    if quote.estimated_cost > args.max_creditos:
        raise ValueError('Presupuesto excedido; no se subieron datos.')
    modelo = TabPFNClassifier.create_default_for_version('v3.5-fast', n_estimators=2,
        random_state=config['seed'], fit_mode='fit_preprocessors', inference_precision='autocast',
        categorical_features_indices=[columnas.index(c) for c in ['Visa_status','Master_status','tcuentas']],
        inference_config={'SUBSAMPLE_SAMPLES': None})
    modelo.fit(xt.to_numpy(dtype=np.float32), yt)
    prob = modelo.predict_proba(xp.to_numpy(dtype=np.float32))[:, list(modelo.classes_).index(1)]
    if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
        raise ValueError('Probabilidades invalidas.')
    pred = futuro[claves].copy()
    pred['probabilidad'] = prob
    pred.to_csv(out/'predicciones_agosto.csv', index=False)
    seleccion = pred.loc[pred.probabilidad.gt(0.025)].sort_values(['probabilidad',config['id_col']], ascending=[False,True])
    ids = seleccion[config['id_col']]
    if ids.isna().any() or ids.duplicated().any() or not np.equal(ids, np.floor(ids)).all():
        raise ValueError('IDs invalidos.')
    manifest['contactos_umbral'] = len(ids)
    if not 8000 <= len(ids) <= 15000:
        manifest['estado'] = 'requiere_decision_contactos'
        guardar()
        raise ValueError(f'Umbral genera {len(ids)} contactos fuera de 8000..15000; predicciones guardadas.')
    archivo = out/(nombre+'.csv')
    contenido = ''.join(f'{int(i)}\n' for i in ids)
    archivo.write_text(contenido, encoding='ascii')
    lineas = archivo.read_text(encoding='ascii').splitlines()
    assert len(lineas) == len(ids) and all(s.isdigit() for s in lineas)
    assert set(map(int,lineas)).issubset(set(map(int,futuro[config['id_col']])))
    manifest.update(estado='completo', archivo_submit=archivo.name,
                    archivo_sha256=hashlib.sha256(archivo.read_bytes()).hexdigest())
    guardar()
    (out/'MENSAJE_ZULIP.txt').write_text('submit '+nombre, encoding='ascii')
    print('Contactos:', len(ids), '\nAdjunto:', archivo, '\nMensaje: submit '+nombre, flush=True)


if __name__ == '__main__':
    main()
