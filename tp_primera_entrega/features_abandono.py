"""Senales de interrupcion y caida conjunta; solo un mes calendario previo.

Separado de features.py para conservar los generadores/hashes de referencias.
No lee etiquetas. Un dato ausente no representa inactividad.
"""
import numpy as np
import pandas as pd

ACTIVIDAD = ['ctrx_quarter','Visa_mconsumototal','Master_mconsumototal',
             'ctarjeta_visa_transacciones','ctarjeta_master_transacciones',
             'chomebanking_transacciones','cmobile_app_trx']
FUENTES = ACTIVIDAD + ['mpayroll','mcuentas_saldo','cproductos']


def bandera(condicion, conocidas):
    return condicion.astype(float).where(conocidas)


def agregar_abandono(datos):
    keys=['numero_de_cliente','foto_mes']
    if datos[keys].isna().any().any() or datos.duplicated(keys).any():
        raise ValueError('Claves incompletas o duplicadas.')
    fecha=pd.to_datetime(datos.foto_mes.astype(str),format='%Y%m')
    ordinal=fecha.dt.year*12+fecha.dt.month
    previo=datos[['numero_de_cliente']+FUENTES].copy()
    previo['_mes']=ordinal.to_numpy()+1
    actual=datos[['numero_de_cliente']].copy()
    actual['_mes']=ordinal.to_numpy()
    lag=actual.merge(previo,on=['numero_de_cliente','_mes'],how='left',sort=False,validate='one_to_one')[FUENTES]
    lag.index=datos.index
    x=datos[FUENTES].replace([np.inf,-np.inf],np.nan)
    lag=lag.replace([np.inf,-np.inf],np.nan)
    out=datos[keys].copy()
    for c in ACTIVIDAD+['mpayroll']:
        conocidas=x[c].notna() & lag[c].notna()
        out['abandono_pasa_a_cero_'+c]=bandera((lag[c]>0)&x[c].eq(0),conocidas)
    out['abandono_reduce_productos']=bandera(x.cproductos<lag.cproductos,x.cproductos.notna() & lag.cproductos.notna())
    conocidas=x[ACTIVIDAD].notna() & lag[ACTIVIDAD].notna()
    caidas=(x[ACTIVIDAD]<lag[ACTIVIDAD]).astype(float).where(conocidas)
    out['abandono_cantidad_actividades_en_caida']=caidas.sum(axis=1,min_count=len(ACTIVIDAD))
    out['abandono_fraccion_actividades_en_caida']=out.abandono_cantidad_actividades_en_caida/len(ACTIVIDAD)
    consumo=x.Visa_mconsumototal+x.Master_mconsumototal
    consumo_previo=lag.Visa_mconsumototal+lag.Master_mconsumototal
    grupos=pd.DataFrame({
        'actividad':bandera(x.ctrx_quarter<lag.ctrx_quarter,x.ctrx_quarter.notna()&lag.ctrx_quarter.notna()),
        'consumo':bandera(consumo<consumo_previo,consumo.notna()&consumo_previo.notna()),
        'saldo':bandera(x.mcuentas_saldo<lag.mcuentas_saldo,x.mcuentas_saldo.notna()&lag.mcuentas_saldo.notna())})
    out['abandono_cantidad_frentes_en_caida']=grupos.sum(axis=1,min_count=3)
    out['abandono_caida_tres_frentes']=bandera(out.abandono_cantidad_frentes_en_caida.eq(3),out.abandono_cantidad_frentes_en_caida.notna())
    return out
