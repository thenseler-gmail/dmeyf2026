"""Invertidos202 corte2,75%: local reutilizado, cinco LGB finales, payload sin API."""
import importlib
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

base = importlib.import_module('116_promedio20_hist189')
OUT = base.SAL / 'invertidos202_corte275_20261010'
TAB = base.SAL / 'validacion_tabpfn_combinado_20261006_003126'
OLD = base.SAL / 'validacion_targets_ensemble_20261006_002629'
SRC7 = base.BOT / '7_EnsembleCombinadoTabPFN5_20261005_210238'
SRC8 = base.BOT / '8_EnsembleAbrilMayo5_20261005_220000'
KEYS = ['numero_de_cliente', 'foto_mes']


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def matrix_sha(x):
    import hashlib
    return hashlib.sha256(x.to_numpy(dtype=np.float32).tobytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    ref = read(SRC8 / 'manifest.json'); r7 = read(SRC7 / 'manifest.json')
    tm = read(TAB / 'manifest.json'); om = read(OLD / 'manifest.json')
    cols = ref['firma']['features']; seeds = ref['firma']['semillas']; spec = ref['firma']['elegido']
    assert len(cols) == 202 and cols == tm['firma']['features'] == om['features'] == r7['features_lightgbm']
    assert tm['firma']['train'] == [202104] and tm['firma']['evaluacion'] == 202105
    assert tm['firma']['target_tabpfn'] == 'BAJA+1/BAJA+2' and tm['firma']['model_version'] == 'v3.5-fast'
    assert spec['num_boost_round'] == 273
    sources = [SRC8 / 'manifest.json', SRC8 / 'predicciones_agosto.csv', SRC7 / 'manifest.json',
               SRC7 / 'predicciones_mayo.csv', TAB / 'manifest.json', TAB / 'predicciones_mayo.csv',
               OLD / 'manifest.json', OLD / 'predicciones_mayo.csv']
    plan = dict(fecha='2026-10-10', train=[202104,202105], predict=202108, features=cols, semillas=seeds,
        target_lightgbm='BAJA+2', target_tabpfn='BAJA+1/BAJA+2', params=spec['params'], rounds=273,
        pesos=dict(lightgbm=.5,tabpfn=.5), umbral=.0275, operador='>', agregacion='promedio5probabilidades',
        model_version='v3.5-fast', n_estimators=2, seed_tabpfn=214363,
        fit_mode='fit_preprocessors', inference_precision='autocast', inference_config={'SUBSAMPLE_SAMPLES':None},
        categorical_features=['Visa_status','Master_status','tcuentas'],
        nueva_correccion_ccajas=False, vinculos=False, max_creditos_propuesto=80000,
        api_envio_autorizado=False, autorizacion_actual='Usuario pide targets invertidos202 corte2,75%; preparar resultado concreto y cotizacion antes del envio API.',
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in sources},
        codigo_sha256={f:base.sha(base.TP/f) for f in [Path(__file__).name,'148_api_invertidos202.py',
            '149_entrega_invertidos202.py','features.py','baseline.py','116_promedio20_hist189.py']},
        limitacion='Mayo y semillas reutilizados; corte2,75 elegido por usuario. Cambio de targets y202variables no se atribuye solo al corte ni garantiza publico. Datos historicos sin correccion nueva.')
    base.save(OUT/'PLAN.json',plan)
    # Recompute local comparisons at the user-frozen cutoff, without API or fits.
    for folder, meta in [(TAB,tm),(OLD,om)]:
        for name,h in meta['archivos_sha256'].items():assert base.sha(folder/name)==h
    p=pd.read_csv(OLD/'predicciones_mayo.csv',float_precision='round_trip')
    t=pd.read_csv(TAB/'predicciones_mayo.csv',float_precision='round_trip')
    ctrl=pd.read_csv(SRC7/'predicciones_mayo.csv',float_precision='round_trip')
    assert base.sha(SRC7/'predicciones_mayo.csv')==r7['hashes_resultados']['predicciones_mayo.csv']
    for q in [t,ctrl]:pd.testing.assert_frame_equal(p[KEYS+['clase_ternaria']],q[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(p.p_tabpfn,t.p_tabpfn_baja2,rtol=0,atol=1e-15)
    values=p[[f'p_baja2_seed{s}' for s in seeds]].to_numpy()
    controls=ctrl[[f'p_seed{s}' for s in seeds]].to_numpy()
    y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    score0=.5*controls.mean(axis=1)+.5*t.p_tabpfn_baja2.to_numpy()
    score1=.5*values.mean(axis=1)+.5*t.p_tabpfn_combinado.to_numpy()
    a=base.metric(y,score0);b=base.metric(y,score1);pairs=[]
    for i,s in enumerate(seeds):
        ca=base.metric(y,.5*controls[:,i]+.5*t.p_tabpfn_baja2.to_numpy())
        cb=base.metric(y,.5*values[:,i]+.5*t.p_tabpfn_combinado.to_numpy())
        pairs.append(dict(seed=s,control=ca,candidato=cb,delta_total=cb['ganancia_total']-ca['ganancia_total']))
    base.save(OUT/'RESULTADO_LOCAL.json',dict(control202=a,invertido202=b,delta_total=b['ganancia_total']-a['ganancia_total'],
        media_delta_listas=float(np.mean([r['delta_total'] for r in pairs])),pareados=pairs,
        control189_conocido_total=275385000,delta_vs189_total=b['ganancia_total']-275385000,
        nota='Control202 aisla targets;189 es referencia actual con otras features. Corte>2,75. Sin nueva API local.'))
    print('Local corte2,75:',a,b,'delta',b['ganancia_total']-a['ganancia_total'],flush=True)
    # Preserve the source8 exact 202-column preparation and exclude future labels.
    config=read(base.TP/'config.json')
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos WHERE foto_mes IN (202104,202105,202108) ORDER BY foto_mes,numero_de_cliente').df()
        history=con.sql('SELECT '+','.join(KEYS+HISTORICAS+HISTORICAS_EXTRA)+' FROM datos WHERE foto_mes BETWEEN202103 AND202108 ORDER BY foto_mes,numero_de_cliente'.replace('BETWEEN202103','BETWEEN 202103').replace('AND202108','AND 202108')).df()
    assert not raw.duplicated(KEYS).any() and not history.duplicated(KEYS).any()
    h=agregar_historicas_ampliadas(history);hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.isin([202104,202105])].reset_index(drop=True)
    future=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327052 and len(future)==164647 and future.clase_ternaria.isna().all()
    xt=preparar(train,cols)[0];xf=preparar(future,cols)[0]
    assert matrix_sha(xt)==ref['firma']['matriz_train_sha256'] and matrix_sha(xf)==ref['firma']['matriz_agosto_sha256']
    assert base.sha(SRC8/'predicciones_agosto.csv')==ref['predicciones_sha256']
    oldfinal=pd.read_csv(SRC8/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(future[KEYS],oldfinal[KEYS])
    y2=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    yc=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(np.int64).to_numpy()
    values,hashes=base.run_models(xt,xf,y2,seeds,plan['params'],OUT/'modelos_lightgbm',OUT/'sin_reuso',{},'Invertidos202 final BAJA2')
    pred=future[KEYS].copy()
    for i,s in enumerate(seeds):pred[f'p_lgb_baja2_seed{s}']=values[:,i]
    pred.to_csv(OUT/'predicciones_lgb_agosto.csv',index=False)
    np.savez_compressed(OUT/'payload_tabpfn.npz',train=xt.to_numpy(dtype=np.float32),predict=xf.to_numpy(dtype=np.float32),target=yc)
    base.save(OUT/'payload.json',dict(features=cols,filas_train=len(xt),filas_predict=len(xf),
        target_tabpfn='BAJA+1/BAJA+2',target_lightgbm='BAJA+2',
        npz_sha256=base.sha(OUT/'payload_tabpfn.npz'),predicciones_lgb_sha256=base.sha(OUT/'predicciones_lgb_agosto.csv'),
        matriz_train_sha256=matrix_sha(xt),matriz_predict_sha256=matrix_sha(xf),
        modelos_lightgbm_sha256=hashes,IDs_no_en_payload=True,mes_no_en_payload=True,labels_agosto_no_en_payload=True))
    for path,digest in plan['fuentes_sha256'].items():assert base.sha(base.ROOT/path)==digest
    base.save(OUT/'estado.json',dict(estado='preparado_verificado_pendiente_cotizacion_y_autorizacion_api',fits_lightgbm=5,api=False,creditos=0))
    print('Payload y cinco modelos finales listos; no envio API.',flush=True)


if __name__=='__main__':main()
