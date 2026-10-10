"""Dos entregas a 2,75% y 3,25% con el score congelado de35."""
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TP = Path(__file__).resolve().parent
ROOT = TP.parent
SAL = TP/'salidas'
BOT = SAL/'01_entregas_bot'
SOURCE = BOT/'35_Ensemble16Promedio5Corte30_20261009_192311'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    ref = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    source = SOURCE/'predicciones_agosto.csv'
    assert sha(source) == ref['predicciones_sha256']
    assert ref['umbral'] == .03 and ref['operador'] == '>'
    original = SOURCE/ref['archivos'][0]['archivo']
    assert sha(original) == ref['archivos'][0]['sha256']
    pred = pd.read_csv(source, float_precision='round_trip')
    assert len(pred) == 164647 and pred.numero_de_cliente.is_unique and pred.foto_mes.eq(202108).all()
    score = pred.score_promedio5
    assert np.isfinite(score).all() and score.between(0,1).all()
    expected = pred.loc[score>.03].sort_values(['score_promedio5','numero_de_cliente'], ascending=[False,True])
    assert original.read_text(encoding='ascii').splitlines() == [str(int(i)) for i in expected.numero_de_cliente]
    first = max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    stamp = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    results = []
    for number, (cut, label) in enumerate([(.0275,'275'),(.0325,'325')], start=first):
        name = f'Ensemble16Promedio5Corte{label}_{stamp}'
        out = BOT/f'{number}_{name}'
        out.mkdir(); (out/'adjuntos').mkdir()
        shutil.copy2(source, out/'predicciones_agosto.csv')
        assert sha(out/'predicciones_agosto.csv') == ref['predicciones_sha256']
        selected = pred.loc[score>cut].sort_values(['score_promedio5','numero_de_cliente'], ascending=[False,True])
        ids = set(selected.numero_de_cliente)
        baseline_ids = set(expected.numero_de_cliente)
        assert (baseline_ids < ids) if cut<.03 else (ids < baseline_ids)
        target = out/'adjuntos'/f'{name}.csv'
        target.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
        meta = {k:ref[k] for k in ['train_final','futuro','semillas','pesos','agregacion','features_lightgbm',
                                  'features_tabpfn','target_lightgbm','target_tabpfn']}
        meta.update(estado='preparado_pendiente_verificacion', entrega=number, submit=name, enviado=False,
                    fuente_entrega=str(SOURCE.relative_to(ROOT)), fuente_manifest_sha256=sha(SOURCE/'manifest.json'),
                    fuente_predicciones_sha256=sha(source), predicciones_sha256=sha(out/'predicciones_agosto.csv'),
                    umbral=cut, operador='>', score_columna='score_promedio5',
                    archivos=[dict(score_columna='score_promedio5',archivo=str(target.relative_to(out)),
                                   contactos=len(selected),sha256=sha(target))],
                    cambios_vs35=dict(agregados=len(ids-baseline_ids),retirados=len(baseline_ids-ids)),
                    referencia_publica35=97047500, api=False,creditos=0,nuevos_fits=0,
                    firma=dict(codigo_sha256={Path(__file__).name:sha(Path(__file__))}),
                    limitacion='Exploración de dos cortes autorizados alrededor de35; sin nuevo resultado público. Una sola lista no mide variabilidad entre semillas.')
        save(out/'manifest.json',meta)
        subprocess.run([sys.executable,str(TP/'105_reproducir_csv_entrega.py'),'--entrega',str(out),
                        '--salida',str(SAL/f'reproduccion_{number}')],check=True)
        meta['estado']='completo_verificado_preparado_pendiente'
        save(out/'manifest.json',meta)
        (out/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
        (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVÍO MANUAL. Un CSV en una corrida separada.\n',encoding='utf-8')
        (out/'INFORME.md').write_text(
            f'# Entrega {number}: corte {cut:.2%}\n\nScore idéntico al de35: promedio de cinco semillas LightGBM189, '
            f'mezcla50/50 con TabPFN202 original16. Corte estricto >{cut:.2%}. {len(selected)} clientes.\n\n'
            f'Frente35: {len(ids-baseline_ids)} agregados y {len(baseline_ids-ids)} retirados.\n\n'
            f'Adjuntar el único CSV de adjuntos en una corrida separada. Comando: `submit {name}`.\n\n'
            'Predicciones copiadas con hash idéntico a35; lista reproducida independientemente con hash idéntico. '
            'Sin entrenamientos, API ni créditos. Resultado público pendiente.\n',encoding='utf-8')
        importlib.import_module('104_archivar_codigo_entrega').archivar(out)
        results.append(dict(entrega=number,carpeta=str(out.relative_to(ROOT)),comando='submit '+name,
                            contactos=len(selected),umbral=cut,**meta['cambios_vs35']))
    assert sha(source) == ref['predicciones_sha256']
    note='\n## Dos cortes alrededor de35 preparados — 2026-10-09\n\n'
    for entry in results:
        note+=f"Entrega{entry['entrega']}: corte>{entry['umbral']:.2%}, {entry['contactos']} clientes, unCSV. {entry['comando']}. Pendiente envío manual.\n\n"
    note+='Mismos scores35, promedio5 y mezcla50/50. CSV reproducidos con hashes idénticos; cero fits/API/créditos.\n'
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write(note)
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
