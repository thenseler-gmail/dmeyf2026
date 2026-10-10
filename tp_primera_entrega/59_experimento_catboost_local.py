"""Tres variantes predefinidas con CatBoost BAJA+2; solo validacion abril->mayo."""
import argparse
import hashlib
import importlib.metadata
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier,Pool
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
KEYS=['numero_de_cliente','foto_mes']
CAT_COLS=['Visa_status','Master_status','tcuentas']
# Fijados antes de observar ganancias: no early stopping ni eval_set en mayo.
PARAMS=dict(iterations=800,learning_rate=.05,depth=6,l2_leaf_reg=5,
    loss_function='Logloss',boosting_type='Plain',bootstrap_type='Bernoulli',
    subsample=.8,rsm=.8,random_strength=1,border_count=128,nan_mode='Min',
    thread_count=4,task_type='CPU',allow_writing_files=False)
VARIANTES=['CatBoost_solo','CatBoost_TabPFN_50_50','LightGBM_TabPFN_CatBoost_40_40_20']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,m):p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def cargar():
    src=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    ref=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    assert ref['validacion_train']==[202104] and ref['validacion_eval']==202105
    cols=ref['features_lightgbm'];seeds=ref['semillas'];assert len(cols)==202 and len(seeds)==5
    sf=src/'predicciones_mayo.csv';assert sha(sf)==ref['hashes_resultados']['predicciones_mayo.csv']
    control=pd.read_csv(sf)
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any()
    h=agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.eq(202104)].reset_index(drop=True)
    valid=raw.loc[raw.foto_mes.eq(202105)].reset_index(drop=True)
    assert len(train)==163284 and len(valid)==163768
    pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],control[KEYS+['clase_ternaria']])
    xt=preparar(train,cols)[0];xv=preparar(valid,cols)[0]
    return src,cols,seeds,train,valid,xt,xv,control

def categorizar(x):
    x=x.copy()
    for c in CAT_COLS:x[c]=x[c].astype('string').fillna('__MISSING__').astype(str)
    return x

def metric(y,prob):
    sel=np.asarray(prob)>.025;n=int(sel.sum());tp=int((sel&y).sum());g=tp*1100000-n*27500
    assert int(np.where(y,1072500,-27500)[sel].sum())==g
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)

