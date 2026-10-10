"""Etapas independientes: preparar, CatBoost189, TabPFN189 API, evaluar local."""
import argparse
import hashlib
import importlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];SAL=ROOT/'tp_primera_entrega/salidas'
LIGHT=SAL/'features_local_20261006_140702';CAT=SAL/'catboost_local_20261006_004259'
KEYS=['numero_de_cliente','foto_mes'];SEEDS=[541440,408476,741961,248865,717444]
VARIANTS=['control16_50_50','mix17_40_40_20','cat189_tab202','cat202_tab189','todos189_40_40_20','lgb189_tab189_50_50']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def msha(x):return hashlib.sha256(x.astype(np.float32).tobytes()).hexdigest()


def preparar():
    module=importlib.import_module('63_experimentos_features_local')
    ref,seeds,train,valid,xt,xv,unused=module.cargar()
    lm=json.loads((LIGHT/'manifest.json').read_text(encoding='utf-8'))
    cm=json.loads((CAT/'manifest.json').read_text(encoding='utf-8'))
    assert lm['estado']==cm['estado']=='completo_verificado'
    for d,meta in [(LIGHT,lm),(CAT,cm)]:
        assert json.loads((d/'verificacion_independiente.json').read_text())['estado']=='verificado'
        for f,h in meta['archivos_sha256'].items():assert sha(d/f)==h
    cols=lm['firma']['variants']['historia_1_mes']['features']
    assert len(cols)==189 and seeds==SEEDS==cm['firma']['seeds']
    xt=xt[cols];xv=xv[cols]
    tx=xt.to_numpy();vx=xv.to_numpy();yt=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert msha(tx)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert msha(vx)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    assert hashlib.sha256(yt.tobytes()).hexdigest()==cm['firma']['target_train_sha256']
    lp=pd.read_csv(LIGHT/'historia_1_mes/predicciones_mayo.csv');cp=pd.read_csv(CAT/'predicciones_mayo.csv')
    pd.testing.assert_frame_equal(lp[KEYS+['clase_ternaria','parte_cliente']],cp[KEYS+['clase_ternaria','parte_cliente']])
    pd.testing.assert_frame_equal(lp[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(lp.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
    for seed in SEEDS:
        mp=LIGHT/'historia_1_mes'/f'seed{seed}.txt'
        assert sha(mp)==lm['modelos_sha256'][str(mp.relative_to(LIGHT))]
        model=lgb.Booster(model_file=str(mp));assert model.feature_name()==cols and model.num_trees()==273
        np.testing.assert_allclose(model.predict(xv,validate_features=True),lp[f'p_seed{seed}'],rtol=0,atol=1e-15)
        mp=CAT/'modelos'/f'seed{seed}.cbm';assert sha(mp)==cm['modelos_sha256'][mp.name]
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('todos189_local_%Y%m%d_%H%M%S');out.mkdir()
    np.savez_compressed(out/'matrices.npz',train=tx,valid=vx,target=yt)
    base=lp[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].rename(columns={'p_tabpfn':'p_tab202'})
    for seed in SEEDS:
        base[f'p_lgb189_seed{seed}']=lp[f'p_seed{seed}'];base[f'p_cat202_seed{seed}']=cp[f'p_cat_seed{seed}']
    base.to_csv(out/'predicciones_fuentes.csv',index=False)
    m=dict(estado='preparado',train=[202104],evaluacion=202105,aux_historia=[202103],features=cols,seeds=SEEDS,
        params_catboost=cm['firma']['params'],cat_features=cm['firma']['cat_features'],
        config_tabpfn=dict(model_version='v3.5-fast',n_estimators=2,random_state=214363,
                         fit_mode='fit_preprocessors',inference_precision='autocast',subsample_samples=None),
        target_catboost='BAJA+2',target_tabpfn='BAJA+2',target_lightgbm='BAJA+1/BAJA+2',
        variantes=VARIANTS,filas_train=163284,filas_validacion=163768,umbral=.025,operador='>',
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['72_todos189_local.py','63_experimentos_features_local.py','features.py','baseline.py']},
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [LIGHT/'manifest.json',CAT/'manifest.json',
             LIGHT/'historia_1_mes/predicciones_mayo.csv',CAT/'predicciones_mayo.csv']},
        matrices_sha256=sha(out/'matrices.npz'),train_matrix_sha256=msha(tx),valid_matrix_sha256=msha(vx),
        target_sha256=hashlib.sha256(yt.tobytes()).hexdigest(),base_predictions_sha256=sha(out/'predicciones_fuentes.csv'),
        nuevos_fits_catboost=5,nuevos_fits_lightgbm=0,nuevos_fits_tabpfn=1,api=False,creditos=0,submits=0,
        fit_eval_set=False,junio_leido=False,agosto_leido=False,
        payload_tabpfn='189featuresabril + targetBAJA2abril;189featuresmayo. SinID/mes/labelsMay ni junio/agosto. Destino API PriorLabs.',
        limitaciones='Mayo/semillas reutilizados, no test independiente. Pesos/corte/params congelados. Cruces prespecificados para separar cambios Cat/Tab; sin Optuna. Score de targets distintos no P(BAJA+2) calibrada.')
    save(out/'manifest.json',m);print('Salida:',out,flush=True)


def cargar(out):
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    for f,h in m['codigo_sha256'].items():assert sha(Path(__file__).parent/f)==h
    for f,h in m['source_hashes'].items():assert sha(ROOT/f)==h
    assert sha(out/'matrices.npz')==m['matrices_sha256'] and sha(out/'predicciones_fuentes.csv')==m['base_predictions_sha256']
    a=np.load(out/'matrices.npz');tx=a['train'];vx=a['valid'];y=a['target']
    assert msha(tx)==m['train_matrix_sha256'] and msha(vx)==m['valid_matrix_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==m['target_sha256']
    assert tx.shape==(163284,189) and vx.shape==(163768,189) and np.unique(y).tolist()==[0,1]
    return m,tx,vx,y


def catboost(out):
    from catboost import CatBoostClassifier,Pool
    m,tx,vx,y=cargar(out);cols=m['features']
    xt=pd.DataFrame(tx,columns=cols);xv=pd.DataFrame(vx,columns=cols)
    for frame in [xt,xv]:
        for c in m['cat_features']:frame[c]=frame[c].astype('string').fillna('__MISSING__').astype(str)
    pool=Pool(xt,label=y,cat_features=m['cat_features']);vp=Pool(xv,cat_features=m['cat_features'])
    base=pd.read_csv(out/'predicciones_fuentes.csv');p=base[KEYS].copy();md=out/'modelos_catboost189';md.mkdir(exist_ok=True)
    state=dict(estado='entrenando',semillas_completadas=[],params=m['params_catboost'],fit_eval_set=False,features=189)
    for seed in SEEDS:
        path=md/f'seed{seed}.cbm';start=time.perf_counter()
        if path.exists():model=CatBoostClassifier();model.load_model(str(path))
        else:
            print('Entrenando CatBoost189',seed,flush=True)
            model=CatBoostClassifier(**m['params_catboost'],random_seed=seed);model.fit(pool,verbose=100);model.save_model(str(path))
        assert model.tree_count_==800 and model.feature_names_==cols and model.classes_.tolist()==[0,1]
        p[f'p_cat189_seed{seed}']=model.predict_proba(vp)[:,1]
        reload=CatBoostClassifier();reload.load_model(str(path))
        np.testing.assert_allclose(reload.predict_proba(vp)[:,1],p[f'p_cat189_seed{seed}'],rtol=0,atol=0)
        p.to_csv(out/'predicciones_catboost189.csv',index=False)
        state['semillas_completadas'].append(seed);state.setdefault('tiempos',[]).append(dict(seed=seed,segundos=time.perf_counter()-start))
        save(out/'catboost_estado.json',state);print('CatBoost189',seed,'completo',flush=True)
    state.update(estado='completo',modelos_sha256={p.name:sha(p) for p in md.glob('*.cbm')},predicciones_sha256=sha(out/'predicciones_catboost189.csv'))
    save(out/'catboost_estado.json',state)


def tabpfn(out,max_creditos):
    m,tx,vx,y=cargar(out)
    if (out/'predicciones_tabpfn189.csv').exists():
        state=json.loads((out/'tabpfn_estado.json').read_text(encoding='utf-8'))
        assert state['estado']=='completo' and sha(out/'predicciones_tabpfn189.csv')==state['predicciones_sha256']
        print('TabPFN189 ya completo; no nueva API.',flush=True);return
    assert os.environ.get('TABPFN_TOKEN'),'Falta credencial en memoria'
    from tabpfn_client import TabPFNClassifier,estimate_cost,get_api_usage
    before=str(get_api_usage());quote=estimate_cost(tx.astype(np.float32),vx.astype(np.float32),model_version='v3.5-fast',n_estimators=2)
    state=dict(estado='cotizado',cuota_antes=before,cotizacion=quote.model_dump(mode='json'),max_creditos=max_creditos,
               payload=m['payload_tabpfn'],features=189,train=[202104],evaluacion=202105,creditos=0)
    save(out/'tabpfn_estado.json',state);print('Creditos estimados:',quote.estimated_cost,flush=True)
    if quote.estimated_cost>max_creditos:raise RuntimeError('Cotizacion supera limite; no inferencia')
    model=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,random_state=214363,
        fit_mode='fit_preprocessors',inference_precision='autocast',
        categorical_features_indices=[m['features'].index(c) for c in m['cat_features']],inference_config={'SUBSAMPLE_SAMPLES':None})
    state['estado']='ejecutando_api';save(out/'tabpfn_estado.json',state)
    model.fit(tx.astype(np.float32),y)
    prob=model.predict_proba(vx.astype(np.float32))[:,list(model.classes_).index(1)]
    assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
    p=pd.read_csv(out/'predicciones_fuentes.csv',usecols=KEYS);p['p_tab189']=prob
    p.to_csv(out/'predicciones_tabpfn189.csv',index=False)
    after=str(get_api_usage());used=lambda s:int(re.search(r'used (\d+)',s).group(1))
    state.update(estado='completo',cuota_despues=after,creditos=used(after)-used(before),predicciones_sha256=sha(out/'predicciones_tabpfn189.csv'),classes=model.classes_.tolist())
    save(out/'tabpfn_estado.json',state);print('TabPFN189 completo; creditos:',state['creditos'],flush=True)


def scores(p,s):
    lb=p[f'p_lgb189_seed{s}'];oldcb=p[f'p_cat202_seed{s}'];newcb=p[f'p_cat189_seed{s}'];oldtb=p.p_tab202;newtb=p.p_tab189
    return dict(control16_50_50=(lb+oldtb)/2,mix17_40_40_20=.4*lb+.4*oldtb+.2*oldcb,
        cat189_tab202=.4*lb+.4*oldtb+.2*newcb,cat202_tab189=.4*lb+.4*newtb+.2*oldcb,
        todos189_40_40_20=.4*lb+.4*newtb+.2*newcb,lgb189_tab189_50_50=(lb+newtb)/2)


def metric(y,q):
    sel=np.asarray(q)>.025;tp=int((sel&y).sum());n=int(sel.sum());g=tp*1100000-n*27500
    assert g==int(np.where(y,1072500,-27500)[sel].sum())
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)


