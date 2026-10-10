"""LightGBM189/193, abril->mayo, cinco semillas, Tab202 guardado, corte2,75%."""
import importlib
import json
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_vinculos import FEATURES,FUENTES,KEYS,agregar_vinculos,verificar_independiente,verificar_ejemplos

FEATURES=['vinculos_perdida_debitos','vinculos_perdida_pagos',
          'vinculos_servicios_recurrentes','vinculos_delta_servicios_recurrentes']

base=importlib.import_module('116_promedio20_hist189')
TP=base.TP;ROOT=base.ROOT;OUT=base.SAL/'servicios_recurrentes_20261010'
def main():
    OUT.mkdir(exist_ok=True)
    ref=json.loads((base.D16/'manifest.json').read_text(encoding='utf-8'))
    lm=json.loads((base.LOCAL/'manifest.json').read_text(encoding='utf-8'))
    seeds=ref['firma']['seeds'];cols=ref['firma']['features']
    sources=[base.D16/'manifest.json',base.D36/'manifest.json',base.LOCAL/'manifest.json']
    plan=dict(fecha='2026-10-10',train=[202104],eval=202105,features_control=cols,features_candidato=cols+FEATURES,
        fuentes_vinculos=FUENTES,semillas=seeds,params=ref['firma']['params'],rounds=273,
        pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,operador='>',
        politica='Misma configuración16 sin correcciones adicionales; única diferencia cuatro señales de debitos/pagos nuevas',
        promocion='Ganancia única lista promedio5 y media cinco listas superiores al control; sin tuning',
        api=False,creditos=0,submits=0,fuentes_sha256={str(p.relative_to(ROOT)):base.sha(p) for p in sources},
        codigo_sha256={f:base.sha(TP/f) for f in ['124_servicios_recurrentes_local.py','features_vinculos.py','116_promedio20_hist189.py','63_experimentos_features_local.py','baseline.py','features.py']})
    if (OUT/'PLAN.json').exists():assert json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))==plan
    else:base.save(OUT/'PLAN.json',plan)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices',api=False,creditos=0))
    checks=verificar_ejemplos();print('Ejemplos calendario/nulos verificados',flush=True)
    mod=importlib.import_module('63_experimentos_features_local')
    _,_,train,valid,xt,xv,_=mod.cargar();xt=xt[cols];xv=xv[cols]
    assert mod.matrix_sha(xt)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert mod.matrix_sha(xv)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    config=json.loads((TP/'config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    new=agregar_vinculos(history);audit=verificar_independiente(history,new)
    for frame,x in [(train,xt),(valid,xv)]:
        joined=frame[KEYS].merge(new,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(joined[KEYS],frame[KEYS])
        for c in FEATURES:x[c]=joined[c].to_numpy()
    assert len(xt.columns)==193 and len(xv.columns)==193
    xt.iloc[:,189:].describe().to_csv(OUT/'descripcion_features_train.csv')
    xv.iloc[:,189:].isna().mean().rename('fraccion_nulos').to_csv(OUT/'nulos_features_mayo.csv')
    lp=base.LOCAL/'historia_1_mes/predicciones_mayo.csv'
    assert base.sha(lp)==lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    old=pd.read_csv(lp,float_precision='round_trip')
    pd.testing.assert_frame_equal(old[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    # Reload all five control models against identical 189-column matrices.
    control=[]
    for s in seeds:
        path=base.LOCAL/'historia_1_mes'/f'seed{s}.txt'
        assert base.sha(path)==lm['modelos_sha256'][f'historia_1_mes\\seed{s}.txt']
        q=lgb.Booster(model_file=str(path)).predict(xv[cols],validate_features=True,num_threads=4)
        np.testing.assert_allclose(q,old[f'p_seed{s}'],rtol=0,atol=1e-15);control.append(q)
    base.save(OUT/'estado.json',dict(estado='entrenando',semillas=seeds,api=False,creditos=0))
    values,hashes=base.run_models(xt,xv,train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int),seeds,plan['params'],OUT/'modelos_mayo',OUT/'sin_reuso',{},'Servicios mayo')
    control=np.column_stack(control);tab=old.p_tabpfn.to_numpy();y=old.clase_ternaria.eq('BAJA+2').to_numpy()
    qs0=.5*control+.5*tab[:,None];qs1=.5*values+.5*tab[:,None]
    q0=qs0.mean(axis=1);q1=qs1.mean(axis=1)
    a=base.metric(y,q0);b=base.metric(y,q1);assert a['ganancia_total']==275385000
    paired=[]
    for i,s in enumerate(seeds):
        ca=base.metric(y,qs0[:,i]);cb=base.metric(y,qs1[:,i])
        paired.append(dict(seed=s,control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    parts=[]
    for part in sorted(old.parte_cliente.unique()):
        ix=old.parte_cliente.to_numpy()==part;ca=base.metric(y[ix],q0[ix]);cb=base.metric(y[ix],q1[ix])
        parts.append(dict(parte=int(part),control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    pred=old[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy()
    for i,s in enumerate(seeds):pred[f'p_control_seed{s}']=control[:,i];pred[f'p_vinculos_seed{s}']=values[:,i]
    pred['score_control']=q0;pred['score_vinculos']=q1;pred.to_csv(OUT/'predicciones_mayo.csv',index=False)
    reread=pd.read_csv(OUT/'predicciones_mayo.csv',float_precision='round_trip')
    independent=reread[[f'p_vinculos_seed{s}' for s in seeds]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(independent,reread.score_vinculos,rtol=0,atol=1e-15)
    assert base.metric(y,independent)==b
    delta=b['ganancia_total']-a['ganancia_total'];meandelta=float(np.mean([r['delta_total'] for r in paired]))
    assert sum(r['delta_total'] for r in parts)==delta
    promote=delta>0 and meandelta>0
    result=dict(estado='completo_verificado',control=a,candidato=b,delta_total=delta,delta_25pct=delta/4,
        media_delta_semillas=meandelta,semillas_mejoran=sum(r['delta_total']>0 for r in paired),
        partes_mejoran=sum(r['delta_total']>0 for r in parts),pareados=paired,partes=parts,
        supera_control_local=promote,modelos_sha256=hashes,predicciones_sha256=base.sha(OUT/'predicciones_mayo.csv'),
        matrices=dict(train=mod.matrix_sha(xt),mayo=mod.matrix_sha(xv)),verificacion_features=audit,checks=checks,
        api=False,creditos=0,submits=0,limitacion='Mayo/semillas reutilizados; no test independiente ni garantía pública')
    base.save(OUT/'RESULTADO_LOCAL.json',result);base.save(OUT/'estado.json',dict(estado='completo_verificado',supera_control_local=promote))
    note=f"# Vínculos recurrentes: piloto verificado\n\nCuatro señales de debitos/pagos, 189→193 variables; resto configuración16 congelado. Abril→mayo, cinco semillas, TabPFN202 guardado,50/50,corte>2,75%.\n\nControl promedio5 total ${a['ganancia_total']:,};25% ${a['ganancia_25pct']:,};{a['contactos']} contactos,{a['tp']} bajas. Candidato total ${b['ganancia_total']:,};25% ${b['ganancia_25pct']:,};{b['contactos']} contactos,{b['tp']} bajas. Delta total ${delta:,};25% ${delta/4:,}.\n\nMejoran {result['semillas_mejoran']}/5 semillas y {result['partes_mejoran']}/4 partes; delta medio listas individuales ${meandelta:,}. Supera puerta local: {promote}.\n\nMes calendario, nulos desconocidos, ausencia requiere todas las fuentes en cero, positivos parciales establecen presencia. Préstamos pueden cancelarse normalmente. Features reconstruidas por lookup independiente y toy de huecos/año/nulos/negativos; modelos recargados y ganancias reproducidas. Mayo y semillas reutilizados; no test independiente ni garantía pública. Sin API/créditos/submit. Referencia pública36 preservada.\n"
    (OUT/'MINI_INFORME.md').write_text(note,encoding='utf-8')
    for p,h in plan['fuentes_sha256'].items():assert base.sha(ROOT/p)==h
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Vínculos recurrentes — 2026-10-10\n\n'+note+'\n')
    steps=TP/'NEXT_STEPS_IDEAS.md';steps.write_text(note+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['control','candidato','delta_total','delta_25pct','semillas_mejoran','partes_mejoran','media_delta_semillas','supera_control_local']},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
    main()
    importlib.import_module('125_comprobar_servicios_junio').main()
