"""Cinco LightGBM189 finales abril+mayo->agosto + TabPFN202 guardado 50/50."""
import argparse
import hashlib
import importlib.metadata
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
SOURCE=SAL/'01_entregas_bot/8_EnsembleAbrilMayo5_20261005_220000'
LOCAL=SAL/'features_local_20261006_140702'
D15=SAL/'01_entregas_bot/15_EnsembleCatBoost5_20261006_085026'
KEYS=['numero_de_cliente','foto_mes']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def matrix_sha(x):
    return hashlib.sha256(x.to_numpy(dtype=np.float32).tobytes()).hexdigest()


def verificar15():
    m=json.loads((D15/'manifest.json').read_text(encoding='utf-8'))
    assert m['entrega']==15 and m['estado']=='completo_verificado_preparado_pendiente'
    assert m['train_final']==[202104,202105] and m['futuro']==202108
    assert json.loads((D15/'verificacion_independiente.json').read_text())['estado']=='verificado'
    assert len(m['archivos'])==5
    for name,h in m['documentos_sha256'].items(): assert sha(D15/name)==h
    for name,h in m['archivos_sha256'].items(): assert sha(D15/name)==h
    for name,h in m['modelos_sha256'].items(): assert sha(D15/'modelos_catboost'/name)==h
    for name,h in m['firma']['codigo_sha256'].items(): assert sha(Path(__file__).parent/name)==h
    p=pd.read_csv(D15/'predicciones_agosto.csv')
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any()
    for entry in m['archivos']:
        seed=entry['seed'];score=.4*p[f'p_lgb_seed{seed}']+.4*p.p_tabpfn+.2*p[f'p_cat_seed{seed}']
        np.testing.assert_allclose(score,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        selected=p.loc[score>.025,KEYS].copy();selected['score']=score[score>.025]
        selected=selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=D15/entry['archivo']
        assert sha(path)==entry['sha256'] and len(selected)==entry['contactos']
        assert path.read_text(encoding='ascii')==''.join(f'{int(i)}\n' for i in selected.numero_de_cliente)
    assert (D15/'MENSAJE_SEMILLAS.txt').read_text().strip()=='submit '+m['submit']
    return dict(estado='verificado_sin_reentrenar',carpeta=str(D15.relative_to(ROOT)),
                manifest_sha256=sha(D15/'manifest.json'),adjuntos=5,submit=m['submit'])


def cargar():
    ref=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8-sig'))
    lm=json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8'))
    assert lm['estado']=='completo_verificado'
    assert json.loads((LOCAL/'verificacion_independiente.json').read_text())['estado']=='verificado'
    assert ref['train_final']==[202104,202105] and ref['futuro']==202108
    spec=ref['firma']['elegido'];seeds=ref['firma']['semillas'];basecols=ref['firma']['features']
    cols=lm['firma']['variants']['historia_1_mes']['features']
    assert lm['firma']['params']==spec['params'] and lm['firma']['rounds']==spec['num_boost_round']==273
    assert spec['target']=='bajas' and seeds==lm['firma']['seeds']==[541440,408476,741961,248865,717444]
    assert lm['firma']['base_features']==basecols and len(basecols)==202 and len(cols)==189
    removed=['historial_meses_previos_3']+[prefix+c for c in HISTORICAS for prefix in
                 ['media_previa_3_','delta_media_previa_3_','observaciones_previas_3_']]
    assert len(removed)==13 and cols==[c for c in basecols if c not in removed]
    for name in ['features.py','baseline.py']:
        assert sha(Path(__file__).parent/name)==ref['firma']['codigo'][name]==lm['firma']['codigo_sha256'][name]
    for name,h in lm['archivos_sha256'].items(): assert sha(LOCAL/name)==h
    metrics=pd.read_csv(LOCAL/'comparacion_media5.csv').set_index('variante')
    assert metrics.loc['historia_1_mes','ganancia']==266420000
    assert metrics.loc['historia_1_mes','semillas_mejoran']==5 and metrics.loc['control_entrega8','ganancia']==258368000
    assert sha(SOURCE/'predicciones_agosto.csv')==ref['predicciones_sha256']
    source=pd.read_csv(SOURCE/'predicciones_agosto.csv')
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) '
                    'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
                    'WHERE foto_mes IN (202104,202105,202108) ORDER BY foto_mes,numero_de_cliente').df()
        history=con.sql('SELECT '+','.join(KEYS+HISTORICAS+HISTORICAS_EXTRA)+
                        ' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any() and not history.duplicated(KEYS).any()
    hist=agregar_historicas_ampliadas(history)
    hc=[c for c in hist if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA];assert len(hc)==50
    raw=raw.merge(hist[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.isin([202104,202105])].reset_index(drop=True)
    august=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327052 and len(august)==164647 and august.clase_ternaria.isna().all()
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    pd.testing.assert_frame_equal(august[KEYS],source[KEYS])
    assert not source.numero_de_cliente.duplicated().any()
    assert matrix_sha(preparar(train,basecols)[0])==ref['firma']['matriz_train_sha256']
    assert matrix_sha(preparar(august,basecols)[0])==ref['firma']['matriz_agosto_sha256']
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    y2=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(y2.tobytes()).hexdigest()==ref['firma']['target_tabpfn_sha256']
    return ref,lm,cols,removed,seeds,preparar(train,cols)[0],preparar(august,cols)[0],y,august[KEYS],source


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    audit15=verificar15()
    ref,lm,cols,removed,seeds,xt,xp,y,keys,source=cargar()
    sig=dict(params=ref['firma']['elegido']['params'],rounds=273,seeds=seeds,features=cols,removed_features=removed,
        target='BAJA+1/BAJA+2',train=[202104,202105],futuro=202108,
        source_predictions_sha256=sha(SOURCE/'predicciones_agosto.csv'),
        source_manifest_sha256=sha(SOURCE/'manifest.json'),local_manifest_sha256=sha(LOCAL/'manifest.json'),
        local_verification_sha256=sha(LOCAL/'verificacion_independiente.json'),
        matriz_train_sha256=matrix_sha(xt),matriz_agosto_sha256=matrix_sha(xp),
        target_train_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['66_preparar_entrega_hist189.py','features.py','baseline.py']},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','pandas','numpy','duckdb']})
    if args.reanudar:
        out=args.reanudar.resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        assert m['firma']==sig and not m['enviado']
    else:
        bot=SAL/'01_entregas_bot'
        assert max(int(p.name.split('_')[0]) for p in bot.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())==15
        name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHist1895_%Y%m%d_%H%M%S')
        out=bot/f'16_{name}';out.mkdir()
        m=dict(estado='entrenando_lightgbm_final',entrega=16,submit=name+'_semillas',enviado=False,firma=sig,
            train_final=[202104,202105],futuro=202108,filas_train=len(xt),filas_agosto=len(xp),
            features_lightgbm=189,features_tabpfn=202,umbral=.025,operador='>',pesos=dict(lightgbm=.5,tabpfn=.5),
            target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',api=False,creditos=0,
            nuevos_fits_lightgbm=5,nuevos_fits_tabpfn=0,fit_eval_set=False,etiquetas_extraidas=[202104,202105],
            junio_validacion=False,junio_julio_solo_historia=True,fuente_tabpfn=str(SOURCE.relative_to(ROOT)),
            fuente_validacion=str(LOCAL.relative_to(ROOT)),verificacion_entrega15=audit15,modelos_completados=[],
            validacion_local=dict(control_total=258368000,control_25pct=64592000,candidato_total=266420000,
                candidato_25pct=66605000,delta_total=8052000,delta_25pct=2013000,semillas_mejoran=5,partes_mejoran=4),
            limitaciones='Mayo y semillas reutilizados; no test independiente ni garantia de mejora publica. '
                         'Historia agosto tiene mayor cobertura que abril/mayo. Mezcla de targets distintos es score, no P(BAJA+2) calibrada. '
                         'Solo se retiran13resumenes; relativos conservados. Sin nuevos rangos, CatBoost, tuning, cambio de pesos/corte ni envio automatico.')
    save(out/'manifest.json',m)
    md=out/'modelos';md.mkdir(exist_ok=True)
    pred=keys.copy();pred['p_tabpfn']=source.p_tabpfn
    print('Entrega15 verificada; salida entrega16:',out,flush=True)
    for seed in seeds:
        path=md/f'seed{seed}.txt';start=time.perf_counter()
        if path.exists():model=lgb.Booster(model_file=str(path))
        else:
            model=lgb.train(dict(sig['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=273)
            model.save_model(str(path))
        assert model.feature_name()==cols and model.num_trees()==273
        pred[f'p_lgb_seed{seed}']=model.predict(xp,validate_features=True)
        loaded=lgb.Booster(model_file=str(path))
        np.testing.assert_allclose(loaded.predict(xp,validate_features=True),pred[f'p_lgb_seed{seed}'],rtol=0,atol=0)
        pred[f'score_seed{seed}']=(pred[f'p_lgb_seed{seed}']+pred.p_tabpfn)/2
        pred.to_csv(out/'predicciones_agosto.csv',index=False)
        m['modelos_completados']=[int(c.removeprefix('p_lgb_seed')) for c in pred if c.startswith('p_lgb_seed')]
        m.setdefault('tiempos',[]).append(dict(seed=seed,segundos=time.perf_counter()-start));save(out/'manifest.json',m)
        print('LightGBM189',seed,'completo',flush=True)
    values=pred.drop(columns=KEYS).to_numpy()
    assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    adj=out/'adjuntos_semillas';adj.mkdir(exist_ok=True);files=[];changes=[]
    for seed in seeds:
        score=pred[f'score_seed{seed}'];sel=score>.025
        selected=pred.loc[sel,KEYS].copy();selected['score']=score[sel]
        selected=selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=adj/f"{m['submit']}_seed{seed}.csv"
        path.write_text(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente),encoding='ascii')
        assert len(selected)==selected.numero_de_cliente.nunique()
        files.append(dict(seed=seed,archivo=str(path.relative_to(out)),contactos=len(selected),sha256=sha(path)))
        old=(source[f'p_seed{seed}']+source.p_tabpfn)/2>.025
        changes.append(dict(seed=seed,contactos_entrega8=int(old.sum()),contactos_nuevos=int(sel.sum()),
                            agregados=int((sel&~old).sum()),retirados=int((old&~sel).sum())))
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    (out/'MENSAJE_SEMILLAS.txt').write_text('submit '+m['submit']+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO, PENDIENTE ENVIO MANUAL POR TOMAS.\n'
        'Una corrida exclusiva con cinco CSV de adjuntos_semillas.\nResultado publico desconocido.\n',encoding='utf-8')
    m.update(estado='preparado_pendiente_verificacion',archivos=files,
             modelos_sha256={p.name:sha(p) for p in md.glob('*.txt')},
             archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    save(out/'manifest.json',m)
    print('Cinco adjuntos generados; pendiente verificacion independiente.',flush=True)
    print('submit '+m['submit'],flush=True)


if __name__=='__main__':main()
