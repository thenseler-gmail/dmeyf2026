"""Pipeline reanudable: ablaciones16, Optuna AUC, ensemble y scoring final.

No llama API ni envía al Bot. Junio sólo se lee con etiquetas en etapa final.
"""
import argparse
import hashlib
import importlib
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import roc_auc_score
from baseline import preparar
from calidad_datos import corregir_datos
from features_catedra import construir, ORDEN2, verificar, KEYS, FUENTES

TP = Path(__file__).resolve().parent
ROOT = TP.parent
SAL = TP / 'salidas'
OLD = SAL / 'features_local_20261006_140702'
SEEDS = [541440, 408476, 741961, 248865, 717444]
FIXED = dict(objective='binary', metric='auc', max_bin=31, min_data_in_leaf=0,
             feature_fraction=.50, feature_fraction_bynode=.20, learning_rate=.005,
             feature_pre_filter=False, num_threads=4, verbosity=-1,
             deterministic=True, force_col_wise=True, seed=SEEDS[0])


def save(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def metric(y, q, ids, n=None):
    mask = np.asarray(q) > .025
    if n is not None:
        mask = np.zeros(len(q), dtype=bool)
        mask[np.lexsort((np.asarray(ids), -np.asarray(q)))[:n]] = True
    tp = int((mask & np.asarray(y)).sum()); contactos = int(mask.sum())
    gain = tp * 1100000 - contactos * 27500
    return dict(contactos=contactos, tp=tp, fp=contactos-tp,
                ganancia=gain, ganancia_25pct=gain/4)


def fuentes():
    m = json.loads((OLD / 'manifest.json').read_text(encoding='utf-8'))
    cols = m['firma']['variants']['historia_1_mes']['features']
    assert len(cols) == 189
    return m, cols


def leer(final=False):
    config = json.loads((TP/'config.json').read_text(encoding='utf-8'))
    meses = '202103,202104,202105,202106,202108' if final else '202103,202104,202105'
    etiquetas = '202103,202104,202105,202106' if final else '202103,202104,202105'
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw = con.sql(f'SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN ({etiquetas}) '
                      f'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
                      f'WHERE foto_mes IN ({meses}) ORDER BY foto_mes,numero_de_cliente').df()
        if final:
            hist = con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos '
                           'ORDER BY foto_mes,numero_de_cliente').df()
        else:
            hist = raw[KEYS+FUENTES].copy()
    # Corrección se aplica sobre la tabla completa antes del join de históricos.
    raw, audit = corregir_datos(raw)
    h, _ = construir(hist)
    nuevos = [c for c in h if c not in KEYS+FUENTES]
    datos = raw.merge(h[KEYS+nuevos], on=KEYS, sort=False, validate='one_to_one')
    pd.testing.assert_frame_equal(datos[KEYS], raw[KEYS])
    return datos, audit


def fit_cached(path, xt, y, xv, params, rounds, valid_y=None):
    start = time.perf_counter()
    if path.exists():
        model = lgb.Booster(model_file=str(path))
    else:
        train = lgb.Dataset(xt, label=y)
        kwargs = {}
        if valid_y is not None:
            kwargs = dict(valid_sets=[lgb.Dataset(xv, label=valid_y, reference=train)],
                          callbacks=[lgb.early_stopping(500, verbose=False)])
        model = lgb.train(params, train, num_boost_round=rounds, **kwargs)
        model.save_model(str(path))
    assert model.feature_name() == list(xt)
    q = model.predict(xv, validate_features=True)
    # Saved model is the actual model used for the prediction.
    reload = lgb.Booster(model_file=str(path))
    np.testing.assert_allclose(q, reload.predict(xv, validate_features=True), rtol=0, atol=0)
    return q, model.num_trees(), time.perf_counter()-start


