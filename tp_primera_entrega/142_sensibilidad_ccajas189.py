"""Mayo ccajas=0 vs NA: mismos cinco LGB189 y Tab202, sin fits/API."""
import importlib
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from calidad_datos import corregir_datos
from features import HISTORICAS, HISTORICAS_EXTRA

base = importlib.import_module('116_promedio20_hist189')
local = importlib.import_module('63_experimentos_features_local')
OUT = base.SAL / 'sensibilidad_ccajas189_20261010_v2'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=False)
    lm = read(base.LOCAL / 'manifest.json')
    m16 = read(base.D16 / 'manifest.json')
    cols = m16['firma']['features']; seeds = m16['firma']['seeds']
    assert len(cols) == 189 and len(seeds) == 5
    assert 'ccajas_depositos' not in HISTORICAS + HISTORICAS_EXTRA
    lp = base.LOCAL / 'historia_1_mes/predicciones_mayo.csv'
    sources = [base.LOCAL / 'manifest.json', base.D16 / 'manifest.json', lp,
               base.SAL / 'auditoria_calidad_drift_20261010_v3/CONCLUSION.json']
    plan = dict(fecha='2026-10-10', autorizacion='Usuario dale a sensibilidad ccajas de mayo con modelos guardados',
                train=[202104], eval=202105, semillas=seeds, features=cols,
                unica_diferencia='ccajas_depositos mayo cero->NA; abril y todas las otras variables sin cambios',
                pesos=dict(lightgbm=.5, tabpfn=.5), umbral=.0275, operador='>',
                target_lightgbm='BAJA+1/BAJA+2', target_tabpfn='BAJA+2',
                modelos_reutilizados=5, nuevos_fits=0, api=False, creditos=0, final_agosto=False,
                criterio='Informar delta lista promedio5, media listas individuales, TP/FP/contactos, semillas y partes. Sin ajuste de corte.',
                alcance='Sensibilidad de inferencia; no efecto de entrenar abril+mayo corregidos ni garantia publica.',
                fuentes_sha256={str(p.relative_to(base.ROOT)): base.sha(p) for p in sources},
                codigo_sha256={f: base.sha(base.TP / f) for f in [Path(__file__).name,
                    'calidad_datos.py', 'baseline.py', 'features.py', '116_promedio20_hist189.py',
                    '63_experimentos_features_local.py']})
    base.save(OUT / 'PLAN.json', plan)
    base.save(OUT / 'estado.json', dict(estado='reproduciendo_control', fits=0, api=False))
    print('Plan congelado; reconstruyendo control abril->mayo', flush=True)
    _, oldseeds, train, valid, xt, xv, _ = local.cargar()
    assert seeds == oldseeds
    xt = xt[cols]; xv = xv[cols]
    assert local.matrix_sha(xt) == lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert local.matrix_sha(xv) == lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    assert base.sha(lp) == lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    old = pd.read_csv(lp, float_precision='round_trip')
    keys = local.KEYS + ['clase_ternaria']
    pd.testing.assert_frame_equal(old[keys], valid[keys])
    corrected_train, audit_train = corregir_datos(train)
    corrected_valid, audit_valid = corregir_datos(valid)
    pd.testing.assert_frame_equal(corrected_train, train, check_dtype=False)
    pd.testing.assert_frame_equal(corrected_valid.drop(columns='ccajas_depositos'), valid.drop(columns='ccajas_depositos'))
    pd.testing.assert_frame_equal(xt, preparar(corrected_train, cols)[0])
    candidate_x = preparar(corrected_valid, cols)[0]
    pd.testing.assert_frame_equal(candidate_x.drop(columns='ccajas_depositos'), xv.drop(columns='ccajas_depositos'))
    assert xv.ccajas_depositos.eq(0).all() and candidate_x.ccajas_depositos.isna().all()
    controls = []; candidates = []; hashes = {}; uses = []
    for seed in seeds:
        path = base.LOCAL / 'historia_1_mes' / f'seed{seed}.txt'
        assert base.sha(path) == lm['modelos_sha256'][f'historia_1_mes\\seed{seed}.txt']
        model = lgb.Booster(model_file=str(path))
        assert model.feature_name() == cols and model.num_trees() == 273
        q0 = model.predict(xv, validate_features=True, num_threads=4)
        np.testing.assert_allclose(q0, old[f'p_seed{seed}'], rtol=0, atol=1e-15)
        q1 = model.predict(candidate_x, validate_features=True, num_threads=4)
        assert np.isfinite(q1).all() and ((q1 >= 0) & (q1 <= 1)).all()
        splits = int(model.feature_importance('split')[cols.index('ccajas_depositos')])
        if splits == 0:
            np.testing.assert_array_equal(q0, q1)
        uses.append(dict(seed=seed, splits_ccajas=splits, probabilidades_cambian=int((q0 != q1).sum())))
        controls.append(q0); candidates.append(q1)
        hashes[str(path.relative_to(base.ROOT))] = base.sha(path)
        print('Modelo reutilizado', seed, 'splits ccajas', splits, 'probabilidades modificadas', uses[-1]['probabilidades_cambian'], flush=True)
    controls = np.column_stack(controls); candidates = np.column_stack(candidates)
    tab = old.p_tabpfn.to_numpy(); y = old.clase_ternaria.eq('BAJA+2').to_numpy()
    score0 = .5 * controls.mean(axis=1) + .5 * tab
    score1 = .5 * candidates.mean(axis=1) + .5 * tab
    a = base.metric(y, score0); b = base.metric(y, score1)
    assert a['ganancia_total'] == 275385000 and a['contactos'] == 9906 and a['tp'] == 498
    paired = []; parts = []
    for i, seed in enumerate(seeds):
        aa = base.metric(y, .5 * controls[:, i] + .5 * tab)
        bb = base.metric(y, .5 * candidates[:, i] + .5 * tab)
        paired.append(dict(seed=seed, control=aa, candidato=bb, delta_total=bb['ganancia_total'] - aa['ganancia_total']))
    for part in sorted(old.parte_cliente.unique()):
        ix = old.parte_cliente.to_numpy() == part
        aa = base.metric(y[ix], score0[ix]); bb = base.metric(y[ix], score1[ix])
        parts.append(dict(parte=int(part), control=aa, candidato=bb, delta_total=bb['ganancia_total'] - aa['ganancia_total']))
    delta = b['ganancia_total'] - a['ganancia_total']
    assert sum(r['delta_total'] for r in parts) == delta
    pred = old[local.KEYS + ['clase_ternaria', 'parte_cliente', 'p_tabpfn']].copy()
    for i, seed in enumerate(seeds):
        pred[f'p_control_seed{seed}'] = controls[:, i]
        pred[f'p_ccajas_na_seed{seed}'] = candidates[:, i]
    pred['score_control'] = score0; pred['score_ccajas_na'] = score1
    pred.to_csv(OUT / 'predicciones_mayo.csv', index=False)
    reread = pd.read_csv(OUT / 'predicciones_mayo.csv', float_precision='round_trip')
    independent = reread[[f'p_ccajas_na_seed{s}' for s in seeds] + ['p_tabpfn']].to_numpy() @ np.array([.1] * 5 + [.5])
    np.testing.assert_allclose(independent, score1, rtol=0, atol=1e-15)
    assert base.metric(y, independent) == b
    select0 = score0 > base.CUT; select1 = score1 > base.CUT
    adds = select1 & ~select0; removes = select0 & ~select1
    mean_delta = float(np.mean([r['delta_total'] for r in paired]))
    result = dict(estado='completo_verificado', control=a, candidato=b, delta_total=delta, delta_25pct=delta / 4,
                  media_delta_listas_individuales=mean_delta, semillas_mejoran=sum(r['delta_total'] > 0 for r in paired),
                  partes_mejoran=sum(r['delta_total'] > 0 for r in parts), pareados=paired, partes=parts, uso_modelos=uses,
                  cambios_lista=dict(agregados=int(adds.sum()), retirados=int(removes.sum()),
                                      tp_agregados=int((adds & y).sum()), tp_retirados=int((removes & y).sum())),
                  correccion=dict(train=audit_train, mayo=audit_valid), nuevos_fits=0, api=False, creditos=0,
                  final_agosto=False, modelos_sha256=hashes, predicciones_sha256=base.sha(OUT / 'predicciones_mayo.csv'),
                  matrices=dict(train_control=local.matrix_sha(xt), mayo_control=local.matrix_sha(xv), mayo_candidato=local.matrix_sha(candidate_x)),
                  evidencia_positiva=delta > 0 and mean_delta > 0,
                  limitacion='Sensibilidad de inferencia abril->mayo reutilizado; no mide entrenar abril+mayo corregidos ni garantiza publico. TabPFN sigue sin corregir.')
    base.save(OUT / 'RESULTADO_LOCAL.json', result)
    pd.DataFrame([dict(seed=r['seed'], control_total=r['control']['ganancia_total'], candidato_total=r['candidato']['ganancia_total'], delta_total=r['delta_total']) for r in paired]).to_csv(OUT / 'pares_semillas.csv', index=False)
    pd.DataFrame(parts).to_json(OUT / 'partes.json', orient='records', indent=2)
    fmt = lambda n: ('$' + f'{n:,.0f}').replace(',', '.')
    note = '# Sensibilidad de depósitos de caja sobre LightGBM189\n\n'
    note += f"Control promedio5: {fmt(a['ganancia_total'])}, {a['contactos']} contactos, {a['tp']} BAJA+2. Candidato mayo=NA: {fmt(b['ganancia_total'])}, {b['contactos']} contactos, {b['tp']} BAJA+2. Diferencia total: {fmt(delta)}; diferencia25%: {fmt(delta / 4)}.\n\n"
    note += f"Media de diferencias en cinco listas individuales: {fmt(mean_delta)}. Mejoran {result['semillas_mejoran']}/5 semillas y {result['partes_mejoran']}/4 partes. Agregados {int(adds.sum())}, retirados {int(removes.sum())}.\n\n"
    note += '| Semilla | Diferencia total | Splits ccajas | Probabilidades modificadas |\n|---|---:|---:|---:|\n'
    for pair, use in zip(paired, uses):
        note += f"| {pair['seed']} | {fmt(pair['delta_total'])} | {use['splits_ccajas']} | {use['probabilidades_cambian']} |\n"
    note += ('\nÚnico cambio: ccajas_depositos de mayo=NA. Abril idéntico y ccajas no es fuente histórica; cinco modelos273árboles reutilizados con hashes verificados. '
             'TabPFN202 guardado sin cambios, pesos50/50, corte estricto>2,75%, mismos clientes/labels/partes. '
             'Control$275.385.000 reproducido; matriz idéntica salvo la columna, ganancias verificadas por recarga y producto matricial. '
             'Cero fits/API/créditos/submits. Valores totales de mayo y escalado25% ilustrativo, no Public gain del Bot.\n\n')
    if delta <= 0 or mean_delta <= 0:
        note += 'Esta sensibilidad no aporta mejora consistente; no promover ni crear entrega. La regla de calidad conocida se conserva, pero el efecto de reentrenar abril+mayo corregidos queda sin medir.\n'
    else:
        note += 'Sensibilidad positiva en mayo; evidencia exploratoria. El efecto de reentrenar con mayo corregido y el rendimiento público siguen sin medir; no se ejecuta agosto automáticamente.\n'
    note += '\nMayo y semillas ya reutilizados; no test independiente. No se modifica el corte ni se corrigen mora/préstamos. Fuentes históricas y entrega43 preservadas.\n'
    (OUT / 'INFORME.md').write_text(note, encoding='utf-8')
    for path, h in plan['fuentes_sha256'].items():
        assert base.sha(base.ROOT / path) == h
    base.save(OUT / 'estado.json', dict(estado='completo_verificado_sensibilidad_local', delta_total=delta, final_agosto=False))
    configpath = base.TP / 'config_validacion_lightgbm.json'; config = read(configpath)
    config['sensibilidad_ccajas189_mayo'] = dict(estado=result['estado'], delta_total=delta, media_delta_listas_individuales=mean_delta,
        semillas_mejoran=result['semillas_mejoran'], nuevos_fits=0, api=False, creditos=0,
        informe=str((OUT / 'INFORME.md').relative_to(base.ROOT)), alcance=result['limitacion'])
    base.save(configpath, config)
    nextpath = base.TP / 'NEXT_STEPS_IDEAS.md'; oldtext = nextpath.read_text(encoding='utf-8-sig')
    nextpath.write_text('# Sensibilidad ccajas189 completada — 2026-10-10\n\n' + note.split('\n\n', 1)[1] + '\n---\n\n' + oldtext, encoding='utf-8')
    with (base.ROOT / 'BITACORA_DMEYF.md').open('a', encoding='utf-8') as f:
        f.write('\n' + note)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
