"""Compara target por fila y cohorte alguna vez BAJA+2 con toda la cartera.

Referencia primaria: todas las filas CONTINUA del mismo mes calendario,
en los meses con target completo. No usa los fieles balanceados del RF.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from validacion_clusters_k5_th import ROOT, OUT, KEY, BINARY, CATS, ID, MONTH, TARGET, save
from z501_cluster_rf_th import cargar_diccionario


def main():
    con=duckdb.connect()
    assignments=pd.read_csv(OUT/'asignaciones_clientes.csv')
    con.register('asignaciones',assignments)
    variables=list(dict.fromkeys(KEY+BINARY))
    columns=[ID,MONTH,TARGET]+list(dict.fromkeys(variables+CATS))
    cols=', '.join('r."'+c+'"' for c in columns)
    print('Leyendo cartera completa para referencia calendario...',flush=True)
    con.execute(f'''CREATE TABLE cartera AS SELECT {cols}, a.cluster,
        a.{ID} IS NOT NULL AS alguna_vez_BAJA2
        FROM read_csv(?, sample_size=-1) r LEFT JOIN asignaciones a
        ON CAST(r.{ID} AS BIGINT)=a.{ID}''',[str(ROOT/'data/competencia_01.csv')])
    check=con.sql(f'''SELECT COUNT(DISTINCT {ID}) n,
        COUNT(*) FILTER (WHERE NOT alguna_vez_BAJA2) sin_asignacion FROM cartera WHERE {TARGET}='BAJA+2' ''').df().iloc[0]
    assert check.n==4067 and check.sin_asignacion==0
    # Cada mes incluye filas sin target en su denominador; desconocido no equivale a CONTINUA.
    counts=con.sql(f'''SELECT {MONTH}, COALESCE({TARGET},'SIN_TARGET') clase_fila, count(*) n
                      FROM cartera GROUP BY ALL ORDER BY 1,2''').df()
    counts['n_cartera_mes']=counts.groupby(MONTH).n.transform('sum')
    counts['pct_cartera_mes']=100*counts.n/counts.n_cartera_mes
    missing=counts[counts.clase_fila.eq('SIN_TARGET')][MONTH].tolist()
    complete=sorted(set(counts[MONTH])-set(missing))
    assert complete==[202103,202104,202105,202106]
    counts['target_completo_mes']=counts[MONTH].isin(complete)
    counts['interpretacion']=np.where(counts.target_completo_mes,'Distribución de targets de filas de la cartera del mes',
        'Target incompleto: no estimar BAJA+2 ni CONTINUA a partir de faltantes')
    save(counts,'target_cartera_denominadores')
    crossed=con.sql(f'''SELECT {MONTH}, COALESCE({TARGET},'SIN_TARGET') clase_fila,
                       alguna_vez_BAJA2, count(*) n FROM cartera GROUP BY ALL ORDER BY 1,2,3''').df()
    crossed['n_cartera_mes']=crossed.groupby(MONTH).n.transform('sum')
    crossed['n_cohorte_mes']=crossed.groupby([MONTH,'alguna_vez_BAJA2']).n.transform('sum')
    crossed['n_clase_mes']=crossed.groupby([MONTH,'clase_fila']).n.transform('sum')
    crossed['pct_de_cartera_mes']=100*crossed.n/crossed.n_cartera_mes
    crossed['pct_dentro_cohorte_mes']=100*crossed.n/crossed.n_cohorte_mes
    crossed['pct_dentro_clase_mes']=100*crossed.n/crossed.n_clase_mes
    save(crossed,'target_fila_vs_cohorte_cliente')
    cluster_counts=con.sql(f'''SELECT {MONTH}, cluster, COALESCE({TARGET},'SIN_TARGET') clase_fila,
                        count(*) n FROM cartera WHERE alguna_vez_BAJA2 GROUP BY ALL ORDER BY 1,2,3''').df()
    cluster_counts['n_presentes_cluster_mes']=cluster_counts.groupby([MONTH,'cluster']).n.transform('sum')
    cluster_counts['pct_dentro_presentes_cluster_mes']=100*cluster_counts.n/cluster_counts.n_presentes_cluster_mes
    save(cluster_counts,'target_por_cluster_calendario')
    months=','.join(map(str,complete))
    # La cartera CONTINUA puede incluir futuros BAJA+2: es correcto para target de fila.
    # Referencia secundaria excluye los que alguna vez tienen BAJA+2 en la ventana observada.
    con.execute(f'''CREATE VIEW grupos AS
        SELECT *, 'cartera_por_target' poblacion, 0 cluster_comparacion FROM cartera WHERE {MONTH} IN ({months})
        UNION ALL
        SELECT *, 'cluster_en_BAJA2' poblacion, cluster cluster_comparacion FROM cartera
            WHERE {MONTH} IN ({months}) AND {TARGET}='BAJA+2'
        UNION ALL
        SELECT *, 'CONTINUA_sin_BAJA2_observada' poblacion, 0 cluster_comparacion FROM cartera
            WHERE {MONTH} IN ({months}) AND {TARGET}='CONTINUA' AND NOT alguna_vez_BAJA2''')
    dims=f'{MONTH}, poblacion, {TARGET}, cluster_comparacion'
    dictionary=cargar_diccionario(ROOT/'dmeyf2026-9c6f_DiccionarioDatos_2026.ods')
    records=[]
    for v in variables:
        q=con.sql(f'''SELECT {dims}, COUNT(*) n_poblacion, COUNT("{v}") n_validos,
            COUNT(*)-COUNT("{v}") n_faltantes, AVG("{v}") media,
            quantile_cont("{v}",0.25) p25, median("{v}") mediana,
            quantile_cont("{v}",0.75) p75, quantile_cont("{v}",0.9) p90,
            COUNT(*) FILTER(WHERE "{v}">0) n_positivo,
            COUNT(*) FILTER(WHERE "{v}"=1) n_uno
            FROM grupos GROUP BY {dims} ORDER BY {dims}''').df()
        q['variable']=v; q['descripcion']=dictionary[v]
        q['faltantes_pct']=100*q.n_faltantes/q.n_poblacion
        q['pct_positivo_validos']=100*q.n_positivo/q.n_validos.replace(0,np.nan)
        q['pct_uno_validos']=100*q.n_uno/q.n_validos.replace(0,np.nan) if v in BINARY else np.nan
        if v not in BINARY: q['n_uno']=np.nan
        records.append(q)
    profiles=pd.concat(records,ignore_index=True)
    save(profiles,'perfiles_target_cartera_calendario')
    categories=[]
    for v in CATS+['Visa_delinquency','Master_delinquency']:
        q=con.sql(f'''SELECT {dims}, CAST("{v}" AS VARCHAR) valor, COUNT(*) n FROM grupos
                     GROUP BY {dims}, "{v}" ORDER BY {dims}, "{v}"''').df()
        q['valor']=q.valor.fillna('FALTANTE')
        q['variable']=v
        q['n_poblacion']=q.groupby([MONTH,'poblacion',TARGET,'cluster_comparacion']).n.transform('sum')
        q['porcentaje']=100*q.n/q.n_poblacion
        categories.append(q)
    save(pd.concat(categories,ignore_index=True),'categorias_target_cartera_calendario')
    # Comparación de cada cluster en BAJA+2 contra cada target de TODA la cartera del MISMO mes.
    cl=profiles[profiles.poblacion.eq('cluster_en_BAJA2')]
    ref=profiles[profiles.poblacion.eq('cartera_por_target')]
    comparison=cl.merge(ref,on=[MONTH,'variable'],suffixes=('_cluster','_referencia'),validate='many_to_many')
    for metric in ['media','mediana','p25','p75','p90','pct_positivo_validos','faltantes_pct']:
        comparison['diferencia_'+metric]=comparison[metric+'_cluster']-comparison[metric+'_referencia']
    save(comparison,'comparacion_clusters_target_mismo_mes')
    # Estandarización de medias: peso de cada mes = clientes BAJA+2 del cluster en ese mes / total cluster.
    # No promedia medianas ni percentiles. Con faltantes, pondera por válidos del cluster de cada variable.
    standardized=[]
    for c in range(1,6):
        for v in variables:
            focal=cl[(cl.cluster_comparacion==c)&cl.variable.eq(v)].sort_values(MONTH)
            valid_total=focal.n_validos.sum()
            if not valid_total: continue
            weights=focal.n_validos/valid_total
            for reference in ['cartera_por_target','CONTINUA_sin_BAJA2_observada']:
                rr=profiles[(profiles.poblacion==reference)&profiles.variable.eq(v)&profiles[TARGET].eq('CONTINUA')].set_index(MONTH)
                rr=rr.loc[focal[MONTH]]
                assert rr.media.notna().all()
                mean_cluster=float(np.dot(weights,focal.media))
                mean_ref=float(np.dot(weights,rr.media))
                for i,(_,row) in enumerate(focal.iterrows()):
                    standardized.append({'cluster':c,'variable':v,'referencia':reference,
                        MONTH:int(row[MONTH]),'peso_mes':float(weights.iloc[i]),
                        'n_cluster_mes':int(row.n_poblacion),'n_validos_cluster_mes':int(row.n_validos),
                        'n_referencia_mes':int(rr.iloc[i].n_poblacion),'n_validos_referencia_mes':int(rr.iloc[i].n_validos),
                        'media_cluster_mes':row.media,'media_referencia_mes':rr.iloc[i].media,
                        'media_cluster_estandarizada':mean_cluster,'media_referencia_estandarizada':mean_ref,
                        'diferencia_media_estandarizada':mean_cluster-mean_ref})
    weights=pd.DataFrame(standardized)
    save(weights,'referencia_CONTINUA_pesos_y_medias')
    assert np.allclose(weights.groupby(['cluster','variable','referencia']).peso_mes.sum(),1)
    result=weights.drop_duplicates(['cluster','variable','referencia'])[['cluster','variable','referencia',
        'media_cluster_estandarizada','media_referencia_estandarizada','diferencia_media_estandarizada']]
    save(result,'comparacion_CONTINUA_estandarizada')
    # Gráfico 8: tasas de targets sobre toda la cartera, no sobre la muestra balanceada.
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for target,color in [('BAJA+1','#eb6834'),('BAJA+2','#2a78d6')]:
        q=counts[counts.clase_fila.eq(target)&counts.target_completo_mes].sort_values(MONTH)
        axes[0].plot(range(4),q.pct_cartera_mes,marker='o',label=target,color=color)
    totals=counts[counts.target_completo_mes].groupby(MONTH).n.sum()
    axes[0].set_xticks(range(4),[f'{m}\nn={totals[m]:,}' for m in complete],fontsize=8)
    axes[0].set_ylabel('% de filas de toda la cartera del mes'); axes[0].legend(frameon=False)
    axes[0].set_ylim(0,.9); axes[0].grid(axis='y',alpha=.2)
    tab=crossed[crossed.alguna_vez_BAJA2&crossed[MONTH].isin(complete)].pivot(index=MONTH,columns='clase_fila',values='pct_dentro_cohorte_mes').fillna(0)
    bottom=np.zeros(4)
    for target,color in [('CONTINUA','#1baf7a'),('BAJA+2','#2a78d6'),('BAJA+1','#eb6834')]:
        vals=tab[target].to_numpy()
        axes[1].bar(range(4),vals,bottom=bottom,label=target,color=color); bottom+=vals
    ncoh=crossed[crossed.alguna_vez_BAJA2&crossed[MONTH].isin(complete)].groupby(MONTH).n.sum()
    axes[1].set_xticks(range(4),[f'{m}\nn={ncoh[m]:,}' for m in complete],fontsize=8)
    axes[1].set_ylabel('% de presentes de la cohorte alguna vez BAJA+2'); axes[1].legend(frameon=False,fontsize=8)
    fig.suptitle('Target de la fila y pertenencia a la cohorte son conceptos distintos',x=.05,ha='left',fontsize=15,weight='bold')
    axes[0].set_title('Cartera completa: denominador poblacional',fontsize=11)
    axes[1].set_title('Cohorte seleccionada: composición de targets',fontsize=11)
    fig.text(.05,.025,'Marzo-junio de 2021: target completo. CONTINUA es el estado de esa fila, no la promesa de permanencia futura.',fontsize=9)
    fig.tight_layout(rect=(.02,.08,.98,.91),pad=2)
    for ext in ['png','svg','pdf']: fig.savefig(OUT/'graficos'/f'08_target_fila_y_cohorte.{ext}',dpi=180)
    plt.close(fig)
    rows=[]
    for month,g in counts[counts.target_completo_mes].groupby(MONTH):
        n=int(g.n_cartera_mes.iloc[0]); vals=g.set_index('clase_fila')
        rows.append(f"| {month} | {n:,} | {int(vals.loc['BAJA+1','n']):,} ({vals.loc['BAJA+1','pct_cartera_mes']:.4f}%) | {int(vals.loc['BAJA+2','n']):,} ({vals.loc['BAJA+2','pct_cartera_mes']:.4f}%) | {int(vals.loc['CONTINUA','n']):,} ({vals.loc['CONTINUA','pct_cartera_mes']:.4f}%) |")
    # Ejemplos auditables de la diferencia target/cohorte.
    first=crossed[crossed.foto_mes.eq(202103)&crossed.alguna_vez_BAJA2].set_index('clase_fila')
    sample=result[result.referencia.eq('cartera_por_target')&result.variable.isin(['ctrx_quarter','mprestamos_personales','mpayroll'])]
    examples=[]
    for _,r in sample.iterrows():
        examples.append(f"| C{int(r.cluster)} | {r.variable} | {r.media_cluster_estandarizada:,.2f} | {r.media_referencia_estandarizada:,.2f} |")
    report=f'''# Comparación con clase_ternaria y referencia de continuadores

## Dos conceptos distintos

`clase_ternaria` pertenece a una **fila cliente-mes**: BAJA+1, BAJA+2, CONTINUA o sin target conocido. `alguna_vez_BAJA2` pertenece al **cliente**: vale verdadero si tiene al menos una fila BAJA+2 durante la ventana observada. Los cinco clusters segmentan exclusivamente esta segunda cohorte, de 4.067 personas, usando toda su historia.

Por ejemplo, en marzo hay 4.044 clientes presentes de esa cohorte: **{int(first.loc['CONTINUA','n'])} filas CONTINUA y {int(first.loc['BAJA+2','n'])} BAJA+2**. Que una fila sea CONTINUA no impide que ese cliente tenga BAJA+2 en otro mes. No se asignan clusters retrospectivos a los demás clientes.

## Distribución de targets en toda la cartera

Denominador: todas las filas (una por cliente presente) del mes calendario, sin selección por resultado futuro ni muestreo. No se suman meses para construir una tasa por cliente: los clientes se repiten entre meses. Estos porcentajes describen la cartera incluida en el archivo, no clientes o productos ajenos a ese universo.

| Mes | Clientes presentes | BAJA+1 | BAJA+2 | CONTINUA |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

Julio tiene 164.348 filas: 1.103 BAJA+1 y 163.245 sin target; agosto tiene 164.647 filas, todas sin target. Se conservan en las tablas de auditoría, pero **no entran en la comparación BAJA+1/BAJA+2/CONTINUA con target completo**. La falta de BAJA+2 o CONTINUA en esos meses no significa tasa cero. No se renormalizan los pocos targets conocidos como si representaran al mes entero.

## Selección de la referencia

**Referencia primaria:** todas las filas CONTINUA de marzo, abril, mayo y junio, en el mismo mes calendario que la fila de baja comparada. No se exige permanecer los seis meses ni no tener bajas en otro momento; hacerlo introduciría una selección por permanencia futura. Por ello, esta referencia puede incluir clientes que luego o antes son BAJA+2. CONTINUA no significa “fiel permanente”.

**Referencia secundaria de sensibilidad:** filas CONTINUA del mismo mes excluyendo clientes con alguna BAJA+2 observada. Se etiqueta `CONTINUA_sin_BAJA2_observada`; no debe interpretarse como ausencia de bajas fuera de la ventana o ausencia de BAJA+1. Las dos referencias usan toda la población elegible, sin muestreo.

Los **4.067 fieles muestreados por el script original** sirven para entrenar el bosque. Son clientes presentes todos los meses y sin BAJA+1/BAJA+2 observada, seleccionados por hash/semilla y balanceados contra las bajas. **No representan toda la cartera ni se utilizan para ninguna tasa poblacional ni para la referencia primaria de este contraste.**

## Perfiles en meses equivalentes

`perfiles_target_cartera_calendario.csv` separa por mes los tres targets de toda la cartera, los miembros de cada cluster en su mes BAJA+2 y la referencia secundaria. Para cada variable incluye población, válidos, faltantes, media, mediana, P25, P75 y P90. Los estados de tarjetas, mora e internet están desglosados en `categorias_target_cartera_calendario.csv` con faltantes separados.

`comparacion_clusters_target_mismo_mes.csv` compara cada cluster **en BAJA+2** con BAJA+1, BAJA+2 total y CONTINUA del mismo mes. La comparación con BAJA+2 total tiene solapamiento deliberado: el cluster es un subconjunto de ese total. Los grupos BAJA+1 y BAJA+2 de un mismo mes contienen clientes distintos, por lo que esas diferencias son de perfil/composición, no cambios individuales.

Para resumir sin confundir calendario y perfil, `referencia_CONTINUA_pesos_y_medias.csv` hace explícitos los pesos: proporción de observaciones válidas BAJA+2 del cluster aportadas por cada mes para esa variable. Se aplica **el mismo peso mensual** a la media del cluster y a la media de CONTINUA. No se promedian medianas ni percentiles. Los faltantes y denominadores de cada mes se mantienen visibles; si su patrón difiere, las medias describen solo los valores observados.

Ejemplos de medias estandarizadas por calendario (pesos para variables monetarias, cantidad para movimientos):

| Cluster | Variable | Cluster en BAJA+2 | CONTINUA del mismo calendario |
|---|---|---:|---:|
{chr(10).join(examples)}

Los continuadores no están emparejados por edad, productos u otras características: se controla el mes, no todas las diferencias de composición. Un mismo continuador puede contribuir a varios meses, pero no se concatena toda su historia para obtener un promedio sin ponderación explícita. Esta estandarización representa una referencia cliente-mes según el calendario del cluster, no una muestra de clientes únicos de control. No se atribuyen causalidad, significancia estadística ni respuesta a retención.

## Archivos y denominadores

- `target_cartera_denominadores.csv`: n por target y denominador de toda la cartera del mes; indicador de target completo.
- `target_fila_vs_cohorte_cliente.csv`: cruza target de fila con pertenencia a la cohorte, con porcentajes sobre cartera mensual, cohorte presente y total de la clase.
- `target_por_cluster_calendario.csv`: composición BAJA+1/BAJA+2/CONTINUA/sin target entre presentes de cada cluster. **No son tasas poblacionales de baja**.
- `comparacion_CONTINUA_estandarizada.csv`: medias comparables por calendario con ambas referencias; sus pesos y n se conservan en la tabla detallada.
- Gráfico 8: denominadores poblacionales y de cohorte en paneles separados. Los siete gráficos anteriores mantienen sus poblaciones originales, indicadas en cada pie.

Reproducir con `python dmeyf2026/monday/comparacion_clase_ternaria_k5_th.py` después de generar las asignaciones. La referencia proviene directamente de `data/competencia_01.csv`, no de la muestra balanceada ni del CSV de historias segmentadas.
'''
    (OUT/'comparacion_clase_ternaria.md').write_text(report,encoding='utf-8')
    # Evidencia adicional, sin sobreescribir la validación anterior.
    evidence=[]
    for _,r in counts.iterrows():
        evidence.append({'afirmacion':'Distribución de target en cartera completa','variable':'clase_ternaria',
            'clase':r.clase_fila,'cifra':r.pct_cartera_mes,'unidad':'%','numerador':r.n,
            'denominador':r.n_cartera_mes,'poblacion':'Todas las filas de la cartera del mes',
            'momento':r[MONTH],'limitacion':r.interpretacion,'fuente':'target_cartera_denominadores.csv'})
    save(evidence,'tabla_evidencia_target')
    print('Comparación completa: referencia poblacional, calendario, pesos y denominadores exportados.',flush=True)


if __name__=='__main__': main()
