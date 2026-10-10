"""Cinco CSV de LGB189 congelado16 + TabPFN226 nuevo; no envío al Bot."""
import argparse
import importlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
import pandas as pd

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();src=args.salida.resolve()
m=json.loads((src/'manifest.json').read_text(encoding='utf-8'))
state=json.loads((src/'tabpfn_estado.json').read_text(encoding='utf-8'))
assert state['estado']=='completo_verificado' and state['creditos']<=80000
assert pipe.sha(src/'predicciones_tab226_agosto.csv')==state['predicciones_sha256']
assert pipe.sha(src/'predicciones_lightgbm16.csv')==m['base_predictions_sha256']
for f,h in m['lightgbm_sha256'].items():assert pipe.sha(pipe.ROOT/f)==h
base=pd.read_csv(src/'predicciones_lightgbm16.csv');tab=pd.read_csv(src/'predicciones_tab226_agosto.csv')
pd.testing.assert_frame_equal(base[pipe.KEYS],tab[pipe.KEYS]);assert len(base)==164647 and base.numero_de_cliente.is_unique
pred=base.copy();pred['p_tab226']=tab.p_tab226
assert np.isfinite(pred.filter(like='p_').to_numpy()).all()
folders=pipe.SAL/'01_entregas_bot';num=max(int(p.name.split('_')[0]) for p in folders.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
tag=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
name=f'EnsembleLGB189Tab2265_{tag}';out=folders/f'{num}_{name}';out.mkdir()
adj=out/'adjuntos_semillas';adj.mkdir();counts=[];changes=[]
old=pd.read_csv(pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235/predicciones_agosto.csv')
pd.testing.assert_frame_equal(old[pipe.KEYS],pred[pipe.KEYS])
for s in pipe.SEEDS:
    score=(pred[f'p_lgb_seed{s}']+pred.p_tab226)/2;pred[f'score_seed{s}']=score
    selected=pred.assign(score=score).loc[score>.025].sort_values(['score','numero_de_cliente'],ascending=[False,True])
    path=adj/f'{name}_seed{s}.csv'
    selected.numero_de_cliente.to_csv(path,index=False,header=False,lineterminator='\n')
    ids=pd.read_csv(path,header=None)[0].to_numpy()
    np.testing.assert_array_equal(ids,selected.numero_de_cliente.to_numpy());assert len(np.unique(ids))==len(ids)
    before=old[f'score_seed{s}']>.025;after=score>.025
    counts.append(dict(seed=s,contactos=len(ids),archivo=str(path.relative_to(out)),sha256=pipe.sha(path)))
    changes.append(dict(seed=s,contactos_16=int(before.sum()),contactos_nuevos=int(after.sum()),
             agregados=int((after&~before).sum()),retirados=int((before&~after).sum())))
pred.to_csv(out/'predicciones_agosto.csv',index=False)
pd.DataFrame(changes).to_csv(out/'cambios_contactos_vs16.csv',index=False)
command='submit '+name+'_semillas'
(out/'MENSAJE_SEMILLAS.txt').write_text(command+'\n',encoding='utf-8')
(out/'ESTADO_ENVIO.txt').write_text('Preparado/verificado, pendiente de envío manual. Sin resultado público.\n',encoding='utf-8')
pipe.save(out/'manifest.json',dict(estado='completo_verificado_preparado_pendiente',entrega=num,submit=name+'_semillas',
      enviado=False,train=[202104,202105],prediccion=202108,features_lightgbm=189,features_tabpfn=226,
      target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',pesos=dict(lightgbm=.5,tabpfn=.5),
      umbral=.025,operador='>',semillas=pipe.SEEDS,fuente_final=str(src.relative_to(pipe.ROOT)),
      fuente_manifest_sha256=pipe.sha(src/'manifest.json'),estado_tabpfn_sha256=pipe.sha(src/'tabpfn_estado.json'),
      creditos=state['creditos'],lightgbm='Modelos congelados16; sólo TabPFN actualizado',
      adjuntos=counts,referencia_local=m['referencia_local'],referencia_publica16=96921000,
      codigo_sha256={f:pipe.sha(pipe.TP/f) for f in ['103_preparar_entrega_tabpfn226.py','102_tabpfn226_agosto.py','104_archivar_codigo_entrega.py']},
      predicciones_sha256=pipe.sha(out/'predicciones_agosto.csv')))
(out/'INFORME.md').write_text('# Actualización de TabPFN del ensemble16\n\n'
      'LightGBM189 original de16, target combinado; TabPFN226 nuevo BAJA+2, ambos abril+mayo→agosto. '
      'Mezcla50/50, corte>2,5%, cinco CSV individuales. TabPFN incorpora corrección ccajas mayo y24lag2/delta2. '
      'LightGBM mantiene el entrenamiento original, sin nuevas columnas.\n\n'
      'Referencia local: total$268.367.000,25%$67.091.750 frente16total$266.420.000,25%$66.605.000. '
      'Mayo reutilizado; entrenamiento final TabPFN sí observa lag2 en mayo, ausente en entrenamiento localabril. '
      'No garantía pública. Agosto sin etiquetas: no se calcula ganancia final.\n\n'
      'Comando: `'+command+'`. Adjuntar sólo los cincoCSV de adjuntos_semillas. '
      'No se envió al Bot.\n',encoding='utf-8')
pipe.save(out/'verificacion_independiente.json',dict(estado='verificado',checks=['claves iguales','modelos LGB hashes fuente',
      'predicciones API hashes','mezcla por cliente','corte estricto','orden score e ID','lectura exacta cinco CSV'],archivos=counts))
importlib.import_module('104_archivar_codigo_entrega').archivar(out,
    ['101_preparar_tabpfn226_agosto.py','102_tabpfn226_agosto.py','103_preparar_entrega_tabpfn226.py','89_catedra_pipeline.py'])
print('Entrega preparada:',out,flush=True);print(command,flush=True)
