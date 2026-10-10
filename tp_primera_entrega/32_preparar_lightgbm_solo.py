"""Prepara referencia LightGBM puro desde 20 semillas guardadas, sin entrenar.

No usa la probabilidad TabPFN. No envia el archivo al Bot ni lo numera como enviado.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'


def main():
    fuente=SAL/'01_entregas_bot/3_EnsembleHist_20261005_131953'
    ref=json.loads((fuente/'manifest.json').read_text())
    configpath=SAL/'revision_umbral_20261005_131001/bajas/manifest.json'
    modelref=json.loads(configpath.read_text())
    assert ref['estado']=='completo' and ref['train_lightgbm']==[202105,202106]
    assert ref['elegido']['target']=='bajas' and ref['elegido']['trial']==6
    assert ref['elegido']==modelref['elegido'] and ref['semillas']==modelref['semillas']
    assert len(modelref['features'])==202 and len(ref['semillas'])==20
    cols=['numero_de_cliente','foto_mes']+[f'p_seed{s}' for s in ref['semillas']]+['p_lightgbm']
    source=fuente/'predicciones_agosto.csv'
    df=pd.read_csv(source,usecols=cols)
    assert len(df)==164647 and df.foto_mes.eq(202108).all()
    assert not df.numero_de_cliente.duplicated().any()
    p=df[[f'p_seed{s}' for s in ref['semillas']]].mean(axis=1)
    assert np.allclose(p,df.p_lightgbm,rtol=1e-12,atol=1e-14)
    assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        ids=con.sql('SELECT numero_de_cliente FROM datos WHERE foto_mes=202108 ORDER BY numero_de_cliente').df()
    assert np.array_equal(np.sort(df.numero_de_cliente.to_numpy()),ids.numero_de_cliente.to_numpy())
    nombre=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('LightGBMHistSolo_%Y%m%d_%H%M%S')
    out=SAL/'candidatos_pendientes'/nombre
    out.mkdir(parents=True,exist_ok=False)
    pred=df[['numero_de_cliente','foto_mes']].copy()
    pred['probabilidad']=p
    pred.to_csv(out/'predicciones_agosto.csv',index=False)
    selected=pred.loc[pred.probabilidad>.025].sort_values(['probabilidad','numero_de_cliente'],ascending=[False,True])
    archivo=out/(nombre+'.csv')
    archivo.write_text(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente),encoding='ascii')
    enviados=list(map(int,archivo.read_text().splitlines()))
    assert len(enviados)==len(set(enviados))==len(selected)
    assert set(enviados)==set(pred.loc[pred.probabilidad>.025,'numero_de_cliente'])
    (out/'MENSAJE_ZULIP.txt').write_text('submit '+nombre,encoding='ascii')
    manifest=dict(estado='completo_verificado',rol='referencia LightGBM puro, no ganador del nuevo CV',submit=nombre,
        archivo_submit=archivo.name,archivo_sha256=hashlib.sha256(archivo.read_bytes()).hexdigest(),
        fuente_probabilidades=str(source),fuente_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        features=modelref['features'],elegido=ref['elegido'],semillas=ref['semillas'],versiones=modelref['versiones'],
        train_meses=[202105,202106],futuro=202108,umbral=.025,operador='>',contactos=len(enviados),
        filas_agosto=len(df),api=False,creditos=0,peso_tabpfn=0,
        referencia_junio=dict(ganancia=402765000,ganancia_25pct=100691250,contactos=12674),
        objetivo_publico=100000000,ganancia_agosto='desconocida',
        notas='Promedio de20 semillas LightGBM combinado ya guardadas; no usa TabPFN ni nuevas inferencias. La referencia junio es exploratoria y no garantiza100millones publico. No enviado ni numerado como entrega; train junio permanece, aunque junio no decida solo la seleccion.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Salida:',out,'\nContactos:',len(enviados),'\nMensaje: submit '+nombre)


if __name__=='__main__':
    main()
