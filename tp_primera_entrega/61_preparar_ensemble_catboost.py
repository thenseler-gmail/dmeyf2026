"""Entrega de cinco mezclas LGB/TabPFN/CatBoost 40/40/20, abril+mayo->agosto.

CatBoost conserva la configuracion validada localmente. Reutiliza entrega8.
No llama APIs, no envia al Bot, no usa etiquetas junio/julio/agosto.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT / 'tp_primera_entrega/salidas'
SOURCE = SAL / '01_entregas_bot/8_EnsembleAbrilMayo5_20261005_220000'
LOCAL = SAL / 'catboost_local_20261006_004259'
KEYS = ['numero_de_cliente', 'foto_mes']
WEIGHTS = dict(lightgbm=.4, tabpfn=.4, catboost=.2)
module = importlib.import_module('59_experimento_catboost_local')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def hash_frame(frame):
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()).hexdigest()


def cargar():
    ref = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8-sig'))
    local = json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8-sig'))
    assert json.loads((LOCAL/'verificacion_independiente.json').read_text())['estado'] == 'verificado'
    assert ref['train_final'] == [202104, 202105] and ref['futuro'] == 202108
    cols = ref['firma']['features']; seeds = ref['firma']['semillas']
    assert cols == local['firma']['features'] and len(cols) == 202
    assert seeds == local['firma']['seeds'] == [541440, 408476, 741961, 248865, 717444]
    assert module.PARAMS == local['firma']['params'] and module.CAT_COLS == local['firma']['cat_features']
    for f in ['features.py', 'baseline.py']:
        assert sha(Path(__file__).parent/f) == ref['firma']['codigo'][f] == local['firma']['codigo_sha256'][f]
    assert sha(Path(__file__).parent/'59_experimento_catboost_local.py') == local['firma']['codigo_sha256']['59_experimento_catboost_local.py']
    for name, value in local['archivos_sha256'].items():
        assert sha(LOCAL/name) == value
    metrics = pd.read_csv(LOCAL/'comparacion_media5.csv').set_index('variante')
    result = metrics.loc['LightGBM_TabPFN_CatBoost_40_40_20']
    assert result.ganancia == 261833000 and result.delta_total == 3465000 and result.semillas_mejoran == 5
    assert sha(SOURCE/'predicciones_agosto.csv') == ref['predicciones_sha256']
    pred = pd.read_csv(SOURCE/'predicciones_agosto.csv')
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        # Solo etiquetas abril/mayo. La otra lectura es historia de features.
        raw = con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) '
                      'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
                      'WHERE foto_mes IN (202104,202105,202108) ORDER BY foto_mes,numero_de_cliente').df()
        hist_raw = con.sql('SELECT '+','.join(KEYS+HISTORICAS+HISTORICAS_EXTRA)+
                           ' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 '
                           'ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any() and not hist_raw.duplicated(KEYS).any()
    hist = agregar_historicas_ampliadas(hist_raw)
    hc = [c for c in hist if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    assert len(hc) == 50
    raw = raw.merge(hist[KEYS+hc], on=KEYS, validate='one_to_one', sort=False)
    train = raw.loc[raw.foto_mes.isin([202104,202105])].reset_index(drop=True)
    august = raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train) == 327052 and len(august) == 164647
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all() and august.clase_ternaria.isna().all()
    pd.testing.assert_frame_equal(pred[KEYS], august[KEYS])
    assert not pred.numero_de_cliente.duplicated().any()
    xt = preparar(train, cols)[0]; xp = preparar(august, cols)[0]
    for frame, name in [(xt,'matriz_train_sha256'), (xp,'matriz_agosto_sha256')]:
        assert hashlib.sha256(frame.to_numpy(dtype=np.float32).tobytes()).hexdigest() == ref['firma'][name]
    y = train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(y.tobytes()).hexdigest() == ref['firma']['target_tabpfn_sha256']
    # Reproducir LightGBM final y comprobar exactamente la fuente TabPFN.
    for seed in seeds:
        path = SOURCE/'modelos'/f'seed{seed}.txt'
        assert sha(path) == ref['modelos_sha256'][path.name]
        model = lgb.Booster(model_file=str(path))
        assert model.feature_name() == cols and model.num_trees() == 273
        np.testing.assert_allclose(model.predict(xp, validate_features=True), pred[f'p_seed{seed}'], rtol=0, atol=1e-15)
    assert np.isfinite(pred.p_tabpfn).all() and pred.p_tabpfn.between(0,1).all()
    return ref, local, cols, seeds, module.categorizar(xt), module.categorizar(xp), y, august[KEYS], pred


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reanudar', type=Path)
    args = ap.parse_args()
    ref, local, cols, seeds, xt, xp, y, keys, source = cargar()
    signature = dict(params=module.PARAMS, cat_features=module.CAT_COLS, features=cols, seeds=seeds,
                     weights=WEIGHTS, train=[202104,202105], futuro=202108, target_catboost='BAJA+2',
                     source_predictions_sha256=sha(SOURCE/'predicciones_agosto.csv'),
                     local_manifest_sha256=sha(LOCAL/'manifest.json'),
                     local_verification_sha256=sha(LOCAL/'verificacion_independiente.json'),
                     source_models_sha256=ref['modelos_sha256'],
                     matriz_train_catboost_sha256=hash_frame(xt), matriz_agosto_catboost_sha256=hash_frame(xp),
                     matriz_train_float32_sha256=ref['firma']['matriz_train_sha256'],
                     matriz_agosto_float32_sha256=ref['firma']['matriz_agosto_sha256'],
                     target_train_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
                     codigo_sha256={f:sha(Path(__file__).parent/f) for f in
                                    ['61_preparar_ensemble_catboost.py','59_experimento_catboost_local.py','features.py','baseline.py']},
                     versiones={p:importlib.metadata.version(p) for p in ['catboost','lightgbm','pandas','numpy','duckdb']})
    if args.reanudar:
        out = args.reanudar.resolve(); m = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        assert m['firma'] == signature and not m['enviado']
    else:
        base = SAL/'01_entregas_bot'
        numbers = [int(p.name.split('_')[0]) for p in base.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit()]
        number = max(numbers)+1
        name = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleCatBoost5_%Y%m%d_%H%M%S')
        out = base/f'{number}_{name}'; out.mkdir()
        m = dict(estado='entrenando_catboost_final', entrega=number, submit=name+'_semillas',
                 enviado=False, firma=signature, train_final=[202104,202105], futuro=202108,
                 filas_train=len(xt), filas_agosto=len(xp), umbral=.025, operador='>', pesos=WEIGHTS,
                 target_lightgbm='BAJA+1/BAJA+2', target_tabpfn='BAJA+2', target_catboost='BAJA+2',
                 fuente_lightgbm_tabpfn=str(SOURCE.relative_to(ROOT)), fuente_validacion=str(LOCAL.relative_to(ROOT)),
                 creditos=0, api=False, nuevos_fits_catboost=5, nuevos_fits_lightgbm=0, nuevos_fits_tabpfn=0,
                 fit_eval_set=False, etiquetas_extraidas=[202104,202105], junio_validacion=False,
                 junio_julio_solo_historia=True, modelos_completados=[],
                 validacion_local=dict(control_total=258368000, control_25pct=64592000,
                    candidato_total=261833000, candidato_25pct=65458250, delta_total=3465000,
                    delta_25pct=866250, semillas_mejoran=5),
                 limitaciones='Mayo y semillas reutilizados; validacion retrospectiva, no test independiente ni garantia agosto. '
                             'Pesos/configuracion congelados del piloto CatBoost. Score mezcla distintos targets, no P(BAJA+2) calibrada. '
                             'No Optuna, features nuevas, ajuste de corte, ni seleccion por etiquetas junio/agosto.')
    save(out/'manifest.json', m)
    md = out/'modelos_catboost'; md.mkdir(exist_ok=True)
    pred = keys.copy(); pred['p_tabpfn'] = source.p_tabpfn
    for seed in seeds: pred[f'p_lgb_seed{seed}'] = source[f'p_seed{seed}']
    tp = Pool(xt, label=y, cat_features=module.CAT_COLS)
    vp = Pool(xp, cat_features=module.CAT_COLS)
    print('Salida:', out, flush=True)
    for seed in seeds:
        path = md/f'seed{seed}.cbm'; start = time.perf_counter()
        if path.exists():
            model = CatBoostClassifier(); model.load_model(str(path))
        else:
            print('Entrenando CatBoost final semilla', seed, flush=True)
            model = CatBoostClassifier(**module.PARAMS, random_seed=seed)
            model.fit(tp, verbose=100)
            model.save_model(str(path))
        assert model.feature_names_ == cols and model.tree_count_ == 800 and model.classes_.tolist() == [0,1]
        assert model.get_all_params()['random_seed'] == seed
        p = model.predict_proba(vp)[:,1]
        reloaded = CatBoostClassifier(); reloaded.load_model(str(path))
        np.testing.assert_allclose(reloaded.predict_proba(vp)[:,1], p, rtol=0, atol=0)
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        pred[f'p_cat_seed{seed}'] = p
        pred[f'score_seed{seed}'] = .4*pred[f'p_lgb_seed{seed}']+.4*pred.p_tabpfn+.2*p
        pred.to_csv(out/'predicciones_agosto.csv', index=False)
        m['modelos_completados'] = [int(c.removeprefix('p_cat_seed')) for c in pred if c.startswith('p_cat_seed')]
        m.setdefault('tiempos',[]).append(dict(seed=seed, segundos=time.perf_counter()-start))
        save(out/'manifest.json', m)
        print('Semilla',seed,'completa',flush=True)
    adj = out/'adjuntos_semillas'; adj.mkdir(exist_ok=True)
    assert not list(adj.glob('*.csv'))
    files = []; changes = []
    for seed in seeds:
        score = pred[f'score_seed{seed}']; sel = score>.025
        selected = pred.loc[sel,KEYS].copy(); selected['score'] = score[sel]
        selected = selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path = adj/f"{m['submit']}_seed{seed}.csv"
        path.write_text(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente), encoding='ascii')
        assert len(selected) == selected.numero_de_cliente.nunique()
        files.append(dict(seed=seed, archivo=str(path.relative_to(out)), contactos=len(selected), sha256=sha(path)))
        base = (pred[f'p_lgb_seed{seed}']+pred.p_tabpfn)/2>.025
        changes.append(dict(seed=seed, contactos_entrega8=int(base.sum()), contactos_nuevos=int(sel.sum()),
                            agregados=int((sel&~base).sum()), retirados=int((base&~sel).sum())))
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    (out/'MENSAJE_SEMILLAS.txt').write_text('submit '+m['submit']+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO, PENDIENTE ENVIO MANUAL POR TOMAS.\n'
                                    'Una corrida con los cinco CSV de adjuntos_semillas.\n'
                                    'Resultado agosto desconocido; no se envio al Bot.\n',encoding='utf-8')
    m.update(estado='preparado_pendiente_verificacion', archivos=files,
             modelos_sha256={p.name:sha(p) for p in md.glob('*.cbm')},
             archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    save(out/'manifest.json',m)
    print('Cinco CSV preparados; falta verificacion independiente.',flush=True)
    print('Comando: submit '+m['submit'],flush=True)


if __name__ == '__main__':
    main()
