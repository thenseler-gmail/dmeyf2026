"""Registra resultado publico41 informado por Tomas; preserva payload y pre_envio."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TP = ROOT/'tp_primera_entrega'
D = TP/'salidas/01_entregas_bot/41_EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654'
OUT = TP/'salidas/tres_exploratorias_final_20261010'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    m = read(D/'manifest.json')
    assert m['entrega']==41 and len(m['archivos'])==1
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256']
    assert read(TP/'salidas/01_entregas_bot/36_Ensemble16Promedio5Corte275_20261009_192946/RESULTADO_BOT.json')['media_publica_pesos']==98175000
    result = dict(fecha='2026-10-10', entrega=41, public_gain_mean=97.0750, public_gain_std_dev=0.0,
        media_publica_pesos=97075000, desvio_publico_pesos=0, archivos=1, submission_id=None,
        fuente='Resultado informado explicitamente por Tomas en el chat: 41 -> mean97.0750/std0.0000',
        delta_vs_entrega36_pesos=-1100000, faltante_objetivo_100millones=2925000,
        mejor_entrega=36, mejor_ganancia_publica_pesos=98175000, faltante_mejor_al_objetivo=1825000,
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
    (D/'ESTADO_ENVIO.txt').write_text('ENVIADA POR TOMAS. Resultado publico registrado: $97.075.000; desvio $0; un CSV.\n', encoding='utf-8')
    note = ('## Resultado publico41 — 2026-10-10\n\n'
        'Mezcla general/especialistas: **$97.075.000**, desvio $0, una sola lista. '
        'Queda $1.100.000 por debajo de36 ($98.175.000). Referencia36 conservada; '
        'faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. '
        'El desvio cero proviene de una sola lista y no mide estabilidad. '
        'Importes ya publicos del25%, sin volver a dividir. '
        'Esperar resultados42 y43 antes de continuar con experimentos;40 sigue sin resultado informado. '
        'Sin nuevos fits, APIs, creditos ni envios automaticos.\n')
    for p in [D/'INFORME.md', TP/'PLAN_EXPERIMENTOS_20261010.md', ROOT/'BITACORA_DMEYF.md']:
        content = p.read_text(encoding='utf-8')
        if note not in content:
            p.write_text(content+'\n'+note, encoding='utf-8')
    for p in [TP/'NEXT_STEPS_IDEAS.md',OUT/'ENTREGAS_PARA_BOT.md']:
        content = p.read_text(encoding='utf-8')
        if note not in content:
            p.write_text(note+'\n'+content, encoding='utf-8')
    cfgpath = TP/'config_validacion_lightgbm.json'
    cfg = read(cfgpath)
    policy = cfg['politica_exploratoria_20261010']
    for entry in policy['tres_entregas_adicionales']:
        if entry['entrega']==41:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    policy['estado']='41 resultado publico $97.075.000;42/43 pendientes;40 sin resultado informado. Esperar antes de nuevos experimentos.'
    save(cfgpath, cfg)
    path = OUT/'RESULTADO.json'
    batch = read(path)
    for entry in batch['entregas']:
        if entry['entrega']==41:
            entry.update(estado='enviado_resultado_informado', resultado_publico=result)
    save(path, batch)
    for entry in m['archivos']:
        assert sha(D/entry['archivo'])==entry['sha256']
    assert sha(D/'predicciones_agosto.csv')==m['predicciones_sha256']
    print('41 registrada: $97.075.000; delta36 -$1.100.000. Referencia36 intacta; esperar42/43.')


if __name__=='__main__':
    main()
