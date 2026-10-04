"""Auditoría local de las 202 features. No elimina columnas ni llama a la API.

Detecta en abril; mayo solo describe estabilidad, sin usar sus etiquetas.
"""
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from baseline import preparar

ROOT = Path(__file__).resolve().parents[1]


def perfil(x):
    return pd.DataFrame({'no_nulos': x.notna().sum(),
                         'faltantes_pct': x.isna().mean() * 100,
                         'valores_distintos_sin_nulos': x.nunique(dropna=True),
                         'valores_distintos_con_nulos': x.nunique(dropna=False)})


def duplicadas(x):
    # Hash solo agrupa candidatos; igualdad exacta confirma valores y faltantes.
    grupos = {}
    for c in x:
        digest = hashlib.sha256(pd.util.hash_pandas_object(x[c], index=False).values.tobytes()).hexdigest()
        grupos.setdefault(digest, []).append(c)
    pares = []
    for grupo in grupos.values():
        for i, a in enumerate(grupo):
            for b in grupo[i + 1:]:
                if x[a].equals(x[b]):
                    pares.append((a, b))
    return pares


def main():
    carpeta = ROOT / 'tp_primera_entrega'
    spec = importlib.util.spec_from_file_location('historia_tabpfn', carpeta / '11_tabpfn_historicas.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    config = json.loads((carpeta / 'config.json').read_text(encoding='utf-8'))
    _, train, valid, originales, nuevas = modulo.preparar_experimento(ROOT, config, 'ampliadas')
    columnas = originales + nuevas
    xt, _ = preparar(train, columnas)
    xv, _ = preparar(valid, columnas)
    pt, pv = perfil(xt), perfil(xv)
    reporte = pt.add_suffix('_abril').join(pv.add_suffix('_mayo'))
    reporte['historica'] = reporte.index.isin(nuevas)
    reporte['vacia_abril'] = reporte.no_nulos_abril.eq(0)
    reporte['constante_abril_incluye_faltantes'] = reporte.valores_distintos_con_nulos_abril.eq(1)
    reporte['constante_no_nula_con_faltantes_abril'] = (
        reporte.valores_distintos_sin_nulos_abril.eq(1)
        & reporte.valores_distintos_con_nulos_abril.gt(1))
    pares = duplicadas(xt)
    detalle = []
    for a, b in pares:
        detalle.append(dict(columna_a=a, columna_b=b,
                            iguales_mayo=xv[a].equals(xv[b]),
                            incluye_historica=a in nuevas or b in nuevas))
    out = ROOT / config['salidas'] / datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('auditoria_features_%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True)
    reporte.to_csv(out / 'perfil_columnas.csv', index_label='variable')
    pd.DataFrame(detalle, columns=['columna_a','columna_b','iguales_mayo','incluye_historica']).to_csv(out / 'duplicadas_abril.csv', index=False)
    resumen = dict(features=len(columnas), filas_abril=len(xt), filas_mayo=len(xv),
        vacias_abril=reporte.index[reporte.vacia_abril].tolist(),
        constantes_abril=reporte.index[reporte.constante_abril_incluye_faltantes & ~reporte.vacia_abril].tolist(),
        valor_constante_con_faltantes_abril=reporte.index[reporte.constante_no_nula_con_faltantes_abril].tolist(),
        pares_duplicados_abril=detalle, columnas_eliminadas=[], llamadas_api=0,
        criterio='Detectar con abril; mayo solo describe estabilidad, sin etiquetas. No se decide eliminar automáticamente.',
        notas='Duplicación en abril puede desaparecer en mayo por distinta historia disponible. No inferir irrelevancia predictiva por este diagnóstico.')
    (out / 'resumen.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding='utf-8')
    lineas = ['# Auditoría local de features TabPFN', '',
        f'{len(columnas)} variables; {len(xt):,} filas de abril y {len(xv):,} de mayo.', '',
        'No se eliminaron columnas ni se ejecutaron llamadas API. No se usaron etiquetas para seleccionar features.', '',
        '## Vacías en abril', '', ', '.join(resumen['vacias_abril']) or 'Ninguna.', '',
        '## Constantes en abril, incluidos faltantes', '', ', '.join(resumen['constantes_abril']) or 'Ninguna.', '',
        '## Duplicadas exactas en abril', '',
        '| Columna A | Columna B | También iguales en mayo |', '|---|---|---|']
    lineas += [f"| {d['columna_a']} | {d['columna_b']} | {'Sí' if d['iguales_mayo'] else 'No'} |" for d in detalle]
    lineas += ['', '## Interpretación', '',
        'Las constantes y duplicadas son hallazgos descriptivos, no evidencia de que quitarlas mejore la ganancia. Las variables con valor observado constante y faltantes pueden informar por su patrón de ausencia.', '',
        'Con un solo mes previo en abril, medias y lags pueden coincidir; en mayo hay dos meses previos y esa igualdad puede desaparecer. Mantener las 202 variables hasta definir y validar una alternativa. No eliminar automáticamente por correlación o falta de variación en un único mes.']
    (out / 'informe.md').write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in resumen.items() if k != 'pares_duplicados_abril'}, ensure_ascii=False, indent=2))
    print('Pares duplicados:', len(detalle), '; cambian en mayo:', sum(not d['iguales_mayo'] for d in detalle))
    print('Informe:', out)


if __name__ == '__main__':
    main()
