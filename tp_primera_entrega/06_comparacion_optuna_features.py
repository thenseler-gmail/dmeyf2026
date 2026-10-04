"""Completa intrames y reúne tres variantes LightGBM con 30 trials cada una.

Reutiliza originales/históricas ya verificados. Train abril, validación mayo,
umbral 0,025. Agosto es entrega; junio no participa. Experimento retrospectivo.
Intrames agrega conjuntamente las nueve features de los tres bloques, sin historia.
"""
from pathlib import Path
import argparse
import hashlib
import importlib
import importlib.metadata
import json

import numpy as np
import optuna
import pandas as pd

from baseline import metricas


def leer(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verificar_antecedente(root, config, anterior):
    m = leer(anterior / 'manifest.json')
    c = m['config_experimental']
    for key in ['dataset', 'id_col', 'mes_col', 'target_col', 'clase_positiva', 'seed', 'ganancia']:
        if config[key] != c[key]:
            raise ValueError(f'Cambió {key}; no reutilizar la corrida anterior.')
    if c['split']['train_meses'] != [202104] or c['split']['validacion_meses'] != [202105]:
        raise ValueError('Meses incompatibles.')
    for archivo in ['baseline.py', 'features.py', '04_comparar_historicas.py']:
        actual = hashlib.sha256((root / 'tp_primera_entrega' / archivo).read_bytes()).hexdigest()
        if actual != m['codigo_sha256'][archivo]:
            raise ValueError(f'Cambió {archivo}; revisar compatibilidad antes de reutilizar.')
    for package, version in m['versiones'].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f'Cambió versión de {package}.')
    studies = {}
    storage = 'sqlite:///' + (anterior / 'estudios.db').resolve().as_posix()
    r = leer(anterior / 'resultados.json')
    for nombre in ['originales', 'historicas']:
        study = optuna.load_study(study_name=nombre, storage=storage)
        if len(study.trials) != 30 or any(t.state != optuna.trial.TrialState.COMPLETE for t in study.trials):
            raise ValueError('Se necesitan 30 trials completos por variante previa.')
        if study.best_value != r[nombre]['ganancia']:
            raise ValueError('Resultado inconsistente con SQLite.')
        studies[nombre] = study
    return m, r, studies


def comparar(root, config, anterior, intrames_existente=None):
    anterior = anterior.resolve()
    old_manifest, old_resultados, studies = verificar_antecedente(root, config, anterior)
    motor = importlib.import_module('05_optuna_historicas_rf')
    # Un estudio nuevo; no se tocan SQLite ni modelos previos.
    out = intrames_existente.resolve() if intrames_existente else motor.ejecutar(
        root, config, n_trials=30, variantes=['intrames'], incluir_rf=False)
    nuevo = leer(out / 'manifest.json')
    for key in ['dataset', 'id_col', 'mes_col', 'target_col', 'clase_positiva', 'seed', 'ganancia']:
        if nuevo['config_experimental'][key] != old_manifest['config_experimental'][key]:
            raise ValueError(f'Configuración intrames incompatible: {key}.')
    for key in ['train_meses', 'validacion_meses', 'test_meses']:
        if nuevo['config_experimental']['split'][key] != old_manifest['config_experimental']['split'][key]:
            raise ValueError(f'Partición intrames incompatible: {key}.')
    if nuevo['variantes'] != ['intrames'] or len(nuevo['intrames']) != 9:
        raise ValueError('Se requiere la variante con nueve intrames, sin históricas.')
    for key in ['filas_train', 'filas_validacion', 'positivos_train', 'positivos_validacion',
                'originales', 'nuevas', 'categoricas', 'auditoria_train', 'auditoria_validacion', 'versiones']:
        if nuevo[key] != old_manifest[key]:
            raise ValueError(f'Comparación incompatible: {key}.')
    st = optuna.load_study(study_name='intrames', storage='sqlite:///' + (out / 'estudios.db').resolve().as_posix())
    if len(st.trials) != 30 or any(t.state != optuna.trial.TrialState.COMPLETE for t in st.trials):
        raise ValueError('Intrames debe completar los 30 trials.')
    for s in [*studies.values(), st]:
        for trial in s.trials:
            if trial.distributions != st.trials[0].distributions:
                raise ValueError('Espacios de búsqueda distintos.')
        if s.trials[0].params != st.trials[0].params:
            raise ValueError('Referencias iniciales distintas.')
    resultados = {n: old_resultados[n] for n in ['originales', 'historicas']}
    resultados['intrames'] = leer(out / 'resultados.json')['intrames']
    if st.best_value != resultados['intrames']['ganancia']:
        raise ValueError('Mejor intrames inconsistente.')
    pred_old = pd.read_csv(anterior / 'predicciones_validacion.csv')
    pred_new = pd.read_csv(out / 'predicciones_validacion.csv')
    keys = [config['id_col'], config['mes_col'], config['target_col']]
    if not pred_old[keys].equals(pred_new[keys]):
        raise ValueError('No se evaluaron las mismas filas y etiquetas.')
    if pred_old.duplicated(keys[:2]).any() or not pred_old[config['mes_col']].eq(202105).all():
        raise ValueError('Claves de validación incorrectas.')
    y = pred_old[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    pred = pred_old[keys + ['p_originales', 'p_historicas']].copy()
    pred['p_intrames'] = pred_new.p_intrames
    for nombre, r in resultados.items():
        prob = pred['p_' + nombre].to_numpy()
        if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
            raise ValueError('Probabilidades inválidas.')
        calculadas = metricas(y, prob, config)
        for metrica in ['ganancia', 'contactos', 'tp', 'fp', 'umbral']:
            if calculadas[metrica] != r[metrica]:
                raise ValueError(f'{nombre}: discrepancia en {metrica}.')
    tabla = pd.DataFrame(resultados).T.drop(columns=['parametros'])
    tabla['delta_vs_originales'] = tabla.ganancia - resultados['originales']['ganancia']
    tabla.to_csv(out / 'comparacion_tres_variantes.csv', index_label='variante')
    pred.to_csv(out / 'predicciones_tres_variantes.csv', index=False)
    motor.guardar_json(out / 'comparacion_tres_variantes.json', dict(
        config_actual=config, resultados=resultados,
        fuentes={'originales': str(anterior), 'historicas': str(anterior), 'intrames': str(out)},
        codigo_comparacion_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        comprobaciones='Mismos meses, filas de validación y etiquetas, versiones, código de preparación, '
                       'espacio de parámetros, semilla, referencia inicial y 30 trials por variante. '
                       'Ganancias recalculadas desde predicciones.',
        notas='Se reutilizan 60 trials y se ejecutan 30 nuevos. Los nueve intrames se agregan juntos. '
              'La configuración de entrega previa era septiembre; no intervino en train/validación. '
              'Agosto es entrega actual. Sin evaluación de junio. Mejores resultados seleccionados '
              'en mayo, una semilla y protocolo retrospectivo: no prueban significación.'))
    print(tabla[['ganancia', 'delta_vs_originales', 'tp', 'fp', 'contactos']].to_string(), flush=True)
    print('Comparación consolidada:', out, flush=True)
    return out


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anterior', type=Path,
                        default=root / 'tp_primera_entrega/salidas/optuna_20261001_183546_498714')
    parser.add_argument('--intrames-existente', type=Path,
                        help='Consolidar una corrida intrames completa sin volver a entrenar.')
    args = parser.parse_args()
    comparar(root, leer(root / 'tp_primera_entrega/config.json'), args.anterior, args.intrames_existente)