def probabilities(p,s):
    cb=p[f'p_cat_seed{s}'].to_numpy();lb=p[f'p_lgb_seed{s}'].to_numpy();tb=p.p_tabpfn.to_numpy()
    return {'control_entrega8':(lb+tb)/2,'CatBoost_solo':cb,
      'CatBoost_TabPFN_50_50':(cb+tb)/2,'LightGBM_TabPFN_CatBoost_40_40_20':.4*lb+.4*tb+.2*cb}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    src,cols,seeds,train,valid,xt,xv,control=cargar()
    # Primero reproducir todos los LightGBM del control, sin nuevos fits.
    for s in seeds:
        model=lgb.Booster(model_file=str(src/'modelos_validacion'/f'seed{s}.txt'))
        assert model.feature_name()==cols and model.num_trees()==273
        np.testing.assert_allclose(model.predict(xv,validate_features=True),control[f'p_seed{s}'],rtol=0,atol=1e-15)
    yt=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy();yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xct=categorizar(xt);xcv=categorizar(xv)
    signature=dict(params=PARAMS,features=cols,cat_features=CAT_COLS,seeds=seeds,target='BAJA+2',
        source_sha256=sha(src/'predicciones_mayo.csv'),
        matriz_train_sha256=hashlib.sha256(pd.util.hash_pandas_object(xct,index=False).to_numpy().tobytes()).hexdigest(),
        matriz_mayo_sha256=hashlib.sha256(pd.util.hash_pandas_object(xcv,index=False).to_numpy().tobytes()).hexdigest(),
        target_train_sha256=hashlib.sha256(yt.tobytes()).hexdigest(),
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['59_experimento_catboost_local.py','features.py','baseline.py']},
        versiones={p:importlib.metadata.version(p) for p in ['catboost','lightgbm','numpy','pandas','duckdb']})
    if args.reanudar:
        out=args.reanudar;m=json.loads((out/'manifest.json').read_text());assert m['firma']==signature
    else:
        out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('catboost_local_%Y%m%d_%H%M%S');out.mkdir()
        m=dict(estado='entrenando',firma=signature,train=[202104],evaluacion=202105,aux_historia=[202103],
             filas_train=len(train),filas_validacion=len(valid),umbral=.025,operador='>',
             variantes=VARIANTES,fuente_control=str(src),api=False,creditos=0,submits=0,nuevos_fits_catboost=5,
             junio_leido=False,agosto_leido=False,fit_eval_set=False,semillas_completadas=[],
             limitaciones='Mayo y semillas reutilizados: no test independiente ni garantia agosto. Parametros CatBoost fijados sin busqueda; primera configuracion, no mejor CatBoost posible. Tres variables categoricas tratadas como categorias, resto numeric/NaN; mismos202predictores. Ganancia premia solo BAJA+2, controlLightGBM combinado. No validacion junio ni Bot.')
    save(out/'manifest.json',m);md=out/'modelos';md.mkdir(exist_ok=True)
    tp=Pool(xct,label=yt,cat_features=CAT_COLS);vp=Pool(xcv,cat_features=CAT_COLS)
    print('Salida:',out,flush=True)
    pred=valid[KEYS+['clase_ternaria']].copy();pred['p_tabpfn']=control.p_tabpfn
    for s in seeds:pred[f'p_lgb_seed{s}']=control[f'p_seed{s}']
    timings=[]
    for s in seeds:
        mp=md/f'seed{s}.cbm';start=time.perf_counter()
        if mp.exists():model=CatBoostClassifier();model.load_model(str(mp))
        else:
            model=CatBoostClassifier(**PARAMS,random_seed=s)
            print('Iniciando semilla',s,flush=True);model.fit(tp,verbose=100)
            model.save_model(str(mp))
        assert model.feature_names_==cols and model.tree_count_==800 and model.classes_.tolist()==[0,1]
        prob=model.predict_proba(vp)[:,list(model.classes_).index(1)]
        loaded=CatBoostClassifier();loaded.load_model(str(mp))
        np.testing.assert_allclose(loaded.predict_proba(vp)[:,1],prob,rtol=0,atol=0)
        assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
        pred[f'p_cat_seed{s}']=prob;pred.to_csv(out/'predicciones_mayo.csv',index=False)
        timing=dict(seed=s,segundos=time.perf_counter()-start);timings.append(timing)
        m['semillas_completadas']=[int(c.removeprefix('p_cat_seed')) for c in pred if c.startswith('p_cat_seed')]
        m['tiempos']=timings;save(out/'manifest.json',m)
        print('Semilla',s,'completa, segundos',round(timing['segundos'],1),flush=True)
    rows=[];changes=[];partrows=[]
    perm=np.random.default_rng(214363).permutation(len(pred));fold=np.empty(len(pred),dtype=int);fold[perm]=np.arange(len(pred))%4
    pred['parte_cliente']=fold;pred.to_csv(out/'predicciones_mayo.csv',index=False)
    for s in seeds:
        ps=probabilities(pred,s);base=ps['control_entrega8']>.025
        for v,q in ps.items():
            rows.append(dict(variante=v,seed=s,**metric(yv,q)))
            for k in range(4):partrows.append(dict(variante=v,seed=s,parte=k,**metric(yv[fold==k],q[fold==k])))
            sel=q>.025;add=sel&~base;remove=base&~sel
            changes.append(dict(variante=v,seed=s,agregados=int(add.sum()),agregados_baja2=int((add&yv).sum()),
                agregados_fp=int((add&~yv).sum()),retirados=int(remove.sum()),retirados_baja2=int((remove&yv).sum()),retirados_fp=int((remove&~yv).sum())))
    individual=pd.DataFrame(rows);individual.to_csv(out/'resultados_semillas.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    pd.DataFrame(partrows).to_csv(out/'resultados_partes_mayo.csv',index=False)
    summary=individual.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean().loc[['control_entrega8']+VARIANTES]
    pivot=individual.pivot(index='seed',columns='variante',values='ganancia').loc[seeds]
    summary['delta_total']=summary.ganancia-summary.loc['control_entrega8','ganancia']
    summary['delta_25pct']=summary.delta_total/4
    summary['delta_pct']=summary.delta_total/summary.loc['control_entrega8','ganancia']*100
    summary['semillas_mejoran']=[0]+[int((pivot[v]>pivot.control_entrega8).sum()) for v in VARIANTES]
    summary.to_csv(out/'comparacion_media5.csv')
    # Una lista promediando probabilidades: separada de media cinco listas.
    meanframe=pred[KEYS+['clase_ternaria','p_tabpfn']].copy();marker=seeds[0]
    meanframe[f'p_cat_seed{marker}']=pred[[f'p_cat_seed{s}' for s in seeds]].mean(axis=1)
    meanframe[f'p_lgb_seed{marker}']=pred[[f'p_lgb_seed{s}' for s in seeds]].mean(axis=1)
    pd.DataFrame([dict(variante=v,**metric(yv,q)) for v,q in probabilities(meanframe,marker).items()]).to_csv(out/'lista_promedio5.csv',index=False)
    correlation=pd.DataFrame({v:probabilities(pred,seeds[0])[v] for v in ['control_entrega8','CatBoost_solo']}).corr()
    correlation.to_csv(out/'correlacion_scores_semilla541440.csv')
    winners=[v for v in VARIANTES if summary.loc[v,'delta_total']>0]
    m.update(estado='completo_verificado',resultados=summary.reset_index().to_dict('records'),superan_control_local=winners,
             modelos_sha256={p.name:sha(p) for p in md.glob('*.cbm')},archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},
             decision='No enviar nada al Bot. Variantes con mejora local son candidatas exploratorias; revisar mini informe por la mañana.')
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',modelos_catboost_reproducidos=5,modelos_control_reproducidos=5,
        variantes_nuevas=3,eval_set_en_fit=False,junio=False,agosto=False,creditos=0,submits=0))
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained');pos=np.arange(4)
    labels=['Control 8','CatBoost','CatBoost + Tab','Tres modelos']
    colors=['#337b9d','#cf8b38','#489671','#9a6bac']
    for ax,scale,title in [(axes[0],1e6,'Ganancia total media de cinco listas'),(axes[1],4e6,'25% de referencia local')]:
        ax.bar(pos,summary.ganancia/scale,color=colors)
        ax.axhline(summary.loc['control_entrega8','ganancia']/scale,color='#666',linestyle='--')
        ax.set(xticks=pos,xticklabels=labels,ylabel='Millones de pesos',title=title);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.tick_params(axis='x',labelrotation=18)
    fig.suptitle('Abril → mayo, 202 variables, cinco semillas, corte 2,5%')
    fig.savefig(out/'comparacion_tres_variantes.png',dpi=160);plt.close(fig)
    report=['# Mini informe: tres pruebas con CatBoost','',
        'Entrenamiento abril (163.284 clientes), evaluacion mayo (163.768). CatBoost BAJA+2, cinco semillas fijas, 202 variables. Reutilizacion de LightGBM combinado y TabPFN BAJA+2 del control de entrega8. Corte estricto2,5%. Tres pruebas calculadas a partir de los mismos cinco CatBoost; cinco fits nuevos, no quince.','',
        '| Prueba | Contactos medios | TP medios | FP medios | Ganancia total media | 25% local | Diferencia total vs control | Semillas mejores |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for v,r in summary.iterrows():report.append(f'| {v} | {r.contactos:,.1f} | {r.tp:,.1f} | {r.fp:,.1f} | ${r.ganancia:,.0f} | ${r.ganancia_25pct:,.0f} | ${r.delta_total:,.0f} | {int(r.semillas_mejoran)}/5 |')
    report+=['','Pesos fijados antes de ver resultados: CatBoostsolo; CatBoost50%+TabPFN50%; LightGBM40%+TabPFN40%+CatBoost20%. No busqueda de corte, pesos ni hiperparametros. CatBoost800arboles/profundidad6/lr0.05/L2=5,CPU4hilos,sin classweights ni earlystopping en mayo. Visa_status/Master_status/tcuentas se tratan como categorias; faltantescategoricos __MISSING__,numeric NaN.','',
        'Conclusion: '+('Superan el control local: '+', '.join(winners)+'.' if winners else 'Ninguna de las tres variantes supera el control local; no preparar submit con esta configuracion.'),
        '',m['limitaciones'],'','Las partes de mayo y cinco semillas son comprobaciones de consistencia, no nuevos meses independientes. Ver cambios de contactos para TP nuevos y FP agregados. No probar agosto ni consumir submits.','',
        'Modelos/predicciones/resultados conservados y verificados. Costo API:0creditos. Submits:0. Ganancia de lista promedio5 guardada separadamente para evitar confundir metricas.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    (out/'INFORME.md').write_text('Ver MINI_INFORME.md para resultados y limites.\n',encoding='utf-8')
    print('COMPLETO:',out,flush=True);print(summary.to_string(),flush=True)

if __name__=='__main__':main()
