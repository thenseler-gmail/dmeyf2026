"""Registra43 como mejor publico: $100.815.000; objetivo100M alcanzado."""
import importlib

previous = importlib.import_module('128_registrar_resultado41')
ROOT, TP, OUT = previous.ROOT, previous.TP, previous.OUT
read, save, sha = previous.read, previous.save, previous.sha
D = TP/'salidas/01_entregas_bot/43_EnsembleVinculos197Promedio5Corte275_20261010_094750'


def main():
    m = read(D/'manifest.json')
    assert m['entrega']==43 and len(m['archivos'])==1 and m['features_lightgbm']==197
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256'] and entry['contactos']==10404
    for path, digest in m['modelos_sha256'].items():
        assert sha(ROOT/path)==digest
    refdir = TP/'salidas/01_entregas_bot/36_Ensemble16Promedio5Corte275_20261009_192946'
    ref = read(refdir/'RESULTADO_BOT.json')
    assert ref['media_publica_pesos']==98175000
    result = dict(fecha='2026-10-10', entrega=43, public_gain_mean=100.8150, public_gain_std_dev=0.0,
        media_publica_pesos=100815000, desvio_publico_pesos=0, archivos=1, submission_id=None,
        fuente='Resultado informado explicitamente por Tomas en el chat: 43 -> mean100.8150/std0.0000',
        delta_vs_entrega36_pesos=2640000, delta_vs_entrega41_pesos=3740000,
        delta_vs_entrega42_pesos=4400000, faltante_objetivo_100millones=0,
        excedente_objetivo_100millones=815000, objetivo_publico_alcanzado=True,
        mejor_entrega=43, mejor_ganancia_publica_pesos=100815000, faltante_mejor_al_objetivo=0,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Una sola lista; desvio cero no mide estabilidad entre semillas ni en private.')
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
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Resultado publico registrado: $100.815.000; desvio $0; un CSV. Nueva mejor entrega43; objetivo publico100M alcanzado.\n', encoding='utf-8')
    note = ('## Nueva mejor entrega43: objetivo publico100M alcanzado — 2026-10-10\n\n'
        '**43, ocho vinculos recurrentes: $100.815.000**, desvio $0, una sola lista de10.404clientes. '
        'Supera36 ($98.175.000) en **$2.640.000**,41 ($97.075.000) en $3.740.000 y42 ($96.415.000) en $4.400.000. '
        '**Objetivo publico $100 millones alcanzado, con $815.000 de excedente.** '
        'Nueva referencia43: LightGBM197 con ocho vinculos recurrentes y TabPFN202 guardado, '
        'promedio de cinco probabilidades, pesos50/50, corte>2,75%, abril+mayo->agosto. '
        'Segmentacion y especialistas no forman parte de43. Referencia36 y artefactos originales conservados.\n\n'
        'La lista promedio perdia $3.162.500 en mayo y la media de cinco listas perdia $5.934.500; '
        'la prueba exploratoria autorizada mejora en el publico de agosto. Mantener ambos resultados; '
        'no reescribir la validacion local ni presentar el publico como garantia privada. '
        'Public gain ya corresponde al25%; no dividir otra vez. Desvio cero significa una sola lista.\n\n'
        'Tanda41/42/43 completada, todos los resultados registrados.40 sigue sin resultado informado. '
        'Siguiente trabajo pendiente: retomar plan desde auditoria de calidad/drift, usando43 como referencia vigente '
        'y36 para medir el aporte de los ocho vinculos. No se ejecutan nuevos experimentos por este registro. '
        'Cero nuevos fits, APIs, creditos o envios automaticos.\n')
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
        if entry['entrega']==43:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    policy.update(estado='Tanda41/42/43 completada.43 nueva mejor: $100.815.000, objetivo publico100M alcanzado.40 sin resultado informado.',
        mejor_entrega_actual=43, mejor_ganancia_publica_actual=100815000, objetivo_publico_alcanzado=True)
    # La referencia36 de la politica original permanece como control historico.
    oldbest = cfg.get('mejor_publico_registrado')
    if oldbest and oldbest['entrega']!=43:
        history = cfg.setdefault('historial_mejor_publico_registrado', [])
        if oldbest not in history:
            history.append(oldbest)
    cfg['mejor_publico_registrado'] = dict(entrega=43, fuente=str(D.relative_to(ROOT)),
        resultado_fuente=str((D/'RESULTADO_BOT.json').relative_to(ROOT)),
        fecha='2026-10-10', public_gain_mean=100.8150, public_gain_std_dev=0.0,
        media_publica_pesos=100815000, desvio_publico_pesos=0, archivos=1,
        train_final=m['train_final'], futuro=m['futuro'], features_lightgbm=197, features_tabpfn=202,
        pesos=m['pesos'], umbral=.0275, operador='>', agregacion=m['agregacion'],
        contactos=10404, referencia_previa=36, ganancia_publica_previa=98175000,
        delta_vs_referencia_previa=2640000, objetivo_publico_alcanzado=True,
        excedente_objetivo_publico=815000, api=False, creditos=0,
        limitacion='Mejor publico informado; private desconocido. Desvio0 corresponde a una lista.')
    cfg['estado_objetivo_publico'] = dict(objetivo_pesos=100000000, alcanzado=True,
        entrega=43, ganancia_pesos=100815000, excedente_pesos=815000, fecha='2026-10-10')
    save(cfgpath, cfg)
    path = OUT/'RESULTADO.json'
    batch = read(path)
    for entry in batch['entregas']:
        if entry['entrega']==43:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    assert all(e['estado']=='enviado_resultado_informado' for e in batch['entregas'])
    batch.update(resultados_publicos_completos=True, mejor_entrega=43,
        mejor_ganancia_publica_pesos=100815000, objetivo_publico_alcanzado=True)
    save(path, batch)
    save(OUT/'estado.json', dict(estado='completo_verificado_resultados_publicos_registrados',
        entregas=[41,42,43], mejor_entrega=43, objetivo_publico_alcanzado=True, api=False, creditos=0))
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('43 registrada como nueva mejor: $100.815.000; +$2.640.000 vs36; objetivo100M superado en $815.000. Artefactos intactos.')


if __name__=='__main__':
    main()
