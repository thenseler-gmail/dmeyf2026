"""Registra44: cinco listas individuales, no cinco ensembles completos."""
import importlib

helper=importlib.import_module('128_registrar_resultado41')
ROOT,TP=helper.ROOT,helper.TP
read,save,sha=helper.read,helper.save,helper.sha
D=TP/'salidas/01_entregas_bot/44_EnsembleVinculos197Semillas5Corte275_20261010_095402'
OUT=TP/'salidas/distribucion43_semillas_20261010'


def main():
    m=read(D/'manifest.json')
    assert m['entrega']==44 and len(m['archivos'])==5
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    cfgpath=TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    assert cfg['mejor_publico_registrado']['entrega']==43
    assert cfg['mejor_publico_registrado']['media_publica_pesos']==100815000
    r=dict(fecha='2026-10-10',entrega=44,public_gain_mean=94.4955,public_gain_std_dev=2.8642,
        media_publica_pesos=94495500,desvio_publico_pesos=2864200,archivos=5,submission_id=None,
        fuente='Resultado de44 informado explicitamente por Tomas y repetido con los mismos valores en el chat',
        delta_vs_entrega43_pesos=-6319500,delta_vs_entrega36_pesos=-3679500,
        faltante_objetivo_100millones=5504500,mejor_entrega=43,mejor_ganancia_publica_pesos=100815000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Media/desvio entre cinco listas con un LightGBM197 y TabPFN cada una. '
            '43 promedia cinco probabilidades LightGBM antes del corte;45 son cinco ensembles completos.')
    if (D/'RESULTADO_BOT.json').exists():assert read(D/'RESULTADO_BOT.json')==r
    else:assert not m['enviado']
    snap=D/'pre_envio';snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json']:
        if not (snap/name).exists():(snap/name).write_bytes((D/name).read_bytes())
    save(D/'RESULTADO_BOT.json',r)
    m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,
        resultados_bot=dict(semillas5=r),manifest_pre_envio_archivado='pre_envio/manifest.json',
        manifest_pre_envio_sha256=sha(snap/'manifest.json'))
    save(D/'manifest.json',m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Media publica $94.495.500; desvio $2.864.200; cinco listas individuales. Resultado registrado una vez.\n',encoding='utf-8')
    note=('## Resultado44 y cinco ensembles completos45 — 2026-10-10\n\n'
        '44: media publica **$94.495.500**, desvio entre cinco listas **$2.864.200**. '
        'Queda $6.319.500 debajo de43 ($100.815.000), que conserva la mejor referencia y el objetivo publico alcanzado. '
        'Resultado repetido por el usuario con mismos valores; registrado una sola vez. '
        '44 usa una semilla LightGBM197 y TabPFN compartido por lista;43 usa el promedio de cinco LightGBM antes del corte. '
        'No intercambiar estas dos metricas ni interpretar el desvio44 como desvio de la lista fija43.\n\n'
        'El pedido corregido de cinco ensembles completos ya esta preparado como45: '
        'cada uno promedia cinco LightGBM197, mezcla50/50 con el mismo TabPFN y corte>2,75%. '
        'Grupo1 reproduce43 exactamente; otros cuatro usan veinte semillas nuevas congeladas. '
        'Pendiente envio manual de los cinco CSV de45 juntos y resultado. '
        'Public gain ya corresponde al25%, sin volver a dividir. Este registro no agrega fits/API/creditos/envios.\n')
    for p in [D/'INFORME.md',TP/'PLAN_EXPERIMENTOS_20261010.md',ROOT/'BITACORA_DMEYF.md']:
        text=p.read_text(encoding='utf-8')
        if note not in text:p.write_text(text+'\n'+note,encoding='utf-8')
    p=TP/'NEXT_STEPS_IDEAS.md';text=p.read_text(encoding='utf-8')
    if note not in text:p.write_text(note+'\n'+text,encoding='utf-8')
    entry=cfg['distribucion_cinco_listas_entrega43']
    entry.update(estado='enviado_resultado_informado',resultado_publico=r)
    save(cfgpath,cfg)
    result=read(OUT/'RESULTADO.json')
    result.update(estado='enviado_resultado_informado',resultado_publico=r)
    save(OUT/'RESULTADO.json',result)
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('44 registrada una vez: media $94.495.500, desvio $2.864.200. Mejor43 preservada;45 lista para envio.')


if __name__=='__main__':main()
