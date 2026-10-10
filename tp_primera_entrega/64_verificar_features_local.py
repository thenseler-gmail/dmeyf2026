"""Reproduce modelos y pagos; verifica rangos con frecuencias, sin pandas.rank."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['numero_de_cliente','foto_mes']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank_frequencies(x):
    counts = x.dropna().value_counts(sort=False).sort_index()
    if len(counts)==0:
        return pd.Series(np.nan,index=x.index)
    # Rango medio de cada grupo: previos + (cantidad+1)/2.
    mapping = (counts.cumsum()-counts+(counts+1)/2)/counts.sum()
    return x.map(mapping)


def main():
    out = Path(sys.argv[1]).resolve()
    m = json.loads((out/'manifest.json').read_text(encoding='utf-8')); sig=m['firma']
    assert m['train']==[202104] and m['evaluacion']==202105 and m['aux_historia']==[202103]
    assert m['umbral']==.025 and m['operador']=='>' and m['peso_tabpfn']==.5
    assert not m['fit_eval_set'] and not m['api'] and m['creditos']==m['submits']==0
    assert not m['junio_leido'] and not m['agosto_leido'] and m['nuevos_fits_lightgbm']==20
    for f,h in sig['codigo_sha256'].items():
        assert sha(Path(__file__).parent/f)==h
    for f,h in m['archivos_sha256'].items():
        assert sha(out/f)==h
    module = importlib.import_module('63_experimentos_features_local')
    ref,seeds,train,valid,xt,xv,control = module.cargar()
    assert sig['params']==ref['elegido']['params'] and sig['rounds']==273 and sig['seeds']==seeds
    assert sig['target_train']=='BAJA+1/BAJA+2' and sig['base_features']==list(xt)
    yt = train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    y = valid.clase_ternaria.eq('BAJA+2').to_numpy()
    assert hashlib.sha256(yt.tobytes()).hexdigest()==sig['target_train_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==sig['target_eval_sha256']
    assert module.matrix_sha(xt)==sig['base_train_sha256'] and module.matrix_sha(xv)==sig['base_mayo_sha256']
    assert sha(module.SOURCE/'predicciones_mayo.csv')==sig['source_predictions_sha256']
    for seed in seeds:
        assert sha(module.SOURCE/'modelos_validacion'/f'seed{seed}.txt')==sig['source_models_sha256'][f'seed{seed}.txt']
    np.testing.assert_allclose(rank_frequencies(pd.Series([np.nan,0.,0.,-1.,2.])),
                               [np.nan,.625,.625,.25,1.],rtol=0,atol=0,equal_nan=True)
    assert rank_frequencies(pd.Series([np.nan,np.nan])).isna().all()
    def independent_variants(x):
        long=[c for c in x if c=='historial_meses_previos_3' or c.startswith(
            ('media_previa_3_','delta_media_previa_3_','observaciones_previas_3_'))]
        relative=[c for c in x if c.startswith('variacion_relativa_1_')]
        assert len(long)==13 and len(relative)==12
        ranked=x.copy()
        for c in ['mpayroll','mcuentas_saldo','mrentabilidad']:
            ranked['rango_mensual_'+c]=rank_frequencies(x[c])
        return dict(sin_prestamos=x.drop(columns=['cprestamos_personales','mprestamos_personales']),
                    rangos_mensuales=ranked,historia_1_mes=x.drop(columns=long),
                    historia_1_mes_sin_relativos=x.drop(columns=long+relative))
    tx=independent_variants(xt); vx=independent_variants(xv)
    for v in module.VARIANTS:
        pd.testing.assert_frame_equal(tx[v],module.matrices(xt)[v])
        pd.testing.assert_frame_equal(vx[v],module.matrices(xv)[v])
        assert list(tx[v])==sig['variants'][v]['features']
        assert module.matrix_sha(tx[v])==sig['variants'][v]['train_sha256']
        assert module.matrix_sha(vx[v])==sig['variants'][v]['mayo_sha256']
    cp=pd.read_csv(out/'control_mayo.csv')
    pd.testing.assert_frame_equal(cp[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    perm=np.random.default_rng(214363).permutation(len(valid)); parts=np.empty(len(valid),dtype=int)
    parts[perm]=np.arange(len(valid))%4
    np.testing.assert_array_equal(cp.parte_cliente,parts)
    catlocal=ROOT/'tp_primera_entrega/salidas/catboost_local_20261006_004259/predicciones_mayo.csv'
    catparts=pd.read_csv(catlocal,usecols=KEYS+['parte_cliente'])
    pd.testing.assert_frame_equal(cp[KEYS+['parte_cliente']],catparts)
    np.testing.assert_allclose(cp.p_tabpfn,control.p_tabpfn,rtol=0,atol=1e-15)
    for seed in seeds:
        np.testing.assert_allclose(cp[f'p_seed{seed}'],control[f'p_seed{seed}'],rtol=0,atol=1e-15)
    predictions={'control_entrega8':cp}
    assert len(m['modelos_sha256'])==20
    for v in module.VARIANTS:
        p=pd.read_csv(out/v/'predicciones_mayo.csv');predictions[v]=p
        pd.testing.assert_frame_equal(p[KEYS+['clase_ternaria','parte_cliente']],cp[KEYS+['clase_ternaria','parte_cliente']])
        np.testing.assert_allclose(p.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
        for seed in seeds:
            mp=out/v/f'seed{seed}.txt';assert sha(mp)==m['modelos_sha256'][str(mp.relative_to(out))]
            model=lgb.Booster(model_file=str(mp))
            assert model.num_trees()==273 and model.feature_name()==list(vx[v])
            assert int(model.params['seed'])==seed and model.params['objective']=='binary'
            for k in ['num_leaves','max_bin','bagging_freq','min_data_in_leaf']:
                assert int(model.params[k])==sig['params'][k]
            for k in ['learning_rate','feature_fraction','bagging_fraction']:
                # Parametros del TXT se serializan con seis cifras significativas.
                assert float(model.params[k]) == float(format(sig['params'][k],'.6g'))
            np.testing.assert_allclose(model.predict(vx[v],validate_features=True),p[f'p_seed{seed}'],rtol=0,atol=1e-15)
        values=p[['p_tabpfn']+[f'p_seed{s}' for s in seeds]].to_numpy()
        assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    def selection(v,seed,mean=False):
        p=predictions[v]
        lgbp=p[[f'p_seed{s}' for s in seeds]].mean(axis=1) if mean else p[f'p_seed{seed}']
        return ((lgbp+p.p_tabpfn)/2>.025).to_numpy()
    payment=np.where(y,1072500,-27500)
    rows=pd.read_csv(out/'resultados_semillas.csv');assert len(rows)==25
    for r in rows.itertuples():
        sel=selection(r.variante,r.seed)
        assert payment[sel].sum()==r.ganancia and r.ganancia_25pct==r.ganancia/4
        assert sel.sum()==r.contactos and (sel&y).sum()==r.tp and (sel&~y).sum()==r.fp and (~sel&y).sum()==r.fn
    partrows=pd.read_csv(out/'resultados_partes_mayo.csv');assert len(partrows)==100
    for r in partrows.itertuples():
        sel=selection(r.variante,r.seed)&(parts==r.parte)
        assert payment[sel].sum()==r.ganancia and r.ganancia_25pct==r.ganancia/4
        assert sel.sum()==r.contactos and (sel&y).sum()==r.tp and (sel&~y).sum()==r.fp
    changes=pd.read_csv(out/'cambios_contactos.csv');assert len(changes)==25
    for r in changes.itertuples():
        base=selection('control_entrega8',r.seed);sel=selection(r.variante,r.seed)
        add=sel&~base;remove=base&~sel
        assert add.sum()==r.agregados and remove.sum()==r.retirados
        assert (add&y).sum()==r.agregados_baja2 and (remove&y).sum()==r.retirados_baja2
        assert (add&~y).sum()==r.agregados_fp and (remove&~y).sum()==r.retirados_fp
        assert payment[sel].sum()-payment[base].sum()==(r.agregados_baja2-r.retirados_baja2)*1100000-(r.agregados-r.retirados)*27500
    avg=pd.read_csv(out/'lista_promedio5.csv');assert len(avg)==5
    for r in avg.itertuples():
        assert payment[selection(r.variante,seeds[0],True)].sum()==r.ganancia
    means=rows.groupby('variante')[['features','contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean()
    summary=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
    np.testing.assert_allclose(means.loc[summary.index],summary[means.columns],rtol=0,atol=1e-8)
    assert summary.loc['control_entrega8','ganancia']==258368000
    pivot=rows.pivot(index='seed',columns='variante',values='ganancia')
    groups=partrows.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    for v,r in summary.iterrows():
        assert r.delta_total==r.ganancia-258368000 and r.delta_25pct==r.delta_total/4
        assert r.semillas_mejoran==(pivot[v]>pivot.control_entrega8).sum()
        assert r.partes_mejoran==(groups[v]>groups.control_entrega8).sum()
    verification=dict(estado='verificado',modelos_nuevos_reproducidos=20,modelos_control_reproducidos=5,
        matrices_y_targets_verificados=True,rangos_por_frecuencias_verificados=True,ganancias_individuales=25,
        resultados_partes=100,cambios_contactos=25,listas_promedio5=5,api=False,creditos=0,submits=0,
        junio=False,agosto=False,codigo_verificador_sha256=sha(Path(__file__)))
    (out/'verificacion_independiente.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    m['estado']='completo_verificado'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(verification,indent=2),flush=True)


if __name__=='__main__':
    main()