def evaluar(out):
    m,unused1,unused2,unused3=cargar(out)
    cs=json.loads((out/'catboost_estado.json').read_text(encoding='utf-8'));ts=json.loads((out/'tabpfn_estado.json').read_text(encoding='utf-8'))
    assert cs['estado']==ts['estado']=='completo' and cs['semillas_completadas']==SEEDS
    assert sha(out/'predicciones_catboost189.csv')==cs['predicciones_sha256'] and sha(out/'predicciones_tabpfn189.csv')==ts['predicciones_sha256']
    p=pd.read_csv(out/'predicciones_fuentes.csv');cb=pd.read_csv(out/'predicciones_catboost189.csv');tb=pd.read_csv(out/'predicciones_tabpfn189.csv')
    for frame in [cb,tb]:pd.testing.assert_frame_equal(p[KEYS],frame[KEYS])
    for c in cb:
        if c not in KEYS:p[c]=cb[c]
    p['p_tab189']=tb.p_tab189;p.to_csv(out/'predicciones_mayo.csv',index=False)
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();parts=p.parte_cliente.to_numpy();rows=[];pr=[];changes=[]
    for s in SEEDS:
        qs=scores(p,s);base=qs['control16_50_50']>.025
        for v,q in qs.items():
            rows.append(dict(variante=v,seed=s,**metric(y,q)))
            for k in range(4):mask=parts==k;pr.append(dict(variante=v,seed=s,parte=k,**metric(y[mask],q[mask])))
            sel=q>.025;add=sel&~base;remove=base&~sel
            changes.append(dict(variante=v,seed=s,agregados=int(add.sum()),retirados=int(remove.sum()),agregados_baja2=int((add&y).sum()),retirados_baja2=int((remove&y).sum())))
    r=pd.DataFrame(rows);r.to_csv(out/'resultados_semillas.csv',index=False)
    pr=pd.DataFrame(pr);pr.to_csv(out/'resultados_partes_mayo.csv',index=False);pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    summary=r.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean().loc[VARIANTS]
    assert summary.loc['control16_50_50','ganancia']==266420000 and summary.loc['mix17_40_40_20','ganancia']==269813500
    pivot=r.pivot(index='seed',columns='variante',values='ganancia');groups=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['delta_vs16_total']=summary.ganancia-266420000;summary['delta_vs16_25pct']=summary.delta_vs16_total/4
    summary['delta_vs17_total']=summary.ganancia-269813500;summary['delta_vs17_25pct']=summary.delta_vs17_total/4
    summary['semillas_mejoran_vs16']=[int((pivot[v]>pivot.control16_50_50).sum()) for v in VARIANTS]
    summary['semillas_mejoran_vs17']=[int((pivot[v]>pivot.mix17_40_40_20).sum()) for v in VARIANTS]
    summary['partes_mejoran_vs16']=[int((groups[v]>groups.control16_50_50).sum()) for v in VARIANTS]
    summary.to_csv(out/'comparacion_media5.csv')
    pmean=p.copy();s=SEEDS[0]
    for prefix in ['p_lgb189_seed','p_cat202_seed','p_cat189_seed']:pmean[prefix+str(s)]=p[[prefix+str(k) for k in SEEDS]].mean(axis=1)
    pd.DataFrame([dict(variante=v,**metric(y,q)) for v,q in scores(pmean,s).items()]).to_csv(out/'lista_promedio5.csv',index=False)
    m.update(estado='completo_pendiente_verificacion',api=True,creditos=ts['creditos'],resultados=summary.reset_index().to_dict('records'),
             modelos_catboost_sha256=cs['modelos_sha256'],archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},
             supera16_local=bool(summary.loc['todos189_40_40_20','ganancia']>266420000),supera17_local=bool(summary.loc['todos189_40_40_20','ganancia']>269813500))
    save(out/'manifest.json',m);print(summary.to_string(),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--etapa',choices=['preparar','catboost','tabpfn','evaluar'],required=True)
    ap.add_argument('--salida',type=Path);ap.add_argument('--max-creditos',type=int,default=80000);args=ap.parse_args()
    if args.etapa=='preparar':preparar()
    else:
        assert args.salida is not None
        if args.etapa=='catboost':catboost(args.salida.resolve())
        elif args.etapa=='tabpfn':tabpfn(args.salida.resolve(),args.max_creditos)
        else:evaluar(args.salida.resolve())
