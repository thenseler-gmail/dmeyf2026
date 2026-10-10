"""Canaritos189: cinco fits, control reproducido y permutacion de bloques mayo."""
import importlib
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

base = importlib.import_module('116_promedio20_hist189')
local = importlib.import_module('63_experimentos_features_local')
OUT = base.SAL / 'canaritos189_20261010'
N_NOISE = 19
NOISE_SEEDS = [2026101001, 2026101002]
PERM_SEEDS = [2026101011, 2026101012, 2026101013]


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def evaluate(y, ycombined, probabilities, tab):
    mean = probabilities.mean(axis=1)
    score = .5 * mean + .5 * tab
    return dict(**base.metric(y, score), ap_lgb_target_combinado=float(average_precision_score(ycombined, mean)),
                ap_ensemble_baja2=float(average_precision_score(y, score)))


def main():
    OUT.mkdir(exist_ok=False); (OUT / 'modelos_mayo').mkdir()
    m16 = read(base.D16 / 'manifest.json'); lm = read(base.LOCAL / 'manifest.json')
    cols = m16['firma']['features']; seeds = m16['firma']['seeds']
    noise_cols = [f'canarito_{i:02d}' for i in range(1, N_NOISE + 1)]
    assert len(cols) == 189 and len(seeds) == 5 and not set(cols) & set(noise_cols)
    pathpred = base.LOCAL / 'historia_1_mes/predicciones_mayo.csv'
    sources = [base.D16 / 'manifest.json', base.LOCAL / 'manifest.json', pathpred]
    plan = dict(fecha='2026-10-10', autorizacion='Usuario: bueno, dale..vamos con los canaritos',
        train=[202104], eval=202105, semillas_modelos=seeds, params=m16['firma']['params'], rounds=273,
        features=cols, canaritos=noise_cols, semillas_ruido=NOISE_SEEDS,
        ruido='Uniforme(0,1) float32 con RNG independientes abril/mayo; mismo ruido para los cinco modelos; sin usar labels/IDs',
        regla_debiles='Gain real <= mediana gain19canaritos en >=4/5 modelos; ordenar por mediana porcentaje gain y nombre; maximo8variables',
        comprobacion='Permutar conjuntamente bloque debil y, por separado, bloque19canaritos en mayo completo;3permutaciones fijas. No elegir otro bloque segun mayo.',
        semillas_permutacion=PERM_SEEDS, metricas_permutacion=['AP LightGBM target combinado', 'AP ensemble BAJA+2', 'ganancia ensemble'],
        pesos=dict(lightgbm=.5, tabpfn=.5), umbral=.0275, operador='>',
        nuevos_fits_max=5, api=False, creditos=0, final_agosto=False, poda_automatica=False,
        politica='Diagnostico solamente: no ablar/reentrenar otro bloque ni preparar submits en este script.',
        limitaciones='Canaritos continuos favorecidos por oportunidades de corte; correlacion puede reducir importancia real. Agregarlos cambia competencia bajo feature_fraction. Mayo/semillas reutilizados; no test independiente.',
        fuentes_sha256={str(p.relative_to(base.ROOT)): base.sha(p) for p in sources},
        codigo_sha256={f: base.sha(base.TP / f) for f in [Path(__file__).name, '63_experimentos_features_local.py',
            '116_promedio20_hist189.py', 'baseline.py', 'features.py']})
    base.save(OUT / 'PLAN.json', plan); print('Plan congelado; reconstruyendo matrices y control', flush=True)
    _, oldseeds, train, valid, xt, xv, _ = local.cargar()
    assert oldseeds == seeds
    xt = xt[cols]; xv = xv[cols]
    assert local.matrix_sha(xt) == lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert local.matrix_sha(xv) == lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    assert base.sha(pathpred) == lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    old = pd.read_csv(pathpred, float_precision='round_trip')
    pd.testing.assert_frame_equal(old[local.KEYS + ['clase_ternaria']], valid[local.KEYS + ['clase_ternaria']])
    ytrain = train.clase_ternaria.isin(['BAJA+1', 'BAJA+2']).astype(int).to_numpy()
    ycombined = valid.clase_ternaria.isin(['BAJA+1', 'BAJA+2']).to_numpy()
    y = valid.clase_ternaria.eq('BAJA+2').to_numpy(); tab = old.p_tabpfn.to_numpy()
    controls = []
    for seed in seeds:
        p = base.LOCAL / 'historia_1_mes' / f'seed{seed}.txt'
        assert base.sha(p) == lm['modelos_sha256'][f'historia_1_mes\\seed{seed}.txt']
        model = lgb.Booster(model_file=str(p))
        q = model.predict(xv, validate_features=True, num_threads=4)
        np.testing.assert_allclose(q, old[f'p_seed{seed}'], rtol=0, atol=1e-15); controls.append(q)
    controls = np.column_stack(controls)
    control_metric = evaluate(y, ycombined, controls, tab)
    assert control_metric['ganancia_total'] == 275385000
    noise_train = np.random.default_rng(NOISE_SEEDS[0]).random((len(xt), N_NOISE), dtype=np.float32)
    noise_valid = np.random.default_rng(NOISE_SEEDS[1]).random((len(xv), N_NOISE), dtype=np.float32)
    np.savez_compressed(OUT / 'ruido.npz', train=noise_train, valid=noise_valid)
    for i, field in enumerate(noise_cols):
        xt[field] = noise_train[:, i]; xv[field] = noise_valid[:, i]
    assert list(xt) == list(xv) == cols + noise_cols
    base.save(OUT / 'MATRICES.json', dict(train=local.matrix_sha(xt), mayo=local.matrix_sha(xv), ruido_sha256=base.sha(OUT / 'ruido.npz')))
    importances = []; values = []; models = []; hashes = {}; pairs = []
    base.save(OUT / 'estado.json', dict(estado='entrenando_diagnostico', fits_completados=0, api=False))
    for seed in seeds:
        start = time.perf_counter()
        model = lgb.train(dict(plan['params'], seed=seed), lgb.Dataset(xt, label=ytrain), num_boost_round=273)
        path = OUT / 'modelos_mayo' / f'seed{seed}.txt'; model.save_model(str(path))
        reloaded = lgb.Booster(model_file=str(path))
        assert model.num_trees() == reloaded.num_trees() == 273 and reloaded.feature_name() == list(xt)
        q = model.predict(xv, validate_features=True, num_threads=4)
        np.testing.assert_array_equal(q, reloaded.predict(xv, validate_features=True, num_threads=4))
        assert np.isfinite(q).all() and ((q >= 0) & (q <= 1)).all()
        models.append(reloaded); values.append(q); hashes[path.name] = base.sha(path)
        gains = reloaded.feature_importance('gain'); splits = reloaded.feature_importance('split')
        threshold = float(np.median(gains[-N_NOISE:]))
        for i, field in enumerate(reloaded.feature_name()):
            importances.append(dict(seed=seed, campo=field, canarito=field in noise_cols,
                gain=float(gains[i]), gain_pct=float(100 * gains[i] / gains.sum()), splits=int(splits[i]),
                mediana_gain_canaritos=threshold, debajo_mediana_canaritos=bool(gains[i] <= threshold)))
        base.save(OUT / 'estado.json', dict(estado='entrenando_diagnostico', fits_completados=len(models), api=False))
        print('Canaritos modelo', seed, 'completo', round(time.perf_counter() - start, 1), 's', flush=True)
    imp = pd.DataFrame(importances); imp.to_csv(OUT / 'importancias_semilla.csv', index=False)
    ranking = imp.groupby(['campo', 'canarito'], sort=False).agg(mediana_gain_pct=('gain_pct', 'median'),
        semillas_debajo_ruido=('debajo_mediana_canaritos', 'sum'), mediana_splits=('splits', 'median')).reset_index()
    ranking = ranking.sort_values(['mediana_gain_pct', 'campo'])
    ranking.to_csv(OUT / 'ranking_diagnostico.csv', index=False)
    weak = ranking.loc[~ranking.canarito & ranking.semillas_debajo_ruido.ge(4)].head(8).campo.tolist()
    # Freeze the sole block before computing any May permutation result.
    base.save(OUT / 'BLOQUE_CONGELADO.json', dict(campos=weak, origen='regla PLAN y gain entrenamiento abril exclusivamente',
        sin_poda_automatica=True, ranking_sha256=base.sha(OUT / 'ranking_diagnostico.csv')))
    values = np.column_stack(values); noise_metric = evaluate(y, ycombined, values, tab)
    print('Bloque debil congelado:', weak, flush=True)
    permutations = []
    base.save(OUT / 'estado.json', dict(estado='permutaciones_bloques_mayo', fits_completados=5, bloque=weak, api=False))
    for name, fields in [('debil', weak), ('canaritos', noise_cols)]:
        if not fields:
            continue
        for permseed in PERM_SEEDS:
            start = time.perf_counter(); changed = xv.copy()
            order = np.random.default_rng(permseed).permutation(len(changed))
            changed[fields] = xv[fields].to_numpy()[order]
            pd.testing.assert_frame_equal(changed.drop(columns=fields), xv.drop(columns=fields))
            probabilities = np.column_stack([model.predict(changed, validate_features=True, num_threads=4) for model in models])
            met = evaluate(y, ycombined, probabilities, tab)
            permutations.append(dict(bloque=name, campos=fields, semilla_permutacion=permseed, metricas=met,
                perdida_ap_combinado=noise_metric['ap_lgb_target_combinado'] - met['ap_lgb_target_combinado'],
                perdida_ap_baja2=noise_metric['ap_ensemble_baja2'] - met['ap_ensemble_baja2'],
                perdida_ganancia_total=noise_metric['ganancia_total'] - met['ganancia_total']))
            print('Permutacion', name, permseed, 'completa', round(time.perf_counter() - start, 1), 's', flush=True)
    score0 = .5 * controls.mean(axis=1) + .5 * tab
    score1 = .5 * values.mean(axis=1) + .5 * tab
    for i, seed in enumerate(seeds):
        a = base.metric(y, .5 * controls[:, i] + .5 * tab)
        b = base.metric(y, .5 * values[:, i] + .5 * tab)
        pairs.append(dict(seed=seed, control=a, con_ruido=b, delta_total=b['ganancia_total'] - a['ganancia_total']))
    parts = []
    for part in sorted(old.parte_cliente.unique()):
        ix = old.parte_cliente.to_numpy() == part
        a = base.metric(y[ix], score0[ix]); b = base.metric(y[ix], score1[ix])
        parts.append(dict(parte=int(part), control=a, con_ruido=b, delta_total=b['ganancia_total'] - a['ganancia_total']))
    pred = old[local.KEYS + ['clase_ternaria', 'parte_cliente', 'p_tabpfn']].copy()
    for i, seed in enumerate(seeds):
        pred[f'p_control_seed{seed}'] = controls[:, i]; pred[f'p_canaritos_seed{seed}'] = values[:, i]
    pred['score_control'] = score0; pred['score_canaritos'] = score1
    pred.to_csv(OUT / 'predicciones_mayo.csv', index=False)
    reread = pd.read_csv(OUT / 'predicciones_mayo.csv', float_precision='round_trip')
    q = reread[[f'p_canaritos_seed{s}' for s in seeds] + ['p_tabpfn']].to_numpy() @ np.array([.1] * 5 + [.5])
    np.testing.assert_allclose(q, score1, rtol=0, atol=1e-15)
    assert base.metric(y, q)['ganancia_total'] == noise_metric['ganancia_total']
    result = dict(estado='diagnostico_completo_verificado', control=control_metric, con_canaritos=noise_metric,
        delta_total=noise_metric['ganancia_total'] - control_metric['ganancia_total'],
        media_delta_listas=float(np.mean([r['delta_total'] for r in pairs])), pareados=pairs, partes=parts,
        bloque_debil=weak, permutaciones=permutations, modelos_sha256=hashes,
        nuevos_fits=5, api=False, creditos=0, final_agosto=False, poda_ejecutada=False,
        limitaciones=plan['limitaciones'], predicciones_sha256=base.sha(OUT / 'predicciones_mayo.csv'))
    assert sum(r['delta_total'] for r in parts) == result['delta_total']
    for p, h in plan['fuentes_sha256'].items():
        assert base.sha(base.ROOT / p) == h
    base.save(OUT / 'RESULTADO_LOCAL.json', result)
    base.save(OUT / 'estado.json', dict(estado=result['estado'], fits_completados=5, api=False, bloque_debil=weak))
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
