"""Resultado40 informado por Tomas; preservar payload, mejor43 y control36."""
import importlib

base = importlib.import_module('116_promedio20_hist189')
D = base.BOT / '40_EnsembleServicios193Promedio5Corte275_20261010_093934'


def read(path):
    import json
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    m = read(D / 'manifest.json')
    assert m['entrega'] == 40 and m['features_lightgbm'] == 193 and len(m['archivos']) == 1
    assert base.sha(D / 'predicciones_agosto.csv') == m['predicciones_sha256']
    for item in m['archivos']:
        assert base.sha(D / item['archivo']) == item['sha256']
    for p, h in m['modelos_sha256'].items():
        assert base.sha(base.ROOT / p) == h
    r36 = read(base.D36 / 'RESULTADO_BOT.json')
    r43 = read(base.BOT / '43_EnsembleVinculos197Promedio5Corte275_20261010_094750/RESULTADO_BOT.json')
    assert r36['media_publica_pesos'] == 98175000 and r43['media_publica_pesos'] == 100815000
    result = dict(fecha='2026-10-10', entrega=40, public_gain_mean=97.1850, public_gain_std_dev=0.0,
        media_publica_pesos=97185000, desvio_publico_pesos=0, archivos=1, submission_id=None,
        fuente='Tomas informa explicitamente40 mean97.1850 std0.0000 tras indicar que la entrega',
        delta_vs_entrega36_pesos=-990000, delta_vs_entrega43_pesos=-3630000,
        mejor_entrega=43, mejor_ganancia_publica_pesos=100815000,
        escala='Public gain ya corresponde al25%; no dividir nuevamente.',
        nota='Una sola lista; desvio cero no mide estabilidad. Comparacion exploratoria de cuatro servicios; no mejora el control36.')
    if (D / 'RESULTADO_BOT.json').exists():
        assert read(D / 'RESULTADO_BOT.json') == result
    snap = D / 'pre_envio'; snap.mkdir(exist_ok=True)
    for name in ['manifest.json', 'INFORME.md', 'ESTADO_ENVIO.txt', 'verificacion_independiente.json']:
        if (D / name).exists() and not (snap / name).exists():
            (snap / name).write_bytes((D / name).read_bytes())
    base.save(D / 'RESULTADO_BOT.json', result)
    m.update(estado='completo_verificado_enviado_resultado_informado', enviado=True,
             resultados_bot=dict(promedio5=result), manifest_pre_envio_archivado='pre_envio/manifest.json',
             manifest_pre_envio_sha256=base.sha(snap / 'manifest.json'))
    base.save(D / 'manifest.json', m)
    (D / 'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Public gain$97.185.000, desvio$0, una lista. Resultado registrado; mejor43 preservada.\n', encoding='utf-8')
    note = ('## Resultado publico40 registrado — 2026-10-10\n\n'
        'Cuatro señales de débitos/pagos, LightGBM193 +TabPFN202, promedio5,50/50,corte>2,75%: '
        '**$97.185.000**, desvio0, una lista. Frente36($98.175.000), **-$990.000**; frente43($100.815.000), **-$3.630.000**. '
        'No mejora al control36; bloque servicios193 cerrado tras prueba exploratoria pública. '
        'Conservar evidencia local: lista promedio+$137.500 total, media listas individuales-$7.018.000. '
        'Mejor entrega pública43 y base de comparación189+TabPFN202 conservadas. '
        'Desvio0 por única lista, no estabilidad. Importes públicos ya25%, no dividir otra vez. '
        'Pendiente40 resuelto. Plan segmentación/vínculos/calidad/canaritos completado; targets invertidos202 sigue reservado, '
        'reentrenamiento con mayo corregido sin evaluar, semántica de ceros mora sin confirmar. '
        'Registro sin nuevos fits/API/créditos/envíos.\n')
    for path in [D / 'INFORME.md', base.ROOT / 'BITACORA_DMEYF.md', base.TP / 'PLAN_EXPERIMENTOS_20261010.md']:
        content = path.read_text(encoding='utf-8-sig')
        if note not in content:
            path.write_text(content + '\n' + note, encoding='utf-8')
    path = base.TP / 'NEXT_STEPS_IDEAS.md'; content = path.read_text(encoding='utf-8-sig')
    if note not in content:
        path.write_text(note + '\n' + content, encoding='utf-8')
    path = base.TP / 'config_validacion_lightgbm.json'; cfg = read(path)
    best_before = cfg['mejor_publico_registrado'].copy()
    assert best_before['entrega'] == 43
    cfg['resultado_entrega40'] = result
    cfg['politica_exploratoria_20261010'].update(
        resultado_primera_entrega=result,
        estado='40/41/42/43 resultados registrados;43 mejor publica100.815.000. Plan local de cuatro pasos completado.')
    assert cfg['mejor_publico_registrado'] == best_before
    base.save(path, cfg)
    for item in m['archivos']:
        assert base.sha(D / item['archivo']) == item['sha256']
    assert base.sha(D / 'predicciones_agosto.csv') == m['predicciones_sha256']
    print('40 registrada:97.185.000; delta36=-990.000; delta43=-3.630.000. Mejor43 preservada.')


if __name__ == '__main__':
    main()
