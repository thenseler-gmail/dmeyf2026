"""Columna cluster categórica en LightGBM: ensemble alineado con control36 local."""
import importlib
import json
from pathlib import Path
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
seg=importlib.import_module('108_segmentos_local')
SOURCE=base.SAL/'estrategias_segmentos_20261010'
OUT=base.SAL/'cluster_columna_ensemble_20261010'
def main():
    OUT.mkdir(exist_ok=True)
    m=json.loads((base.D16/'manifest.json').read_text(encoding='utf-8'))
    lm=json.loads((base.LOCAL/'manifest.json').read_text(encoding='utf-8'))
    sr=json.loads((SOURCE/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    assert base.sha(SOURCE/'segmentador.joblib')==sr['segmentador_sha256']
    cluster=joblib.load(SOURCE/'segmentador.joblib')
    cols=m['firma']['features'];seeds=m['firma']['seeds']
    plan=dict(train=[202104],eval=202105,features_control=cols,features_candidato=cols+['segmento_cliente'],
        categorical='segmento_cliente categorías0/1/2/3',params=m['firma']['params'],rounds=273,semillas=seeds,
        pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,operador='>',api=False,creditos=0,submits=0,
        segmentador='Aprendido solo en abril, sin etiquetas, reutilizado del ensayo119',
        segmentador_sha256=sr['segmentador_sha256'],fuente_manifest_sha256=base.sha(base.D16/'manifest.json'),
        fuente_control_local_sha256=lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv'],
        criterio='Mejorar ganancia de lista promedio5 y media cinco listas individuales; sin tuning',
        codigo_sha256={f:base.sha(base.TP/f) for f in ['122_cluster_columna_ensemble.py','108_segmentos_local.py','116_promedio20_hist189.py','63_experimentos_features_local.py','features.py','baseline.py']})
    if (OUT/'PLAN.json').exists():assert json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))==plan
    else:base.save(OUT/'PLAN.json',plan)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices',api=False,creditos=0))
    mod=importlib.import_module('63_experimentos_features_local')
    _,_,train,valid,xt,xv,_=mod.cargar();xt=xt[cols];xv=xv[cols]
    assert mod.matrix_sha(xt)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert mod.matrix_sha(xv)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    def predict(frame):
        z=cluster['scaler'].transform(cluster['imputer'].transform(seg.transform(frame)))
        return cluster['cluster'].predict(np.clip(z,-5,5))
    gt=predict(train);gv=predict(valid)
    for frame,g,name in [(train,gt,'train'),(valid,gv,'mayo')]:
        stored=pd.read_csv(SOURCE/f'segmentos_{name}.csv')
        pd.testing.assert_frame_equal(stored[mod.KEYS],frame[mod.KEYS])
        np.testing.assert_array_equal(g,stored.segmento)
    dtype=pd.CategoricalDtype([0,1,2,3])
    xt['segmento_cliente']=pd.Series(gt,dtype=dtype);xv['segmento_cliente']=pd.Series(gv,dtype=dtype)
    oldpath=base.LOCAL/'historia_1_mes/predicciones_mayo.csv'
    assert base.sha(oldpath)==plan['fuente_control_local_sha256']
    old=pd.read_csv(oldpath,float_precision='round_trip')
    pd.testing.assert_frame_equal(old[mod.KEYS+['clase_ternaria']],valid[mod.KEYS+['clase_ternaria']])
    values,hashes=base.run_models(xt,xv,train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int),seeds,
        plan['params'],OUT/'modelos_mayo',OUT/'sin_reuso',{},'Cluster columna')
    general=old[[f'p_seed{s}' for s in seeds]].to_numpy()
    for i,s in enumerate(seeds):
        path=base.LOCAL/'historia_1_mes'/f'seed{s}.txt'
        assert base.sha(path)==lm['modelos_sha256'][f'historia_1_mes\\seed{s}.txt']
        np.testing.assert_allclose(lgb.Booster(model_file=str(path)).predict(xv[cols],validate_features=True,num_threads=4),general[:,i],rtol=0,atol=1e-15)
        cluster_model=lgb.Booster(model_file=str(OUT/'modelos_mayo'/f'seed{s}.txt'))
        assert cluster_model.pandas_categorical==[[0,1,2,3]]
    tab=old.p_tabpfn.to_numpy();y=old.clase_ternaria.eq('BAJA+2').to_numpy()
    control=.5*general+.5*tab[:,None];candidate=.5*values+.5*tab[:,None]
    q0=control.mean(axis=1);q1=candidate.mean(axis=1)
    a=base.metric(y,q0);b=base.metric(y,q1);assert a['ganancia_total']==275385000
    paired=[];parts=[]
    for i,s in enumerate(seeds):
        ca=base.metric(y,control[:,i]);cb=base.metric(y,candidate[:,i])
        paired.append(dict(seed=s,control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    for part in sorted(old.parte_cliente.unique()):
        ix=old.parte_cliente.to_numpy()==part;ca=base.metric(y[ix],q0[ix]);cb=base.metric(y[ix],q1[ix])
        parts.append(dict(parte=int(part),control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    p=old[mod.KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy();p['cluster']=gv
    for i,s in enumerate(seeds):p[f'p_general_seed{s}']=general[:,i];p[f'p_cluster_seed{s}']=values[:,i]
    p['score_control']=q0;p['score_cluster']=q1;p.to_csv(OUT/'predicciones_mayo.csv',index=False)
    saved=pd.read_csv(OUT/'predicciones_mayo.csv',float_precision='round_trip')
    independent=saved[[f'p_cluster_seed{s}' for s in seeds]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(independent,saved.score_cluster,rtol=0,atol=1e-15)
    assert np.array_equal(independent>.0275,saved.score_cluster.to_numpy()>.0275)
    payoff=np.where(y,1072500,-27500)
    assert int(payoff[independent>.0275].sum())==b['ganancia_total']
    delta=b['ganancia_total']-a['ganancia_total'];mean=float(np.mean([r['delta_total'] for r in paired]))
    assert sum(r['delta_total'] for r in parts)==delta
    result=dict(estado='completo_verificado',control=a,candidato=b,delta_total=delta,delta25pct=delta/4,
        media_delta_semillas=mean,semillas_mejoran=sum(r['delta_total']>0 for r in paired),
        partes_mejoran=sum(r['delta_total']>0 for r in parts),pareados=paired,partes=parts,
        supera_control_local=delta>0 and mean>0,modelos_sha256=hashes,predicciones_sha256=base.sha(OUT/'predicciones_mayo.csv'),
        api=False,creditos=0,submits=0,limitacion='Mayo y cinco semillas reutilizados; no test independiente ni garantía pública.')
    assert base.sha(base.D16/'manifest.json')==plan['fuente_manifest_sha256']
    assert base.sha(SOURCE/'segmentador.joblib')==plan['segmentador_sha256']
    base.save(OUT/'RESULTADO_LOCAL.json',result)
    base.save(OUT/'estado.json',dict(estado='completo_verificado',supera_control_local=result['supera_control_local']))
    text=f"# Columna cluster dentro del ensemble\n\nAblación alineada abril→mayo: LightGBM189 contra190 con cluster categórico; mismo target combinado,273árboles,cinco semillas,TabPFN202 guardado,pesos50/50,corte>2,75%. Cluster aprendido solo en abril, sin etiquetas; no estrategias por grupo.\n\nControl total ${a['ganancia_total']:,};25% ${a['ganancia_25pct']:,};{a['contactos']}contactos,{a['tp']}bajas. Candidato total ${b['ganancia_total']:,};25% ${b['ganancia_25pct']:,};{b['contactos']}contactos,{b['tp']}bajas. Delta total ${delta:,};25% ${delta/4:,}. Mejoran {result['semillas_mejoran']}/5 semillas y {result['partes_mejoran']}/4 partes. Delta medio listas individuales ${mean:,}. Supera puerta local:{result['supera_control_local']}.\n\nModelos recargados, categorías verificadas, cluster reproducido contra archivos119; scores reconstruidos mediante producto matricial y ganancias desde pagos por cliente. Mayo/semillas reutilizados; no test independiente ni garantía pública. Sin API/créditos/submit. Referencia36 preservada.\n"
    (OUT/'MINI_INFORME.md').write_text(text,encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Columna cluster en ensemble — 2026-10-10\n\n'+text+'\n')
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['control','candidato','delta_total','delta25pct','media_delta_semillas','semillas_mejoran','partes_mejoran','supera_control_local']},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
