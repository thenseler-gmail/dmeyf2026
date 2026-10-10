"""Cinco ensembles completos tipo43: grupos disjuntos de cinco LightGBM197.

Grupo1 reproduce43; grupos2-5 usan veinte nuevas semillas sin seleccion por score.
Cada grupo promedia cinco probabilidades LightGBM y mezcla50/50 con el mismo TabPFN.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
import hashlib
import importlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import duckdb
import numpy as np
import pandas as pd
from features_vinculos import KEYS,FUENTES,FEATURES,agregar_vinculos,verificar_independiente,verificar_ejemplos

base=importlib.import_module('116_promedio20_hist189')
final=importlib.import_module('66_preparar_entrega_hist189')
SOURCE=base.BOT/'43_EnsembleVinculos197Promedio5Corte275_20261010_094750'
SHARED=base.SAL/'tres_exploratorias_final_20261010'
OUT=base.SAL/'cinco_ensembles43_20261010'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=True)
    ref=read(SOURCE/'manifest.json');r16=read(base.D16/'manifest.json')
    assert ref['entrega']==43 and ref['enviado'] and ref['features_lightgbm']==197
    assert ref['umbral']==.0275 and ref['pesos']==dict(lightgbm=.5,tabpfn=.5)
    assert read(SOURCE/'RESULTADO_BOT.json')['media_publica_pesos']==100815000
    original_seeds=ref['semillas']
    assert original_seeds==[541440,408476,741961,248865,717444]
    seeds=original_seeds.copy();rng=np.random.default_rng(20261010)
    while len(seeds)<25:
        s=int(rng.integers(1,1000000))
        if s not in seeds:seeds.append(s)
    groups={str(i+1):seeds[i*5:(i+1)*5] for i in range(5)}
    assert len(set(seeds))==25 and groups['1']==original_seeds
    cols=r16['firma']['features']+FEATURES
    assert cols==ref['firma']['features'] and len(cols)==197
    source_paths=[SOURCE/'manifest.json',SOURCE/'predicciones_agosto.csv',SOURCE/'RESULTADO_BOT.json',
        SOURCE/'verificacion_independiente.json',SOURCE/ref['archivos'][0]['archivo'],
        SHARED/'manifest.json',base.D16/'manifest.json']
    code=['132_preparar_cinco_ensembles43.py','116_promedio20_hist189.py','66_preparar_entrega_hist189.py',
        'features_vinculos.py','features.py','baseline.py','104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']
    signature=dict(train_final=[202104,202105],futuro=202108,features=cols,
        grupos_semillas=groups,semillas=seeds,params=ref['firma']['params'],rounds=273,
        pesos=ref['pesos'],umbral=.0275,operador='>',
        regla_semillas='Grupo1 original43; grupos2-5 bloques sucesivos de default_rng(20261010), unicos, sin elegir por ganancia',
        regla_score='Cada archivo: 0.5*mean(probabilidades de5LightGBM197 del grupo)+0.5*TabPFN202 compartido',
        fuente_entrega=str(SOURCE.relative_to(base.ROOT)),
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in source_paths},
        codigo_sha256={f:base.sha(base.TP/f) for f in code},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb']},
        autorizacion_usuario='Correccion del pedido: generar cinco ensembles completos tipo43, no cinco modelos individuales',
        nuevos_fits_lightgbm=20,fits_lightgbm_reutilizados=5,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False,
        limitacion='La primera replica43 fue previamente seleccionada por resultado; las cuatro nuevas no. '
            'Mismos datos e igual TabPFN compartido: desvio entre ensembles no es intervalo de confianza ni incertidumbre privada.')
    if (OUT/'PLAN.json').exists():assert read(OUT/'PLAN.json')==signature
    else:base.save(OUT/'PLAN.json',signature)
    print('Cinco grupos congelados:',json.dumps(groups),flush=True)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices_finales',api=False,creditos=0))
    _,_,fcols,_,fseeds,xt,xv,y,keys,_=final.cargar()
    assert fcols==r16['firma']['features'] and fseeds==original_seeds
    assert final.matrix_sha(xt)==r16['firma']['matriz_train_sha256']
    assert final.matrix_sha(xv)==r16['firma']['matriz_agosto_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==r16['firma']['target_train_sha256']
    config=read(base.TP/'config.json')
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    trainkeys=history.loc[history.foto_mes.isin([202104,202105]),KEYS].reset_index(drop=True)
    assert len(trainkeys)==len(xt)==327052 and len(keys)==len(xv)==164647
    pd.testing.assert_frame_equal(keys,history.loc[history.foto_mes.eq(202108),KEYS].reset_index(drop=True))
    features=agregar_vinculos(history)
    audit=verificar_independiente(history,features);examples=verificar_ejemplos()
    for frame,x in [(trainkeys,xt),(keys,xv)]:
        joined=frame.merge(features,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(frame,joined[KEYS])
        for c in FEATURES:x[c]=joined[c].to_numpy()
    assert list(xt)==list(xv)==cols
    assert final.matrix_sha(xt)==ref['firma']['matriz_train_sha256']
    assert final.matrix_sha(xv)==ref['firma']['matriz_agosto_sha256']
    old=pd.read_csv(SOURCE/'predicciones_agosto.csv',float_precision='round_trip')
    assert base.sha(SOURCE/'predicciones_agosto.csv')==ref['predicciones_sha256']
    pd.testing.assert_frame_equal(keys,old[KEYS])
    expected={ (base.ROOT/p).name:h for p,h in ref['modelos_sha256'].items() }
    assert set(expected)=={f'seed{s}.txt' for s in original_seeds}
    base.save(OUT/'estado.json',dict(estado='entrenando20_modelos_finales',semillas_nuevas=seeds[5:],api=False,creditos=0))
    values,hashes=base.run_models(xt,xv,y,seeds,signature['params'],OUT/'modelos',SHARED/'modelos_vinculos',expected,'Replica ensemble43')
    np.testing.assert_allclose(values[:,:5],old[[f'p_lgb_seed{s}' for s in original_seeds]],rtol=0,atol=1e-15)
    pred=keys.copy();pred['p_tabpfn']=old.p_tabpfn
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    for i in range(5):
        q=.5*values[:,i*5:(i+1)*5].mean(axis=1)+.5*old.p_tabpfn
        if i==0:
            np.testing.assert_allclose(q,old.score_promedio5,rtol=0,atol=1e-15)
            np.testing.assert_array_equal(q>.0275,old.score_promedio5>.0275)
            # Conservar bytes y orden exactos de la lista43 previamente enviada.
            q=old.score_promedio5
        pred[f'score_ensemble{i+1}']=q
    assert np.isfinite(pred[[f'score_ensemble{i+1}' for i in range(5)]]).all().all()
    if (OUT/'ENTREGA.json').exists():loc=read(OUT/'ENTREGA.json')
    else:
        number=max(int(p.name.split('_')[0]) for p in base.BOT.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
        stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
        name='EnsembleVinculos197CincoEnsemblesCorte275_'+stamp
        loc=dict(entrega=number,submit=name,carpeta=str((base.BOT/f'{number}_{name}').relative_to(base.ROOT)))
        base.save(OUT/'ENTREGA.json',loc)
    delivery=base.ROOT/loc['carpeta'];delivery.mkdir(exist_ok=True);(delivery/'adjuntos').mkdir(exist_ok=True)
    assert not (delivery/'RESULTADO_BOT.json').exists()
    if (delivery/'manifest.json').exists():assert not read(delivery/'manifest.json')['enviado']
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    entries=[];changes=[];sets={}
    oldids=set(old.loc[old.score_promedio5>.0275,'numero_de_cliente'])
    assert len(oldids)==10404
    for i in range(1,6):
        col=f'score_ensemble{i}'
        chosen=pred.loc[pred[col]>.0275].sort_values([col,'numero_de_cliente'],ascending=[False,True])
        ids=set(chosen.numero_de_cliente);sets[i]=ids
        path=delivery/'adjuntos'/f'{loc["submit"]}_ensemble{i}.csv'
        path.write_bytes(''.join(f'{int(cid)}\n' for cid in chosen.numero_de_cliente).encode('ascii'))
        if i==1:assert base.sha(path)==ref['archivos'][0]['sha256']
        entries.append(dict(ensemble=i,semillas=groups[str(i)],score_columna=col,archivo=str(path.relative_to(delivery)),
                            contactos=len(ids),sha256=base.sha(path),equivalente_entrega43=(i==1)))
        changes.append(dict(ensemble=i,contactos=len(ids),comunes_con43=len(ids&oldids),
            agregados_vs43=len(ids-oldids),retirados_vs43=len(oldids-ids)))
    assert len(set(e['sha256'] for e in entries))==5
    pd.DataFrame(changes).to_csv(delivery/'comparacion_ensembles_vs43.csv',index=False)
    overlaps=[dict(ensemble_a=a,ensemble_b=b,comunes=len(sets[a]&sets[b]),union=len(sets[a]|sets[b]),
                   jaccard=len(sets[a]&sets[b])/len(sets[a]|sets[b])) for a in range(1,6) for b in range(a+1,6)]
    pd.DataFrame(overlaps).to_csv(delivery/'solapamiento_ensembles.csv',index=False)
    meta=dict(**loc,estado='preparado_pendiente_verificacion',enviado=False,firma=signature,
        train_final=[202104,202105],futuro=202108,semillas=seeds,grupos_semillas=groups,
        features_lightgbm=197,features_tabpfn=202,target_lightgbm=ref['target_lightgbm'],target_tabpfn=ref['target_tabpfn'],
        pesos=ref['pesos'],umbral=.0275,operador='>',agregacion='cinco_ensembles_cada_uno_promedia_cinco_probabilidades',
        fuente_entrega=str(SOURCE.relative_to(base.ROOT)),fuente_modelos_finales=str(OUT.relative_to(base.ROOT)),
        archivos=entries,modelos_sha256=hashes,predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        matriz_train_sha256=final.matrix_sha(xt),matriz_agosto_sha256=final.matrix_sha(xv),
        verificacion_features=audit,checks_features=examples,comparacion_vs43=changes,
        validacion_local_nuevos_grupos=False,etiquetas_entrenamiento=[202104,202105],etiquetas_auxiliares_extraidas=False,
        public_gain_grupo1_conocido=100815000,public_gain_grupos2a5_desconocido=True,
        nuevos_fits_lightgbm=20,fits_lightgbm_reutilizados=5,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False,
        limitacion=signature['limitacion'])
    base.save(delivery/'manifest.json',meta)
    saved=pd.read_csv(delivery/'predicciones_agosto.csv',float_precision='round_trip')
    for e in entries:
        q=saved[[f'p_lgb_seed{s}' for s in e['semillas']]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
        np.testing.assert_allclose(q,saved[e['score_columna']],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(q>.0275,saved[e['score_columna']].to_numpy()>.0275)
    subprocess.run([sys.executable,str(base.TP/'105_reproducir_csv_entrega.py'),'--entrega',str(delivery),
                    '--salida',str(OUT/'reproduccion_csv')],check=True)
    base.save(delivery/'verificacion_independiente.json',dict(estado='verificado',archivos=5,
        mezcla_reconstruida_por_producto_matricial=True,modelos_recargados=True,
        matrices197_identicas_a43=True,grupo1_csv_identico_a43=True,
        csv_reproducidos_hash_identico=True,grupos_disjuntos=True,fuente43_preservada=True,api=False,creditos=0))
    meta['estado']='completo_verificado_preparado_pendiente';base.save(delivery/'manifest.json',meta)
    base.save(OUT/'manifest.json',dict(estado='completo_verificado',firma=signature,modelos_sha256=hashes,
        entrega=loc['entrega'],fuente_entrega=str(SOURCE.relative_to(base.ROOT))))
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+loc['submit']+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envio manual: adjuntar los CINCO ensembles juntos. Resultado medio/desvio publico desconocido.\n',encoding='utf-8')
    note=f"# Entrega{loc['entrega']}: cinco ensembles completos de43\n\nCada uno: 50% promedio de cinco LightGBM197 +50% TabPFN202 compartido; corte>2,75%. Grupo1 usa las cinco semillas originales y reproduce exactamente43 ($100.815.000 publico). Otros cuatro grupos usan veinte semillas nuevas de RNG congelado, sin seleccion por rendimiento.25modelosLightGBM totales:5reutilizados y20nuevos,273arboles,abril+mayo->agosto; ceroAPI/creditos/nuevosfitsTabPFN.\n\n```json\n"+json.dumps(groups,indent=2)+"\n```\n\n```text\n"+pd.DataFrame(changes).to_string(index=False)+f"\n```\n\nComando: `submit {loc['submit']}`. Adjuntar los CINCO CSV de `adjuntos/` juntos, sin encabezado ni indice. No adjuntar archivos de44 ni predicciones_agosto.csv. No enviado automaticamente.\n\n44 preparaba cinco listas con un solo LightGBM cada una y TabPFN; esta entrega corresponde al pedido corregido de cinco ensembles completos con cinco LightGBM cada uno.44 se conserva como alternativa y no se incluye en este envio.\n\nEl Bot informara media/desvio de cinco ganancias de ensembles. Grupos distintos de semillas pero mismos datos y TabPFN: no es un intervalo de confianza ni garantia privada. Grupo1 ya seleccionado previamente por score publico; las otras cuatro replicas nuevas no fueron seleccionadas por rendimiento. Resultado de nuevos grupos y su media desconocidos. No se ejecuta nueva validacion local: pedido de replicas finales, sin tuning de parametros/corte/pesos ni seleccion de ganadores.\n\nMatrices197 identicas a43, fuentes de vinculos auditadas por lookup independiente, cinco modelos originales reproducidos,25modelos recargados,cinco mezclas reconstruidas por producto matricial y CSV reproducidos con hash identico. Fuente43,modelos y su lista preservados. Codigo firmado archivado.\n"
    (delivery/'INFORME.md').write_text(note,encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    for p,h in signature['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    for p,h in hashes.items():assert base.sha(base.ROOT/p)==h
    result=dict(**loc,estado='completo_verificado_preparado_pendiente',archivos=entries,
        comando='submit '+loc['submit'],grupos_semillas=groups,nuevos_fits_lightgbm=20,
        fits_lightgbm_reutilizados=5,api=False,creditos=0)
    base.save(OUT/'RESULTADO.json',result)
    base.save(OUT/'estado.json',dict(estado='completo_verificado_cinco_ensembles_preparados',entrega=loc['entrega'],api=False,creditos=0))
    summary=f"## Cinco ensembles completos de43 preparados — 2026-10-10\n\nEntrega{loc['entrega']}: cinco CSV, cada uno promedia cinco LightGBM197 y mezcla50/50 con TabPFN202 guardado,corte>2,75%. Grupo1 identico a43, cuatro grupos nuevos con semillas disjuntas y congeladas.20fitsLightGBM nuevos,ceroAPI/creditos. Pedido corregido respecto de44 (unLightGBM por lista). Usar solo los cinco archivos de{loc['entrega']} con `submit {loc['submit']}`; pendientes de envio manual y resultado. Mejor publica43 $100.815.000 preservada. [Informe]({delivery.relative_to(base.TP).as_posix()}/INFORME.md).\n"
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(summary+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+summary.replace('(salidas/','(tp_primera_entrega/salidas/')+'\n'+note)
    with (base.TP/'PLAN_EXPERIMENTOS_20261010.md').open('a',encoding='utf-8') as f:f.write('\n'+summary)
    cfgpath=base.TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    cfg['distribucion_cinco_ensembles_entrega43']=result
    cfg['distribucion_cinco_listas_entrega43']['nota_pedido_corregido']=f'Usuario pide cinco ensembles completos; preparar entrega{loc["entrega"]}.44 conservada como alternativa, no mezclar en el envio.'
    assert cfg['mejor_publico_registrado']['entrega']==43
    base.save(cfgpath,cfg)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
