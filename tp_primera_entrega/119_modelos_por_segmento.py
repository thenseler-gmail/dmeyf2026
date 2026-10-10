"""Estrategias por segmento: cuatro especialistas vs LightGBM general, ensemble fijo."""
import importlib
import json
import time
from pathlib import Path
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
seg=importlib.import_module('108_segmentos_local')
ROOT=base.ROOT;TP=base.TP;OUT=base.SAL/'estrategias_segmentos_20261010'
STRATEGIES={'general':0.,'especialistas':1.,'general50_especialista50':.5}
def main():
    OUT.mkdir(exist_ok=True)
    ref=json.loads((base.D16/'manifest.json').read_text(encoding='utf-8'))
    lm=json.loads((base.LOCAL/'manifest.json').read_text(encoding='utf-8'))
    cols=ref['firma']['features'];seeds=ref['firma']['seeds']
    plan=dict(train=[202104],eval=202105,clusters=4,cluster_sources=seg.SOURCES,
        cluster_rule='log con signo, mediana+indicadores, escala train, clip5, MiniBatchKMeans seed214363',
        estrategias=STRATEGIES,especialista='Un modelo por segmento, entrenado solo con sus clientes, por cada semilla',
        features=cols,semillas=seeds,params=ref['firma']['params'],rounds=273,
        pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,api=False,creditos=0,submits=0,
        criterios='Comparar lista promedio5 y media cinco listas; resultados por segmento diagnósticos. No elegir ganadores por segmento con las etiquetas de mayo.',
        fuente_manifest_sha256={str(p.relative_to(ROOT)):base.sha(p) for p in [base.D16/'manifest.json',base.D36/'manifest.json',base.LOCAL/'manifest.json']},
        codigo_sha256={f:base.sha(TP/f) for f in ['119_modelos_por_segmento.py','108_segmentos_local.py','116_promedio20_hist189.py','63_experimentos_features_local.py','features.py','baseline.py']})
    if (OUT/'PLAN.json').exists():assert json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))==plan
    else:base.save(OUT/'PLAN.json',plan)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices',api=False,creditos=0))
    mod=importlib.import_module('63_experimentos_features_local')
    _,_,train,valid,xt,xv,_=mod.cargar();xt=xt[cols];xv=xv[cols]
    assert mod.matrix_sha(xt)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert mod.matrix_sha(xv)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    imputer=seg.SimpleImputer(strategy='median',add_indicator=True)
    scaler=seg.StandardScaler()
    zt=np.clip(scaler.fit_transform(imputer.fit_transform(seg.transform(train))),-5,5)
    zv=np.clip(scaler.transform(imputer.transform(seg.transform(valid))),-5,5)
    cluster=seg.MiniBatchKMeans(n_clusters=4,random_state=214363,n_init=10,batch_size=4096,max_iter=100)
    gt=cluster.fit_predict(zt);gv=cluster.predict(zv)
    np.testing.assert_array_equal(gt,cluster.predict(zt))
    assert set(gt)==set(gv)=={0,1,2,3}
    joblib.dump(dict(imputer=imputer,scaler=scaler,cluster=cluster,sources=seg.SOURCES),OUT/'segmentador.joblib')
    loaded=joblib.load(OUT/'segmentador.joblib')
    np.testing.assert_array_equal(gv,loaded['cluster'].predict(np.clip(loaded['scaler'].transform(loaded['imputer'].transform(seg.transform(valid))),-5,5)))
    profile=train[seg.SOURCES].assign(segmento=gt).groupby('segmento').median()
    profile['filas_train']=pd.Series(gt).value_counts();profile['filas_mayo']=pd.Series(gv).value_counts()
    profile.to_csv(OUT/'perfil_segmentos.csv')
    train[mod.KEYS].assign(segmento=gt).to_csv(OUT/'segmentos_train.csv',index=False)
    valid[mod.KEYS].assign(segmento=gv).to_csv(OUT/'segmentos_mayo.csv',index=False)
    lp=base.LOCAL/'historia_1_mes/predicciones_mayo.csv'
    assert base.sha(lp)==lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    old=pd.read_csv(lp,float_precision='round_trip')
    pd.testing.assert_frame_equal(old[mod.KEYS+['clase_ternaria']],valid[mod.KEYS+['clase_ternaria']])
    general=old[[f'p_seed{s}' for s in seeds]].to_numpy()
    for i,s in enumerate(seeds):
        path=base.LOCAL/'historia_1_mes'/f'seed{s}.txt'
        assert base.sha(path)==lm['modelos_sha256'][f'historia_1_mes\\seed{s}.txt']
        np.testing.assert_allclose(lgb.Booster(model_file=str(path)).predict(xv,validate_features=True,num_threads=4),general[:,i],rtol=0,atol=1e-15)
    yt=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    specialists=np.full((len(valid),5),np.nan);hashes={};fitstats=[]
    folder=OUT/'modelos';folder.mkdir(exist_ok=True)
    for group in range(4):
        it=np.flatnonzero(gt==group);iv=np.flatnonzero(gv==group)
        assert len(it)>1000 and len(iv)>0 and set(yt[it])=={0,1}
        for i,s in enumerate(seeds):
            base.save(OUT/'estado.json',dict(estado='entrenando_especialistas',segmento=group,seed=s,api=False,creditos=0))
            start=time.perf_counter();path=folder/f'segmento{group}_seed{s}.txt'
            if path.exists():model=lgb.Booster(model_file=str(path))
            else:
                model=lgb.train(dict(plan['params'],seed=s),lgb.Dataset(xt.iloc[it],label=yt[it]),num_boost_round=273)
                model.save_model(str(path))
            assert model.feature_name()==cols and model.num_trees()==273
            q=model.predict(xv.iloc[iv],validate_features=True,num_threads=4)
            np.testing.assert_array_equal(q,lgb.Booster(model_file=str(path)).predict(xv.iloc[iv],validate_features=True,num_threads=4))
            specialists[iv,i]=q;hashes[str(path.relative_to(ROOT))]=base.sha(path)
            fitstats.append(dict(segmento=group,seed=s,train=len(it),eval=len(iv),segundos=time.perf_counter()-start))
            print('Especialista segmento',group,'seed',s,round(fitstats[-1]['segundos'],2),'s',flush=True)
    assert np.isfinite(specialists).all() and ((specialists>=0)&(specialists<=1)).all()
    tab=old.p_tabpfn.to_numpy();y=old.clase_ternaria.eq('BAJA+2').to_numpy()
    pred=old[mod.KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy();pred['segmento']=gv
    for i,s in enumerate(seeds):pred[f'p_general_seed{s}']=general[:,i];pred[f'p_especialista_seed{s}']=specialists[:,i]
    scores={};perseed={};summary=[];details=[];paired=[]
    for name,w in STRATEGIES.items():
        q=.5*((1-w)*general+w*specialists)+.5*tab[:,None]
        avg=q.mean(axis=1);scores[name]=avg;perseed[name]=q;pred[f'score_{name}']=avg
        metrics=[base.metric(y,q[:,i]) for i in range(5)]
        a=base.metric(y,avg)
        summary.append(dict(estrategia=name,**a,media_ganancia_semillas=float(np.mean([m['ganancia_total'] for m in metrics]))))
        for group in range(4):
            sel=gv==group
            details.append(dict(estrategia=name,segmento=group,clientes=int(sel.sum()),bajas=int(y[sel].sum()),**base.metric(y[sel],avg[sel])))
        for i,s in enumerate(seeds):paired.append(dict(estrategia=name,seed=s,**metrics[i]))
    control=summary[0];assert control['ganancia_total']==275385000
    for row in summary:
        row['delta_total']=row['ganancia_total']-control['ganancia_total'];row['delta_25pct']=row['delta_total']/4
        row['delta_media_semillas']=row['media_ganancia_semillas']-control['media_ganancia_semillas']
        row['semillas_mejoran']=sum(base.metric(y,perseed[row['estrategia']][:,i])['ganancia_total']>base.metric(y,perseed['general'][:,i])['ganancia_total'] for i in range(5))
        assert sum(d['ganancia_total'] for d in details if d['estrategia']==row['estrategia'])==row['ganancia_total']
    for d in details:
        c=next(r for r in details if r['estrategia']=='general' and r['segmento']==d['segmento'])
        d['delta_total']=d['ganancia_total']-c['ganancia_total']
    pred.to_csv(OUT/'predicciones_mayo.csv',index=False)
    pd.DataFrame(summary).to_csv(OUT/'comparacion.csv',index=False)
    pd.DataFrame(details).to_csv(OUT/'comparacion_por_segmento.csv',index=False)
    pd.DataFrame(paired).to_csv(OUT/'ganancias_semillas.csv',index=False)
    saved=pd.read_csv(OUT/'predicciones_mayo.csv',float_precision='round_trip')
    pay=np.where(y,1072500,-27500)
    for row in summary:
        name=row['estrategia'];w=STRATEGIES[name]
        a=saved[[f'p_general_seed{s}' for s in seeds]].to_numpy()
        b=saved[[f'p_especialista_seed{s}' for s in seeds]].to_numpy()
        independent=(a@np.full(5,.1*(1-w)))+(b@np.full(5,.1*w))+.5*saved.p_tabpfn.to_numpy()
        np.testing.assert_allclose(independent,saved[f'score_{name}'],rtol=0,atol=1e-15)
        assert np.array_equal(independent>.0275,saved[f'score_{name}'].to_numpy()>.0275)
        assert int(pay[independent>.0275].sum())==row['ganancia_total']
    eligible=[r['estrategia'] for r in summary[1:] if r['delta_total']>0 and r['delta_media_semillas']>0]
    result=dict(estado='completo_verificado',resumen=summary,por_segmento=details,
        supera_control_local=eligible,modelos_sha256=hashes,fitstats=fitstats,
        predicciones_sha256=base.sha(OUT/'predicciones_mayo.csv'),segmentador_sha256=base.sha(OUT/'segmentador.joblib'),
        fuentes_intactas=True,api=False,creditos=0,submits=0,
        limitacion='Mayo y cinco semillas reutilizados. No elegir retrospectivamente un ganador por segmento; umbrales y pesos por grupo requieren selección fuera de esta evaluación.')
    for p,h in plan['fuente_manifest_sha256'].items():assert base.sha(ROOT/p)==h
    base.save(OUT/'RESULTADO_LOCAL.json',result);base.save(OUT/'estado.json',dict(estado='completo_verificado',candidatos=eligible))
    text='# Estrategias por segmento\n\nLa prueba previa108 agregó una variable categórica; no evaluó especialistas ni cortes/pesos por grupo. Este ensayo entrena cuatro modelos especializados, cinco semillas cada uno, y asigna a cada cliente el modelo de su grupo. Segmentación aprendida solo en abril, sin etiquetas.\n\nControl general189 frente especialistas189, y mezcla predefinida50/50 de general/especialista dentro del componente LightGBM. TabPFN202 guardado, pesos LightGBM/Tab50/50 y corte>2,75% fijos. Abril→mayo, sin nueva API ni scoring agosto.\n\n```text\n'+pd.DataFrame(summary).to_string(index=False)+'\n```\n\nDiagnóstico por segmento:\n\n```text\n'+pd.DataFrame(details).to_string(index=False)+'\n```\n\n'
    text+=f'Candidatos que superan el control tanto en única lista promedio5 como en media de cinco listas: {eligible}.\n\n'
    text+='Mayo y semillas reutilizados; no test independiente ni garantía pública. No se optimizaron cortes ni pesos por segmento ni se eligieron modelos ganadores por segmento con mayo. El resultado no descarta todas las estrategias segmentadas. Modelos recargados y scores/ganancias reconstruidos desde archivos; fuentes y referencia36 preservadas.\n'
    (OUT/'MINI_INFORME.md').write_text(text,encoding='utf-8')
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Estrategias por segmento — 2026-10-10\n\n'+text+'\n')
    steps=TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
