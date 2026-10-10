"""Optuna CatBoost202 BAJA+2: CV3 abril; un ganador congelado, cinco semillas mayo.

La funcion objetivo es ganancia CatBoost solo a >.025. No se usan predicciones
TabPFN entrenadas con los clientes de CV para optimizar un ensemble contaminado.
El ensemble LGB189/Tab202/Cat202 se comprueba despues, pesos40/40/20 fijos.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import optuna
from catboost import CatBoostClassifier,Pool
from sklearn.model_selection import StratifiedKFold

ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas'
CAT=SAL/'catboost_local_20261006_004259';FEATURE=SAL/'features_local_20261006_140702'
SEEDS=[541440,408476,741961,248865,717444];KEYS=['numero_de_cliente','foto_mes']
SEARCH_SEED=214363
SEARCH_KEYS=['iterations','depth','learning_rate','l2_leaf_reg','subsample','rsm','random_strength']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(v):return '$'+f'{v:,.0f}'.replace(',','.')
def framehash(x):return hashlib.sha256(pd.util.hash_pandas_object(x,index=False).to_numpy().tobytes()).hexdigest()
def params_for(trial,base):
    return dict(base,iterations=trial.suggest_categorical('iterations',[400,600,800,1000]),
        depth=trial.suggest_int('depth',4,7),learning_rate=trial.suggest_float('learning_rate',.03,.12,log=True),
        l2_leaf_reg=trial.suggest_float('l2_leaf_reg',2,30,log=True),subsample=trial.suggest_float('subsample',.6,1),
        rsm=trial.suggest_float('rsm',.5,1),random_strength=trial.suggest_float('random_strength',.1,3,log=True))
def metric(y,p):
    selected=np.asarray(p)>.025;n=int(selected.sum());tp=int((selected&y).sum());g=tp*1100000-n*27500
    assert g==np.where(y,1072500,-27500)[selected].sum()
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trials',type=int,default=16);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    cm=json.loads((CAT/'manifest.json').read_text(encoding='utf-8'))
    fm=json.loads((FEATURE/'manifest.json').read_text(encoding='utf-8'))
    assert cm['estado']==fm['estado']=='completo_verificado'
    for d,meta in [(CAT,cm),(FEATURE,fm)]:
        for f,h in meta['archivos_sha256'].items():assert sha(d/f)==h
    ref,seeds,train,valid,xt,xv,old=importlib.import_module('63_experimentos_features_local').cargar()
    assert seeds==SEEDS and len(xt)==163284 and len(xv)==163768 and train.numero_de_cliente.is_unique
    base=cm['firma']['params'];cols=cm['firma']['features'];cats=cm['firma']['cat_features']
    assert list(xt)==list(xv)==cols and len(cols)==202
    for frame in [xt,xv]:
        for c in cats:frame[c]=frame[c].astype('string').fillna('__MISSING__').astype(str)
    y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy();yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    assert framehash(xt)==cm['firma']['matriz_train_sha256'] and framehash(xv)==cm['firma']['matriz_mayo_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==cm['firma']['target_train_sha256']
    lp=pd.read_csv(FEATURE/'historia_1_mes/predicciones_mayo.csv');cp=pd.read_csv(CAT/'predicciones_mayo.csv')
    for p in [lp,cp]:pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],p[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(lp.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
    folds=np.full(len(y),-1,dtype=int)
    cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=SEARCH_SEED)
    for k,(tr,va) in enumerate(cv.split(np.zeros(len(y)),y)):
        assert not set(train.numero_de_cliente.iloc[tr]).intersection(train.numero_de_cliente.iloc[va]);folds[va]=k
    assert np.all(folds>=0)
    out=args.reanudar or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('optuna_catboost_%Y%m%d_%H%M%S')
    out.mkdir(exist_ok=bool(args.reanudar));(out/'trials').mkdir(exist_ok=True);(out/'modelos_mayo').mkdir(exist_ok=True)
    signature=dict(features=cols,cat_features=cats,base=base,seeds=SEEDS,train_matrix=framehash(xt),valid_matrix=framehash(xv),
        target_sha256=hashlib.sha256(y.tobytes()).hexdigest(),folds_sha256=hashlib.sha256(folds.tobytes()).hexdigest(),
        codigo={f:sha(TP/f) for f in ['84_optuna_catboost.py','63_experimentos_features_local.py','features.py','baseline.py']})
    if args.reanudar:
        m=json.loads((out/'manifest.json').read_text(encoding='utf-8'));assert m['firma']==signature
    else:
        m=dict(estado='busqueda_abril',firma=signature,trials_solicitados=args.trials,train=[202104],evaluacion=202105,
            target_catboost='BAJA+2',target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
            features_lightgbm=189,features_tabpfn=202,features_catboost=202,semillas=SEEDS,
            protocolo='16 trials incluyendo baseline; CV3 estratificada por cliente solo abril, seed fija541440. '
            'Maximizar suma ganancia OOF CatBoost a>.025. Pruning por ganancia OOF parcial escalada a todo abril, despues de5 trials iniciales. '
            'No early stopping con mayo. Un unico ganador por CV congelado antes de evaluar5semillas abril->mayo. '
            'Ensemble40/40/20,corte>.025; comparar contra16 y17. Sin optimizar pesos/features/target/corte.',
            api=False,creditos=0,submits=0,junio_validacion=False,fit_eval_set=False,
            source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [CAT/'manifest.json',CAT/'predicciones_mayo.csv',FEATURE/'manifest.json',FEATURE/'historia_1_mes/predicciones_mayo.csv']},
            versiones={p:importlib.metadata.version(p) for p in ['optuna','catboost','numpy','pandas']},
            limitacion='CV por clientes de abril no es test temporal; se selecciona por CatBoost solo y su aporte al ensemble se comprueba despues. '
            'Mayo/semillas reutilizados: no validacion independiente ni garantia publica. No hay OOF compatibles de TabPFN en abril '
            'para optimizar el ensemble sin nuevas inferencias; no usar sus predicciones in-sample para tuning.')
        assignments=train[KEYS+['clase_ternaria']].copy();assignments['fold']=folds;assignments.to_csv(out/'folds_abril.csv',index=False)
    save(out/'manifest.json',m);print('Salida:',out,flush=True)
    pools=[]
    for k in range(3):
        tr=folds!=k;va=folds==k
        pools.append((Pool(xt.loc[tr],label=y[tr],cat_features=cats),Pool(xt.loc[va],cat_features=cats),va))
    study=optuna.create_study(study_name='catboost_abril_cv3_ganancia025',storage='sqlite:///'+str((out/'optuna.sqlite3').resolve()).replace('\\','/'),
        direction='maximize',load_if_exists=True,sampler=optuna.samplers.TPESampler(seed=SEARCH_SEED,n_startup_trials=5),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5,n_warmup_steps=0))
    if not study.trials:study.enqueue_trial({k:base[k] for k in SEARCH_KEYS})
    def objective(trial):
        start=time.perf_counter();params=params_for(trial,base);td=out/'trials'/f'trial{trial.number:03d}';td.mkdir(exist_ok=True)
        probabilities=np.full(len(y),np.nan);foldresults=[];total=0;seen=0
        save(td/'params.json',params)
        print('Trial',trial.number,'params', {k:params[k] for k in SEARCH_KEYS},flush=True)
        for k,(trpool,vpool,mask) in enumerate(pools):
            model=CatBoostClassifier(**params,random_seed=SEEDS[0]);model.fit(trpool,verbose=False)
            p=model.predict_proba(vpool)[:,1];assert model.tree_count_==params['iterations'] and np.isfinite(p).all()
            model.save_model(str(td/f'fold{k}.cbm'));probabilities[mask]=p
            met=metric(y[mask].astype(bool),p);foldresults.append(dict(fold=k,filas=int(mask.sum()),**met))
            total+=met['ganancia'];seen+=int(mask.sum());trial.report(total/seen*len(y),step=k)
            save(td/'estado.json',dict(estado='evaluando',folds=foldresults,segundos=time.perf_counter()-start))
            print('Trial',trial.number,'fold',k,'ganancia',met['ganancia'],'25%',met['ganancia_25pct'],flush=True)
            if k<2 and trial.should_prune():
                np.save(td/'predicciones_oof.npy',probabilities)
                save(td/'estado.json',dict(estado='pruned',folds=foldresults,segundos=time.perf_counter()-start))
                raise optuna.TrialPruned()
        np.save(td/'predicciones_oof.npy',probabilities)
        assert np.isfinite(probabilities).all() and metric(y.astype(bool),probabilities)['ganancia']==total
        trial.set_user_attr('ganancia_25pct',total/4);trial.set_user_attr('segundos',time.perf_counter()-start)
        save(td/'estado.json',dict(estado='completo',folds=foldresults,ganancia=total,ganancia_25pct=total/4,segundos=time.perf_counter()-start))
        return total
    def checkpoint(study,trial):
        study.trials_dataframe().to_csv(out/'trials.csv',index=False)
        m.update(trials_terminados=sum(t.state.is_finished() for t in study.trials),mejor_trial_provisional=study.best_trial.number,
            mejor_ganancia_cv=study.best_value,mejor_ganancia_cv_25pct=study.best_value/4)
        save(out/'manifest.json',m)
    remaining=max(0,args.trials-sum(t.state.is_finished() for t in study.trials))
    if remaining:study.optimize(objective,n_trials=remaining,callbacks=[checkpoint],gc_after_trial=True)
    winner=study.best_trial;params=dict(base,**winner.params)
    np.testing.assert_allclose(metric(y.astype(bool),np.load(out/'trials'/f'trial{winner.number:03d}'/'predicciones_oof.npy'))['ganancia'],winner.value,rtol=0,atol=0)
    save(out/'seleccion_congelada.json',dict(trial=winner.number,params=params,ganancia_cv=winner.value,ganancia_cv_25pct=winner.value/4,
        seleccionado_solo_abril=True,mayo_no_usado_por_optuna=True,fecha=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).isoformat()))
    m.update(estado='evaluando_mayo',trial_elegido=winner.number,params_elegidos=params,semillas_completadas=[]);save(out/'manifest.json',m)
    print('GANADOR CONGELADO',winner.number,'gananciaCV',winner.value,'25%',winner.value/4,flush=True)
    trpool=Pool(xt,label=y,cat_features=cats);vp=Pool(xv,cat_features=cats)
    pred=lp[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy();rows=[];partrows=[]
    for seed in SEEDS:
        path=out/'modelos_mayo'/f'seed{seed}.cbm'
        if not path.exists():
            if params==base:path.write_bytes((CAT/'modelos'/f'seed{seed}.cbm').read_bytes())
            else:
                model=CatBoostClassifier(**params,random_seed=seed);model.fit(trpool,verbose=200);model.save_model(str(path))
        model=CatBoostClassifier();model.load_model(str(path))
        assert model.feature_names_==cols and model.tree_count_==params['iterations'] and model.get_all_params()['random_seed']==seed
        new=model.predict_proba(vp)[:,1];assert np.isfinite(new).all() and ((new>=0)&(new<=1)).all()
        pred[f'p_cat_seed{seed}']=new;pred[f'p_lgb_seed{seed}']=lp[f'p_seed{seed}']
        scores=dict(control16=(lp[f'p_seed{seed}']+lp.p_tabpfn)/2,
            mix17=.4*lp[f'p_seed{seed}']+.4*lp.p_tabpfn+.2*cp[f'p_cat_seed{seed}'],
            mix_catboost_optuna=.4*lp[f'p_seed{seed}']+.4*lp.p_tabpfn+.2*new,
            catboost_base=cp[f'p_cat_seed{seed}'],catboost_optuna=new)
        for name,q in scores.items():
            pred[f'score_{name}_seed{seed}']=q;rows.append(dict(variante=name,seed=seed,**metric(yv,q)))
            for k in range(4):mask=lp.parte_cliente.eq(k).to_numpy();partrows.append(dict(variante=name,seed=seed,parte=k,**metric(yv[mask],np.asarray(q)[mask])))
        pred.to_csv(out/'predicciones_mayo.csv',index=False);m['semillas_completadas'].append(seed);save(out/'manifest.json',m)
        print('Mayo semilla',seed,'completa',flush=True)
    r=pd.DataFrame(rows);pr=pd.DataFrame(partrows);summary=r.groupby('variante')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    assert summary.loc['control16','ganancia']==266420000 and summary.loc['mix17','ganancia']==269813500
    pivot=r.pivot(index='seed',columns='variante',values='ganancia');groups=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    for control in ['control16','mix17']:
        summary['delta_vs_'+control]=summary.ganancia-summary.loc[control,'ganancia'];summary['delta_vs_'+control+'_25pct']=summary['delta_vs_'+control]/4
        summary['semillas_mejoran_'+control]=[int((pivot[v]>pivot[control]).sum()) for v in summary.index]
        summary['partes_mejoran_'+control]=[int((groups[v]>groups[control]).sum()) for v in summary.index]
    r.to_csv(out/'resultados_semillas.csv',index=False);pr.to_csv(out/'resultados_partes.csv',index=False);summary.to_csv(out/'comparacion_media5.csv')
    # Comprobacion independiente de mezcla desde archivos y pago de seleccion.
    disk=pd.read_csv(out/'predicciones_mayo.csv')
    for seed in SEEDS:
        model=CatBoostClassifier();model.load_model(str(out/'modelos_mayo'/f'seed{seed}.cbm'))
        np.testing.assert_allclose(model.predict_proba(vp)[:,1],disk[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        q=np.column_stack([disk[f'p_lgb_seed{seed}'],disk.p_tabpfn,disk[f'p_cat_seed{seed}']])@np.array([.4,.4,.2])
        np.testing.assert_array_equal(q>.025,disk[f'score_mix_catboost_optuna_seed{seed}']>.025)
        assert metric(yv,q)['ganancia']==r[(r.variante=='mix_catboost_optuna')&(r.seed==seed)].ganancia.iloc[0]
    row=summary.loc['mix_catboost_optuna']
    m.update(estado='completo_verificado',resultados=summary.reset_index().to_dict('records'),
        supera16=bool(row.ganancia>266420000),supera17=bool(row.ganancia>269813500),
        modelos_sha256={f.name:sha(f) for f in (out/'modelos_mayo').glob('*.cbm')},
        archivos_sha256={str(f.relative_to(out)):sha(f) for f in out.glob('*.csv')},
        modelos_finales_nuevos=0,entrega_preparada=False)
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',ganancia_oof_reproducida=True,clientes_train_valid_disjuntos=True,
        seleccion_solo_abril=True,modelos_mayo_reproducidos=5,control16_y17_reproducidos=True,score_matricial_verificado=True,api=False))
    report=['# Optuna CatBoost: CV en abril y ensemble en mayo','',
        f'Trial elegido{winner.number}; parámetros: `{params}`.','',
        m['protocolo'],'',
        'Optuna optimiza CatBoost solo. El aporte al ensemble se evalúa después de congelar el ganador. La falta de predicciones OOF compatibles de TabPFN en abril impide usar sus scores entrenados en abril como objetivo interno sin fuga.','',
        '| Variante | Total medio5 | 25% | Delta vs16 | 25% delta | Semillas mejores vs16 | Partes mejores vs16 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,v in summary.iterrows():report.append(f'| {name} | {money(v.ganancia)} | {money(v.ganancia_25pct)} | {money(v.delta_vs_control16)} | {money(v.delta_vs_control16_25pct)} | {int(v.semillas_mejoran_control16)}/5 | {int(v.partes_mejoran_control16)}/4 |')
    report+=['',f'Delta ensemble frente17: {money(row.delta_vs_mix17)},25% {money(row.delta_vs_mix17_25pct)}. '
        f'Mejora{int(row.semillas_mejoran_mix17)}/5 semillas y{int(row.partes_mejoran_mix17)}/4 partes.','',m['limitacion'],'',
        'Cero créditos/API/submits. Aún no se entrenó con abril+mayo para agosto. Vínculos recurrentes quedan para mañana sobre el mejor modelo disponible.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('RESULTADO FINAL',out,flush=True);print(summary.to_string(),flush=True)

if __name__=='__main__':main()
