"""Correcciones confirmadas para nuevas corridas; no modifica el dataset fuente.

Aplicar corregir_datos antes de construir lags/deltas. Para matrices finales,
usar preparar_corregido en lugar de baseline.preparar.
"""
import numpy as np


def corregir_datos(df):
    datos = df.copy()
    auditoria = {}
    if 'ccajas_depositos' in datos:
        if 'foto_mes' not in datos:
            raise ValueError('Se necesita foto_mes para corregir ccajas_depositos.')
        mayo = datos['foto_mes'].eq(202105)
        auditoria['ccajas_depositos_202105_valores_reemplazados'] = int(
            datos.loc[mayo, 'ccajas_depositos'].notna().sum()
        )
        auditoria['ccajas_depositos_202105_filas'] = int(mayo.sum())
        datos.loc[mayo, 'ccajas_depositos'] = np.nan
    return datos, auditoria


def preparar_corregido(df, features):
    from baseline import preparar
    datos, auditoria = corregir_datos(df)
    matriz, otras_reglas = preparar(datos, features)
    return matriz, {**otras_reglas, **auditoria}
