"""Piloto local: CV por cliente abril/mayo + control temporal marzo -> mayo.

CV retrospectivo: cada mes usa etiquetas de otros clientes hasta ese mismo mes.
No sustituye el control temporal de dos meses ni un test independiente.
Sin TabPFN, API, tuning de umbral ni seleccion de una nueva entrega.
"""
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
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT / 'tp_primera_entrega/salidas'
KEYS = ['numero_de_cliente', 'foto_mes']


def guardar(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def medir(df, p):
    p = np.asarray(p)
    assert len(df) == len(p) and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
    selected = p > 0.025
    y = df.clase_ternaria.eq('BAJA+2').to_numpy()
    tp = int((selected & y).sum())
    fp = int((selected & ~y).sum())
    gain = tp * 1072500 - fp * 27500
    return dict(filas=len(df), contactos=tp+fp, tp=tp, fp=fp, ganancia=gain, ganancia_25pct=gain/4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--semillas', type=int, choices=[1, 3], default=1)
    parser.add_argument('--salida', type=Path)
    args = parser.parse_args()
    out = args.salida or SAL / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('validacion_lgbm_%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=False)
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8'))
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        inventario = con.sql("""SELECT foto_mes, count(*) filas,
            count(*) FILTER (WHERE clase_ternaria IN ('CONTINUA','BAJA+1','BAJA+2')) etiquetas_conocidas,
            count(*) FILTER (WHERE clase_ternaria='BAJA+2') baja2,
            count(*) FILTER (WHERE mpayroll>0) clientes_haberes,
            median(mpayroll) FILTER (WHERE mpayroll>0) mediana_haberes_positivos,
            avg(mpayroll) FILTER (WHERE mpayroll>0) media_haberes_positivos
            FROM datos GROUP BY foto_mes ORDER BY foto_mes""").df()
        # Las etiquetas de junio/julio/agosto solo se cuentan para el inventario.
        df = con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    inventario.to_csv(out/'inventario_meses.csv', index=False)
    assert not df.duplicated(KEYS).any()
    assert df.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    basecols = [c for c in df if c not in KEYS+['clase_ternaria']]
    historia = agregar_historicas_ampliadas(df[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    nuevas = [c for c in historia if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    df = df.merge(historia[KEYS+nuevas], on=KEYS, validate='one_to_one', sort=False)
    cols = basecols+nuevas
    assert len(cols) == 202 and len(basecols) == 152
    x = preparar(df, cols)[0]
    referencias = {}
    for target in ['baja2','bajas']:
        path = SAL/'revision_umbral_20261005_131001'/target/'manifest.json'
        referencias[target] = json.loads(path.read_text())
    seeds = referencias['bajas']['semillas'][:args.semillas]
    clientes = np.sort(df.numero_de_cliente.unique())
    clientes = np.random.default_rng(214363).permutation(clientes)
    mapa = pd.Series(np.arange(len(clientes)) % 4, index=clientes)
    folds = df.numero_de_cliente.map(mapa).to_numpy(dtype=int)
    asignacion = df[KEYS+['clase_ternaria']].copy()
    asignacion['fold_cliente'] = folds
    asignacion.to_csv(out/'asignacion_folds.csv', index=False)
    manifest = dict(estado='ejecutando',features=cols, folds=4,seed_folds=214363,
        semillas=seeds,objetivo_publico=100000000,referencia_total_equivalente=400000000,
        fecha_entrega=config['fecha_entrega'],umbral=0.025,operador='>',
        cv_meses=[202104,202105],train_permitido=[202103,202104,202105],
        control_temporal=dict(train=[202103],evaluacion=202105,distancia_meses=2),
        control_retrospectivo=dict(train=[202104],evaluacion=202105,distancia_meses=1),
        modelos={t:r['elegido'] for t,r in referencias.items()},
        versiones={p:importlib.metadata.version(p) for p in ['lightgbm','duckdb','numpy','pandas']},
        codigo_sha256={f:hashlib.sha256((Path(__file__).parent/f).read_bytes()).hexdigest() for f in ['30_validacion_lightgbm.py','features.py','baseline.py']},
        limitaciones='CV por cliente retrospectivo: usa etiquetas de otros clientes del mismo mes. No evalua drift futuro. Marzo sin febrero. Mayo reutilizado y parametros previamente seleccionados en mayo. Piloto sin tuning; una semilla por defecto no demuestra robustez. Junio solo inventario, no seleccion. BAJA+1 cuenta como error de ganancia; el score del target combinado no es P(BAJA+2).',
        auditoria_folds=[],resultados=[])
    guardar(out/'manifest.json',manifest)
    resultados=[]
    detalles=[]
    for target,ref in referencias.items():
        spec=ref['elegido']
        y=(df.clase_ternaria.eq('BAJA+2') if target=='baja2' else df.clase_ternaria.isin(['BAJA+1','BAJA+2'])).astype(int).to_numpy()
        for mes in [202104,202105]:
            ivmes=np.flatnonzero(df.foto_mes.to_numpy()==mes)
            probs=np.full((len(df),len(seeds)),np.nan)
            for fold in range(4):
                it=np.flatnonzero((df.foto_mes.to_numpy()<=mes)&(folds!=fold))
                iv=np.flatnonzero((df.foto_mes.to_numpy()==mes)&(folds==fold))
                assert set(df.numero_de_cliente.iloc[it]).isdisjoint(set(df.numero_de_cliente.iloc[iv]))
                assert df.foto_mes.iloc[it].max()<=mes
                manifest['auditoria_folds'].append(dict(target=target,mes_eval=mes,fold=fold,max_mes_train=int(df.foto_mes.iloc[it].max()),clientes_solapados=0,filas_train=len(it),filas_eval=len(iv)))
                for j,seed in enumerate(seeds):
                    model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it],label=y[it]),num_boost_round=spec['num_boost_round'])
                    probs[iv,j]=model.predict(x.iloc[iv])
                p=probs[iv].mean(axis=1)
                metric=medir(df.iloc[iv],p)
                fraccion=len(iv)/len(ivmes)
                detalles.append(dict(target=target,mes=mes,fold=fold,fraccion_evaluada=fraccion,**metric,
                    ganancia_equivalente_mes=metric['ganancia']/fraccion,
                    ganancia_equivalente_mes_25pct=metric['ganancia']/fraccion/4))
                print(target,mes,'fold',fold+1,'/4 completo',flush=True)
            p=probs[ivmes].mean(axis=1)
            pred=df.iloc[ivmes][KEYS+['clase_ternaria']].copy()
            pred['fold_cliente']=folds[ivmes]
            for j,seed in enumerate(seeds):
                pred[f'p_seed{seed}']=probs[ivmes,j]
            pred['probabilidad']=p
            pred.to_csv(out/f'cv_{target}_{mes}.csv',index=False)
            resultados.append(dict(etapa='cv_cliente',target=target,mes=mes,**medir(pred,p)))
            manifest['resultados']=resultados
            guardar(out/'manifest.json',manifest)
            pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
            pd.DataFrame(detalles).to_csv(out/'detalle_folds.csv',index=False)
        for etapa,train_meses in [('temporal_2meses',[202103]),('retrospectivo_1mes',[202104])]:
            it=np.flatnonzero(df.foto_mes.isin(train_meses).to_numpy())
            iv=np.flatnonzero(df.foto_mes.eq(202105).to_numpy())
            psem=[]
            for seed in seeds:
                model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it],label=y[it]),num_boost_round=spec['num_boost_round'])
                psem.append(model.predict(x.iloc[iv]))
            pred=df.iloc[iv][KEYS+['clase_ternaria']].copy()
            for seed,pseed in zip(seeds,psem):
                pred[f'p_seed{seed}']=pseed
            pred['probabilidad']=np.mean(psem,axis=0)
            pred.to_csv(out/f'{etapa}_{target}.csv',index=False)
            resultados.append(dict(etapa=etapa,target=target,mes=202105,**medir(pred,pred.probabilidad)))
            print(target,etapa,resultados[-1],flush=True)
    manifest.update(estado='completo',resultados=resultados,filas=len(df),clientes=len(clientes),
        archivos_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')})
    pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
    # Actualizar el hash despues de escribir la tabla final.
    manifest['archivos_sha256']['comparacion.csv']=hashlib.sha256((out/'comparacion.csv').read_bytes()).hexdigest()
    guardar(out/'manifest.json',manifest)
    print(pd.DataFrame(resultados).to_string(index=False),flush=True)
    print('Salida:',out,flush=True)


if __name__=='__main__':
    main()
