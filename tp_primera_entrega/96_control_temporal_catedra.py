"""Control189 con parámetros16 y la misma ventana marzo+abril→mayo que Optuna."""
import argparse
import importlib
import json
from pathlib import Path
import pandas as pd
from baseline import preparar

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();out=args.salida
raw,audit=pipe.leer();unused,cols=pipe.fuentes()
ref=json.loads((pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235/manifest.json').read_text(encoding='utf-8'))
tr=raw[raw.foto_mes.isin([202103,202104])].reset_index(drop=True)
va=raw[raw.foto_mes.eq(202105)].reset_index(drop=True)
xt=preparar(tr,cols)[0];xv=preparar(va,cols)[0];yt=tr.clase_ternaria.ne('CONTINUA').astype(int)
old=pd.read_csv(pipe.OLD/'historia_1_mes/predicciones_mayo.csv')
pd.testing.assert_frame_equal(va[pipe.KEYS+['clase_ternaria']],old[pipe.KEYS+['clase_ternaria']])
md=out/'control_temporal';md.mkdir(exist_ok=True);pred=old[pipe.KEYS+['clase_ternaria','p_tabpfn']].copy();rows=[]
for s in pipe.SEEDS:
    q,n,seconds=pipe.fit_cached(md/f'seed{s}.txt',xt,yt,xv,dict(ref['firma']['params'],seed=s),273)
    pred[f'p_seed{s}']=q
    for tipo,score in [('lgb',q),('mix50',(q+pred.p_tabpfn)/2)]:
        rows.append(dict(tipo=tipo,seed=s,**pipe.metric(va.clase_ternaria.eq('BAJA+2'),score,va.numero_de_cliente)))
    pred.to_csv(md/'predicciones_mayo.csv',index=False)
pd.DataFrame(rows).to_csv(md/'resultados_semillas.csv',index=False)
top=pd.read_csv(out/'predicciones_top10_mayo.csv');mean=pred[[f'p_seed{s}' for s in pipe.SEEDS]].mean(axis=1)
comparacion=[]
for name,q in [('control_lgb_promedio5',mean),('control_mix_promedio5',(mean+pred.p_tabpfn)/2),
               ('catedra_lgb_top10',top.p_lgb_top10),('catedra_mix_top10',top.score_mix50)]:
    for n in [None,10000,10500,11000,11500,12000]:
        comparacion.append(dict(variante=name,corte='p>.025' if n is None else 'top'+str(n),
                    **pipe.metric(va.clase_ternaria.eq('BAJA+2'),q,va.numero_de_cliente,n)))
pd.DataFrame(comparacion).to_csv(out/'comparacion_misma_ventana.csv',index=False)
pipe.save(md/'manifest.json',dict(estado='completo_verificado',train=[202103,202104],eval=202105,
     features=cols,rounds=273,params=ref['firma']['params'],undersampling=False,api=False,creditos=0,
     limitacion='Mayo reutilizado; promedios de probabilidades no equivalen a media de ganancias individuales.'))
print('Control temporal comparable verificado.',flush=True)
