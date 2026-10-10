"""Prueba ventana abril+mayo->agosto; parametros/semillas/features congelados.

Por defecto prepara LightGBM local. API opcional para alinear TabPFN BAJA+2.
No selecciona con junio ni agosto; no envia mensajes al Bot.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
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
SAL=ROOT/'tp_primera_entrega/salidas'
KEYS=['numero_de_cliente','foto_mes']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,m):
    p.write_text(json.dumps(m,indent=2,ensure_ascii=False,default=str),encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reanudar',type=Path)
    ap.add_argument('--ejecutar-api',action='store_true')
    ap.add_argument('--max-creditos',type=int,default=150000)
    args=ap.parse_args()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    rp=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238/manifest.json'
    ref=json.loads(rp.read_text());cols=ref['features_lightgbm'];seeds=ref['semillas'];spec=ref['elegido']
    assert spec['target']=='bajas' and spec['trial']==6 and len(cols)==202 and len(seeds)==5
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(datos[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    datos=datos.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.isin([202104,202105])].reset_index(drop=True)
    august=datos.loc[datos.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327052 and len(august)==164647
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all() and august.clase_ternaria.isna().all()
    xt=preparar(train,cols)[0];xp=preparar(august,cols)[0]
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
    yt=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    firma=dict(codigo={f:sha(Path(__file__).parent/f) for f in ['45_ventana_abril_mayo_agosto.py','features.py','baseline.py']},
               features=cols,semillas=seeds,elegido=spec,train=[202104,202105],futuro=202108,
               versiones={p:importlib.metadata.version(p) for p in ['lightgbm','tabpfn-client','numpy','pandas','duckdb']},
               matriz_train_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
               matriz_agosto_sha256=hashlib.sha256(xp.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
               target_tabpfn_sha256=hashlib.sha256(yt.tobytes()).hexdigest())
    if args.reanudar:
        out=args.reanudar;meta=json.loads((out/'manifest.json').read_text());assert meta['firma']==firma
    else:
        name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleAbrilMayo5_%Y%m%d_%H%M%S')
        root=SAL/'01_entregas_bot'
        numbers=[int(p.name.split('_')[0]) for p in root.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit()]
        out=root/f'{max(numbers)+1}_{name}';out.mkdir()
        meta=dict(estado='preparando_local',submit=name,firma=firma,enviado=False,umbral=.025,operador='>',
                  peso_tabpfn=.5,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
                  train_final=[202104,202105],futuro=202108,filas_train=len(train),filas_agosto=len(august),
                  model_version='v3.5-fast',n_estimators=2,seed_tabpfn=214363,referencia=str(rp.parent),
                  criterio='Cambiar exclusivamente la ventana de train; no nueva busqueda/seleccion de parametros o semillas.',
                  limitaciones='Ganancia agosto desconocida. Se conserva historia calendario previa: junio/julio aportan features de agosto, sin etiquetas. Abril/mayo tienen menor cobertura historica que mayo/junio. No test local posterior sin junio.',
                  creditos=0,api=False)
    save(out/'manifest.json',meta)
    modeldir=out/'modelos';modeldir.mkdir(exist_ok=True)
    predpath=out/'predicciones_agosto.csv'
    pred=pd.read_csv(predpath) if predpath.exists() else august[KEYS].copy()
    pd.testing.assert_frame_equal(pred[KEYS],august[KEYS])
    print('Salida:',out,flush=True)
    for seed in seeds:
        col=f'p_seed{seed}';mp=modeldir/f'seed{seed}.txt'
        if col not in pred:
            model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=spec['num_boost_round'])
            model.save_model(str(mp));pred[col]=model.predict(xp,validate_features=True)
            pred.to_csv(predpath,index=False)
        assert mp.exists()
        print('LightGBM semilla',seed,'lista',flush=True)
    pred['p_lightgbm']=pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    def export(variante,probabilidades):
        folder=out/f'adjuntos_{variante}';folder.mkdir(exist_ok=True)
        submit=meta['submit']+'_'+variante;files=[]
        for label,p in probabilidades:
            assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
            sel=pred.loc[p>.025,KEYS].copy();sel['p']=p[p>.025]
            sel=sel.sort_values(['p','numero_de_cliente'],ascending=[False,True])
            file=folder/f'{submit}_{label}.csv'
            file.write_text(''.join(f'{int(i)}\n' for i in sel.numero_de_cliente),encoding='ascii')
            assert len(sel)==sel.numero_de_cliente.nunique()
            files.append(dict(variante=variante,label=label,archivo=str(file.relative_to(out)),contactos=len(sel),sha256=sha(file)))
        (out/f'MENSAJE_{variante.upper()}.txt').write_text('submit '+submit,encoding='ascii')
        meta.setdefault('archivos',{})[variante]=files
    export('lightgbm',[(f'seed{s}',pred[f'p_seed{s}']) for s in seeds])
    pred.to_csv(predpath,index=False)
    meta.update(estado='lightgbm_preparado_tabpfn_pendiente',modelos_sha256={p.name:sha(p) for p in modeldir.glob('*.txt')})
    save(out/'manifest.json',meta)
    if 'p_tabpfn' not in pred and args.ejecutar_api:
        if not os.environ.get('TABPFN_TOKEN'):raise RuntimeError('Falta credencial en entorno del proceso.')
        from tabpfn_client import TabPFNClassifier,estimate_cost,get_api_usage
        meta['cuota_antes']=str(get_api_usage())
        quote=estimate_cost(xt,xp,model_version='v3.5-fast',n_estimators=2)
        meta['cotizacion']=quote.model_dump(mode='json');save(out/'manifest.json',meta)
        print('Creditos estimados:',quote.estimated_cost,flush=True)
        if quote.estimated_cost>args.max_creditos:raise RuntimeError('Cotizacion supera limite local; sin inferencia.')
        model=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,random_state=214363,
              fit_mode='fit_preprocessors',inference_precision='autocast',
              categorical_features_indices=[cols.index(c) for c in ['Visa_status','Master_status','tcuentas']],
              inference_config={'SUBSAMPLE_SAMPLES':None})
        meta['estado']='ejecutando_tabpfn';save(out/'manifest.json',meta)
        model.fit(xt.to_numpy(dtype=np.float32),yt)
        p=model.predict_proba(xp.to_numpy(dtype=np.float32))[:,list(model.classes_).index(1)]
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        pred['p_tabpfn']=p;pred.to_csv(predpath,index=False)
        meta.update(api=True,creditos_estimados=quote.estimated_cost,cuota_despues=str(get_api_usage()))
        save(out/'manifest.json',meta)
    if 'p_tabpfn' in pred:
        pred['probabilidad']=(pred.p_lightgbm+pred.p_tabpfn)/2
        export('semillas',[(f'seed{s}',(pred[f'p_seed{s}']+pred.p_tabpfn)/2) for s in seeds])
        export('promedio5',[('promedio',pred.probabilidad)])
        pred.to_csv(predpath,index=False)
        meta.update(estado='completo_preparado_pendiente',estado_envio='todas variantes pendientes',
                    predicciones_sha256=sha(predpath))
        (out/'ESTADO_ENVIO.txt').write_text('PENDIENTE DE ENVIO POR TOMAS\nPreferencia: cinco mezclas en adjuntos_semillas/.\nLightGBM solo y promedio5 son alternativas separadas.\n',encoding='utf-8')
    else:
        meta['predicciones_sha256']=sha(predpath)
        (out/'ESTADO_ENVIO.txt').write_text('LightGBM5 preparado, TabPFN/ensemble pendiente. No enviado.\n',encoding='utf-8')
    save(out/'manifest.json',meta)
    print(meta['estado'],meta.get('archivos'),flush=True)


if __name__=='__main__':main()
