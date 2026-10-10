"""Congela el bloque auditado; train abril/mayo->agosto, TabPFN202 guardado."""
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas
from features_trayectorias import FEATURES,FUENTES,KEYS,agregar_trayectorias


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1];sal=root/'tp_primera_entrega/salidas';source=Path(sys.argv[1])
    m=json.loads((source/'manifest.json').read_text())
    assert json.loads((source/'verificacion.json').read_text())['estado']=='verificado'
    scores=pd.read_csv(source/'comparacion.csv').set_index('variante')
    assert scores.loc['trayectorias','ganancia']>scores.loc['control','ganancia']
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    cols=m['features_control']+FEATURES;seeds=m['semillas'];spec=m['elegido']
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(root/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * EXCLUDE(clase_ternaria),CASE WHEN foto_mes IN (202104,202105) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(datos[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy());hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    datos=datos.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    datos=datos.merge(agregar_trayectorias(datos[KEYS+FUENTES]),on=KEYS,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.isin([202104,202105])];august=datos.loc[datos.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327052 and len(august)==164647 and august.clase_ternaria.isna().all()
    xt=preparar(train,cols)[0];xp=preparar(august,cols)[0];y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleTrayectorias5_%Y%m%d_%H%M%S')
    out=sal/'candidatos_pendientes'/name;out.mkdir(parents=True);(out/'modelos').mkdir()
    pred=august[KEYS].copy()
    for seed in seeds:
        model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=spec['num_boost_round'])
        model.save_model(str(out/'modelos'/f'seed{seed}.txt'));pred[f'p_seed{seed}']=model.predict(xp,validate_features=True)
        pred.to_csv(out/'predicciones_agosto.csv',index=False);print('Final agosto semilla',seed,'lista',flush=True)
    tabpath=sal/'01_entregas_bot/8_EnsembleAbrilMayo5_20261005_220000/predicciones_agosto.csv'
    tbm=json.loads((tabpath.parent/'manifest.json').read_text());assert tbm['train_final']==[202104,202105] and tbm['target_tabpfn']=='BAJA+2'
    tab=pd.read_csv(tabpath);pd.testing.assert_frame_equal(pred[KEYS],tab[KEYS])
    pred['p_tabpfn']=tab.p_tabpfn;pred['p_lightgbm']=pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    pred['probabilidad']=(pred.p_tabpfn+pred.p_lightgbm)/2;pred.to_csv(out/'predicciones_agosto.csv',index=False)
    files=[]
    for variante in ['semillas','lightgbm','promedio5']:
        adj=out/f'adjuntos_{variante}';adj.mkdir();submit=name+'_'+variante
        choices=[('promedio',pred.probabilidad)] if variante=='promedio5' else [(f'seed{s}',pred[f'p_seed{s}'] if variante=='lightgbm' else (pred[f'p_seed{s}']+pred.p_tabpfn)/2) for s in seeds]
        for label,p in choices:
            assert np.isfinite(p).all() and p.between(0,1).all()
            df=pred.loc[p>.025,KEYS].copy();df['p']=p[p>.025];df=df.sort_values(['p','numero_de_cliente'],ascending=[False,True])
            file=adj/f'{submit}_{label}.csv';file.write_text(''.join(f'{int(i)}\n' for i in df.numero_de_cliente),encoding='ascii')
            assert len(df)==df.numero_de_cliente.nunique()
            files.append(dict(variante=variante,label=label,archivo=str(file.relative_to(out)),contactos=len(df),sha256=sha(file)))
        (out/f'MENSAJE_{variante.upper()}.txt').write_text('submit '+submit,encoding='ascii')
    meta=dict(estado='preparado_pendiente',enviado=False,submit=name,semillas=seeds,features_lightgbm=cols,
              features_tabpfn=tbm['firma']['features'],elegido=spec,train=[202104,202105],futuro=202108,
              umbral=.025,operador='>',peso_tabpfn=.5,api=False,creditos=0,fuente_desarrollo=str(source),
              fuente_tabpfn=str(tabpath),fuente_tabpfn_sha256=sha(tabpath),archivos=files,
              archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},
              modelos_sha256={p.name:sha(p) for p in (out/'modelos').glob('*.txt')},
              codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['49_candidato_trayectorias.py','features_trayectorias.py','features.py','baseline.py']},
              limitaciones=m['limitaciones'],resultado_local=m['comparacion'])
    (out/'manifest.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'ESTADO_ENVIO.txt').write_text('PENDIENTE. Preferencia:5mezclas en adjuntos_semillas/. LocalCVmayo porcliente,no garantiaagosto.\n',encoding='utf-8')
    print('Candidato:',out,'\nAdjuntos:',files,flush=True)


if __name__=='__main__':main()
