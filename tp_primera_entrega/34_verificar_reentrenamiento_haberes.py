"""Auditoria independiente de ganancias, folds, feature y candidato del script33."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas
from features_abandono import FUENTES, agregar_abandono

ROOT=Path(__file__).resolve().parents[1]
KEYS=['numero_de_cliente','foto_mes']


def valores(df,p):
    s=np.asarray(p)>.025
    y=df.clase_ternaria.eq('BAJA+2').to_numpy()
    tp=int((s&y).sum()); fp=int((s&~y).sum())
    gain=tp*1072500-fp*27500
    return len(df),int(s.sum()),tp,fp,gain,gain/4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta',type=Path)
    out=parser.parse_args().carpeta
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo' and m['umbral']==.025 and m['operador']=='>'
    assert m['api'] is False and m['creditos']==0
    cols=m['firma']['features']; semillas=m['firma']['semillas']
    assert len(cols['historicas'])==202 and cols['haberes']==cols['historicas']+[m['feature_nueva']]
    assert not set(cols['haberes'])&set(KEYS+['clase_ternaria']) and len(semillas)==3
    for file,h in m['archivos_sha256'].items():
        assert hashlib.sha256((out/file).read_bytes()).hexdigest()==h,file
    grupos=pd.read_csv(out/'asignacion_folds.csv')
    assert not grupos.duplicated(KEYS).any() and set(grupos.foto_mes)=={202103,202104,202105}
    assert grupos.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
    assert set(grupos.fold_cliente)=={0,1,2,3}
    for a in m['auditoria_folds']:
        it=grupos.foto_mes.le(a['mes'])&grupos.fold_cliente.ne(a['fold'])
        iv=grupos.foto_mes.eq(a['mes'])&grupos.fold_cliente.eq(a['fold'])
        assert it.sum()==a['filas_train'] and iv.sum()==a['filas_eval']
        assert grupos.loc[it,'foto_mes'].max()==a['max_mes_train']<=a['mes']
        assert set(grupos.loc[it,'numero_de_cliente']).isdisjoint(set(grupos.loc[iv,'numero_de_cliente']))
    tabla=pd.read_csv(out/'comparacion.csv')
    individual=pd.read_csv(out/'resultados_semillas.csv')
    detalles=pd.read_csv(out/'detalle_folds.csv')
    assert len(tabla)==16 and len(individual)==48 and len(detalles)==32 and len(m['auditoria_folds'])==32
    for r in tabla.itertuples():
        name=f'{r.variante}_cv_{r.target}_{r.mes}.csv' if r.etapa=='cv_cliente' else f'{r.variante}_{r.etapa}_{r.target}.csv'
        df=pd.read_csv(out/name)
        ref=grupos[grupos.foto_mes.eq(r.mes)].reset_index(drop=True)
        pd.testing.assert_frame_equal(df[KEYS+['clase_ternaria']].reset_index(drop=True),ref[KEYS+['clase_ternaria']])
        pcols=[f'p_seed{s}' for s in semillas]
        assert np.isfinite(df[pcols+['probabilidad']]).all().all()
        assert ((df[pcols+['probabilidad']]>=0)&(df[pcols+['probabilidad']]<=1)).all().all()
        assert np.allclose(df[pcols].mean(axis=1),df.probabilidad)
        assert valores(df,df.probabilidad)==(r.filas,r.contactos,r.tp,r.fp,r.ganancia,r.ganancia_25pct)
        for q in individual[individual.variante.eq(r.variante)&individual.target.eq(r.target)&individual.etapa.eq(r.etapa)&individual.mes.eq(r.mes)].itertuples():
            assert valores(df,df[f'p_seed{q.seed}'])==(q.filas,q.contactos,q.tp,q.fp,q.ganancia,q.ganancia_25pct)
        if r.etapa=='cv_cliente':
            assert df.fold_cliente.equals(ref.fold_cliente)
            for q in detalles[detalles.variante.eq(r.variante)&detalles.target.eq(r.target)&detalles.mes.eq(r.mes)].itertuples():
                part=df[df.fold_cliente.eq(q.fold)]
                assert valores(part,part.probabilidad)==(q.filas,q.contactos,q.tp,q.fp,q.ganancia,q.ganancia_25pct)
                assert np.isclose(q.fraccion,len(part)/len(df))
                assert np.isclose(q.ganancia_equivalente_mes,q.ganancia/q.fraccion)
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT numero_de_cliente,foto_mes,mpayroll FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    perfil=pd.read_csv(out/'feature_desarrollo.csv')
    pd.testing.assert_frame_equal(raw[KEYS],perfil[KEYS])
    ordinal=(raw.foto_mes//100)*12+(raw.foto_mes%100)
    previo=raw[['numero_de_cliente','mpayroll']].copy()
    previo['ordinal']=ordinal+1
    actual=raw[['numero_de_cliente']].copy(); actual['ordinal']=ordinal
    lag=actual.merge(previo,on=['numero_de_cliente','ordinal'],how='left',sort=False,validate='one_to_one').mpayroll.replace([np.inf,-np.inf],np.nan)
    current=raw.mpayroll.replace([np.inf,-np.inf],np.nan)
    esperado=((lag>0)&current.eq(0)).astype(float).where(lag.notna()&current.notna())
    assert np.allclose(esperado,perfil[m['feature_nueva']],equal_nan=True)
    ver=dict(estado='verificado',comparaciones=16,resultados_semillas=48,folds_auditados=32,
        clientes_disjuntos=True,meses_fit_verificados=True,feature_recalculada_desde_csv_crudo=True,
        probabilidades_y_ganancias_reconstruidas=True,api=False,creditos=0,test_independiente=False)
    if 'carpeta_candidato' in m:
        candidato=Path(m['carpeta_candidato'])
        cm=json.loads((candidato/'manifest.json').read_text())
        assert cm['target']=='baja2' and cm['features']==cols['haberes'] and len(cm['semillas'])==20
        assert cm['train']==[202105,202106] and cm['futuro']==202108
        df=pd.read_csv(candidato/'predicciones_agosto.csv')
        pcols=[f'p_seed{s}' for s in cm['semillas']]
        assert len(df)==164647 and df.foto_mes.eq(202108).all() and not df.numero_de_cliente.duplicated().any()
        assert np.isfinite(df[pcols+['probabilidad']]).all().all()
        assert ((df[pcols+['probabilidad']]>=0)&(df[pcols+['probabilidad']]<=1)).all().all()
        assert np.allclose(df[pcols].mean(axis=1),df.probabilidad)
        archivo=candidato/cm['archivo_submit']
        assert hashlib.sha256(archivo.read_bytes()).hexdigest()==cm['archivo_sha256']
        ids=list(map(int,archivo.read_text().splitlines()))
        assert len(ids)==len(set(ids))==cm['contactos']
        assert set(ids)==set(df.loc[df.probabilidad>.025,'numero_de_cliente'])
        for seed in cm['semillas']:
            model=lgb.Booster(model_file=str(candidato/'modelos'/f'seed{seed}.txt'))
            assert model.feature_name()==cols['haberes'] and model.num_trees()==cm['elegido']['num_boost_round']
        # Reconstruir agosto y reproducir una semilla final desde el modelo guardado.
        with duckdb.connect() as con:
            con.execute('SET threads=2')
            con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
            agosto=con.sql('SELECT * EXCLUDE(clase_ternaria) FROM datos WHERE foto_mes=202108 ORDER BY numero_de_cliente').df()
            fuentes=list(dict.fromkeys(HISTORICAS+HISTORICAS_EXTRA+FUENTES))
            hist=con.sql('SELECT numero_de_cliente,foto_mes,'+','.join(fuentes)+' FROM datos WHERE foto_mes<=202108 ORDER BY foto_mes,numero_de_cliente').df()
        h=agregar_historicas_ampliadas(hist[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
        a=agregar_abandono(hist[KEYS+FUENTES])
        nuevas=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
        agosto=agosto.merge(h[KEYS+nuevas],on=KEYS,validate='one_to_one',sort=False)
        agosto=agosto.merge(a[KEYS+[m['feature_nueva']]],on=KEYS,validate='one_to_one',sort=False)
        pd.testing.assert_frame_equal(agosto[KEYS],df[KEYS])
        seed=cm['semillas'][1]
        model=lgb.Booster(model_file=str(candidato/'modelos'/f'seed{seed}.txt'))
        xp=preparar(agosto,cols['haberes'])[0]
        assert np.allclose(model.predict(xp),df[f'p_seed{seed}'],rtol=1e-10,atol=1e-12)
        cv=dict(estado='verificado',claves_agosto=True,umbral_y_promedio_20semillas=True,
            modelos_guardados=20,semilla_reproducida=seed,contactos=len(ids),ganancia_agosto_desconocida=True)
        (candidato/'verificacion.json').write_text(json.dumps(cv,indent=2),encoding='utf-8')
        ver['candidato']=cv
    (out/'verificacion.json').write_text(json.dumps(ver,indent=2),encoding='utf-8')
    print(ver)


if __name__=='__main__':
    main()
