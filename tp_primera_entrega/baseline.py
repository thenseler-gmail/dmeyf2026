"""Baseline reproducible: marzo -> mayo. No consulta el test de junio.

Logística múltiple significa varios predictores para un target binario.
Los coeficientes son asociaciones ajustadas, no efectos causales ni p-valores.
"""
from pathlib import Path
from datetime import datetime
import json
import time
import warnings
import importlib.metadata

import duckdb
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, log_loss
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits


def cargar_particiones(root, config):
    split = config['split']
    train_meses = split['train_meses']
    valid_meses = split['validacion_meses']
    if not split['confirmado'] or not train_meses or not valid_meses:
        raise ValueError('Falta confirmar las particiones.')
    if set(train_meses) & set(valid_meses) or max(train_meses) >= min(valid_meses):
        raise ValueError('Particiones temporales incorrectas.')
    meses = train_meses + valid_meses
    if set(meses) & set(split['test_meses']):
        raise ValueError('El baseline no puede utilizar el test.')
    with duckdb.connect() as con:
        con.execute("SET threads=2")
        con.read_csv(str(root / config['dataset'])).create_view('datos')
        df = con.execute(
            'SELECT * FROM datos WHERE foto_mes IN (' + ','.join('?' for _ in meses)
            + ') ORDER BY foto_mes, numero_de_cliente', meses
        ).df()
    if df.duplicated([config['id_col'], config['mes_col']]).any():
        raise ValueError('Claves cliente-mes duplicadas.')
    if df[config['target_col']].isna().any() or not df[config['target_col']].isin(
        ['BAJA+1', 'BAJA+2', 'CONTINUA']
    ).all():
        raise ValueError('Etiquetas incompletas o inválidas.')
    train = df.loc[df.foto_mes.isin(train_meses)].copy()
    valid = df.loc[df.foto_mes.isin(valid_meses)].copy()
    if train.empty or valid.empty:
        raise ValueError('Partición vacía.')
    return train, valid


def preparar(df, features):
    """Reglas fijas, sin estimar estadísticas con validación."""
    x = df[features].astype(float).copy()
    auditoria = {}
    for col in x:
        no_finitos = x[col].notna() & ~np.isfinite(x[col])
        if no_finitos.any():
            auditoria[col + '_no_finitos'] = int(no_finitos.sum())
            x.loc[no_finitos, col] = np.nan
    # El diccionario expresa días al vencimiento del plástico. Más de 100 años
    # vencido es incompatible con ese significado. Regla conservadora explícita,
    # no un código especial confirmado. Preservamos los otros negativos.
    for col in ['Visa_Fvencimiento', 'Master_Fvencimiento']:
        if col in x:
            anomalo = x[col] < -36500
            auditoria[col + '_menor_menos_36500'] = int(anomalo.sum())
            x.loc[anomalo, col] = np.nan
    return x, auditoria


def metricas(y, prob, config):
    premio, error = config['ganancia']['acierto'], config['ganancia']['error']
    umbral = -error / (premio - error)
    seleccion = prob > umbral
    tp = int(((y == 1) & seleccion).sum())
    fp = int(((y == 0) & seleccion).sum())
    return dict(umbral=umbral, contactos=int(seleccion.sum()), tp=tp, fp=fp,
                ganancia=int(tp * premio + fp * error),
                precision=tp / max(1, tp + fp), recall=tp / int(y.sum()),
                average_precision=float(average_precision_score(y, prob)),
                roc_auc=float(roc_auc_score(y, prob)),
                log_loss=float(log_loss(y, prob)))


def crear_lightgbm(config):
    """Parámetros comunes al baseline y a las comparaciones de features."""
    return LGBMClassifier(
        objective='binary', n_estimators=200, learning_rate=0.05,
        num_leaves=15, min_child_samples=100, reg_lambda=1.0,
        random_state=config['seed'], n_jobs=4, verbosity=-1,
        deterministic=True, force_col_wise=True, importance_type='gain')


