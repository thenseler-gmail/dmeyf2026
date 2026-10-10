"""Reconstruye historia de un mes por calendario, modelos y cinco CSV finales."""
import hashlib
import json
import sys
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar

ROOT=Path(__file__).resolve().parents[1]
KEYS=['numero_de_cliente','foto_mes']
SOURCES=['ctrx_quarter','mpayroll','mcuentas_saldo','cproductos','Visa_mconsumototal','Master_mconsumototal',
         'ctarjeta_visa_transacciones','ctarjeta_master_transacciones','chomebanking_transacciones',
         'cmobile_app_trx','ctarjeta_visa','ctarjeta_master']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'));sig=m['firma']
    assert m['entrega']==16 and m['train_final']==sig['train']==[202104,202105] and m['futuro']==sig['futuro']==202108
    assert m['features_lightgbm']==189 and m['features_tabpfn']==202
    assert m['pesos']==dict(lightgbm=.5,tabpfn=.5) and m['umbral']==.025 and m['operador']=='>'
    assert m['target_lightgbm']==sig['target']=='BAJA+1/BAJA+2' and m['target_tabpfn']=='BAJA+2'
    assert not m['api'] and m['creditos']==0 and not m['enviado'] and not m['fit_eval_set']
    assert m['nuevos_fits_lightgbm']==5 and m['nuevos_fits_tabpfn']==0
    assert m['etiquetas_extraidas']==[202104,202105] and not m['junio_validacion'] and m['junio_julio_solo_historia']
    for f,h in sig['codigo_sha256'].items():assert sha(Path(__file__).parent/f)==h
    for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
    src=ROOT/m['fuente_tabpfn'];local=ROOT/m['fuente_validacion']
    ref=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    lm=json.loads((local/'manifest.json').read_text(encoding='utf-8'))
    assert sha(src/'manifest.json')==sig['source_manifest_sha256']
    assert sha(local/'manifest.json')==sig['local_manifest_sha256']
    assert sha(local/'verificacion_independiente.json')==sig['local_verification_sha256']
    assert json.loads((local/'verificacion_independiente.json').read_text())['estado']=='verificado'
    assert ref['train_final']==[202104,202105] and ref['futuro']==202108
    assert sig['params']==ref['firma']['elegido']['params']==lm['firma']['params'] and sig['rounds']==273
    basecols=ref['firma']['features'];cols=sig['features'];seeds=sig['seeds']
    removed=[c for c in basecols if c=='historial_meses_previos_3' or c.startswith(
        ('media_previa_3_','delta_media_previa_3_','observaciones_previas_3_'))]
    assert len(removed)==13 and set(removed)==set(sig['removed_features'])
    assert cols==[c for c in basecols if c not in removed]==lm['firma']['variants']['historia_1_mes']['features']
    assert len(cols)==len(set(cols))==189 and len([c for c in cols if c.startswith('variacion_relativa_1_')])==12
    assert seeds==[541440,408476,741961,248865,717444]==lm['firma']['seeds']
    for f,h in lm['archivos_sha256'].items():assert sha(local/f)==h
    metrics=pd.read_csv(local/'comparacion_media5.csv').set_index('variante')
    assert metrics.loc['historia_1_mes','ganancia']==m['validacion_local']['candidato_total']==266420000
    assert m['validacion_local']['candidato_25pct']==266420000/4
    assert metrics.loc['historia_1_mes','semillas_mejoran']==5 and metrics.loc['historia_1_mes','partes_mejoran']==4
    assert metrics.loc['control_entrega8','ganancia']==258368000
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) '
            'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
            'WHERE foto_mes IN (202104,202105,202108) ORDER BY foto_mes,numero_de_cliente').df()
        hist=con.sql('SELECT '+','.join(KEYS+SOURCES)+
            ' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any() and not hist.duplicated(KEYS).any()
    # Implementacion independiente: un unico join del mes calendario anterior.
    d=pd.to_datetime(hist.foto_mes.astype(str),format='%Y%m')
    prev=hist[['numero_de_cliente']+SOURCES].rename(columns={c:'lag_1_'+c for c in SOURCES})
    prev['_ordinal']=d.dt.year*12+d.dt.month+1;prev['_presente']=1
    d=pd.to_datetime(raw.foto_mes.astype(str),format='%Y%m')
    current=raw[['numero_de_cliente']].copy();current['_ordinal']=d.dt.year*12+d.dt.month
    joined=current.merge(prev,on=['numero_de_cliente','_ordinal'],how='left',sort=False,validate='one_to_one')
    for c in SOURCES:
        lag=joined['lag_1_'+c].to_numpy();raw['lag_1_'+c]=lag
        raw['delta_1_'+c]=raw[c]-lag
        denominator=pd.Series(np.abs(lag),index=raw.index)
        raw['variacion_relativa_1_'+c]=(raw['delta_1_'+c]/denominator.where(denominator>0)).replace([np.inf,-np.inf],np.nan)
    raw['historial_mes_anterior_disponible']=joined['_presente'].fillna(0).astype(int).to_numpy()
    train=raw.loc[raw.foto_mes.isin([202104,202105])].reset_index(drop=True)
    august=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==m['filas_train']==327052 and len(august)==m['filas_agosto']==164647
    assert august.clase_ternaria.isna().all() and train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(train,cols)[0];xp=preparar(august,cols)[0]
    for x,key in [(xt,'matriz_train_sha256'),(xp,'matriz_agosto_sha256')]:
        assert hashlib.sha256(x.to_numpy(dtype=np.float32).tobytes()).hexdigest()==sig[key]
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    assert hashlib.sha256(y.tobytes()).hexdigest()==sig['target_train_sha256']
    y2=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(y2.tobytes()).hexdigest()==ref['firma']['target_tabpfn_sha256']
    assert sha(src/'predicciones_agosto.csv')==sig['source_predictions_sha256']==ref['predicciones_sha256']
    source=pd.read_csv(src/'predicciones_agosto.csv');p=pd.read_csv(out/'predicciones_agosto.csv')
    pd.testing.assert_frame_equal(p[KEYS],august[KEYS]);pd.testing.assert_frame_equal(p[KEYS],source[KEYS])
    assert not p.numero_de_cliente.duplicated().any()
    np.testing.assert_allclose(p.p_tabpfn,source.p_tabpfn,rtol=0,atol=1e-15)
    assert len(m['archivos'])==len(m['modelos_sha256'])==5
    assert {str(f.relative_to(out)) for f in (out/'adjuntos_semillas').glob('*.csv')}=={e['archivo'] for e in m['archivos']}
    assert {f.name for f in (out/'modelos').glob('*.txt')}=={f'seed{s}.txt' for s in seeds}
    changes=pd.read_csv(out/'cambios_contactos_agosto.csv').set_index('seed')
    for seed in seeds:
        modelpath=out/'modelos'/f'seed{seed}.txt';assert sha(modelpath)==m['modelos_sha256'][modelpath.name]
        model=lgb.Booster(model_file=str(modelpath))
        assert model.num_trees()==273 and model.feature_name()==cols and int(model.params['seed'])==seed
        assert model.params['objective']=='binary'
        for k in ['num_leaves','min_data_in_leaf','max_bin','bagging_freq']:
            assert int(model.params[k])==sig['params'][k]
        for k in ['learning_rate','feature_fraction','bagging_fraction']:
            assert float(model.params[k])==float(format(sig['params'][k],'.6g'))
        np.testing.assert_allclose(model.predict(xp,validate_features=True),p[f'p_lgb_seed{seed}'],rtol=0,atol=1e-15)
        score=(p[f'p_lgb_seed{seed}']+p.p_tabpfn)/2
        np.testing.assert_allclose(score,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        selected=p.loc[score>.025,KEYS].copy();selected['score']=score[score>.025]
        selected=selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        entry=next(e for e in m['archivos'] if e['seed']==seed);path=out/entry['archivo']
        assert path.name==f"{m['submit']}_seed{seed}.csv" and sha(path)==entry['sha256']
        assert path.read_text(encoding='ascii')==''.join(f'{int(i)}\n' for i in selected.numero_de_cliente)
        assert entry['contactos']==len(selected)==selected.numero_de_cliente.nunique()
        old=(source[f'p_seed{seed}']+source.p_tabpfn)/2>.025;new=score>.025;r=changes.loc[seed]
        assert r.contactos_entrega8==old.sum() and r.contactos_nuevos==new.sum()
        assert r.agregados==(new&~old).sum() and r.retirados==(old&~new).sum()
    values=p.drop(columns=KEYS).to_numpy();assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    assert (out/'MENSAJE_SEMILLAS.txt').read_text().strip()=='submit '+m['submit']
    d15=ROOT/m['verificacion_entrega15']['carpeta']
    assert sha(d15/'manifest.json')==m['verificacion_entrega15']['manifest_sha256']
    # Corroborar que todos los adjuntos originales15 siguen intactos.
    d15m=json.loads((d15/'manifest.json').read_text(encoding='utf-8'))
    for e in d15m['archivos']:assert sha(d15/e['archivo'])==e['sha256']
    v=dict(estado='verificado',modelos_lightgbm_reproducidos=5,adjuntos_verificados=5,
        historia_calendario_independiente=True,matrices_y_target_verificados=True,features_lightgbm=189,
        features_tabpfn=202,corte_estricto=.025,mezcla=[.5,.5],entrenamiento=[202104,202105],
        etiquetas_agosto=False,control_local_superado=True,entrega15_preservada=True,api=False,creditos=0,
        enviado=False,codigo_verificador_sha256=sha(Path(__file__)))
    (out/'verificacion_independiente.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    m['estado']='completo_verificado_preparado_pendiente'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(v,indent=2),flush=True)


if __name__=='__main__':main()
