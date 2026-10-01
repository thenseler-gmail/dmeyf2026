"""Asociación de mpayroll con mantenimiento: corte mensual y cambios individuales.

Referencia CONTINUA = toda la cartera con ese target en la fila del mes.
No se utiliza la muestra balanceada de fieles.
"""
import numpy as np
import pandas as pd
import duckdb
from validacion_clusters_k5_th import ROOT, OUT, ID, MONTH, TARGET, save
from z501_cluster_rf_th import cargar_diccionario


def main():
    d=cargar_diccionario(ROOT/'dmeyf2026-9c6f_DiccionarioDatos_2026.ods')
    definitions=['mpayroll','mpayroll2','cpayroll_trx','mcomisiones_mantenimiento','mcomisiones']
    save([{'variable':v,'definicion_oficial':d[v]} for v in definitions],'haberes_definiciones')
    con=duckdb.connect()
    con.register('asignaciones',pd.read_csv(OUT/'asignaciones_clientes.csv'))
    print('Leyendo haberes y comisiones de toda la cartera...',flush=True)
    con.execute(f'''CREATE TABLE cartera AS SELECT CAST(r.{ID} AS BIGINT) {ID}, r.{MONTH}, r.{TARGET},
        r.mpayroll, r.mpayroll2, r.cpayroll_trx, r.mcomisiones_mantenimiento, a.cluster,
        CAST(r.{MONTH}//100 AS INTEGER)*12 + r.{MONTH}%100 AS ordinal,
        CASE WHEN r.mpayroll IS NULL THEN 'FALTANTE' WHEN r.mpayroll>0 THEN 'CON_MPAYROLL'
             WHEN r.mpayroll=0 THEN 'SIN_MPAYROLL' ELSE 'MPAYROLL_NEGATIVO' END grupo_haberes
        FROM read_csv(?,sample_size=-1) r LEFT JOIN asignaciones a ON CAST(r.{ID} AS BIGINT)=a.{ID}''',
        [str(ROOT/'data/competencia_01.csv')])
    con.execute('''CREATE VIEW poblaciones AS
        SELECT *, 'cohorte_alguna_vez_BAJA2' poblacion, cluster grupo_cluster FROM cartera WHERE cluster IS NOT NULL
        UNION ALL SELECT *, 'CONTINUA_cartera' poblacion, 0 grupo_cluster FROM cartera
        WHERE clase_ternaria='CONTINUA' AND foto_mes BETWEEN 202103 AND 202106''')
    dims='poblacion, grupo_cluster, foto_mes, grupo_haberes'
    summary=con.sql(f'''SELECT {dims}, COUNT(*) n_clientes, COUNT(mcomisiones_mantenimiento) n_mantenimiento_valido,
        COUNT(*) FILTER(WHERE mcomisiones_mantenimiento IS NULL) n_mantenimiento_faltante,
        COUNT(*) FILTER(WHERE mcomisiones_mantenimiento=0) n_mantenimiento_cero,
        COUNT(*) FILTER(WHERE mcomisiones_mantenimiento<0) n_mantenimiento_negativo,
        AVG(mcomisiones_mantenimiento) media_mantenimiento, MEDIAN(mcomisiones_mantenimiento) mediana_mantenimiento,
        COUNT(*) FILTER(WHERE mpayroll2>0) n_mpayroll2_positivo,
        COUNT(*) FILTER(WHERE cpayroll_trx>0) n_cpayroll_trx_positivo,
        COUNT(*) FILTER(WHERE mpayroll2 IS NULL) n_mpayroll2_faltante
        FROM poblaciones GROUP BY {dims} ORDER BY {dims}''').df()
    summary['pct_cero_entre_validos']=100*summary.n_mantenimiento_cero/summary.n_mantenimiento_valido.replace(0,np.nan)
    summary['pct_cero_del_grupo']=100*summary.n_mantenimiento_cero/summary.n_clientes
    summary['pct_mantenimiento_faltante']=100*summary.n_mantenimiento_faltante/summary.n_clientes
    # Mostrar también grupos de haberes vacíos, con n=0 y porcentajes no definidos.
    group_keys=summary[['poblacion','grupo_cluster','foto_mes']].drop_duplicates()
    all_groups=group_keys.merge(pd.DataFrame({'grupo_haberes':['CON_MPAYROLL','SIN_MPAYROLL','MPAYROLL_NEGATIVO','FALTANTE']}),how='cross')
    summary=all_groups.merge(summary,on=['poblacion','grupo_cluster','foto_mes','grupo_haberes'],how='left')
    for c in summary:
        if c.startswith('n_'): summary[c]=summary[c].fillna(0).astype(int)
    save(summary,'haberes_mantenimiento_mensual')
    # La composición de targets de cada corte de la cohorte permanece auditable.
    status=con.sql('''SELECT poblacion, grupo_cluster, foto_mes, grupo_haberes,
        COALESCE(clase_ternaria,'SIN_TARGET') clase_fila, COUNT(*) n FROM poblaciones GROUP BY ALL ORDER BY ALL''').df()
    save(status,'haberes_mantenimiento_composicion_target')
    contrast=summary[summary.grupo_haberes.eq('CON_MPAYROLL')].merge(summary[summary.grupo_haberes.eq('SIN_MPAYROLL')],
        on=['poblacion','grupo_cluster','foto_mes'],suffixes=('_con','_sin'))
    contrast['diferencia_pct_cero_pp']=contrast.pct_cero_entre_validos_con-contrast.pct_cero_entre_validos_sin
    contrast['diferencia_media']=contrast.media_mantenimiento_con-contrast.media_mantenimiento_sin
    contrast['diferencia_mediana']=contrast.mediana_mantenimiento_con-contrast.mediana_mantenimiento_sin
    save(contrast,'haberes_mantenimiento_contraste_mensual')
    # Transiciones solo entre meses calendario consecutivos del mismo cliente.
    con.execute(f'''CREATE TABLE transiciones AS
        SELECT t.{ID}, t.cluster, t.foto_mes mes_t, t.clase_ternaria clase_t,
            b.foto_mes mes_previo, b.clase_ternaria clase_previa, n.foto_mes mes_siguiente, n.clase_ternaria clase_siguiente,
            b.mpayroll payroll_previo, t.mpayroll payroll_t, n.mpayroll payroll_siguiente,
            b.mcomisiones_mantenimiento mantenimiento_previo, t.mcomisiones_mantenimiento mantenimiento_t,
            n.mcomisiones_mantenimiento mantenimiento_siguiente,
            CASE WHEN b.mpayroll IS NULL OR t.mpayroll IS NULL THEN 'NO_EVALUABLE_FALTANTES'
                 WHEN b.mpayroll<0 OR t.mpayroll<0 THEN 'NO_EVALUABLE_NEGATIVOS'
                 WHEN b.mpayroll=0 AND t.mpayroll>0 THEN 'EMPIEZA'
                 WHEN b.mpayroll>0 AND t.mpayroll=0 THEN 'DEJA'
                 WHEN b.mpayroll>0 AND t.mpayroll>0 THEN 'SIGUE_CON'
                 ELSE 'SIGUE_SIN' END transicion
        FROM cartera t JOIN cartera b ON t.{ID}=b.{ID} AND t.ordinal=b.ordinal+1
        LEFT JOIN cartera n ON t.{ID}=n.{ID} AND n.ordinal=t.ordinal+1''')
    con.execute('''CREATE VIEW transiciones_poblaciones AS
        SELECT *, 'cohorte_alguna_vez_BAJA2' poblacion, cluster grupo_cluster FROM transiciones WHERE cluster IS NOT NULL
        UNION ALL SELECT *, 'CONTINUA_en_mes_t' poblacion, 0 grupo_cluster FROM transiciones
        WHERE clase_t='CONTINUA' AND mes_t BETWEEN 202103 AND 202106''')
    audit=con.sql('''SELECT poblacion, grupo_cluster, mes_t, transicion, COUNT(*) n_eventos,
                    COUNT(DISTINCT numero_de_cliente) n_clientes, COUNT(mes_siguiente) n_con_foto_siguiente
                    FROM transiciones_poblaciones GROUP BY ALL ORDER BY ALL''').df()
    save(audit,'haberes_transiciones_cobertura')
    events=con.sql('''SELECT * FROM transiciones_poblaciones WHERE transicion IN ('EMPIEZA','DEJA') ORDER BY poblacion,grupo_cluster,numero_de_cliente,mes_t''').df()
    events['persistencia_mes_siguiente']=np.where(events.payroll_siguiente.isna(),'SIN_DATO',np.where(events.payroll_siguiente<0,'NEGATIVO',
        np.where((events.transicion.eq('EMPIEZA')&events.payroll_siguiente.gt(0))|(events.transicion.eq('DEJA')&events.payroll_siguiente.eq(0)),
                 'PERSISTE','REVIERTE')))
    save(events,'haberes_transiciones_eventos')
    # Cada contraste usa exactamente las mismas personas con ambos mantenimientos conocidos.
    contrasts=[]
    for a,b in [('previo','t'),('t','siguiente'),('previo','siguiente')]:
        x='mantenimiento_'+a; y='mantenimiento_'+b
        q=con.sql(f'''SELECT poblacion, grupo_cluster, mes_t, transicion, COUNT(*) n_eventos,
            COUNT(DISTINCT numero_de_cliente) n_clientes,
            COUNT(*) FILTER(WHERE {x} IS NOT NULL AND {y} IS NOT NULL) n_pares_validos,
            AVG({x}) FILTER(WHERE {x} IS NOT NULL AND {y} IS NOT NULL) media_a,
            AVG({y}) FILTER(WHERE {x} IS NOT NULL AND {y} IS NOT NULL) media_b,
            MEDIAN({x}) FILTER(WHERE {x} IS NOT NULL AND {y} IS NOT NULL) mediana_a,
            MEDIAN({y}) FILTER(WHERE {x} IS NOT NULL AND {y} IS NOT NULL) mediana_b,
            AVG({y}-{x}) media_cambio, MEDIAN({y}-{x}) mediana_cambio,
            COUNT(*) FILTER(WHERE {x} IS NOT NULL AND {y}=0) n_cero_b,
            COUNT(*) FILTER(WHERE {y} IS NOT NULL AND {x}=0) n_cero_a,
            COUNT(*) FILTER(WHERE {y}>{x}) n_aumenta, COUNT(*) FILTER(WHERE {y}<{x}) n_disminuye,
            COUNT(*) FILTER(WHERE {y}={x}) n_igual
            FROM transiciones_poblaciones GROUP BY poblacion,grupo_cluster,mes_t,transicion ORDER BY ALL''').df()
        q['momento_a']=a; q['momento_b']=b
        for col,new in [('n_cero_a','pct_cero_a'),('n_cero_b','pct_cero_b'),('n_aumenta','pct_aumenta'),('n_disminuye','pct_disminuye')]:
            q[new]=100*q[col]/q.n_pares_validos.replace(0,np.nan)
        contrasts.append(q)
    paired=pd.concat(contrasts,ignore_index=True)
    save(paired,'haberes_mantenimiento_cambios_pareados')
    # Panel con los tres importes observados: misma cohorte en t-1, t y t+1.
    complete=events.dropna(subset=['mantenimiento_previo','mantenimiento_t','mantenimiento_siguiente'])
    panels=[]
    for keys,g in complete.groupby(['poblacion','grupo_cluster','mes_t','transicion','persistencia_mes_siguiente']):
        for col in ['previo','t','siguiente']:
            s=g['mantenimiento_'+col]
            panels.append(dict(zip(['poblacion','grupo_cluster','mes_t','transicion','persistencia_mes_siguiente'],keys))|
                 {'momento':col,'n_eventos':len(g),'n_clientes':g.numero_de_cliente.nunique(),'media':s.mean(),
                  'mediana':s.median(),'n_cero':s.eq(0).sum(),'pct_cero':100*s.eq(0).mean()})
    save(panels,'haberes_mantenimiento_panel_tres_meses')
    assert (summary.n_mantenimiento_valido+summary.n_mantenimiento_faltante).eq(summary.n_clientes).all()
    assert (paired.n_pares_validos==paired.n_aumenta+paired.n_disminuye+paired.n_igual).all()
    def f(x,dec=2):
        if pd.isna(x): return 'n.a.'
        return f'{x:,.{dec}f}'.replace(',','_').replace('.',',').replace('_','.')
    ref=summary[summary.poblacion.eq('CONTINUA_cartera')&summary.grupo_haberes.isin(['CON_MPAYROLL','SIN_MPAYROLL'])]
    reference_rows=[]
    for _,r in ref.iterrows():
        reference_rows.append(f"| {r.foto_mes} | {'>0' if r.grupo_haberes=='CON_MPAYROLL' else '=0'} | {f(r.n_clientes,0)} | {f(r.pct_cero_entre_validos)}% | ${f(r.media_mantenimiento)} | ${f(r.mediana_mantenimiento)} | {f(r.n_mantenimiento_negativo,0)} |")
    cluster_rows=[]
    for _,r in contrast[contrast.poblacion.eq('cohorte_alguna_vez_BAJA2')&contrast.foto_mes.eq(202106)].iterrows():
        cluster_rows.append(f"| C{int(r.grupo_cluster)} | {int(r.n_clientes_con)} | {int(r.n_clientes_sin)} | {f(r.pct_cero_entre_validos_con)}% | {f(r.pct_cero_entre_validos_sin)}% | ${f(r.media_mantenimiento_con)} / ${f(r.media_mantenimiento_sin)} | ${f(r.mediana_mantenimiento_con)} / ${f(r.mediana_mantenimiento_sin)} |")
    reference_pair=paired[paired.poblacion.eq('CONTINUA_en_mes_t')&paired.transicion.isin(['EMPIEZA','DEJA'])&paired.momento_a.eq('previo')&paired.momento_b.eq('siguiente')]
    transition_rows=[]
    for _,r in reference_pair.iterrows():
        middle=paired[paired.poblacion.eq(r.poblacion)&paired.mes_t.eq(r.mes_t)&paired.transicion.eq(r.transicion)&paired.momento_a.eq('previo')&paired.momento_b.eq('t')].iloc[0]
        transition_rows.append(f"| {r.mes_t} | {r.transicion} | {int(r.n_pares_validos)} | {f(r.pct_cero_a)}% | {f(middle.pct_cero_b)}% | {f(r.pct_cero_b)}% | ${f(r.media_a)} → ${f(middle.media_b)} → ${f(r.media_b)} |")
    coverage=events.groupby(['poblacion','grupo_cluster','transicion']).agg(n_eventos=(ID,'size'),n_clientes=(ID,'nunique'),n_siguiente=('mes_siguiente','count')).reset_index()
    save(coverage,'haberes_transiciones_clientes_unicos')
    report=f'''# Haberes y comisión de mantenimiento

## Resultado

Hay una **asociación descriptiva fuerte en CONTINUA**: en marzo-junio, el mantenimiento es cero para aproximadamente 96% de las filas con `mpayroll>0`, frente a 32–37% con `mpayroll=0`. Dentro de los clusters de bajas la asociación es heterogénea y a menudo hay muy pocos clientes con acreditación. La evolución al empezar o dejar de acreditar no muestra una regla inmediata y universal. **No demuestra una condición contractual de bonificación**.

## Definiciones verificadas

- `mpayroll`: monto mensual acreditado por empleadores “acreditados”, en pesos. No abarca necesariamente todas las fuentes de ingresos ni toda acreditación salarial posible.
- `mpayroll2`: monto mensual acreditado fuera de archivo por esos empleadores, registrado por separado.
- `cpayroll_trx`: número de acreditaciones de haberes de empresas con contrato con el banco; pueden existir varias por empleado y mes.
- `mcomisiones_mantenimiento`: monto total de las comisiones de mantenimiento **de productos** cobradas durante el mes, en pesos. No es necesariamente el precio de un único paquete, ni un indicador de condición contractual.
- `mcomisiones` es el total más amplio de comisiones y no se utiliza como sustituto de mantenimiento.

Fuente: diccionario oficial 2026, hoja Diccionario. El texto exacto está en `haberes_definiciones.csv`. El diccionario no establece aquí un umbral salarial, una exención, un plazo de aplicación ni una regla que vincule ambas variables.

## Poblaciones y faltantes

La comparación principal usa **con acreditación en mpayroll = mpayroll>0** y **sin acreditación en mpayroll = mpayroll=0**. Los negativos y faltantes de mpayroll son grupos distintos. No se interpreta cero como ausencia de cualquier ingreso. La tabla informa también cuántos registros tienen `mpayroll2>0` o `cpayroll_trx>0`.

Para los clusters se utilizan todos sus clientes presentes **en cada mes de marzo a agosto**, con target de fila documentado por separado. La referencia son **todas las filas CONTINUA del mismo mes calendario** de marzo a junio; no la muestra de 4.067 fieles. Para julio/agosto no hay una referencia CONTINUA identificable en el archivo, por lo que no se imputa ni se extrapola.

En estas poblaciones no se observaron faltantes de `mpayroll` ni de mantenimiento, ni mpayroll negativo. Se conservaron columnas y grupos de control con n=0. Los porcentajes de mantenimiento cero usan como denominador el número con mantenimiento válido dentro del grupo/mes; también se exporta el porcentaje sobre todo el grupo. Un grupo vacío tiene n=0 y porcentaje/media/mediana **no definidos**, no cero.

Hay mantenimientos negativos. Se preservan en medias y medianas y se cuentan por separado; **no se suman a mantenimiento cero**. El diccionario no permite concluir si son ajustes, reversos u otro mecanismo, por lo que no se les asigna esa causa.

## CONTINUA: comparación mensual de toda la referencia

| Mes | mpayroll | n válido | Mantenimiento cero | Media mantenimiento | Mediana | n mantenimiento negativo |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

Son cortes mensuales: una fila por persona presente en ese mes. No se agrupan todos los meses en una única media que sobrepondere a quienes tienen más historia. CONTINUA es el target de la fila, no la garantía de permanecer en el banco indefinidamente.

## Clusters: ejemplo de junio, con el mismo calendario

Los resultados completos para **cada mes y cada cluster** están en `haberes_mantenimiento_mensual.csv`; junio ilustra la heterogeneidad:

| Cluster | n con | n sin | % cero con | % cero sin | Media con / sin | Mediana con / sin |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(cluster_rows)}

En C1/junio los porcentajes de cero son parecidos aunque las medias difieren; no alcanza con mirar solo el promedio. C2 muestra una diferencia grande, pero no representa a todos los clusters. C4 no tiene observaciones con mpayroll positivo en junio y C5 tiene una: no hay base para generalizar un efecto en esos grupos. Las medias incluyen valores negativos, por eso se acompañan de mediana, frecuencia de cero y conteos.

## Cambios dentro del mismo cliente

Se unen únicamente **meses calendario consecutivos** del mismo ID. “EMPIEZA” significa mpayroll=0 en t−1 y >0 en t; “DEJA”, >0 en t−1 y =0 en t. No es necesariamente el primer alta o la baja definitiva de haberes de la vida del cliente. Se mide mantenimiento en t−1, t y t+1, sin rellenar meses ausentes.

La referencia dinámica incluye clientes con **target CONTINUA en t** (abril-junio), sin exigir que tengan ese target en t−1 o t+1. Se usa el mantenimiento observado en t+1, incluso julio, sin inventar su target. `clase_previa`, `clase_t` y `clase_siguiente` se exportan con cada evento. Los clusters conservan su pertenencia retrospectiva alguna vez BAJA+2. Las dos poblaciones pueden solaparse y no se suman.

Para cada comparación t−1/t, t/t+1 y t−1/t+1 se informan n de eventos, clientes únicos, n de pares válidos, media/mediana en ambos extremos, media/mediana del cambio individual y porcentajes que aumentan/disminuyen. El panel de tres meses exige las tres mediciones; separa si la nueva condición de mpayroll persiste o revierte en t+1. No se confunde una caída de la media por composición con un cambio dentro de las mismas personas.

Referencia CONTINUA en el mes de transición, panel con seguimiento:

| t | Transición | n pares t−1/t+1 | % cero t−1 | % cero t | % cero t+1 | Media t−1 → t → t+1 |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(transition_rows)}

Las medianas de mantenimiento de estos seis grupos son cero en los tres momentos. Al dejar de acreditar, la proporción de mantenimiento cero sigue alta, incluso en el mes siguiente; no aparece un salto general e inmediato a cobrar mantenimiento. Al empezar, el promedio suele caer, pero la frecuencia de cero no mejora de manera uniforme en el mismo mes y existen negativos: no equivale a observar una bonificación aplicada automáticamente. Los CSV permiten separar quienes mantienen el cambio de quienes revierten.

En los clusters hay eventos, pero con tamaños mucho menores, especialmente C4/C5. Algunas transiciones carecen de seguimiento porque el cliente deja de aparecer. No se interpreta esa ausencia como mantenimiento cero. Las tablas de cobertura documentan los casos perdidos; los resultados con seguimiento describen a los observados, no a todos los clientes que empezaron o dejaron de acreditar.

## Alcance de la conclusión

La asociación es compatible con varias explicaciones y el archivo no permite distinguirlas. No controla por productos, antigüedad, campañas, importes mínimos, políticas tarifarias u otras condiciones. Los controles estables (SIGUE_CON/SIGUE_SIN) se exportan para comparar la evolución del mismo calendario, pero no constituyen un diseño causal. Un mismo cliente puede generar varios eventos; las cifras mensuales son eventos de personas distintas dentro de ese mes, y los totales de eventos no deben confundirse con clientes únicos. La evidencia **no prueba una cláusula contractual ni causalidad**.

## Archivos

- `haberes_mantenimiento_mensual.csv`: cantidades, ceros, faltantes, negativos, media y mediana por población/cluster/mes/grupo.
- `haberes_mantenimiento_contraste_mensual.csv`: diferencias con menos sin; porcentajes expresados en puntos porcentuales.
- `haberes_mantenimiento_composicion_target.csv`: target de fila de cada corte.
- `haberes_transiciones_eventos.csv`: eventos individuales, observaciones previa/actual/siguiente y persistencia.
- `haberes_transiciones_cobertura.csv` y `haberes_transiciones_clientes_unicos.csv`: denominadores y seguimiento; no sumar poblaciones superpuestas.
- `haberes_mantenimiento_cambios_pareados.csv`: tres contrastes temporales, con pares válidos y controles estables.
- `haberes_mantenimiento_panel_tres_meses.csv`: mismo panel en los tres momentos, separado por persistencia/reversión.

Reproducción: `python dmeyf2026/monday/haberes_mantenimiento_k5_th.py`. Se lee directamente la cartera completa y se reutilizan solamente las asignaciones de cluster.
'''
    report=report.replace('n.a.%','n.a.').replace('$n.a.','n.a.')
    (OUT/'haberes_mantenimiento.md').write_text(report,encoding='utf-8')
    ev=ref[['poblacion','grupo_cluster','foto_mes','grupo_haberes','n_clientes','n_mantenimiento_cero','pct_cero_entre_validos','media_mantenimiento','mediana_mantenimiento']].copy()
    ev['afirmacion']='Asociación entre mpayroll positivo y mantenimiento cero en CONTINUA'
    ev['limitacion']='Corte mensual descriptivo; mantenimiento agregado de productos, no condición contractual demostrada.'
    save(ev,'tabla_evidencia_haberes')
    print('Tablas de asociación y transiciones exportadas.',flush=True)


if __name__=='__main__': main()
