"""Compara Fast con 1, 2, 4 y 8 estimadores en marzo -> mayo.

Reutiliza validaciones completas compatibles; no consulta junio ni agosto.
Las corridas nuevas usan la API autorizada y requieren TABPFN_TOKEN.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from baseline import metricas

ROOT = Path(__file__).resolve().parents[1]
CARPETA = Path(__file__).resolve().parent
ESTIMADORES = (1, 2, 4, 8)


def compatibles(m, referencia):
    campos = ('train_meses', 'evaluacion_mes', 'seed', 'batch_size', 'umbral',
              'model_version', 'variables', 'muestreo', 'backend', 'features',
              'versiones', 'codigo_sha256', 'config', 'filas_train', 'filas_evaluacion')
    return (m.get('estado') == 'completo' and m.get('etapa') == 'validacion'
            and all(m.get(k) == referencia.get(k) for k in campos))


def resumir(carpeta, m, clientes):
    pred = pd.read_csv(carpeta / 'predicciones.csv')
    claves = [m['config']['id_col'], m['config']['mes_col'], m['config']['target_col']]
    if not pred[claves].equals(clientes):
        raise ValueError(f'Clientes/etiquetas distintos: {carpeta}')
    prob = pred['p_tabpfn'].to_numpy()
    if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
        raise ValueError(f'Probabilidades inválidas: {carpeta}')
    resultado = metricas(pred[claves[-1]].eq('BAJA+2'), prob, m['config'])
    for k, valor in resultado.items():
        if not np.isclose(valor, m['resultados'][k], rtol=1e-10, atol=1e-10):
            raise ValueError(f'Métrica {k} no coincide con CSV: {carpeta}')
    return dict(n_estimators=m['n_estimators'], **resultado,
                segundos=m['resultados']['segundos'],
                consumo_estimado=m['consumo_estimado'], carpeta=str(carpeta))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--referencia', type=Path,
                        default=CARPETA / 'salidas/tabpfn_api_validacion_20261004_160420_775408')
    parser.add_argument('--solo-consolidar', action='store_true',
                        help='Verificar y comparar corridas disponibles, sin red ni nuevas inferencias.')
    parser.add_argument('--max-creditos', type=int, default=200000,
                        help='Tope estimado por corrida nueva; 8 estimadores puede superar 100.000.')
    args = parser.parse_args()
    if args.max_creditos < 1:
        parser.error('max-creditos debe ser positivo.')
    referencia = json.loads((args.referencia / 'manifest.json').read_text(encoding='utf-8'))
    if (referencia.get('estado') != 'completo' or referencia.get('etapa') != 'validacion'
            or referencia.get('backend') != 'priorlabs_api'
            or referencia.get('model_version') != 'v3.5-fast'
            or referencia.get('n_estimators') != 1
            or referencia.get('train_meses') != [202103]
            or referencia.get('evaluacion_mes') != 202105
            or referencia.get('batch_size') != 0 or referencia.get('umbral') != 0.025):
        raise ValueError('Referencia incompatible con este experimento.')
    config = json.loads((CARPETA / 'config.json').read_text(encoding='utf-8'))
    if config != referencia['config']:
        raise ValueError('config.json cambió desde la referencia.')
    for nombre, digest in referencia['codigo_sha256'].items():
        if hashlib.sha256((CARPETA / nombre).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Código distinto de la referencia: {nombre}')
    for paquete, version in referencia['versiones'].items():
        if importlib.metadata.version(paquete) != version:
            raise ValueError(f'Versión distinta de la referencia: {paquete}')
    clientes = pd.read_csv(args.referencia / 'predicciones.csv')[[
        config['id_col'], config['mes_col'], config['target_col']]]
    if len(clientes) != referencia['filas_evaluacion'] or clientes.duplicated(clientes.columns[:2]).any():
        raise ValueError('Cobertura o claves inválidas en la referencia.')
    disponibles = {1: (args.referencia, referencia)}
    for path in sorted((ROOT / config['salidas']).glob('tabpfn_api_validacion_*/manifest.json')):
        m = json.loads(path.read_text(encoding='utf-8'))
        n = m.get('n_estimators')
        if n in ESTIMADORES and n not in disponibles and compatibles(m, referencia):
            disponibles[n] = (path.parent, m)
    faltantes = [n for n in ESTIMADORES if n not in disponibles]
    if faltantes and not args.solo_consolidar and not os.environ.get('TABPFN_TOKEN'):
        raise SystemExit('Falta TABPFN_TOKEN en esta terminal. No se ejecutaron inferencias.')

    spec = importlib.util.spec_from_file_location('experimento_tabpfn_api', CARPETA / '08_experimento_tabpfn.py')
    experimento = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experimento)
    out = ROOT / config['salidas'] / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('tabpfn_estimadores_%Y%m%d_%H%M%S_%f')
    out.mkdir()
    filas = []
    for n in ESTIMADORES:
        if n not in disponibles:
            if args.solo_consolidar:
                continue
            print(f'\nEjecutando Fast con {n} estimadores (marzo -> mayo)', flush=True)
            carpeta = experimento.ejecutar(SimpleNamespace(
                etapa='validacion', validacion_existente=None, n_estimators=n,
                batch_size=0, model_version='v3.5-fast', max_creditos=args.max_creditos))
            m = json.loads((carpeta / 'manifest.json').read_text(encoding='utf-8'))
            if not compatibles(m, referencia):
                raise ValueError('La nueva corrida no coincide con el protocolo de referencia.')
            disponibles[n] = (carpeta, m)
        carpeta, m = disponibles[n]
        print(f'Resultado verificado: {n} estimadores; {carpeta}', flush=True)
        filas.append(resumir(carpeta, m, clientes))
        tabla = pd.DataFrame(filas)
        tabla['diferencia_vs_1'] = tabla['ganancia'] - referencia['resultados']['ganancia']
        tabla.to_csv(out / 'comparacion.csv', index=False)
        (out / 'comparacion.json').write_text(json.dumps(dict(
            estado='completo' if len(filas) == len(ESTIMADORES) else 'parcial',
            referencia=str(args.referencia), resultados=tabla.to_dict(orient='records'),
            criterio='Ganancia mayo a umbral fijo 0,025; selección sobre validación, una semilla.',
            junio_evaluado=False), indent=2, ensure_ascii=False), encoding='utf-8')
    print('\n' + tabla[['n_estimators', 'ganancia', 'diferencia_vs_1', 'contactos', 'tp', 'fp', 'segundos', 'consumo_estimado']].to_string(index=False))
    print('\nComparación guardada en:', out)


if __name__ == '__main__':
    main()
