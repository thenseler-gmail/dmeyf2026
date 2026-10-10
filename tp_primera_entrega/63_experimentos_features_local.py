"""Cuatro cambios aislados en LightGBM; abril->mayo, TabPFN guardado, sin Bot."""
import argparse
import hashlib
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
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT/'tp_primera_entrega/salidas'
SOURCE = SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
KEYS = ['numero_de_cliente','foto_mes']
RANK_SOURCES = ['mpayroll','mcuentas_saldo','mrentabilidad']
VARIANTS = ['sin_prestamos','rangos_mensuales','historia_1_mes','historia_1_mes_sin_relativos']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def matrix_sha(frame):
    return hashlib.sha256(frame.to_numpy(dtype=np.float32).tobytes()).hexdigest()


def matrices(x):
    """Cambios congelados antes de ver la ganancia, cada uno desde 202."""
    drop_long = ['historial_meses_previos_3']+[prefix+c for c in HISTORICAS for prefix in
                 ['media_previa_3_','delta_media_previa_3_','observaciones_previas_3_']]
    drop_relative = ['variacion_relativa_1_'+c for c in HISTORICAS+HISTORICAS_EXTRA]
    ranked = x.copy()
    for c in RANK_SOURCES:
        # Se llama con un mes completo; sin etiquetas, sin sustituir faltantes.
        ranked['rango_mensual_'+c] = x[c].rank(method='average',pct=True,na_option='keep')
    result = dict(sin_prestamos=x.drop(columns=['cprestamos_personales','mprestamos_personales']),
                  rangos_mensuales=ranked,historia_1_mes=x.drop(columns=drop_long),
                  historia_1_mes_sin_relativos=x.drop(columns=drop_long+drop_relative))
    assert [len(result[v].columns) for v in VARIANTS] == [200,205,189,177]
    return result


