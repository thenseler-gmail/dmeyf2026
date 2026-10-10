"""Una lista promedio5 invertidos202, corte>2,75; sin llamadas API."""
import importlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
OUT=base.SAL/'invertidos202_corte275_20261010'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    plan=read(OUT/'PLAN.json');payload=read(OUT/'payload.json');state=read(OUT/'api_estado.json')
    assert state['estado']=='completo_verificado'
    p=OUT/'predicciones_completas_agosto.csv';assert base.sha(p)==state['predicciones_sha256']
    pred=pd.read_csv(p,float_precision='round_trip');old=pd.read_csv(OUT/'predicciones_lgb_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(pred[old.columns],old)
    assert len(pred)==164647 and pred.foto_mes.eq(202108).all() and not pred.numero_de_cliente.duplicated().any()
    cols=[f'p_lgb_baja2_seed{s}' for s in plan['semillas']]
    pred['score_promedio5']=.5*pred[cols].mean(axis=1)+.5*pred.p_tab_combinado
    independent=pred[cols+['p_tab_combinado']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(independent,pred.score_promedio5,rtol=0,atol=1e-15)
    selected=pred.loc[pred.score_promedio5>.0275].sort_values(['score_promedio5','numero_de_cliente'],ascending=[False,True])
    if (OUT/'ENTREGA.json').exists():raise RuntimeError('Entrega ya creada; verificar antes de repetir')
    number=max(int(d.name.split('_')[0]) for d in base.BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    name='EnsembleInvertidos202Promedio5Corte275_'+datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    delivery=base.BOT/f'{number}_{name}';delivery.mkdir();(delivery/'adjuntos').mkdir()
    csv=delivery/'adjuntos'/f'{name}.csv';csv.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    assert csv.read_text(encoding='ascii')==''.join(f'{int(i)}\n' for i in selected.numero_de_cliente)
    meta=dict(estado='completo_verificado_preparado_pendiente',entrega=number,submit=name,enviado=False,
        firma=plan,train_final=[202104,202105],futuro=202108,features_lightgbm=202,features_tabpfn=202,
        target_lightgbm='BAJA+2',target_tabpfn='BAJA+1/BAJA+2',semillas=plan['semillas'],pesos=plan['pesos'],umbral=.0275,operador='>',
        agregacion='promedio_probabilidades5',fuente_entrega=str(OUT.relative_to(base.ROOT)),
        modelos_sha256=payload['modelos_lightgbm_sha256'],predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        archivos=[dict(score_columna='score_promedio5',archivo=str(csv.relative_to(delivery)),contactos=len(selected),sha256=base.sha(csv))],
        validacion_local=read(OUT/'RESULTADO_LOCAL.json'),api=True,creditos=state['creditos_consumidos'],
        limitacion=plan['limitacion'],excepcion_promocion_autorizada='Prueba exploratoria solicitada por usuario; no garantia publica.')
    base.save(delivery/'manifest.json',meta)
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envio manual de un CSV promedio5.\n',encoding='utf-8')
    note=f'# Entrega{number}: targets invertidos202\n\nLightGBM BAJA+2 y TabPFN combinado, ambos202variables, abril+mayo→agosto. Promedio5 LightGBM, mezcla50/50 y score>2,75%. {len(selected)}clientes. Un solo CSV; no representa distribucion entre ensembles.\n\nConsumo TabPFN: {state["creditos_consumidos"]}creditos. Resultado público pendiente. Mejor43 conservada.\n\nComando: `submit {name}`.\n'
    (delivery/'INFORME.md').write_text(note,encoding='utf-8')
    base.save(delivery/'verificacion_independiente.json',dict(estado='verificado',score_reconstruido=True,clientes=len(selected),csv_sha256=base.sha(csv)))
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    record=dict(estado='entrega_preparada_verificada',entrega=number,carpeta=str(delivery.relative_to(base.ROOT)),submit=name,clientes=len(selected),creditos=state['creditos_consumidos'])
    base.save(OUT/'ENTREGA.json',record)
    cfgpath=base.TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    cfg['pendiente_ultima_hora'].update(estado='entrega_preparada_pendiente_envio',umbral=.0275,agregacion='promedio5probabilidades',entrega_final=record)
    base.save(cfgpath,cfg)
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+note)
    nxt=base.TP/'NEXT_STEPS_IDEAS.md';nxt.write_text(note+'\n'+nxt.read_text(encoding='utf-8-sig'),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
