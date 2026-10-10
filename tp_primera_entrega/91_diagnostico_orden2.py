"""Diagnóstico retrospectivo por clientes: mayo tiene historia orden2 disponible.

No valida temporalmente ni selecciona con junio. Compara213 vs189 con los
parámetros del mejor trial AUC, congelados previamente. TabPFN guardado no es
compatible con esta partición; no mezclar sus predicciones en este diagnóstico.
"""
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
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
out=args.salida
spec=json.loads((out/'top10_congelado.json').read_text(encoding='utf-8'))
best=spec['configuraciones'][0]
raw,audit=pipe.leer();unused,cols=pipe.fuentes()
source=pd.read_csv(pipe.OLD/'historia_1_mes/predicciones_mayo.csv')
heldout_ids=source.loc[source.parte_cliente.eq(0),'numero_de_cliente']
va=raw[raw.foto_mes.eq(202105)&raw.numero_de_cliente.isin(heldout_ids)].reset_index(drop=True)
tr=raw[~raw.numero_de_cliente.isin(heldout_ids)].reset_index(drop=True)
assert not set(tr.numero_de_cliente).intersection(va.numero_de_cliente)
assert set(tr.foto_mes)=={202103,202104,202105} and set(va.foto_mes)=={202105}
yt=tr.clase_ternaria.ne('CONTINUA').astype(int);yv=va.clase_ternaria.ne('CONTINUA').astype(int)
params={k:v for k,v in best['params'].items() if k!='num_iterations'}
md=out/'diagnostico_orden2';md.mkdir(exist_ok=True);rows=[]
pred=va[pipe.KEYS+['clase_ternaria']].copy()
for name,features in [('corregido189',cols),('corregido213',cols+pipe.ORDEN2)]:
    xt=preparar(tr,features)[0];xv=preparar(va,features)[0]
    for seed in pipe.SEEDS:
        q,n,seconds=pipe.fit_cached(md/f'{name}_seed{seed}.txt',xt,yt,xv,
                       dict(pipe.FIXED,**params,seed=seed),best['effective_rounds'])
        pred[f'{name}_seed{seed}']=q
        rows.append(dict(variante=name,seed=seed,auc_combinado=roc_auc_score(yv,q),
             segundos=seconds,**pipe.metric(va.clase_ternaria.eq('BAJA+2'),q,va.numero_de_cliente)))
        pred.to_csv(md/'predicciones_clientes_mayo.csv',index=False)
        pd.DataFrame(rows).to_csv(md/'resultados_semillas.csv',index=False)
summary=pd.DataFrame(rows).groupby('variante')[['auc_combinado','contactos','ganancia','ganancia_25pct']].mean()
summary.to_csv(md/'resumen.csv')
pipe.save(md/'verificacion.json',dict(estado='verificado',train_clientes_excluidos=True,
      filas_train=len(tr),filas_eval=len(va),trial_congelado=best,solo_lightgbm=True,
      train_historia2_no_nula=int(tr.lag_2_ctrx_quarter.notna().sum()),
      limitacion='Clientes dentro de mayo; no validación temporal ni test independiente. Ganancia corresponde sólo a la parte retenida.'))
print(summary.to_string(),flush=True)
