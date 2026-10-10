"""Paso2: comprobar servicios en junio solo si superan el control en mayo."""
import importlib
import json
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_vinculos import FUENTES,KEYS,agregar_vinculos,verificar_independiente

base=importlib.import_module('116_promedio20_hist189')
pilot=importlib.import_module('124_servicios_recurrentes_local')
OUT=pilot.OUT
JUNE=base.SAL/'cortes_segmentos_junio_20261010'
TAB=base.SAL/'tabpfn_historicas_20261004_172322_339836'
def record(text):
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Paso2: servicios separados — 2026-10-10\n\n'+text+'\n')
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    plan=base.TP/'PLAN_EXPERIMENTOS_20261010.md'
    with plan.open('a',encoding='utf-8') as f:f.write('\n## Resultado paso2 — 2026-10-10\n\n'+text+'\n')
def main():
    may=json.loads((OUT/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    assert may['estado']=='completo_verificado'
    assert base.sha(OUT/'predicciones_mayo.csv')==may['predicciones_sha256']
    for path,h in may['modelos_sha256'].items():assert base.sha(base.ROOT/path)==h
    if not may['supera_control_local']:
        base.save(OUT/'estado.json',dict(estado='completo_verificado_no_promovido',junio_ejecutado=False,api=False,creditos=0))
        text=f"# Paso2 completado: cuatro señales de débitos/pagos\n\nAbril→mayo, LightGBM189→193, cinco semillas,273árboles,mezcla50/50 con TabPFN202 guardado,corte>2,75%. Control total ${may['control']['ganancia_total']:,};25% ${may['control']['ganancia_25pct']:,}. Candidato total ${may['candidato']['ganancia_total']:,};25% ${may['candidato']['ganancia_25pct']:,}. Delta total ${may['delta_total']:,};25% ${may['delta_25pct']:,};delta medio listas individuales ${may['media_delta_semillas']:,}. Mejoran {may['semillas_mejoran']}/5semillas y {may['partes_mejoran']}/4partes.\n\nNo supera la puerta de mayo: no ejecutar junio, no entrenamiento final ni nueva entrega. Rama cerrada para este bloque. Cinco fits locales nuevos, cero API/créditos/submits. Mayo reutilizado; no prueba independiente. Referencia36 preservada. Siguiente pendiente del plan: auditoría de calidad/drift, no ejecutada por este encargo.\n"
        (OUT/'CONCLUSION.md').write_text(text,encoding='utf-8');record(text)
        print('Paso2 completo; no supera mayo, no se ejecuta junio.',flush=True)
        return
    original=json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))
    previous=json.loads((JUNE/'RESULTADO.json').read_text(encoding='utf-8'))
    juneplan=dict(train=[202103,202104],eval=202106,features=original['features_candidato'],
        params=original['params'],semillas=original['semillas'],rounds=273,pesos=original['pesos'],umbral=.0275,
        fuente_mayo_sha256=base.sha(OUT/'RESULTADO_LOCAL.json'),fuente_control_sha256=base.sha(JUNE/'RESULTADO.json'),
        fuente_predicciones_control_sha256=previous['predicciones_sha256'],fuente_tab_manifest_sha256=base.sha(TAB/'manifest.json'),
        codigo_sha256={f:base.sha(base.TP/f) for f in ['125_comprobar_servicios_junio.py','124_servicios_recurrentes_local.py','features_vinculos.py']},
        api=False,creditos=0,submits=0,regla='No ajustar variables/params/pesos/corte usando junio')
    path=OUT/'PLAN_JUNIO.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf-8'))==juneplan
    else:base.save(path,juneplan)
    base.save(OUT/'estado.json',dict(estado='comprobacion_junio',api=False,creditos=0))
    print('Supera mayo; comienza comprobacion congelada en junio',flush=True)
    tm=json.loads((TAB/'manifest.json').read_text(encoding='utf-8'))
    assert tm['train_meses']==juneplan['train'] and tm['evaluacion_mes']==202106
    loader=importlib.import_module('11_tabpfn_historicas')
    _,train,valid,originals,news=loader.preparar_experimento(base.ROOT,tm['config_experimental'],'ampliadas','junio')
    cols=original['features_control'];xt=preparar(train,cols)[0];xv=preparar(valid,cols)[0]
    mod=importlib.import_module('63_experimentos_features_local')
    assert mod.matrix_sha(xt)==previous['matrices_sha256']['train']
    assert mod.matrix_sha(xv)==previous['matrices_sha256']['junio']
    cp=JUNE/'predicciones_junio.csv';assert base.sha(cp)==previous['predicciones_sha256']
    control=pd.read_csv(cp,float_precision='round_trip')
    pd.testing.assert_frame_equal(control[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    config=tm['config_experimental']
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes IN (202103,202104,202105,202106) ORDER BY foto_mes,numero_de_cliente').df()
    features=agregar_vinculos(history);audit=verificar_independiente(history,features)
    for frame,x in [(train,xt),(valid,xv)]:
        joined=frame[KEYS].merge(features,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(joined[KEYS],frame[KEYS])
        for c in pilot.FEATURES:x[c]=joined[c].to_numpy()
    assert list(xt)==list(xv)==juneplan['features'] and len(xv.columns)==193
    seeds=juneplan['semillas']
    for s in seeds:
        modelpath=JUNE/'modelos'/f'seed{s}.txt'
        assert base.sha(modelpath)==previous['modelos_sha256'][str(modelpath.relative_to(base.ROOT))]
        np.testing.assert_allclose(lgb.Booster(model_file=str(modelpath)).predict(xv[cols],validate_features=True,num_threads=4),control[f'p_lgb_seed{s}'],rtol=0,atol=1e-15)
    values,hashes=base.run_models(xt,xv,train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int),seeds,
        juneplan['params'],OUT/'modelos_junio',OUT/'sin_reuso',{},'Servicios junio')
    y=valid.clase_ternaria.eq('BAJA+2').to_numpy();tab=control.p_tabpfn.to_numpy()
    qs=.5*values+.5*tab[:,None];old=.5*control[[f'p_lgb_seed{s}' for s in seeds]].to_numpy()+.5*tab[:,None]
    a=base.metric(y,old.mean(axis=1));b=base.metric(y,qs.mean(axis=1));assert a['ganancia_total']==418330000
    paired=[]
    for i,s in enumerate(seeds):
        ca=base.metric(y,old[:,i]);cb=base.metric(y,qs[:,i])
        paired.append(dict(seed=s,control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    pred=control[KEYS+['clase_ternaria','p_tabpfn']].copy()
    for i,s in enumerate(seeds):pred[f'p_control_seed{s}']=control[f'p_lgb_seed{s}'];pred[f'p_servicios_seed{s}']=values[:,i]
    pred['score_control']=old.mean(axis=1);pred['score_servicios']=qs.mean(axis=1)
    pred.to_csv(OUT/'predicciones_junio.csv',index=False)
    saved=pd.read_csv(OUT/'predicciones_junio.csv',float_precision='round_trip')
    independent=saved[[f'p_servicios_seed{s}' for s in seeds]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(independent,saved.score_servicios,rtol=0,atol=1e-15)
    assert base.metric(y,independent)==b
    delta=b['ganancia_total']-a['ganancia_total'];mean=float(np.mean([r['delta_total'] for r in paired]))
    passes=delta>0 and mean>0
    result=dict(estado='completo_verificado',control=a,candidato=b,delta_total=delta,delta_25pct=delta/4,
        media_delta_semillas=mean,pareados=paired,semillas_mejoran=sum(r['delta_total']>0 for r in paired),
        supera_control_junio=passes,modelos_sha256=hashes,predicciones_sha256=base.sha(OUT/'predicciones_junio.csv'),
        verificacion_features=audit,api=False,creditos=0,submits=0,limitacion='Junio ya expuesto; comprobación exploratoria, no test independiente')
    base.save(OUT/'RESULTADO_JUNIO.json',result)
    base.save(OUT/'estado.json',dict(estado='completo_verificado',supera_ambos_meses=passes,api=False,creditos=0))
    decision='Candidata supera puertas locales; entrenamiento final aún no ejecutado' if passes else 'No se sostiene en junio; cerrar rama, sin nueva entrega'
    text=f"# Paso2: servicios separados, comprobación temporal\n\nMayo delta total ${may['delta_total']:,};25% ${may['delta_25pct']:,}. Junio control total ${a['ganancia_total']:,};25% ${a['ganancia_25pct']:,};candidato total ${b['ganancia_total']:,};25% ${b['ganancia_25pct']:,};delta total ${delta:,};25% ${delta/4:,}. Delta medio de cinco listas en junio ${mean:,};mejoran {result['semillas_mejoran']}/5 semillas.\n\n{decision}. Sin API/créditos/submits. Cinco fits nuevos en mayo y cinco en junio; control junio reutilizado. Mismos parámetros/semillas/pesos/corte, reglas de señales congeladas; mayo y junio reutilizados, no tests independientes. Referencia36 preservada.\n"
    (OUT/'CONCLUSION.md').write_text(text,encoding='utf-8');record(text)
    print(json.dumps({k:result[k] for k in ['control','candidato','delta_total','delta_25pct','media_delta_semillas','semillas_mejoran','supera_control_junio']},ensure_ascii=False,indent=2),flush=True)
    print(decision,flush=True)
if __name__=='__main__':main()