def ejecutar_baseline(root, config):
    out = root / config['salidas'] / datetime.now().strftime('baseline_%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=False)
    train, valid = cargar_particiones(root, config)
    excluidas = [config['id_col'], config['mes_col'], config['target_col']]
    features = [c for c in train.columns if c not in excluidas]
    xtrain, audit_train = preparar(train, features)
    xvalid, audit_valid = preparar(valid, features)
    ytrain = train[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    yvalid = valid[config['target_col']].eq(config['clase_positiva']).astype(int).to_numpy()
    if len(np.unique(ytrain)) != 2 or len(np.unique(yvalid)) != 2:
        raise ValueError('Ambas particiones deben contener positivos y negativos.')
    categoricas = [c for c in ['Visa_status', 'Master_status', 'tcuentas'] if c in features]
    numericas = [c for c in features if c not in categoricas]
    preproceso = ColumnTransformer([
        ('numericas', Pipeline([
            ('imputar', SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True)),
            ('escalar', StandardScaler()),
        ]), numericas),
        ('categoricas', Pipeline([
            ('imputar', SimpleImputer(strategy='constant', fill_value=-1, keep_empty_features=True)),
            ('codificar', OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False)),
        ]), categoricas),
    ])
    modelos = {
        'logistica': Pipeline([
            ('preparar', preproceso),
            ('modelo', LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000,
                                           random_state=config['seed'])),
        ]),
        'lightgbm': crear_lightgbm(config),
    }
    resultados = {}
    predicciones = valid[excluidas].copy()
    manifest = dict(config=config, features=features, categoricas=categoricas,
                    filas_train=len(train), filas_validacion=len(valid),
                    positivos_train=int(ytrain.sum()), positivos_validacion=int(yvalid.sum()),
                    auditoria_train=audit_train, auditoria_validacion=audit_valid,
                    versiones={k: importlib.metadata.version(k) for k in
                               ['lightgbm', 'scikit-learn', 'pandas', 'numpy', 'duckdb']},
                    notas='Sin balanceo, Optuna ni ajuste de umbral; sin consulta al test. '
                          'Importancia LightGBM por ganancia de splits, no ganancia monetaria. '
                          'Coeficientes numéricos por desvío estándar tras imputación; '
                          'categóricos contra la categoría de referencia. Sin inferencia causal.')
    for nombre, modelo in modelos.items():
        print(f'Entrenando {nombre}: {len(train):,} filas, {len(features)} variables...', flush=True)
        xt, xv = xtrain.copy(), xvalid.copy()
        if nombre == 'lightgbm':
            for col in categoricas:
                categorias = sorted(xt[col].dropna().unique())
                xt[col] = pd.Categorical(xt[col], categories=categorias)
                xv[col] = pd.Categorical(xv[col], categories=categorias)
        inicio = time.perf_counter()
        with threadpool_limits(limits=4), warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter('always', ConvergenceWarning)
            modelo.fit(xt, ytrain)
        prob = modelo.predict_proba(xv)[:, 1]
        if not np.isfinite(prob).all() or not ((prob >= 0) & (prob <= 1)).all():
            raise ValueError('Probabilidades inválidas.')
        resultados[nombre] = metricas(yvalid, prob, config)
        resultados[nombre]['segundos'] = time.perf_counter() - inicio
        resultados[nombre]['avisos'] = [str(w.message) for w in avisos]
        predicciones['p_' + nombre] = prob
        if nombre == 'logistica':
            fitted = modelo.named_steps['modelo']
            coef = fitted.coef_[0]
            tabla = pd.DataFrame({'variable': preproceso.get_feature_names_out(),
                                  'coeficiente': coef, 'magnitud': abs(coef)})
            tabla['odds_ratio'] = np.exp(coef)
            resultados[nombre]['iteraciones'] = int(fitted.n_iter_[0])
            resultados[nombre]['intercepto'] = float(fitted.intercept_[0])
            manifest['referencias_categoricas'] = {
                col: float(cats[0]) for col, cats in zip(categoricas,
                    preproceso.named_transformers_['categoricas'].named_steps['codificar'].categories_)}
            tabla.sort_values('magnitud', ascending=False).to_csv(out / 'coeficientes_logistica.csv', index=False)
        else:
            pd.DataFrame({'variable': features, 'ganancia_splits': modelo.feature_importances_}).sort_values(
                'ganancia_splits', ascending=False).to_csv(out / 'importancias_lightgbm.csv', index=False)
            modelo.booster_.save_model(str(out / 'lightgbm.txt'))
        import joblib
        joblib.dump(modelo, out / (nombre + '.joblib'))
        manifest[nombre + '_parametros'] = modelo.get_params()
        (out / 'resultados.json').write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding='utf-8')
        print(nombre, resultados[nombre], flush=True)
    predicciones.to_csv(out / 'predicciones_validacion.csv', index=False)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print('Resultados guardados en', out, flush=True)
    return out
