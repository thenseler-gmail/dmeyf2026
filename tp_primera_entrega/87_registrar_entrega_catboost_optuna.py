"""Registra entrega final verificada y siguiente idea, sin enviar al Bot."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
assert m['estado']=='completo_verificado_preparado_pendiente' and not m['enviado']
assert m['semillas_completadas']==[541440,408476,741961,248865,717444]
assert json.loads((out/'verificacion_independiente.json').read_text())['adjuntos_verificados']==5
for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
for f,h in m['modelos_sha256'].items():assert sha(out/'modelos_catboost'/f)==h
for f in m['archivos']:assert sha(out/f['archivo'])==f['sha256']
assert (out/'MENSAJE_SEMILLAS.txt').read_text().strip()=='submit '+m['submit']
local=ROOT/m['fuente_local'];lm=json.loads((local/'manifest.json').read_text(encoding='utf-8'))
entry=json.loads((local/'entrega_preparada.json').read_text(encoding='utf-8'));assert entry['entrega']==m['entrega']
cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
c['optuna_catboost']['entrega_preparada']=entry
c['optuna_catboost']['comparacion_final']='Supera16local, pero no mejora17. Optuna no mejoro el ensemble base en mayo.'
c['optuna_catboost']['proxima_idea'].update(fecha='2026-10-07',base='mejor modelo disponible; referencia publica actual16',ejecutado=False)
save(cfg,c)
note=(f'**Entrega{m["entrega"]} CatBoost ajustado preparada/verificada:** '
    f'[informe](salidas/01_entregas_bot/{out.name}/INFORME.md). Cinco CatBoost finales abril+mayo, '
    '800 árboles/profundidad4, LightGBM189 y TabPFN202 guardados de16;40/40/20,corte2,5%. '
    'Local total$268.845.500,25%$67.211.375: supera16 por$2.425.500,25%$606.375 (4/5 semillas,3/4 partes), '
    'pero pierde contra17 por$968.000,25%$242.000 (mejora2/5 semillas,1/4 partes). '
    'Se preparó según condición del usuario de superar16; no presentar como mejora demostrada frente17. '
    f'Mensaje `submit {m["submit"]}`. Pendiente envío manual, sin resultado público. '
    'Cero créditos/API/submits automáticos. Mañana7 de octubre: vínculos recurrentes sobre mejor modelo disponible.')
nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
if note not in s:nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
bit=ROOT/'BITACORA_DMEYF.md';s=bit.read_text(encoding='utf-8');head='## 111. Entrega20 CatBoost ajustado preparada y verificada - 2026-10-06'
if head not in s:
    with bit.open('a',encoding='utf-8') as f:f.write('\n'+head+'\n\n'+note+'\n\n'
        'Script85 usa constructor final61, verifica matrices/target de abril+mayo, fuente16/17, CatBoost ganadorCV3abril y cinco semillas. '
        'Scores comprobados por producto matricial y selección/listasIDs exactas desde archivos, modelos recargados; archivos fuente preservados. '
        'No se usaron etiquetas junio/julio/agosto. Script87 comprueba hashes finales/adjuntos/modelos/comando y registra estado.\n')
report=local/'MINI_INFORME.md';s=report.read_text(encoding='utf-8')
finalnote=(f'Entrega final preparada: {out.relative_to(ROOT)}. '
    'Cumple superar16 pero no supera17; ambos son candidatos sin resultado público informado. '
    'CatBoost ajustado no mejoró su aporte local frente a CatBoost original. '
    'Enviado: no; usuario realiza envío manual. Mañana: vínculos recurrentes sobre el mejor modelo disponible.')
if finalnote not in s:report.write_text(s+'\n## Preparación final\n\n'+finalnote+'\n',encoding='utf-8')
print('Entrega final registrada, payloads y hashes verificados. Enviado: no.')
