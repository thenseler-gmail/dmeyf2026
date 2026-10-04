"""TabPFN, 2 estimadores: originales vs historia, abril -> mayo.

Por defecto prepara y verifica localmente, sin red. --ejecutar-api autoriza
las dos inferencias. Experimento retrospectivo, sin consultar junio/agosto.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
from baseline import cargar_particiones, preparar, metricas
from features import agregar_historicas, agregar_historicas_ampliadas, HISTORICAS, HISTORICAS_EXTRA

ROOT = Path(__file__).resolve().parents[1]


def preparar_experimento(root, config, bloque='basicas', etapa='mayo'):
    experimental = deepcopy(config)
    meses_train, mes_eval = ([202104], 202105) if etapa == 'mayo' else ([202103, 202104], 202106)
    experimental['split'].update(train_meses=meses_train, validacion_meses=[mes_eval],
                                 tipo_evaluacion='Retrospectiva; junio expuesto es exploratorio')
    if etapa == 'junio':
        # cargar_particiones impide consultar su test; aquí junio es explícitamente
        # la evaluación exploratoria autorizada de este experimento separado.
        experimental['split']['test_meses'] = []
    train, valid = cargar_particiones(root, experimental)
    claves = [config['id_col'], config['mes_col']]
    originales = [c for c in train if c not in claves + [config['target_col']]]
    fuentes = HISTORICAS + HISTORICAS_EXTRA if bloque == 'ampliadas' else HISTORICAS
    with duckdb.connect() as con:
        con.read_csv(str(root / config['dataset'])).create_view('datos')
        historia = con.sql('SELECT numero_de_cliente, foto_mes, ' + ','.join(fuentes)
                           + (' FROM datos WHERE foto_mes IN (202103,202104,202105)' if etapa == 'mayo'
                              else ' FROM datos WHERE foto_mes IN (202103,202104,202105,202106)')
                           + ' ORDER BY foto_mes,numero_de_cliente').df()
    historia[fuentes] = historia[fuentes].replace([np.inf, -np.inf], np.nan)
    historia = (agregar_historicas_ampliadas if bloque == 'ampliadas' else agregar_historicas)(historia)
    nuevas = [c for c in historia if c not in claves + fuentes]
    particiones = []
    for df in (train, valid):
        unido = df.merge(historia[claves + nuevas], on=claves, how='left',
                         sort=False, validate='one_to_one')
        if not unido[claves].equals(df[claves].reset_index(drop=True)):
            raise ValueError('La asociación histórica cambió las filas o su orden.')
        if unido['historial_mes_anterior_disponible'].isna().any():
            raise ValueError('Falta indicador histórico.')
        particiones.append(unido)
    return experimental, *particiones, originales, nuevas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ejecutar-api', action='store_true')
    parser.add_argument('--model-version', choices=['v3.5', 'v3.5-fast'], default='v3.5')
    parser.add_argument('--bloque', choices=['basicas', 'ampliadas'], default='basicas')
    parser.add_argument('--etapa', choices=['mayo', 'junio'], default='mayo')
    parser.add_argument('--validacion-existente', type=Path)
    parser.add_argument('--max-creditos-total', type=int, default=200000)
    args = parser.parse_args()
    if args.max_creditos_total < 1:
        parser.error('El presupuesto debe ser positivo.')
    config = json.loads((ROOT / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    previo = None
    if args.etapa == 'junio':
        if not args.validacion_existente:
            parser.error('Junio requiere --validacion-existente.')
        previo = json.loads((args.validacion_existente / 'manifest.json').read_text(encoding='utf-8'))
        if (previo.get('estado') != 'completo' or previo.get('evaluacion_mes') != 202105
                or previo.get('model_version') != args.model_version
                or previo.get('bloque_historico') != args.bloque
                or previo.get('n_estimators') != 2 or previo.get('seed') != config['seed']
                or previo.get('umbral') != 0.025):
            raise ValueError('Validación incompatible con la configuración congelada.')
        for p in ['features.py', 'baseline.py']:
            if hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest() != previo['codigo_sha256'][p]:
                raise ValueError('Generador o preparación cambió: ' + p)
        for p, version in previo['versiones'].items():
            if importlib.metadata.version(p) != version:
                raise ValueError('Versión cambió: ' + p)
    config, train, valid, originales, nuevas = preparar_experimento(ROOT, config, args.bloque, args.etapa)
    if previo and (previo['originales'] != originales or previo['nuevas'] != nuevas):
        raise ValueError('Columnas distintas de la validación congelada.')
    xt, at = preparar(train, originales + nuevas)
    xv, av = preparar(valid, originales + nuevas)
    yt = train[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    yv = valid[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    if len(np.unique(yt)) != 2 or len(np.unique(yv)) != 2:
        raise ValueError('Se requieren ambas clases en cada partición.')
    out = ROOT / config['salidas'] / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('tabpfn_historicas_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True)
    manifest = dict(estado='preparado', config_experimental=config,
                    train_meses=config['split']['train_meses'], evaluacion_mes=config['split']['validacion_meses'][0],
                    etapa=args.etapa, validacion_existente=str(args.validacion_existente) if previo else None,
                    model_version=args.model_version, bloque_historico=args.bloque,
                    n_estimators=2, seed=config['seed'], umbral=0.025,
                    filas_train=len(train), filas_validacion=len(valid), originales=originales, nuevas=nuevas,
                    muestreo=False, auditoria_train=at, auditoria_validacion=av,
                    sin_historia_train=int(train.historial_mes_anterior_disponible.eq(0).sum()),
                    sin_historia_validacion=int(valid.historial_mes_anterior_disponible.eq(0).sum()),
                    faltantes_historicas_train=xt[nuevas].isna().sum().to_dict(),
                    faltantes_historicas_validacion=xv[nuevas].isna().sum().to_dict(),
                    versiones={p: importlib.metadata.version(p) for p in ['tabpfn-client','duckdb','numpy','pandas','scikit-learn','lightgbm']},
                    codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest()
                                   for p in ['11_tabpfn_historicas.py','features.py','baseline.py']},
                    notas='Retrospectiva. Junio expuesto: exploratorio, sin tuning. Marzo sin febrero se conserva con historia faltante. Historia auxiliar sin targets. Sin agosto.')
    def guardar():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    guardar()
    print(f'Train {manifest["train_meses"]}: {len(train)}; evaluación {manifest["evaluacion_mes"]}: {len(valid)}; originales: {len(originales)}; nuevas: {len(nuevas)}', flush=True)
    print('Históricas:', ', '.join(nuevas), flush=True)
    print('Sin historia:', manifest['sin_historia_train'], 'train;', manifest['sin_historia_validacion'], 'validación', flush=True)
    if not args.ejecutar_api:
        print('Preparación local completa. Sin llamadas API. Artefactos:', out)
        return
    if not os.environ.get('TABPFN_TOKEN'):
        raise RuntimeError('Falta TABPFN_TOKEN; no se subieron datos.')
    from tabpfn_client import TabPFNClassifier, estimate_cost, get_api_usage
    variantes = {'originales': originales, 'historicas': originales + nuevas}
    try:
        manifest['cuota_antes'] = str(get_api_usage())
        manifest['cotizaciones'] = {nombre: estimate_cost(xt[cols], xv[cols], model_version=args.model_version, n_estimators=2).model_dump(mode='json') for nombre, cols in variantes.items()}
        total = sum(q['estimated_cost'] for q in manifest['cotizaciones'].values())
        manifest['consumo_estimado_total'] = total
        guardar()
        print('Consumo estimado total:', total, flush=True)
        if total > args.max_creditos_total:
            raise ValueError('Cotización supera presupuesto; no se subieron datos.')
        resultados = {}
        pred = valid[[config['id_col'], config['mes_col'], config['target_col']]].copy()
        for nombre, cols in variantes.items():
            modelo = TabPFNClassifier.create_default_for_version(args.model_version, n_estimators=2,
                random_state=config['seed'], fit_mode='fit_preprocessors', inference_precision='autocast',
                categorical_features_indices=[cols.index(c) for c in ['Visa_status','Master_status','tcuentas']],
                inference_config={'SUBSAMPLE_SAMPLES': None})
            manifest.update(estado='ejecutando', variante_actual=nombre)
            guardar()
            inicio = time.perf_counter()
            modelo.fit(xt[cols].to_numpy(dtype=np.float32), yt)
            prob = modelo.predict_proba(xv[cols].to_numpy(dtype=np.float32))[:, list(modelo.classes_).index(1)]
            if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
                raise ValueError('Probabilidades inválidas.')
            pred['p_' + nombre] = prob
            pred.to_csv(out / 'predicciones.csv', index=False)
            csv = pd.read_csv(out / 'predicciones.csv')
            resultado = metricas(yv, csv['p_' + nombre], config)
            resultado.update(segundos=time.perf_counter()-inicio, variables=len(cols))
            resultados[nombre] = resultado
            manifest.update(resultados=resultados)
            guardar()
            print(nombre, resultado, flush=True)
        tabla = pd.DataFrame(resultados).T
        tabla['diferencia_vs_originales'] = tabla.ganancia - resultados['originales']['ganancia']
        tabla.to_csv(out / 'comparacion.csv', index_label='variante')
        manifest['estado'] = 'completo'
        guardar()
        try:
            manifest['cuota_despues'] = str(get_api_usage())
        except Exception as exc:
            manifest['cuota_despues_error'] = type(exc).__name__
        guardar()
        print('Resultados:', out)
    except BaseException as exc:
        manifest.update(estado='error', error_tipo=type(exc).__name__, error=str(exc))
        guardar()
        raise


if __name__ == '__main__':
    main()
