"""Inferencia local226 después de autorización específica; sin fit final ni Bot."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
from tabpfn_client import TabPFNClassifier, estimate_cost, get_api_usage

ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True)
ap.add_argument('--max-creditos',type=int,default=50000);args=ap.parse_args();out=args.salida
m=json.loads((out/'tabpfn226_payload.json').read_text(encoding='utf-8'))
assert (out/'AUTORIZACION_TABPFN226.md').exists(), 'Falta registrar autorización del usuario'
assert os.environ.get('TABPFN_TOKEN'), 'Falta credencial en memoria'
assert hashlib.sha256((out/'tabpfn226_local.npz').read_bytes()).hexdigest()==m['archivo_sha256']
a=np.load(out/'tabpfn226_local.npz');xt=a['train'];xv=a['valid'];y=a['target']
assert xt.shape==(163284,226) and xv.shape==(163768,226) and y.shape==(163284,)
assert np.unique(y).tolist()==[0,1]
quote=estimate_cost(xt,xv,model_version='v3.5-fast',n_estimators=2)
assert quote.estimated_cost<=args.max_creditos, 'Cotización supera límite; no inferencia'
before=str(get_api_usage())
state=dict(estado='cotizado',cotizacion=quote.model_dump(mode='json'),cuota_antes=before,
           max_creditos=args.max_creditos,datos_enviados=False)
def save():
    (out/'tabpfn226_estado.json').write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
save()
model=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,random_state=214363,
      fit_mode='fit_preprocessors',inference_precision='autocast',
      categorical_features_indices=[m['features'].index(c) for c in ['Visa_status','Master_status','tcuentas']],
      inference_config={'SUBSAMPLE_SAMPLES':None})
state.update(estado='ejecutando_api',datos_enviados=True);save()
model.fit(xt,y);q=model.predict_proba(xv)[:,list(model.classes_).index(1)]
assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
pred=pd.read_csv(out/'predicciones_ablacion_mayo.csv')
pred['p_tab226']=q;pred.to_csv(out/'predicciones_tab226_mayo.csv',index=False)
after=str(get_api_usage());used=lambda s:int(re.search(r'used (\d+)',s).group(1))
state.update(estado='completo_verificado',cuota_despues=after,creditos=used(after)-used(before),
             predicciones_sha256=hashlib.sha256((out/'predicciones_tab226_mayo.csv').read_bytes()).hexdigest())
save();print('TabPFN226 local completo; consumo:',state['creditos'],flush=True)
