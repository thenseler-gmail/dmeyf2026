"""Payload local TabPFN202+8 vinculos, control189 cinco grupos, sin nueva API."""
import hashlib
import importlib
import importlib.metadata
import json
import duckdb
import numpy as np
import pandas as pd
from features_vinculos import KEYS,FUENTES,FEATURES,agregar_vinculos,verificar_independiente,verificar_ejemplos

base=importlib.import_module('116_promedio20_hist189')
local=importlib.import_module('63_experimentos_features_local')
OUT=base.SAL/'tabpfn210_vinculos_local_20261010'
P20=base.SAL/'promedio20_hist189_20261010'
PAIR=base.SAL/'control_pareado_vinculos_20261010'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=True)
    r16=read(base.D16/'manifest.json');lm=read(base.LOCAL/'manifest.json')
    seedplan=read(PAIR/'PLAN.json');groups=seedplan['grupos_semillas'];seeds=seedplan['semillas']
    assert len(seeds)==25 and len(set(seeds))==25
    assert seeds[:20]==read(P20/'PLAN.json')['semillas']
    ref7=read(local.SOURCE/'manifest.json');cols202=ref7['features_lightgbm'];cols189=r16['firma']['features']
    assert len(cols202)==202 and len(cols189)==189
    assert ref7['tabpfn_model_version']=='v3.5-fast' and ref7['tabpfn_n_estimators']==2
    files=[local.SOURCE/'manifest.json',local.SOURCE/'predicciones_mayo.csv',base.D16/'manifest.json',
        base.LOCAL/'manifest.json',P20/'PLAN.json',P20/'RESULTADO_LOCAL.json',PAIR/'PLAN.json']
    code=['137_preparar_tabpfn210_local.py','138_tabpfn210_piloto.py','139_evaluar_tabpfn210.py',
        '63_experimentos_features_local.py','116_promedio20_hist189.py','features_vinculos.py','features.py','baseline.py']
    plan=dict(train=[202104],eval=202105,target_tabpfn='BAJA+2',target_lightgbm='BAJA+1/BAJA+2',
        features_control_tabpfn=cols202,features_candidato_tabpfn=cols202+FEATURES,
        features_lightgbm=cols189,grupos_semillas=groups,semillas=seeds,
        model_version='v3.5-fast',n_estimators=2,seed_tabpfn=214363,
        categorical_features=['Visa_status','Master_status','tcuentas'],
        fit_mode='fit_preprocessors',inference_precision='autocast',inference_config={'SUBSAMPLE_SAMPLES':None},
        pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,operador='>',
        unica_diferencia='TabPFN210 incorpora ocho vinculos; LightGBM189 sin vinculos congelado',
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in files},
        codigo_sha256={f:base.sha(base.TP/f) for f in code},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb']},
        autorizacion='Usuario dice dale al piloto TabPFN210, primero cotizar. No autoriza final/agosto en esta etapa',
        max_creditos_piloto=50000,api=False,creditos=0,nuevos_fits_lightgbm=5,
        control_tabpfn_reutilizado=True,final_autorizado=False,
        criterios='Informar delta promedio entre cinco ensembles, grupo1 y otros cuatro, pares, listas individuales y partes; sin tuning',
        limitacion='Mayo reutilizado, control API historico. Cambios del servicio pueden influir; no test independiente ni garantia publica.')
    if (OUT/'PLAN.json').exists():assert read(OUT/'PLAN.json')==plan
    else:base.save(OUT/'PLAN.json',plan)
    base.save(OUT/'estado.json',dict(estado='preparando_payload_local',api=False,creditos=0))
    _,_,train,valid,xt,xv,_=local.cargar()
    assert list(xt)==list(xv)==cols202
    controlpath=base.LOCAL/'historia_1_mes/predicciones_mayo.csv'
    assert base.sha(controlpath)==lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    control=pd.read_csv(controlpath,float_precision='round_trip')
    pd.testing.assert_frame_equal(control[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    np.testing.assert_allclose(control.p_tabpfn,pd.read_csv(local.SOURCE/'predicciones_mayo.csv',float_precision='round_trip').p_tabpfn,rtol=0,atol=1e-15)
    x189t=xt[cols189];x189v=xv[cols189]
    assert local.matrix_sha(x189t)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert local.matrix_sha(x189v)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    yc=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    p20=read(P20/'RESULTADO_LOCAL.json')
    expected5={f'seed{s}.txt':lm['modelos_sha256'][f'historia_1_mes\\seed{s}.txt'] for s in seeds[:5]}
    expected20={(base.ROOT/p).name:h for p,h in p20['modelos_sha256'].items()}
    folder=OUT/'modelos_lightgbm_local';folder.mkdir(exist_ok=True)
    values=[];hashes={}
    for chunk,reuse,expected in [(seeds[:5],base.LOCAL/'historia_1_mes',expected5),
        (seeds[5:20],P20/'modelos_mayo',expected20),(seeds[20:],OUT/'sin_reuso',{})]:
        q,h=base.run_models(x189t,x189v,yc,chunk,r16['firma']['params'],folder,reuse,expected,'Control189 local piloto210')
        values.append(q);hashes.update(h)
    values=np.column_stack(values)
    for i,s in enumerate(seeds[:5]):np.testing.assert_allclose(values[:,i],control[f'p_seed{s}'],rtol=0,atol=1e-15)
    pred=control[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy()
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    for i in range(5):pred[f'score_control_ensemble{i+1}']=.5*values[:,i*5:(i+1)*5].mean(axis=1)+.5*pred.p_tabpfn
    assert base.metric(pred.clase_ternaria.eq('BAJA+2').to_numpy(),pred.score_control_ensemble1.to_numpy())['ganancia_total']==275385000
    pred.to_csv(OUT/'predicciones_control_mayo.csv',index=False)
    config=read(base.TP/'config.json')
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    features=agregar_vinculos(history);audit=verificar_independiente(history,features);checks=verificar_ejemplos()
    hashes202=dict(train=local.matrix_sha(xt),valid=local.matrix_sha(xv))
    for raw,x in [(train,xt),(valid,xv)]:
        new=raw[KEYS].merge(features,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(raw[KEYS],new[KEYS])
        for c in FEATURES:x[c]=new[c].to_numpy()
    assert list(xt)==list(xv)==cols202+FEATURES and len(xv.columns)==210
    np.savez_compressed(OUT/'tabpfn210_local.npz',train=xt.to_numpy(dtype=np.float32),valid=xv.to_numpy(dtype=np.float32),
        target=train.clase_ternaria.eq('BAJA+2').astype(np.int64).to_numpy())
    payload=dict(features=cols202+FEATURES,train=[202104],eval=202105,target='BAJA+2',filas_train=163284,filas_valid=163768,
        IDs_no_incluidos=True,mes_no_incluido=True,etiquetas_mayo_no_incluidas=True,etiquetas_auxiliares_no_extraidas=True,
        archivo_sha256=base.sha(OUT/'tabpfn210_local.npz'),predicciones_control_sha256=base.sha(OUT/'predicciones_control_mayo.csv'),
        matriz210_train_sha256=local.matrix_sha(xt),matriz210_valid_sha256=local.matrix_sha(xv),matrices_control202=hashes202,
        modelos_lightgbm_sha256=hashes,verificacion_features=audit,checks=checks,enviado=False)
    base.save(OUT/'payload.json',payload)
    base.save(OUT/'estado.json',dict(estado='payload_preparado_verificado_pendiente_cotizacion',api=False,creditos=0,
        bloqueo_actual='Autenticacion Prior Labs pendiente de habilitar por usuario',nuevos_fits_lightgbm=5))
    for p,h in plan['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    note='# Piloto TabPFN210 preparado — 2026-10-10\n\nTabPFN202 guardado frente a210 con ocho vinculos; abril->mayo,targetBAJA+2,modelo v3.5-fast,dos estimadores,seed214363. LightGBM189 sin vinculos y cinco grupos identicos a45/46;20modelos locales reutilizados y5nuevos. Pesos50/50,corte>2,75%,sin tuning. Payload210 y controles verificados; no nuevas llamadas API ni creditos. Cotizacion/autenticacion pendientes. Limite preventivo local50.000creditos; no etapa final/agosto por este piloto.\n\nEvaluacion prevista: cinco ganancias por ensemble,delta pareado y promedio,grupo1 vsotros cuatro,media de25listas individuales y cuatro partes de clientes. Mayo reutilizado y control202 historico; no garantia publica. Scripts138 cotiza/infiere y139 evalua. Fuente43 conservada como mejor publica; no promover por un solo grupo.\n'
    (OUT/'INFORME_PREPARACION.md').write_text(note,encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+note)
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(note+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print('Piloto210 preparado y verificado. Cero creditos; pendiente acceso/cotizacion.',flush=True)


if __name__=='__main__':main()
