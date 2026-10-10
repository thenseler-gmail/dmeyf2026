"""Compara TabPFN202/226 en todas las ablaciones y, si existe, ensemble top10."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();out=args.salida
state=json.loads((out/'tabpfn226_estado.json').read_text(encoding='utf-8'))
assert state['estado']=='completo_verificado' and state['creditos']<=50000
path=out/'predicciones_tab226_mayo.csv'
assert hashlib.sha256(path.read_bytes()).hexdigest()==state['predicciones_sha256']
p=pd.read_csv(path);q0=pd.read_csv(out/'predicciones_ablacion_mayo.csv')
pd.testing.assert_frame_equal(p[q0.columns],q0)
y=p.clase_ternaria.eq('BAJA+2').to_numpy();rows=[];parts=[];means=[]
for v in ['A0_control16','A1_correccion','A2_orden2']:
    for tb in ['p_tabpfn','p_tab226']:
        for s in pipe.SEEDS:
            score=(p[f'{v}_seed{s}']+p[tb])/2
            rows.append(dict(variante=v,tabpfn=tb,seed=s,**pipe.metric(y,score,p.numero_de_cliente)))
            for k in range(4):
                mask=p.parte_cliente.eq(k).to_numpy()
                parts.append(dict(variante=v,tabpfn=tb,seed=s,parte=k,
                             **pipe.metric(y[mask],score[mask],p.numero_de_cliente[mask])))
        score=(p[[f'{v}_seed{s}' for s in pipe.SEEDS]].mean(axis=1)+p[tb])/2
        for n in [None,10000,10500,11000,11500,12000]:
            means.append(dict(variante=v,tabpfn=tb,corte='p>.025' if n is None else 'top'+str(n),
                         **pipe.metric(y,score,p.numero_de_cliente,n)))
pd.DataFrame(rows).to_csv(out/'resultados_tab226_semillas.csv',index=False)
pd.DataFrame(parts).to_csv(out/'resultados_tab226_partes.csv',index=False)
summary=pd.DataFrame(rows).groupby(['variante','tabpfn'])[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
assert summary.loc[('A0_control16','p_tabpfn'),'ganancia']==266420000
summary.to_csv(out/'resumen_tab226.csv')
if (out/'predicciones_top10_mayo.csv').exists():
    top=pd.read_csv(out/'predicciones_top10_mayo.csv')
    pd.testing.assert_frame_equal(top[pipe.KEYS+['clase_ternaria']],p[pipe.KEYS+['clase_ternaria']])
    for tb in ['p_tabpfn','p_tab226']:
        score=(top.p_lgb_top10+p[tb])/2
        for n in [None,10000,10500,11000,11500,12000]:
            means.append(dict(variante='catedra_top10',tabpfn=tb,corte='p>.025' if n is None else 'top'+str(n),
                              **pipe.metric(y,score,p.numero_de_cliente,n)))
pd.DataFrame(means).to_csv(out/'cortes_tab226.csv',index=False)
report=['# TabPFN226 local y combinaciones','',
        'Consumo autorizado local: '+str(state['creditos'])+' créditos. '
        'Abril→mayo; lag2 no observable en abril. Mayo reutilizado. '
        'El score combina target combinado LightGBM y BAJA+2 TabPFN; no está calibrado.','',
        'Ganancias siguientes son medias de cinco listas individuales a >2,5%; los cortes '
        'por promedio de probabilidades se guardan aparte en cortes_tab226.csv.','',
        '```text',summary.to_string(),'```','']
(out/'INFORME_TABPFN226.md').write_text('\n'.join(report),encoding='utf-8')
pipe.save(out/'verificacion_tab226_ensemble.json',dict(estado='verificado',keys_exactas=True,
          predicciones_ablacion_preservadas=True,creditos=state['creditos'],submits=0,final_reentrenado=False))
print(summary.to_string(),flush=True)
