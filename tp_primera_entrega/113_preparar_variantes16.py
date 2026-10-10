"""Tres pruebas de corte/agregación de entrega16; predicciones congeladas."""
import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TP = Path(__file__).resolve().parent
ROOT = TP.parent
SAL = TP / 'salidas'
BOT = SAL / '01_entregas_bot'
SOURCE = BOT / '16_EnsembleHist1895_20261006_143235'
LOCAL = SAL / 'features_local_20261006_140702/historia_1_mes/predicciones_mayo.csv'
SEEDS = [541440, 408476, 741961, 248865, 717444]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    ref = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    expected = ref.get('predicciones_sha256') or ref['archivos_sha256']['predicciones_agosto.csv']
    assert sha(SOURCE/'predicciones_agosto.csv') == expected
    assert ref['firma']['seeds'] == SEEDS
    for entry in ref['archivos']:
        assert sha(SOURCE/entry['archivo']) == entry['sha256']
    p = pd.read_csv(SOURCE/'predicciones_agosto.csv', float_precision='round_trip')
    local = pd.read_csv(LOCAL, float_precision='round_trip')
    assert len(p) == 164647 and p.numero_de_cliente.is_unique and p.foto_mes.eq(202108).all()
    assert local.numero_de_cliente.is_unique and local.foto_mes.eq(202105).all()
    pred = p[['numero_de_cliente', 'foto_mes', 'p_tabpfn']].copy()
    local_scores = {}
    for seed in SEEDS:
        q = .5*p[f'p_lgb_seed{seed}'] + .5*p.p_tabpfn
        np.testing.assert_allclose(q, p[f'score_seed{seed}'], atol=1e-15, rtol=0)
        pred[f'score_seed{seed}'] = q
        local_scores[f'score_seed{seed}'] = .5*local[f'p_seed{seed}'] + .5*local.p_tabpfn
    columns = [f'score_seed{s}' for s in SEEDS]
    pred['score_promedio5'] = pred[columns].mean(axis=1)
    local_scores['score_promedio5'] = pd.DataFrame(local_scores)[columns].mean(axis=1)
    assert np.isfinite(pred[columns+['score_promedio5']].to_numpy()).all()
    pay = np.where(local.clase_ternaria.eq('BAJA+2'), 1072500, -27500)
    gain = lambda score, cut: int(pay[np.asarray(score)>cut].sum())
    baseline = np.mean([gain(local_scores[c], .025) for c in columns])
    assert baseline == 266420000
    variants = [
        ('Ensemble16Promedio5Corte25', .025, ['score_promedio5'], 268317500),
        ('Ensemble16SemillasCorte30', .030, columns, 272904500),
        ('Ensemble16Promedio5Corte30', .030, ['score_promedio5'], 284817500),
    ]
    first = max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    stamp = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    deliveries = []
    for number, (label, cut, scorecols, expected_local) in enumerate(variants, start=first):
        name = f'{label}_{stamp}'
        out = BOT/f'{number}_{name}'
        out.mkdir(); (out/'adjuntos').mkdir()
        pred.to_csv(out/'predicciones_agosto.csv', index=False)
        entries, metrics = [], []
        for col in scorecols:
            selected = pred.loc[pred[col]>cut].sort_values([col,'numero_de_cliente'],ascending=[False,True])
            suffix = col.removeprefix('score_')
            path = out/'adjuntos'/f'{name}_{suffix}.csv'
            path.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
            entries.append(dict(score_columna=col, archivo=str(path.relative_to(out)), contactos=len(selected), sha256=sha(path)))
            metrics.append(dict(score_columna=col, contactos=int((local_scores[col]>cut).sum()), ganancia=gain(local_scores[col],cut)))
        local_gain = float(np.mean([m['ganancia'] for m in metrics]))
        assert local_gain == expected_local
        pd.DataFrame(metrics).to_csv(out/'resultados_locales.csv', index=False)
        manifest = dict(estado='preparado_pendiente_verificacion', entrega=number, submit=name, enviado=False,
            fuente_entrega=str(SOURCE.relative_to(ROOT)), fuente_manifest_sha256=sha(SOURCE/'manifest.json'),
            fuente_predicciones_sha256=expected, fuente_local=str(LOCAL.relative_to(ROOT)), fuente_local_sha256=sha(LOCAL),
            train_final=[202104,202105], futuro=202108, semillas=SEEDS,
            pesos=dict(lightgbm=.5,tabpfn=.5), umbral=cut, operador='>',
            agregacion='promedio_probabilidades_cinco_semillas' if len(scorecols)==1 else 'cinco_listas_individuales',
            features_lightgbm=189, features_tabpfn=202, target_lightgbm='BAJA+1/BAJA+2', target_tabpfn='BAJA+2',
            archivos=entries, predicciones_sha256=sha(out/'predicciones_agosto.csv'),
            validacion_local=dict(ganancia_total=local_gain, ganancia_25pct=local_gain/4,
                control16_media_total=baseline, delta_total=local_gain-baseline, delta_25pct=(local_gain-baseline)/4),
            firma=dict(codigo_sha256={Path(__file__).name:sha(Path(__file__))}),
            api=False, creditos=0, nuevos_fits=0,
            limitacion='Mayo reutilizado. Una lista de probabilidades promediadas no es una media de ganancias de cinco listas. Mejoras locales no predicen el incremento público.')
        save(out/'manifest.json',manifest)
        subprocess.run([sys.executable,str(TP/'105_reproducir_csv_entrega.py'),'--entrega',str(out),
                        '--salida',str(SAL/f'reproduccion_{number}')],check=True)
        manifest['estado']='completo_verificado_preparado_pendiente'
        save(out/'manifest.json',manifest)
        (out/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
        (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVÍO MANUAL.\n',encoding='utf-8')
        (out/'INFORME.md').write_text(
            f'# Entrega {number}: {label}\n\nMismos modelos y TabPFN de16; mezcla50/50, corte estricto >{cut:.1%}. '
            f'Adjuntar únicamente los {len(entries)} CSV de adjuntos en una corrida separada.\n\n'
            f'Comando: `submit {name}`\n\n'
            f'Ganancia local total: ${local_gain:,.0f}; 25%: ${local_gain/4:,.0f}. '
            f'Delta contra media16: ${local_gain-baseline:,.0f}. '
            +manifest['limitacion']+'\n\nCSV reproducidos con hashes idénticos. Sin entrenamiento, API ni créditos.\n', encoding='utf-8')
        importlib.import_module('104_archivar_codigo_entrega').archivar(out)
        deliveries.append(dict(entrega=number,carpeta=str(out.relative_to(ROOT)),comando='submit '+name,
                               archivos=len(entries),contactos=[e['contactos'] for e in entries]))
    assert sha(SOURCE/'predicciones_agosto.csv') == expected
    note='\n## Variantes de entrega16 preparadas — 2026-10-09\n\n'
    for d in deliveries:
        note+=f"Entrega{d['entrega']}: {d['comando']}; {d['archivos']} CSV; pendiente envío manual. Carpeta {d['carpeta']}.\n\n"
    note+='Promedio5 a2,5%, cinco listas a3%, promedio5 a3%. Mismos modelos16 y mezcla50/50. Siete CSV reproducidos con hashes idénticos. Sin fits/API/créditos.\n'
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write(note)
    print(json.dumps(deliveries,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
