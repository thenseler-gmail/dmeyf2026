"""Registra la comparacion completa y la entrega17 elegida; no envia al Bot."""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega'
out=TP/'salidas/combinaciones189_202_20261006_152106'
delivery=TP/'salidas/01_entregas_bot/17_EnsembleHist189CatBoost5_20261006_145854'
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
d=json.loads((delivery/'manifest.json').read_text(encoding='utf-8'))
assert m['mejor']['variante']=='LGB189_Tab202_Cat202' and d['entrega']==17 and not d['enviado']
assert json.loads((delivery/'verificacion_independiente.json').read_text())['adjuntos_verificados']==5
r=pd.read_csv(out/'resultados_semillas.csv')
s=pd.read_csv(out/'comparacion_media5.csv')
assert len(r)==40 and len(s)==8
for row in s.itertuples():
    subset=r[r.variante.eq(row.variante)]
    assert len(subset)==5 and set(subset.seed)==set(m['semillas'])
    assert (subset.ganancia==subset.tp*1072500-subset.fp*27500).all()
    assert subset.ganancia.mean()==row.ganancia and row.ganancia_25pct==row.ganancia/4
message=('**Ocho combinaciones 189/202 completas:** '
         '[informe](salidas/combinaciones189_202_20261006_152106/MINI_INFORME.md). '
         'Mejor local LightGBM189 + TabPFN202 + CatBoost202 40/40/20: '
         'total medio $269.813.500; 25% $67.453.375. Es exactamente la entrega17 existente; '
         'sus cinco CSV fueron verificados nuevamente. Elegida para el siguiente envío manual, '
         'sin duplicar carpeta, reentrenar ni consumir créditos. Mensaje: '
         '`submit '+d['submit']+'`. Sin resultado público informado. '
         'Mayo y semillas reutilizados; selección entre ocho variantes no es test independiente.')
p=TP/'NEXT_STEPS_IDEAS.md';text=p.read_text(encoding='utf-8')
marker='## Plan consolidado vigente — 2026-10-06\n'
if message not in text:text=text.replace(marker,marker+'\n'+message+'\n',1)
p.write_text(text,encoding='utf-8')
p=TP/'config_validacion_lightgbm.json';c=json.loads(p.read_text(encoding='utf-8'))
c['combinaciones189_202_local']={**m,'fuente':str(out.relative_to(ROOT)),
    'entrega_seleccionada':17,'carpeta_entrega':str(delivery.relative_to(ROOT)),
    'submit':d['submit'],'enviado':False,'resultado_publico':None}
c['mix_hist189_catboost_local']['estado_entrega_final']='seleccionada_mejor_de_ocho_verificada_pendiente_envio_manual'
p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'BITACORA_DMEYF.md';text=p.read_text(encoding='utf-8')
heading='## 102. Ocho combinaciones189/202 y seleccion entrega17 - 2026-10-06'
if heading not in text:
    text+='\n'+heading+'\n\n'+message+'\n\n'
    text+=('Usuario autoriza completar todas las combinaciones y elegir la mejor para el Bot. '
           'Script75 evalúa40 listas individuales/160 partes/8 listas promedio desde fuentes guardadas, '
           'valida hashes/alineación/selección por producto matricial y reproduce cinco controles previos. '
           'Script76 comprueba gananciasTP/FP y medias guardadas. Parámetros,targets,pesos,corte y semillas congelados; '
           'cero lecturasdataset/fits/API/créditos/submits. Tres nuevas combinaciones conLGB202 pierden contra17. '
           'Script71 vuelve a verificar los cinco adjuntos finales,probabilidades fuente,IDs/orden/corte y hashes. '
           'Se conserva17, no se crea18 duplicada. Mejor público sigue16$96.921.000; '
           'el envío queda a cargo de Tomás como en las entregas anteriores.\n')
    p.write_text(text,encoding='utf-8')
(out/'ENTREGA_SELECCIONADA.md').write_text('# Entrega seleccionada\n\n'+message+'\n\n'
    'Carpeta: '+str(delivery.relative_to(ROOT))+'/adjuntos_semillas\n',encoding='utf-8')
print('Ocho variantes registradas. Entrega17 verificada, lista para envio manual.')
