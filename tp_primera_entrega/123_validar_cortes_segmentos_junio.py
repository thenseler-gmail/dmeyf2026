"""Plan1: cortes elegidos en mayo, congelados antes de comparar en junio. Sin API."""
import importlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from baseline import preparar

base=importlib.import_module('116_promedio20_hist189')
seg=importlib.import_module('108_segmentos_local')
pol=importlib.import_module('120_politicas_por_segmento')
SOURCE=base.SAL/'estrategias_segmentos_20261010'
TAB=base.SAL/'tabpfn_historicas_20261004_172322_339836'
OLDJUNE=base.SAL/'ensemble_junio_20261005_134901'
OUT=base.SAL/'cortes_segmentos_junio_20261010'
KEYS=['numero_de_cliente','foto_mes']
def freeze():
    OUT.mkdir(exist_ok=True)
    maymeta=json.loads((SOURCE/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    assert base.sha(SOURCE/'predicciones_mayo.csv')==maymeta['predicciones_sha256']
    assert base.sha(SOURCE/'segmentador.joblib')==maymeta['segmentador_sha256']
    ref=json.loads((base.D16/'manifest.json').read_text(encoding='utf-8'))
    existing=json.loads((SOURCE/'PLAN_POLITICAS.json').read_text(encoding='utf-8'))
    assert existing['cortes']==pol.CUTS
    may=pd.read_csv(SOURCE/'predicciones_mayo.csv',float_precision='round_trip')
    seeds=ref['firma']['seeds']
    q=may[[f'p_general_seed{s}' for s in seeds]].mean(axis=1).to_numpy()
    t=may.p_tabpfn.to_numpy();y=may.clase_ternaria.eq('BAJA+2').to_numpy()
    allrows=np.ones(len(may),dtype=bool)
    globalcut=pol.choose(y,q,t,allrows,'corte')
    groupcuts={str(g):pol.choose(y,q,t,may.segmento.to_numpy()==g,'corte') for g in range(4)}
    plan=dict(fecha='2026-10-10',train=[202103,202104],eval=202106,
        historia_auxiliar=[202105],target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
        columnas=ref['firma']['features'],params=ref['firma']['params'],rounds=273,semillas=seeds,
        pesos=dict(lightgbm=.5,tabpfn=.5),operador='>',
        reglas=dict(fijo=.0275,global_mayo=globalcut,segmentados_mayo=groupcuts),
        seleccion='Grilla de120 en todo mayo; desempate hacia2,75%; reglas finales congeladas antes de consultar junio',
        segmentador='119 aprendido solo en abril; números de grupo preservados',
        criterio='Segmentados supera fijo y global equivalente en lista promedio5 y media de cinco listas; revisar diferencias por grupo',
        api=False,creditos=0,submits=0,
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in [
            base.D16/'manifest.json',base.D36/'manifest.json',SOURCE/'predicciones_mayo.csv',SOURCE/'segmentador.joblib',
            SOURCE/'PLAN_POLITICAS.json',TAB/'manifest.json',TAB/'predicciones.csv',OLDJUNE/'predicciones_junio.csv']},
        codigo_sha256={f:base.sha(base.TP/f) for f in ['123_validar_cortes_segmentos_junio.py',
            '11_tabpfn_historicas.py','features.py','baseline.py','108_segmentos_local.py','116_promedio20_hist189.py','120_politicas_por_segmento.py']},
        limitacion='Junio ya expuesto y con aguinaldo; comprobación exploratoria, no test temporal independiente. Ventana distinta de abril->mayo.')
    path=OUT/'PLAN_CONGELADO.json'
    prior=OUT/'PLAN_ANTES_AJUSTE_PRECISION.json'
    if prior.exists():
        previous=json.loads(prior.read_text(encoding='utf-8'))
        assert {k:v for k,v in previous.items() if k!='codigo_sha256'}=={k:v for k,v in plan.items() if k!='codigo_sha256'}
        assert {k:v for k,v in previous['codigo_sha256'].items() if k!=Path(__file__).name}=={k:v for k,v in plan['codigo_sha256'].items() if k!=Path(__file__).name}
    if path.exists():assert json.loads(path.read_text(encoding='utf-8'))==plan
    else:base.save(path,plan)
    assert globalcut in pol.CUTS and all(c in pol.CUTS for c in groupcuts.values())
    print('REGLAS CONGELADAS',json.dumps(plan['reglas']),flush=True)
    return plan
def metric(y,q,cut):
    selected=q>cut;n=int(selected.sum());tp=int((selected&y).sum())
    gain=int(np.where(y,1072500,-27500)[selected].sum());assert gain==tp*1100000-n*27500
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia_total=gain,ganancia_25pct=gain/4)
def main():
    plan=freeze()
    base.save(OUT/'estado.json',dict(estado='verificando_fuente_tabpfn',api=False,creditos=0))
    tm=json.loads((TAB/'manifest.json').read_text(encoding='utf-8'))
    assert tm['estado']=='completo' and tm['train_meses']==[202103,202104] and tm['evaluacion_mes']==202106
    assert tm['n_estimators']==2 and tm['bloque_historico']=='ampliadas' and tm['model_version']=='v3.5-fast'
    assert tm['config_experimental']['clase_positiva']=='BAJA+2' and not tm['muestreo']
    for f,h in tm['codigo_sha256'].items():assert base.sha(base.TP/f)==h
    loader=importlib.import_module('11_tabpfn_historicas')
    _,train,valid,originals,newcols=loader.preparar_experimento(base.ROOT,tm['config_experimental'],'ampliadas','junio')
    assert originals==tm['originales'] and newcols==tm['nuevas'] and len(originals+newcols)==202
    assert len(train)==tm['filas_train']==326184 and len(valid)==tm['filas_validacion']==164114
    assert train.foto_mes.isin([202103,202104]).all() and valid.foto_mes.eq(202106).all()
    assert int(train.historial_mes_anterior_disponible.eq(0).sum())==tm['sin_historia_train']
    assert int(valid.historial_mes_anterior_disponible.eq(0).sum())==tm['sin_historia_validacion']
    tabtrain=preparar(train,originals+newcols)[0];tabvalid=preparar(valid,originals+newcols)[0]
    assert tabtrain[newcols].isna().sum().to_dict()==tm['faltantes_historicas_train']
    assert tabvalid[newcols].isna().sum().to_dict()==tm['faltantes_historicas_validacion']
    tab=pd.read_csv(TAB/'predicciones.csv',float_precision='round_trip')
    assert tab.numero_de_cliente.is_unique
    pd.testing.assert_frame_equal(tab[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    old=pd.read_csv(OLDJUNE/'predicciones_junio.csv',float_precision='round_trip')
    # A second historical artifact carries the same predictions and evaluation universe.
    pd.testing.assert_frame_equal(old[KEYS+['clase_ternaria']],tab[KEYS+['clase_ternaria']])
    historical_diff=float(np.max(np.abs(old.p_tabpfn.to_numpy()-tab.p_historicas.to_numpy())))
    # The older ensemble read the original CSV using pandas' default parser,
    # losing decimal digits when serializing its copy. Do not alter original q.
    np.testing.assert_allclose(old.p_tabpfn,tab.p_historicas,rtol=0,atol=1e-15)
    assert np.array_equal(old.p_tabpfn.to_numpy()>.025,tab.p_historicas.to_numpy()>.025)
    tabq=tab.p_historicas.to_numpy();y=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    assert np.isfinite(tabq).all() and ((tabq>=0)&(tabq<=1)).all()
    tabmetric=metric(y,tabq,.025)
    for key in ['contactos','tp','fp']:assert tabmetric[key]==tm['resultados']['historicas'][key]
    assert tabmetric['ganancia_total']==tm['resultados']['historicas']['ganancia']==380792500
    xt=tabtrain[plan['columnas']];xv=tabvalid[plan['columnas']]
    matrixinfo=dict(train=importlib.import_module('63_experimentos_features_local').matrix_sha(xt),
                    junio=importlib.import_module('63_experimentos_features_local').matrix_sha(xv))
    cluster=joblib.load(SOURCE/'segmentador.joblib')
    assert cluster['sources']==seg.SOURCES
    z=cluster['scaler'].transform(cluster['imputer'].transform(seg.transform(valid)))
    groups=cluster['cluster'].predict(np.clip(z,-5,5))
    assert set(groups)=={0,1,2,3}
    valid[KEYS].assign(segmento=groups).to_csv(OUT/'segmentos_junio.csv',index=False)
    base.save(OUT/'estado.json',dict(estado='entrenando_control_junio',semillas=plan['semillas'],api=False,creditos=0))
    values,hashes=base.run_models(xt,xv,train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int),
        plan['semillas'],plan['params'],OUT/'modelos',OUT/'sin_reuso',{},'Control189 junio')
    scores=.5*values+.5*tabq[:,None];avg=scores.mean(axis=1)
    cuts={'fijo':np.full(len(valid),plan['reglas']['fijo']),
          'global_mayo':np.full(len(valid),plan['reglas']['global_mayo']),
          'segmentados_mayo':np.array([plan['reglas']['segmentados_mayo'][str(g)] for g in groups])}
    pred=valid[KEYS+['clase_ternaria']].copy();pred['segmento']=groups;pred['p_tabpfn']=tabq
    for i,s in enumerate(plan['semillas']):pred[f'p_lgb_seed{s}']=values[:,i]
    pred['score_promedio5']=avg
    summary=[];paired=[];details=[]
    for name,cut in cuts.items():
        pred[f'corte_{name}']=cut;pred[f'seleccion_{name}']=avg>cut
        individual=[]
        for i,s in enumerate(plan['semillas']):
            row=dict(politica=name,seed=s,**metric(y,scores[:,i],cut))
            paired.append(row);individual.append(row['ganancia_total'])
        row=dict(politica=name,**metric(y,avg,cut),media_ganancia_semillas=float(np.mean(individual)))
        summary.append(row)
        for g in range(4):
            ix=groups==g
            details.append(dict(politica=name,segmento=g,clientes=int(ix.sum()),bajas=int(y[ix].sum()),corte=float(cut[ix][0]),**metric(y[ix],avg[ix],cut[ix])))
        assert sum(r['ganancia_total'] for r in details if r['politica']==name)==row['ganancia_total']
    fixed=summary[0];globalrow=summary[1]
    for row in summary:
        row['delta_vs_fijo']=row['ganancia_total']-fixed['ganancia_total'];row['delta_vs_fijo25pct']=row['delta_vs_fijo']/4
        row['delta_vs_global']=row['ganancia_total']-globalrow['ganancia_total']
        row['delta_media_vs_fijo']=row['media_ganancia_semillas']-fixed['media_ganancia_semillas']
        row['delta_media_vs_global']=row['media_ganancia_semillas']-globalrow['media_ganancia_semillas']
        def gain(name,s):return next(r['ganancia_total'] for r in paired if r['politica']==name and r['seed']==s)
        row['semillas_mejoran_fijo']=sum(gain(row['politica'],s)>gain('fijo',s) for s in plan['semillas'])
        row['semillas_mejoran_global']=sum(gain(row['politica'],s)>gain('global_mayo',s) for s in plan['semillas'])
    for row in details:
        same=lambda name:next(r for r in details if r['politica']==name and r['segmento']==row['segmento'])
        row['delta_vs_fijo']=row['ganancia_total']-same('fijo')['ganancia_total']
        row['delta_vs_global']=row['ganancia_total']-same('global_mayo')['ganancia_total']
    pred.to_csv(OUT/'predicciones_junio.csv',index=False)
    pd.DataFrame(summary).to_csv(OUT/'comparacion.csv',index=False)
    pd.DataFrame(paired).to_csv(OUT/'ganancias_semillas.csv',index=False)
    pd.DataFrame(details).to_csv(OUT/'comparacion_por_segmento.csv',index=False)
    saved=pd.read_csv(OUT/'predicciones_junio.csv',float_precision='round_trip')
    reconstructed=saved[[f'p_lgb_seed{s}' for s in plan['semillas']]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(reconstructed,saved.score_promedio5,rtol=0,atol=1e-15)
    for row in summary:
        name=row['politica'];cut=saved[f'corte_{name}'].to_numpy()
        assert np.array_equal(reconstructed>cut,saved[f'seleccion_{name}'].to_numpy())
        check=metric(y,reconstructed,cut)
        assert all(row[k]==v for k,v in check.items())
    candidate=summary[2]
    passes=all(candidate[key]>0 for key in ['delta_vs_fijo','delta_vs_global','delta_media_vs_fijo','delta_media_vs_global'])
    decision='Supera comparaciones de junio; revisar evidencia global antes de promoción' if passes else 'Cerrar rama actual: cortes segmentados no superan ambos controles y métricas'
    for path,h in plan['fuentes_sha256'].items():assert base.sha(base.ROOT/path)==h
    result=dict(estado='completo_verificado',reglas_congeladas=plan['reglas'],resumen=summary,por_segmento=details,
        supera_puerta_junio=passes,decision=decision,matrices_sha256=matrixinfo,modelos_sha256=hashes,
        predicciones_sha256=base.sha(OUT/'predicciones_junio.csv'),api=False,creditos=0,submits=0,
        verificacion_tabpfn=dict(estado='verificado',historico_sin_hash_csv_en_manifest=True,
            checksum_actual_congelado=plan['fuentes_sha256'][str((TAB/'predicciones.csv').relative_to(base.ROOT))],
            copia_historica_coincide_a_precision_csv=True,max_diferencia_copia_historica=historical_diff,
            filas=len(tab),metrica_historica_coincide=True),
        limitacion=plan['limitacion'])
    base.save(OUT/'RESULTADO.json',result);base.save(OUT/'verificacion_independiente.json',result)
    base.save(OUT/'estado.json',dict(estado='completo_verificado',decision=decision,api=False,creditos=0))
    text='# Cortes por segmento: comprobación congelada en junio\n\nReglas elegidas únicamente con mayo antes de leer resultados de junio:\n\n```json\n'+json.dumps(plan['reglas'],ensure_ascii=False,indent=2)+'\n```\n\n'
    text+='LightGBM189 marzo+abril→junio,cinco semillas,273árboles,parámetros16; TabPFN202 BAJA+2 de la misma ventana,guardado,50/50. Mismas probabilidades para todos los brazos. Cluster119 aprendido en abril se conserva; mayo solo aporta historia al entrenamiento, sus etiquetas eligieron las reglas.\n\n```text\n'+pd.DataFrame(summary).to_string(index=False)+'\n```\n\n'
    text+=decision+'.\n\nDiagnóstico por segmento:\n\n```text\n'+pd.DataFrame(details).to_string(index=False)+'\n```\n\n'
    text+='Junio ya expuesto y con aguinaldo; no test independiente ni garantía pública. No ajustar reglas con junio ni producir un nuevo CSV del Bot en esta comprobación. TabPFN: manifest,ventana,features,claves,labels,nulos y ganancia histórica comprobados; su CSV no tenía hash histórico en el manifest, por lo que se congeló checksum actual y se contrastó con una segunda copia histórica. Modelos recargados,scores reconstruidos por producto matricial,selecciones y pagos verificados; fuentes intactas. Sin API ni créditos. Referencia36 preservada.\n'
    (OUT/'MINI_INFORME.md').write_text(text,encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Paso1: cortes segmentados en junio — 2026-10-10\n\n'+text+'\n')
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True);print(decision,flush=True)
if __name__=='__main__':main()
