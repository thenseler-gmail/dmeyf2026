"""Sólo cotización: envía dimensiones, no datos ni etiquetas. No inferencia."""
import argparse
import json
from pathlib import Path
import numpy as np
from tabpfn_client import estimate_cost

ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
payload=json.loads((args.salida/'tabpfn226_payload.json').read_text(encoding='utf-8'))
assert len(payload['features'])==226 and not payload['enviado']
quotes={}
for nombre,ntrain,npredict in [('local_abril_mayo',163284,163768),
                              ('final_abril_mayo_agosto',327052,164647),
                              ('final_marzo_junio_agosto',654066,164647)]:
    # estimate_cost sólo inspecciona shape; esta vista no contiene datos de clientes.
    tx=np.broadcast_to(np.float32(0),(ntrain,226))
    xp=np.broadcast_to(np.float32(0),(npredict,226))
    quote=estimate_cost(tx,xp,model_version='v3.5-fast',n_estimators=2)
    quotes[nombre]=quote.model_dump(mode='json')
    print(nombre,'costo estimado',quote.estimated_cost,flush=True)
(args.salida/'cotizacion_tabpfn226.json').write_text(json.dumps(
    dict(cotizaciones=quotes,datos_clientes_enviados=False,creditos_consumidos=0,
         elegibilidad_no_garantizada=True,inferencia_autorizada=False),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