def cargar():
    ref = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8-sig'))
    assert ref['validacion_train'] == [202104] and ref['validacion_eval'] == 202105
    assert ref['elegido']['target'] == 'bajas' and ref['elegido']['num_boost_round'] == 273
    assert ref['peso_tabpfn'] == .5 and ref['umbral'] == .025 and ref['operador'] == '>'
    cols = ref['features_lightgbm']; seeds = ref['semillas']
    assert len(cols) == 202 and seeds == [541440,408476,741961,248865,717444]
    for f in ['features.py','baseline.py']:
        assert sha(Path(__file__).parent/f) == ref['codigo_sha256'][f]
    assert sha(SOURCE/'predicciones_mayo.csv') == ref['hashes_resultados']['predicciones_mayo.csv']
    control = pd.read_csv(SOURCE/'predicciones_mayo.csv')
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw = con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) '
                      'THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos '
                      'WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    assert not raw.duplicated(KEYS).any()
    hist = agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc = [c for c in hist if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    assert len(hc) == 50
    raw = raw.merge(hist[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train = raw.loc[raw.foto_mes.eq(202104)].reset_index(drop=True)
    valid = raw.loc[raw.foto_mes.eq(202105)].reset_index(drop=True)
    assert len(train) == 163284 and len(valid) == 163768
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],control[KEYS+['clase_ternaria']])
    xt = preparar(train,cols)[0]; xv = preparar(valid,cols)[0]
    for seed in seeds:
        model = lgb.Booster(model_file=str(SOURCE/'modelos_validacion'/f'seed{seed}.txt'))
        assert model.feature_name() == cols and model.num_trees() == 273
        np.testing.assert_allclose(model.predict(xv,validate_features=True),control[f'p_seed{seed}'],rtol=0,atol=1e-15)
    return ref,seeds,train,valid,xt,xv,control


def metric(y,score):
    selected = np.asarray(score)>.025
    n = int(selected.sum()); tp = int((selected&y).sum())
    g = int(np.where(y,1072500,-27500)[selected].sum())
    assert g == tp*1100000-n*27500
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reanudar',type=Path)
    args = ap.parse_args()
    ref,seeds,train,valid,xt,xv,control = cargar()
    tx = matrices(xt); vx = matrices(xv)
    yt = train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    yv = valid.clase_ternaria.eq('BAJA+2').to_numpy()
    # Mismas partes por cliente del piloto CatBoost, sin seleccion por parte.
    permutation = np.random.default_rng(214363).permutation(len(valid))
    parts = np.empty(len(valid),dtype=int); parts[permutation] = np.arange(len(valid))%4
    signature = dict(params=ref['elegido']['params'],rounds=273,seeds=seeds,target_train='BAJA+1/BAJA+2',
        base_features=list(xt),variants={v:dict(features=list(tx[v]),train_sha256=matrix_sha(tx[v]),
                                              mayo_sha256=matrix_sha(vx[v])) for v in VARIANTS},
        base_train_sha256=matrix_sha(xt),base_mayo_sha256=matrix_sha(xv),
        target_train_sha256=hashlib.sha256(yt.tobytes()).hexdigest(),
        target_eval_sha256=hashlib.sha256(yv.tobytes()).hexdigest(),
        source_predictions_sha256=sha(SOURCE/'predicciones_mayo.csv'),
        source_models_sha256={f'seed{s}.txt':sha(SOURCE/'modelos_validacion'/f'seed{s}.txt') for s in seeds},
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['63_experimentos_features_local.py','features.py','baseline.py']},
        rank_rule=dict(method='average',pct=True,na_option='keep',zeros='validos',negatives='validos',
                       population='mes completo no nulo; train y validacion por separado, sin etiquetas'),
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','pandas','numpy','duckdb']})
    if args.reanudar:
        out = args.reanudar.resolve(); m = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        assert m['firma'] == signature
    else:
        out = SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('features_local_%Y%m%d_%H%M%S')
        out.mkdir()
        m = dict(estado='entrenando',firma=signature,train=[202104],evaluacion=202105,aux_historia=[202103],
                 fuente_control=str(SOURCE.relative_to(ROOT)),filas_train=len(train),filas_mayo=len(valid),
                 umbral=.025,operador='>',peso_tabpfn=.5,target_tabpfn='BAJA+2',
                 api=False,creditos=0,submits=0,junio_leido=False,agosto_leido=False,fit_eval_set=False,
                 nuevos_fits_lightgbm=20,variantes_completadas=[],
                 criterio='Cambios aislados contra configuracion8; media ganancias5listas. Sin tuning, cambio de target, pesos o corte.',
                 limitaciones='Mayo y semillas reutilizados; no test independiente ni garantia publica. '
                             'Rangos usan contexto de poblacion mensual sin etiquetas. El muestreo de columnas cambia al cambiar features; '
                             'ablacion no demuestra causa ni drift. Partes mayo no son meses independientes. '
                             'Sin entrenamiento final/API/entrega nueva al Bot durante ensayo.')
    save(out/'manifest.json',m)
    print('Salida:',out,flush=True)
    cp = valid[KEYS+['clase_ternaria']].copy(); cp['parte_cliente'] = parts; cp['p_tabpfn'] = control.p_tabpfn
    for s in seeds: cp[f'p_seed{s}'] = control[f'p_seed{s}']
    cp.to_csv(out/'control_mayo.csv',index=False)
    for v in VARIANTS:
        vd = out/v; vd.mkdir(exist_ok=True)
        pred = cp[KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy()
        for seed in seeds:
            path = vd/f'seed{seed}.txt'; start = time.perf_counter()
            if path.exists():
                model = lgb.Booster(model_file=str(path))
            else:
                print('Entrenando',v,'semilla',seed,flush=True)
                model = lgb.train(dict(signature['params'],seed=seed),lgb.Dataset(tx[v],label=yt),num_boost_round=273)
                model.save_model(str(path))
            assert model.feature_name() == list(tx[v]) and model.num_trees() == 273
            pred[f'p_seed{seed}'] = model.predict(vx[v],validate_features=True)
            reloaded = lgb.Booster(model_file=str(path))
            np.testing.assert_allclose(reloaded.predict(vx[v],validate_features=True),pred[f'p_seed{seed}'],rtol=0,atol=0)
            pred.to_csv(vd/'predicciones_mayo.csv',index=False)
            m.setdefault('tiempos',[]).append(dict(variante=v,seed=seed,segundos=time.perf_counter()-start))
            save(out/'manifest.json',m)
            print(v,seed,'completo',flush=True)
        m['variantes_completadas'] = VARIANTS[:VARIANTS.index(v)+1]
        save(out/'manifest.json',m)
    rows=[]; partrows=[]; changes=[]; meanrows=[]
    sources = dict(control_entrega8=cp,**{v:pd.read_csv(out/v/'predicciones_mayo.csv') for v in VARIANTS})
    for v,p in sources.items():
        for seed in seeds:
            score = (p[f'p_seed{seed}']+p.p_tabpfn)/2
            base = (cp[f'p_seed{seed}']+cp.p_tabpfn)/2>.025
            sel = score>.025; add=sel&~base; remove=base&~sel
            rows.append(dict(variante=v,seed=seed,features=202 if v=='control_entrega8' else len(tx[v].columns),**metric(yv,score)))
            for k in range(4):
                mask = parts==k
                partrows.append(dict(variante=v,seed=seed,parte=k,**metric(yv[mask],score[mask])))
            changes.append(dict(variante=v,seed=seed,agregados=int(add.sum()),retirados=int(remove.sum()),
                agregados_baja2=int((add&yv).sum()),retirados_baja2=int((remove&yv).sum()),
                agregados_fp=int((add&~yv).sum()),retirados_fp=int((remove&~yv).sum())))
        meanrows.append(dict(variante=v,**metric(yv,(p[[f'p_seed{s}' for s in seeds]].mean(axis=1)+p.p_tabpfn)/2)))
    individual = pd.DataFrame(rows); individual.to_csv(out/'resultados_semillas.csv',index=False)
    pd.DataFrame(partrows).to_csv(out/'resultados_partes_mayo.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    pd.DataFrame(meanrows).to_csv(out/'lista_promedio5.csv',index=False)
    ordered = ['control_entrega8']+VARIANTS
    summary = individual.groupby('variante')[['features','contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean().loc[ordered]
    assert summary.loc['control_entrega8','ganancia'] == 258368000
    pivot = individual.pivot(index='seed',columns='variante',values='ganancia')
    summary['delta_total'] = summary.ganancia-258368000
    summary['delta_25pct'] = summary.delta_total/4
    summary['delta_pct'] = summary.delta_total/258368000*100
    summary['semillas_mejoran'] = [int((pivot[v]>pivot.control_entrega8).sum()) for v in ordered]
    pr = pd.DataFrame(partrows).groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['partes_mejoran'] = [int((pr[v]>pr.control_entrega8).sum()) for v in ordered]
    summary.to_csv(out/'comparacion_media5.csv')
    models = {str(p.relative_to(out)):sha(p) for v in VARIANTS for p in (out/v).glob('seed*.txt')}
    csvs = {str(p.relative_to(out)):sha(p) for p in out.rglob('*.csv')}
    m.update(estado='completo_pendiente_verificacion',resultados=summary.reset_index().to_dict('records'),
             modelos_sha256=models,archivos_sha256=csvs,
             superan_control_local=[v for v in VARIANTS if summary.loc[v,'delta_total']>0])
    save(out/'manifest.json',m)
    print('COMPLETO; pendiente verificacion independiente:',out,flush=True)
    print(summary.to_string(),flush=True)


if __name__ == '__main__':
    main()
