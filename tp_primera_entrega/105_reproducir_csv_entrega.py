"""Regenera listas desde scores guardados y exige hash idéntico al adjunto original."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ap=argparse.ArgumentParser()
ap.add_argument('--entrega',type=Path,default=Path(__file__).resolve().parent.parent)
ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
delivery=args.entrega.resolve();out=args.salida.resolve()
assert out!=delivery and not out.is_relative_to(delivery), 'La salida debe estar fuera de la entrega original'
manifest=json.loads((delivery/'manifest.json').read_text(encoding='utf-8-sig'))
pred=pd.read_csv(delivery/'predicciones_agosto.csv',float_precision='round_trip')
assert pred.numero_de_cliente.is_unique and pred.foto_mes.eq(202108).all()
entries=manifest.get('adjuntos',manifest.get('archivos'))
if not isinstance(entries,list) or not all('sha256' in e and ('seed' in e or 'score_columna' in e) for e in entries):
    raise ValueError('El formato de esta entrega necesita un adaptador de listas')
assert manifest.get('operador','>') in ['>','top_n']
out.mkdir(parents=True,exist_ok=True);results=[]
for entry in entries:
    seed=entry.get('seed','ensemble');score_column=entry.get('score_columna',f'score_seed{seed}')
    if score_column not in pred:raise ValueError('No hay score guardado: '+score_column)
    q=pred[score_column].to_numpy();ids=pred.numero_de_cliente.to_numpy()
    order=np.lexsort((ids,-q))
    selected=ids[order[:entry['top_n']]] if 'top_n' in entry else ids[order[q[order]>manifest['umbral']]]
    original=(delivery/entry['archivo']).read_bytes()
    assert hashlib.sha256(original).hexdigest()==entry['sha256'], 'El adjunto original fue modificado'
    # Preservar también el formato histórico: algunas entregas Windows usan CRLF.
    newline='\r\n' if b'\r\n' in original else '\n'
    content=''.join(str(int(i))+newline for i in selected).encode('ascii')
    digest=hashlib.sha256(content).hexdigest()
    assert digest==entry['sha256'], 'La lista regenerada no coincide con el hash original'
    path=out/Path(entry['archivo']).name
    if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, 'La salida ya contiene otro archivo'
    else:path.write_bytes(content)
    results.append(dict(seed=seed,contactos=len(selected),sha256=digest))
(out/'VERIFICACION.json').write_text(json.dumps(dict(estado='verificado',entrega=str(delivery),
     api=False,creditos=0,archivos=results),indent=2)+'\n',encoding='utf-8')
print('CSV regenerados con hashes idénticos:',len(results))
