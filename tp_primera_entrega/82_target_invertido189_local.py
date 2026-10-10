"""LightGBM189 BAJA+2 + TabPFN202 combinado guardado; ensayo local fijo50/50."""
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas'
FEATURE=SAL/'features_local_20261006_140702'
TAB=SAL/'validacion_tabpfn_combinado_20261006_003126'
OLD=SAL/'validacion_targets_ensemble_20261006_002629'
SEEDS=[541440,408476,741961,248865,717444];KEYS=['numero_de_cliente','foto_mes']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(x):return '$'+f'{x:,.0f}'.replace(',','.')

def main():
    fm=json.loads((FEATURE/'manifest.json').read_text(encoding='utf-8'))
    tm=json.loads((TAB/'manifest.json').read_text(encoding='utf-8'))
    om=json.loads((OLD/'manifest.json').read_text(encoding='utf-8'))
    for path,meta in [(FEATURE,fm),(TAB,tm),(OLD,om)]:
        assert meta['estado']=='completo_verificado'
        for f,h in meta['archivos_sha256'].items():assert sha(path/f)==h
    assert tm['firma']['train']==[202104] and tm['firma']['evaluacion']==202105 and tm['firma']['target_tabpfn']=='BAJA+1/BAJA+2'
    ref,seeds,train,valid,xt,xv,original=importlib.import_module('63_experimentos_features_local').cargar()
    assert seeds==SEEDS
    cols=fm['firma']['variants']['historia_1_mes']['features'];assert len(cols)==189
    xt=xt[cols];xv=xv[cols]
    for frame,key in [(xt,'train_matrix_sha256'),(xv,'valid_matrix_sha256')]:
        # Exact keys are verified below against the saved npz provenance as well.
        assert frame.columns.tolist()==cols
    matrixdir=SAL/'todos189_local_20261006_150519'
    mm=json.loads((matrixdir/'manifest.json').read_text(encoding='utf-8'))
    assert sha(matrixdir/'matrices.npz')==mm['matrices_sha256']
    matrices=np.load(matrixdir/'matrices.npz')
    np.testing.assert_allclose(xt.to_numpy(),matrices['train'],rtol=0,atol=0,equal_nan=True)
    np.testing.assert_allclose(xv.to_numpy(),matrices['valid'],rtol=0,atol=0,equal_nan=True)
    y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy();yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    np.testing.assert_array_equal(y,matrices['target'])
    tp=pd.read_csv(TAB/'predicciones_mayo.csv');old=pd.read_csv(OLD/'predicciones_mayo.csv')
    ctrl=pd.read_csv(FEATURE/'historia_1_mes/predicciones_mayo.csv')
    for p in [tp,old,ctrl]:pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],p[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(tp.p_tabpfn_baja2,ctrl.p_tabpfn,rtol=0,atol=1e-15)
    params=ref['elegido']['params'];rounds=ref['elegido']['num_boost_round'];assert rounds==273
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('target_invertido189_%Y%m%d_%H%M%S');out.mkdir();md=out/'modelos';md.mkdir()
    m=dict(estado='entrenando',train=[202104],evaluacion=202105,historia_auxiliar=[202103],semillas=SEEDS,
        features_lightgbm=cols,features_tabpfn=tm['firma']['features'],target_lightgbm='BAJA+2',target_tabpfn='BAJA+1/BAJA+2',
        params=params,num_boost_round=rounds,pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.025,operador='>',
        nuevos_fits=5,api=False,creditos=0,submits=0,fit_eval_set=False,
        train_matrix_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        valid_matrix_sha256=hashlib.sha256(xv.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        target_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [FEATURE/'manifest.json',FEATURE/'historia_1_mes/predicciones_mayo.csv',
            TAB/'manifest.json',TAB/'predicciones_mayo.csv',OLD/'manifest.json',OLD/'predicciones_mayo.csv']},
        codigo_sha256=sha(Path(__file__)),limitacion='Mayo y semillas reutilizados: no test independiente ni garantia agosto. '
        'Parametros fijados para target combinado; no optimizacion por nuevo target. Score mezclado no P(BAJA+2) calibrada. '
        'No junio/agosto; TabPFN202 combinado abril->mayo reutilizado, cero API.')
    save(out/'manifest.json',m);print('Salida:',out,flush=True)
    pred=ctrl[KEYS+['clase_ternaria','parte_cliente']].copy();pred['p_tab_combinado']=tp.p_tabpfn_combinado
    pred['p_tab_baja2']=ctrl.p_tabpfn;rows=[];parts=[];changes=[]
    def metric(q,area=None):
        sel=np.asarray(q)>.025
        if area is not None:sel=sel&area
        n=int(sel.sum());hits=int((sel&yv).sum());g=hits*1100000-n*27500
        assert g==int(np.where(yv,1072500,-27500)[sel].sum())
        return dict(contactos=n,tp=hits,fp=n-hits,ganancia=g,ganancia_25pct=g/4)
    for seed in SEEDS:
        model=lgb.train(dict(params,seed=seed),lgb.Dataset(xt,label=y),num_boost_round=rounds)
        path=md/f'seed{seed}.txt';model.save_model(str(path));q=model.predict(xv,validate_features=True)
        reload=lgb.Booster(model_file=str(path));assert reload.feature_name()==cols and reload.num_trees()==273
        np.testing.assert_allclose(q,reload.predict(xv,validate_features=True),rtol=0,atol=0)
        pred[f'p_lgb_baja2_seed{seed}']=q
        scores=dict(control16=(ctrl[f'p_seed{seed}']+ctrl.p_tabpfn)/2,
            invertido202=(old[f'p_baja2_seed{seed}']+tp.p_tabpfn_combinado)/2,
            invertido189=(q+tp.p_tabpfn_combinado)/2,
            ambos_baja2_189=(q+ctrl.p_tabpfn)/2)
        control=np.asarray(scores['control16'])>.025
        for name,score in scores.items():
            assert np.isfinite(score).all() and np.asarray(score).min()>=0 and np.asarray(score).max()<=1
            pred[f'score_{name}_seed{seed}']=score
            rows.append(dict(variante=name,seed=seed,**metric(score)))
            for k in range(4):parts.append(dict(variante=name,seed=seed,parte=k,**metric(score,pred.parte_cliente.eq(k).to_numpy())))
            sel=np.asarray(score)>.025;add=sel&~control;remove=control&~sel
            changes.append(dict(variante=name,seed=seed,agregados=int(add.sum()),retirados=int(remove.sum()),
                agregados_baja2=int((add&yv).sum()),retirados_baja2=int((remove&yv).sum())))
        pred.to_csv(out/'predicciones_mayo.csv',index=False);print('Semilla',seed,'completa',flush=True)
    r=pd.DataFrame(rows);pr=pd.DataFrame(parts)
    summary=r.groupby('variante')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    assert summary.loc['control16','ganancia']==266420000 and summary.loc['invertido202','ganancia']==261684500
    pivot=r.pivot(index='seed',columns='variante',values='ganancia')
    group=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['delta_vs16_total']=summary.ganancia-266420000;summary['delta_vs16_25pct']=summary.delta_vs16_total/4
    summary['semillas_mejoran_vs16']=[int((pivot[v]>pivot.control16).sum()) for v in summary.index]
    summary['partes_mejoran_vs16']=[int((group[v]>group.control16).sum()) for v in summary.index]
    r.to_csv(out/'resultados_semillas.csv',index=False);pr.to_csv(out/'resultados_partes.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False);summary.to_csv(out/'comparacion_media5.csv')
    assert np.isfinite(pred.drop(columns=KEYS+['clase_ternaria','parte_cliente']).to_numpy()).all()
    # Verificar de disco scores del candidato con producto matricial independiente.
    disk=pd.read_csv(out/'predicciones_mayo.csv')
    for seed in SEEDS:
        q=np.column_stack([disk[f'p_lgb_baja2_seed{seed}'],disk.p_tab_combinado])@np.array([.5,.5])
        np.testing.assert_array_equal(q>.025,disk[f'score_invertido189_seed{seed}']>.025)
        assert metric(q)['ganancia']==r[(r.variante=='invertido189')&(r.seed==seed)].ganancia.iloc[0]
    m.update(estado='completo_verificado',resultados=summary.reset_index().to_dict('records'),
        supera16_local=bool(summary.loc['invertido189','ganancia']>266420000),
        modelos_sha256={f.name:sha(f) for f in md.glob('*.txt')},archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')})
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',matrices_raw_y_guardadas_iguales=True,
        target_baja2_reconstruido=True,modelos_reproducidos=5,control16_reproducido=True,
        invertido202_reproducido=True,selecciones_producto_matricial=True,api=False))
    report=['# Target invertido con LightGBM189','',
        'Train abril, evaluación mayo. LightGBM189 BAJA+2 nuevo, TabPFN202 combinado guardado. Cinco semillas, '
        '273 árboles/params congelados, mezcla50/50 y corte >0,025. Sin CatBoost, búsqueda de corte o pesos.','',
        '| Variante | Total medio | 25% | Delta total vs16 | 25% del delta | Semillas mejores | Partes mejores |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,row in summary.iterrows():report.append(f'| {name} | {money(row.ganancia)} | {money(row.ganancia_25pct)} | {money(row.delta_vs16_total)} | {money(row.delta_vs16_25pct)} | {int(row.semillas_mejoran_vs16)}/5 | {int(row.partes_mejoran_vs16)}/4 |')
    report+=['',m['limitacion'],'',
        'invertido202 reproduce la prueba anterior reservada. ambos_baja2_189 es un diagnóstico adicional con los mismos fits nuevos, sin créditos. '
        'El candidato pedido es invertido189; no cambiar de target/corte/pesos automáticamente al mirar resultados. '
        'No entrenamiento final abril+mayo, nuevas llamadas PriorLabs ni nuevos CSVBot. Mejor público sigue16$96.921.000.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    c['target_invertido189_local']={**m,'carpeta':str(out.relative_to(ROOT))};save(cfg,c)
    row=summary.loc['invertido189']
    note=(f'**Target invertido189 completo:** total medio {money(row.ganancia)},25% {money(row.ganancia_25pct)}; '
        f'delta frente16 {money(row.delta_vs16_total)},25% {money(row.delta_vs16_25pct)}; '
        f'{int(row.semillas_mejoran_vs16)}/5 semillas,{int(row.partes_mejoran_vs16)}/4 partes. '
        f'[Informe](salidas/{out.name}/MINI_INFORME.md). Cinco fitsLightGBM189BAJA2, TabPFN202 combinado reutilizado. '
        'Cero API/créditos/submits/fitsfinales. Mayo reutilizado; sin garantía pública.')
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## 108. Target invertido con LightGBM189 evaluado - 2026-10-06\n\n'+note+'\n')
    print(summary.to_string(),flush=True)

if __name__=='__main__':main()
