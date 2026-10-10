"""Publico47:99.110M, conservar mejor43 y hashes originales."""
import importlib
import json

base=importlib.import_module('116_promedio20_hist189')
OUT=base.SAL/'invertidos202_corte275_20261010'
D=base.BOT/'47_EnsembleInvertidos202Promedio5Corte275_20261010_170851'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    m=read(D/'manifest.json');assert m['entrega']==47 and len(m['archivos'])==1
    assert m['umbral']==.0275 and m['target_lightgbm']=='BAJA+2' and m['target_tabpfn']=='BAJA+1/BAJA+2'
    assert base.sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for e in m['archivos']:assert base.sha(D/e['archivo'])==e['sha256']
    for p,h in m['modelos_sha256'].items():assert base.sha(base.ROOT/p)==h
    qa=read(D/'VERIFICACION_FINAL.json');assert qa['estado']=='verificado' and qa['clientes']==10609
    r36=read(base.D36/'RESULTADO_BOT.json');r43=read(base.BOT/'43_EnsembleVinculos197Promedio5Corte275_20261010_094750/RESULTADO_BOT.json')
    result=dict(fecha='2026-10-10',entrega=47,public_gain_mean=99.1100,public_gain_std_dev=0.0,
        media_publica_pesos=99110000,desvio_publico_pesos=0,archivos=1,submission_id=None,
        fuente='Resultado informado por Tomas inmediatamente despues de entrega47: mean99.1100/std0.0000; atribuido a47 por contexto.',
        delta_vs_entrega36_pesos=99110000-r36['media_publica_pesos'],delta_vs_entrega43_pesos=99110000-r43['media_publica_pesos'],
        faltante_objetivo_100millones=890000,mejor_entrega=43,mejor_ganancia_publica_pesos=100815000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Una sola lista, desvio0 no mide estabilidad. Frente189 cambia targets y features; no aisla aporte de invertir targets ni demuestra superioridad privada.')
    if (D/'RESULTADO_BOT.json').exists():assert read(D/'RESULTADO_BOT.json')==result
    snap=D/'pre_envio';snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json','VERIFICACION_FINAL.json']:
        if (D/name).exists() and not (snap/name).exists():(snap/name).write_bytes((D/name).read_bytes())
    base.save(D/'RESULTADO_BOT.json',result)
    m.update(estado='completo_verificado_enviado_resultado_informado',enviado=True,resultados_bot=dict(promedio5=result),
        manifest_pre_envio_archivado='pre_envio/manifest.json',manifest_pre_envio_sha256=base.sha(snap/'manifest.json'))
    base.save(D/'manifest.json',m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Public gain$99.110.000, desvio0, una lista. Mejor43 conservada.\n',encoding='utf-8')
    note=('## Resultado público47: targets invertidos202 — 2026-10-10\n\n'
        '**$99.110.000**, desvio0, una lista promedio5 de10.609clientes. LightGBM202 BAJA+2 +TabPFN202 combinado,50/50,>2,75%,abril+mayo→agosto. '
        'Frente36($98.175.000): **+$935.000**. Frente43($100.815.000): **-$1.705.000**. Esta entrega queda$890.000 por debajo de100M; '
        'el objetivo ya se alcanzó con43, que sigue como mejor pública. No interpretar desvio0 como estabilidad. '
        'Comparación contra36 cambia también189→202, por lo que no aisla efecto de los targets. '
        'Conservar local: invertido202$268.702.500 total, control202$267.217.500,delta+$1.485.000; contra189$275.385.000,delta-$6.682.500. '
        'Importes públicos ya25%, no dividir nuevamente. Candidato reservado resuelto en esta configuración; no nuevas API/créditos/fits/envíos por registro. '
        'Historial, CSV, modelos y mejor43 preservados. Reentrenar con mayo corregido sigue sin evaluar; semántica de ceros mora sigue sin confirmar.\n')
    for p in [D/'INFORME.md',base.ROOT/'BITACORA_DMEYF.md',base.TP/'PLAN_EXPERIMENTOS_20261010.md']:
        old=p.read_text(encoding='utf-8-sig')
        if note not in old:p.write_text(old+'\n'+note,encoding='utf-8')
    p=base.TP/'NEXT_STEPS_IDEAS.md';old=p.read_text(encoding='utf-8-sig')
    if note not in old:p.write_text(note+'\n'+old,encoding='utf-8')
    p=base.TP/'config_validacion_lightgbm.json';cfg=read(p);best=cfg['mejor_publico_registrado'].copy();assert best['entrega']==43
    cfg['resultado_entrega47']=result
    cfg['invertidos202_corte275_final'].update(estado='enviado_resultado_informado',resultado_publico=result)
    cfg['pendiente_ultima_hora'].update(estado='ejecutado_entrega47_resultado_informado',resultado_publico=result,umbral=.0275)
    if 'entrega_final' in cfg['pendiente_ultima_hora']:cfg['pendiente_ultima_hora']['entrega_final'].update(estado='enviado_resultado_informado',resultado_publico=result)
    assert cfg['mejor_publico_registrado']==best;base.save(p,cfg)
    for p in [OUT/'ENTREGA.json',OUT/'estado.json']:
        record=read(p);record.update(estado='enviado_resultado_informado',resultado_publico=result);base.save(p,record)
    for e in m['archivos']:assert base.sha(D/e['archivo'])==e['sha256']
    assert base.sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('47 registrada:99.110.000; +935.000 vs36; -1.705.000 vs43. Mejor43 preservada.')


if __name__=='__main__':main()
