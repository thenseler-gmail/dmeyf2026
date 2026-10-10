"""Historicas +/- interrupcion de haberes, nuevas particiones y tres semillas.

Parametros congelados; CV retrospectivo por cliente abril/mayo y dos controles.
Prepara candidato BAJA+2 con20 semillas mayo/junio -> agosto; nunca envia al Bot.
"""
import argparse
import hashlib
import importlib
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
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas
from features_abandono import FUENTES, agregar_abandono

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT/'tp_primera_entrega/salidas'
KEYS = ['numero_de_cliente', 'foto_mes']
FEATURE = 'abandono_pasa_a_cero_mpayroll'
metricas = importlib.import_module('30_validacion_lightgbm').medir


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guardar(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def cargar_desarrollo(config):
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos = con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    assert not datos.duplicated(KEYS).any()
    assert datos.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    originales = [c for c in datos if c not in KEYS+['clase_ternaria']]
    historia = agregar_historicas_ampliadas(datos[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    nuevas = [c for c in historia if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    extras = agregar_abandono(datos[KEYS+FUENTES])
    datos = datos.merge(historia[KEYS+nuevas], on=KEYS, validate='one_to_one', sort=False)
    datos = datos.merge(extras[KEYS+[FEATURE]], on=KEYS, validate='one_to_one', sort=False)
    assert len(originales)==152 and len(nuevas)==50
    return datos, originales+nuevas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reanudar', type=Path)
    parser.add_argument('--solo-validacion', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    protocolo = json.loads((ROOT/'tp_primera_entrega/config_validacion_lightgbm.json').read_text(encoding='utf-8'))
    assert protocolo['umbral']==.025 and protocolo['cv_desarrollo']['folds']==4
    assert protocolo['cv_desarrollo']['meses_evaluados']==[202104,202105]
    refdir = SAL/'validacion_lgbm_20261005_190758'
    refcv = json.loads((refdir/'manifest.json').read_text())
    assert json.loads((refdir/'verificacion.json').read_text())['estado']=='verificado'
    for name,h in refcv['archivos_sha256'].items():
        assert sha(refdir/name)==h
    referencias={t:json.loads((SAL/'revision_umbral_20261005_131001'/t/'manifest.json').read_text()) for t in ['baja2','bajas']}
    semillas = referencias['bajas']['semillas'][:3]
    semillas_final = referencias['baja2']['semillas']
    assert semillas==referencias['baja2']['semillas'][:3] and len(semillas_final)==20
    datos, cols = cargar_desarrollo(config)
    assert cols==refcv['features']
    asignacion = pd.read_csv(refdir/'asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']].reset_index(drop=True),asignacion[KEYS+['clase_ternaria']])
    folds = asignacion.fold_cliente.to_numpy()
    assert datos.loc[datos.foto_mes.eq(202103),FEATURE].isna().all()
    assert datos[FEATURE].dropna().isin([0.,1.]).all()
    nombres=['haberes','historicas']
    columnas={'historicas':cols,'haberes':cols+[FEATURE]}
    x=preparar(datos,cols+[FEATURE])[0]
    versiones={p:importlib.metadata.version(p) for p in ['lightgbm','duckdb','numpy','pandas']}
    assert versiones==refcv['versiones']
    codigo={f:sha(Path(__file__).parent/f) for f in ['33_reentrenar_lightgbm_haberes.py','features.py','features_abandono.py','baseline.py','30_validacion_lightgbm.py']}
    firma=dict(codigo=codigo,versiones=versiones,referencias={t:r['elegido'] for t,r in referencias.items()},
        semillas=semillas,semillas_final=semillas_final,features=columnas,protocolo_sha256=sha(ROOT/'tp_primera_entrega/config_validacion_lightgbm.json'))
    out = args.reanudar or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('lgbm_haberes_particiones_%Y%m%d_%H%M%S')
    out.mkdir(parents=True,exist_ok=bool(args.reanudar))
    if args.reanudar:
        manifest=json.loads((out/'manifest.json').read_text())
        assert manifest['firma']==firma,'Cambio de codigo/configuracion/versiones'
    else:
        manifest=dict(estado='ejecutando_validacion',firma=firma,fuente_particiones=str(refdir),umbral=.025,operador='>',
            target_principal='baja2',feature_nueva=FEATURE,cv_meses=[202104,202105],folds=4,
            final=dict(target='baja2',variante='haberes',train=[202105,202106],eval=202108,semillas=semillas_final),
            api=False,creditos=0,seleccion_automatica=False,
            limitaciones='CV retrospectivo, etiquetas de otros clientes del mismo mes. Parametros antes elegidos en mayo reutilizado. Marzo sin febrero ni feature de haberes observable. Agregar columna cambia tambien muestreo de variables, no atribuir diferencia exclusivamente a su significado. Junio no usado para seleccion. Candidato solicitado BAJA+2/haberes, no garantia del publico.',
            resultados=[],auditoria_folds=[],entrenamientos_nuevos=0)
    cache=out/'cache_predicciones'; cache.mkdir(exist_ok=True)
    def save():
        guardar(out/'manifest.json',manifest)
    save()
    asignacion.to_csv(out/'asignacion_folds.csv',index=False)
    datos[KEYS+['clase_ternaria',FEATURE]].to_csv(out/'feature_desarrollo.csv',index=False)
    print('Salida:',out,flush=True)
    resultados=[]; individuales=[]; detalles=[]; auditoria=[]
    def predecir(variante,target,etapa,seed,it,iv,p_ref=None):
        nombre=f'{variante}_{target}_{etapa}_{seed}'
        fichero=cache/(nombre+'.npy')
        if fichero.exists():
            p=np.load(fichero,allow_pickle=False)
        elif p_ref is not None:
            p=np.asarray(p_ref,dtype=float)
            np.save(fichero,p,allow_pickle=False)
        else:
            spec=referencias[target]['elegido']
            y=(datos.clase_ternaria.eq('BAJA+2') if target=='baja2' else datos.clase_ternaria.isin(['BAJA+1','BAJA+2'])).astype(int).to_numpy()
            model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it][columnas[variante]],label=y[it]),num_boost_round=spec['num_boost_round'])
            p=model.predict(x.iloc[iv][columnas[variante]])
            np.save(fichero,p,allow_pickle=False)
            manifest['entrenamientos_nuevos']+=1
            save()
        assert len(p)==len(iv) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        return p
    for variante in nombres:
        for target in ['baja2','bajas']:
            for mes in [202104,202105]:
                ivmes=np.flatnonzero(datos.foto_mes.to_numpy()==mes)
                probs=np.full((len(datos),3),np.nan)
                anterior=pd.read_csv(refdir/f'cv_{target}_{mes}.csv') if variante=='historicas' else None
                if anterior is not None:
                    pd.testing.assert_frame_equal(datos.iloc[ivmes][KEYS+['clase_ternaria']].reset_index(drop=True),anterior[KEYS+['clase_ternaria']])
                    assert np.array_equal(folds[ivmes],anterior.fold_cliente.to_numpy())
                for fold in range(4):
                    it=np.flatnonzero((datos.foto_mes.to_numpy()<=mes)&(folds!=fold))
                    iv=np.flatnonzero((datos.foto_mes.to_numpy()==mes)&(folds==fold))
                    assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
                    assert datos.foto_mes.iloc[it].max()<=mes
                    auditoria.append(dict(variante=variante,target=target,mes=mes,fold=fold,max_mes_train=int(datos.foto_mes.iloc[it].max()),filas_train=len(it),filas_eval=len(iv),clientes_solapados=0))
                    for j,seed in enumerate(semillas):
                        p_ref=anterior.loc[anterior.fold_cliente.eq(fold),f'p_seed{seed}'].to_numpy() if anterior is not None and seed==semillas[0] else None
                        probs[iv,j]=predecir(variante,target,f'cv_{mes}_{fold}',seed,it,iv,p_ref)
                    met=metricas(datos.iloc[iv],probs[iv].mean(axis=1))
                    fraction=len(iv)/len(ivmes)
                    detalles.append(dict(variante=variante,target=target,mes=mes,fold=fold,fraccion=fraction,**met,
                        ganancia_equivalente_mes=met['ganancia']/fraction,ganancia_equivalente_mes_25pct=met['ganancia']/fraction/4))
                    print(variante,target,mes,'fold',fold+1,'/4 completo',flush=True)
                pred=datos.iloc[ivmes][KEYS+['clase_ternaria']].copy()
                pred['fold_cliente']=folds[ivmes]
                for j,seed in enumerate(semillas):
                    pred[f'p_seed{seed}']=probs[ivmes,j]
                    individuales.append(dict(variante=variante,target=target,etapa='cv_cliente',mes=mes,seed=seed,**metricas(pred,probs[ivmes,j])))
                pred['probabilidad']=probs[ivmes].mean(axis=1)
                pred.to_csv(out/f'{variante}_cv_{target}_{mes}.csv',index=False)
                resultados.append(dict(variante=variante,target=target,etapa='cv_cliente',mes=mes,**metricas(pred,pred.probabilidad)))
                manifest.update(resultados=resultados,auditoria_folds=auditoria)
                save()
                pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
                pd.DataFrame(detalles).to_csv(out/'detalle_folds.csv',index=False)
            for etapa,train in [('temporal_2meses',[202103]),('retrospectivo_1mes',[202104])]:
                it=np.flatnonzero(datos.foto_mes.isin(train).to_numpy()); iv=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy())
                anterior=pd.read_csv(refdir/f'{etapa}_{target}.csv') if variante=='historicas' else None
                if anterior is not None:
                    pd.testing.assert_frame_equal(datos.iloc[iv][KEYS+['clase_ternaria']].reset_index(drop=True),anterior[KEYS+['clase_ternaria']])
                pred=datos.iloc[iv][KEYS+['clase_ternaria']].copy()
                for seed in semillas:
                    p_ref=anterior[f'p_seed{seed}'].to_numpy() if anterior is not None and seed==semillas[0] else None
                    p=predecir(variante,target,etapa,seed,it,iv,p_ref)
                    pred[f'p_seed{seed}']=p
                    individuales.append(dict(variante=variante,target=target,etapa=etapa,mes=202105,seed=seed,**metricas(pred,p)))
                pred['probabilidad']=pred.filter(like='p_seed').mean(axis=1)
                pred.to_csv(out/f'{variante}_{etapa}_{target}.csv',index=False)
                resultados.append(dict(variante=variante,target=target,etapa=etapa,mes=202105,**metricas(pred,pred.probabilidad)))
                print(variante,target,etapa,resultados[-1],flush=True)
    pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
    pd.DataFrame(individuales).to_csv(out/'resultados_semillas.csv',index=False)
    pd.DataFrame(detalles).to_csv(out/'detalle_folds.csv',index=False)
    manifest.update(estado='validacion_completa',resultados=resultados,auditoria_folds=auditoria)
    save()
    print(pd.DataFrame(resultados).to_string(index=False),flush=True)
    if not args.solo_validacion:
        # Junio entra solo ahora: etiquetas de entrenamiento final, sin ganancia de seleccion.
        with duckdb.connect() as con:
            con.execute('SET threads=2')
            con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
            actuales=con.sql('SELECT * FROM datos WHERE foto_mes IN (202105,202106,202108) ORDER BY foto_mes,numero_de_cliente').df()
            fuentes=list(dict.fromkeys(HISTORICAS+HISTORICAS_EXTRA+FUENTES))
            hist=con.sql('SELECT numero_de_cliente,foto_mes,'+','.join(fuentes)+' FROM datos ORDER BY foto_mes,numero_de_cliente').df()
        h=agregar_historicas_ampliadas(hist[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
        a=agregar_abandono(hist[KEYS+FUENTES])
        actuales=actuales.merge(h[KEYS+[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]],on=KEYS,validate='one_to_one',sort=False)
        actuales=actuales.merge(a[KEYS+[FEATURE]],on=KEYS,validate='one_to_one',sort=False)
        train=actuales.loc[actuales.foto_mes.isin([202105,202106])].reset_index(drop=True)
        agosto=actuales.loc[actuales.foto_mes.eq(202108)].reset_index(drop=True)
        assert len(train)==327882 and len(agosto)==164647
        assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
        xt=preparar(train,columnas['haberes'])[0]; xp=preparar(agosto,columnas['haberes'])[0]
        y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
        nombre=manifest.get('nombre_candidato') or datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('LightGBMHaberesBaja2_%Y%m%d_%H%M%S')
        candidato=SAL/'candidatos_pendientes'/nombre
        candidato.mkdir(parents=True,exist_ok=True)
        modelos=candidato/'modelos'; modelos.mkdir(exist_ok=True)
        manifest.update(estado='entrenando_final',nombre_candidato=nombre,carpeta_candidato=str(candidato))
        save()
        pred=agosto[KEYS].copy()
        spec=referencias['baja2']['elegido']
        for seed in semillas_final:
            archivo_cache=cache/f'final_baja2_haberes_{seed}.npy'
            modelo_path=modelos/f'seed{seed}.txt'
            if archivo_cache.exists() and modelo_path.exists():
                p=np.load(archivo_cache,allow_pickle=False)
            else:
                model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=spec['num_boost_round'])
                p=model.predict(xp)
                model.save_model(str(modelo_path))
                np.save(archivo_cache,p,allow_pickle=False)
                manifest['entrenamientos_nuevos']+=1
            assert len(p)==len(agosto) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
            pred[f'p_seed{seed}']=p
            pred.to_csv(candidato/'predicciones_agosto.csv',index=False)
            save()
            print('Final agosto semilla',seed,'completa',flush=True)
        pred['probabilidad']=pred.filter(like='p_seed').mean(axis=1)
        pred.to_csv(candidato/'predicciones_agosto.csv',index=False)
        seleccion=pred.loc[pred.probabilidad>.025].sort_values(['probabilidad','numero_de_cliente'],ascending=[False,True])
        archivo=candidato/(nombre+'.csv')
        archivo.write_text(''.join(f'{int(i)}\n' for i in seleccion.numero_de_cliente),encoding='ascii')
        assert len(seleccion)==seleccion.numero_de_cliente.nunique()
        assert set(map(int,archivo.read_text().splitlines()))==set(seleccion.numero_de_cliente)
        (candidato/'MENSAJE_ZULIP.txt').write_text('submit '+nombre,encoding='ascii')
        cm=dict(estado='completo',submit=nombre,archivo_submit=archivo.name,archivo_sha256=sha(archivo),
            target='baja2',feature_nueva=FEATURE,features=columnas['haberes'],elegido=spec,semillas=semillas_final,
            train=[202105,202106],filas_train=len(train),futuro=202108,filas_agosto=len(agosto),contactos=len(seleccion),
            umbral=.025,operador='>',fuente_validacion=str(out),versiones=versiones,codigo_sha256=codigo,
            api=False,creditos=0,tabpfn=False,ganancia_agosto='desconocida',
            notas='Candidato solicitado historicas+haberes y target principal BAJA+2; no seleccionado automaticamente por ganancias. Sin envio al Bot.')
        guardar(candidato/'manifest.json',cm)
        manifest['candidato']=cm
        print('Candidato:',candidato,'Contactos:',len(seleccion),flush=True)
    manifest['estado']='completo'
    manifest['archivos_sha256']={p.name:sha(p) for p in out.glob('*.csv')}
    save()
    print('COMPLETO:',out,flush=True)


if __name__=='__main__':
    main()
