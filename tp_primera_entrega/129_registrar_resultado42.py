"""Registra resultado42 informado, conservando payload y snapshot pre_envio."""
import importlib

previous = importlib.import_module('128_registrar_resultado41')
ROOT, TP, OUT = previous.ROOT, previous.TP, previous.OUT
read, save, sha = previous.read, previous.save, previous.sha
D = TP/'salidas/01_entregas_bot/42_EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659'


def main():
    m = read(D/'manifest.json')
    assert m['entrega']==42 and len(m['archivos'])==1
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256']
    best = read(TP/'salidas/01_entregas_bot/36_Ensemble16Promedio5Corte275_20261009_192946/RESULTADO_BOT.json')
    r41 = read(previous.D/'RESULTADO_BOT.json')
    assert best['media_publica_pesos']==98175000 and r41['media_publica_pesos']==97075000
    result = dict(fecha='2026-10-10', entrega=42, public_gain_mean=96.4150, public_gain_std_dev=0.0,
        media_publica_pesos=96415000, desvio_publico_pesos=0, archivos=1, submission_id=None,
        fuente='Resultado informado explicitamente por Tomas en el chat: 42 -> mean96.4150/std0.0000',
        delta_vs_entrega36_pesos=96415000-best['media_publica_pesos'],
        delta_vs_entrega41_pesos=96415000-r41['media_publica_pesos'],
        faltante_objetivo_100millones=3585000, mejor_entrega=36,
        mejor_ganancia_publica_pesos=98175000, faltante_mejor_al_objetivo=1825000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Una sola lista; desvio cero no mide estabilidad entre semillas.')
    if (D/'RESULTADO_BOT.json').exists():
        assert read(D/'RESULTADO_BOT.json')==result
    else:
        assert not m['enviado']
    snap = D/'pre_envio'
    snap.mkdir(exist_ok=True)
    for name in ['manifest.json','INFORME.md','ESTADO_ENVIO.txt','verificacion_independiente.json']:
        target = snap/name
        if not target.exists():
            target.write_bytes((D/name).read_bytes())
    save(D/'RESULTADO_BOT.json', result)
    m.update(estado='completo_verificado_enviado_resultado_informado', enviado=True,
        resultados_bot=dict(promedio5=result), manifest_pre_envio_archivado='pre_envio/manifest.json',
        manifest_pre_envio_sha256=sha(snap/'manifest.json'))
    save(D/'manifest.json', m)
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Resultado publico registrado: $96.415.000; desvio $0; un CSV.\n', encoding='utf-8')
    note = ('## Resultado publico42 — 2026-10-10\n\n'
        'Eleccion de modelo por segmento: **$96.415.000**, desvio $0, una sola lista. '
        'Queda $1.760.000 por debajo de36 ($98.175.000) y $660.000 debajo de41 ($97.075.000). '
        'Ambas estrategias de especialistas probadas pierden contra36 en este publico; '
        'el resultado no descarta todas las formas de segmentacion. Referencia36 conservada: '
        'faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. '
        'El desvio cero proviene de una sola lista y no mide estabilidad. '
        'Importes ya publicos del25%, sin volver a dividir. '
        'Esperar resultado43 antes de continuar con experimentos;40 sigue sin resultado informado. '
        'Sin nuevos fits, APIs, creditos ni envios automaticos.\n')
    for p in [D/'INFORME.md', TP/'PLAN_EXPERIMENTOS_20261010.md', ROOT/'BITACORA_DMEYF.md']:
        content = p.read_text(encoding='utf-8')
        if note not in content:
            p.write_text(content+'\n'+note, encoding='utf-8')
    for p in [TP/'NEXT_STEPS_IDEAS.md', OUT/'ENTREGAS_PARA_BOT.md']:
        content = p.read_text(encoding='utf-8')
        if note not in content:
            p.write_text(note+'\n'+content, encoding='utf-8')
    cfgpath = TP/'config_validacion_lightgbm.json'
    cfg = read(cfgpath)
    policy = cfg['politica_exploratoria_20261010']
    for entry in policy['tres_entregas_adicionales']:
        if entry['entrega']==42:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    policy['estado']='41 $97.075.000 y42 $96.415.000 registrados;43 pendiente;40 sin resultado informado. Esperar antes de nuevos experimentos.'
    save(cfgpath, cfg)
    path = OUT/'RESULTADO.json'
    batch = read(path)
    for entry in batch['entregas']:
        if entry['entrega']==42:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    save(path, batch)
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('42 registrada: $96.415.000; delta36 -$1.760.000, delta41 -$660.000. Referencia36 intacta; esperar43.')


if __name__=='__main__':
    main()
