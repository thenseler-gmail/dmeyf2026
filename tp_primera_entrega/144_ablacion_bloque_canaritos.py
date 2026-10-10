"""Unica ablacion189->181 del bloque congelado en143; sin ruido ni API."""
import importlib
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd

base = importlib.import_module('116_promedio20_hist189')
local = importlib.import_module('63_experimentos_features_local')
DIAG = base.SAL / 'canaritos189_20261010'
OUT = base.SAL / 'ablacion_canaritos181_20261010'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=False)
    r16 = read(base.D16 / 'manifest.json'); lm = read(base.LOCAL / 'manifest.json')
    block = read(DIAG / 'BLOQUE_CONGELADO.json')['campos']
    diag = read(DIAG / 'RESULTADO_LOCAL.json')
    assert diag['estado'] == 'diagnostico_completo_verificado' and block == diag['bloque_debil'] and len(block) == 8
    cols = r16['firma']['features']; remaining = [c for c in cols if c not in block]; seeds = r16['firma']['seeds']
    assert len(cols) == 189 and len(remaining) == 181
    predpath = base.LOCAL / 'historia_1_mes/predicciones_mayo.csv'
    sources = [base.D16 / 'manifest.json', base.LOCAL / 'manifest.json', predpath,
               DIAG / 'PLAN.json', DIAG / 'BLOQUE_CONGELADO.json', DIAG / 'RESULTADO_LOCAL.json']
    plan = dict(fecha='2026-10-10', train=[202104], eval=202105, semillas=seeds,
        features_control=cols, features_candidato=remaining, bloque_retirado=block,
        motivo='Unico bloque fijado por regla de gain abril antes de permutar mayo; efecto pequeno en permutacion. Ensayo de ablacion, no poda de produccion.',
        params=r16['firma']['params'], rounds=273, pesos=dict(lightgbm=.5, tabpfn=.5), umbral=.0275, operador='>',
        unica_diferencia='Retirar ocho variables; sin canaritos ni otras correcciones',
        criterio='Reportar lista promedio5 y media listas individuales, pares, partes, contactos/TP/FP. No otros subconjuntos ni tuning.',
        nuevos_fits=5, api=False, creditos=0, final_agosto=False,
        limitacion='Bloque propuesto por diagnostico en abril/mayo reutilizados; no validacion independiente ni garantia publica. Cambia competencia en feature_fraction.',
        fuentes_sha256={str(p.relative_to(base.ROOT)): base.sha(p) for p in sources},
        codigo_sha256={f: base.sha(base.TP / f) for f in [Path(__file__).name, '63_experimentos_features_local.py',
            '116_promedio20_hist189.py', 'features.py', 'baseline.py']})
    base.save(OUT / 'PLAN.json', plan)
    print('Ablacion181 congelada; reproduciendo control189', flush=True)
    _, oldseeds, train, valid, xt, xv, _ = local.cargar()
    assert oldseeds == seeds
    xt = xt[cols]; xv = xv[cols]
    assert local.matrix_sha(xt) == lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert local.matrix_sha(xv) == lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    assert base.sha(predpath) == lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    old = pd.read_csv(predpath, float_precision='round_trip')
    pd.testing.assert_frame_equal(old[local.KEYS + ['clase_ternaria']], valid[local.KEYS + ['clase_ternaria']])
    controls = []
    for seed in seeds:
        path = base.LOCAL / 'historia_1_mes' / f'seed{seed}.txt'
        assert base.sha(path) == lm['modelos_sha256'][f'historia_1_mes\\seed{seed}.txt']
        q = lgb.Booster(model_file=str(path)).predict(xv, validate_features=True, num_threads=4)
        np.testing.assert_allclose(q, old[f'p_seed{seed}'], rtol=0, atol=1e-15); controls.append(q)
    controls = np.column_stack(controls)
    values, hashes = base.run_models(xt[remaining], xv[remaining], train.clase_ternaria.isin(['BAJA+1', 'BAJA+2']).astype(int),
        seeds, plan['params'], OUT / 'modelos_mayo', OUT / 'sin_reuso', {}, 'Ablacion181')
    y = old.clase_ternaria.eq('BAJA+2').to_numpy(); tab = old.p_tabpfn.to_numpy()
    score0 = .5 * controls.mean(axis=1) + .5 * tab; score1 = .5 * values.mean(axis=1) + .5 * tab
    a = base.metric(y, score0); b = base.metric(y, score1)
    assert a['ganancia_total'] == 275385000
    pairs = []; parts = []
    for i, seed in enumerate(seeds):
        ca = base.metric(y, .5 * controls[:, i] + .5 * tab); cb = base.metric(y, .5 * values[:, i] + .5 * tab)
        pairs.append(dict(seed=seed, control=ca, candidato=cb, delta_total=cb['ganancia_total'] - ca['ganancia_total']))
    for part in sorted(old.parte_cliente.unique()):
        ix = old.parte_cliente.to_numpy() == part; ca = base.metric(y[ix], score0[ix]); cb = base.metric(y[ix], score1[ix])
        parts.append(dict(parte=int(part), control=ca, candidato=cb, delta_total=cb['ganancia_total'] - ca['ganancia_total']))
    delta = b['ganancia_total'] - a['ganancia_total']; mean_delta = float(np.mean([p['delta_total'] for p in pairs]))
    assert sum(p['delta_total'] for p in parts) == delta
    adds = (score1 > base.CUT) & ~(score0 > base.CUT); removes = (score0 > base.CUT) & ~(score1 > base.CUT)
    pred = old[local.KEYS + ['clase_ternaria', 'parte_cliente', 'p_tabpfn']].copy()
    for i, seed in enumerate(seeds):
        pred[f'p_control_seed{seed}'] = controls[:, i]; pred[f'p_181_seed{seed}'] = values[:, i]
    pred['score_control'] = score0; pred['score_181'] = score1; pred.to_csv(OUT / 'predicciones_mayo.csv', index=False)
    reread = pd.read_csv(OUT / 'predicciones_mayo.csv', float_precision='round_trip')
    q = reread[[f'p_181_seed{s}' for s in seeds] + ['p_tabpfn']].to_numpy() @ np.array([.1] * 5 + [.5])
    np.testing.assert_allclose(q, score1, rtol=0, atol=1e-15); assert base.metric(y, q) == b
    result = dict(estado='ablacion_completa_verificada', control=a, candidato=b, delta_total=delta,
        media_delta_listas=mean_delta, semillas_mejoran=sum(p['delta_total'] > 0 for p in pairs),
        partes_mejoran=sum(p['delta_total'] > 0 for p in parts), pareados=pairs, partes=parts,
        bloque_retirado=block, cambios_lista=dict(agregados=int(adds.sum()), retirados=int(removes.sum()),
            tp_agregados=int((adds & y).sum()), tp_retirados=int((removes & y).sum())),
        evidencia_local_positiva=delta > 0 and mean_delta > 0, modelos_sha256=hashes,
        predicciones_sha256=base.sha(OUT / 'predicciones_mayo.csv'), nuevos_fits=5, api=False, creditos=0,
        final_agosto=False, limitacion=plan['limitacion'])
    for p, h in plan['fuentes_sha256'].items():
        assert base.sha(base.ROOT / p) == h
    base.save(OUT / 'RESULTADO_LOCAL.json', result)
    base.save(OUT / 'estado.json', dict(estado=result['estado'], evidencia_local_positiva=result['evidencia_local_positiva']))
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
