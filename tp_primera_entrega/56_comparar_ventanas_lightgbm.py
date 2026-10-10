"""Compara ventanas finales congeladas; junio solo train, sin API ni Bot."""
import argparse
import hashlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
BOT=SAL/'01_entregas_bot'
KEYS=['numero_de_cliente','foto_mes']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,m):p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def create(label):
    stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    number=max(int(p.name.split('_')[0]) for p in BOT.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
    name=label+'_'+stamp;out=BOT/f'{number}_{name}';out.mkdir()
    return out,name,number

def export(out,m,p):
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any()
    adj=out/'adjuntos_semillas';adj.mkdir(exist_ok=True);files=[]
    for s in m['semillas']:
        prob=p[f'p_seed{s}'];assert np.isfinite(prob).all() and prob.between(0,1).all()
        df=p.loc[prob>.025,KEYS].copy();df['prob']=prob[prob>.025]
        df=df.sort_values(['prob','numero_de_cliente'],ascending=[False,True])
        file=adj/f'{m["submit"]}_semillas_seed{s}.csv'
        file.write_text(''.join(f'{int(i)}\n' for i in df.numero_de_cliente),encoding='ascii')
        ids=pd.read_csv(file,header=None)[0].to_numpy()
        np.testing.assert_array_equal(ids,df.numero_de_cliente.to_numpy())
        assert len(ids)==len(set(ids))
        files.append(dict(seed=s,archivo=str(file.relative_to(out)),contactos=len(ids),sha256=sha(file)))
    p.to_csv(out/'predicciones_agosto.csv',index=False)
    m.update(archivos=files,predicciones_sha256=sha(out/'predicciones_agosto.csv'),estado='verificado_preparado')
    save(out/'manifest.json',m)
    cmd='submit '+m['submit']+'_semillas'
    (out/'MENSAJE_SEMILLAS.txt').write_text(cmd+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PENDIENTE envio manual. Cinco CSV de adjuntos_semillas.\n'+cmd+'\n',encoding='utf-8')
    (out/'PARA_ENVIAR_BOT.txt').write_text('Adjuntar los cinco CSV solo de esta carpeta.\n'+cmd+'\n',encoding='utf-8')
    save(out/'verificacion.json',dict(estado='verificado',adjuntos=5,umbral=.025,operador='>',
         modelos_reproducidos=m.get('modelos_reproducidos',0),fuente_predicciones_verificada=m.get('fuente_predicciones_verificada',False)))
    (out/'INFORME.md').write_text('# LightGBM: ventana '+str(m['train_final'])+'\n\nCinco semillas fijas, target BAJA+1/BAJA+2, 202 variables, trial6/273rondas. Corte estrictamente >2,5%. Solo cambia la ventana de etiquetas de entrenamiento. Junio nunca se evalua ni elige parametros; historia auxiliar anterior preservada.\n\n'+m['limitaciones']+'\n\n'+cmd+'\n',encoding='utf-8')
    print('Preparado:',out,'contactos:',[f['contactos'] for f in files],flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    ref=BOT/'12_LightGBMAbrilMayo5_20261005_235459'
    r=json.loads((ref/'manifest.json').read_text(encoding='utf-8-sig'))
    cols=r['features_lightgbm'];seeds=r['semillas'];spec=r['elegido']
    assert len(cols)==202 and spec['target']=='bajas' and spec['num_boost_round']==273
    common=dict(modelo='LightGBM solo',features_lightgbm=cols,semillas=seeds,elegido=spec,
        target_lightgbm='BAJA+1/BAJA+2',umbral=.025,operador='>',futuro=202108,api=False,creditos=0,
        enviado=False,estado_envio='pendiente_envio_manual',resultados_bot={},
        referencia_abril_mayo=str(ref.relative_to(ROOT)),
        referencia_publica_abril_mayo=dict(mean=91.6905,std_dev=2.1),
        limitaciones='Ganancia agosto desconocida. Solo tres ventanas predefinidas; no optimizar contra el Bot ni seleccionar semillas por publico. Abril/mayo reutilizados y semillas previamente seleccionadas. No hay test temporal local completo sin junio. No mezclar con TabPFN de otra ventana.',
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['56_comparar_ventanas_lightgbm.py','features.py','baseline.py']},
        versiones={f:importlib.metadata.version(f) for f in ['numpy','pandas','lightgbm','duckdb']})
    if args.reanudar:
        plan=args.reanudar;study=json.loads((plan/'manifest.json').read_text())
        assert study['codigo_sha256']==common['codigo_sha256']
        oldout=ROOT/study['mayo_junio'];newout=ROOT/study['abril_mayo_junio']
    else:
        plan=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('ventanas_lightgbm_%Y%m%d_%H%M%S');plan.mkdir()
        oldout,oldname,oldnumber=create('LightGBMMayoJunio5')
        newout,newname,newnumber=create('LightGBMAbrilMayoJunio5')
        save(oldout/'manifest.json',dict(common,submit=oldname,numero_entrega=oldnumber,train_final=[202105,202106],nuevos_fits=0,estado='preparando'))
        save(newout/'manifest.json',dict(common,submit=newname,numero_entrega=newnumber,train_final=[202104,202105,202106],nuevos_fits=5,estado='preparando'))
        study=dict(estado='preparando',ventanas=[[202104,202105],[202105,202106],[202104,202105,202106]],
              abril_mayo=str(ref.relative_to(ROOT)),mayo_junio=str(oldout.relative_to(ROOT)),abril_mayo_junio=str(newout.relative_to(ROOT)),
              codigo_sha256=common['codigo_sha256'],api=False,creditos=0,validacion_junio=False)
        save(plan/'manifest.json',study)
    print('Estudio:',plan,flush=True)
    # Mayo/junio: reutilizar exactamente las probabilidades LightGBM de entrega7.
    src=BOT/'7_EnsembleCombinadoTabPFN5_20261005_210238'
    sm=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    assert sm['train_final']==[202105,202106] and sm['features_lightgbm']==cols and sm['elegido']==spec and sm['semillas']==seeds
    predfile=src/'predicciones_agosto.csv'
    assert sha(predfile)==sm['hashes_resultados']['predicciones_agosto.csv']
    old=pd.read_csv(predfile)[KEYS+[f'p_seed{s}' for s in seeds]]
    original=BOT/'3_EnsembleHist_20261005_131953/predicciones_agosto.csv'
    assert sha(original)==sm['fuentes'][str(original)]
    orig=pd.read_csv(original);pd.testing.assert_frame_equal(old[KEYS],orig[KEYS])
    for s in seeds:np.testing.assert_allclose(old[f'p_seed{s}'],orig[f'p_seed{s}'],rtol=0,atol=1e-15)
    om=json.loads((oldout/'manifest.json').read_text());om.update(fuente_predicciones=str(predfile.relative_to(ROOT)),fuente_sha256=sha(predfile),fuente_predicciones_verificada=True)
    export(oldout,om,old)
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria),CASE WHEN foto_mes IN (202104,202105,202106) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.isin([202104,202105,202106])].reset_index(drop=True)
    aug=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(aug)==164647 and aug.clase_ternaria.isna().all()
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(train,cols)[0];xp=preparar(aug,cols)[0];y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
    pd.testing.assert_frame_equal(old[KEYS],aug[KEYS])
    nm=json.loads((newout/'manifest.json').read_text());nm.update(filas_train=len(train),filas_agosto=len(aug),
        conteo_train_por_mes={str(k):int(v) for k,v in train.foto_mes.value_counts().items()},
        matriz_train_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        matriz_agosto_sha256=hashlib.sha256(xp.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        target_sha256=hashlib.sha256(y.to_numpy().tobytes()).hexdigest())
    save(newout/'manifest.json',nm)
    modeldir=newout/'modelos';modeldir.mkdir(exist_ok=True)
    pred=aug[KEYS].copy()
    for s in seeds:
        mp=modeldir/f'seed{s}.txt'
        if mp.exists():model=lgb.Booster(model_file=str(mp))
        else:
            model=lgb.train(dict(spec['params'],seed=s),lgb.Dataset(xt,label=y),num_boost_round=spec['num_boost_round'])
            model.save_model(str(mp))
        assert model.feature_name()==cols and model.num_trees()==273
        prob=model.predict(xp,validate_features=True)
        loaded=lgb.Booster(model_file=str(mp));np.testing.assert_allclose(loaded.predict(xp,validate_features=True),prob,rtol=0,atol=0)
        pred[f'p_seed{s}']=prob;pred.to_csv(newout/'predicciones_agosto.csv',index=False)
        print('Abril+mayo+junio semilla',s,'lista',flush=True)
    nm.update(modelos_sha256={p.name:sha(p) for p in modeldir.glob('*.txt')},modelos_reproducidos=5)
    export(newout,nm,pred)
    rows=[]
    for path in [ref,oldout,newout]:
        tm=json.loads((path/'manifest.json').read_text(encoding='utf-8-sig'))
        for f in tm['archivos']:
            rows.append(dict(entrega=tm['numero_entrega'],train='+'.join(str(i) for i in tm['train_final']),seed=f['seed'],contactos=f['contactos'],ganancia_publica_conocida=tm.get('resultados_bot',{}).get('semillas5',{}).get('public_gain_mean')))
    pd.DataFrame(rows).to_csv(plan/'comparacion_contactos.csv',index=False)
    study.update(estado='completo_verificado',nuevos_fits=5)
    save(plan/'manifest.json',study)
    (plan/'INFORME.md').write_text('# Comparacion de ventanas LightGBM\n\nTres ventanas predefinidas, mismos cinco seeds/202variables/targetcombinado/parametros273rondas/corte2.5%. Abril+mayo ya enviado: media publica $91.690.500/std$2.100.000, entrega12. Mayo+junio reutilizado de entrega7, nueva carpeta exclusiva LightGBM. Abril+mayo+junio entrenado con5fits. Ganancias nuevas desconocidas; junio nunca usado como validacion.\n\nUna carpeta por entrega. Enviar cinco archivos de cada carpeta en corridas separadas para comparar medias. No repetir entrega12.\n\n'+str(oldout)+'\n\n'+str(newout)+'\n',encoding='utf-8')
    print('COMPLETO:',plan,flush=True)

if __name__=='__main__':main()
