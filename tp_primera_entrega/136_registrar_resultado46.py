"""Registra46 y completa comparacion pareada media197 vs189, sin inventar pares."""
import importlib

helper=importlib.import_module('128_registrar_resultado41')
ROOT,TP=helper.ROOT,helper.TP
read,save,sha=helper.read,helper.save,helper.sha
OUT=TP/'salidas/control_pareado_vinculos_20261010'


def main():
    loc=read(OUT/'ENTREGA.json');D=ROOT/loc['carpeta']
    m=read(D/'manifest.json');CAND=ROOT/m['fuente_candidato']
    cand=read(CAND/'RESULTADO_BOT.json')
    assert m['entrega']==46 and len(m['archivos'])==5
    assert cand['media_publica_pesos']==96838500 and cand['desvio_publico_pesos']==2037600
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    cfgpath=TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    assert cfg['mejor_publico_registrado']['entrega']==43
    delta=cand['media_publica_pesos']-96690000
    assert delta==148500
    r=dict(fecha='2026-10-10',entrega=46,public_gain_mean=96.6900,public_gain_std_dev=0.9437,
        media_publica_pesos=96690000,desvio_publico_pesos=943700,archivos=5,submission_id=None,
        fuente='Resultado informado por Tomas inmediatamente despues de preparar46; atribuido a46 por contexto',
        delta_vs_entrega45_pesos=-148500,delta_vs_entrega43_pesos=-4125000,
        faltante_objetivo_100millones=3310000,mejor_entrega=43,mejor_ganancia_publica_pesos=100815000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Cinco controles189, mismos grupos que45. Agregados no permiten reconstruir diferencias individuales ni su desvio.')
    if (D/'RESULTADO_BOT.json').exists():assert read(D/'RESULTADO_BOT.json')==r
    else:assert not m['enviado']
    snap=D/'pre_envio';snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json','COMPARACION_PUBLICA.json']:
        if not (snap/name).exists():(snap/name).write_bytes((D/name).read_bytes())
    save(D/'RESULTADO_BOT.json',r)
    comparison=read(D/'COMPARACION_PUBLICA.json')
    comparison.update(control_media_publica_pesos=96690000,control_desvio_publico_pesos=943700,
        delta_promedio_vinculos_pesos=delta,delta_desvio_marginal_vinculos_pesos=1093900,
        candidato_media_grupos2a5_derivada=(5*96838500-100815000)/4,
        control_media_grupos2a5_derivada=(5*96690000-98175000)/4,
        delta_promedio_vinculos_grupos2a5_derivado=(5*delta-2640000)/4,
        derivacion_grupos2a5='Restar del total5 la ganancia del grupo1 conocido y dividir por4; aproximado por redondeo del Bot',
        conclusion='Aporte promedio cinco grupos +$148.500. Grupo1 +$2.640.000; otros cuatro promedio -$474.375. '
            'La gran ventaja del grupo1 no se sostuvo en promedio en los otros cuatro. Sin evidencia de mejora consistente.',
        resultados_individuales_bot_disponibles=False,desvio_diferencias_pareadas_calculable=False,
        estado='comparacion_media_completada_resultados_publicos_informados')
    assert comparison['delta_promedio_vinculos_grupos2a5_derivado']==-474375
    save(D/'COMPARACION_PUBLICA.json',comparison)
    m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,
        resultados_bot=dict(ensembles5=r),comparacion_publica=comparison,
        manifest_pre_envio_archivado='pre_envio/manifest.json',manifest_pre_envio_sha256=sha(snap/'manifest.json'))
    save(D/'manifest.json',m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS, ATRIBUIDA A46 POR CONTEXTO. Media $96.690.000; desvio $943.700. Comparacion promedio45-46: vinculos +$148.500.\n',encoding='utf-8')
    note=('## Control46: aporte promedio de vinculos completado — 2026-10-10\n\n'
        '| Variante | Entrega | Media publica | Desvio entre cinco ensembles |\n'
        '|---|---:|---:|---:|\n'
        '| Con ocho vinculos197 |45|$96.838.500|$2.037.600|\n'
        '| Sin ocho vinculos189 |46|$96.690.000|$943.700|\n\n'
        'Mismos cinco grupos de semillas, datos abril+mayo->agosto,target combinado,273arboles, '
        'params,TabPFN202,pesos50/50 y corte>2,75%. **Aporte promedio de vinculos: +$148.500**, '
        'aproximadamente0,154% frente al control. Desvio marginal observado mayor con vinculos; '
        'no confundir diferencia de desvios marginales con desvio de diferencias pareadas.\n\n'
        '**Grupo1 conocido:**43 $100.815.000 contra36 $98.175.000,delta+$2.640.000. '
        '**Otros cuatro grupos:** media con vinculos derivada aprox.$95.844.375, '
        'sin vinculos aprox.$96.318.750,delta promedio aprox.**-$474.375**. '
        'Derivacion: (5*delta promedio total -delta grupo1)/4. Aproximado por redondeo de agregados. '
        'La gran ventaja del grupo1 no se sostuvo en promedio en los cuatro grupos nuevos. '
        'No sabemos que grupos particulares mejoran ni cuantos: Bot solo devuelve resumen. '
        'No inferir significancia o intervalo de confianza sin resultados individuales/covarianza.\n\n'
        'Conservar43 como mejor lista publica y objetivo100M alcanzado, sin atribuir su valor '
        'al rendimiento tipico. No declarar ocho vinculos como mejora consistente. '
        'Control189 de46 queda disponible para proximas comparaciones; conservar ambos lados y mismos grupos. '
        'Publico reutilizado y primer grupo previamente elegido; evaluacion exploratoria, no test independiente. '
        'Resultado46 atribuido por contexto inmediato. Registro sin nuevos fits/API/creditos/envios; '
        'public gain ya corresponde al25%, sin volver a dividir.40 sin resultado informado.\n')
    for p in [D/'INFORME.md',TP/'PLAN_EXPERIMENTOS_20261010.md',ROOT/'BITACORA_DMEYF.md']:
        text=p.read_text(encoding='utf-8')
        if note not in text:p.write_text(text+'\n'+note,encoding='utf-8')
    p=TP/'NEXT_STEPS_IDEAS.md';text=p.read_text(encoding='utf-8')
    if note not in text:p.write_text(note+'\n'+text,encoding='utf-8')
    (OUT/'COMPARACION_PUBLICA.md').write_text(note,encoding='utf-8')
    entry=cfg['control_pareado_vinculos_entrega45']
    entry.update(estado='enviado_resultado_informado',resultado_publico=r,comparacion_publica=comparison)
    save(cfgpath,cfg)
    result=read(OUT/'RESULTADO.json')
    result.update(estado='enviado_resultado_informado',resultado_publico=r,comparacion_publica=comparison)
    save(OUT/'RESULTADO.json',result)
    save(OUT/'estado.json',dict(estado='completo_verificado_comparacion_publica_registrada',
        entrega=46,delta_promedio_vinculos=148500,delta_grupos2a5_derivado=-474375,api=False,creditos=0))
    for e in m['archivos']:assert sha(D/e['archivo'])==e['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('46 registrada: media $96.690.000, desvio $943.700. Vinculos +$148.500 promedio5; grupos2-5 aprox.-$474.375. Mejor43 preservada.')


if __name__=='__main__':main()
