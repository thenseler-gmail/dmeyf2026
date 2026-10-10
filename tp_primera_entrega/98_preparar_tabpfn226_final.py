"""Prepara payloads finales para revisión; no envía datos ni consume créditos."""
import argparse
import importlib
import json
from pathlib import Path
import numpy as np
from baseline import preparar

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();out=args.salida
local=json.loads((out/'tabpfn226_payload.json').read_text(encoding='utf-8'))
cols=local['features'];assert len(cols)==226
raw,audit=pipe.leer(final=True)
aug=raw[raw.foto_mes.eq(202108)].reset_index(drop=True)
assert aug.clase_ternaria.isna().all()
xp=preparar(aug,cols)[0].to_numpy(dtype=np.float32)
for name,meses in [('abril_mayo',[202104,202105]),('marzo_junio',[202103,202104,202105,202106])]:
    tr=raw[raw.foto_mes.isin(meses)].reset_index(drop=True)
    assert tr.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(tr,cols)[0].to_numpy(dtype=np.float32)
    y=tr.clase_ternaria.eq('BAJA+2').astype(np.int64).to_numpy()
    path=out/f'tabpfn226_final_{name}.npz'
    np.savez_compressed(path,train=xt,valid=xp,target=y)
    pipe.save(out/f'tabpfn226_final_{name}_payload.json',dict(features=cols,train=meses,prediccion=202108,
          filas_train=len(tr),filas_prediccion=len(aug),target='BAJA+2',ID_mes_no_incluidos=True,
          etiquetas_agosto_no_incluidas=True,autorizacion_final_pendiente=True,enviado=False,
          archivo_sha256=pipe.sha(path),auditoria=audit))
    del xt,y,tr
print('Dos payloads TabPFN226 finales preparados, sin envío ni consumo.',flush=True)
