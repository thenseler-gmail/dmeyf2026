"""Optuna combinado: abril CV por cliente, top5 x5 semillas abril->mayo.

Junio nunca se usa en desarrollo. No API, ranking/topN ni tuning de umbral.
El candidato final, si supera el control de mayo, usa mayo/junio->agosto.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
KEYS=['numero_de_cliente','foto_mes']
prep=importlib.import_module('33_reentrenar_lightgbm_haberes')
medir=importlib.import_module('30_validacion_lightgbm').medir


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,m):
    p.write_text(json.dumps(m,indent=2,ensure_ascii=False,default=str),encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reanudar',type=Path)
    ap.add_argument('--trials',type=int,default=30)
    ap.add_argument('--max-rounds',type=int,default=1000)
    args=ap.parse_args()
    assert args.trials>=5 and args.max_rounds>0
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    policy=json.loads((ROOT/'tp_primera_entrega/config_validacion_lightgbm.json').read_text())
    seeds=policy['politica_semillas_proximas_pruebas']['exploracion']
    assert seeds==[541440,408476,741961,248865,717444]
    reference=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    ref=json.loads((reference/'manifest.json').read_text())
    assert json.loads((reference/'verificacion.json').read_text())['estado']=='verificado'
    old=ref['elegido'];base=dict(old['params'])
    for k in ['num_leaves','learning_rate','min_data_in_leaf','feature_fraction','bagging_fraction']:
        base.pop(k)
    datos,cols=prep.cargar_desarrollo(config)
    assert cols==ref['features_lightgbm'] and len(cols)==202
    assert datos.foto_mes.max()==202105
    groups=pd.read_csv(SAL/'top5_semillas_20261005_194616/asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']],groups[KEYS+['clase_ternaria']])
    folds=groups.fold_cliente.to_numpy()
    x=preparar(datos,cols)[0]
    y=datos.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    out=args.reanudar or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('optuna_combinado_%Y%m%d_%H%M%S')
    out.mkdir(parents=True,exist_ok=bool(args.reanudar))
    (out/'cache').mkdir(exist_ok=True)
    (out/'modelos').mkdir(exist_ok=True)
    firma=dict(codigo={f:sha(Path(__file__).parent/f) for f in ['43_optuna_combinado.py','features.py','features_abandono.py','baseline.py','33_reentrenar_lightgbm_haberes.py']},
               features=cols,semillas=seeds,max_rounds=args.max_rounds,
               versiones={p:importlib.metadata.version(p) for p in ['lightgbm','optuna','pandas','numpy','duckdb']},
               fuente_cv_sha256=sha(SAL/'top5_semillas_20261005_194616/asignacion_folds.csv'),
               referencia_mayo_sha256=sha(reference/'predicciones_mayo.csv'))
    if args.reanudar:
        meta=json.loads((out/'manifest.json').read_text());assert meta['firma']==firma
    else:
        meta=dict(estado='busqueda',firma=firma,trials_solicitados=args.trials,umbral=.025,operador='>',target='BAJA+1/BAJA+2',
                  referencia=str(reference),control=old,seed_busqueda=seeds[0],seed_sampler=214363,
                  seleccion='Top5 por suma de ganancias OOF abril con una semilla; elegir por ganancia de promedio5 abril->mayo. Desempate media individual, menor std, trial menor.',
                  junio='Excluido de desarrollo; solo train final si mejora mayo',
                  limitaciones='CV abril retrospectivo con otros clientes del mismo mes, early stopping optimista. Mayo y semillas reutilizadas: no test independiente. Chequeo marzo->mayo limitado por marzo sin historia. Sin garantia de publico.',
                  api=False,creditos=0)
    save(out/'manifest.json',meta)
    groups.to_csv(out/'asignacion_folds.csv',index=False)
    print('Salida:',out,flush=True)
    ivabril=np.flatnonzero(datos.foto_mes.eq(202104).to_numpy())
    audit=[]
    def objective(trial):
        params=dict(base,seed=seeds[0],
                    num_leaves=trial.suggest_int('num_leaves',8,96),
                    learning_rate=trial.suggest_float('learning_rate',.01,.15,log=True),
                    min_data_in_leaf=trial.suggest_int('min_data_in_leaf',200,2000),
                    feature_fraction=trial.suggest_float('feature_fraction',.15,.85),
                    bagging_fraction=trial.suggest_float('bagging_fraction',.6,1),
                    lambda_l1=trial.suggest_float('lambda_l1',0,20),
                    lambda_l2=trial.suggest_float('lambda_l2',0,30))
        prob=np.full(len(datos),np.nan);rounds=[];metrics=[]
        for fold in range(4):
            it=np.flatnonzero((datos.foto_mes.to_numpy()<=202104)&(folds!=fold))
            iv=np.flatnonzero(datos.foto_mes.eq(202104).to_numpy()&(folds==fold))
            assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
            reward=np.where(datos.clase_ternaria.iloc[iv].eq('BAJA+2'),1072500,-27500)
            def feval(p,d):
                return 'ganancia',float(reward[p>.025].sum()),True
            train=lgb.Dataset(x.iloc[it],label=y[it])
            valid=lgb.Dataset(x.iloc[iv],label=y[iv],reference=train)
            model=lgb.train(params,train,num_boost_round=args.max_rounds,valid_sets=[valid],feval=feval,
                            callbacks=[lgb.early_stopping(75,verbose=False)])
            p=model.predict(x.iloc[iv],num_iteration=model.best_iteration,validate_features=True)
            prob[iv]=p;rounds.append(model.best_iteration)
            metrics.append(medir(datos.iloc[iv],p))
            audit.append(dict(trial=trial.number,fold=fold,filas_train=len(it),filas_eval=len(iv),max_mes_train=int(datos.foto_mes.iloc[it].max()),best_iter=model.best_iteration))
        df=datos.iloc[ivabril][KEYS+['clase_ternaria']].reset_index(drop=True)
        df['probabilidad']=prob[ivabril];df.to_csv(out/f'trial{trial.number}_oof_abril.csv',index=False)
        met=medir(df,df.probabilidad)
        trial.set_user_attr('rounds',int(np.median(rounds)))
        trial.set_user_attr('fold_rounds',rounds);trial.set_user_attr('fold_metrics',metrics)
        trial.set_user_attr('ganancia_25pct',met['ganancia_25pct'])
        pd.DataFrame(audit).to_csv(out/'auditoria_busqueda.csv',index=False)
        print('Trial',trial.number,'ganancia',met['ganancia'],'25%',met['ganancia_25pct'],'rounds',trial.user_attrs['rounds'],flush=True)
        return float(met['ganancia'])
    storage='sqlite:///'+(out/'estudio.db').resolve().as_posix()
    study=optuna.create_study(study_name='combinado',storage=storage,direction='maximize',load_if_exists=True,
                              sampler=optuna.samplers.TPESampler(seed=214363))
    if not study.trials:
        study.enqueue_trial({**{k:old['params'][k] for k in ['num_leaves','learning_rate','min_data_in_leaf','feature_fraction','bagging_fraction']},'lambda_l1':0,'lambda_l2':0})
    complete=[t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
    if len(complete)<args.trials:
        study.optimize(objective,n_trials=args.trials-len(complete))
    study.trials_dataframe().to_csv(out/'trials.csv',index=False)
    best=sorted([t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE],key=lambda t:(-t.value,t.number))[:5]
    meta.update(estado='seleccion_mayo',top5=[t.number for t in best]);save(out/'manifest.json',meta)
    baseline=pd.read_csv(reference/'predicciones_mayo.csv')
    iv=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy());it=np.flatnonzero(datos.foto_mes.eq(202104).to_numpy())
    template=datos.iloc[iv][KEYS+['clase_ternaria']].reset_index(drop=True)
    pd.testing.assert_frame_equal(template,baseline[template.columns])
    summary=[];single=[]
    def evaluate(name,params,rounds,indices,tab=False):
        pred=template.copy()
        for seed in seeds:
            cache=out/'cache'/f'{name}_{seed}.npy'
            modelpath=out/'modelos'/f'{name}_{seed}.txt'
            if cache.exists():
                p=np.load(cache,allow_pickle=False)
            else:
                model=lgb.train(dict(params,seed=seed),lgb.Dataset(x.iloc[indices],label=y[indices]),num_boost_round=rounds)
                model.save_model(str(modelpath));p=model.predict(x.iloc[iv],validate_features=True)
                np.save(cache,p,allow_pickle=False)
            pred[f'p_seed{seed}']=p
            single.append(dict(configuracion=name,seed=seed,**medir(pred,p)))
            print(name,'semilla',seed,'completa',flush=True)
        pred['p_lightgbm']=pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
        if tab:
            pred['p_tabpfn']=baseline.p_tabpfn
            pred['p_mezcla']=(pred.p_lightgbm+pred.p_tabpfn)/2
        pred.to_csv(out/f'{name}_mayo.csv',index=False)
        return pred
    for t in best:
        params=dict(base,**t.params);rounds=t.user_attrs['rounds']
        pred=evaluate(f'trial{t.number}',params,rounds,it,True)
        ind=[r['ganancia'] for r in single if r['configuracion']==f'trial{t.number}']
        summary.append(dict(trial=t.number,rounds=rounds,ganancia_cv_abril=t.value,
                            media_individual=float(np.mean(ind)),std_individual=float(np.std(ind,ddof=1)),
                            **medir(pred,pred.p_lightgbm),ganancia_mezcla=medir(pred,pred.p_mezcla)['ganancia']))
        pd.DataFrame(summary).to_csv(out/'seleccion_mayo.csv',index=False)
        pd.DataFrame(single).to_csv(out/'semillas_mayo.csv',index=False)
    selected=sorted(summary,key=lambda r:(-r['ganancia'],-r['media_individual'],r['std_individual'],r['trial']))[0]
    winner=next(t for t in best if t.number==selected['trial'])
    params=dict(base,**winner.params);rounds=winner.user_attrs['rounds']
    control=medir(baseline,baseline.p_lightgbm)
    elegido=dict(target='bajas',trial=winner.number,params=params,num_boost_round=rounds,resultados_mayo=selected)
    save(out/'configuracion_elegida.json',elegido)
    meta.update(estado='chequeo_temporal',elegido=elegido,control_mayo=control,mejora_mayo=selected['ganancia']-control['ganancia']);save(out/'manifest.json',meta)
    checks=[]
    imarch=np.flatnonzero(datos.foto_mes.eq(202103).to_numpy())
    for name,p,r in [('control_temporal',old['params'],old['num_boost_round']),('ganador_temporal',params,rounds)]:
        pred=evaluate(name,p,r,imarch)
        checks.append(dict(configuracion=name,**medir(pred,pred.p_lightgbm)))
    pd.DataFrame(single).to_csv(out/'semillas_mayo.csv',index=False)
    pd.DataFrame(checks).to_csv(out/'chequeo_temporal.csv',index=False)
    meta['chequeo_temporal']=checks
    # Congelado antes de consultar junio para el entrenamiento final.
    if selected['ganancia']>control['ganancia']:
        name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('LightGBMOptunaCombinado5_%Y%m%d_%H%M%S')
        candidate=SAL/'candidatos_pendientes'/name;candidate.mkdir(parents=True)
        (candidate/'modelos').mkdir()
        with duckdb.connect() as con:
            con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
            all_data=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202105,202106) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos ORDER BY foto_mes,numero_de_cliente').df()
        hist=agregar_historicas_ampliadas(all_data[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
        hc=[c for c in hist if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
        all_data=all_data.merge(hist[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
        train=all_data.loc[all_data.foto_mes.isin([202105,202106])]
        august=all_data.loc[all_data.foto_mes.eq(202108)].reset_index(drop=True)
        assert train.clase_ternaria.isin(['BAJA+1','BAJA+2','CONTINUA']).all() and august.clase_ternaria.isna().all()
        xt=preparar(train,cols)[0];xp=preparar(august,cols)[0]
        yf=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
        pred=august[KEYS].copy()
        for seed in seeds:
            model=lgb.train(dict(params,seed=seed),lgb.Dataset(xt,label=yf),num_boost_round=rounds)
            model.save_model(str(candidate/'modelos'/f'seed{seed}.txt'))
            pred[f'p_seed{seed}']=model.predict(xp,validate_features=True)
            print('Final agosto semilla',seed,'completa',flush=True)
        pred['p_lightgbm']=pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
        tb=SAL/'01_entregas_bot/1_TabPFNHist_20261004_223836/predicciones_agosto.csv'
        tab=pd.read_csv(tb);pd.testing.assert_frame_equal(pred[KEYS],tab[KEYS])
        pred['p_tabpfn']=tab.probabilidad
        pred['p_mezcla']=(pred.p_lightgbm+pred.p_tabpfn)/2
        pred.to_csv(candidate/'predicciones_agosto.csv',index=False)
        files=[]
        for variante in ['lightgbm','mezcla']:
            adj=candidate/f'adjuntos_{variante}';adj.mkdir()
            for seed in seeds:
                col=f'p_seed{seed}'
                prob=pred[col] if variante=='lightgbm' else (pred[col]+pred.p_tabpfn)/2
                sel=pred.loc[prob>.025,KEYS].copy();sel['probabilidad']=prob[prob>.025]
                sel=sel.sort_values(['probabilidad','numero_de_cliente'],ascending=[False,True])
                file=adj/f'{name}_{variante}_seed{seed}.csv'
                file.write_text(''.join(f'{int(i)}\n' for i in sel.numero_de_cliente),encoding='ascii')
                files.append(dict(variante=variante,seed=seed,archivo=str(file.relative_to(candidate)),contactos=len(sel),sha256=sha(file)))
            (candidate/f'MENSAJE_{variante.upper()}.txt').write_text('submit '+name+'_'+variante,encoding='ascii')
        cm=dict(estado='preparado_pendiente',enviado=False,semillas=seeds,features=cols,elegido=elegido,
                fuente_desarrollo=str(out),train=[202105,202106],futuro=202108,umbral=.025,operador='>',
                archivos=files,api=False,creditos=0,fuente_tabpfn=str(tb),fuente_tabpfn_sha256=sha(tb),
                limitaciones=meta['limitaciones'],hashes={p.name:sha(p) for p in candidate.glob('*.csv')})
        save(candidate/'manifest.json',cm)
        (candidate/'ESTADO_ENVIO.txt').write_text('PENDIENTE. Candidato local elegido por mayo reutilizado, no garantia agosto.\nLightGBM y mezcla son lotes separados.\n',encoding='utf-8')
        meta['candidato']=str(candidate)
    meta.update(estado='completo',archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    save(out/'manifest.json',meta)
    print('ELEGIDO:',elegido,flush=True);print('CONTROL:',control,'\nTEMPORAL:',checks,flush=True)


if __name__=='__main__':
    main()
