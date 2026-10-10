"""Cotizacion por dimensiones; envio202 combinado solo con autorizacion concreta."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tp_primera_entrega/salidas/invertidos202_corte275_20261010'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ejecutar',action='store_true');args=ap.parse_args()
    plan=read(OUT/'PLAN.json');payload=read(OUT/'payload.json')
    assert sha(OUT/'payload_tabpfn.npz')==payload['npz_sha256']
    assert sha(OUT/'predicciones_lgb_agosto.csv')==payload['predicciones_lgb_sha256']
    for name,h in plan['codigo_sha256'].items():assert sha(ROOT/'tp_primera_entrega'/name)==h
    from tabpfn_client import estimate_cost,get_api_usage,TabPFNClassifier
    tx=np.broadcast_to(np.float32(0),(327052,202));px=np.broadcast_to(np.float32(0),(164647,202))
    quote=estimate_cost(tx,px,model_version=plan['model_version'],n_estimators=2)
    save(OUT/'COTIZACION.json',dict(cotizacion=quote.model_dump(mode='json'),datos_clientes_enviados=False,
        creditos_consumidos=0,max_creditos_propuesto=plan['max_creditos_propuesto']))
    print('Cotizacion final202:',quote.estimated_cost,'creditos; solo dimensiones enviadas.',flush=True)
    if not args.ejecutar:return
    auth=read(OUT/'AUTORIZACION_API.json')
    assert auth['autorizado'] and auth['destino']=='Prior Labs' and auth['target']=='BAJA+1/BAJA+2'
    assert quote.estimated_cost<=auth['max_creditos']<=plan['max_creditos_propuesto']
    path=OUT/'api_estado.json'
    if path.exists():
        previous=read(path)
        if previous['estado']=='completo_verificado':
            assert sha(OUT/'predicciones_completas_agosto.csv')==previous['predicciones_sha256'];return
        if previous.get('datos_enviados'):raise RuntimeError('API iniciada previamente: revisar consumo antes de reintentar')
    a=np.load(OUT/'payload_tabpfn.npz');xt=a['train'];xp=a['predict'];y=a['target']
    assert xt.shape==(327052,202) and xp.shape==(164647,202) and np.unique(y).tolist()==[0,1]
    state=dict(estado='ejecutando_api',datos_enviados=True,cuota_antes=str(get_api_usage()),cotizacion=quote.model_dump(mode='json'))
    save(path,state)
    try:
        model=TabPFNClassifier.create_default_for_version(plan['model_version'],n_estimators=2,random_state=214363,
            fit_mode=plan['fit_mode'],inference_precision=plan['inference_precision'],
            categorical_features_indices=[plan['features'].index(c) for c in plan['categorical_features']],inference_config=plan['inference_config'])
        model.fit(xt,y);q=model.predict_proba(xp)[:,list(model.classes_).index(1)]
        assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
        p=pd.read_csv(OUT/'predicciones_lgb_agosto.csv',float_precision='round_trip');p['p_tab_combinado']=q
        p.to_csv(OUT/'predicciones_completas_agosto.csv',index=False)
        state.update(estado='completo_verificado',cuota_despues=str(get_api_usage()),classes=model.classes_.tolist(),
            predicciones_sha256=sha(OUT/'predicciones_completas_agosto.csv'))
        used=lambda t:int(re.search(r'used (\d+)',t).group(1))
        state['creditos_consumidos']=used(state['cuota_despues'])-used(state['cuota_antes']);save(path,state)
        print('API completa; consumo',state['creditos_consumidos'],flush=True)
    except Exception:
        state['estado']='fallo_tras_inicio_api_revisar_consumo';save(path,state);raise


if __name__=='__main__':main()
