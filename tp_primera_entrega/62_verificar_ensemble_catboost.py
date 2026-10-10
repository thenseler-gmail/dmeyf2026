"""Verificacion desde datos originales de modelos y cinco adjuntos CatBoost."""
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['numero_de_cliente', 'foto_mes']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_sha(frame):
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()).hexdigest()


def main():
    out = Path(sys.argv[1]).resolve()
    m = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    sig = m['firma']
    assert m['train_final'] == sig['train'] == [202104, 202105]
    assert m['futuro'] == sig['futuro'] == 202108
    assert not m['enviado'] and not m['api'] and m['creditos'] == 0
    assert m['nuevos_fits_catboost'] == 5 and m['nuevos_fits_lightgbm'] == m['nuevos_fits_tabpfn'] == 0
    assert m['etiquetas_extraidas'] == [202104,202105] and not m['junio_validacion']
    assert not m['fit_eval_set'] and m['junio_julio_solo_historia']
    assert m['target_lightgbm'] == 'BAJA+1/BAJA+2'
    assert m['target_catboost'] == m['target_tabpfn'] == sig['target_catboost'] == 'BAJA+2'
    assert m['umbral'] == .025 and m['operador'] == '>'
    assert m['pesos'] == sig['weights'] == dict(lightgbm=.4,tabpfn=.4,catboost=.2)
    cols = sig['features']; seeds = sig['seeds']
    assert len(cols) == len(set(cols)) == 202
    assert seeds == [541440,408476,741961,248865,717444]
    assert sig['cat_features'] == ['Visa_status','Master_status','tcuentas']
    for name, digest in sig['codigo_sha256'].items():
        assert sha(Path(__file__).parent/name) == digest
    for name, digest in m['archivos_sha256'].items():
        assert sha(out/name) == digest
    source = ROOT/m['fuente_lightgbm_tabpfn']; local = ROOT/m['fuente_validacion']
    ref = json.loads((source/'manifest.json').read_text(encoding='utf-8-sig'))
    lm = json.loads((local/'manifest.json').read_text(encoding='utf-8-sig'))
    assert sha(local/'manifest.json') == sig['local_manifest_sha256']
    assert sha(local/'verificacion_independiente.json') == sig['local_verification_sha256']
    assert json.loads((local/'verificacion_independiente.json').read_text())['estado'] == 'verificado'
    assert sig['params'] == lm['firma']['params'] and cols == ref['firma']['features'] == lm['firma']['features']
    for name, digest in lm['archivos_sha256'].items():
        assert sha(local/name) == digest
    metrics = pd.read_csv(local/'comparacion_media5.csv').set_index('variante')
    a = metrics.loc['LightGBM_TabPFN_CatBoost_40_40_20']; b = metrics.loc['control_entrega8']
    assert a.ganancia == 261833000 and b.ganancia == 258368000
    assert a.ganancia > b.ganancia and a.semillas_mejoran == 5
    assert m['validacion_local']['candidato_25pct'] == a.ganancia/4
    assert m['validacion_local']['control_25pct'] == b.ganancia/4
    assert sha(source/'predicciones_agosto.csv') == sig['source_predictions_sha256'] == ref['predicciones_sha256']
    control = pd.read_csv(source/'predicciones_agosto.csv')
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw = con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) '
                      'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
                      'WHERE foto_mes IN (202104,202105,202108) ORDER BY foto_mes,numero_de_cliente').df()
        history = con.sql('SELECT '+','.join(KEYS+HISTORICAS+HISTORICAS_EXTRA)+
                          ' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any() and not history.duplicated(KEYS).any()
    hist = agregar_historicas_ampliadas(history)
    hc = [c for c in hist if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    assert len(hc) == 50
    raw = raw.merge(hist[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train = raw.loc[raw.foto_mes.isin([202104,202105])].reset_index(drop=True)
    future = raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train) == m['filas_train'] == 327052 and len(future) == m['filas_agosto'] == 164647
    assert future.clase_ternaria.isna().all()
    target = train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(target.tobytes()).hexdigest() == sig['target_train_sha256'] == ref['firma']['target_tabpfn_sha256']
    xt = preparar(train,cols)[0]; xp = preparar(future,cols)[0]
    for frame, name in [(xt,'matriz_train'),(xp,'matriz_agosto')]:
        assert hashlib.sha256(frame.to_numpy(dtype=np.float32).tobytes()).hexdigest() == sig[name+'_float32_sha256'] == ref['firma'][name+'_sha256']
        for c in sig['cat_features']:
            frame[c] = frame[c].astype('string').fillna('__MISSING__').astype(str)
        assert frame_sha(frame) == sig[name+'_catboost_sha256']
    p = pd.read_csv(out/'predicciones_agosto.csv')
    pd.testing.assert_frame_equal(p[KEYS],future[KEYS])
    pd.testing.assert_frame_equal(p[KEYS],control[KEYS])
    assert not p.numero_de_cliente.duplicated().any()
    np.testing.assert_allclose(p.p_tabpfn,control.p_tabpfn,rtol=0,atol=1e-15)
    numeric_xp = preparar(future,cols)[0]
    pool = Pool(xp,cat_features=sig['cat_features'])
    assert len(m['archivos']) == len(m['modelos_sha256']) == 5
    assert {f.name for f in (out/'modelos_catboost').glob('*.cbm')} == {f'seed{s}.cbm' for s in seeds}
    assert {str(f.relative_to(out)) for f in (out/'adjuntos_semillas').glob('*.csv')} == {a['archivo'] for a in m['archivos']}
    changes = pd.read_csv(out/'cambios_contactos_agosto.csv').set_index('seed')
    for seed in seeds:
        lp = source/'modelos'/f'seed{seed}.txt'
        assert sha(lp) == sig['source_models_sha256'][lp.name] == ref['modelos_sha256'][lp.name]
        lb = lgb.Booster(model_file=str(lp))
        assert lb.feature_name() == cols and lb.num_trees() == 273
        np.testing.assert_allclose(lb.predict(numeric_xp,validate_features=True),p[f'p_lgb_seed{seed}'],rtol=0,atol=1e-15)
        np.testing.assert_allclose(control[f'p_seed{seed}'],p[f'p_lgb_seed{seed}'],rtol=0,atol=1e-15)
        cp = out/'modelos_catboost'/f'seed{seed}.cbm'
        assert sha(cp) == m['modelos_sha256'][cp.name]
        model = CatBoostClassifier(); model.load_model(str(cp))
        assert model.tree_count_ == 800 and model.feature_names_ == cols and model.classes_.tolist() == [0,1]
        assert set(model.get_cat_feature_indices()) == {cols.index(c) for c in sig['cat_features']}
        params = model.get_all_params()
        assert params['random_seed'] == seed
        for key in ['iterations','learning_rate','depth','l2_leaf_reg','loss_function','boosting_type',
                    'bootstrap_type','subsample','rsm','random_strength','border_count','nan_mode','task_type']:
            if isinstance(sig['params'][key],float):
                np.testing.assert_allclose(params[key],sig['params'][key],rtol=0,atol=1e-7)
            else:
                assert params[key] == sig['params'][key]
        np.testing.assert_allclose(model.predict_proba(pool)[:,1],p[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        score = .4*p[f'p_lgb_seed{seed}']+.4*p.p_tabpfn+.2*p[f'p_cat_seed{seed}']
        np.testing.assert_allclose(score,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        chosen = p.loc[score>.025,KEYS].copy(); chosen['score'] = score[score>.025]
        chosen = chosen.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        expected = ''.join(f'{int(i)}\n' for i in chosen.numero_de_cliente).encode('ascii')
        entry = next(f for f in m['archivos'] if f['seed'] == seed)
        path = out/entry['archivo']
        assert path.name == f"{m['submit']}_seed{seed}.csv"
        # write_text utiliza CRLF en Windows; ambos finales de linea son validos.
        assert path.read_bytes() in (expected,expected.replace(b'\n',b'\r\n'))
        assert sha(path) == entry['sha256']
        assert entry['contactos'] == len(chosen) == chosen.numero_de_cliente.nunique()
        old = (control[f'p_seed{seed}']+control.p_tabpfn)/2>.025; new = score>.025
        row = changes.loc[seed]
        assert row.contactos_entrega8 == old.sum() and row.contactos_nuevos == new.sum()
        assert row.agregados == (new&~old).sum() and row.retirados == (old&~new).sum()
    values = p.drop(columns=KEYS).to_numpy()
    assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    assert (out/'MENSAJE_SEMILLAS.txt').read_text().strip() == 'submit '+m['submit']
    verification = dict(estado='verificado',modelos_catboost_reproducidos=5,modelos_lightgbm_reproducidos=5,
                        adjuntos_verificados=5,filas_agosto=164647,matrices_y_target_verificados=True,
                        corte_estricto=.025,mezcla=[.4,.4,.2],control_local_superado=True,
                        entrenamiento=[202104,202105],etiquetas_agosto=False,api=False,creditos=0,enviado=False,
                        codigo_verificador_sha256=sha(Path(__file__)))
    (out/'verificacion_independiente.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    m['estado'] = 'completo_verificado_preparado_pendiente'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(verification,indent=2),flush=True)


if __name__ == '__main__':
    main()
