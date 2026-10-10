"""Registra el ensayo local verificado sin modificar las entregas preparadas."""
import json
from pathlib import Path
import pandas as pd

root=Path(__file__).resolve().parent
out=root/'salidas/todos189_local_20261006_150519'
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
assert m['estado']=='completo_verificado'
r=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
row=r.loc['todos189_40_40_20']
money=lambda x:'$'+f'{x:,.0f}'.replace(',','.')
text=(f'**Ensayo de los tres modelos con 189 variables completo y verificado:** '
      f'[mini informe](salidas/{out.name}/MINI_INFORME.md). Abril → mayo, mismas cinco semillas, '
      f'pesos LightGBM/TabPFN/CatBoost 40/40/20 y corte >0,025. '
      f'Total medio {money(row.ganancia)}; 25% {money(row.ganancia_25pct)}. '
      f'Delta frente a16: {money(row.delta_vs16_total)}; 25% {money(row.delta_vs16_25pct)}. '
      f'Delta frente al mix17: {money(row.delta_vs17_total)}; 25% {money(row.delta_vs17_25pct)}. '
      f'Cinco CatBoost nuevos y una inferencia TabPFN189 ({m["creditos"]:,} créditos); LightGBM reutilizado. '
      f'Sin Optuna, sin entrenamiento final ni nuevo submit. Entrega17 conservada y postergada por pedido del usuario. '
      f'Mejor público sigue16: $96.921.000. Mayo reutilizado; no garantiza mejora en agosto.')
path=root/'NEXT_STEPS_IDEAS.md'
s=path.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
assert marker in s
if text not in s:s=s.replace(marker,marker+'\n'+text+'\n',1)
path.write_text(s,encoding='utf-8')
path=root/'config_validacion_lightgbm.json';c=json.loads(path.read_text(encoding='utf-8'))
c['todos189_local']={
    'fecha':'2026-10-06','estado':m['estado'],'fuente':str(out.relative_to(root.parent)),
    'train':[202104],'evaluacion':202105,'features':189,
    'targets':{'lightgbm':'BAJA+1 y BAJA+2','tabpfn':'BAJA+2','catboost':'BAJA+2'},
    'semillas':[541440,408476,741961,248865,717444],
    'pesos':{'lightgbm':.4,'tabpfn':.4,'catboost':.2},'umbral':.025,'operador':'>',
    'resultados':r.reset_index().to_dict('records'),'supera16_local':m['supera16_local'],
    'supera17_local':m['supera17_local'],'nuevos_fits_catboost':5,'api':True,
    'creditos':m['creditos'],'submits':0,'final_preparado':False,'optuna':'pendiente',
    'autorizacion_api':'AUTORIZACION_API.md','limitacion':m['limitaciones']}
c['mix_hist189_catboost_local']['catboost189']='ensayo_local_completo_verificado'
c['mix_hist189_catboost_local']['estado_entrega_final']='preparada_verificada_postergada_por_usuario'
path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=root.parent/'BITACORA_DMEYF.md';s=path.read_text(encoding='utf-8')
heading='## 101. Los tres modelos con189 evaluados localmente - 2026-10-06'
if heading not in s:
    s+='\n'+heading+'\n\n'+text+'\n\n'
    s+=('PriorLabs inicialmente bloqueado por revisión automática antes de crear el proceso, cero créditos. '
        'Usuario autorizó explícitamente payload189 de abril con BAJA+2 y mayo sin etiquetas/IDs/mes, máximo80.000 créditos. '
        'Cotización y consumo39.272; aprobación registrada. Modelos800árboles de CatBoost y matrices reconstruidos independientemente; '
        '30 ganancias individuales,120 por partes y6 listas de promedio verificadas. '
        'No junio/agosto, no etiquetas de mayo en entrenamiento/API. Fuentes y entrega17 preservadas.\n')
    path.write_text(s,encoding='utf-8')
report=out/'MINI_INFORME.md'
s=report.read_text(encoding='utf-8')
conclusion=(f'**Resultado:** todos189 supera al control16 en {money(row.delta_vs16_total)} '
            f'(25%: {money(row.delta_vs16_25pct)}), pero queda por debajo del mix17 en '
            f'{money(abs(row.delta_vs17_total))} (25%: {money(abs(row.delta_vs17_25pct))}). '
            f'Solo mejora al mix17 en {int(row.semillas_mejoran_vs17)}/5 semillas. '
            'La diferencia de media es pequeña; este ensayo no justifica reemplazar el mix17 por todos189. '
            'El mejor público continúa siendo entrega16; mix17 todavía no fue enviado.')
if conclusion not in s:
    s=s.replace('# Todos los modelos con189 variables: ensayo local\n',
                '# Todos los modelos con 189 variables: ensayo local\n\n'+conclusion+'\n',1)
    report.write_text(s,encoding='utf-8')
print('Documentacion y configuracion actualizadas; entrega17 preservada.')
