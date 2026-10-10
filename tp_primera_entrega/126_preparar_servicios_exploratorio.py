"""Entrega exploratoria193 autorizada pese a no pasar puerta local entre semillas."""
import importlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from features_vinculos import FUENTES,KEYS,agregar_vinculos,verificar_independiente,verificar_ejemplos

base=importlib.import_module('116_promedio20_hist189')
pilot=importlib.import_module('124_servicios_recurrentes_local')
final=importlib.import_module('66_preparar_entrega_hist189')
OUT=base.SAL/'servicios_final_exploratorio_20261010'
def main():
    OUT.mkdir(exist_ok=True)
    local=json.loads((pilot.OUT/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    spec=json.loads((pilot.OUT/'PLAN.json').read_text(encoding='utf-8'))
    ref=json.loads((base.D16/'manifest.json').read_text(encoding='utf-8'))
    controlref=json.loads((base.D36/'manifest.json').read_text(encoding='utf-8'))
    assert local['estado']=='completo_verificado' and not local['supera_control_local']
    assert local['delta_total']==137500 and local['media_delta_semillas']==-7018000
    assert base.sha(pilot.OUT/'predicciones_mayo.csv')==local['predicciones_sha256']
    signature=dict(train=[202104,202105],futuro=202108,features=spec['features_candidato'],
        nuevas_features=pilot.FEATURES,semillas=spec['semillas'],params=spec['params'],rounds=273,
        pesos=spec['pesos'],umbral=.0275,operador='>',
        politica='Submit exploratorio, usuario autoriza relajar puerta local; no es mejora demostrada',
        fecha_autorizacion='2026-10-10',texto_autorizacion='tengo submits igual...relajar un poco la regla...Submiteemos algo que este cerca',
        fuente_entrega=str(base.D16.relative_to(base.ROOT)),fuente_control=str(base.D36.relative_to(base.ROOT)),
        fuente_validacion=str(pilot.OUT.relative_to(base.ROOT)),
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in [
            base.D16/'manifest.json',base.D16/'predicciones_agosto.csv',base.D36/'manifest.json',
            base.D36/'predicciones_agosto.csv',pilot.OUT/'RESULTADO_LOCAL.json',pilot.OUT/'PLAN.json']},
        codigo_sha256={f:base.sha(base.TP/f) for f in ['126_preparar_servicios_exploratorio.py','124_servicios_recurrentes_local.py',
            '66_preparar_entrega_hist189.py','features_vinculos.py','features.py','baseline.py','116_promedio20_hist189.py',
            '104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb']},
        api=False,creditos=0,submit_automatico=False)
    path=OUT/'PLAN.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf-8'))==signature
    else:base.save(path,signature)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices_finales',api=False,creditos=0))
    _,_,cols,_,seeds,xt,xv,y,keys,_=final.cargar()
    assert cols==spec['features_control'] and seeds==spec['semillas']
    assert final.matrix_sha(xt)==ref['firma']['matriz_train_sha256']
    assert final.matrix_sha(xv)==ref['firma']['matriz_agosto_sha256']
    assert __import__('hashlib').sha256(y.tobytes()).hexdigest()==ref['firma']['target_train_sha256']
    config=json.loads((base.TP/'config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(base.ROOT/config['dataset'])).create_view('datos')
        history=con.sql('SELECT '+','.join(KEYS+FUENTES)+' FROM datos WHERE foto_mes BETWEEN 202103 AND 202108 ORDER BY foto_mes,numero_de_cliente').df()
    # Only feature sources, no auxiliary-month labels, in the historical query.
    features=agregar_vinculos(history);audit=verificar_independiente(history,features)
    checks=verificar_ejemplos()
    trainkeys=history.loc[history.foto_mes.isin([202104,202105]),KEYS].reset_index(drop=True)
    assert len(trainkeys)==len(xt)==327052 and len(keys)==len(xv)==164647
    assert trainkeys.sort_values(['foto_mes','numero_de_cliente']).reset_index(drop=True).equals(trainkeys)
    for frame,x in [(trainkeys,xt),(keys,xv)]:
        new=frame.merge(features,on=KEYS,how='left',sort=False,validate='one_to_one')
        pd.testing.assert_frame_equal(frame,new[KEYS])
        for c in pilot.FEATURES:x[c]=new[c].to_numpy()
    assert list(xt)==list(xv)==signature['features'] and len(xv.columns)==193
    old=pd.read_csv(base.D16/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(keys,old[KEYS])
    for s in seeds:
        modelpath=base.D16/'modelos'/f'seed{s}.txt';assert base.sha(modelpath)==ref['modelos_sha256'][modelpath.name]
        q=lgb.Booster(model_file=str(modelpath)).predict(xv[cols],validate_features=True,num_threads=4)
        np.testing.assert_allclose(q,old[f'p_lgb_seed{s}'],rtol=0,atol=1e-15)
    control=pd.read_csv(base.D36/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(keys,control[KEYS])
    baseline=.5*old[[f'p_lgb_seed{s}' for s in seeds]].mean(axis=1)+.5*old.p_tabpfn
    np.testing.assert_allclose(baseline,control.score_promedio5,rtol=0,atol=1e-15)
    baseline_ids=set(control.loc[control.score_promedio5>.0275,'numero_de_cliente'])
    assert len(baseline_ids)==10420
    base.save(OUT/'estado.json',dict(estado='entrenando_final',semillas=seeds,api=False,creditos=0))
    values,hashes=base.run_models(xt,xv,y,seeds,signature['params'],OUT/'modelos',OUT/'sin_reuso',{},'Servicios finales')
    pred=keys.copy();pred['p_tabpfn']=old.p_tabpfn
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    pred['score_promedio5']=.5*values.mean(axis=1)+.5*old.p_tabpfn
    independent=np.mean(.5*values+.5*old.p_tabpfn.to_numpy()[:,None],axis=1)
    np.testing.assert_allclose(independent,pred.score_promedio5,rtol=0,atol=1e-15)
    selected=pred.loc[pred.score_promedio5>.0275].sort_values(['score_promedio5','numero_de_cliente'],ascending=[False,True])
    assert selected.numero_de_cliente.is_unique
    chosen=set(selected.numero_de_cliente)
    changes=dict(control36_contactos=10420,candidato_contactos=len(selected),
        agregados=len(chosen-baseline_ids),retirados=len(baseline_ids-chosen),comunes=len(chosen&baseline_ids))
    assert changes['comunes']+changes['agregados']==len(selected)
    assert changes['comunes']+changes['retirados']==10420
    pred.to_csv(OUT/'predicciones_agosto.csv',index=False)
    if (OUT/'ENTREGA.json').exists():
        location=json.loads((OUT/'ENTREGA.json').read_text(encoding='utf-8'));delivery=base.ROOT/location['carpeta'];number=location['entrega'];name=location['submit']
    else:
        number=max(int(d.name.split('_')[0]) for d in base.BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
        stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
        name=f'EnsembleServicios193Promedio5Corte275_{stamp}'
        delivery=base.BOT/f'{number}_{name}';delivery.mkdir();(delivery/'adjuntos').mkdir()
        base.save(OUT/'ENTREGA.json',dict(entrega=number,submit=name,carpeta=str(delivery.relative_to(base.ROOT))))
    assert not (delivery/'RESULTADO_BOT.json').exists()
    target=delivery/'adjuntos'/f'{name}.csv'
    target.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    changes_df=keys.copy();changes_df['score_control36']=baseline;changes_df['score_candidato']=pred.score_promedio5
    changes_df['seleccion_control36']=baseline>.0275;changes_df['seleccion_candidato']=pred.score_promedio5>.0275
    changes_df.loc[changes_df.seleccion_control36!=changes_df.seleccion_candidato].to_csv(delivery/'cambios_vs36.csv',index=False)
    manifest=dict(estado='preparado_pendiente_verificacion',entrega=number,submit=name,enviado=False,
        firma=signature,train_final=[202104,202105],futuro=202108,semillas=seeds,
        features_lightgbm=193,features_tabpfn=202,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
        agregacion='promedio_probabilidades_cinco_semillas',pesos=signature['pesos'],umbral=.0275,operador='>',
        fuente_entrega=str(base.D16.relative_to(base.ROOT)),fuente_control=str(base.D36.relative_to(base.ROOT)),
        fuente_validacion=str(pilot.OUT.relative_to(base.ROOT)),fuente_modelos_finales=str(OUT.relative_to(base.ROOT)),
        modelos_sha256=hashes,predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        archivos=[dict(score_columna='score_promedio5',archivo=str(target.relative_to(delivery)),contactos=len(selected),sha256=base.sha(target))],
        cambios_vs36=changes,validacion_local=local,verificacion_features=audit,checks=checks,
        matriz_train_sha256=final.matrix_sha(xt),matriz_agosto_sha256=final.matrix_sha(xv),
        excepcion_promocion_autorizada=True,supera_puerta_local_estricta=False,
        nuevos_fits_lightgbm=5,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False,
        etiquetas_entrenamiento=[202104,202105],etiquetas_auxiliares_extraidas=False,
        limitacion='Prueba exploratoria autorizada; mejora promedio local mínima, media entre semillas empeora. Junio no evaluado. Ganancia agosto desconocida.')
    base.save(delivery/'manifest.json',manifest)
    subprocess.run([sys.executable,str(base.TP/'105_reproducir_csv_entrega.py'),'--entrega',str(delivery),
        '--salida',str(OUT/'reproduccion_csv')],check=True)
    saved=pd.read_csv(delivery/'predicciones_agosto.csv',float_precision='round_trip')
    score=saved[[f'p_lgb_seed{s}' for s in seeds]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
    np.testing.assert_allclose(score,saved.score_promedio5,rtol=0,atol=1e-15)
    assert np.array_equal(score>.0275,saved.score_promedio5.to_numpy()>.0275)
    verification=dict(estado='verificado',entrega=number,contactos=len(selected),
        modelos_recargados=True,control36_reproducido=True,csv_reproducido_hash_identico=True,
        mezcla_reconstruida_por_producto_matricial=True,cambios_vs36=changes,api=False,creditos=0)
    base.save(delivery/'verificacion_independiente.json',verification)
    manifest['estado']='completo_verificado_preparado_pendiente';base.save(delivery/'manifest.json',manifest)
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envío manual al Bot, un CSV. Resultado público desconocido.\n',encoding='utf-8')
    text=f"# Entrega{number}: servicios193, submit exploratorio\n\nLightGBM193 abril+mayo→agosto,cinco semillas,273árboles. Cuatro señales de débitos/pagos añadidas; TabPFN202 de16 guardado. Promedio5,50/50,corte>2,75%;{len(selected)}clientes en una sola lista. Sin cambios de pesos/target/corte/ventana ni nueva API.\n\nMayo: control total$275.385.000/25%$68.846.250; candidato total$275.522.500/25%$68.880.625; delta total+$137.500/25%+$34.375. Media de listas individuales pierde$7.018.000,mejora1/5semillas. No pasa puerta estricta; usuario autoriza un submit exploratorio el10/10. No presentar como mejora demostrada. Junio no evaluado y mayo reutilizado.\n\nFrente a36 en agosto: {changes['agregados']}clientes agregados,{changes['retirados']}retirados,{changes['comunes']}comunes. Esto no permite conocer TP/FP ni ganancia de agosto. Referencia36 pública$98.175.000 conservada.\n\nComando:`submit {name}`. Adjuntar exclusivamente `{target.name}` de `adjuntos/`,sin encabezado ni índice. No enviado automáticamente.\n\nCinco fits finales nuevos,cero fitsTab/ceroAPI/créditos. Modelos recargados,control36 reproducido,features calendario reconstruidas por lookup,mezcla verificada y CSV reproducido con hash idéntico. Código archivado con firmas; modelos finales en `{str(OUT.relative_to(base.ROOT))}/modelos`.\n"
    (delivery/'INFORME.md').write_text(text,encoding='utf-8');(OUT/'MINI_INFORME.md').write_text(text,encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    for p,h in signature['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    for p,h in hashes.items():assert base.sha(base.ROOT/p)==h
    base.save(OUT/'estado.json',dict(estado='completo_verificado_entrega_preparada',entrega=number,carpeta=str(delivery.relative_to(base.ROOT)),api=False,creditos=0))
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Submit exploratorio autorizado — 2026-10-10\n\n'+text+'\n')
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(dict(entrega=number,carpeta=str(delivery.relative_to(base.ROOT)),csv=str(target.relative_to(base.ROOT)),comando='submit '+name,cambios_vs36=changes),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
