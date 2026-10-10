"""Reproduce los CSV finales del script 14, sin repetir Optuna ni seleccion.

Usa el manifest completo del experimento y compara hashes de cada CSV.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--salida',required=True,type=Path)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    if manifest['estado']!='completo':
        raise ValueError('Se necesita un experimento completo.')
    for p,v in manifest['versiones'].items():
        if importlib.metadata.version(p)!=v:
            raise ValueError('Version incompatible: '+p)
    for p in ['features.py','baseline.py']:
        if hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest()!=manifest['codigo_sha256'][p]:
            raise ValueError('Generador incompatible: '+p)
    if args.salida.exists():
        raise ValueError('La salida debe ser una carpeta nueva.')
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    claves=['numero_de_cliente','foto_mes']
    fuentes=HISTORICAS+HISTORICAS_EXTRA
    historia=datos[claves+fuentes].copy()
    historia[fuentes]=historia[fuentes].replace([np.inf,-np.inf],np.nan)
    historia=agregar_historicas_ampliadas(historia)
    nuevas=[c for c in historia if c not in claves+fuentes]
    datos=datos.merge(historia[claves+nuevas],on=claves,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.isin(manifest['train_final'])].reset_index(drop=True)
    futuro=datos.loc[datos.foto_mes.eq(manifest['futuro'])].reset_index(drop=True)
    if train.empty or futuro.empty or not train.clase_ternaria.isin(['BAJA+1','BAJA+2','CONTINUA']).all():
        raise ValueError('Dataset incompatible.')
    xt,_=preparar(train,manifest['features'])
    xp,_=preparar(futuro,manifest['features'])
    elegido=manifest['elegido']
    y=(train.clase_ternaria.eq('BAJA+2') if elegido['target']=='baja2'
       else train.clase_ternaria.isin(['BAJA+1','BAJA+2'])).astype(int).to_numpy()
    args.salida.mkdir(parents=True)
    resultados=[]
    for seed,archivo in zip(manifest['semillas'],manifest['archivos'],strict=True):
        model=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt,label=y),
                        num_boost_round=elegido['num_boost_round'])
        prob=model.predict(xp)
        if not np.isfinite(prob).all():
            raise ValueError('Probabilidades invalidas.')
        ids=futuro.numero_de_cliente.to_numpy()
        ids=ids[np.lexsort((ids,-prob))[:elegido['contactos']]]
        destino=args.salida/Path(archivo['nombre']).name
        destino.write_text(''.join(f'{int(i)}\n' for i in ids),encoding='ascii')
        digest=hashlib.sha256(destino.read_bytes()).hexdigest()
        coincide=digest==archivo['sha256']
        resultados.append(dict(archivo=destino.name,sha256=digest,coincide=coincide))
        print(seed,'identico:',coincide,flush=True)
        if not coincide:
            raise ValueError('No reprodujo el CSV original: '+destino.name)
    (args.salida/'verificacion.json').write_text(json.dumps(resultados,indent=2),encoding='utf-8')
    print('Los 20 CSV coinciden byte por byte con los originales.',flush=True)


if __name__=='__main__':
    main()
