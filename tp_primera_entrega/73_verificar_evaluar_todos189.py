"""Verifica CatBoost desde raw y compara cruces189; parcial sin nueva API."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier,Pool

ROOT=Path(__file__).resolve().parents[1]
KEYS=['numero_de_cliente','foto_mes']
SEEDS=[541440,408476,741961,248865,717444]
WEIGHTS=dict(control16_50_50=[.5,.5,0,0,0],mix17_40_40_20=[.4,.4,.2,0,0],
    cat189_tab202=[.4,.4,0,.2,0],cat202_tab189=[.4,0,.2,0,.4],
    todos189_40_40_20=[.4,0,0,.2,.4],lgb189_tab189_50_50=[.5,0,0,0,.5])


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(v):return '$'+f'{v:,.0f}'.replace(',','.')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('salida',type=Path);ap.add_argument('--completo',action='store_true');args=ap.parse_args()
    out=args.salida.resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    module=importlib.import_module('72_todos189_local');m,tx,vx,yt=module.cargar(out)
    assert len(m['features'])==189 and m['train']==[202104] and m['evaluacion']==202105
    assert not m['fit_eval_set'] and m['target_catboost']==m['target_tabpfn']=='BAJA+2'
    source=importlib.import_module('63_experimentos_features_local')
    ref,seeds,train,valid,xt,xv,unused=source.cargar()
    np.testing.assert_allclose(xt[m['features']].to_numpy(),tx,rtol=0,atol=0,equal_nan=True)
    np.testing.assert_allclose(xv[m['features']].to_numpy(),vx,rtol=0,atol=0,equal_nan=True)
    np.testing.assert_array_equal(train.clase_ternaria.eq('BAJA+2').astype(int),yt)
    base=pd.read_csv(out/'predicciones_fuentes.csv');cb=pd.read_csv(out/'predicciones_catboost189.csv')
    pd.testing.assert_frame_equal(base[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    pd.testing.assert_frame_equal(base[KEYS],cb[KEYS]);assert base.foto_mes.eq(202105).all() and not base.numero_de_cliente.duplicated().any()
    cs=json.loads((out/'catboost_estado.json').read_text(encoding='utf-8'))
    assert cs['estado']=='completo' and cs['semillas_completadas']==SEEDS and cs['params']==m['params_catboost']
    assert sha(out/'predicciones_catboost189.csv')==cs['predicciones_sha256']
    frame=pd.DataFrame(vx,columns=m['features'])
    for c in m['cat_features']:frame[c]=frame[c].astype('string').fillna('__MISSING__').astype(str)
    pool=Pool(frame,cat_features=m['cat_features'])
    p=base.copy()
    for seed in SEEDS:
        path=out/'modelos_catboost189'/f'seed{seed}.cbm';assert sha(path)==cs['modelos_sha256'][path.name]
        model=CatBoostClassifier();model.load_model(str(path))
        assert model.tree_count_==800 and model.feature_names_==m['features'] and model.classes_.tolist()==[0,1]
        assert set(model.get_cat_feature_indices())=={m['features'].index(c) for c in m['cat_features']}
        params=model.get_all_params();assert params['random_seed']==seed
        for c in ['iterations','depth','loss_function','bootstrap_type','border_count','nan_mode']:
            assert params[c]==m['params_catboost'][c]
        for c in ['learning_rate','l2_leaf_reg','subsample','rsm','random_strength']:
            np.testing.assert_allclose(params[c],m['params_catboost'][c],rtol=0,atol=1e-7)
        np.testing.assert_allclose(model.predict_proba(pool)[:,1],cb[f'p_cat189_seed{seed}'],rtol=0,atol=1e-15)
        p[f'p_cat189_seed{seed}']=cb[f'p_cat189_seed{seed}']
    tabready=(out/'predicciones_tabpfn189.csv').exists()
    if args.completo:assert tabready
    if tabready:
        ts=json.loads((out/'tabpfn_estado.json').read_text(encoding='utf-8'))
        assert ts['estado']=='completo' and ts['train']==[202104] and ts['evaluacion']==202105 and ts['features']==189
        assert ts['classes']==[0,1] and ts['cotizacion']['estimated_cost']<=ts['max_creditos']
        assert sha(out/'predicciones_tabpfn189.csv')==ts['predicciones_sha256']
        tb=pd.read_csv(out/'predicciones_tabpfn189.csv');pd.testing.assert_frame_equal(p[KEYS],tb[KEYS])
        p['p_tab189']=tb.p_tab189
    else:p['p_tab189']=0.
    variants=list(WEIGHTS) if tabready else ['control16_50_50','mix17_40_40_20','cat189_tab202']
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();parts=p.parte_cliente.to_numpy();payments=np.where(y,1072500,-27500)
    assert y.sum()==870
    rows=[];partrows=[];predictions={}
    def stats(mask):
        n=int(mask.sum());tp=int((mask&y).sum());g=int(payments[mask].sum())
        return dict(contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4)
    for seed in SEEDS:
        matrix=np.column_stack([p[f'p_lgb189_seed{seed}'],p.p_tab202,p[f'p_cat202_seed{seed}'],p[f'p_cat189_seed{seed}'],p.p_tab189])
        assert np.isfinite(matrix).all() and ((matrix>=0)&(matrix<=1)).all()
        for v in variants:
            q=matrix@np.array(WEIGHTS[v]);predictions[(v,seed)]=q
            rows.append(dict(variante=v,seed=seed,**stats(q>.025)))
            for k in range(4):partrows.append(dict(variante=v,seed=seed,parte=k,**stats((q>.025)&(parts==k))))
    r=pd.DataFrame(rows);pr=pd.DataFrame(partrows)
    summary=r.groupby('variante')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean().loc[variants]
    assert summary.loc['control16_50_50','ganancia']==266420000 and summary.loc['mix17_40_40_20','ganancia']==269813500
    pivot=r.pivot(index='seed',columns='variante',values='ganancia')
    summary['delta_vs16_total']=summary.ganancia-266420000;summary['delta_vs16_25pct']=summary.delta_vs16_total/4
    summary['delta_vs17_total']=summary.ganancia-269813500;summary['delta_vs17_25pct']=summary.delta_vs17_total/4
    summary['semillas_mejoran_vs16']=[int((pivot[v]>pivot.control16_50_50).sum()) for v in variants]
    summary['semillas_mejoran_vs17']=[int((pivot[v]>pivot.mix17_40_40_20).sum()) for v in variants]
    if args.completo:
        for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
        saved=pd.read_csv(out/'resultados_semillas.csv')
        merged=saved.merge(r,on=['variante','seed'],suffixes=('_saved','_audit'),validate='one_to_one');assert len(merged)==30
        for c in ['contactos','tp','fp','ganancia','ganancia_25pct']:
            np.testing.assert_allclose(merged[c+'_saved'],merged[c+'_audit'],rtol=0,atol=0)
        saved=pd.read_csv(out/'resultados_partes_mayo.csv')
        merged=saved.merge(pr,on=['variante','seed','parte'],suffixes=('_saved','_audit'),validate='one_to_one');assert len(merged)==120
        for c in ['contactos','tp','fp','ganancia','ganancia_25pct']:
            np.testing.assert_allclose(merged[c+'_saved'],merged[c+'_audit'],rtol=0,atol=0)
        avg=pd.read_csv(out/'lista_promedio5.csv');assert len(avg)==6
        meanmatrix=np.column_stack([p[[f'p_lgb189_seed{s}' for s in SEEDS]].mean(axis=1),p.p_tab202,
            p[[f'p_cat202_seed{s}' for s in SEEDS]].mean(axis=1),p[[f'p_cat189_seed{s}' for s in SEEDS]].mean(axis=1),p.p_tab189])
        for row in avg.itertuples():assert stats(meanmatrix@np.array(WEIGHTS[row.variante])>.025)['ganancia']==row.ganancia
        saved=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
        shared=summary.columns.intersection(saved.columns)
        np.testing.assert_allclose(summary[shared],saved.loc[summary.index,shared],rtol=0,atol=1e-8)
        m['estado']='completo_verificado';m['bloqueo_api_resuelto']=True
        save(out/'manifest.json',m)
    else:
        r.to_csv(out/'resultados_catboost_parcial.csv',index=False);summary.to_csv(out/'comparacion_catboost_parcial.csv')
    name='verificacion_independiente.json' if args.completo else 'verificacion_catboost189.json'
    save(out/name,dict(estado='verificado',matrices_desde_raw=True,catboost189_modelos_reproducidos=5,
        ganancias_individuales=len(r),ganancias_partes=len(pr),tabpfn189_completo=tabready,api_repetida=False,
        codigo_verificador_sha256=sha(Path(__file__))))
    report=['# Todos los modelos con189 variables: ensayo local','',
        'Entrenamiento en abril y evaluación en mayo. Mismas cinco semillas, parámetros, pesos y corte estricto >0,025. LightGBM189 combinado reutilizado; CatBoost189 y TabPFN189 nuevos, ambos BAJA+2. Sin Optuna ni cambio de target.','',
        '| Variante | Ganancia total media5 | 25% | Delta total vs16 | 25% delta | Semillas mejores vs16 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for v,row in summary.iterrows():report.append(f'| {v} | {money(row.ganancia)} | {money(row.ganancia_25pct)} | {money(row.delta_vs16_total)} | {money(row.delta_vs16_25pct)} | {int(row.semillas_mejoran_vs16)}/5 |')
    report+=['',
        'Los cruces definidos antes de evaluar separan los cambios: cat189_tab202 reduce las variables solo de CatBoost; cat202_tab189 solo de TabPFN; todos189 de ambos. Las mezclas de tres modelos conservan pesos 40/40/20 para LightGBM/TabPFN/CatBoost; las de dos modelos, 50/50. La métrica principal es la media de las cinco listas individuales; la lista que promedia predicciones se informa aparte.','',
        'Estado: '+('TabPFN189 completo. Créditos consumidos: '+str(ts['creditos'])+'.' if tabready else
            'TabPFN189 pendiente de autorizacion explicita solicitada tras rechazo de revision automatica. Proceso API no creado; cero creditos. SoloCatBoost189 completo; resultado de todos189 todavia no calculado.'),
        '',m['limitaciones'],'',
        'No se leyeron junio ni agosto. Las etiquetas de mayo se usaron solo para evaluar, nunca en el entrenamiento ni en la API. El mejor público sigue siendo entrega16: $96.921.000, ya correspondiente al 25%. No se preparó ni envió un nuevo submit; la entrega17 queda conservada y postergada por pedido del usuario.','',
        'Se reconstruyeron matrices y targets originales y se reprodujeron las predicciones de los cinco CatBoost. Fuentes LightGBM/TabPFN202/CatBoost202 verificadas. Las predicciones de TabPFN189 se conservan por hash; la auditoría no repite llamadas a la API. Los modelos nuevos usan exactamente las mismas 189 columnas en el mismo orden.']
    (out/('MINI_INFORME.md' if args.completo else 'MINI_INFORME_CATBOOST.md')).write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string(),flush=True)


if __name__=='__main__':main()
