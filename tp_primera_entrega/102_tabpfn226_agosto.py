"""TabPFN226 abril+mayo→agosto, después de autorización específica final."""
import argparse
import json
import os
import re
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from tabpfn_client import TabPFNClassifier, estimate_cost, get_api_usage

ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True)
ap.add_argument('--max-creditos',type=int,default=80000);args=ap.parse_args();out=args.salida
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
assert (out/'AUTORIZACION_FINAL.md').exists(), 'Falta autorización específica final'
assert os.environ.get('TABPFN_TOKEN'), 'Falta credencial en memoria'
assert m['train']==[202104,202105] and m['prediccion']==202108
assert len(m['features_tabpfn'])==226 and not set(['numero_de_cliente','foto_mes','clase_ternaria']).intersection(m['features_tabpfn'])
assert hashlib.sha256((out/'payload_api.npz').read_bytes()).hexdigest()==m['payload_sha256']
arrays=np.load(out/'payload_api.npz');xt=arrays['train'];xp=arrays['valid'];y=arrays['target']
assert xt.shape==(327052,226) and xp.shape==(164647,226) and y.shape==(327052,)
assert np.unique(y).tolist()==[0,1]
quote=estimate_cost(xt,xp,model_version='v3.5-fast',n_estimators=2)
assert quote.estimated_cost<=args.max_creditos, 'Cotización supera límite; no fit'
state=dict(estado='cotizado',cotizacion=quote.model_dump(mode='json'),max_creditos=args.max_creditos,
           cuota_antes=str(get_api_usage()),datos_enviados=False)
def save():
    (out/'tabpfn_estado.json').write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
save()
model=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,random_state=214363,
      fit_mode='fit_preprocessors',inference_precision='autocast',
      categorical_features_indices=[m['features_tabpfn'].index(c) for c in ['Visa_status','Master_status','tcuentas']],
      inference_config={'SUBSAMPLE_SAMPLES':None})
state.update(estado='ejecutando_api',datos_enviados=True);save()
model.fit(xt,y);q=model.predict_proba(xp)[:,list(model.classes_).index(1)]
assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
keys=pd.read_csv(out/'claves_agosto.csv');assert len(keys)==len(q) and keys.numero_de_cliente.is_unique
keys['p_tab226']=q;keys.to_csv(out/'predicciones_tab226_agosto.csv',index=False)
after=str(get_api_usage());used=lambda s:int(re.search(r'used (\d+)',s).group(1))
state.update(estado='completo_verificado',cuota_despues=after,creditos=used(after)-used(state['cuota_antes']),
      predicciones_sha256=hashlib.sha256((out/'predicciones_tab226_agosto.csv').read_bytes()).hexdigest(),classes=model.classes_.tolist())
save();print('TabPFN226 agosto completo; consumo:',state['creditos'],flush=True)
