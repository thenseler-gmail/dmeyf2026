"""Desarrollo por familias en mayo; comprobar en junio solo ganador de mayo.

Sin modificar bloque completo ya evaluado, pesos, parametros ni umbral.
"""
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
from features_abandono import agregar_abandono,FUENTES,ACTIVIDAD
from importlib import import_module

ROOT=Path(__file__).resolve().parents[1]


def main():
    met=import_module('22_experimento_abandono').metricas
    sal=ROOT/'tp_primera_entrega/salidas'
    referencia=sal/'abandono_20261005_145518'
    m=json.loads((referencia/'manifest.json').read_text())
    fuente=json.loads((sal/'revision_umbral_20261005_131001/bajas/manifest.json').read_text())
    out=sal/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('abandono_familias_%Y%m%d_%H%M%S')
    out.mkdir()
    familias={
        'haberes':['abandono_pasa_a_cero_mpayroll'],
        'actividades_a_cero':['abandono_pasa_a_cero_'+c for c in ACTIVIDAD],
        'caidas_conjuntas':['abandono_reduce_productos','abandono_cantidad_actividades_en_caida','abandono_cantidad_frentes_en_caida','abandono_caida_tres_frentes']}
    protocolo=dict(estado='desarrollo',familias=familias,referencia=str(referencia),umbral=0.025,peso_tabpfn=0.5,
        criterio='Elegir por ganancia de mezcla promedio mayo (tres semillas), requiere superar control. Junio no decide variante.',
        notas='Mayo y junio reutilizados, exploratorio. Familias definidas tras bloque completo. No repetir Optuna ni API.')
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        datos=con.sql('SELECT * FROM datos WHERE foto_mes<=202105 ORDER BY foto_mes,numero_de_cliente').df()
    claves=['numero_de_cliente','foto_mes']; fs=HISTORICAS+HISTORICAS_EXTRA
    historia=agregar_historicas_ampliadas(datos[claves+fs].replace([np.inf,-np.inf],np.nan))
    extra=[c for c in historia if c not in claves+fs]
    datos=datos.merge(historia[claves+extra],on=claves,validate='one_to_one',sort=False)
    datos=datos.merge(agregar_abandono(datos[claves+FUENTES]),on=claves,validate='one_to_one',sort=False)
    train=datos.loc[datos.foto_mes.eq(202104)].reset_index(drop=True)
    valid=datos.loc[datos.foto_mes.eq(202105)].reset_index(drop=True)
    base=pd.read_csv(referencia/'predicciones_mayo.csv')
    pd.testing.assert_frame_equal(valid[claves],base[claves])
    elegido=m['elegido']; semillas=fuente['semillas'][:3]
    y=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int)
    resultados=[]
    for nombre,nuevas in familias.items():
        columnas=m['features_base']+nuevas
        xt=preparar(train,columnas)[0]; xp=preparar(valid,columnas)[0]
        pred=base[claves+['clase_ternaria','p_historicas']].copy()
        for seed in semillas:
            modelo=lgb.train(dict(elegido['params'],seed=seed),lgb.Dataset(xt,label=y),num_boost_round=elegido['num_boost_round'])
            pred[f'p_seed{seed}']=modelo.predict(xp)
        pred['p_lightgbm']=pred.filter(like='p_seed').mean(axis=1)
        pred['p_mezcla']=(pred.p_lightgbm+pred.p_historicas)/2
        for tipo,c in [('LightGBM','p_lightgbm'),('50/50','p_mezcla')]:
            resultados.append(dict(familia=nombre,modelo=tipo,**met(pred,pred[c])))
        pred.to_csv(out/(nombre+'_mayo.csv'),index=False)
        pd.DataFrame(resultados).to_csv(out/'comparacion_mayo.csv',index=False)
        print(nombre,met(pred,pred.p_mezcla),flush=True)
    control=met(base,base.p_mezcla_base)
    mejor=max([r for r in resultados if r['modelo']=='50/50'],key=lambda r:r['ganancia'])
    protocolo.update(control_mayo=control,ganador_mayo=mejor,familia_elegida=mejor['familia'] if mejor['ganancia']>control['ganancia'] else None)
    save()
    # Si ninguna mejora mayo, no elegir una por lo que haga en junio.
    if protocolo['familia_elegida'] is None:
        protocolo.update(estado='completo',junio_ejecutado=False)
        save()
        print('Sin familia que supere control en mayo. Salida:',out,flush=True)
        return
    # Dejar configuracion concreta para comprobacion, solo de familia elegida.
    protocolo.update(estado='seleccion_completa',features_elegidas=familias[mejor['familia']])
    save()
    print('FAMILIA ELEGIDA:',protocolo['familia_elegida'],'\nSalida:',out,flush=True)


if __name__=='__main__':
    main()
