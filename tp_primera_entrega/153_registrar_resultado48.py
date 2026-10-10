"""Registra publico48:98.8625M; mantiene43 como mejor publica y final elegida."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TP=ROOT/'tp_primera_entrega'
OUT=TP/'salidas/tabpfn35_contra43_20261010'
D=TP/'salidas/01_entregas_bot/48_EnsembleVinculos197TabPFN35Promedio5Corte275_20261010_172925'

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    m=read(D/'manifest.json')
    assert m['entrega']==48 and m['model_version_tabpfn']=='v3.5' and m['creditos']==151033
    assert m['umbral']==.0275 and len(m['archivos'])==1
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    for name,h in m['modelos_sha256'].items():assert sha(ROOT/name)==h
    assert read(D/'VERIFICACION_FINAL.json')['estado']=='verificado'
    result=dict(fecha='2026-10-10',entrega=48,public_gain_mean=98.8625,public_gain_std_dev=0.0,
        media_publica_pesos=98862500,desvio_publico_pesos=0,archivos=1,submission_id=None,
        fuente='Resultado informado por Tomas inmediatamente despues de48: mean98.8625/std0.0000; atribuido a48 por contexto.',
        delta_vs_entrega43_pesos=-1952500,delta_vs_entrega47_pesos=-247500,delta_vs_entrega36_pesos=687500,
        mejor_entrega=43,mejor_ganancia_publica_pesos=100815000,faltante_objetivo_100millones=1137500,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Cambio exclusivo v3.5-fast a v3.5, sin nueva validacion local. Pierde frente43 en este publico; no establece superioridad general de una version. Una lista, desvio0 no mide estabilidad.')
    if (D/'RESULTADO_BOT.json').exists():assert read(D/'RESULTADO_BOT.json')==result
    snap=D/'pre_envio';snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json','VERIFICACION_FINAL.json']:
        if not (snap/name).exists():(snap/name).write_bytes((D/name).read_bytes())
    save(D/'RESULTADO_BOT.json',result)
    m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,resultados_bot=dict(promedio5=result),
        manifest_pre_envio_archivado='pre_envio/manifest.json',manifest_pre_envio_sha256=sha(snap/'manifest.json'))
    save(D/'manifest.json',m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Public gain$98.862.500, desvio0, una lista. Mejor43 conservada.\n',encoding='utf-8')
    note=('## Resultado publico48: TabPFN v3.5 — 2026-10-10\n\n'
        '**$98.862.500**, desvio0, una lista promedio5 de10.834clientes. Frente43($100.815.000): **-$1.952.500**; '
        'frente47($99.110.000): -$247.500; frente36($98.175.000): +$687.500. '
        'Cambio exclusivo de version TabPFN v3.5-fast a v3.5,202variables,BAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. '
        'Se reutilizaron los cinco LightGBM197 de43,mezcla50/50,corte>2,75%. Consumo151.033creditos; no mejoro la referencia43 en este publico. '
        'No generalizar a superioridad de una version ni interpretar desvio0 como estabilidad. '
        'Prueba cerrada. Mejor43 y su paquete GitHub se conservan como final elegida; sin nuevas API,fits,creditos o envios por este registro.\n')
    for p in [D/'INFORME.md',OUT/'README.md',ROOT/'BITACORA_DMEYF.md',TP/'PLAN_EXPERIMENTOS_20261010.md']:
        old=p.read_text(encoding='utf-8-sig')
        if note not in old:p.write_text(old+'\n'+note,encoding='utf-8')
    p=TP/'NEXT_STEPS_IDEAS.md';old=p.read_text(encoding='utf-8-sig')
    if note not in old:p.write_text(note+'\n'+old,encoding='utf-8')
    p=TP/'config_validacion_lightgbm.json';cfg=read(p);best=cfg['mejor_publico_registrado'].copy()
    assert best['entrega']==43
    cfg['resultado_entrega48']=result
    cfg['tabpfn35_contra43_final'].update(estado='enviado_resultado_informado',resultado_publico=result)
    assert cfg['mejor_publico_registrado']==best;save(p,cfg)
    p=OUT/'ENTREGA.json';record=read(p);record.update(estado='enviado_resultado_informado',resultado_publico=result);save(p,record)
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('48 registrada:98.862.500; -1.952.500 vs43. Mejor43 y paquete final preservados.')


if __name__=='__main__':main()
