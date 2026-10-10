"""Aplica corte ya congelado en mayo a entrega8; no entrenamiento/API/Bot."""
import hashlib
import importlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    root=Path(__file__).resolve().parents[1];sal=root/'tp_primera_entrega/salidas'
    audit=Path(sys.argv[1]);m=json.loads((audit/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='verificado' and m['candidato_viable'] and not m['lectura_junio']
    module=importlib.import_module('54_explorar_corte_score')
    source=Path(m['fuente']);assert sha(source)==m['fuente_sha256']
    p=pd.read_csv(source);y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    scores=np.column_stack([(p[f'p_seed{s}']+p.p_tabpfn)/2 for s in m['semillas']])
    f=pd.read_csv(audit/'particiones_clientes.csv');pd.testing.assert_frame_equal(f[['numero_de_cliente','foto_mes']],p[['numero_de_cliente','foto_mes']])
    for c in m['cortes']:
        tr=f.fold.ne(c['fold']).to_numpy();u,_=module.choose(module.curves(scores[tr],y[tr]))
        assert u==c['umbral']
        # Etiquetas de clientes reservados no influyen en seleccion del corte.
        altered=y.copy();altered[~tr]=~altered[~tr]
        assert module.choose(module.curves(scores[tr],altered[tr]))[0]==u
    u,band=module.choose(module.curves(scores,y));assert u==m['corte_final']
    src=sal/'01_entregas_bot/8_EnsembleAbrilMayo5_20261005_220000'
    fm=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    assert fm['train_final']==[202104,202105] and fm['firma']['semillas']==m['semillas']
    assert len(fm['firma']['features'])==202
    pred=pd.read_csv(src/'predicciones_agosto.csv')
    assert len(pred)==164647 and pred.foto_mes.eq(202108).all() and not pred.numero_de_cliente.duplicated().any()
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleAbrilMayoCorte33_%Y%m%d_%H%M%S')
    folders=sal/'01_entregas_bot';number=max(int(p.name.split('_')[0]) for p in folders.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
    out=folders/f'{number}_{name}';out.mkdir();adj=out/'adjuntos_semillas';adj.mkdir()
    files=[];compare=[]
    for s in m['semillas']:
        score=(pred[f'p_seed{s}']+pred.p_tabpfn)/2
        assert np.isfinite(score).all() and score.between(0,1).all()
        df=pred.loc[score>u,['numero_de_cliente']].copy();df['score']=score[score>u]
        df=df.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=adj/f'{name}_semillas_seed{s}.csv'
        path.write_text(''.join(f'{int(i)}\n' for i in df.numero_de_cliente),encoding='ascii')
        ids=pd.read_csv(path,header=None)[0].to_numpy()
        np.testing.assert_array_equal(ids,df.numero_de_cliente.to_numpy())
        assert len(ids)==len(set(ids)) and set(ids)<=set(pred.numero_de_cliente[score>.025])
        files.append(dict(seed=s,archivo=str(path.relative_to(out)),contactos=len(ids),sha256=sha(path)))
        compare.append(dict(seed=s,contactos_025=int((score>.025).sum()),contactos_033=len(ids),menos_contactos=int((score>.025).sum())-len(ids)))
    cmd='submit '+name+'_semillas'
    (out/'MENSAJE_SEMILLAS.txt').write_text(cmd+'\n',encoding='ascii')
    pd.DataFrame(compare).to_csv(out/'comparacion_contactos_agosto.csv',index=False)
    meta=dict(estado='verificado_preparado',estado_envio='pendiente',enviado=False,submit=name,
         fuente_predicciones=str(src/'predicciones_agosto.csv'),fuente_sha256=sha(src/'predicciones_agosto.csv'),
         fuente_corte=str(audit),fuente_corte_manifest_sha256=sha(audit/'manifest.json'),
         semillas=m['semillas'],umbral=u,operador='>',peso_tabpfn=.5,train_final=[202104,202105],futuro=202108,
         features=202,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
         nuevos_fits=0,api=False,creditos=0,archivos=files,limitaciones=m['limitacion'])
    (out/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'verificacion.json').write_text(json.dumps(dict(estado='verificado',adjuntos=5,cortes_cruzados_reproducidos=4,
         etiquetas_reservadas_no_influyen=True,ids_y_hashes=True,umbral=u),indent=2),encoding='utf-8')
    (out/'ESTADO_ENVIO.txt').write_text('PENDIENTE envio manual. Adjuntar cinco CSV de adjuntos_semillas.\n'+cmd+'\n',encoding='utf-8')
    (out/'INFORME.md').write_text('# Candidato: corte 3,3% sobre entrega8\n\nMismos modelos202 y ventana abril+mayo de entrega8; no trayectorias. Solo cambia corte2,5%->3,3%. Mezcla50/50 tratada como score, no P(BAJA+2) calibrada. Cinco semillas fijas. Seleccion de corte en mayo mediante cuatro particiones por cliente, sin junio ni publico.\n\nFuente del analisis: '+str(audit/'INFORME.md')+'\n\nLa ganancia publica es desconocida. '+m['limitacion']+'\n\n'+cmd+'\n',encoding='utf-8')
    print('Entrega:',out);print(pd.DataFrame(compare).to_string(index=False));print(cmd)

if __name__=='__main__':main()
