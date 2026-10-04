"""30 trials por variante LightGBM y un Random Forest de referencia.

Experimento retrospectivo separado: abril train, mayo validación. Junio excluido.
No optimiza el umbral (0,025) ni ejecuta la evaluación final.
Uso: .venv/Scripts/python.exe tp_primera_entrega/05_optuna_historicas_rf.py
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import time

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

from baseline import cargar_particiones, crear_lightgbm, preparar, metricas
from features import HISTORICAS, BLOQUES, agregar_intrames


def guardar_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def ejecutar(root, config, n_trials=30, resume=None, variantes=None, incluir_rf=True):
    if n_trials < 1:
        raise ValueError('n_trials debe ser positivo.')
    variantes = ['originales', 'historicas'] if variantes is None else list(variantes)
    if not variantes or len(set(variantes)) != len(variantes) or set(variantes) - {'originales', 'historicas', 'intrames'}:
        raise ValueError('Variantes inválidas.')
    experimental = deepcopy(config)
    experimental['split'].update(train_meses=[202104], validacion_meses=[202105],
                                  reentrenamiento_meses=[],
                                  tipo_evaluacion='Retrospectiva abril -> mayo; etiquetas de abril disponibles en junio')
    experimental['optimizacion']['n_trials'] = n_trials
    train, valid = cargar_particiones(root, experimental)
    cargar_historia = importlib.import_module('04_comparar_historicas').cargar_historia
    historia = cargar_historia(root, experimental)
    claves = [config['id_col'], config['mes_col']]
    excluidas = claves + [config['target_col']]
    originales = [c for c in train if c not in excluidas]
    nuevas = [c for c in historia if c not in claves + HISTORICAS]
    train = train.merge(historia[claves + nuevas], on=claves, how='left', validate='one_to_one')
    valid = valid.merge(historia[claves + nuevas], on=claves, how='left', validate='one_to_one')
    if train.historial_mes_anterior_disponible.isna().any() or valid.historial_mes_anterior_disponible.isna().any():
        raise ValueError('Falló el enlace con la historia.')
    xt, audit_train = preparar(train, originales + nuevas)
    xv, audit_valid = preparar(valid, originales + nuevas)
    intrames = []
    if 'intrames' in variantes:
        xt = agregar_intrames(xt, list(BLOQUES))
        xv = agregar_intrames(xv, list(BLOQUES))
        intrames = [c for b in BLOQUES.values() for c in b]
    yt = train[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    yv = valid[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    if len(np.unique(yt)) != 2 or len(np.unique(yv)) != 2:
        raise ValueError('Faltan clases en alguna partición.')
    categoricas = [c for c in ['Visa_status', 'Master_status', 'tcuentas'] if c in originales]
    xtrf, xvrf = xt[originales].copy(), xv[originales].copy()
    for c in categoricas:
        categorias = sorted(xt[c].dropna().unique())
        xt[c] = pd.Categorical(xt[c], categories=categorias)
        xv[c] = pd.Categorical(xv[c], categories=categorias)
    out = Path(resume).resolve() if resume else root / config['salidas'] / datetime.now().strftime('optuna_%Y%m%d_%H%M%S_%f')
    if resume:
        anterior = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
        if anterior['config_experimental'] != experimental:
            raise ValueError('La configuración no coincide con el estudio a recuperar.')
    else:
        out.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        config_experimental=experimental, n_trials_por_variante=n_trials,
        variantes=variantes, incluir_rf=incluir_rf, intrames=intrames,
        filas_train=len(train), filas_validacion=len(valid),
        positivos_train=int(yt.sum()), positivos_validacion=int(yv.sum()),
        originales=originales, nuevas=nuevas, categoricas=categoricas,
        auditoria_train=audit_train, auditoria_validacion=audit_valid,
        versiones={k: importlib.metadata.version(k) for k in
                   ['lightgbm', 'optuna', 'scikit-learn', 'numpy', 'pandas', 'duckdb']},
        codigo_sha256={p: hashlib.sha256((Path(__file__).parent / p).read_bytes()).hexdigest()
                       for p in ['05_optuna_historicas_rf.py', '04_comparar_historicas.py', 'baseline.py', 'features.py']},
        notas='Cada estudio: mismo espacio y cantidad de trials, TPE con semilla fija; '
              'las sugerencias pueden divergir porque cada estudio observa resultados distintos. '
              'Sin pruning ni early stopping; igual presupuesto de intentos, no de segundos. '
              'RF es una referencia sin tuning, no una comparación de presupuestos iguales. '
              'Umbral fijo 0,025. Mejor ganancia elegida en mayo: estimación optimista, no test. '
              'Protocolo retrospectivo. Junio no se consulta. Sin balanceo de clases.')
    if resume:
        # Conserva el manifest original y documenta código/entorno de recuperación.
        manifest['recuperacion'] = dict(fecha=datetime.now().isoformat(),
            nota='Proceso anterior terminado. Trial interrumpido se marca FAIL y se reintenta. '
                 'Se reinicia el sampler TPE con la misma semilla: la secuencia posterior '
                 'puede diferir de una corrida sin interrupción.')
        guardar_json(out / ('recuperacion_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json'), manifest)
        predicciones = pd.read_csv(out / 'predicciones_validacion.csv')
        if not predicciones[excluidas].equals(valid[excluidas].reset_index(drop=True)):
            raise ValueError('Las filas guardadas no coinciden con la validación actual.')
        resultados = json.loads((out / 'resultados.json').read_text(encoding='utf-8'))
    else:
        guardar_json(out / 'manifest.json', manifest)
        predicciones = valid[excluidas].copy()
        resultados = {}
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage = 'sqlite:///' + (out / 'estudios.db').resolve().as_posix()
    print('Salida:', out, flush=True)
    referencia = dict(n_estimators=200, learning_rate=0.05, num_leaves=15,
                      min_child_samples=100, reg_lambda=1.0,
                      colsample_bytree=1.0, subsample=1.0)
    columnas_por_variante = {'originales': originales, 'historicas': originales + nuevas,
                            'intrames': originales + intrames}
    for nombre in variantes:
        columnas = columnas_por_variante[nombre]
        study = optuna.create_study(study_name=nombre, storage=storage, direction='maximize', load_if_exists=bool(resume),
                                   sampler=optuna.samplers.TPESampler(seed=config['seed']))
        # El primer intento reproduce el baseline; el presupuesto lo incluye.
        if not study.trials:
            study.enqueue_trial(referencia)
        if resume and study.get_trials(states=[optuna.trial.TrialState.RUNNING]):
            raise RuntimeError('Hay trials RUNNING: comprobar el proceso antes de recuperar; no se alteró su estado.')
        completos = len(study.get_trials(states=[optuna.trial.TrialState.COMPLETE]))
        mejor = study.best_value if completos else -float('inf')
        inicio_estudio = time.perf_counter()

        def objective(trial):
            nonlocal mejor
            params = dict(
                n_estimators=trial.suggest_int('n_estimators', 100, 400, step=50),
                learning_rate=trial.suggest_float('learning_rate', 0.015, 0.12, log=True),
                num_leaves=trial.suggest_categorical('num_leaves', [7, 15, 31, 63]),
                min_child_samples=trial.suggest_int('min_child_samples', 30, 500, log=True),
                reg_lambda=trial.suggest_float('reg_lambda', 0.0001, 20.0, log=True),
                colsample_bytree=trial.suggest_float('colsample_bytree', 0.7, 1.0),
                subsample=trial.suggest_float('subsample', 0.7, 1.0))
            modelo = crear_lightgbm(experimental).set_params(
                **params, subsample_freq=1 if params['subsample'] < 1.0 else 0)
            inicio = time.perf_counter()
            with threadpool_limits(limits=4):
                modelo.fit(xt[columnas], yt)
                prob = modelo.predict_proba(xv[columnas])[:, 1]
            if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
                raise ValueError('Probabilidades inválidas.')
            r = metricas(yv, prob, experimental)
            r['segundos'] = time.perf_counter() - inicio
            trial.set_user_attr('metricas', r)
            if r['ganancia'] > mejor:
                mejor = r['ganancia']
                modelo.booster_.save_model(str(out / f'lightgbm_{nombre}.txt'))
                predicciones['p_' + nombre] = prob
                predicciones.to_csv(out / 'predicciones_validacion.csv', index=False)
                pd.DataFrame({'variable': columnas, 'ganancia_splits': modelo.feature_importances_}).sort_values(
                    'ganancia_splits', ascending=False).to_csv(out / f'importancias_{nombre}.csv', index=False)
            print(f'{nombre} trial {trial.number + 1}/{n_trials}: '
                  f'ganancia={r["ganancia"]:,}; mejor={mejor:,}', flush=True)
            return r['ganancia']

        faltan = max(0, n_trials - completos)
        if faltan:
            study.optimize(objective, n_trials=faltan, n_jobs=1, gc_after_trial=True)
        study.trials_dataframe().to_csv(out / f'trials_{nombre}.csv', index=False)
        resultados[nombre] = dict(**study.best_trial.user_attrs['metricas'],
                                  mejor_trial=study.best_trial.number,
                                  parametros=study.best_params,
                                  trials_completos=len(study.get_trials(states=[optuna.trial.TrialState.COMPLETE])),
                                  trials_fallidos=len(study.get_trials(states=[optuna.trial.TrialState.FAIL])),
                                  segundos_estudio=resultados.get(nombre, {}).get('segundos_estudio', 0)
                                                   + time.perf_counter() - inicio_estudio)
        guardar_json(out / 'resultados.json', resultados)

    if not incluir_rf:
        pd.DataFrame(resultados).T.drop(columns=['parametros']).to_csv(out / 'comparacion.csv', index_label='modelo')
        print('Resultados guardados:', out, flush=True)
        return out

    # RF sobre los mismos datos de abril/mayo, con originales y sin balancear.
    print('Entrenando Random Forest de referencia (300 árboles)...', flush=True)
    numericas = [c for c in originales if c not in categoricas]
    pre = ColumnTransformer([
        ('numericas', SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True), numericas),
        ('categoricas', Pipeline([
            ('imputar', SimpleImputer(strategy='constant', fill_value=-1)),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
        ]), categoricas),
    ])
    rf_params = dict(n_estimators=300, max_depth=12, min_samples_leaf=50,
                     max_features='sqrt', n_jobs=4, random_state=config['seed'])
    rf = Pipeline([('preparar', pre), ('modelo', RandomForestClassifier(**rf_params))])
    inicio = time.perf_counter()
    with threadpool_limits(limits=4):
        rf.fit(xtrf, yt)
        prob = rf.predict_proba(xvrf)[:, 1]
    resultados['random_forest'] = dict(**metricas(yv, prob, experimental),
                                      segundos=time.perf_counter() - inicio, parametros=rf_params)
    joblib.dump(rf, out / 'random_forest.joblib')
    predicciones['p_random_forest'] = prob
    predicciones.to_csv(out / 'predicciones_validacion.csv', index=False)
    guardar_json(out / 'resultados.json', resultados)
    pd.DataFrame(resultados).T.drop(columns=['parametros']).to_csv(out / 'comparacion.csv', index_label='modelo')
    print('Resultados finales:', json.dumps(resultados, ensure_ascii=False), flush=True)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=30)
    parser.add_argument('--resume', type=Path, help='Carpeta de una corrida interrumpida; detener el proceso previo antes de usar.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    ejecutar(root, config, args.trials, args.resume)
