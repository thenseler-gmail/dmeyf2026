"""Auditoria agregada de mayo y evaluacion local de un bloque predefinido.

Errores: modelos train abril, eval mayo. Comparacion de features: CV cliente
en mayo, pool abril/mayo excluyendo clientes de cada fold. No junio/API.
"""
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_trayectorias import FEATURES,FUENTES,KEYS,agregar_trayectorias

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
prep=importlib.import_module('33_reentrenar_lightgbm_haberes')
medir=importlib.import_module('30_validacion_lightgbm').medir


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,m):p.write_text(json.dumps(m,indent=2,ensure_ascii=False,default=str),encoding='utf-8')


def main():
    ref=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    m=json.loads((ref/'manifest.json').read_text());assert m['validacion_train']==[202104] and m['validacion_eval']==202105
    seeds=m['semillas'];spec=m['elegido'];cols=m['features_lightgbm']
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    datos,basecols=prep.cargar_desarrollo(config);assert basecols==cols and len(cols)==202
    nuevos=agregar_trayectorias(datos[KEYS+FUENTES])
    datos=datos.merge(nuevos,on=KEYS,validate='one_to_one',sort=False)
    pred=pd.read_csv(ref/'predicciones_mayo.csv')
    may=datos.loc[datos.foto_mes.eq(202105)].reset_index(drop=True)
    pd.testing.assert_frame_equal(may[KEYS+['clase_ternaria']],pred[KEYS+['clase_ternaria']])
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('auditoria_trayectorias_%Y%m%d_%H%M%S');out.mkdir()
    (out/'modelos').mkdir()
    meta=dict(estado='auditando',semillas=seeds,elegido=spec,features_control=cols,features_nuevas=FEATURES,
              fuente_errores=str(ref/'predicciones_mayo.csv'),fuente_sha256=sha(ref/'predicciones_mayo.csv'),
              umbral=.025,operador='>',target='BAJA+1/BAJA+2',api=False,creditos=0,
              auditoria='Mayo predicho sin entrenar con sus etiquetas, ambos modelos fit abril. Mayo previamente reutilizado.',
              comparacion='OOF mayo por cuatro grupos cliente, pool abril/mayo excluye todas filas del cliente del fold. Misma seed/params, p>.025. No es test temporal.',
              limitaciones='Features elegidas como bloque antes de observar auditoria; analisis y comparacion en mayo reutilizado, semillas seleccionadas abril/mayo. No prueba independiente. Caidas sostenidas desconocidas en abril; prueba temporal abril->mayo no puede aprenderlas.',
              codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['47_auditar_errores_trayectorias.py','features_trayectorias.py','features.py','baseline.py']})
    save(out/'manifest.json',meta);print('Salida:',out,flush=True)
    true=may.clase_ternaria.eq('BAJA+2');selected=pred.probabilidad>.025
    group=np.select([selected&true,selected&~true,~selected&true],['TP','FP','FN'],default='TN')
    may['grupo_error']=group;may['probabilidad']=pred.probabilidad
    counts=may.groupby(['grupo_error','clase_ternaria']).size().reset_index(name='clientes')
    counts.to_csv(out/'conteo_errores.csv',index=False)
    summary=[]
    for g,df in may.groupby('grupo_error'):
        for c in ['probabilidad','cliente_antiguedad','cliente_edad']+FEATURES+['mpayroll','ctrx_quarter','mcuentas_saldo','cproductos']:
            summary.append(dict(grupo=g,feature=c,filas=len(df),observados=int(df[c].notna().sum()),mediana=df[c].median(),media=df[c].mean()))
    pd.DataFrame(summary).to_csv(out/'perfil_grupos.csv',index=False)
    bins=[]
    for c in ['tray_canales_perdidos_1','tray_delta_canales_activos_1']+FEATURES[3:]:
        if 'ratio' in c:bucket=pd.cut(may[c],[-np.inf,.25,.5,.75,1,1.25,np.inf]).astype(str)
        else:bucket=may[c].astype(str)
        temp=pd.DataFrame(dict(bin=bucket,y=true.astype(int),seleccionado=selected.astype(int),fn=(true&~selected).astype(int)))
        b=temp.groupby('bin').agg(clientes=('y','size'),baja2=('y','sum'),contactados=('seleccionado','sum'),falsos_negativos=('fn','sum')).reset_index()
        b['feature']=c;b['tasa_baja2']=b.baja2/b.clientes;bins.append(b)
    pd.concat(bins,ignore_index=True).to_csv(out/'tasas_por_senal.csv',index=False)
    coverage=datos.groupby('foto_mes')[FEATURES].agg(lambda s:s.notna().mean()).reset_index()
    coverage.to_csv(out/'cobertura_features.csv',index=False)
    meta.update(estado='comparando',errores_ensemble=medir(pred,pred.probabilidad));save(out/'manifest.json',meta)
    groups=pd.read_csv(SAL/'top5_semillas_20261005_194616/asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']],groups[KEYS+['clase_ternaria']])
    folds=groups.fold_cliente.to_numpy();groups.to_csv(out/'asignacion_folds.csv',index=False)
    x=preparar(datos,cols+FEATURES)[0]
    y=datos.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    ivmes=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy());results=[];individual=[];audit=[]
    for variant,columns in [('control',cols),('trayectorias',cols+FEATURES)]:
        table=datos.iloc[ivmes][KEYS+['clase_ternaria']].reset_index(drop=True)
        for seed in seeds:
            prob=np.full(len(datos),np.nan)
            for fold in range(4):
                it=np.flatnonzero(datos.foto_mes.isin([202104,202105]).to_numpy()&(folds!=fold))
                iv=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy()&(folds==fold))
                assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
                model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it][columns],label=y[it]),num_boost_round=spec['num_boost_round'])
                model.save_model(str(out/'modelos'/f'{variant}_{seed}_{fold}.txt'))
                prob[iv]=model.predict(x.iloc[iv][columns],validate_features=True)
                audit.append(dict(variante=variant,seed=seed,fold=fold,filas_train=len(it),filas_eval=len(iv),meses_train=[202104,202105]))
            table[f'p_seed{seed}']=prob[ivmes]
            individual.append(dict(variante=variant,seed=seed,**medir(table,prob[ivmes])))
            print(variant,'semilla',seed,'completa',flush=True)
        table['probabilidad']=table[[f'p_seed{s}' for s in seeds]].mean(axis=1)
        table.to_csv(out/f'oof_{variant}_mayo.csv',index=False)
        results.append(dict(variante=variant,features=len(columns),**medir(table,table.probabilidad)))
        pd.DataFrame(results).to_csv(out/'comparacion.csv',index=False)
        pd.DataFrame(individual).to_csv(out/'resultados_semillas.csv',index=False)
    save(out/'auditoria_fits.json',audit)
    meta.update(estado='completo',comparacion=resultados if False else results,entrenamientos_nuevos=40,
                archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    save(out/'manifest.json',meta)
    print('ERRORES:',counts.to_string(index=False),flush=True)
    print('COMPARACION:',results,flush=True)


if __name__=='__main__':main()
