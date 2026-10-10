"""Ablacion congelada: 202 variables vs bloque de interrupciones, sin API."""
import hashlib
import argparse
import json
import importlib.metadata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas
from features_abandono import agregar_abandono,FUENTES

ROOT=Path(__file__).resolve().parents[1]


def metricas(df,p):
    s=np.asarray(p)>0.025
    tp=int((s&df.clase_ternaria.eq('BAJA+2').to_numpy()).sum()); n=int(s.sum())
    g=tp*1072500-(n-tp)*27500
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4)


def prueba_features():
    filas=[]
    for mes,valor in [(202103,10),(202104,0),(202106,2)]:
        filas.append(dict(numero_de_cliente=1,foto_mes=mes,**{c:valor for c in FUENTES}))
    df=pd.DataFrame(filas); a=agregar_abandono(df)
    assert a.iloc[0,2:].isna().all()
    assert a.loc[1,'abandono_pasa_a_cero_mpayroll']==1
    assert a.loc[1,'abandono_caida_tres_frentes']==1
    assert a.iloc[2,2:].isna().all()  # No usar abril como lag de junio.
    futuro=df.copy(); futuro.loc[2,FUENTES]=999
    pd.testing.assert_frame_equal(a.iloc[:2],agregar_abandono(futuro).iloc[:2])
    falta=df.copy(); falta.loc[1,'mpayroll']=np.nan
    assert pd.isna(agregar_abandono(falta).loc[1,'abandono_pasa_a_cero_mpayroll'])
    cero=df.copy(); cero.loc[0,'mpayroll']=0
    assert agregar_abandono(cero).loc[1,'abandono_pasa_a_cero_mpayroll']==0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--familia-manifest',type=Path)
    args=parser.parse_args()
    prueba_features()
    sal=ROOT/'tp_primera_entrega/salidas'
    ref=sal/'revision_umbral_20261005_131001/bajas'
    m=json.loads((ref/'manifest.json').read_text())
    for paquete,v in m['versiones'].items():
        assert importlib.metadata.version(paquete)==v,paquete
    for archivo in ['features.py','baseline.py']:
        assert hashlib.sha256((Path(__file__).parent/archivo).read_bytes()).hexdigest()==m['codigo_sha256'][archivo]
    elegido=m['elegido']
    out=sal/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('abandono_%Y%m%d_%H%M%S')
    out.mkdir()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * FROM datos WHERE foto_mes<=202106 ORDER BY foto_mes,numero_de_cliente').df()
    claves=['numero_de_cliente','foto_mes']
    fuentes=HISTORICAS+HISTORICAS_EXTRA
    historia=agregar_historicas_ampliadas(datos[claves+fuentes].replace([np.inf,-np.inf],np.nan))
    nuevas_hist=[c for c in historia if c not in claves+fuentes]
    datos=datos.merge(historia[claves+nuevas_hist],on=claves,validate='one_to_one',sort=False)
    adicionales=agregar_abandono(datos[claves+FUENTES])
    nuevas=[c for c in adicionales if c not in claves]
    familia=None
    if args.familia_manifest:
        familia=json.loads(args.familia_manifest.read_text())
        if familia.get('estado') not in ['seleccion_completa','completo'] or not familia.get('familia_elegida'):
            raise ValueError('Se requiere familia seleccionada exclusivamente en mayo.')
        nuevas=familia['features_elegidas']
        assert set(nuevas).issubset(adicionales.columns)
    datos=datos.merge(adicionales[claves+nuevas],on=claves,validate='one_to_one',sort=False)
    columnas=m['features']+nuevas
    protocolo=dict(estado='configuracion_congelada',features_base=m['features'],features_nuevas=nuevas,
        versiones=m['versiones'],
        elegido=elegido,umbral=0.025,operador='>',peso_tabpfn=0.5,
        desarrollo=dict(train=[202104],eval=202105,semillas=m['semillas'][:3]),
        comprobacion=dict(train=[202103,202104],eval=202106,semillas=m['semillas']),
        codigo_sha256={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['features_abandono.py','22_experimento_abandono.py','features.py','baseline.py']},
        notas='Un bloque predefinido; sin tuning, API ni cambio de pesos/corte. Mayo retrospectivo reutilizado. Junio expuesto exploratorio. No incorpora tendencia de dos meses: no hay ejemplos observables de esa tendencia en train marzo/abril.')
    if familia:
        protocolo.update(familia_elegida=familia['familia_elegida'],fuente_seleccion_mayo=str(args.familia_manifest))
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    perfil=[]
    for mes in [202103,202104,202105,202106]:
        df=datos.loc[datos.foto_mes.eq(mes)]
        for c in nuevas:
            perfil.append(dict(mes=mes,variable=c,filas=len(df),no_nulos=int(df[c].notna().sum()),valores_distintos=int(df[c].nunique())))
    pd.DataFrame(perfil).to_csv(out/'cobertura_features.csv',index=False)
    resultados=[]
    for etapa,train_meses,mes,seeds,refpath,tabpath in [
        ('mayo',[202104],202105,m['semillas'][:3],sal/'revision_umbral_20261005_131001/2_lgbm_catedra_hist_20261004_225654_bajas_trial6_mayo.csv',sal/'tabpfn_historicas_20261004_165442_887149/predicciones.csv'),
        ('junio',[202103,202104],202106,m['semillas'],sal/'ensemble_junio_20261005_134901/predicciones_junio.csv',sal/'tabpfn_historicas_20261004_172322_339836/predicciones.csv')]:
        if familia and etapa=='mayo':
            continue
        train=datos.loc[datos.foto_mes.isin(train_meses)].reset_index(drop=True)
        evaluacion=datos.loc[datos.foto_mes.eq(mes)].reset_index(drop=True)
        assert train.clase_ternaria.isin(['BAJA+1','BAJA+2','CONTINUA']).all()
        xt=preparar(train,columnas)[0]; xp=preparar(evaluacion,columnas)[0]
        y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
        pred=evaluacion[claves+['clase_ternaria']].copy()
        base=pd.read_csv(refpath)
        tab=pd.read_csv(tabpath)[claves+['clase_ternaria','p_historicas']]
        pred=pred.merge(base[claves+['clase_ternaria']+[f'p_seed{s}' for s in seeds]],on=claves,validate='one_to_one',suffixes=('','_base'))
        assert pred.clase_ternaria.eq(pred.clase_ternaria_base).all()
        pred=pred.merge(tab,on=claves,validate='one_to_one',suffixes=('','_tab'))
        assert len(pred)==len(evaluacion)==len(base)==len(tab)
        assert pred.clase_ternaria.eq(pred.clase_ternaria_tab).all()
        pred=pred.rename(columns={f'p_seed{s}':f'p_base_seed{s}' for s in seeds})
        # Reproducir control de una semilla para confirmar orden/preparacion/parametros.
        control=lgb.train(dict(elegido['params'],seed=seeds[0]),lgb.Dataset(xt[m['features']],label=y),num_boost_round=elegido['num_boost_round'])
        control_prob=control.predict(xp[m['features']])
        assert np.allclose(control_prob,pred[f'p_base_seed{seeds[0]}'],rtol=1e-10,atol=1e-12)
        for seed in seeds:
            modelo=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=elegido['num_boost_round'])
            prob=modelo.predict(xp)
            assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
            pred[f'p_nuevo_seed{seed}']=prob
            resultados.append(dict(etapa=etapa,modelo='LightGBM nuevo individual',seed=seed,**metricas(pred,prob)))
            # Guardar avance para poder recuperar semillas completas.
            pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
            print(etapa,'semilla completa:',seed,flush=True)
        pred['p_base']=pred[[f'p_base_seed{s}' for s in seeds]].mean(axis=1)
        pred['p_nuevo']=pred[[f'p_nuevo_seed{s}' for s in seeds]].mean(axis=1)
        pred['p_mezcla_base']=(pred.p_base+pred.p_historicas)/2
        pred['p_mezcla_nueva']=(pred.p_nuevo+pred.p_historicas)/2
        for nombre,col in [('TabPFN','p_historicas'),('LightGBM base promedio','p_base'),('LightGBM nuevo promedio','p_nuevo'),('50/50 base','p_mezcla_base'),('50/50 nuevo','p_mezcla_nueva')]:
            resultados.append(dict(etapa=etapa,modelo=nombre,seed='promedio',**metricas(pred,pred[col])))
        pred.to_csv(out/f'predicciones_{etapa}.csv',index=False)
        pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
        protocolo['etapa_completada']=etapa
        save()
        print(pd.DataFrame(resultados).query("seed == 'promedio'").to_string(index=False),flush=True)
    protocolo.update(estado='completo',resultados=resultados,prueba_features='calendario/faltantes/ceros/independencia_futuro correctos',control_base_reproducido=True)
    save()
    print('COMPLETO:',out,flush=True)


if __name__=='__main__':
    main()
