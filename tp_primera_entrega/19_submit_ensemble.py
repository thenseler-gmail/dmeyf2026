"""Genera ensemble agosto, 20 LightGBM + TabPFN guardado, p > 0.025."""
import hashlib
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--abandono-manifest',type=Path)
    args=parser.parse_args()
    sal=ROOT/'tp_primera_entrega/salidas'
    fuente=args.abandono_manifest or sal/'revision_umbral_20261005_131001/bajas/manifest.json'
    tabpath=sal/'01_entregas_bot/1_TabPFNHist_20261004_223836/predicciones_agosto.csv'
    m=json.loads(fuente.read_text())
    for f in ['features.py','baseline.py']:
        assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==m['codigo_sha256'][f]
    import importlib.metadata
    versiones=m.get('versiones')
    if versiones is None:
        versiones=json.loads((sal/'revision_umbral_20261005_131001/bajas/manifest.json').read_text())['versiones']
    for paquete,version in versiones.items():
        assert importlib.metadata.version(paquete)==version,paquete
    if args.abandono_manifest:
        assert m['estado']=='completo' and m.get('familia_elegida')=='haberes'
        assert m['features_nuevas']==['abandono_pasa_a_cero_mpayroll']
        columnas=m['features_base']+m['features_nuevas']
        semillas=m['comprobacion']['semillas']
        nombre=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHaberes_%Y%m%d_%H%M%S')
        out=sal/'candidatos_pendientes'/nombre
    else:
        columnas=m['features']
        semillas=m['semillas']
        nombre=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHist_%Y%m%d_%H%M%S')
        out=sal/'01_entregas_bot'/('3_'+nombre)
    out.mkdir(parents=True,exist_ok=False)
    elegido=m['elegido']
    assert elegido['target']=='bajas' and elegido['trial']==6
    protocolo=dict(estado='iniciado',submit=nombre,umbral=0.025,operador='>',peso_tabpfn=0.5,
        train_lightgbm=[202105,202106],futuro=202108,semillas=semillas,elegido=elegido,features=columnas,
        fuente_configuracion=str(fuente),versiones=versiones,fuente_tabpfn=str(tabpath),
        fuente_tabpfn_sha256=hashlib.sha256(tabpath.read_bytes()).hexdigest(),
        notas='Seleccion de configuracion en mayo por umbral fijo. No usa ranking ni top N. Sin inferencia API ni envio al bot.')
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
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
    if args.abandono_manifest:
        from features_abandono import agregar_abandono,FUENTES
        assert hashlib.sha256((Path(__file__).parent/'features_abandono.py').read_bytes()).hexdigest()==m['codigo_sha256']['features_abandono.py']
        adicionales=agregar_abandono(datos[claves+FUENTES])
        datos=datos.merge(adicionales[claves+m['features_nuevas']],on=claves,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.isin([202105,202106])].reset_index(drop=True)
    agosto=datos.loc[datos.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327882 and len(agosto)==164647
    assert train.clase_ternaria.isin(['BAJA+1','BAJA+2','CONTINUA']).all()
    xt=preparar(train,columnas)[0]; xp=preparar(agosto,columnas)[0]
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
    pred=agosto[claves].copy()
    for seed in semillas:
        modelo=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=elegido['num_boost_round'])
        pred[f'p_seed{seed}']=modelo.predict(xp)
        print('Semilla completa:',seed,flush=True)
    pred['p_lightgbm']=pred.filter(like='p_seed').mean(axis=1)
    tab=pd.read_csv(tabpath).rename(columns={'probabilidad':'p_tabpfn'})
    pred=pred.merge(tab,on=claves,validate='one_to_one')
    assert len(pred)==len(agosto)==len(tab)
    pred['probabilidad']=(pred.p_lightgbm+pred.p_tabpfn)/2
    probs=pred.filter(regex='^(p_|probabilidad)')
    assert np.isfinite(probs).all().all() and ((probs>=0)&(probs<=1)).all().all()
    pred.to_csv(out/'predicciones_agosto.csv',index=False)
    seleccion=pred.loc[pred.probabilidad>0.025].sort_values(['probabilidad','numero_de_cliente'],ascending=[False,True])
    ids=seleccion.numero_de_cliente
    assert not ids.duplicated().any() and np.equal(ids,np.floor(ids)).all()
    archivo=out/(nombre+'.csv')
    archivo.write_text(''.join(f'{int(i)}\n' for i in ids),encoding='ascii')
    lineas=archivo.read_text().splitlines()
    assert len(lineas)==len(ids) and all(i.isdigit() for i in lineas)
    assert set(map(int,lineas))==set(pred.loc[pred.probabilidad>0.025,'numero_de_cliente'].astype(int))
    assert set(map(int,lineas)).issubset(set(agosto.numero_de_cliente.astype(int)))
    (out/'MENSAJE_ZULIP.txt').write_text('submit '+nombre,encoding='ascii')
    protocolo.update(estado='completo',contactos=len(ids),filas_agosto=len(pred),archivo_submit=archivo.name,
        archivo_sha256=hashlib.sha256(archivo.read_bytes()).hexdigest())
    save()
    print('COMPLETO:',out,'\nContactos:',len(ids),'\nMensaje: submit '+nombre,flush=True)


if __name__=='__main__':
    main()
