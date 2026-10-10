"""Reproduce cinco CatBoost desde raw y reconstruye ganancias de tres pruebas."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier,Pool

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo_verificado' and m['train']==[202104] and m['evaluacion']==202105
    assert not m['api'] and m['creditos']==m['submits']==0 and not m['junio_leido'] and not m['agosto_leido']
    assert not m['fit_eval_set'] and m['umbral']==.025 and m['operador']=='>'
    for f,h in m['firma']['codigo_sha256'].items():assert sha(Path(__file__).parent/f)==h
    for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
    module=importlib.import_module('59_experimento_catboost_local')
    src,cols,seeds,train,valid,xt,xv,control=module.cargar()
    assert m['firma']['features']==cols and m['firma']['seeds']==seeds
    assert sha(src/'predicciones_mayo.csv')==m['firma']['source_sha256']
    cx=module.categorizar(xv);ct=module.categorizar(xt)
    assert hashlib.sha256(pd.util.hash_pandas_object(cx,index=False).to_numpy().tobytes()).hexdigest()==m['firma']['matriz_mayo_sha256']
    assert hashlib.sha256(pd.util.hash_pandas_object(ct,index=False).to_numpy().tobytes()).hexdigest()==m['firma']['matriz_train_sha256']
    target=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(target.tobytes()).hexdigest()==m['firma']['target_train_sha256']
    p=pd.read_csv(out/'predicciones_mayo.csv')
    pd.testing.assert_frame_equal(p[['numero_de_cliente','foto_mes','clase_ternaria']],valid[['numero_de_cliente','foto_mes','clase_ternaria']])
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();payments=np.where(y,1072500,-27500)
    np.testing.assert_allclose(p.p_tabpfn,control.p_tabpfn,rtol=0,atol=1e-15)
    pool=Pool(cx,cat_features=module.CAT_COLS)
    for s in seeds:
        mp=out/'modelos'/f'seed{s}.cbm';assert sha(mp)==m['modelos_sha256'][mp.name]
        model=CatBoostClassifier();model.load_model(str(mp))
        assert model.tree_count_==800 and model.feature_names_==cols
        assert set(model.get_cat_feature_indices())=={cols.index(c) for c in module.CAT_COLS}
        params=model.get_all_params();assert params['random_seed']==s and params['loss_function']=='Logloss'
        np.testing.assert_allclose(model.predict_proba(pool)[:,1],p[f'p_cat_seed{s}'],rtol=0,atol=1e-15)
        np.testing.assert_allclose(p[f'p_lgb_seed{s}'],control[f'p_seed{s}'],rtol=0,atol=1e-15)
    def score(v,s,mean=False):
        cb=p[[f'p_cat_seed{k}' for k in seeds]].mean(axis=1).to_numpy() if mean else p[f'p_cat_seed{s}'].to_numpy()
        lb=p[[f'p_lgb_seed{k}' for k in seeds]].mean(axis=1).to_numpy() if mean else p[f'p_lgb_seed{s}'].to_numpy()
        tb=p.p_tabpfn.to_numpy()
        return {'control_entrega8':(lb+tb)/2,'CatBoost_solo':cb,'CatBoost_TabPFN_50_50':(cb+tb)/2,
                'LightGBM_TabPFN_CatBoost_40_40_20':.4*lb+.4*tb+.2*cb}[v]
    r=pd.read_csv(out/'resultados_semillas.csv');assert len(r)==20
    for row in r.itertuples():
        selected=score(row.variante,row.seed)>.025
        assert int(payments[selected].sum())==row.ganancia and int(selected.sum())==row.contactos
        assert int((selected&y).sum())==row.tp and row.ganancia_25pct==row.ganancia/4
    avg=pd.read_csv(out/'lista_promedio5.csv');assert len(avg)==4
    for row in avg.itertuples():assert int(payments[score(row.variante,seeds[0],True)>.025].sum())==row.ganancia
    parts=pd.read_csv(out/'resultados_partes_mayo.csv');assert len(parts)==80
    for row in parts.itertuples():
        sel=(score(row.variante,row.seed)>.025)&p.parte_cliente.eq(row.parte).to_numpy()
        assert int(payments[sel].sum())==row.ganancia
    changes=pd.read_csv(out/'cambios_contactos.csv');assert len(changes)==20
    for row in changes.itertuples():
        old=score('control_entrega8',row.seed)>.025;new=score(row.variante,row.seed)>.025
        add=new&~old;remove=old&~new
        assert int(add.sum())==row.agregados and int(remove.sum())==row.retirados
        assert int((add&y).sum())==row.agregados_baja2 and int((remove&y).sum())==row.retirados_baja2
        assert int(payments[new].sum()-payments[old].sum())==(row.agregados_baja2-row.retirados_baja2)*1100000-(row.agregados-row.retirados)*27500
    sums=r.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean()
    stored=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
    np.testing.assert_allclose(sums.loc[stored.index].to_numpy(),stored[sums.columns].to_numpy(),rtol=0,atol=1e-8)
    assert stored.loc['control_entrega8','ganancia']==258368000
    v=dict(estado='verificado',modelos_catboost_reproducidos=5,ganancias_individuales=20,
           ganancias_lista_promedio5=4,resultados_por_parte=80,cambios_contactos=20,
           matrices_y_target_verificados=True,fit_solo_abril=True,eval_set_mayo=False,api=False,creditos=0,submits=0)
    (out/'verificacion_independiente.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    print(v)

if __name__=='__main__':main()
