"""Features intrames e históricas. No usan etiquetas ni aprenden del test."""
import numpy as np
import pandas as pd

# Mismos ocho componentes del notebook previo; incluye canales y tarjetas.
CANALES = [
    'chomebanking_transacciones', 'cmobile_app_trx',
    'ctarjeta_debito_transacciones', 'ctarjeta_visa_transacciones',
    'ctarjeta_master_transacciones', 'catm_trx',
    'ccajas_transacciones', 'ccallcenter_transacciones',
]
BLOQUES = {
    'actividad': ['actividad_por_producto', 'cantidad_canales_activos'],
    'tarjetas': ['tarjetas_saldo_total', 'tarjetas_consumo_total', 'tarjetas_limite_total'],
    'utilizacion': ['Visa_saldo_sobre_limite', 'Visa_consumo_sobre_limite',
                    'Master_saldo_sobre_limite', 'Master_consumo_sobre_limite'],
}
HISTORICAS = ['ctrx_quarter', 'mpayroll', 'mcuentas_saldo', 'cproductos']
HISTORICAS_EXTRA = ['Visa_mconsumototal', 'Master_mconsumototal',
                    'ctarjeta_visa_transacciones', 'ctarjeta_master_transacciones',
                    'chomebanking_transacciones', 'cmobile_app_trx',
                    'ctarjeta_visa', 'ctarjeta_master']


def agregar_historicas_ampliadas(datos):
    """Bloque anterior + lags/deltas relativos y promedio de hasta 3 meses previos.

    Solo historia pasada; promedios ignoran faltantes y registran cobertura.
    La variación relativa usa el valor absoluto anterior, sin dividir por cero.
    """
    out = agregar_historicas(datos)
    keys = ['numero_de_cliente', 'foto_mes']
    fechas = pd.to_datetime(datos.foto_mes.astype(str), format='%Y%m')
    ordinal = fechas.dt.year * 12 + fechas.dt.month
    actual = datos[['numero_de_cliente']].copy()
    actual['_mes'] = ordinal.to_numpy()
    fuentes = HISTORICAS + HISTORICAS_EXTRA
    pasados = []
    coberturas = []
    for lag in (1, 2, 3):
        previo = datos[['numero_de_cliente', *fuentes]].copy()
        previo['_mes'] = ordinal.to_numpy() + lag
        previo['_presente'] = 1
        unido = actual.merge(previo, on=['numero_de_cliente', '_mes'], how='left',
                             sort=False, validate='one_to_one')
        pasados.append(unido[fuentes].reset_index(drop=True))
        coberturas.append(unido['_presente'].fillna(0).to_numpy())
    for c in HISTORICAS_EXTRA:
        anterior = pasados[0][c].to_numpy()
        out['lag_1_' + c] = anterior
        out['delta_1_' + c] = out[c] - anterior
    for c in fuentes:
        denominador = pd.Series(pasados[0][c].abs().to_numpy(), index=out.index)
        out['variacion_relativa_1_' + c] = ratio_seguro(out[c] - out['lag_1_' + c], denominador)
    out['historial_meses_previos_3'] = np.sum(coberturas, axis=0).astype(int)
    for c in HISTORICAS:
        valores = pd.concat([p[c] for p in pasados], axis=1)
        media = valores.mean(axis=1).to_numpy()
        out['media_previa_3_' + c] = media
        out['delta_media_previa_3_' + c] = out[c] - media
        out['observaciones_previas_3_' + c] = valores.notna().sum(axis=1).to_numpy()
    return out


def ratio_seguro(numerador, denominador):
    """NaN si falta una fuente, el denominador es <= 0 o resulta infinito."""
    return (numerador / denominador.where(denominador > 0)).replace(
        [np.inf, -np.inf], np.nan)


def agregar_intrames(x, bloques):
    """Conserva originales e índice. Los nulos no se convierten en ceros.

    Sumas de tarjetas estrictas: un componente desconocido deja total NaN.
    Canales: si alguno es desconocido, el conteo total es desconocido.
    No se normalizan ratios a [0,1]: exceder el límite puede ser información.
    """
    if set(bloques) - BLOQUES.keys():
        raise ValueError('Bloque intrames desconocido.')
    nuevas = [c for b in bloques for c in BLOQUES[b]]
    if set(nuevas) & set(x.columns):
        raise ValueError('Las features ya existen; no sobrescribirlas.')
    out = x.copy()
    if 'actividad' in bloques:
        out['actividad_por_producto'] = ratio_seguro(x.ctrx_quarter, x.cproductos)
        uso = x[CANALES].gt(0).astype(float).where(x[CANALES].notna())
        out['cantidad_canales_activos'] = uso.sum(axis=1, min_count=len(CANALES))
    if 'tarjetas' in bloques:
        for fuente, destino in [('msaldototal', 'saldo'), ('mconsumototal', 'consumo'),
                                ('mlimitecompra', 'limite')]:
            out[f'tarjetas_{destino}_total'] = x[f'Visa_{fuente}'] + x[f'Master_{fuente}']
    if 'utilizacion' in bloques:
        for marca in ['Visa', 'Master']:
            for fuente, destino in [('msaldototal', 'saldo'), ('mconsumototal', 'consumo')]:
                out[f'{marca}_{destino}_sobre_limite'] = ratio_seguro(
                    x[f'{marca}_{fuente}'], x[f'{marca}_mlimitecompra'])
    return out


def agregar_historicas(datos):
    """Lag de un mes calendario y delta actual-anterior de cuatro variables.

    El argumento debe incluir historia auxiliar (por ejemplo abril para mayo).
    Conserva orden e índice. No hace shift por registro ni usa el target.
    No se usa todavía en el baseline: marzo no tiene febrero en el dataset.
    """
    keys = ['numero_de_cliente', 'foto_mes']
    if datos[keys].isna().any().any() or datos.duplicated(keys).any():
        raise ValueError('Claves incompletas o duplicadas.')
    meses = pd.to_datetime(datos.foto_mes.astype(str), format='%Y%m', errors='raise')
    numero_mes = meses.dt.year * 12 + meses.dt.month
    anterior = datos[['numero_de_cliente', *HISTORICAS]].copy()
    anterior['_mes'] = numero_mes.to_numpy() + 1
    anterior['historial_mes_anterior_disponible'] = 1
    anterior = anterior.rename(columns={c: 'lag_1_' + c for c in HISTORICAS})
    actual = datos[['numero_de_cliente']].copy()
    actual['_mes'] = numero_mes.to_numpy()
    unidos = actual.merge(anterior, on=['numero_de_cliente', '_mes'], how='left',
                           sort=False, validate='one_to_one')
    out = datos.copy()
    for c in HISTORICAS:
        lag = 'lag_1_' + c
        if lag in out or 'delta_1_' + c in out:
            raise ValueError('Las features históricas ya existen.')
        out[lag] = unidos[lag].to_numpy()
        out['delta_1_' + c] = out[c] - out[lag]
    out['historial_mes_anterior_disponible'] = unidos[
        'historial_mes_anterior_disponible'].fillna(0).astype(int).to_numpy()
    return out
