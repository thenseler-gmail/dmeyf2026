"""Verificación independiente de ablaciones/Optuna; árboles efectivos del modelo guardado."""
import argparse
import importlib
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from baseline import preparar

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();out=args.salida
data,audit=pipe.leer();unused,cols=pipe.fuentes();va=data[data.foto_mes.eq(202105)].reset_index(drop=True)
base=pd.read_csv(pipe.OLD/'historia_1_mes/predicciones_mayo.csv')
pred=pd.read_csv(out/'predicciones_ablacion_mayo.csv')
pd.testing.assert_frame_equal(va[pipe.KEYS+['clase_ternaria']],pred[pipe.KEYS+['clase_ternaria']])
rows=[]
for name,features in [('A0_control16',cols),('A1_correccion',cols),('A2_orden2',cols+pipe.ORDEN2)]:
    xv=preparar(va,features)[0]
    for s in pipe.SEEDS:
        q=base[f'p_seed{s}'].to_numpy() if name=='A0_control16' else lgb.Booster(
             model_file=str(out/name/f'seed{s}.txt')).predict(xv,validate_features=True)
        np.testing.assert_allclose(q,pred[f'{name}_seed{s}'],atol=1e-15,rtol=0)
        for kind,score in [('lgb',q),('mix50',(q+pred.p_tabpfn)/2)]:
            selected=np.asarray(score)>.025
            gain=int(np.where(va.clase_ternaria.eq('BAJA+2'),1072500,-27500)[selected].sum())
            rows.append(dict(variante=name,tipo=kind,seed=s,ganancia=gain))
saved=pd.read_csv(out/'resultados_ablacion_semillas.csv')
pd.testing.assert_frame_equal(pd.DataFrame(rows),saved[['variante','tipo','seed','ganancia']],check_dtype=False)
normalizaciones=[]
if (out/'top10_congelado.json').exists():
    spec=json.loads((out/'top10_congelado.json').read_text(encoding='utf-8'))
    original=out/'top10_pre_verificacion.json'
    if not original.exists():pipe.save(original,spec)
    xv=preparar(va,spec['features'])[0];qs=[]
    for t in spec['configuraciones']:
        model=lgb.Booster(model_file=str(out/'optuna_modelos'/f"trial{t['trial']}.txt"))
        q=model.predict(xv,validate_features=True)
        np.testing.assert_allclose(q,np.load(out/'optuna_modelos'/f"trial{t['trial']}_mayo.npy"),rtol=0,atol=1e-15)
        assert abs(roc_auc_score(va.clase_ternaria.ne('CONTINUA'),q)-t['auc'])<1e-12
        # Early stopping puede guardar menos árboles que el Booster en memoria.
        if model.num_trees()!=t['effective_rounds']:
            normalizaciones.append(dict(trial=t['trial'],antes=t['effective_rounds'],guardados=model.num_trees()))
            t['effective_rounds']=model.num_trees()
        qs.append(q)
    pipe.save(out/'top10_congelado.json',spec)
    p=pd.read_csv(out/'predicciones_top10_mayo.csv')
    np.testing.assert_allclose(np.mean(qs,axis=0),p.p_lgb_top10,atol=1e-15,rtol=0)
    np.testing.assert_allclose((p.p_lgb_top10+p.p_tabpfn)/2,p.score_mix50,atol=1e-15,rtol=0)
pipe.save(out/'verificacion_independiente.json',dict(estado='verificado',
           ablaciones=True,optuna=(out/'top10_congelado.json').exists(),
           arboles_efectivos_normalizados=normalizaciones,labels_junio_leidas=False,
           limitacion='March/April no tienen lag2: no aprendido en la búsqueda temporal. Mayo reutilizado.'))
print('Verificación independiente completa; árboles efectivos normalizados:',normalizaciones,flush=True)
