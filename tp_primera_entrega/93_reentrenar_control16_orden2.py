"""Derivados16 con datos corregidos/213 columnas, conservando sus parámetros.

Dos ventanas finales; junio sólo entrenamiento, ninguna selección por su label.
Reutiliza Tab202 antiguo para diagnóstico, no crea entregas ni envía al Bot.
"""
import argparse
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from baseline import preparar

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
out=args.salida;raw,audit=pipe.leer(final=True);unused,cols=pipe.fuentes();cols=cols+pipe.ORDEN2
refdir=pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235'
ref=json.loads((refdir/'manifest.json').read_text(encoding='utf-8'));params=ref['firma']['params']
aug=raw[raw.foto_mes.eq(202108)].reset_index(drop=True);xp=preparar(aug,cols)[0]
old=pd.read_csv(refdir/'predicciones_agosto.csv');pd.testing.assert_frame_equal(aug[pipe.KEYS],old[pipe.KEYS])
assert aug.clase_ternaria.isna().all()
for name,meses in [('abril_mayo',[202104,202105]),('marzo_junio',[202103,202104,202105,202106])]:
    tr=raw[raw.foto_mes.isin(meses)].reset_index(drop=True)
    assert tr.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(tr,cols)[0];y=tr.clase_ternaria.ne('CONTINUA').astype(int)
    md=out/('control16_actualizado_'+name);md.mkdir(exist_ok=True)
    pred=aug[pipe.KEYS].copy();pred['p_tab202']=old.p_tabpfn
    rows=[]
    for s in pipe.SEEDS:
        print('Reentrenando control16',name,s,flush=True)
        q,n,seconds=pipe.fit_cached(md/f'seed{s}.txt',xt,y,xp,dict(params,seed=s),273)
        assert n==273
        pred[f'p_lgb_seed{s}']=q;pred[f'score_mix_seed{s}']=(q+pred.p_tab202)/2
        rows.append(dict(seed=s,contactos=int((pred[f'score_mix_seed{s}']>.025).sum()),segundos=seconds))
        pred.to_csv(md/'predicciones_agosto.csv',index=False)
    pred['p_lgb_promedio5']=pred[[f'p_lgb_seed{s}' for s in pipe.SEEDS]].mean(axis=1)
    pred['score_mix_promedio5']=(pred.p_lgb_promedio5+pred.p_tab202)/2
    pred.to_csv(md/'predicciones_agosto.csv',index=False)
    pipe.save(md/'manifest.json',dict(estado='completo_verificado',train=meses,filas_train=len(tr),
         features=cols,params=params,rounds=273,semillas=pipe.SEEDS,filas_agosto=len(aug),
         tabpfn='Guardado16 abril+mayo,202 variables; sin corrección ni orden2',
         contactos=rows,auditoria=audit,api=False,creditos=0,enviado=False,
         nuevos_datos_no_reproduccion_exacta16=True,
         predicciones_sha256=pipe.sha(md/'predicciones_agosto.csv')))
print('Dos ventanas de control16 actualizadas y verificadas; no nuevos submits.',flush=True)