def ablation(out):
    ref, seeds, train, valid, xt, xv, unused = importlib.import_module('63_experimentos_features_local').cargar()
    meta, cols = fuentes()
    base = pd.read_csv(OLD/'historia_1_mes/predicciones_mayo.csv')
    pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']], base[KEYS+['clase_ternaria']])
    for s in seeds:
        model = lgb.Booster(model_file=str(OLD/'historia_1_mes'/f'seed{s}.txt'))
        assert sha(OLD/'historia_1_mes'/f'seed{s}.txt') == meta['modelos_sha256'][str(Path('historia_1_mes')/f'seed{s}.txt')]
        np.testing.assert_allclose(model.predict(xv[cols], validate_features=True), base[f'p_seed{s}'], atol=1e-15, rtol=0)
    data, audit = leer()
    tr = data[data.foto_mes.eq(202104)].reset_index(drop=True)
    va = data[data.foto_mes.eq(202105)].reset_index(drop=True)
    pd.testing.assert_frame_equal(va[KEYS+['clase_ternaria']],base[KEYS+['clase_ternaria']])
    y = tr.clase_ternaria.ne('CONTINUA').astype(int)
    yv = va.clase_ternaria.eq('BAJA+2').to_numpy()
    pred = base[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy()
    rows=[]
    for name, features in [('A0_control16',cols), ('A1_correccion',cols), ('A2_orden2',cols+ORDEN2)]:
        vd=out/name; vd.mkdir(exist_ok=True)
        tx=preparar(tr,features)[0];vx=preparar(va,features)[0]
        for s in seeds:
            if name=='A0_control16': q=base[f'p_seed{s}'].to_numpy(); seconds=0
            else:
                print('Fit',name,s,flush=True)
                q, rounds, seconds = fit_cached(vd/f'seed{s}.txt',tx,y,vx,dict(ref['elegido']['params'],seed=s),273)
                assert rounds==273
            pred[f'{name}_seed{s}']=q
            for blend, score in [('lgb',q),('mix50',(q+base.p_tabpfn)/2)]:
                rows.append(dict(variante=name,tipo=blend,seed=s,segundos_fit=seconds,
                                 **metric(yv,score,va.numero_de_cliente)))
        pred.to_csv(out/'predicciones_ablacion_mayo.csv',index=False)
        pd.DataFrame(rows).to_csv(out/'resultados_ablacion_semillas.csv',index=False)
    summary=pd.DataFrame(rows).groupby(['variante','tipo'])[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    assert summary.loc[('A0_control16','mix50'),'ganancia']==266420000
    summary.to_csv(out/'resumen_ablacion.csv')
    # Payload local concreto para cotización posterior; no envío en este script.
    tabcols=list(xt)+ORDEN2
    assert len(tabcols)==226
    np.savez_compressed(out/'tabpfn226_local.npz', train=preparar(tr,tabcols)[0].to_numpy(dtype=np.float32),
                        valid=preparar(va,tabcols)[0].to_numpy(dtype=np.float32),
                        target=tr.clase_ternaria.eq('BAJA+2').astype(np.int64).to_numpy())
    save(out/'tabpfn226_payload.json',dict(features=tabcols,filas_train=len(tr),filas_valid=len(va),
         train=[202104],eval=202105,target='BAJA+2',ids=False,mes=False,etiquetas_mayo=False,
         archivo_sha256=sha(out/'tabpfn226_local.npz'),enviado=False,requiere_autorizacion=True))
    save(out/'ablacion_estado.json',dict(estado='completo_verificado',auditoria=audit,
                                       resumen=summary.reset_index().to_dict('records')))
    print(summary.to_string(),flush=True)


def search(out,trials):
    data,audit=leer();unused,cols=fuentes();cols=cols+ORDEN2
    tr=data[data.foto_mes.isin([202103,202104])].reset_index(drop=True)
    va=data[data.foto_mes.eq(202105)].reset_index(drop=True)
    for frame in [tr,va]:assert frame.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(tr,cols)[0];xv=preparar(va,cols)[0]
    yt=tr.clase_ternaria.ne('CONTINUA').astype(int);yv=va.clase_ternaria.ne('CONTINUA').astype(int)
    base=pd.read_csv(OLD/'historia_1_mes/predicciones_mayo.csv')
    pd.testing.assert_frame_equal(va[KEYS+['clase_ternaria']],base[KEYS+['clase_ternaria']])
    md=out/'optuna_modelos';md.mkdir(exist_ok=True)
    study=optuna.create_study(study_name='catedra_auc',storage='sqlite:///'+str(out/'optuna.db'),
          direction='maximize',load_if_exists=True,sampler=optuna.samplers.TPESampler(seed=214363))
    def objective(t):
        rounds=t.suggest_int('num_iterations',1000,12000,step=500)
        params=dict(FIXED,num_leaves=t.suggest_int('num_leaves',16,256),
                    min_sum_hessian_in_leaf=t.suggest_float('min_sum_hessian_in_leaf',1,100,log=True))
        q,effective,seconds=fit_cached(md/f'trial{t.number}.txt',xt,yt,xv,params,rounds,yv)
        np.save(md/f'trial{t.number}_mayo.npy',q)
        auc=float(roc_auc_score(yv,q))
        t.set_user_attr('effective_rounds',effective);t.set_user_attr('seconds',seconds)
        t.set_user_attr('gain_baja2',metric(va.clase_ternaria.eq('BAJA+2'),q,va.numero_de_cliente))
        print('Trial',t.number,'AUC',auc,'trees',effective,'seconds',seconds,flush=True)
        return auc
    done=len([t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE])
    if done<trials:study.optimize(objective,n_trials=trials-done,gc_after_trial=True)
    study.trials_dataframe().to_csv(out/'optuna_trials.csv',index=False)
    winners=sorted([t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE],key=lambda t:(-t.value,t.number))[:10]
    assert len(winners)==10 and len({json.dumps(t.params,sort_keys=True) for t in winners})==10
    specs=[dict(trial=t.number,auc=t.value,params=t.params,effective_rounds=t.user_attrs['effective_rounds']) for t in winners]
    save(out/'top10_congelado.json',dict(features=cols,fixed=FIXED,configuraciones=specs,
         train=[202103,202104],eval=202105,undersampling=False,seleccion='AUC target combinado',
         early_stopping=500,limitacion='Mayo reutilizado; ensemble evaluado en la misma validación de selección'))
    q=np.mean([np.load(md/f'trial{t.number}_mayo.npy') for t in winners],axis=0)
    pred=base[KEYS+['clase_ternaria','p_tabpfn']].copy();pred['p_lgb_top10']=q
    pred['score_mix50']=(q+pred.p_tabpfn)/2;pred.to_csv(out/'predicciones_top10_mayo.csv',index=False)
    rows=[]
    for kind,s in [('lgb_top10',q),('mix_top10_tab202',(q+pred.p_tabpfn)/2)]:
        for n in [None,10000,10500,11000,11500,12000]:
            rows.append(dict(variante=kind,corte='p>.025' if n is None else 'top'+str(n),
                             **metric(va.clase_ternaria.eq('BAJA+2'),s,va.numero_de_cliente,n)))
    pd.DataFrame(rows).to_csv(out/'cortes_top10_mayo.csv',index=False)
    save(out/'optuna_estado.json',dict(estado='completo_verificado',filas_train=len(tr),filas_eval=len(va),
             undersampling=False,auc_ensemble=float(roc_auc_score(yv,q)),api=False,creditos=0,submits=0))


def final(out):
    specs=json.loads((out/'top10_congelado.json').read_text(encoding='utf-8'))
    data,audit=leer(final=True);cols=specs['features']
    tr=data[data.foto_mes.isin([202103,202104,202105,202106])].reset_index(drop=True)
    august=data[data.foto_mes.eq(202108)].reset_index(drop=True)
    assert tr.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    assert august.clase_ternaria.isna().all() and august.numero_de_cliente.is_unique
    xt=preparar(tr,cols)[0];xp=preparar(august,cols)[0];y=tr.clase_ternaria.ne('CONTINUA').astype(int)
    md=out/'modelos_finales';md.mkdir(exist_ok=True);pred=august[KEYS].copy()
    for t in specs['configuraciones']:
        params={k:v for k,v in t['params'].items() if k!='num_iterations'}
        print('Final trial',t['trial'],flush=True)
        q,rounds,seconds=fit_cached(md/f"trial{t['trial']}.txt",xt,y,xp,dict(FIXED,**params),t['effective_rounds'])
        pred[f"p_trial{t['trial']}"]=q
        pred.to_csv(out/'predicciones_top10_agosto.csv',index=False)
    pred['p_lgb_top10']=pred.filter(like='p_trial').mean(axis=1)
    old=pd.read_csv(SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235/predicciones_agosto.csv')
    pd.testing.assert_frame_equal(pred[KEYS],old[KEYS])
    pred['p_tab202']=old.p_tabpfn;pred['score_mix50']=(pred.p_lgb_top10+pred.p_tab202)/2
    pred.to_csv(out/'predicciones_top10_agosto.csv',index=False)
    save(out/'final_estado.json',dict(estado='completo_verificado',train=[202103,202104,202105,202106],
         filas_train=len(tr),filas_agosto=len(august),configuraciones=10,undersampling=False,
         tabpfn='Guardado16 abril+mayo; todavía no reentrenado',auditoria=audit,
         api=False,creditos=0,enviado=False,predicciones_sha256=sha(out/'predicciones_top10_agosto.csv')))


def informe(out):
    lines=['# Recomendaciones cátedra: avance y resultados','',
           'Junio no se usa para selección. Mayo reutilizado: no test independiente. '
           'Ganancia evaluada por BAJA+2; Optuna maximiza AUC del target combinado. '
           'El TabPFN de control conserva202 variables y no fue actualizado.','']
    for file in ['resumen_ablacion.csv','cortes_top10_mayo.csv']:
        path=out/file
        if path.exists():
            frame=pd.read_csv(path)
            lines += ['## '+file,'','```text',frame.to_string(index=False),'```','']
    lines += ['## Estado','']
    for file in ['ablacion_estado.json','optuna_estado.json','final_estado.json']:
        if (out/file).exists():lines += [f'- {file}: completo verificado']
    lines += ['','TabPFN226 local está preparado para cotización/autorización. '
              'No se envió ningún payload ni se consumieron créditos. '
              'No se creó ni envió una entrega al Bot automáticamente.']
    (out/'MINI_INFORME.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path)
    ap.add_argument('--etapa',choices=['ablacion','optuna','final','todo'],default='ablacion')
    ap.add_argument('--trials',type=int,default=20);args=ap.parse_args()
    assert args.trials>=10
    out=args.salida or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('catedra_implementacion_%Y%m%d_%H%M%S')
    out.mkdir(exist_ok=bool(args.salida));print('Salida:',out,flush=True)
    checks=verificar();save(out/'verificacion_features.json',checks)
    codigo={f:sha(TP/f) for f in ['89_catedra_pipeline.py','features_catedra.py','calidad_datos.py','baseline.py','features.py']}
    manifest=out/'manifest.json'
    if manifest.exists(): assert json.loads(manifest.read_text(encoding='utf-8'))['codigo']==codigo
    else:save(manifest,dict(estado='implementado_ejecutando',codigo=codigo,api=False,creditos=0,submits=0))
    etapas=['ablacion','optuna','final'] if args.etapa=='todo' else [args.etapa]
    for etapa in etapas:
        if etapa=='ablacion':ablation(out)
        elif etapa=='optuna':search(out,args.trials)
        else:final(out)
        informe(out)
    m=json.loads(manifest.read_text(encoding='utf-8'));m['ultima_etapa_completa']=etapas[-1]
    m['estado']='etapas_solicitadas_completas';save(manifest,m)


if __name__=='__main__':main()
