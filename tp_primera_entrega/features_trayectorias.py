"""Trayectorias y perdida de canales, solo meses calendario anteriores.

No acepta ni utiliza etiquetas. Faltante no equivale a cero.
"""
import numpy as np
import pandas as pd
from features import CANALES,HISTORICAS,ratio_seguro

KEYS=['numero_de_cliente','foto_mes']
FUENTES=list(dict.fromkeys(HISTORICAS+CANALES))
BLOQUES={
    'canales':['tray_canales_activos','tray_canales_perdidos_1','tray_delta_canales_activos_1'],
    'nivel_previo':['tray_ratio_max_previo_2_'+c for c in HISTORICAS]+['tray_meses_previos_2'],
    'caida_sostenida':['tray_caida_sostenida_2_'+c for c in HISTORICAS],
}
FEATURES=[c for bloque in BLOQUES.values() for c in bloque]


def agregar_trayectorias(datos):
    if datos[KEYS].isna().any().any() or datos.duplicated(KEYS).any():
        raise ValueError('Claves incompletas o duplicadas')
    meses=pd.to_datetime(datos.foto_mes.astype(str),format='%Y%m')
    ordinal=meses.dt.year*12+meses.dt.month
    x=datos[FUENTES].replace([np.inf,-np.inf],np.nan)
    actual=datos[['numero_de_cliente']].copy();actual['_mes']=ordinal.to_numpy()
    previos=[];presencia=[]
    for lag in [1,2]:
        previo=datos[['numero_de_cliente']].join(x)
        previo['_mes']=ordinal.to_numpy()+lag;previo['_presente']=1
        joined=actual.merge(previo,on=['numero_de_cliente','_mes'],how='left',sort=False,validate='one_to_one')
        pasado=joined[FUENTES].copy();pasado.index=datos.index
        previos.append(pasado);presencia.append(joined['_presente'].fillna(0).to_numpy())
    out=datos[KEYS].copy();p1,p2=previos
    uso=x[CANALES].gt(0).astype(float).where(x[CANALES].notna())
    uso_prev=p1[CANALES].gt(0).astype(float).where(p1[CANALES].notna())
    out['tray_canales_activos']=uso.sum(axis=1,min_count=len(CANALES))
    anteriores=uso_prev.sum(axis=1,min_count=len(CANALES))
    out['tray_delta_canales_activos_1']=out.tray_canales_activos-anteriores
    conocidos=x[CANALES].notna()&p1[CANALES].notna()
    perdidos=((p1[CANALES]>0)&x[CANALES].eq(0)).astype(float).where(conocidos)
    out['tray_canales_perdidos_1']=perdidos.sum(axis=1,min_count=len(CANALES))
    out['tray_meses_previos_2']=np.sum(presencia,axis=0).astype(int)
    for c in HISTORICAS:
        maximo=pd.concat([p1[c],p2[c]],axis=1).max(axis=1)
        out['tray_ratio_max_previo_2_'+c]=ratio_seguro(x[c],maximo)
        conocida=x[c].notna()&p1[c].notna()&p2[c].notna()
        out['tray_caida_sostenida_2_'+c]=((x[c]<p1[c])&(p1[c]<p2[c])).astype(float).where(conocida)
    assert set(out.columns)==set(KEYS+FEATURES)
    return out[KEYS+FEATURES]
