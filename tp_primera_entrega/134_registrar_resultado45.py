"""Registra45 por contexto inmediato: cinco ensembles completos tipo43."""
import importlib

helper=importlib.import_module('128_registrar_resultado41')
ROOT,TP=helper.ROOT,helper.TP
read,save,sha=helper.read,helper.save,helper.sha
OUT=TP/'salidas/cinco_ensembles43_20261010'


def main():
    loc=read(OUT/'ENTREGA.json');D=ROOT/loc['carpeta']
    m=read(D/'manifest.json')
    assert m['entrega']==45 and len(m['archivos'])==5
    assert m['agregacion']=='cinco_ensembles_cada_uno_promedia_cinco_probabilidades'
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    cfgpath=TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    assert cfg['mejor_publico_registrado']['entrega']==43
    assert cfg['mejor_publico_registrado']['media_publica_pesos']==100815000
    r=dict(fecha='2026-10-10',entrega=45,public_gain_mean=96.8385,public_gain_std_dev=2.0376,
        media_publica_pesos=96838500,desvio_publico_pesos=2037600,archivos=5,submission_id=None,
        fuente='Resultado informado por Tomas inmediatamente despues de preparar45; atribuido a45 por contexto',
        delta_vs_entrega43_pesos=-3976500,delta_vs_entrega44_pesos=2343000,
        delta_vs_entrega36_pesos=-1336500,delta_desvio_vs44_pesos=-826600,
        faltante_objetivo_100millones=3161500,mejor_entrega=43,mejor_ganancia_publica_pesos=100815000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Media/desvio de cinco ensembles. Incluye la lista43 previamente seleccionada y cuatro nuevas replicas, '
            'con distintos grupos de semillas pero datos y TabPFN compartidos. No es intervalo de confianza.')
    if (D/'RESULTADO_BOT.json').exists():assert read(D/'RESULTADO_BOT.json')==r
    else:assert not m['enviado']
    snap=D/'pre_envio';snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json']:
        if not (snap/name).exists():(snap/name).write_bytes((D/name).read_bytes())
    save(D/'RESULTADO_BOT.json',r)
    m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,
        resultados_bot=dict(ensembles5=r),manifest_pre_envio_archivado='pre_envio/manifest.json',
        manifest_pre_envio_sha256=sha(snap/'manifest.json'))
    save(D/'manifest.json',m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS, ATRIBUIDA A45 POR CONTEXTO. Media publica $96.838.500; desvio $2.037.600; cinco ensembles completos.\n',encoding='utf-8')
    note=('## Resultado45: cinco ensembles completos — 2026-10-10\n\n'
        '**Media publica $96.838.500, desvio $2.037.600**, cinco ensembles completos. '
        'Resultado atribuido a45 por contexto inmediato; el usuario no repite numero. '
        'Media $3.976.500 debajo de43 ($100.815.000) y $1.336.500 debajo de36 ($98.175.000). '
        'Frente a44 (media $94.495.500/desvio $2.864.200), la media es $2.343.000 mayor '
        'y el desvio $826.600 menor. Las tandas usan grupos distintos: no es comparacion pareada que aisle la agregacion.\n\n'
        'Grupo1 reproduce43; grupos2-5 promedian cinco LightGBM197 con semillas nuevas, '
        'todos mezclados50/50 con el mismo TabPFN202 y corte>2,75%. La lista43 conserva la mejor referencia '
        'publica y el objetivo publico alcanzado; su $100.815.000 no representa la media entre replicas observada. '
        'Primera replica seleccionada previamente por score; nuevas replicas sin seleccion por rendimiento. '
        'No hay resultados individuales informados para identificar la mejor de las cuatro nuevas. '
        'Desvio entre cinco ensembles no es intervalo de confianza ni garantia privada.\n\n'
        'Tanda de distribucion completada. Proximo trabajo pendiente: retomar plan de experimentos, '
        'preservando43 y reportando estabilidad ademas del mejor resultado.40 sigue sin resultado informado. '
        'Public gain ya corresponde al25%, sin volver a dividir. Registro sin nuevos fits/API/creditos/envios.\n')
    for p in [D/'INFORME.md',TP/'PLAN_EXPERIMENTOS_20261010.md',ROOT/'BITACORA_DMEYF.md']:
        text=p.read_text(encoding='utf-8')
        if note not in text:p.write_text(text+'\n'+note,encoding='utf-8')
    p=TP/'NEXT_STEPS_IDEAS.md';text=p.read_text(encoding='utf-8')
    if note not in text:p.write_text(note+'\n'+text,encoding='utf-8')
    cfg['distribucion_cinco_ensembles_entrega43'].update(estado='enviado_resultado_informado',resultado_publico=r)
    save(cfgpath,cfg)
    result=read(OUT/'RESULTADO.json');result.update(estado='enviado_resultado_informado',resultado_publico=r)
    save(OUT/'RESULTADO.json',result)
    save(OUT/'estado.json',dict(estado='completo_verificado_resultado_publico_registrado',entrega=45,api=False,creditos=0))
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('45 registrada por contexto: media $96.838.500, desvio $2.037.600. Mejor43 preservada.')


if __name__=='__main__':main()
