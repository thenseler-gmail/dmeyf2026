"""Control189 de cinco ensembles197 de45: mismos grupos, datos, params, Tab y corte.

Bot solo informa agregados: diferencia de medias es media de diferencias pareadas;
no permite reconstruir diferencias por grupo ni su desvio sin covarianza.
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
import numpy as np
import pandas as pd
from features_vinculos import FEATURES

base=importlib.import_module('116_promedio20_hist189')
final=importlib.import_module('66_preparar_entrega_hist189')
CANDIDATE=base.BOT/'45_EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912'
OUT=base.SAL/'control_pareado_vinculos_20261010'
KEYS=['numero_de_cliente','foto_mes']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=True)
    cand=read(CANDIDATE/'manifest.json');pub=read(CANDIDATE/'RESULTADO_BOT.json')
    r16=read(base.D16/'manifest.json');r36=read(base.D36/'manifest.json')
    groups=cand['grupos_semillas'];seeds=[s for i in range(1,6) for s in groups[str(i)]]
    cols=r16['firma']['features']
    assert cand['entrega']==45 and cand['enviado'] and pub['media_publica_pesos']==96838500
    assert len(set(seeds))==25 and seeds==cand['semillas']
    assert groups['1']==r16['firma']['seeds']
    assert cand['firma']['features']==cols+FEATURES and len(cols)==189
    assert cand['firma']['params']==r16['firma']['params'] and cand['firma']['rounds']==273
    assert cand['train_final']==[202104,202105] and cand['futuro']==202108
    assert cand['umbral']==.0275 and cand['pesos']==dict(lightgbm=.5,tabpfn=.5)
    assert base.sha(CANDIDATE/'predicciones_agosto.csv')==cand['predicciones_sha256']
    for e in cand['archivos']:assert base.sha(CANDIDATE/e['archivo'])==e['sha256']
    for p,h in cand['modelos_sha256'].items():assert base.sha(base.ROOT/p)==h
    paths=[CANDIDATE/'manifest.json',CANDIDATE/'predicciones_agosto.csv',CANDIDATE/'RESULTADO_BOT.json',
        CANDIDATE/'verificacion_independiente.json',base.D16/'manifest.json',base.D16/'predicciones_agosto.csv',
        base.D36/'manifest.json',base.D36/'predicciones_agosto.csv',base.D36/'RESULTADO_BOT.json',
        base.D36/r36['archivos'][0]['archivo']]
    signature=dict(train_final=[202104,202105],futuro=202108,features=cols,features_candidato=cols+FEATURES,
        unica_diferencia='Control sin las ocho features vinculos; mismos datos, params, semillas, target, pesos, corte y TabPFN',
        grupos_semillas=groups,semillas=seeds,params=cand['firma']['params'],rounds=273,
        pesos=cand['pesos'],umbral=.0275,operador='>',
        fuente_candidato=str(CANDIDATE.relative_to(base.ROOT)),fuente_entrega=str(base.D16.relative_to(base.ROOT)),
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in paths},
        codigo_sha256={f:base.sha(base.TP/f) for f in ['135_control_pareado_vinculos.py','116_promedio20_hist189.py',
            '66_preparar_entrega_hist189.py','features_vinculos.py','features.py','baseline.py',
            '104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb']},
        criterio_publico='Aporte promedio de ocho vinculos = media45 -mediaControl. Positivo favorece vinculos; negativo favorece control',
        restriccion_bot='Usuario confirma que Bot solo devuelve media y desvio. No diferencias por grupo ni desvio pareado disponibles',
        nuevos_fits_lightgbm=20,fits_lightgbm_reutilizados=5,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False,
        limitacion='Publico ya reutilizado, prueba exploratoria. Mismas semillas pero aleatoriedad interna puede cambiar '
            'al variar numero de features. No inferir significancia ni intervalo de confianza con desvios agregados.')
    if (OUT/'PLAN.json').exists():assert read(OUT/'PLAN.json')==signature
    else:base.save(OUT/'PLAN.json',signature)
    print('Comparacion congelada: control189 vs197, mismos cinco grupos',json.dumps(groups),flush=True)
    base.save(OUT/'estado.json',dict(estado='cargando_matrices_finales',api=False,creditos=0))
    _,_,fcols,_,fseeds,xt,xv,y,keys,_=final.cargar()
    assert fcols==cols and fseeds==groups['1']
    assert final.matrix_sha(xt)==r16['firma']['matriz_train_sha256']
    assert final.matrix_sha(xv)==r16['firma']['matriz_agosto_sha256']
    assert hashlib.sha256(y.tobytes()).hexdigest()==r16['firma']['target_train_sha256']
    cp=pd.read_csv(CANDIDATE/'predicciones_agosto.csv',float_precision='round_trip')
    old=pd.read_csv(base.D16/'predicciones_agosto.csv',float_precision='round_trip')
    control36=pd.read_csv(base.D36/'predicciones_agosto.csv',float_precision='round_trip')
    for p in [cp,old,control36]:pd.testing.assert_frame_equal(keys,p[KEYS])
    np.testing.assert_array_equal(cp.p_tabpfn,old.p_tabpfn)
    for i in range(1,6):
        q=cp[[f'p_lgb_seed{s}' for s in groups[str(i)]]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
        np.testing.assert_allclose(q,cp[f'score_ensemble{i}'],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(q>.0275,cp[f'score_ensemble{i}'].to_numpy()>.0275)
    expected={f'seed{s}.txt':r16['modelos_sha256'][f'seed{s}.txt'] for s in groups['1']}
    base.save(OUT/'estado.json',dict(estado='entrenando20_controles',api=False,creditos=0))
    values,hashes=base.run_models(xt,xv,y,seeds,signature['params'],OUT/'modelos',base.D16/'modelos',expected,'Control pareado189')
    np.testing.assert_allclose(values[:,:5],old[[f'p_lgb_seed{s}' for s in groups['1']]],rtol=0,atol=1e-15)
    pred=keys.copy();pred['p_tabpfn']=cp.p_tabpfn
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    for i in range(1,6):
        q=.5*values[:,(i-1)*5:i*5].mean(axis=1)+.5*cp.p_tabpfn
        if i==1:
            np.testing.assert_allclose(q,control36.score_promedio5,rtol=0,atol=1e-15)
            np.testing.assert_array_equal(q>.0275,control36.score_promedio5>.0275)
            q=control36.score_promedio5
        pred[f'score_ensemble{i}']=q
    if (OUT/'ENTREGA.json').exists():loc=read(OUT/'ENTREGA.json')
    else:
        number=max(int(p.name.split('_')[0]) for p in base.BOT.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
        stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
        name='ControlHist189CincoEnsemblesPareados45_'+stamp
        loc=dict(entrega=number,submit=name,carpeta=str((base.BOT/f'{number}_{name}').relative_to(base.ROOT)))
        base.save(OUT/'ENTREGA.json',loc)
    delivery=base.ROOT/loc['carpeta'];delivery.mkdir(exist_ok=True);(delivery/'adjuntos').mkdir(exist_ok=True)
    assert not (delivery/'RESULTADO_BOT.json').exists()
    if (delivery/'manifest.json').exists():assert not read(delivery/'manifest.json')['enviado']
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    entries=[];changes=[];pairs=[]
    for i in range(1,6):
        col=f'score_ensemble{i}'
        chosen=pred.loc[pred[col]>.0275].sort_values([col,'numero_de_cliente'],ascending=[False,True])
        path=delivery/'adjuntos'/f'{loc["submit"]}_ensemble{i}.csv'
        newline='\n'
        if i==1 and b'\r\n' in (base.D36/r36['archivos'][0]['archivo']).read_bytes():newline='\r\n'
        path.write_bytes(''.join(f'{int(cid)}{newline}' for cid in chosen.numero_de_cliente).encode('ascii'))
        if i==1:assert base.sha(path)==r36['archivos'][0]['sha256']
        ids=set(chosen.numero_de_cliente);other=set(cp.loc[cp[col]>.0275,'numero_de_cliente'])
        entries.append(dict(ensemble=i,semillas=groups[str(i)],score_columna=col,archivo=str(path.relative_to(delivery)),
                            contactos=len(ids),sha256=base.sha(path),equivalente_entrega36=(i==1)))
        changes.append(dict(ensemble=i,control_contactos=len(ids),candidato_contactos=len(other),
            comunes=len(ids&other),agregados_por_vinculos=len(other-ids),retirados_por_vinculos=len(ids-other)))
        pairs.append(dict(ensemble=i,semillas=','.join(map(str,groups[str(i)])),
            control_publico_conocido=98175000 if i==1 else None,candidato_publico_conocido=100815000 if i==1 else None,
            delta_vinculos_conocido=2640000 if i==1 else None))
    assert len(set(e['sha256'] for e in entries))==5
    pd.DataFrame(changes).to_csv(delivery/'comparacion_pareada_contactos.csv',index=False)
    pd.DataFrame(pairs).to_csv(delivery/'parejas_ganancia_conocida.csv',index=False)
    comparison=dict(candidato_entrega=45,candidato_media_publica_pesos=96838500,
        candidato_desvio_publico_pesos=2037600,control_entrega=loc['entrega'],control_media_publica_pesos=None,
        delta_promedio_vinculos_pesos=None,formula='96838500 - media_publica_control',
        grupo1_delta_conocido=2640000,resultados_individuales_bot_disponibles=False,
        desvio_diferencias_pareadas_calculable=False,
        explicacion='Diferencia de medias equivale al promedio de diferencias al usar mismos grupos. '
            'Desvio de diferencias requiere covarianza/datos por grupo; no restar desvios ni asumir independencia.')
    base.save(delivery/'COMPARACION_PUBLICA.json',comparison)
    meta=dict(**loc,estado='preparado_pendiente_verificacion',enviado=False,firma=signature,
        train_final=[202104,202105],futuro=202108,semillas=seeds,grupos_semillas=groups,
        features_lightgbm=189,features_tabpfn=202,target_lightgbm=r16['firma']['target'] if 'target' in r16['firma'] else 'BAJA+1/BAJA+2',
        target_tabpfn='BAJA+2',pesos=cand['pesos'],umbral=.0275,operador='>',
        agregacion='cinco_ensembles_cada_uno_promedia_cinco_probabilidades',
        fuente_entrega=str(base.D16.relative_to(base.ROOT)),fuente_candidato=str(CANDIDATE.relative_to(base.ROOT)),
        fuente_modelos_finales=str(OUT.relative_to(base.ROOT)),archivos=entries,
        modelos_sha256=hashes,predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        matriz_train_sha256=final.matrix_sha(xt),matriz_agosto_sha256=final.matrix_sha(xv),
        target_train_sha256=hashlib.sha256(y.tobytes()).hexdigest(),comparacion_pareada=changes,
        comparacion_publica=comparison,validacion_local_nuevos_grupos=False,
        nuevos_fits_lightgbm=20,fits_lightgbm_reutilizados=5,nuevos_fits_tabpfn=0,api=False,creditos=0,submit_automatico=False,
        etiquetas_entrenamiento=[202104,202105],etiquetas_auxiliares_extraidas=False,limitacion=signature['limitacion'])
    base.save(delivery/'manifest.json',meta)
    saved=pd.read_csv(delivery/'predicciones_agosto.csv',float_precision='round_trip')
    for e in entries:
        q=saved[[f'p_lgb_seed{s}' for s in e['semillas']]+['p_tabpfn']].to_numpy()@np.array([.1]*5+[.5])
        np.testing.assert_allclose(q,saved[e['score_columna']],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(q>.0275,saved[e['score_columna']].to_numpy()>.0275)
    subprocess.run([sys.executable,str(base.TP/'105_reproducir_csv_entrega.py'),'--entrega',str(delivery),
                    '--salida',str(OUT/'reproduccion_csv')],check=True)
    base.save(delivery/'verificacion_independiente.json',dict(estado='verificado',archivos=5,modelos_recargados=True,
        grupos_identicos_a45=True,tabpfn_identico_a45=True,parametros_identicos_a45=True,
        control189_matrices_identicas_a16=True,grupo1_csv_identico_a36=True,
        mezclas_reconstruidas_por_producto_matricial=True,csv_reproducidos_hash_identico=True,api=False,creditos=0))
    meta['estado']='completo_verificado_preparado_pendiente';base.save(delivery/'manifest.json',meta)
    base.save(OUT/'manifest.json',dict(estado='completo_verificado',firma=signature,modelos_sha256=hashes,
        entrega=loc['entrega'],fuente_entrega=str(base.D16.relative_to(base.ROOT)),fuente_candidato=str(CANDIDATE.relative_to(base.ROOT))))
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+loc['submit']+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envio manual de cinco controles juntos. Comparar media contra45 $96.838.500.\n',encoding='utf-8')
    note=f"# Entrega{loc['entrega']}: control pareado sin ocho vinculos\n\nControl de45: mismos cinco grupos de cinco semillas, abril+mayo->agosto, LightGBM189 sin ocho features vinculos frente a197 de45. Mismos params273arboles,target combinado, TabPFN202 identico, pesos50/50,corte>2,75%,promediar probabilidades antes del corte en cada grupo. Grupo1 reproduce36 exactamente ($98.175.000 conocido); candidato grupo1 reproduce43 ($100.815.000),delta+$2.640.000. Otros cuatro controles nuevos:20fitsLightGBM,5reutilizados,ceroAPI/creditos.\n\n```text\n"+pd.DataFrame(changes).to_string(index=False)+f"\n```\n\nAdjuntar los CINCO CSV de `adjuntos/` juntos con `submit {loc['submit']}`. Pendiente envio manual; no adjuntar predicciones_agosto.csv.\n\nMetrica primaria: **aporte promedio de vinculos = $96.838.500 (media45) menos media de esta entrega**. Positivo favorece197; negativo favorece189. Bot solo informa media/desvio, confirmado por usuario. Diferencia de medias es media de cinco diferencias pareadas, pero NO conocemos las diferencias individuales ni su desvio. No restar desvios ni calcular intervalo asumiendo independencia; depende de covarianza entre pares.\n\nGrupo1 previamente seleccionado por desempeno; otros cuatro grupos congelados sin elegir por score. Publico reutilizado, resultado exploratorio; no prueba independiente ni garantia privada. No nueva validacion local: control final de replicas publicas. Conservar43 como mejor publica, sin presentar $100.815.000 como rendimiento tipico.\n\nMatrices/target originales verificados, modelos recargados, TabPFN y grupos identicos a45,candidato45 reconstruido,mezclas verificadas por producto matricial y cinco CSV reproducidos con hashes identicos. Grupo1 payload identico a36; fuentes conservadas y codigo firmado archivado.\n"
    (delivery/'INFORME.md').write_text(note,encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    for p,h in signature['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    for p,h in hashes.items():assert base.sha(base.ROOT/p)==h
    result=dict(**loc,estado='completo_verificado_preparado_pendiente',archivos=entries,grupos_semillas=groups,
        comando='submit '+loc['submit'],comparacion_publica=comparison,nuevos_fits_lightgbm=20,api=False,creditos=0)
    base.save(OUT/'RESULTADO.json',result)
    base.save(OUT/'estado.json',dict(estado='completo_verificado_cinco_controles_preparados',entrega=loc['entrega'],api=False,creditos=0))
    summary=f"## Control pareado de vinculos preparado — 2026-10-10\n\nEntrega{loc['entrega']}: cinco ensembles sin las ocho features vinculos, mismos grupos y resto configuracion que45.20fitsLightGBM nuevos,5reutilizados,ceroAPI/creditos. Grupo1 CSV identico a36. Bot solo muestra resumen: comparar aporte promedio = $96.838.500 -mediaControl; no cambios individuales ni desvio pareado calculables. Pendiente envio manual de cinco CSV juntos con `submit {loc['submit']}` y resultado. [Informe]({delivery.relative_to(base.TP).as_posix()}/INFORME.md). Mejor publica43 preservada.\n"
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(summary+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+summary.replace('(salidas/','(tp_primera_entrega/salidas/')+'\n'+note)
    with (base.TP/'PLAN_EXPERIMENTOS_20261010.md').open('a',encoding='utf-8') as f:f.write('\n'+summary)
    cfgpath=base.TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    cfg['control_pareado_vinculos_entrega45']=result
    assert cfg['mejor_publico_registrado']['entrega']==43
    base.save(cfgpath,cfg)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
