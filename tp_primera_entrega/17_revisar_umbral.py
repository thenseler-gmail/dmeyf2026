"""Revisa candidatos existentes en mayo y evalua junio con p > 0.025."""
import json
import importlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
OLD=SAL/'01_entregas_bot/2_lgbm_catedra_hist_20261004_225654'
NEW=SAL/'lgbm_catedra_hist_20261005_124441'


def metricas(df,prob):
    seleccion=np.asarray(prob)>0.025
    tp=int((df.clase_ternaria.eq('BAJA+2').to_numpy() & seleccion).sum())
    n=int(seleccion.sum())
    gain=tp*1072500-(n-tp)*27500
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia=gain,ganancia_25pct=gain/4)


def main():
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('revision_umbral_%Y%m%d_%H%M%S')
    out.mkdir()
    manifests=[json.loads((p/'manifest.json').read_text()) for p in [OLD,NEW]]
    protocolo=dict(estado='iniciado',umbral=0.025,operador='>',seleccion='Mayo, media de tres semillas; candidatos existentes sin repetir Optuna',notas='Junio expuesto, exploratorio. Sin rankings ni optimizacion de contactos/pesos.',fuentes=[str(OLD),str(NEW)])
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    # Primero recalcular las comparaciones guardadas, sin nuevos entrenamientos.
    recalculos=[]
    for carpeta in ['ensemble_junio_20261005_124204','ensemble_junio_20261005_125848']:
        df=pd.read_csv(SAL/carpeta/'predicciones_junio.csv')
        for col in ['p_tabpfn','p_lightgbm','mezcla_probabilidades']:
            recalculos.append(dict(fuente=carpeta,modelo=col,**metricas(df,df[col])))
    pd.DataFrame(recalculos).to_csv(out/'junio_configuraciones_anteriores.csv',index=False)
    print(pd.DataFrame(recalculos).to_string(index=False),flush=True)
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * FROM datos WHERE foto_mes<=202105 ORDER BY foto_mes,numero_de_cliente').df()
    claves=['numero_de_cliente','foto_mes']
    fuentes=HISTORICAS+HISTORICAS_EXTRA
    historia=datos[claves+fuentes].copy()
    historia[fuentes]=historia[fuentes].replace([np.inf,-np.inf],np.nan)
    historia=agregar_historicas_ampliadas(historia)
    nuevas=[c for c in historia if c not in claves+fuentes]
    datos=datos.merge(historia[claves+nuevas],on=claves,validate='one_to_one',sort=False)
    frames={m:datos.loc[datos.foto_mes.eq(m)].reset_index(drop=True) for m in [202104,202105]}
    columnas=manifests[0]['features']
    assert columnas==manifests[1]['features']
    xs={m:preparar(df,columnas)[0] for m,df in frames.items()}
    candidatos=[]; vistos=set(); detalles=[]; cache={}
    for carpeta in [OLD,NEW]:
        for c in json.loads((carpeta/'candidatos.json').read_text()):
            firma=json.dumps([c['target'],c['params'],c['num_boost_round']],sort_keys=True)
            if firma in vistos:
                continue
            vistos.add(firma)
            nombre=f"{carpeta.name}_{c['target']}_trial{c['trial']}"
            pred=frames[202105][claves+['clase_ternaria']].copy()
            y=(frames[202104].clase_ternaria.eq('BAJA+2') if c['target']=='baja2' else frames[202104].clase_ternaria.isin(['BAJA+1','BAJA+2'])).astype(int)
            ganancias=[]
            for seed in manifests[0]['semillas'][:3]:
                model=lgb.train(dict(c['params'],seed=seed),lgb.Dataset(xs[202104],label=y),num_boost_round=c['num_boost_round'])
                prob=model.predict(xs[202105])
                assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
                pred[f'p_seed{seed}']=prob
                met=metricas(pred,prob)
                ganancias.append(met['ganancia'])
                detalles.append(dict(candidato=nombre,target=c['target'],seed=seed,**met))
            pred['p_promedio']=pred.filter(like='p_seed').mean(axis=1)
            pred.to_csv(out/(nombre+'_mayo.csv'),index=False)
            nuevo=dict(c,identificador=nombre,umbral=0.025,ganancia_mayo_media=float(np.mean(ganancias)),ganancia_mayo_std=float(np.std(ganancias,ddof=1)),ensemble_mayo=metricas(pred,pred.p_promedio))
            nuevo.pop('contactos',None)
            candidatos.append(nuevo)
            (out/'candidatos.json').write_text(json.dumps(candidatos,indent=2),encoding='utf-8')
            pd.DataFrame(detalles).to_csv(out/'seleccion_mayo_semillas.csv',index=False)
            print('Candidato:',nombre,nuevo['ganancia_mayo_media'],flush=True)
    ganadores={t:max([c for c in candidatos if c['target']==t],key=lambda c:c['ganancia_mayo_media']) for t in ['baja2','bajas']}
    protocolo.update(estado='seleccion_completa',ganadores=ganadores)
    save()
    # Configuraciones congeladas antes de las nuevas evaluaciones de junio.
    modulo=importlib.import_module('16_ensemble_junio')
    import sys
    for target,c in ganadores.items():
        carpeta=out/target
        carpeta.mkdir()
        m=dict(manifests[0],elegido=c)
        (carpeta/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
        sys.argv=['16_ensemble_junio.py','--fuente',str(carpeta),'--umbral-fijo']
        modulo.main()
    protocolo['estado']='completo'
    save()
    print('REVISION COMPLETA:',out,flush=True)


if __name__=='__main__':
    main()
