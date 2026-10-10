"""Históricos calendario de orden2, sin modificar el código de las entregas previas."""
import numpy as np
import pandas as pd
from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas
from calidad_datos import corregir_datos

KEYS = ['numero_de_cliente', 'foto_mes']
FUENTES = HISTORICAS + HISTORICAS_EXTRA
ORDEN2 = [prefijo + c for c in FUENTES for prefijo in ['lag_2_', 'delta_2_']]


def agregar_orden2(datos):
    if datos[KEYS].isna().any().any() or datos.duplicated(KEYS).any():
        raise ValueError('Claves cliente-mes inválidas.')
    if set(ORDEN2).intersection(datos):
        raise ValueError('Históricos orden2 ya existentes.')
    out = datos.copy()
    fechas = pd.to_datetime(datos.foto_mes.astype(str), format='%Y%m')
    ordinal = fechas.dt.year * 12 + fechas.dt.month
    previo = datos[['numero_de_cliente', *FUENTES]].copy()
    previo['_mes'] = ordinal.to_numpy() + 2
    previo.rename(columns={c: 'lag_2_' + c for c in FUENTES}, inplace=True)
    actual = datos[['numero_de_cliente']].copy()
    actual['_mes'] = ordinal.to_numpy()
    unidos = actual.merge(previo, on=['numero_de_cliente', '_mes'], how='left',
                          sort=False, validate='one_to_one')
    for c in FUENTES:
        out['lag_2_' + c] = unidos['lag_2_' + c].to_numpy()
        out['delta_2_' + c] = out[c] - out['lag_2_' + c]
    return out


def construir(datos):
    corregido, auditoria = corregir_datos(datos)
    # Invalidar infinitos antes de generar diferencias y relativos.
    corregido[FUENTES] = corregido[FUENTES].replace([np.inf, -np.inf], np.nan)
    hist = agregar_orden2(agregar_historicas_ampliadas(corregido[KEYS + FUENTES]))
    nuevas = [c for c in hist if c not in KEYS + FUENTES]
    out = corregido.merge(hist[KEYS + nuevas], on=KEYS, how='left',
                          sort=False, validate='one_to_one')
    pd.testing.assert_frame_equal(out[KEYS].reset_index(drop=True),
                                  datos[KEYS].reset_index(drop=True))
    return out, auditoria


def verificar():
    """Contrasta joins con un diccionario y prueba huecos y cambio de año."""
    toy = pd.DataFrame({'numero_de_cliente': [1, 1, 1, 2, 2, 2],
                        'foto_mes': [202012, 202102, 202103, 202101, 202102, 202103]})
    for c in FUENTES:
        toy[c] = [10., 20., np.nan, 3., 4., 9.]
    toy.index = [5, 3, 8, 2, 10, 11]
    result = agregar_orden2(toy)
    lookup = {(r.numero_de_cliente, str(r.foto_mes)): r.ctrx_quarter for r in toy.itertuples()}
    for i, row in toy.iterrows():
        mes = pd.Period(str(int(row.foto_mes)), freq='M') - 2
        esperado = lookup.get((row.numero_de_cliente, mes.strftime('%Y%m')), np.nan)
        for c in FUENTES:
            np.testing.assert_allclose(result.loc[i, 'lag_2_' + c], esperado, equal_nan=True)
            np.testing.assert_allclose(result.loc[i, 'delta_2_' + c], row[c] - esperado, equal_nan=True)
    pd.testing.assert_frame_equal(result[toy.columns], toy)
    try:
        agregar_orden2(pd.concat([toy, toy.iloc[:1]]))
    except ValueError:
        pass
    else:
        raise AssertionError('No rechazó claves duplicadas')
    return {'estado': 'verificado', 'checks': ['mes calendario', 'huecos', 'cambio de año',
            'NA', 'orden e índice', 'duplicados rechazados'], 'columnas_nuevas': len(ORDEN2)}
