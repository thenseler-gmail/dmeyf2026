"""OOF por cliente y mes: prepara LightGBM -> TabPFN sin llamadas API.

Cada fila recibe promedio de tres semillas de LightGBM que excluyen al cliente
entero. Para las filas de marzo no se utilizan etiquetas/filas de abril.
El OOF es retrospectivo dentro del pool permitido, no un backtest prospectivo
de cada fila de entrenamiento. Evaluacion: nunca entra en el pool de fit.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
NUEVA='p_lightgbm_oof'
ETAPAS={
    'mayo':dict(train=[202104],mes=202105,base=SAL/'revision_umbral_20261005_131001/2_lgbm_catedra_hist_20261004_225654_bajas_trial6_mayo.csv',tab=SAL/'tabpfn_historicas_20261004_165442_887149/predicciones.csv'),
    'junio':dict(train=[202103,202104],mes=202106,base=SAL/'ensemble_junio_20261005_134901/predicciones_junio.csv',tab=SAL/'tabpfn_historicas_20261004_172322_339836/predicciones.csv')}


def guardar(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding='utf-8')


def hash_array(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float32).tobytes()).hexdigest()


def particiones(etapa):
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    prep=importlib.import_module('11_tabpfn_historicas').preparar_experimento
    _,train,valid,originales,historicas=prep(ROOT,config,'ampliadas',etapa)
    return config,train,valid,originales+historicas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida',type=Path,help='Retoma solo etapas/folds locales pendientes.')
    args=parser.parse_args()
    fuente=SAL/'revision_umbral_20261005_131001/bajas/manifest.json'
    ref=json.loads(fuente.read_text())
    elegido=ref['elegido']; semillas=ref['semillas'][:3]
    assert elegido['target']=='bajas' and elegido['trial']==6
    for f in ['features.py','baseline.py']:
        assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==ref['codigo_sha256'][f]
    out=args.salida or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('stacking_preparado_%Y%m%d_%H%M%S')
    out.mkdir(parents=True,exist_ok=True)
    hashes={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['27_preparar_stacking.py','11_tabpfn_historicas.py','features.py','baseline.py']}
    manifest=dict(estado='preparando',fuente_lightgbm=str(fuente),elegido=elegido,semillas_lightgbm=semillas,
        folds=5,semilla_folds=214363,features_base=ref['features'],feature_nueva=NUEVA,umbral=0.025,operador='>',
        model_version='v3.5-fast',n_estimators=2,seed_tabpfn=214363,codigo_sha256=hashes,
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','duckdb','numpy','pandas','scikit-learn']},
        protocolo='OOF: cinco grupos de clientes disjuntos, tres semillas por fold. Fit de cada fila solo usa meses <= su mes, dentro del pool de train. Evaluacion usa promedio de tres modelos entrenados en todo el pool permitido.',
        limitaciones='Mayo y junio reutilizados. Parametros LightGBM seleccionados antes en mayo. OOF interno usa etiquetas de otros clientes del mismo mes: no es prediccion prospectiva de cada fila de train. Marzo OOF tiene menor historia/train que abril. OOF usa 80% de clientes y evaluacion fit completo.',
        etapas={})
    if (out/'manifest.json').exists():
        anterior=json.loads((out/'manifest.json').read_text())
        for campo in ['codigo_sha256','elegido','semillas_lightgbm','features_base','versiones']:
            assert anterior[campo]==manifest[campo],campo
        manifest=anterior
    guardar(out/'manifest.json',manifest)
    for etapa,spec in ETAPAS.items():
        if manifest['etapas'].get(etapa,{}).get('estado')=='completo':
            print('Etapa ya completa:',etapa,flush=True); continue
        config,train,valid,columnas=particiones(etapa)
        assert columnas==manifest['features_base'] and len(columnas)==202
        assert sorted(train.foto_mes.unique().tolist())==spec['train']
        xt=preparar(train,columnas)[0]; xv=preparar(valid,columnas)[0]
        y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
        clientes=np.sort(train.numero_de_cliente.unique())
        rng=np.random.default_rng(manifest['semilla_folds'])
        clientes=rng.permutation(clientes)
        mapa=pd.Series(np.arange(len(clientes))%5,index=clientes)
        folds=train.numero_de_cliente.map(mapa).to_numpy(dtype=int)
        oof=np.full((len(train),len(semillas)),np.nan)
        audit=[]
        for mes in sorted(train.foto_mes.unique()):
            for fold in range(5):
                iv=np.flatnonzero((train.foto_mes.to_numpy()==mes)&(folds==fold))
                it=np.flatnonzero((train.foto_mes.to_numpy()<=mes)&(folds!=fold))
                assert len(iv)>0 and len(it)>0 and len(np.unique(y[it]))==2
                assert set(train.numero_de_cliente.iloc[it]).isdisjoint(set(train.numero_de_cliente.iloc[iv]))
                assert train.foto_mes.iloc[it].max()<=mes
                assert train.foto_mes.iloc[it].max()<spec['mes']
                audit.append(dict(mes_predicho=int(mes),fold=fold,filas_train=len(it),filas_oof=len(iv),max_mes_fit=int(train.foto_mes.iloc[it].max()),clientes_solapados=0))
                for j,seed in enumerate(semillas):
                    cache=out/f'{etapa}_oof_{mes}_{fold}_{seed}.npy'
                    if cache.exists():
                        p=np.load(cache,allow_pickle=False)
                    else:
                        model=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt.iloc[it],label=y[it]),num_boost_round=elegido['num_boost_round'])
                        p=model.predict(xt.iloc[iv])
                        np.save(cache,p,allow_pickle=False)
                    assert len(p)==len(iv) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
                    oof[iv,j]=p
                print(etapa,'mes',mes,'fold',fold+1,'de 5 completo',flush=True)
        assert np.isfinite(oof).all()
        oof_df=train[['numero_de_cliente','foto_mes','clase_ternaria']].copy()
        oof_df['fold_cliente']=folds
        for j,seed in enumerate(semillas):
            oof_df[f'p_oof_seed{seed}']=oof[:,j]
        oof_df[NUEVA]=oof.mean(axis=1)
        oof_df.to_csv(out/f'oof_{etapa}.csv',index=False)
        guardar(out/f'auditoria_folds_{etapa}.json',audit)
        # Control completo: predecir sin etiquetas del mes evaluado y reproducir CSV.
        base=pd.read_csv(spec['base'])
        claves=['numero_de_cliente','foto_mes']
        pd.testing.assert_frame_equal(valid[claves].reset_index(drop=True),base[claves].reset_index(drop=True))
        assert valid.clase_ternaria.reset_index(drop=True).equals(base.clase_ternaria.reset_index(drop=True))
        control=lgb.train(dict(elegido['params'],seed=semillas[0]),lgb.Dataset(xt,label=y),num_boost_round=elegido['num_boost_round'])
        assert np.allclose(control.predict(xv),base[f'p_seed{semillas[0]}'],rtol=1e-10,atol=1e-12)
        ev=base[claves+['clase_ternaria']].copy()
        ev[NUEVA]=base[[f'p_seed{s}' for s in semillas]].mean(axis=1)
        ev['p_lightgbm_control']=base[[c for c in base if c.startswith('p_seed')]].mean(axis=1)
        tab=pd.read_csv(spec['tab'])[claves+['clase_ternaria','p_historicas']]
        ev=ev.merge(tab,on=claves,validate='one_to_one',suffixes=('','_tab'))
        assert len(ev)==len(valid)==len(tab) and ev.clase_ternaria.eq(ev.clase_ternaria_tab).all()
        ev=ev.drop(columns='clase_ternaria_tab').rename(columns={'p_historicas':'p_tabpfn_control'})
        ev.to_csv(out/f'evaluacion_{etapa}.csv',index=False)
        manifest['etapas'][etapa]=dict(estado='completo',train_meses=spec['train'],mes_eval=spec['mes'],filas_train=len(train),filas_eval=len(valid),
            matriz_train_base_sha256=hash_array(xt),matriz_eval_base_sha256=hash_array(xv),oof_sha256=hashlib.sha256((out/f'oof_{etapa}.csv').read_bytes()).hexdigest(),
            evaluacion_sha256=hashlib.sha256((out/f'evaluacion_{etapa}.csv').read_bytes()).hexdigest(),folds=audit,
            control_full_fit_reproducido=True,fuente_tabpfn=str(spec['tab']),fuente_lightgbm=str(spec['base']))
        guardar(out/'manifest.json',manifest)
        print('Etapa verificada:',etapa,'filas OOF',len(train),'evaluacion',len(valid),flush=True)
        del xt,xv,train,valid,oof,base,tab,ev
    manifest['estado']='preparado_verificado'
    guardar(out/'manifest.json',manifest)
    print('PREPARACION COMPLETA:',out,flush=True)


if __name__=='__main__':
    main()
