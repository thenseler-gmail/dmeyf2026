"""Reproduce ganador CV por fold, parametros y scores locales; registra resultado."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier,Pool
from sklearn.model_selection import StratifiedKFold
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SEEDS=[541440,408476,741961,248865,717444]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(v):return '$'+f'{v:,.0f}'.replace(',','.')

def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo_verificado' and m['semillas_completadas']==SEEDS
    for f,h in m['source_hashes'].items():assert sha(ROOT/f)==h
    for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
    for f,h in m['firma']['codigo'].items():assert sha(TP/f)==h
    ref,seeds,train,valid,xt,xv,old=importlib.import_module('63_experimentos_features_local').cargar()
    cols=m['firma']['features'];cats=m['firma']['cat_features'];params=m['params_elegidos']
    assert list(xt)==list(xv)==cols and len(cols)==202 and not set(['numero_de_cliente','foto_mes','clase_ternaria']).intersection(cols)
    for frame in [xt,xv]:
        for c in cats:frame[c]=frame[c].astype('string').fillna('__MISSING__').astype(str)
    hashframe=lambda x:hashlib.sha256(pd.util.hash_pandas_object(x,index=False).to_numpy().tobytes()).hexdigest()
    assert hashframe(xt)==m['firma']['train_matrix'] and hashframe(xv)==m['firma']['valid_matrix']
    y=train.clase_ternaria.eq('BAJA+2').to_numpy();yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    f=pd.read_csv(out/'folds_abril.csv');pd.testing.assert_frame_equal(f[['numero_de_cliente','foto_mes','clase_ternaria']],train[['numero_de_cliente','foto_mes','clase_ternaria']])
    assert train.numero_de_cliente.is_unique and f.foto_mes.eq(202104).all()
    reconstructed=np.full(len(y),-1)
    for k,(tr,va) in enumerate(StratifiedKFold(n_splits=3,shuffle=True,random_state=214363).split(np.zeros(len(y)),y)):
        assert not set(train.numero_de_cliente.iloc[tr]).intersection(train.numero_de_cliente.iloc[va]);reconstructed[va]=k
    np.testing.assert_array_equal(reconstructed,f.fold)
    winner=json.loads((out/'seleccion_congelada.json').read_text(encoding='utf-8'));assert winner['params']==params and winner['trial']==m['trial_elegido']
    rows=pd.read_csv(out/'trials.csv');complete=rows[rows.state.eq('COMPLETE')];best=complete.sort_values(['value','number'],ascending=[False,True]).iloc[0]
    assert best.number==winner['trial'] and best.value==winner['ganancia_cv']
    td=out/'trials'/f'trial{winner["trial"]:03d}';oof=np.load(td/'predicciones_oof.npy');payments=np.where(y,1072500,-27500)
    assert np.isfinite(oof).all() and int(payments[oof>.025].sum())==winner['ganancia_cv']
    def check(model,seed):
        assert model.feature_names_==cols and model.classes_.tolist()==[0,1] and model.tree_count_==params['iterations']
        p=model.get_all_params();assert p['random_seed']==seed and p['depth']==params['depth']
        for key in ['learning_rate','l2_leaf_reg','subsample','rsm','random_strength']:np.testing.assert_allclose(p[key],params[key],rtol=1e-6,atol=1e-7)
        assert p['loss_function']=='Logloss' and p['bootstrap_type']=='Bernoulli' and p['boosting_type']=='Plain'
    for k in range(3):
        model=CatBoostClassifier();model.load_model(str(td/f'fold{k}.cbm'));check(model,SEEDS[0]);mask=reconstructed==k
        np.testing.assert_allclose(model.predict_proba(Pool(xt.loc[mask],cat_features=cats))[:,1],oof[mask],rtol=0,atol=0)
    pred=pd.read_csv(out/'predicciones_mayo.csv');pd.testing.assert_frame_equal(pred[['numero_de_cliente','foto_mes','clase_ternaria']],valid[['numero_de_cliente','foto_mes','clase_ternaria']])
    results=pd.read_csv(out/'resultados_semillas.csv');summary=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
    payments=np.where(yv,1072500,-27500);vp=Pool(xv,cat_features=cats)
    for seed in SEEDS:
        path=out/'modelos_mayo'/f'seed{seed}.cbm';assert sha(path)==m['modelos_sha256'][path.name]
        model=CatBoostClassifier();model.load_model(str(path));check(model,seed)
        np.testing.assert_allclose(model.predict_proba(vp)[:,1],pred[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        q=np.column_stack([pred[f'p_lgb_seed{seed}'],pred.p_tabpfn,pred[f'p_cat_seed{seed}']])@np.array([.4,.4,.2])
        selected=q>.025;np.testing.assert_array_equal(selected,pred[f'score_mix_catboost_optuna_seed{seed}']>.025)
        row=results[(results.variante=='mix_catboost_optuna')&(results.seed==seed)].iloc[0]
        assert int(payments[selected].sum())==row.ganancia and int(selected.sum())==row.contactos
    for name,group in results.groupby('variante'):assert group.ganancia.mean()==summary.loc[name,'ganancia']
    assert summary.loc['control16','ganancia']==266420000 and summary.loc['mix17','ganancia']==269813500
    save(out/'verificacion_independiente.json',dict(estado='verificado',modelos_cv_reproducidos=3,modelos_mayo_reproducidos=5,
        params_verificados=True,folds_reconstruidos=True,clientes_disjuntos=True,ganancia_oof_directa=True,
        seleccion_ganador_abril=True,scores_finales_matriciales=True,api=False,codigo_verificador_sha256=sha(Path(__file__))))
    row=summary.loc['mix_catboost_optuna']
    note=(f'**Optuna CatBoost completo y verificado:** trial{m["trial_elegido"]}; ensemble40/40/20,2,5%: '
        f'total medio {money(row.ganancia)},25% {money(row.ganancia_25pct)}; '
        f'delta frente16 {money(row.delta_vs_control16)},25% {money(row.delta_vs_control16_25pct)}; '
        f'frente17 {money(row.delta_vs_mix17)},25% {money(row.delta_vs_mix17_25pct)}. '
        f'[Informe](salidas/{out.name}/MINI_INFORME.md). CV3 abril; ganador congelado y cinco semillas mayo. '
        'Sin créditos; vínculos recurrentes mañana7 de octubre sobre el mejor modelo disponible.')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    entry=dict(carpeta=str(out.relative_to(ROOT)),estado='completo_verificado',trial=m['trial_elegido'],params=m['params_elegidos'],
        resultados=m['resultados'],supera16=m['supera16'],supera17=m['supera17'],api=False,creditos=0,submits=0,
        proxima_idea=dict(fecha='2026-10-07',experimento='vinculos_recurrentes',base='mejor_modelo_disponible',ejecutado=False))
    prepared=out/'entrega_preparada.json'
    if prepared.exists():entry['entrega_preparada']=json.loads(prepared.read_text(encoding='utf-8'))
    c['optuna_catboost']=entry;save(cfg,c)
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    if note not in s:nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
    bit=ROOT/'BITACORA_DMEYF.md';s=bit.read_text(encoding='utf-8');head='## 110. Optuna CatBoost CV abril y ensemble mayo - 2026-10-06'
    if head not in s:
        with bit.open('a',encoding='utf-8') as f:f.write('\n'+head+'\n\n'+note+'\n\n'+m['limitacion']+'\n')
    print('Verificado CV3,cinco modelos mayo y ganancias.');print(summary.to_string())

if __name__=='__main__':main()
