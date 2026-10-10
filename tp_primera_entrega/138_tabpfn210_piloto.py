"""Cotiza sin datos; inferencia local210 explicita, limite50k y sin agosto."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tp_primera_entrega/salidas/tabpfn210_vinculos_local_20261010'


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ejecutar',action='store_true');args=ap.parse_args()
    plan=read(OUT/'PLAN.json');m=read(OUT/'payload.json')
    assert m['filas_train']==163284 and m['filas_valid']==163768 and len(m['features'])==210
    assert sha(OUT/'tabpfn210_local.npz')==m['archivo_sha256']
    assert sha(OUT/'predicciones_control_mayo.csv')==m['predicciones_control_sha256']
    from tabpfn_client import estimate_cost,get_api_usage,TabPFNClassifier
    tx=np.broadcast_to(np.float32(0),(163284,210));vx=np.broadcast_to(np.float32(0),(163768,210))
    quote=estimate_cost(tx,vx,model_version=plan['model_version'],n_estimators=2)
    save(OUT/'COTIZACION.json',dict(cotizacion=quote.model_dump(mode='json'),datos_clientes_enviados=False,creditos_consumidos=0,
        max_creditos=plan['max_creditos_piloto'],etapa_final_incluida=False))
    print('Cotizacion piloto210:',quote.estimated_cost,'creditos; no datos enviados.',flush=True)
    if not args.ejecutar:return
    assert quote.estimated_cost<=plan['max_creditos_piloto'],'Cotizacion supera50k; no inferencia'
    statepath=OUT/'api_estado.json'
    if statepath.exists():
        existing=read(statepath)
        if existing['estado']=='completo_verificado':
            assert sha(OUT/'predicciones_tab210_mayo.csv')==existing['predicciones_sha256']
            print('Piloto ya completo; no nueva inferencia.');return
        if existing.get('datos_enviados'):raise RuntimeError('Inferencia previa iniciada; revisar estado antes de repetir gasto')
    before=str(get_api_usage())
    a=np.load(OUT/'tabpfn210_local.npz');xt=a['train'];xv=a['valid'];y=a['target']
    assert xt.shape==(163284,210) and xv.shape==(163768,210) and y.shape==(163284,)
    assert np.unique(y).tolist()==[0,1]
    state=dict(estado='ejecutando_api',datos_enviados=True,cotizacion=quote.model_dump(mode='json'),
        max_creditos=plan['max_creditos_piloto'],cuota_antes=before,final_agosto=False)
    save(statepath,state)
    model=TabPFNClassifier.create_default_for_version(plan['model_version'],n_estimators=2,random_state=214363,
        fit_mode=plan['fit_mode'],inference_precision=plan['inference_precision'],
        categorical_features_indices=[m['features'].index(c) for c in plan['categorical_features']],inference_config=plan['inference_config'])
    try:
        model.fit(xt,y);q=model.predict_proba(xv)[:,list(model.classes_).index(1)]
        assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
        p=pd.read_csv(OUT/'predicciones_control_mayo.csv',float_precision='round_trip')
        p['p_tab210']=q;p.to_csv(OUT/'predicciones_tab210_mayo.csv',index=False)
        state.update(estado='completo_verificado',cuota_despues=str(get_api_usage()),classes=model.classes_.tolist(),
            predicciones_sha256=sha(OUT/'predicciones_tab210_mayo.csv'))
        save(statepath,state);print('Piloto210 completo; predicciones guardadas.',flush=True)
    except Exception:
        state['estado']='fallo_tras_inicio_api_revisar_consumo';save(statepath,state);raise


if __name__=='__main__':main()
