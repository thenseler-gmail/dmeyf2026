"""Tres entregas autorizadas: mezcla, selector por segmento y ocho vinculos.

Reutiliza general189/Tab202 de16; especialistas y vinculos se ajustan abril+mayo.
No consulta etiquetas de agosto, no llama APIs ni envia al Bot.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
import hashlib
import importlib
import importlib.metadata
import json
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import duckdb
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from features_vinculos import KEYS, FUENTES, FEATURES, agregar_vinculos, verificar_independiente, verificar_ejemplos

base = importlib.import_module('116_promedio20_hist189')
final = importlib.import_module('66_preparar_entrega_hist189')
seg = importlib.import_module('108_segmentos_local')
OUT = base.SAL/'tres_exploratorias_final_20261010'
LOCAL_SEG = base.SAL/'estrategias_segmentos_20261010'
LOCAL_VIN = base.SAL/'vinculos_recurrentes_20261010'
NAMES = ['general', 'general50_especialista50', 'especialistas']
WEIGHTS = dict(zip(NAMES, [0., .5, 1.]))


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def frozen(path, value):
    if path.exists():
        assert read(path) == value, str(path)+' no coincide con configuracion congelada'
    else:
        base.save(path, value)


def prepare_delivery(key, title, pred, signature, hashes, validation, checks):
    location = OUT/(key+'_ENTREGA.json')
    if location.exists():
        loc = read(location)
    else:
        number = max(int(p.name.split('_')[0]) for p in base.BOT.iterdir()
                     if p.is_dir() and p.name.split('_')[0].isdigit())+1
        stamp = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
        name = key+'Promedio5Corte275_'+stamp
        loc = dict(entrega=number, submit=name, carpeta=str((base.BOT/f'{number}_{name}').relative_to(base.ROOT)))
        base.save(location, loc)
    delivery = base.ROOT/loc['carpeta']
    delivery.mkdir(exist_ok=True)
    (delivery/'adjuntos').mkdir(exist_ok=True)
    assert not (delivery/'RESULTADO_BOT.json').exists()
    if (delivery/'manifest.json').exists():
        assert not read(delivery/'manifest.json')['enviado']
    assert pred.numero_de_cliente.is_unique and pred.foto_mes.eq(202108).all() and len(pred)==164647
    assert np.isfinite(pred.score_promedio5).all()
    chosen = pred.loc[pred.score_promedio5>.0275].sort_values(
        ['score_promedio5', 'numero_de_cliente'], ascending=[False, True])
    target = delivery/'adjuntos'/(loc['submit']+'.csv')
    target.write_bytes(''.join(f'{int(i)}\n' for i in chosen.numero_de_cliente).encode('ascii'))
    pred.to_csv(delivery/'predicciones_agosto.csv', index=False)
    control = pd.read_csv(base.D36/'predicciones_agosto.csv', float_precision='round_trip')
    pd.testing.assert_frame_equal(pred[KEYS], control[KEYS])
    oldids = set(control.loc[control.score_promedio5>.0275, 'numero_de_cliente'])
    newids = set(chosen.numero_de_cliente)
    assert len(oldids)==10420
    changes = dict(control36_contactos=len(oldids), candidato_contactos=len(newids),
                   agregados=len(newids-oldids), retirados=len(oldids-newids), comunes=len(oldids&newids))
    diff = pred[KEYS].copy()
    diff['score_control36'] = control.score_promedio5
    diff['score_candidato'] = pred.score_promedio5
    diff['seleccion_control36'] = control.score_promedio5>.0275
    diff['seleccion_candidato'] = pred.score_promedio5>.0275
    diff.loc[diff.seleccion_control36!=diff.seleccion_candidato].to_csv(delivery/'cambios_vs36.csv', index=False)
    meta = dict(**loc, estado='preparado_pendiente_verificacion', enviado=False, firma=signature,
        train_final=[202104, 202105], futuro=202108, semillas=signature['semillas'],
        features_lightgbm=len(signature['features']), features_tabpfn=202,
        target_lightgbm='BAJA+1/BAJA+2', target_tabpfn='BAJA+2',
        agregacion='promedio_probabilidades_cinco_semillas', pesos=signature['pesos'], umbral=.0275, operador='>',
        fuente_entrega=str(base.D16.relative_to(base.ROOT)), fuente_control=str(base.D36.relative_to(base.ROOT)),
        fuente_modelos_finales=str(OUT.relative_to(base.ROOT)), modelos_sha256=hashes,
        predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        archivos=[dict(score_columna='score_promedio5', archivo=str(target.relative_to(delivery)),
                       contactos=len(chosen), sha256=base.sha(target))],
        cambios_vs36=changes, validacion_local=validation, checks=checks,
        excepcion_promocion_autorizada=True, supera_puerta_local_estricta=False,
        api=False, creditos=0, nuevos_fits_tabpfn=0, submit_automatico=False,
        etiquetas_entrenamiento=[202104, 202105], etiquetas_auxiliares_extraidas=False,
        limitacion='Prueba exploratoria autorizada. Mayo reutilizado; sin garantia publica. Agosto sin etiquetas. '
                   'Seleccion final por segmento ajustada con mayo completo, no es nueva validacion.')
    base.save(delivery/'manifest.json', meta)
    saved = pd.read_csv(delivery/'predicciones_agosto.csv', float_precision='round_trip')
    seeds = signature['semillas']
    if 'segmento' in saved:
        a = saved[[f'p_general_seed{s}' for s in seeds]].to_numpy()
        b = saved[[f'p_especialista_seed{s}' for s in seeds]].to_numpy()
        w = saved.peso_especialista.to_numpy()
        expected = np.full(len(saved), .5) if key=='EnsembleGeneralEspecialistas' else saved.segmento.map(
            {int(g):WEIGHTS[r['modelo']] for g,r in signature['seleccion_final_por_segmento'].items()}).to_numpy()
        np.testing.assert_array_equal(w, expected)
        independent = (1-w)*np.sum(a*np.full(5,.1), axis=1)+w*np.sum(b*np.full(5,.1), axis=1)+.5*saved.p_tabpfn
    else:
        independent = saved[[f'p_lgb_seed{s}' for s in seeds]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(independent, saved.score_promedio5, rtol=0, atol=1e-15)
    np.testing.assert_array_equal(np.asarray(independent)>.0275, saved.score_promedio5.to_numpy()>.0275)
    subprocess.run([sys.executable, str(base.TP/'105_reproducir_csv_entrega.py'), '--entrega', str(delivery),
                    '--salida', str(OUT/('reproduccion_'+str(loc['entrega'])))], check=True)
    base.save(delivery/'verificacion_independiente.json', dict(estado='verificado', contactos=len(chosen),
        score_reconstruido=True, asignacion_pesos_verificada=True, csv_reproducido_hash_identico=True,
        modelos_recargados=True, control36_reproducido=True, cambios_vs36=changes, api=False, creditos=0))
    meta['estado']='completo_verificado_preparado_pendiente'
    base.save(delivery/'manifest.json', meta)
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+loc['submit']+'\n', encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envio manual al Bot, un CSV. Resultado publico desconocido.\n', encoding='utf-8')
    note = f"# Entrega {loc['entrega']}: {title}\n\n{signature['descripcion']}\n\nAbril+mayo -> agosto. Cinco semillas, 273 arboles, corte >2,75%. Una lista de {len(chosen):,} clientes. TabPFN202 guardado de16: cero API y creditos.\n\nValidacion local lista promedio: delta total ${validation['delta_total']:,}; equivalente25% ${validation['delta_total']/4:,}. Delta medio de cinco listas individuales: ${validation['media_delta_semillas']:,}. No pasa puerta estricta; submit exploratorio autorizado. Mayo reutilizado, sin garantia publica.\n\nFrente a36: {changes['agregados']} agregados, {changes['retirados']} retirados y {changes['comunes']} comunes. Referencia36 publica $98.175.000 conservada. Agosto sin etiquetas: ganancia desconocida.\n\nComando: `submit {loc['submit']}`. Adjuntar exclusivamente `{target.name}`, sin encabezado ni indice. No enviado automaticamente.\n\nModelos finales compartidos en `{str(OUT.relative_to(base.ROOT))}`, recargados y firmados. Matrices originales verificadas contra16; selector y segmentador congelados antes de puntuar agosto. Ocho vinculos reconstruidos con mes calendario anterior y lookup independiente. Scores reconstruidos desde archivo y CSV reproducido con hash identico. Codigo archivado.\n"
    if key=='EnsembleModeloPorSegmento':
        note += '\nLa validacion informada selecciona con tres partes de mayo y evalua en la cuarta, cuatro cruces. Para desplegar se ajusta el mismo selector con todo mayo; esa seleccion final NO se mide como validacion. Desempate: general, mezcla, especialistas. Segmentador entrenado en abril sin etiquetas, no se reajusta.\n\n```json\n'+json.dumps(signature['seleccion_final_por_segmento'], ensure_ascii=False, indent=2)+'\n```\n'
    (delivery/'INFORME.md').write_text(note, encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    result = dict(**loc, titulo=title, csv=str(target.relative_to(base.ROOT)), contactos=len(chosen),
                  comando='submit '+loc['submit'], cambios_vs36=changes, validacion_local=validation,
                  estado='preparado_verificado_pendiente_envio_manual')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result, note


def main():
    OUT.mkdir(exist_ok=True)
    r16=read(base.D16/'manifest.json')
    sl=read(LOCAL_SEG/'RESULTADO_LOCAL.json')
    sv=read(LOCAL_VIN/'RESULTADO_LOCAL.json')
    sr=read(LOCAL_SEG/'RESULTADO_SELECCION_MODELOS.json')
    for d,r in [(LOCAL_SEG,sl),(LOCAL_VIN,sv)]:
        assert r['estado']=='completo_verificado'
        assert base.sha(d/'predicciones_mayo.csv')==r['predicciones_sha256']
    assert base.sha(LOCAL_SEG/'segmentador.joblib')==sl['segmentador_sha256']
    assert base.sha(LOCAL_SEG/'predicciones_seleccion_modelos.csv')==sr['predicciones_sha256']
    seeds=r16['firma']['seeds'];cols=r16['firma']['features'];params=r16['firma']['params']
    local=pd.read_csv(LOCAL_SEG/'predicciones_mayo.csv', float_precision='round_trip')
    pay=np.where(local.clase_ternaria.eq('BAJA+2'),1072500,-27500)
    choices={}
    for g in range(4):
        ix=local.segmento.eq(g).to_numpy()
        gains={n:int(pay[ix & (local['score_'+n].to_numpy()>.0275)].sum()) for n in NAMES}
        chosen=NAMES[int(np.argmax(list(gains.values())))]
        choices[str(g)]=dict(modelo=chosen,peso_especialista=WEIGHTS[chosen],ganancias_mayo_ajuste=gains)
    sources=[base.D16/'manifest.json',base.D16/'predicciones_agosto.csv',base.D36/'manifest.json',
             base.D36/'predicciones_agosto.csv',LOCAL_SEG/'PLAN.json',LOCAL_SEG/'RESULTADO_LOCAL.json',
             LOCAL_SEG/'RESULTADO_SELECCION_MODELOS.json',LOCAL_SEG/'segmentador.joblib',
             LOCAL_SEG/'predicciones_mayo.csv',LOCAL_SEG/'predicciones_seleccion_modelos.csv',
             LOCAL_VIN/'PLAN.json',LOCAL_VIN/'RESULTADO_LOCAL.json',LOCAL_VIN/'predicciones_mayo.csv']
    code=['127_preparar_tres_exploratorias.py','119_modelos_por_segmento.py','121_elegir_modelo_por_segmento.py',
          '118_vinculos_recurrentes_local.py','108_segmentos_local.py','66_preparar_entrega_hist189.py',
          '116_promedio20_hist189.py','features_vinculos.py','features.py','baseline.py',
          '104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']
    plan=dict(train=[202104,202105],futuro=202108,features=cols,semillas=seeds,params=params,rounds=273,
        pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.0275,operador='>',
        segmentador='Reusar el ajustado en abril, sin refit ni cambio de IDs',
        seleccion_final_por_segmento=choices,desempate=NAMES,
        seleccion_final='Maxima ganancia por grupo en TODO mayo a corte fijo; ajuste de politica despues de crossfit, no validacion',
        nuevas_features=FEATURES,fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in sources},
        codigo_sha256={f:base.sha(base.TP/f) for f in code},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb','scikit-learn','joblib']},
        autorizacion_usuario='Generar las tres de la tabla, submits exploratorios cercanos autorizados',
        nuevos_fits_lightgbm=25,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False)
    frozen(OUT/'PLAN.json',plan)
    print('Politica congelada antes de cargar agosto:',json.dumps(choices),flush=True)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices',api=False,creditos=0))
    _,_,fcols,_,fseeds,xt,xv,y,keys,_=final.cargar()
    assert fcols==cols and fseeds==seeds
    assert final.matrix_sha(xt)==r16['firma']['matriz_train_sha256']
    assert final.matrix_sha(xv)==r16['firma']['matriz_agosto_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==r16['firma']['target_train_sha256']
    config=read(base.TP/'config.json')
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    trainkeys=history.loc[history.foto_mes.isin([202104,202105]),KEYS].reset_index(drop=True)
    assert len(trainkeys)==len(xt)==327052
    pd.testing.assert_frame_equal(keys,history.loc[history.foto_mes.eq(202108),KEYS].reset_index(drop=True))
    cluster=joblib.load(LOCAL_SEG/'segmentador.joblib')
    assert cluster['sources']==seg.SOURCES
    def groups(x):
        with threadpool_limits(limits=4):
            return cluster['cluster'].predict(np.clip(cluster['scaler'].transform(cluster['imputer'].transform(seg.transform(x))),-5,5))
    gt=groups(xt);gv=groups(xv)
    for month,file in [(202104,'segmentos_train.csv'),(202105,'segmentos_mayo.csv')]:
        ix=trainkeys.foto_mes.eq(month).to_numpy()
        old=pd.read_csv(LOCAL_SEG/file)
        pd.testing.assert_frame_equal(trainkeys.loc[ix,KEYS].reset_index(drop=True),old[KEYS])
        np.testing.assert_array_equal(gt[ix],old.segmento)
    assert set(gt)==set(gv)=={0,1,2,3}
    trainkeys.assign(segmento=gt).to_csv(OUT/'segmentos_train.csv',index=False)
    keys.assign(segmento=gv).to_csv(OUT/'segmentos_agosto.csv',index=False)
    old=pd.read_csv(base.D16/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(keys,old[KEYS])
    general=old[[f'p_lgb_seed{s}' for s in seeds]].to_numpy()
    hashes={}
    for i,s in enumerate(seeds):
        path=base.D16/'modelos'/f'seed{s}.txt'
        assert base.sha(path)==r16['modelos_sha256'][path.name]
        np.testing.assert_allclose(lgb.Booster(model_file=str(path)).predict(xv,validate_features=True,num_threads=4),general[:,i],rtol=0,atol=1e-15)
        hashes[str(path.relative_to(base.ROOT))]=base.sha(path)
    control=pd.read_csv(base.D36/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(keys,control[KEYS])
    np.testing.assert_allclose(.5*general.mean(axis=1)+.5*old.p_tabpfn,control.score_promedio5,rtol=0,atol=1e-15)
    specialists=np.full((len(xv),5),np.nan)
    folder=OUT/'modelos_especialistas';folder.mkdir(exist_ok=True)
    fitstats=[]
    for g in range(4):
        it=np.flatnonzero(gt==g);iv=np.flatnonzero(gv==g)
        assert len(it)>1000 and len(iv)>0 and set(y[it])=={0,1}
        for i,s in enumerate(seeds):
            base.save(OUT/'estado.json',dict(estado='entrenando_especialistas',segmento=g,seed=s,api=False,creditos=0))
            start=time.perf_counter();path=folder/f'segmento{g}_seed{s}.txt'
            if path.exists():model=lgb.Booster(model_file=str(path))
            else:
                model=lgb.train(dict(params,seed=s),lgb.Dataset(xt.iloc[it],label=y[it]),num_boost_round=273)
                model.save_model(str(path))
            assert model.feature_name()==cols and model.num_trees()==273
            q=model.predict(xv.iloc[iv],validate_features=True,num_threads=4)
            np.testing.assert_array_equal(q,lgb.Booster(model_file=str(path)).predict(xv.iloc[iv],validate_features=True,num_threads=4))
            specialists[iv,i]=q;hashes[str(path.relative_to(base.ROOT))]=base.sha(path)
            fitstats.append(dict(segmento=g,seed=s,train=len(it),agosto=len(iv),segundos=time.perf_counter()-start))
            print('Especialista final',g,s,round(fitstats[-1]['segundos'],2),'s',flush=True)
    assert np.isfinite(specialists).all() and ((specialists>=0)&(specialists<=1)).all()
    shared=keys.copy();shared['segmento']=gv;shared['p_tabpfn']=old.p_tabpfn
    for i,s in enumerate(seeds):
        shared[f'p_general_seed{s}']=general[:,i];shared[f'p_especialista_seed{s}']=specialists[:,i]
    shared.to_csv(OUT/'predicciones_especialistas_agosto.csv',index=False)
    base.save(OUT/'manifest.json',dict(estado='especialistas_verificados',firma=plan,modelos_sha256=hashes,
        fitstats=fitstats,predicciones_especialistas_sha256=base.sha(OUT/'predicciones_especialistas_agosto.csv')))
    outputs=[];notes=[]
    blend=next(r for r in sl['resumen'] if r['estrategia']=='general50_especialista50')
    validations=[dict(delta_total=blend['delta_total'],media_delta_semillas=blend['delta_media_semillas'],
                      semillas_mejoran=blend['semillas_mejoran'],fuente=str((LOCAL_SEG/'RESULTADO_LOCAL.json').relative_to(base.ROOT))),
                 dict(next(r for r in sr['resumen'] if r['politica']=='modelo_por_segmento_elegido'),
                      fuente=str((LOCAL_SEG/'RESULTADO_SELECCION_MODELOS.json').relative_to(base.ROOT)))]
    for key,title,w,validation in [
        ('EnsembleGeneralEspecialistas','Mezcla general/especialistas',np.full(len(keys),.5),validations[0]),
        ('EnsembleModeloPorSegmento','Eleccion de modelo por segmento',np.array([choices[str(g)]['peso_especialista'] for g in gv]),validations[1])]:
        pred=shared.copy();pred['peso_especialista']=w
        pred['score_promedio5']=.5*((1-w)*general.mean(axis=1)+w*specialists.mean(axis=1))+.5*old.p_tabpfn
        sig=dict(plan,descripcion=('25% general189 +25% especialistas189 +50% TabPFN202.' if key=='EnsembleGeneralEspecialistas'
                                   else 'Por grupo elegir general, mezcla50/50 o especialista dentro del50% LightGBM;50% TabPFN202 fijo.'))
        result,note=prepare_delivery(key,title,pred,sig,hashes,validation,dict(segmentador_abril_reutilizado=True,
            asignaciones_abril_mayo_reproducidas=True,politica_congelada_antes_agosto=True))
        outputs.append(result);notes.append(note)
    del pred,shared,specialists,general,local
    features=agregar_vinculos(history)
    audit=verificar_independiente(history,features);examples=verificar_ejemplos()
    for frame,x in [(trainkeys,xt),(keys,xv)]:
        joined=frame.merge(features,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(frame,joined[KEYS])
        for c in FEATURES:x[c]=joined[c].to_numpy()
    assert list(xt)==list(xv)==cols+FEATURES and len(xv.columns)==197
    assert read(LOCAL_VIN/'PLAN.json')['features_candidato']==list(xv)
    base.save(OUT/'estado.json',dict(estado='entrenando_vinculos197',api=False,creditos=0))
    values,vhash=base.run_models(xt,xv,y,seeds,params,OUT/'modelos_vinculos',OUT/'sin_reuso',{},'Vinculos197 final')
    pred=keys.copy();pred['p_tabpfn']=old.p_tabpfn
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    pred['score_promedio5']=.5*values.mean(axis=1)+.5*old.p_tabpfn
    sig=dict(plan,features=cols+FEATURES,descripcion='50% LightGBM197 con ocho vinculos recurrentes +50% TabPFN202.',
             matriz_train_sha256=final.matrix_sha(xt),matriz_agosto_sha256=final.matrix_sha(xv))
    manifest=read(OUT/'manifest.json');manifest.update(estado='todos_modelos_verificados',modelos_vinculos_sha256=vhash,
        verificacion_vinculos=audit,checks_vinculos=examples,matriz197_train_sha256=sig['matriz_train_sha256'],
        matriz197_agosto_sha256=sig['matriz_agosto_sha256'])
    base.save(OUT/'manifest.json',manifest)
    validation=dict(delta_total=sv['delta_total'],media_delta_semillas=sv['media_delta_semillas'],
                    semillas_mejoran=sv['semillas_mejoran'],fuente=str((LOCAL_VIN/'RESULTADO_LOCAL.json').relative_to(base.ROOT)))
    result,note=prepare_delivery('EnsembleVinculos197','Ocho vinculos recurrentes',pred,sig,vhash,validation,
                                 dict(features_independientes=audit,ejemplos=examples))
    outputs.append(result);notes.append(note)
    for p,h in plan['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    for p,h in {**hashes,**vhash}.items():assert base.sha(base.ROOT/p)==h
    # El manifiesto compartido ahora incluye ambas familias de modelos: renovar archivo de fuentes.
    for result in outputs:importlib.import_module('104_archivar_codigo_entrega').archivar(base.ROOT/result['carpeta'])
    base.save(OUT/'RESULTADO.json',dict(estado='completo_verificado',entregas=outputs,api=False,creditos=0))
    base.save(OUT/'estado.json',dict(estado='completo_verificado_tres_entregas_preparadas',entregas=[r['entrega'] for r in outputs],api=False,creditos=0))
    summary='# Tres submits exploratorios preparados — 2026-10-10\n\nUsuario confirma las tres variantes cercanas. Una lista promedio5 por variante, corte>2,75%, abril+mayo->agosto. Preparadas y verificadas, pendientes de envio manual y resultado publico. Referencia36 $98.175.000 conservada. 20 especialistas finales compartidos entre dos entregas y cinco fits finales de vinculos197; ceroAPI/creditos.\n\n'
    for result in outputs:
        rel=(base.ROOT/result['carpeta']).relative_to(base.TP).as_posix()
        summary+=f"- **{result['entrega']} — {result['titulo']}**: {result['contactos']:,} clientes. [CSV]({rel}/adjuntos/{result['submit']}.csv); [informe]({rel}/INFORME.md). Comando: `submit {result['submit']}`.\n"
    summary+='\nEsperar resultados de estas entregas antes de seguir con experimentos. Pendiente posterior: paso3, auditoria de calidad/drift. No ejecutado en esta tanda. Cada ganancia publica ya corresponde al25%; no dividir otra vez. Todas son pruebas exploratorias, no mejoras demostradas.\n'
    (OUT/'ENTREGAS_PARA_BOT.md').write_text(summary,encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+summary+'\n'+'\n'.join(notes))
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(summary+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    with (base.TP/'PLAN_EXPERIMENTOS_20261010.md').open('a',encoding='utf-8') as f:f.write('\n'+summary)
    cfgpath=base.TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    cfg['politica_exploratoria_20261010']['tres_entregas_adicionales']=outputs
    cfg['politica_exploratoria_20261010']['estado']='40 y tres adicionales preparadas; esperar resultados publicos antes de nuevos experimentos'
    base.save(cfgpath,cfg)
    print(json.dumps(outputs,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
