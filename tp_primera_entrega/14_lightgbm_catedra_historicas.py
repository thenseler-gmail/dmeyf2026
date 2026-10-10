"""LightGBM: dos targets, top 5, semillas y umbral fijo p > 0.025.

Abril: CV estratificada 5 splits 70/30. Mayo: seleccion top 5 con umbral fijo.
Junio: comprobacion exploratoria congelada. Agosto: 20 semillas, train mayo/junio.
Solo CPU local. No envia datos ni mensajes a servicios externos.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT = Path(__file__).resolve().parents[1]
BASE = dict(objective='binary', metric='None', boosting_type='gbdt',
            boost_from_average=True, feature_pre_filter=False, max_bin=31,
            bagging_freq=1, num_threads=4, verbosity=-1,
            deterministic=True, force_col_wise=True)


def guardar(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding='utf-8')


def etiquetas(df, target):
    if target == 'baja2':
        return df.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    return df.clase_ternaria.isin(['BAJA+1', 'BAJA+2']).astype(int).to_numpy()


def curva(prob, pagos, ids, cortes):
    orden = np.lexsort((ids, -prob))
    acumulada = np.cumsum(pagos[orden])
    return [int(acumulada[k-1]) for k in cortes]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--max-rounds', type=int, default=1000)
    parser.add_argument('--salida', type=Path, help='Reanudar estudios de esta carpeta.')
    parser.add_argument('--target', choices=['baja2', 'bajas', 'ambos'], default='ambos')
    parser.add_argument('--solo-seleccion', action='store_true', help='Finalizar en mayo, sin junio ni agosto.')
    args = parser.parse_args()
    if args.trials < 5 or args.max_rounds < 1:
        parser.error('Se necesitan al menos 5 trials y max-rounds positivo.')
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    out = args.salida or ROOT/config['salidas']/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('lgbm_catedra_hist_%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=True)
    np.random.seed(17)
    semillas = [int(s) for s in np.random.choice(1000000, size=50, replace=False)[:20]]
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        consulta = 'SELECT * FROM datos'
        if args.solo_seleccion:
            consulta += ' WHERE foto_mes <= 202105'
        datos = con.sql(consulta + ' ORDER BY foto_mes,numero_de_cliente').df()
    claves = ['numero_de_cliente', 'foto_mes']
    fuentes = HISTORICAS + HISTORICAS_EXTRA
    originales = [c for c in datos if c not in claves + ['clase_ternaria']]
    historia = datos[claves + fuentes].copy()
    historia[fuentes] = historia[fuentes].replace([np.inf,-np.inf],np.nan)
    historia = agregar_historicas_ampliadas(historia)
    nuevas = [c for c in historia if c not in claves + fuentes]
    datos = datos.merge(historia[claves+nuevas], on=claves, validate='one_to_one', sort=False)
    columnas = originales + nuevas
    meses = [202104,202105] if args.solo_seleccion else [202104,202105,202106,202108]
    frames = {m: datos.loc[datos.foto_mes.eq(m)].reset_index(drop=True) for m in meses}
    for m in [m for m in meses if m != 202108]:
        if frames[m].empty or not frames[m].clase_ternaria.isin(['BAJA+1','BAJA+2','CONTINUA']).all():
            raise ValueError(f'Etiquetas incompletas en {m}.')
    xs = {m: preparar(df,columnas)[0] for m,df in frames.items()}
    pagos = {m: np.where(frames[m].clase_ternaria.eq('BAJA+2'),1072500,-27500) for m in meses if m != 202108}
    cortes = []  # Protocolo vigente: siempre probabilidad > 0.025.
    manifest = dict(estado='busqueda', features=columnas, semillas=semillas,
        cv_mes=202104, seleccion_mes=202105, comprobacion_mes=202106,
        train_final=[202105,202106], futuro=202108, trials_por_target=args.trials,
        max_rounds=args.max_rounds, cortes=cortes, parametros_base=BASE,
        target_solicitado=args.target, solo_seleccion=args.solo_seleccion, umbral=0.025, operador='>',
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','optuna','pandas','numpy','duckdb','scikit-learn']},
        codigo_sha256={p:hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest()
                       for p in ['14_lightgbm_catedra_historicas.py','features.py','baseline.py']},
        notas='Umbral fijo p > 0.025 en todas las etapas. Early stopping por fold con ganancia BAJA+2 real para ambos targets; best_iter mediana de folds. Seleccion temporal en mayo con 3 semillas; junio expuesto es exploratorio.')
    if (out/'manifest.json').exists():
        previo=json.loads((out/'manifest.json').read_text())
        for k in ['codigo_sha256','versiones','max_rounds','features','semillas','target_solicitado','solo_seleccion']:
            if previo[k] != manifest[k]:
                raise ValueError('Reanudacion incompatible: '+k)
    guardar(out/'manifest.json',manifest)
    print('Artefactos:',out, '\nFeatures:',len(columnas),flush=True)
    candidatos=[]
    detalles=[]
    for target in (['baja2','bajas'] if args.target == 'ambos' else [args.target]):
        y=etiquetas(frames[202104],target)
        folds=list(StratifiedShuffleSplit(n_splits=5,test_size=0.3,random_state=semillas[0]).split(xs[202104],y))
        def objective(trial):
            params=dict(BASE, seed=semillas[0],
                num_leaves=trial.suggest_int('num_leaves',8,100),
                learning_rate=trial.suggest_float('learning_rate',0.005,0.3),
                min_data_in_leaf=trial.suggest_int('min_data_in_leaf',1,1000),
                feature_fraction=trial.suggest_float('feature_fraction',0.1,1.0),
                bagging_fraction=trial.suggest_float('bagging_fraction',0.1,1.0))
            gains=[]; rounds=[]
            for it,iv in folds:
                valid_pay=pagos[202104][iv]
                def feval(prob,data):
                    return 'ganancia',float(valid_pay[prob>0.025].sum()/0.3),True
                dt=lgb.Dataset(xs[202104].iloc[it],label=y[it])
                dv=lgb.Dataset(xs[202104].iloc[iv],label=y[iv],reference=dt)
                model=lgb.train(params,dt,num_boost_round=args.max_rounds,valid_sets=[dv],
                    feval=feval,callbacks=[lgb.early_stopping(int(50+5/params['learning_rate']),verbose=False)])
                rounds.append(model.best_iteration)
                gains.append(model.best_score['valid_0']['ganancia'])
            trial.set_user_attr('best_iter',int(np.median(rounds)))
            trial.set_user_attr('fold_rounds',rounds)
            return float(np.mean(gains))
        study=optuna.create_study(study_name=target,storage='sqlite:///'+(out/'estudios.db').resolve().as_posix(),
            direction='maximize',load_if_exists=True,sampler=optuna.samplers.TPESampler(seed=semillas[0]))
        completos=[t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
        if len(completos)<args.trials:
            study.optimize(objective,n_trials=args.trials-len(completos))
        study.trials_dataframe().to_csv(out/(target+'_trials.csv'),index=False)
        mejores=sorted([t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE],key=lambda t:t.value,reverse=True)[:5]
        for t in mejores:
            params=dict(BASE,**t.params)
            num=t.user_attrs['best_iter']
            matriz=[]
            for seed in semillas[:3]:
                model=lgb.train(dict(params,seed=seed),lgb.Dataset(xs[202104],label=y),num_boost_round=num)
                prob=model.predict(xs[202105])
                gains=[int(pagos[202105][prob>0.025].sum())]
                matriz.append(gains)
                detalles.append(dict(target=target,trial=t.number,seed=seed,contactos=int((prob>0.025).sum()),ganancia=gains[0],ganancia_25pct=gains[0]/4))
            media=np.mean(matriz,axis=0)
            pos=int(np.argmax(media))
            candidatos.append(dict(target=target,trial=t.number,params=params,num_boost_round=num,
                umbral=0.025,ganancia_mayo_media=float(media[pos]),
                ganancia_mayo_std=float(np.std(np.array(matriz)[:,pos],ddof=1))))
            print('Candidato:',target,t.number,'umbral 0.025',media[pos],flush=True)
        pd.DataFrame(detalles).to_csv(out/'seleccion_mayo_semillas.csv',index=False)
        guardar(out/'candidatos.json',candidatos)
    elegido=max(candidatos,key=lambda c:c['ganancia_mayo_media'])
    guardar(out/'configuracion_elegida.json',elegido)
    manifest.update(estado='configuracion_congelada',elegido=elegido)
    guardar(out/'manifest.json',manifest)
    if args.solo_seleccion:
        pred = frames[202105][claves + ['clase_ternaria']].copy()
        y = etiquetas(frames[202104], elegido['target'])
        for seed in semillas[:3]:
            model = lgb.train(dict(elegido['params'], seed=seed), lgb.Dataset(xs[202104], label=y),
                              num_boost_round=elegido['num_boost_round'])
            pred[f'p_seed{seed}'] = model.predict(xs[202105])
        pred['p_promedio'] = pred[[f'p_seed{s}' for s in semillas[:3]]].mean(axis=1)
        pred.to_csv(out/'predicciones_mayo.csv', index=False)
        manifest.update(estado='seleccion_completa', junio_evaluado=False, agosto_generado=False)
        guardar(out/'manifest.json', manifest)
        print('SELECCION COMPLETA:', elegido, '\nSalida:', out, flush=True)
        return
    # Junio diagnostico, sin cambiar la configuracion a partir de su resultado.
    train_j=pd.concat([frames[202104],frames[202105]],ignore_index=True)
    xj=preparar(train_j,columnas)[0]
    diagnostico=[]
    for seed in semillas[:3]:
        model=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xj,label=etiquetas(train_j,elegido['target'])),
                        num_boost_round=elegido['num_boost_round'])
        prob=model.predict(xs[202106])
        gain=int(pagos[202106][prob>0.025].sum())
        diagnostico.append(dict(seed=seed,ganancia=gain,ganancia_25pct=gain/4,contactos=int((prob>0.025).sum())))
    guardar(out/'diagnostico_junio.json',diagnostico)
    print('Junio exploratorio:',diagnostico,flush=True)
    train_f=pd.concat([frames[202105],frames[202106]],ignore_index=True)
    xf=preparar(train_f,columnas)[0]
    yf=etiquetas(train_f,elegido['target'])
    adjuntos=out/'adjuntos_zulip'; adjuntos.mkdir(exist_ok=True)
    proba=frames[202108][claves].copy()
    archivos=[]
    for seed in semillas:
        model=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xf,label=yf),num_boost_round=elegido['num_boost_round'])
        model.save_model(str(out/f'modelo_seed{seed}.txt'))
        prob=model.predict(xs[202108])
        if not np.isfinite(prob).all() or not ((prob>=0)&(prob<=1)).all():
            raise ValueError('Probabilidades invalidas.')
        proba[f'p_seed{seed}']=prob
        ids=frames[202108].numero_de_cliente.to_numpy()
        orden=np.lexsort((ids,-prob))
        elegidos=ids[orden[prob[orden]>0.025]]
        if len(set(elegidos))!=len(elegidos) or not np.equal(elegidos,np.floor(elegidos)).all():
            raise ValueError('IDs invalidos.')
        archivo=adjuntos/f'{out.name}_seed{seed}.csv'
        archivo.write_text(''.join(f'{int(i)}\n' for i in elegidos),encoding='ascii')
        lineas=archivo.read_text(encoding='ascii').splitlines()
        assert len(lineas)==int((prob>0.025).sum()) and all(s.isdigit() for s in lineas)
        archivos.append(dict(nombre=archivo.name,sha256=hashlib.sha256(archivo.read_bytes()).hexdigest()))
        proba.to_csv(out/'predicciones_agosto.csv',index=False)
        print('CSV agosto:',seed,len(lineas),flush=True)
    nombre='LGBMHist'+out.name.rsplit('_',2)[-2]+out.name.rsplit('_',1)[-1]
    (out/'MENSAJE_ZULIP.txt').write_text('submit '+nombre,encoding='ascii')
    manifest.update(estado='completo',archivos=archivos,submit=nombre,diagnostico_junio=diagnostico)
    guardar(out/'manifest.json',manifest)
    print('COMPLETO:',out,'\nMensaje: submit '+nombre,flush=True)


if __name__=='__main__':
    main()
