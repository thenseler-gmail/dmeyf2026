"""Selecciona5 de20 semillas por ganancia media OOF abril/mayo, no por agosto."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
KEYS=['numero_de_cliente','foto_mes']
prep=importlib.import_module('33_reentrenar_lightgbm_haberes')
medir=importlib.import_module('30_validacion_lightgbm').medir


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def guardar(p,m):
    p.write_text(json.dumps(m,indent=2,ensure_ascii=False,default=str),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reanudar',type=Path)
    args=parser.parse_args()
    fuente=SAL/'lgbm_haberes_particiones_20261005_191807'
    m=json.loads((fuente/'manifest.json').read_text())
    assert json.loads((fuente/'verificacion.json').read_text())['estado']=='verificado'
    for f,h in m['firma']['codigo'].items():
        assert sha(Path(__file__).parent/f)==h,f
    for f,h in m['archivos_sha256'].items():
        assert sha(fuente/f)==h,f
    for p,v in m['firma']['versiones'].items():
        assert importlib.metadata.version(p)==v,p
    candidato=Path(m['carpeta_candidato'])
    cm=json.loads((candidato/'manifest.json').read_text())
    semillas=cm['semillas']; spec=cm['elegido']; cols=cm['features']
    assert len(semillas)==20 and cm['target']=='baja2' and len(cols)==203
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    datos,basecols=prep.cargar_desarrollo(config)
    assert cols==basecols+['abandono_pasa_a_cero_mpayroll']
    grupos=pd.read_csv(fuente/'asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']].reset_index(drop=True),grupos[KEYS+['clase_ternaria']])
    x=preparar(datos,cols)[0]; y=datos.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    folds=grupos.fold_cliente.to_numpy()
    out=args.reanudar or SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('top5_semillas_%Y%m%d_%H%M%S')
    out.mkdir(parents=True,exist_ok=bool(args.reanudar))
    firma=dict(codigo_sha256=sha(Path(__file__)),fuente_manifest_sha256=sha(fuente/'manifest.json'),
        semillas=semillas,features=cols,elegido=spec,versiones=m['firma']['versiones'])
    if args.reanudar:
        meta=json.loads((out/'manifest.json').read_text())
        assert meta['firma']==firma
    else:
        meta=dict(estado='evaluando',firma=firma,fuente=str(fuente),candidato=str(candidato),
            criterio='Media simple 50/50 de ganancias OOF completas abril y mayo, p>0.025. Desempate por ganancia mayo y luego seed ascendente.',
            meses=[202104,202105],folds=4,umbral=.025,operador='>',target='baja2',
            semillas_previamente_evaluadas=m['firma']['semillas'],entrenamientos_nuevos=0,
            api=False,creditos=0,limitaciones='CV retrospectivo, meses reutilizados; seleccion entre20 semillas optimista. Agosto sin etiquetas: solo se extraen predicciones finales ya guardadas. No prueba superioridad privada.')
    guardar(out/'manifest.json',meta)
    cache=out/'cache'; cache.mkdir(exist_ok=True)
    grupos.to_csv(out/'asignacion_folds.csv',index=False)
    anteriores={mes:pd.read_csv(fuente/f'haberes_cv_baja2_{mes}.csv') for mes in [202104,202105]}
    matrices={mes:datos.loc[datos.foto_mes.eq(mes),KEYS+['clase_ternaria']].reset_index(drop=True) for mes in [202104,202105]}
    for mes,df in matrices.items():
        df['fold_cliente']=folds[datos.foto_mes.eq(mes).to_numpy()]
        pd.testing.assert_frame_equal(df,anteriores[mes][df.columns])
    resultados=[]; audit=[]
    print('Salida:',out,flush=True)
    for n,seed in enumerate(semillas,1):
        for mes in [202104,202105]:
            ivmes=np.flatnonzero(datos.foto_mes.eq(mes).to_numpy())
            prob=np.full(len(datos),np.nan)
            for fold in range(4):
                it=np.flatnonzero((datos.foto_mes.to_numpy()<=mes)&(folds!=fold))
                iv=np.flatnonzero((datos.foto_mes.to_numpy()==mes)&(folds==fold))
                assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
                assert datos.foto_mes.iloc[it].max()<=mes
                audit.append(dict(seed=seed,mes=mes,fold=fold,filas_fit=len(it),filas_eval=len(iv),max_mes_fit=int(datos.foto_mes.iloc[it].max()),clientes_solapados=0))
                cp=cache/f'{mes}_{fold}_{seed}.npy'
                if cp.exists():
                    p=np.load(cp,allow_pickle=False)
                elif seed in m['firma']['semillas']:
                    p=anteriores[mes].loc[anteriores[mes].fold_cliente.eq(fold),f'p_seed{seed}'].to_numpy()
                    np.save(cp,p,allow_pickle=False)
                else:
                    model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it],label=y[it]),num_boost_round=spec['num_boost_round'])
                    p=model.predict(x.iloc[iv])
                    np.save(cp,p,allow_pickle=False)
                    meta['entrenamientos_nuevos']+=1
                    guardar(out/'manifest.json',meta)
                assert len(p)==len(iv) and np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
                prob[iv]=p
            matrices[mes][f'p_seed{seed}']=prob[ivmes]
            matrices[mes].to_csv(out/f'oof_{mes}.csv',index=False)
            resultados.append(dict(seed=seed,mes=mes,**medir(matrices[mes],prob[ivmes])))
        pd.DataFrame(resultados).to_csv(out/'resultados_por_mes.csv',index=False)
        meta.update(semillas_completas=n,auditoria_folds=audit)
        guardar(out/'manifest.json',meta)
        print('Semilla',n,'/20',seed,'evaluada abril/mayo',flush=True)
    tabla=pd.DataFrame(resultados)
    ranking=tabla.pivot(index='seed',columns='mes',values='ganancia').rename(columns={202104:'ganancia_abril',202105:'ganancia_mayo'})
    ranking['ganancia_media']=ranking.mean(axis=1)
    for c in ['ganancia_abril','ganancia_mayo','ganancia_media']:
        ranking[c+'_25pct']=ranking[c]/4
    ranking=ranking.reset_index().sort_values(['ganancia_media','ganancia_mayo','seed'],ascending=[False,False,True]).reset_index(drop=True)
    ranking.insert(0,'puesto',np.arange(1,21))
    ranking.to_csv(out/'ranking_semillas.csv',index=False)
    elegidas=ranking.head(5).seed.astype(int).tolist()
    # Solo exportacion de las predicciones finales ya existentes; no se consultan etiquetas agosto.
    agosto=pd.read_csv(candidato/'predicciones_agosto.csv')
    assert len(agosto)==164647 and agosto.foto_mes.eq(202108).all() and not agosto.numero_de_cliente.duplicated().any()
    adj=candidato/'adjuntos_top5'; adj.mkdir(exist_ok=True)
    submit='LightGBMHaberesBaja2Top5_20261005_192751'
    archivos=[]
    for puesto,seed in enumerate(elegidas,1):
        col=f'p_seed{seed}'
        sel=agosto.loc[agosto[col]>.025].sort_values([col,'numero_de_cliente'],ascending=[False,True])
        archivo=adj/f'{submit}_seed{seed}.csv'
        archivo.write_text(''.join(f'{int(i)}\n' for i in sel.numero_de_cliente),encoding='ascii')
        ids=list(map(int,archivo.read_text().splitlines()))
        assert len(ids)==len(set(ids))==len(sel) and set(ids)==set(sel.numero_de_cliente)
        archivos.append(dict(puesto=puesto,seed=seed,archivo=archivo.name,sha256=sha(archivo),contactos=len(ids)))
    assert set(p.name for p in adj.glob('*.csv'))==set(a['archivo'] for a in archivos)
    (candidato/'MENSAJE_TOP5.txt').write_text('submit '+submit,encoding='ascii')
    ranking.head(5).to_csv(candidato/'ranking_top5.csv',index=False)
    tm=dict(estado='preparado_pendiente',submit=submit,semillas=elegidas,criterio=meta['criterio'],
        fuente_ranking=str(out),fuente_probabilidades_sha256=sha(candidato/'predicciones_agosto.csv'),
        umbral=.025,operador='>',archivos=archivos,api=False,creditos=0,enviado=False)
    guardar(candidato/'manifest_top5.json',tm)
    (candidato/'ESTADO_ENVIO.txt').write_text('PENDIENTE DE ENVIO POR TOMAS\nPreferencia vigente: adjuntos_top5/ (5 CSV), mensaje MENSAJE_TOP5.txt\nPromedio20 y lote20 siguen disponibles como alternativas.\n',encoding='utf-8')
    (candidato/'PARA_ENVIAR_BOT.txt').write_text('Adjuntar los5 CSV de adjuntos_top5/\nMensaje: submit '+submit+'\nSeleccion por ganancia media abril/mayo; puntaje agosto desconocido.\n',encoding='utf-8')
    cm['preparacion_preferida']='top5 semillas independientes'
    cm['fuente_ranking_top5']=str(out)
    guardar(candidato/'manifest.json',cm)
    meta.update(estado='completo',semillas_elegidas=elegidas,archivos_top5=archivos,
        archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    guardar(out/'manifest.json',meta)
    print(ranking.head(5).to_string(index=False),flush=True)
    print('Adjuntos:',adj,'\nMensaje: submit',submit,flush=True)


if __name__=='__main__':
    main()
