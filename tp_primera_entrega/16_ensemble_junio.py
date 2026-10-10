"""Evaluacion exploratoria de ensembles congelados en junio, sin API ni tuning."""
import hashlib
import argparse
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

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fuente', type=Path)
    parser.add_argument('--umbral-fijo', action='store_true', default=True)
    parser.add_argument('--train-meses', nargs=2, type=int, default=[202103,202104],
                        help='Por defecto marzo/abril, alineado con TabPFN y horizonte de agosto.')
    args = parser.parse_args()
    if sorted(args.train_meses) not in [[202103,202104],[202104,202105]]:
        parser.error('Usar marzo/abril o abril/mayo (referencia retrospectiva anterior).')
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    fuente = args.fuente or ROOT/'tp_primera_entrega/salidas/01_entregas_bot/2_lgbm_catedra_hist_20261004_225654'
    tabpath = ROOT/'tp_primera_entrega/salidas/tabpfn_historicas_20261004_172322_339836/predicciones.csv'
    manifest = json.loads((fuente/'manifest.json').read_text(encoding='utf-8'))
    for p, v in manifest['versiones'].items():
        assert importlib.metadata.version(p) == v, p
    for p in ['features.py', 'baseline.py']:
        assert hashlib.sha256((Path(__file__).parent/p).read_bytes()).hexdigest() == manifest['codigo_sha256'][p]
    elegido = manifest['elegido']
    out = ROOT/config['salidas']/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('ensemble_junio_%Y%m%d_%H%M%S')
    out.mkdir()
    protocolo = dict(estado='iniciado', train_lightgbm=args.train_meses, evaluacion=202106,
        semillas=manifest['semillas'], elegido=elegido, peso_tabpfn=0.5,
        cortes=[] if args.umbral_fijo else sorted(set([elegido.get('contactos',8500),8500,9953])), notas='Junio expuesto: exploratorio. Sin seleccion de pesos ni cortes. TabPFN entrenado marzo/abril. Target LightGBM: '+elegido['target'],
        alineado_con_tabpfn=sorted(args.train_meses)==[202103,202104],
        fuente_lightgbm=str(fuente), fuente_tabpfn=str(tabpath))
    def guardar():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    guardar()
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        consulta = 'SELECT * FROM datos WHERE foto_mes <= 202106 ORDER BY foto_mes,numero_de_cliente'
        if sorted(args.train_meses)==[202103,202104]:
            # Mayo aporta historia auxiliar, nunca etiquetas para entrenamiento.
            consulta = "SELECT * REPLACE (CASE WHEN foto_mes=202105 THEN NULL ELSE clase_ternaria END AS clase_ternaria) FROM datos WHERE foto_mes <= 202106 ORDER BY foto_mes,numero_de_cliente"
        datos = con.sql(consulta).df()
    claves=['numero_de_cliente','foto_mes']
    fuentes=HISTORICAS+HISTORICAS_EXTRA
    historia=datos[claves+fuentes].copy()
    historia[fuentes]=historia[fuentes].replace([np.inf,-np.inf],np.nan)
    historia=agregar_historicas_ampliadas(historia)
    nuevas=[c for c in historia if c not in claves+fuentes]
    datos=datos.merge(historia[claves+nuevas],on=claves,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.isin(args.train_meses)].reset_index(drop=True)
    junio=datos.loc[datos.foto_mes.eq(202106)].reset_index(drop=True)
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    protocolo['filas_train']=len(train)
    protocolo['filas_sin_historia_previa']=int(train.historial_mes_anterior_disponible.eq(0).sum())
    guardar()
    xt=preparar(train,manifest['features'])[0]
    xp=preparar(junio,manifest['features'])[0]
    y=(train.clase_ternaria.eq('BAJA+2') if elegido['target']=='baja2' else train.clase_ternaria.isin(['BAJA+1','BAJA+2'])).astype(int)
    pred=junio[claves+['clase_ternaria']].copy()
    for seed in manifest['semillas']:
        model=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=elegido['num_boost_round'])
        pred[f'p_seed{seed}']=model.predict(xp)
        print('Semilla completa:',seed,flush=True)
    pred['p_lightgbm']=pred[[f'p_seed{s}' for s in manifest['semillas']]].mean(axis=1)
    tab=pd.read_csv(tabpath)
    assert not tab.duplicated(claves).any()
    pred=pred.merge(tab[claves+['clase_ternaria','p_historicas']],on=claves,validate='one_to_one',suffixes=('','_tab'))
    assert len(pred)==len(junio)==len(tab)
    assert pred.clase_ternaria.eq(pred.clase_ternaria_tab).all()
    pred=pred.drop(columns='clase_ternaria_tab').rename(columns={'p_historicas':'p_tabpfn'})
    pred['mezcla_probabilidades']=(pred.p_lightgbm+pred.p_tabpfn)/2
    pred['mezcla_rankings']=(pred.p_lightgbm.rank(method='average',pct=True)+pred.p_tabpfn.rank(method='average',pct=True))/2
    assert np.isfinite(pred.select_dtypes('number')).all().all()
    pagos=np.where(pred.clase_ternaria.eq('BAJA+2'),1072500,-27500)
    resultados=[]
    def evaluar(nombre, seleccion):
        tp=int(pred.clase_ternaria.iloc[seleccion].eq('BAJA+2').sum())
        resultados.append(dict(modelo=nombre,contactos=len(seleccion),tp=tp,fp=len(seleccion)-tp,ganancia=int(pagos[seleccion].sum())))
    for col in ['p_tabpfn','p_lightgbm','mezcla_probabilidades','mezcla_rankings']:
        if args.umbral_fijo:
            if col == 'mezcla_rankings':
                continue
            evaluar(col,np.flatnonzero(pred[col].to_numpy()>0.025))
            continue
        orden=np.lexsort((pred.numero_de_cliente.to_numpy(),-pred[col].to_numpy()))
        for k in protocolo['cortes']:
            evaluar(col,orden[:k])
    evaluar('tabpfn_umbral_0.025',np.flatnonzero(pred.p_tabpfn.to_numpy()>0.025))
    if args.umbral_fijo:
        protocolo.update(cortes=[],umbral=0.025,operador='>',notas=protocolo['notas']+' Solo umbral fijo; sin rankings.')
        for r in resultados:
            r['ganancia_25pct']=r['ganancia']/4
    prev=json.loads((fuente/'diagnostico_junio.json').read_text()) if sorted(args.train_meses)==[202104,202105] and (fuente/'diagnostico_junio.json').exists() else []
    for d in prev:
        orden=np.lexsort((pred.numero_de_cliente.to_numpy(),-pred[f"p_seed{d['seed']}"].to_numpy()))
        assert int(pagos[orden[:d['contactos']]].sum())==d['ganancia'], d
    assert resultados[-1]['ganancia']==380792500
    pred.to_csv(out/'predicciones_junio.csv',index=False)
    resumen=pd.DataFrame(resultados)
    resumen.to_csv(out/'comparacion.csv',index=False)
    protocolo.update(estado='completo',filas=len(pred),verificacion=dict(semillas_previas_reproducidas=len(prev),ganancia_tabpfn_reproducida=True,claves_etiquetas_coinciden=True),resultados=resultados)
    guardar()
    print(resumen.to_string(index=False),flush=True)
    print('Salida:',out,flush=True)


if __name__=='__main__':
    main()
