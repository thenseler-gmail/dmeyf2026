"""Registra resultado informado en contexto entrega19, preserva payloads originales."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega'
D=TP/'salidas/01_entregas_bot/19_EnsembleHist189CatBoostCorte31_20261006_153041'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
m=json.loads((D/'manifest.json').read_text(encoding='utf-8'));assert m['entrega']==19
for f,h in m['archivos_sha256'].items():assert sha(D/f)==h
for f in m['archivos']:assert sha(D/f['archivo'])==f['sha256']
snap=D/'pre_envio';snap.mkdir(exist_ok=True)
for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json']:
    target=snap/name
    if not target.exists():target.write_bytes((D/name).read_bytes())
r=dict(fecha='2026-10-06',entrega=19,public_gain_mean=93.6595,public_gain_std_dev=1.8989,
    media_publica_pesos=93659500,desvio_publico_pesos=1898900,archivos=5,submission_id=None,
    fuente='Informado por Tomas como esta, interpretado como entrega19 por contexto inmediato; numero no explicito.',
    delta_vs_entrega16_pesos=-3261500,faltante_objetivo_100millones=6340500,
    escala='Ganancia publica ya correspondiente al25%; no dividir nuevamente.')
save(D/'RESULTADO_BOT.json',r)
m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,resultados_bot=r)
save(D/'manifest.json',m)
(D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR EL USUARIO, RESULTADO INFORMADO.\nPublic mean93.6595/std1.8989. Atribuida a19 por contexto.\n',encoding='utf-8')
note=('**Resultado público atribuido a entrega19:** media $93.659.500, desvío entre semillas $1.898.900. '
      'Por debajo de entrega16 en $3.261.500. Mejor público sigue16$96.921.000; faltan$6.340.500 para objetivo100millones en esta corrida. '
      'Importes ya públicos del25%, sin volver a dividir. Usuario no explicitó número; atribución a19 por contexto. '
      'No distingue efecto del corte frente al agregado de CatBoost/pesos distintos:17/18 no tienen resultado informado. '
      'Mayo reutilizado y ajuste de score pueden no transferir a agosto; no demuestra causa ni significancia con agregados. '
      '17/18 guardadas sin envío, conforme decisión previa del usuario; no nuevo submit automático.')
report=D/'INFORME.md';s=report.read_text(encoding='utf-8')
if note not in s:report.write_text(s+'\n## Resultado público informado\n\n'+note+'\n',encoding='utf-8')
cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
c['busqueda_corte_pesos_mix17'].update(enviado=True,resultado_publico=r,entrega_seleccionada=19)
c['mix_hist189_catboost_local']['estado_entrega_final']='guardada_sin_enviar_por_decision_usuario'
c['corte33_mix17_local']['estado_entrega']='guardada_sin_enviar_por_decision_usuario'
save(cfg,c)
nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
if note not in s:nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
bit=ROOT/'BITACORA_DMEYF.md';s=bit.read_text(encoding='utf-8');head='## 107. Resultado publico entrega19 atribuido por contexto - 2026-10-06'
if head not in s:
    with bit.open('a',encoding='utf-8') as f:f.write('\n'+head+'\n\n'+note+'\n\nSnapshot pre_envio conservado; hashes de cinco adjuntos y probabilidades intactos. Cero fits/API/creditos/submits por registro.\n')
print('Resultado19 registrado; payloads intactos. Referencia publica16 conservada.')
