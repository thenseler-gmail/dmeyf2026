"""TabPFN203features: mayo/junio, señal haberes, controles guardados, API autorizada."""
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
    parser.add_argument('--ejecutar-api',action='store_true')
    parser.add_argument('--max-creditos',type=int,default=250000)
    args=parser.parse_args()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    old=json.loads((SAL/'tabpfn_historicas_20261004_172322_339836/manifest.json').read_text())
    for archivo in ['features.py','baseline.py']:
        assert hashlib.sha256((Path(__file__).parent/archivo).read_bytes()).hexdigest()==old['codigo_sha256'][archivo]
    for paquete,v in old['versiones'].items():
        assert importlib.metadata.version(paquete)==v,paquete
    assert old['model_version']=='v3.5-fast' and old['n_estimators']==2
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('tabpfn_haberes_%Y%m%d_%H%M%S')
    out.mkdir()
    protocolo=dict(estado='preparado',model_version='v3.5-fast',n_estimators=2,seed=config['seed'],umbral=0.025,operador='>',
        nueva_feature='abandono_pasa_a_cero_mpayroll',peso_tabpfn=0.5,versiones=old['versiones'],
        codigo_sha256={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['25_tabpfn_haberes.py','features.py','baseline.py','features_abandono.py']},
        notas='Mayo abril->mayo retrospectivo; junio marzo/abril->junio alineado, exploratorio. Un solo bloque elegido en mayo, sin tuning ni muestreo. Controles TabPFN202 y LightGBM guardados. No genera agosto ni envia al bot.')
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2,default=str),encoding='utf-8')
    save()
    if args.ejecutar_api:
        if not os.environ.get('TABPFN_TOKEN'):
            raise RuntimeError('Falta credencial en entorno del proceso.')
        from tabpfn_client import TabPFNClassifier,estimate_cost,get_api_usage
        protocolo['cuota_antes']=str(get_api_usage())
        cotizaciones={}
        for etapa,nt,nv in [('mayo',163284,163768),('junio',326184,164114)]:
            q=estimate_cost(np.zeros((nt,203),dtype=np.uint8),np.zeros((nv,203),dtype=np.uint8),model_version='v3.5-fast',n_estimators=2)
            cotizaciones[etapa]=q.model_dump(mode='json')
        total=sum(q['estimated_cost'] for q in cotizaciones.values())
        protocolo.update(cotizaciones=cotizaciones,consumo_estimado_total=total)
        save()
        print('Cuota:',protocolo['cuota_antes'],'\nCreditos estimados:',total,flush=True)
        if total>args.max_creditos:
            raise RuntimeError('Cotizacion supera tope local; sin inferencia.')
    preparar_experimento=importlib.import_module('11_tabpfn_historicas').preparar_experimento
    resultados=[]
    claves=['numero_de_cliente','foto_mes']
    for etapa in ['mayo','junio']:
        experimental,train,valid,originales,historicas=preparar_experimento(ROOT,config,'ampliadas',etapa)
        nueva=protocolo['nueva_feature']
        for df in [train,valid]:
            conocido=df.mpayroll.notna()&df.lag_1_mpayroll.notna()
            df[nueva]=((df.lag_1_mpayroll>0)&df.mpayroll.eq(0)).astype(float).where(conocido)
        cols=originales+historicas+[nueva]
        assert len(cols)==203 and cols[:-1]==old['originales']+old['nuevas']
        xt=preparar(train,cols)[0]; xv=preparar(valid,cols)[0]
        y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
        protocolo.setdefault('etapas',{})[etapa]=dict(train=experimental['split']['train_meses'],eval=experimental['split']['validacion_meses'],filas_train=len(train),filas_eval=len(valid),faltantes_nueva_train=int(xt[nueva].isna().sum()),faltantes_nueva_eval=int(xv[nueva].isna().sum()))
        protocolo['features']=cols
        save()
        if not args.ejecutar_api:
            print('Preparacion local:',etapa,len(train),len(valid),len(cols),flush=True)
            continue
        modelo=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,
            random_state=config['seed'],fit_mode='fit_preprocessors',inference_precision='autocast',
            categorical_features_indices=[cols.index(c) for c in ['Visa_status','Master_status','tcuentas']],
            inference_config={'SUBSAMPLE_SAMPLES':None})
        protocolo.update(estado='ejecutando',etapa_actual=etapa)
        save()
        modelo.fit(xt.to_numpy(dtype=np.float32),y)
        prob=modelo.predict_proba(xv.to_numpy(dtype=np.float32))[:,list(modelo.classes_).index(1)]
        assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
        pred=valid[claves+['clase_ternaria']].copy()
        pred['p_tabpfn_nuevo']=prob
        # Persistir inmediatamente la inferencia pagada, antes de comparaciones.
        pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
        if etapa=='mayo':
            base=pd.read_csv(SAL/'abandono_20261005_145518/predicciones_mayo.csv')[claves+['clase_ternaria','p_base','p_historicas']]
            nuevo=pd.read_csv(SAL/'abandono_familias_20261005_150004/haberes_mayo.csv')[claves+['clase_ternaria','p_lightgbm']].rename(columns={'p_lightgbm':'p_lgb_nuevo'})
        else:
            base=pd.read_csv(SAL/'abandono_20261005_150102/predicciones_junio.csv')[claves+['clase_ternaria','p_base','p_historicas','p_nuevo']]
            nuevo=base[claves+['clase_ternaria','p_nuevo']].rename(columns={'p_nuevo':'p_lgb_nuevo'})
            base=base.drop(columns='p_nuevo')
        for df in [base,nuevo]:
            pred=pred.merge(df,on=claves,validate='one_to_one',suffixes=('','_fuente'))
            assert len(pred)==len(valid)==len(df) and pred.clase_ternaria.eq(pred.clase_ternaria_fuente).all()
            pred=pred.drop(columns='clase_ternaria_fuente')
        pred=pred.rename(columns={'p_historicas':'p_tabpfn_base','p_base':'p_lgb_base'})
        for tb in ['base','nuevo']:
            for lb in ['base','nuevo']:
                pred[f'p_mezcla_tab_{tb}_lgb_{lb}']=(pred[f'p_tabpfn_{tb}']+pred[f'p_lgb_{lb}'])/2
        for col in ['p_tabpfn_base','p_tabpfn_nuevo']+[c for c in pred if c.startswith('p_mezcla_')]:
            met=metricas(pred.clase_ternaria.eq('BAJA+2').astype(int).to_numpy(),pred[col].to_numpy(),config)
            met['ganancia_25pct']=met['ganancia']/4
            resultados.append(dict(etapa=etapa,modelo=col,**met))
        pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
        pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
        protocolo.update(resultados=resultados,etapa_completada=etapa)
        save()
        print(pd.DataFrame(resultados)[['etapa','modelo','contactos','tp','fp','ganancia','ganancia_25pct']].to_string(index=False),flush=True)
        del modelo,xt,xv,train,valid
    if args.ejecutar_api:
        protocolo['cuota_despues']=str(get_api_usage())
        print('Cuota despues:',protocolo['cuota_despues'],flush=True)
    protocolo['estado']='completo' if args.ejecutar_api else 'preparado'
    save()
    print('Salida:',out,flush=True)


if __name__=='__main__':
    main()
