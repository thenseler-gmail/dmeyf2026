"""Combina189 columnas con tres rangos mensuales; cinco fits locales fijos."""
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas'
SOURCE=SAL/'features_local_20261006_140702'
RANKS=['mpayroll','mcuentas_saldo','mrentabilidad']
SEEDS=[541440,408476,741961,248865,717444];KEYS=['numero_de_cliente','foto_mes']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(x):return '$'+f'{x:,.0f}'.replace(',','.')

def main():
    fm=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'));assert fm['estado']=='completo_verificado'
    for f,h in fm['archivos_sha256'].items():assert sha(SOURCE/f)==h
    ref,seeds,train,valid,xt,xv,old=importlib.import_module('63_experimentos_features_local').cargar()
    assert seeds==SEEDS
    cols=fm['firma']['variants']['historia_1_mes']['features'];assert len(cols)==189
    xt=xt[cols].copy();xv=xv[cols].copy()
    # Cada mes por separado, poblacion completa, sin etiquetas. Nulos preservados.
    for frame in [xt,xv]:
        for c in RANKS:
            values=frame[c].to_numpy();mask=~np.isnan(values)
            independent=np.full(len(values),np.nan)
            independent[mask]=rankdata(values[mask],method='average')/mask.sum()
            rank=frame[c].rank(method='average',pct=True,na_option='keep')
            np.testing.assert_allclose(rank,independent,rtol=0,atol=0,equal_nan=True)
            frame['rango_mensual_'+c]=rank
    assert xt.columns.tolist()==xv.columns.tolist() and len(xt.columns)==192
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    yv=valid.clase_ternaria.eq('BAJA+2').to_numpy();assert yv.sum()==870
    control=pd.read_csv(SOURCE/'historia_1_mes/predicciones_mayo.csv')
    ranked205=pd.read_csv(SOURCE/'rangos_mensuales/predicciones_mayo.csv')
    for frame in [control,ranked205]:pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],frame[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(control.p_tabpfn,ranked205.p_tabpfn,rtol=0,atol=1e-15)
    params=ref['elegido']['params'];assert ref['elegido']['num_boost_round']==273
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('hist192_rangos_%Y%m%d_%H%M%S');out.mkdir();md=out/'modelos';md.mkdir()
    m=dict(estado='entrenando',train=[202104],evaluacion=202105,historia_auxiliar=[202103],semillas=SEEDS,
        features_lightgbm=xt.columns.tolist(),features_tabpfn=202,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
        nuevas_columnas=['rango_mensual_'+c for c in RANKS],regla_rangos='Cada mes completo por separado, rank average/pct, nulos preservados, ceros y negativos incluidos.',
        params=params,num_boost_round=273,pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.025,operador='>',fit_eval_set=False,
        train_matrix_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        valid_matrix_sha256=hashlib.sha256(xv.to_numpy(dtype=np.float32).tobytes()).hexdigest(),target_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [SOURCE/'manifest.json',SOURCE/'historia_1_mes/predicciones_mayo.csv',SOURCE/'rangos_mensuales/predicciones_mayo.csv']},
        codigo_sha256=sha(Path(__file__)),nuevos_fits=5,api=False,creditos=0,submits=0,
        limitacion='Mayo y semillas reutilizados; no test independiente ni garantia publica. Rangos usan poblacion mensual sin etiquetas. '
        'Agregar columnas tambien cambia el muestreo de features; mejora no demuestra causalidad. Junio/agosto no leidos; sin tuning ni nuevo corte.')
    save(out/'manifest.json',m);print('Salida:',out,flush=True)
    pred=control[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy();rows=[];parts=[];changes=[]
    def metric(q,area=None):
        sel=np.asarray(q)>.025
        if area is not None:sel=sel&area
        n=int(sel.sum());hits=int((sel&yv).sum());g=hits*1100000-n*27500
        assert g==int(np.where(yv,1072500,-27500)[sel].sum())
        return dict(contactos=n,tp=hits,fp=n-hits,ganancia=g,ganancia_25pct=g/4)
    for seed in SEEDS:
        model=lgb.train(dict(params,seed=seed),lgb.Dataset(xt,label=y),num_boost_round=273)
        path=md/f'seed{seed}.txt';model.save_model(str(path));q=model.predict(xv,validate_features=True)
        reload=lgb.Booster(model_file=str(path));assert reload.feature_name()==list(xt) and reload.num_trees()==273
        np.testing.assert_allclose(q,reload.predict(xv,validate_features=True),rtol=0,atol=0)
        pred[f'p_lgb192_seed{seed}']=q
        scores=dict(control16_189=(control[f'p_seed{seed}']+control.p_tabpfn)/2,
            rangos205_previo=(ranked205[f'p_seed{seed}']+control.p_tabpfn)/2,
            historia_rangos192=(q+control.p_tabpfn)/2)
        baseline=np.asarray(scores['control16_189'])>.025
        for name,score in scores.items():
            assert np.isfinite(score).all() and np.asarray(score).min()>=0 and np.asarray(score).max()<=1
            pred[f'score_{name}_seed{seed}']=score
            rows.append(dict(variante=name,seed=seed,**metric(score)))
            for k in range(4):parts.append(dict(variante=name,seed=seed,parte=k,**metric(score,pred.parte_cliente.eq(k).to_numpy())))
            sel=np.asarray(score)>.025;add=sel&~baseline;remove=baseline&~sel
            changes.append(dict(variante=name,seed=seed,agregados=int(add.sum()),retirados=int(remove.sum()),agregados_baja2=int((add&yv).sum()),retirados_baja2=int((remove&yv).sum())))
        pred.to_csv(out/'predicciones_mayo.csv',index=False);print('Semilla',seed,'completa',flush=True)
    r=pd.DataFrame(rows);pr=pd.DataFrame(parts)
    summary=r.groupby('variante')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    assert summary.loc['control16_189','ganancia']==266420000 and summary.loc['rangos205_previo','ganancia']==263549000
    pivot=r.pivot(index='seed',columns='variante',values='ganancia');group=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['delta_vs16_total']=summary.ganancia-266420000;summary['delta_vs16_25pct']=summary.delta_vs16_total/4
    summary['semillas_mejoran_vs16']=[int((pivot[v]>pivot.control16_189).sum()) for v in summary.index]
    summary['partes_mejoran_vs16']=[int((group[v]>group.control16_189).sum()) for v in summary.index]
    r.to_csv(out/'resultados_semillas.csv',index=False);pr.to_csv(out/'resultados_partes.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False);summary.to_csv(out/'comparacion_media5.csv')
    # Verificar selecciones leyendo de disco y recombinando las dos columnas por producto matricial.
    disk=pd.read_csv(out/'predicciones_mayo.csv')
    for seed in SEEDS:
        q=np.column_stack([disk[f'p_lgb192_seed{seed}'],disk.p_tabpfn])@np.array([.5,.5])
        np.testing.assert_array_equal(q>.025,disk[f'score_historia_rangos192_seed{seed}']>.025)
        assert metric(q)['ganancia']==r[(r.variante=='historia_rangos192')&(r.seed==seed)].ganancia.iloc[0]
    avg=(pred[[f'p_lgb192_seed{s}' for s in SEEDS]].mean(axis=1)+pred.p_tabpfn)/2
    pd.DataFrame([dict(variante='historia_rangos192_promedio5',**metric(avg))]).to_csv(out/'lista_promedio5.csv',index=False)
    row=summary.loc['historia_rangos192']
    m.update(estado='completo_verificado',resultados=summary.reset_index().to_dict('records'),supera16_local=bool(row.ganancia>266420000),
        modelos_sha256={f.name:sha(f) for f in md.glob('*.txt')},archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')})
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',rangos_recalculados_scipy_por_mes=True,modelos_reproducidos=5,
        control16_reproducido=True,rangos205_reproducido=True,selecciones_producto_matricial=True,ganancias_verificadas=15,api=False))
    report=['# Historia189 más tres rangos mensuales: LightGBM192','',
        'Abril → mayo, mismas cinco semillas y273 árboles, target combinado, TabPFN202 BAJA+2 guardado, mezcla50/50 y corte >2,5%. '
        'Solo se agregan rangos de mpayroll, mcuentas_saldo y mrentabilidad.','',
        '| Variante | Total medio | 25% | Delta total vs16 | 25% del delta | Semillas mejores | Partes mejores |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,v in summary.iterrows():report.append(f'| {name} | {money(v.ganancia)} | {money(v.ganancia_25pct)} | {money(v.delta_vs16_total)} | {money(v.delta_vs16_25pct)} | {int(v.semillas_mejoran_vs16)}/5 | {int(v.partes_mejoran_vs16)}/4 |')
    report+=['',m['regla_rangos'],'',m['limitacion'],'',
        'Rangos recalculados por scipy.rankdata para auditar pandas.rank. Predicciones de cinco modelos recargados iguales; control16 y prueba205 previos reproducidos. '
        'Métrica principal media de cinco listas; lista promedio guardada aparte. No entrenamiento final ni CSVBot nuevo en este ensayo. Cero créditos.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'));c['hist192_rangos_local']={**m,'carpeta':str(out.relative_to(ROOT))};save(cfg,c)
    note=(f'**LightGBM192 historia+rango completo:** total medio {money(row.ganancia)},25% {money(row.ganancia_25pct)}; '
        f'delta frente16 {money(row.delta_vs16_total)},25% {money(row.delta_vs16_25pct)}; '
        f'{int(row.semillas_mejoran_vs16)}/5 semillas,{int(row.partes_mejoran_vs16)}/4 partes. '
        f'[Informe](salidas/{out.name}/MINI_INFORME.md). Cinco fits nuevos; cero API/créditos/submits. Mayo reutilizado.')
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## 109. LightGBM192 historia y rangos evaluado - 2026-10-06\n\n'+note+'\n')
    print(summary.to_string(),flush=True)

if __name__=='__main__':main()
