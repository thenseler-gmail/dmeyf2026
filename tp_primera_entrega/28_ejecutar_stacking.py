"""TabPFN recibe 202 features + probabilidad LightGBM OOF. Requiere preparacion."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from baseline import preparar,metricas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparacion',required=True,type=Path)
    parser.add_argument('--ejecutar-api',action='store_true')
    parser.add_argument('--max-creditos',type=int,default=250000)
    args=parser.parse_args()
    pre=args.preparacion.resolve()
    m=json.loads((pre/'manifest.json').read_text())
    assert m['estado']=='preparado_verificado'
    for f,h in m['codigo_sha256'].items():
        assert hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest()==h,f
    for p,v in m['versiones'].items():
        assert importlib.metadata.version(p)==v,p
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    preparacion=importlib.import_module('27_preparar_stacking')
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('stacking_tabpfn_%Y%m%d_%H%M%S')
    out.mkdir()
    manifest=dict(estado='preparado',fuente_preparacion=str(pre),fuente_sha256=hashlib.sha256((pre/'manifest.json').read_bytes()).hexdigest(),
        features=m['features_base']+[m['feature_nueva']],umbral=0.025,operador='>',model_version=m['model_version'],n_estimators=m['n_estimators'],seed=m['seed_tabpfn'],
        codigo_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),version_tabpfn_client=importlib.metadata.version('tabpfn-client'),
        limitaciones=m['limitaciones'],notas='Stacking usa LightGBM combinado OOF, TabPFN target BAJA+2. Parametros/columnas congelados. Evaluacion temporal mayo/junio, sin limpieza ni haberes ni agosto.')
    def save():
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2,default=str),encoding='utf-8')
    save()
    if args.ejecutar_api:
        if not os.environ.get('TABPFN_TOKEN'):
            raise RuntimeError('Falta credencial en entorno.')
        from tabpfn_client import TabPFNClassifier,estimate_cost,get_api_usage
        manifest['cuota_antes']=str(get_api_usage())
        cuotas={}
        for etapa,s in m['etapas'].items():
            q=estimate_cost(np.zeros((s['filas_train'],203),dtype=np.uint8),np.zeros((s['filas_eval'],203),dtype=np.uint8),model_version=m['model_version'],n_estimators=m['n_estimators'])
            cuotas[etapa]=q.model_dump(mode='json')
        total=sum(q['estimated_cost'] for q in cuotas.values())
        manifest.update(cotizaciones=cuotas,consumo_estimado_total=total)
        save()
        print('Cuota:',manifest['cuota_antes'],'\nCotizacion total:',total,flush=True)
        if total>args.max_creditos:
            raise RuntimeError('Cotizacion supera tope local; sin inferencia.')
    resultados=[]
    for etapa in ['mayo','junio']:
        spec=m['etapas'][etapa]
        _,train,valid,basecols=preparacion.particiones(etapa)
        xt=preparar(train,basecols)[0]; xv=preparar(valid,basecols)[0]
        assert preparacion.hash_array(xt)==spec['matriz_train_base_sha256']
        assert preparacion.hash_array(xv)==spec['matriz_eval_base_sha256']
        assert hashlib.sha256((pre/f'oof_{etapa}.csv').read_bytes()).hexdigest()==spec['oof_sha256']
        assert hashlib.sha256((pre/f'evaluacion_{etapa}.csv').read_bytes()).hexdigest()==spec['evaluacion_sha256']
        oof=pd.read_csv(pre/f'oof_{etapa}.csv'); ev=pd.read_csv(pre/f'evaluacion_{etapa}.csv')
        for df,referencia in [(oof,train),(ev,valid)]:
            assert len(df)==len(referencia)
            pd.testing.assert_frame_equal(df[['numero_de_cliente','foto_mes','clase_ternaria']].reset_index(drop=True),referencia[['numero_de_cliente','foto_mes','clase_ternaria']].reset_index(drop=True))
        feature=m['feature_nueva']
        xt[feature]=oof[feature].to_numpy(); xv[feature]=ev[feature].to_numpy()
        assert list(xt.columns)==manifest['features']==list(xv.columns)
        assert np.isfinite(xt[feature]).all() and np.isfinite(xv[feature]).all()
        y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
        manifest.setdefault('etapas',{})[etapa]=dict(train_meses=spec['train_meses'],mes_eval=spec['mes_eval'],filas_train=len(train),filas_eval=len(valid))
        save()
        if not args.ejecutar_api:
            print('Entradas verificadas:',etapa,xt.shape,xv.shape,flush=True)
            continue
        cols=manifest['features']
        modelo=TabPFNClassifier.create_default_for_version(m['model_version'],n_estimators=m['n_estimators'],random_state=m['seed_tabpfn'],
            fit_mode='fit_preprocessors',inference_precision='autocast',categorical_features_indices=[cols.index(c) for c in ['Visa_status','Master_status','tcuentas']],
            inference_config={'SUBSAMPLE_SAMPLES':None})
        manifest.update(estado='ejecutando',etapa_actual=etapa)
        save()
        modelo.fit(xt.to_numpy(dtype=np.float32),y)
        prob=modelo.predict_proba(xv.to_numpy(dtype=np.float32))[:,list(modelo.classes_).index(1)]
        assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
        pred=ev.copy(); pred['p_stacking']=prob
        pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
        pred['p_mix_3semillas']=(pred[feature]+pred.p_tabpfn_control)/2
        pred['p_mix_referencia']=(pred.p_lightgbm_control+pred.p_tabpfn_control)/2
        for col in ['p_tabpfn_control','p_mix_3semillas','p_mix_referencia','p_stacking']:
            r=metricas(pred.clase_ternaria.eq('BAJA+2').astype(int).to_numpy(),pred[col].to_numpy(),config)
            r['ganancia_25pct']=r['ganancia']/4
            resultados.append(dict(etapa=etapa,modelo=col,**r))
        pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
        pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
        manifest.update(resultados=resultados,etapa_completada=etapa)
        save()
        print(pd.DataFrame(resultados)[['etapa','modelo','contactos','tp','fp','ganancia','ganancia_25pct']].to_string(index=False),flush=True)
        del modelo,train,valid,xt,xv,oof,ev,pred
    if args.ejecutar_api:
        manifest['cuota_despues']=str(get_api_usage())
        print('Cuota despues:',manifest['cuota_despues'],flush=True)
    manifest['estado']='completo' if args.ejecutar_api else 'entradas_verificadas'
    save()
    print('Salida:',out,flush=True)


if __name__=='__main__':
    main()
