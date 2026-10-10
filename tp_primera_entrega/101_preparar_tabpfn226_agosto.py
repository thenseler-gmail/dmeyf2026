"""Paquete final abril+mayo→agosto: actualiza sólo TabPFN y verifica LGB16 congelado."""
import hashlib
import importlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from calidad_datos import corregir_datos
from features_catedra import construir, KEYS, FUENTES

pipe=importlib.import_module('89_catedra_pipeline')
local=pipe.SAL/'catedra_implementacion_20261006_205501'
refdir=pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235'
localmeta=json.loads((local/'tabpfn226_payload.json').read_text(encoding='utf-8'))
assert pipe.sha(local/'tabpfn226_local.npz')==localmeta['archivo_sha256']
ref=json.loads((refdir/'manifest.json').read_text(encoding='utf-8'))
config=json.loads((pipe.TP/'config.json').read_text(encoding='utf-8'))
cols=localmeta['features'];assert len(cols)==226
with duckdb.connect() as con:
    con.execute('SET threads=2');con.read_csv(str(pipe.ROOT/config['dataset'])).create_view('datos')
    august=con.sql('SELECT * EXCLUDE(clase_ternaria) FROM datos WHERE foto_mes=202108 ORDER BY numero_de_cliente').df()
    history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes BETWEEN 202105 AND 202108 '
                    'ORDER BY foto_mes,numero_de_cliente').df()
    trainkeys=con.sql('SELECT numero_de_cliente,foto_mes,clase_ternaria FROM datos '
                    'WHERE foto_mes IN (202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
assert trainkeys.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
hist,audit=construir(history);new=[c for c in hist if c not in KEYS+FUENTES]
august=august.merge(hist[KEYS+new],on=KEYS,validate='one_to_one',sort=False)
xp=preparar(august,cols)[0]
assert len(xp)==164647 and august.numero_de_cliente.is_unique
data=np.load(local/'tabpfn226_local.npz')
xt=np.concatenate([data['train'],data['valid']],axis=0)
assert xt.shape==(327052,226)
labels=trainkeys.clase_ternaria.eq('BAJA+2').astype(np.int64).to_numpy()
np.testing.assert_array_equal(labels[:163284],data['target'])
localpred=pd.read_csv(local/'predicciones_tab226_mayo.csv')
pd.testing.assert_frame_equal(trainkeys.loc[trainkeys.foto_mes.eq(202105),KEYS+['clase_ternaria']].reset_index(drop=True),
                             localpred[KEYS+['clase_ternaria']])
assert np.isnan(xt[163284:,cols.index('ccajas_depositos')]).all()
old=pd.read_csv(refdir/'predicciones_agosto.csv')
pd.testing.assert_frame_equal(august[KEYS],old[KEYS])
numeric189=preparar(august,ref['firma']['features'])[0]
modelhash={}
for seed in pipe.SEEDS:
    path=refdir/'modelos'/f'seed{seed}.txt'
    modelhash[str(path.relative_to(pipe.ROOT))]=pipe.sha(path)
    assert pipe.sha(path)==ref['modelos_sha256'][path.name]
    model=lgb.Booster(model_file=str(path))
    np.testing.assert_allclose(model.predict(numeric189,validate_features=True),old[f'p_lgb_seed{seed}'],atol=1e-15,rtol=0)
out=pipe.SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('tabpfn226_agosto_%Y%m%d_%H%M%S')
out.mkdir();np.savez_compressed(out/'payload_api.npz',train=xt,valid=xp.to_numpy(dtype=np.float32),target=labels)
base=old[KEYS+[f'p_lgb_seed{s}' for s in pipe.SEEDS]].copy()
base.to_csv(out/'predicciones_lightgbm16.csv',index=False)
august[KEYS].to_csv(out/'claves_agosto.csv',index=False)
pipe.save(out/'manifest.json',dict(estado='preparado_verificado_pendiente_autorizacion_final',features_tabpfn=cols,
       train=[202104,202105],prediccion=202108,filas_train=327052,filas_prediccion=164647,
       target_tabpfn='BAJA+2',target_lightgbm='BAJA+1/BAJA+2',features_lightgbm=189,
       lightgbm='Congelado entrega16, sin nuevo fit; tratamiento anterior de ccajas en entrenamiento',
       cambio='Solo TabPFN226 con corrección ccajas mayo y24 lag2/delta2; resto de mezcla16 conservado',
       pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.025,operador='>',semillas=pipe.SEEDS,
       config_tabpfn=dict(model_version='v3.5-fast',n_estimators=2,random_state=214363),
       payload='226variables abril+mayo y labelsBAJA2,226variables agosto. Sin IDs, mes ni labelsagosto.',
       payload_sha256=pipe.sha(out/'payload_api.npz'),lightgbm_sha256=modelhash,
       base_predictions_sha256=pipe.sha(out/'predicciones_lightgbm16.csv'),
       codigo={f:pipe.sha(pipe.TP/f) for f in ['101_preparar_tabpfn226_agosto.py','features_catedra.py','calidad_datos.py','baseline.py','features.py']},
       referencia_local=dict(control_total=266420000,control25pct=66605000,nuevo_total=268367000,nuevo25pct=67091750),
       referencia_publica16=96921000,api=False,creditos=0,enviado=False,
       cotizacion_previa=78242,max_creditos_propuesto=80000,
       limitacion='Mayo reutilizado. Nueva ventana aprende lag2 en mayo, ausente en entrenamiento local abril; mejora local no garantiza agosto.'))
(out/'INFORME.md').write_text('# Actualización de TabPFN del ensemble16\n\n'
    'Paquete final preparado y verificado: abril+mayo327.052 filas,226variables, targetBAJA+2; '
    'agosto164.647 filas sin etiquetas. Corrección ccajas en mayo y24históricos orden2. '
    'LightGBM189 congelado de16, mezcla50/50 y corte>2,5%, cinco semillas. '
    'Payload API excluye IDs y mes. No se realizó inferencia final ni se envió al Bot.\n\n'
    'Cotización previa78.242 créditos. Límite propuesto80.000; pendiente autorización específica final. '
    'La aprobación anterior cubría sólo abril→mayo y50.000 créditos. '
    'Sin garantía pública: entrenamiento final incluye historia orden2 observable en mayo, ausente en abril.\n',encoding='utf-8')
print('Paquete final:',out,flush=True)
