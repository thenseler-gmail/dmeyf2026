"""Ocho señales de vínculos recurrentes; mes calendario anterior, sin etiquetas."""
import numpy as np
import pandas as pd

KEYS=['numero_de_cliente','foto_mes']
FAMILIAS={
    'debitos':['ccuenta_debitos_automaticos','ctarjeta_visa_debitos_automaticos','ctarjeta_master_debitos_automaticos'],
    'pagos':['cpagodeservicios','cpagomiscuentas'],
    'prestamos':['cprestamos_personales','cprestamos_prendarios','cprestamos_hipotecarios'],
    'inversiones':['cplazo_fijo','cinversion1','cinversion2'],
}
FUENTES=[c for cols in FAMILIAS.values() for c in cols]
FEATURES=['vinculos_familias_actuales','vinculos_delta_familias']+[
    'vinculos_perdida_'+f for f in FAMILIAS]+['vinculos_servicios_recurrentes','vinculos_delta_servicios_recurrentes']

def presentes(frame):
    flags={}
    for family,cols in FAMILIAS.items():
        positive=frame[cols].gt(0).any(axis=1)
        zero=frame[cols].eq(0).all(axis=1)
        flags[family]=positive.astype(float).where(positive|zero)
    return pd.DataFrame(flags,index=frame.index)

def agregar_vinculos(datos):
    if datos[KEYS].isna().any().any() or datos.duplicated(KEYS).any():
        raise ValueError('Claves incompletas o duplicadas')
    x=datos[FUENTES].astype(float).replace([np.inf,-np.inf],np.nan)
    date=pd.to_datetime(datos.foto_mes.astype(str),format='%Y%m')
    ordinal=date.dt.year*12+date.dt.month
    previous=pd.concat([datos[['numero_de_cliente']].reset_index(drop=True),x.reset_index(drop=True)],axis=1)
    previous['_mes']=ordinal.to_numpy()+1
    current=datos[['numero_de_cliente']].copy();current['_mes']=ordinal.to_numpy()
    lag=current.merge(previous,on=['numero_de_cliente','_mes'],how='left',sort=False,validate='one_to_one')[FUENTES]
    lag.index=datos.index
    now=presentes(x);before=presentes(lag)
    count=now.sum(axis=1,min_count=4).where(x.notna().all(axis=1))
    count_before=before.sum(axis=1,min_count=4).where(lag.notna().all(axis=1))
    out=datos[KEYS].copy()
    out[FEATURES[0]]=count;out[FEATURES[1]]=count-count_before
    for family in FAMILIAS:
        known=now[family].notna()&before[family].notna()
        out['vinculos_perdida_'+family]=((before[family]==1)&(now[family]==0)).astype(float).where(known)
    recurrent=FAMILIAS['debitos']+FAMILIAS['pagos']
    services=x[recurrent].gt(0).sum(axis=1).astype(float).where(x[recurrent].notna().all(axis=1))
    services_before=lag[recurrent].gt(0).sum(axis=1).astype(float).where(lag[recurrent].notna().all(axis=1))
    out[FEATURES[-2]]=services;out[FEATURES[-1]]=services-services_before
    assert list(out)==KEYS+FEATURES
    return out

def verificar_independiente(datos,result):
    """Reconstrucción por diccionarios de familias y lookup calendario, sin merge."""
    pd.testing.assert_frame_equal(result[KEYS],datos[KEYS])
    x=datos[FUENTES].astype(float).replace([np.inf,-np.inf],np.nan)
    names=list(FAMILIAS)
    def state(arr):
        positive=(arr>0).any(axis=1);zero=(arr==0).all(axis=1)
        return np.where(positive,1.,np.where(zero,0.,np.nan))
    family={f:state(x[cols].to_numpy()) for f,cols in FAMILIAS.items()}
    flags=np.column_stack([family[f] for f in names])
    count=np.where(x.notna().all(axis=1),flags.sum(axis=1),np.nan)
    rc=FAMILIAS['debitos']+FAMILIAS['pagos']
    services=np.where(x[rc].notna().all(axis=1),(x[rc].to_numpy()>0).sum(axis=1),np.nan)
    months=pd.PeriodIndex(datos.foto_mes.astype(str),freq='M')
    lookup={(int(cid),month):i for i,(cid,month) in enumerate(zip(datos.numero_de_cliente,months))}
    indices=np.array([lookup.get((int(cid),month-1),-1) for cid,month in zip(datos.numero_de_cliente,months)])
    valid=indices>=0
    def prev(a):
        b=np.full(len(a),np.nan);b[valid]=a[indices[valid]];return b
    expected={FEATURES[0]:count,FEATURES[1]:count-prev(count),FEATURES[-2]:services,FEATURES[-1]:services-prev(services)}
    for f in names:
        before=prev(family[f]);current=family[f]
        expected['vinculos_perdida_'+f]=np.where(np.isfinite(before)&np.isfinite(current),((before==1)&(current==0)).astype(float),np.nan)
    for c in FEATURES:np.testing.assert_allclose(result[c],expected[c],rtol=0,atol=0,equal_nan=True)
    return dict(estado='verificado',filas=len(datos),fuentes=len(FUENTES),features=len(FEATURES),regla='mes calendario; faltantes desconocidos')

def verificar_ejemplos():
    toy=pd.DataFrame({'numero_de_cliente':[1,1,1,2,2,3,3],
        'foto_mes':[202012,202101,202103,202101,202102,202101,202102]})
    for c in FUENTES:toy[c]=[1.,0.,0.,0.,0.,0.,0.]
    toy.loc[3,FAMILIAS['debitos'][0]]=np.nan
    toy.loc[3,FAMILIAS['debitos'][1]]=1.
    toy.loc[5,FAMILIAS['prestamos'][0]]=-1.
    a=agregar_vinculos(toy);verificar_independiente(toy,a)
    assert a.loc[1,'vinculos_delta_familias']==-4
    assert a.loc[1,'vinculos_perdida_debitos']==1
    assert pd.isna(a.loc[2,'vinculos_delta_familias'])
    assert a.loc[4,'vinculos_perdida_debitos']==1
    assert pd.isna(a.loc[4,'vinculos_delta_familias'])
    assert pd.isna(a.loc[6,'vinculos_perdida_prestamos'])
    changed=toy.copy();changed['clase_ternaria']='BAJA+2'
    pd.testing.assert_frame_equal(a,agregar_vinculos(changed))
    reordered=toy.sample(frac=1,random_state=7)
    pd.testing.assert_frame_equal(a.sort_index(),agregar_vinculos(reordered).sort_index())
    return dict(estado='verificado',checks=['cambio de año','huecos','positivo parcial','nulos','negativos','sin etiquetas','orden'])
