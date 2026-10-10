"""Verifica y prepara una lista promedio5 con TabPFN v3.5, sin llamadas API."""
from datetime import datetime
import hashlib
import importlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TP = ROOT/'tp_primera_entrega'
PACK = ROOT/'entregas/entrega_final_43'
OUT = TP/'salidas/tabpfn35_contra43_20261010'
BOT = TP/'salidas/01_entregas_bot'
SEEDS = [541440,408476,741961,248865,717444]


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    state=read(OUT/'ESTADO_API.json');plan=read(OUT/'PLAN.json');auth=read(OUT/'AUTORIZACION_API.json')
    assert state['estado']=='completo_verificado_pendiente_archivo_entrega'
    assert state['creditos_consumidos']<=auth['max_creditos']==160000
    assert plan['tabpfn']['model_version']=='v3.5' and plan['tabpfn']['target']=='BAJA+2'
    assert sha(OUT/'predicciones_agosto.csv')==state['predicciones_sha256']
    csv_source=OUT/'EnsembleVinculos197TabPFN35Promedio5Corte275.csv'
    assert sha(csv_source)==state['csv_sha256']
    p=pd.read_csv(OUT/'predicciones_agosto.csv',float_precision='round_trip')
    ref=pd.read_csv(PACK/'artefactos/predicciones_agosto.csv.gz',float_precision='round_trip')
    pd.testing.assert_frame_equal(p[['numero_de_cliente','foto_mes']],ref[['numero_de_cliente','foto_mes']])
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and p.numero_de_cliente.is_unique
    pred=ref.drop(columns=['p_tabpfn','score_promedio5']).copy()
    pred['p_tabpfn_fast43']=ref.p_tabpfn
    pred['p_tabpfn']=p.p_tabpfn35
    values=pred[[f'p_lgb_seed{s}' for s in SEEDS]+['p_tabpfn']].to_numpy()
    assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    score=values@np.array([.1]*5+[.5])
    np.testing.assert_allclose(score,p.score_promedio5,rtol=0,atol=1e-15)
    pred['score_promedio5']=p.score_promedio5
    selected=pred.loc[pred.score_promedio5>.0275].sort_values(['score_promedio5','numero_de_cliente'],ascending=[False,True])
    content=''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii')
    assert csv_source.read_bytes()==content and len(selected)==state['contactos']
    models={str(path.relative_to(ROOT)):sha(path) for path in sorted((PACK/'modelos').glob('seed*.txt'))}
    provenance=read(PACK/'procedencia.json')
    assert len(models)==5
    for name,h in models.items(): assert h==provenance['modelos_sha256'][Path(name).name]
    if (OUT/'ENTREGA.json').exists(): raise RuntimeError('Entrega ya creada; verificar antes de repetir')
    number=max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    name='EnsembleVinculos197TabPFN35Promedio5Corte275_'+datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    delivery=BOT/f'{number}_{name}';delivery.mkdir();(delivery/'adjuntos').mkdir()
    csv=delivery/'adjuntos'/f'{name}.csv';csv.write_bytes(content)
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    code=dict(plan['codigo_sha256'])
    code.update({str(path.relative_to(ROOT)):sha(path) for path in [Path(__file__),TP/'105_reproducir_csv_entrega.py',TP/'104_archivar_codigo_entrega.py']})
    signature=dict(plan,codigo_sha256=code)
    meta=dict(estado='completo_verificado_preparado_pendiente',entrega=number,submit=name,enviado=False,
        firma=signature,train_final=[202104,202105],futuro=202108,semillas=SEEDS,
        features_lightgbm=197,features_tabpfn=202,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
        model_version_tabpfn='v3.5',n_estimators_tabpfn=2,seed_tabpfn=214363,
        agregacion='promedio_probabilidades5',pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,operador='>',
        modelos_sha256=models,predicciones_sha256=sha(delivery/'predicciones_agosto.csv'),
        archivos=[dict(score_columna='score_promedio5',archivo=str(csv.relative_to(delivery)),contactos=len(selected),sha256=sha(csv))],
        api=True,creditos=state['creditos_consumidos'],max_creditos=auth['max_creditos'],nuevos_fits_lightgbm=0,nuevos_fits_tabpfn=1,
        referencia43='43_EnsembleVinculos197Promedio5Corte275_20261010_094750',
        cambios_vs43={k:state[k] for k in ['contactos','comunes','agregados','retirados']},
        validacion_local=None,limite_validacion='Solo prueba final agosto autorizada; sin validacion local nueva para esta version. Ganancia publica pendiente.',
        fuentes_sha256={str((OUT/f).relative_to(ROOT)):sha(OUT/f) for f in ['PLAN.json','PAYLOAD.json','AUTORIZACION_API.json','COTIZACION.json','ESTADO_API.json']})
    save(delivery/'manifest.json',meta)
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADA Y VERIFICADA. Pendiente envio manual de un CSV promedio5.\n',encoding='utf-8')
    audit=dict(estado='verificado',probabilidades_validas=True,score_independiente_producto_matricial=True,
        csv_identico_bytes=True,contactos=len(selected),csv_sha256=sha(csv),api=False,creditos=0,
        correlacion_tabpfn_fast_vs35=float(pred[['p_tabpfn_fast43','p_tabpfn']].corr().iloc[0,1]),
        diferencia_media_absoluta_tabpfn=float(np.abs(pred.p_tabpfn-pred.p_tabpfn_fast43).mean()))
    save(delivery/'verificacion_independiente.json',audit)
    note=(f'## Entrega {number}: TabPFN v3.5 frente a43\n\n'
        'Cambio exclusivo de version TabPFN v3.5-fast a v3.5;202variables,targetBAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. '
        'Cinco LightGBM197 originales de43, targetcombinado; mezcla50/50,promedio5,corteestricto>2,75%. '
        f'{len(selected)}clientes; {state["comunes"]}comunes con43,{state["agregados"]}agregados,{state["retirados"]}retirados. '
        f'Consumo real {state["creditos_consumidos"]}creditos, limiteautorizado160.000. '
        'Sin validacion local nueva para esta version; resultado publico pendiente. Paquete43 publicado y mejorpublica100.815M conservados. '
        'Una lista no mide distribucion entre ensembles. Sin envio automatico al Bot.\n\n'
        f'Comando: `submit {name}`. Adjuntar solo `adjuntos/{name}.csv`.\n')
    (delivery/'INFORME.md').write_text(note,encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    record=dict(estado='entrega_preparada_pendiente_envio',entrega=number,carpeta=str(delivery.relative_to(ROOT)),
                submit=name,clientes=len(selected),creditos=state['creditos_consumidos'])
    save(OUT/'ENTREGA.json',record)
    (OUT/'README.md').write_text(note,encoding='utf-8')
    cfgpath=TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    assert cfg['mejor_publico_registrado']['entrega']==43
    cfg['tabpfn35_contra43_final']=record;save(cfgpath,cfg)
    for path in [ROOT/'BITACORA_DMEYF.md',TP/'PLAN_EXPERIMENTOS_20261010.md']:
        with path.open('a',encoding='utf-8') as f: f.write('\n'+note)
    path=TP/'NEXT_STEPS_IDEAS.md';path.write_text(note+'\n'+path.read_text(encoding='utf-8-sig'),encoding='utf-8')
    print(json.dumps(record,indent=2),flush=True)


if __name__=='__main__':main()
