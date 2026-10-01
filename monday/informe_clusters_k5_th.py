"""Genera evidencia, informe Markdown y siete gráficos desde la validación k=5."""
from pathlib import Path
import json
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter
from validacion_clusters_k5_th import OUT, ID, MONTH, STATUS, flags, save

COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
FIG = OUT / "graficos"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
                     "axes.spines.right":False,"figure.facecolor":"white","savefig.facecolor":"white"})


def read(name):
    return pd.read_csv(OUT/f"{name}.csv")


def fmt(x, digits=2):
    return f"{x:,.{digits}f}".replace(",","_").replace(".",",").replace("_",".")


def main():
    h = read("historia_segmentada")
    s = read("observaciones_mes_baja2")
    prof = read("perfiles_baja2").set_index(["cluster","variable"])
    traits = read("rasgos_baja2").set_index(["cluster","rasgo"])
    cats = read("categorias_baja2")
    conc = read("concentracion_y_sensibilidad")
    stab = read("estabilidad_global")
    sg = read("estabilidad_por_cluster")
    losses = read("perdidas_pareadas_junio_julio")
    dec = read("rentabilidad_descomposicion_junio_julio")
    rec = read("recurrencia_visa_cliente")
    sizes = s.groupby("cluster").size()
    def stat(c,v,k="mediana"):
        return float(prof.loc[(c,v),k])
    def trait(c,v,k="pct_total"):
        return float(traits.loc[(c,v),k])

    # Evidencia de las afirmaciones: cifra, denominador, momento y limitación.
    evidence=[]
    def ev(claim,verdict,var,metric,value,unit,n,moment,limitation,source):
        evidence.append({"afirmacion":claim,"evaluacion":verdict,"variable":var,"metrica":metric,
                         "cifra":value,"unidad":unit,"n_poblacion":n,"momento":moment,
                         "limitacion":limitation,"tabla_fuente":source})
    for c,claim,verdict,var,metric in [
        (1,"C1 uso Visa y débitos sin haberes","Respaldada con matices","uso_visa","pct_total"),
        (1,"C1 uso Visa y débitos sin haberes","Respaldada con matices","debitos_visa","pct_total"),
        (1,"C1 uso Visa y débitos sin haberes","Respaldada con matices","sin_haberes","pct_total"),
        (1,"C1 uso Visa y débitos sin haberes","Respaldada con matices","C1_visa_debitos_sin_haberes","pct_total"),
        (2,"C2 relación amplia con haberes","Requiere matices","haberes","pct_total"),
        (2,"C2 relación amplia con haberes","Requiere matices","C2_relacion_amplia","pct_total"),
        (3,"C3 productos y límites con poco uso","Respaldada con matices","uso_visa","pct_total"),
        (3,"C3 productos y límites con poco uso","Respaldada con matices","C3_productos_limites_poco_uso","pct_total"),
        (4,"C4 poca actividad y tarjetas en cierre","Requiere matices; cierre mayoritario no respaldado","cierre_alguna_tarjeta","pct_total"),
        (4,"C4 poca actividad y tarjetas en cierre","Requiere matices; cierre mayoritario no respaldado","C4_baja_actividad_y_cierre","pct_total"),
        (4,"C4 poca actividad y tarjetas en cierre","Requiere matices; cierre mayoritario no respaldado","mora_alguna_tarjeta","pct_total"),
        (5,"C5 préstamos y rentabilidad particular","Respaldada con matices temporales","prestamos_positivos","pct_total"),
        (5,"C5 préstamos y rentabilidad particular","Respaldada con matices temporales","C5_prestamos_deuda_y_perdida","pct_total"),
    ]:
        ev(claim,verdict,var,metric,trait(c,var,metric),"%",sizes[c],f"C{c}, una observación por cliente en BAJA+2",
           "Porcentaje del total: desconocidos no se cuentan como cumplen; ver n_evaluables y n_desconocidos. Umbrales descriptivos, no regla validada.","rasgos_baja2.csv")
    for c,claim,verdict,variables in [
        (1,"C1 uso Visa y débitos sin haberes","Respaldada con matices",["mtarjeta_visa_consumo","mpayroll"]),
        (2,"C2 relación amplia con haberes","Requiere matices",["ctrx_quarter","mcuentas_saldo","mpayroll","mpagomiscuentas"]),
        (3,"C3 productos y límites con poco uso","Respaldada con matices",["cproductos","Visa_mlimitecompra","ctrx_quarter"]),
        (4,"C4 poca actividad y tarjetas en cierre","Requiere matices",["ctrx_quarter","mtarjeta_visa_consumo"]),
        (5,"C5 préstamos y rentabilidad particular","Respaldada con matices temporales",["cprestamos_personales","mprestamos_personales","mrentabilidad","mrentabilidad_annual"]),
    ]:
        for v in variables:
            for m in ["media","mediana","p90"]:
                ev(claim,verdict,v,m,stat(c,v,m),"pesos" if v.startswith("m") or "mlimite" in v else "cantidad",
                   int(prof.loc[(c,v),"n_validos"]),f"C{c}, BAJA+2","Estadística entre válidos; no combina filas de distintos meses del mismo cliente.","perfiles_baja2.csv")
    for v in ["Visa_status","Master_status"]:
        q=cats[(cats.cluster==4)&(cats.variable==v)&(cats.valor=="FALTANTE")].iloc[0]
        ev("C4 cierre de tarjetas","Cierre mayoritario no respaldado",v,"faltantes_pct",q.porcentaje,"%",559,"C4, BAJA+2",
           "Faltante no equivale a cerrada, abierta ni ausencia de producto.","categorias_baja2.csv")
    c5=conc[(conc.cluster==5)&conc.ambito.eq("baja2")].set_index("variable")
    for v in ["cprestamos_personales","mprestamos_personales"]:
        for m in ["p95","p99","maximo","top1_pct_total","top5_pct_total","mediana_sin_top5","media_sin_top5"]:
            ev("C5 préstamos robustos a extremos","Respaldada",v,m,c5.loc[v,m],"%" if "pct" in m else "pesos" if v.startswith("m") else "cantidad",223,"C5, BAJA+2",
               "Top 1%=3 clientes; top 5%=12. Se excluyen por variable, no se eliminan definitivamente.","concentracion_y_sensibilidad.csv")
    for _,r in losses[losses.cluster.eq(5)].iterrows():
        for m in ["rentabilidad_media","rentabilidad_mediana","pct_negativos","perdidas_top1_pct_total","perdidas_top5_pct_total"]:
            ev("C5 caída de rentabilidad en julio","Respaldada en cohorte pareada","mrentabilidad",m,r[m],"%" if "pct" in m else "pesos",150,
               f"C5, mismos 150 clientes, {int(r['mes'])}","No prueba causa. Las pérdidas son brutas; top 1%=2 y top 5%=8 del panel, incluyendo ceros.","perdidas_pareadas_junio_julio.csv")
    save(evidence,"tabla_evidencia")

    # Cohorte equilibrada: exactamente las mismas personas en -1, 0 y +1.
    w=h[h.mes_relativo.isin([-1,0,1])]
    ids=w.groupby(ID).mes_relativo.nunique()
    panel=w[w[ID].isin(ids[ids.eq(3)].index)]
    panel_summary=panel.groupby(["cluster","mes_relativo"]).agg(n=(ID,"size"),
         mediana_ctrx=("ctrx_quarter","median"),media_ctrx=("ctrx_quarter","mean"),
         mediana_rentabilidad=("mrentabilidad","median"),media_rentabilidad=("mrentabilidad","mean")).reset_index()
    save(panel_summary,"panel_equilibrado_relativo")
    onset=read("primer_cierre_por_cliente")
    onset4=onset[onset.cluster.eq(4)]
    onset_summary=onset4.groupby(["variable","primer_cierre_relativo","ya_cierre_primera_observacion_valida"],dropna=False).size().rename("n").reset_index()
    save(onset_summary,"c4_momento_primer_cierre")
    t=read("transiciones_tarjetas")
    tc=t[t.cluster.eq(4)].copy()
    tc["abierta_a_cierre"]=tc.estado_a.eq(0)&tc.estado_b.isin([6,7,9])
    tc["cierre_a_abierta"]=tc.estado_a.isin([6,7,9])&tc.estado_b.eq(0)
    save(tc.groupby(["variable","relativo_b"]).agg(n_pares=(ID,"size"),aperturas_a_cierre=("abierta_a_cierre","sum"),
         reaperturas=("cierre_a_abierta","sum")).reset_index(),"c4_transiciones_cierre")

    figures=[]
    def finish(fig,name,title,note):
        fig.suptitle(title,x=.06,ha="left",fontsize=17,fontweight="bold")
        fig.text(.06,.025,note,fontsize=9,color="#4b534e",va="bottom")
        fig.tight_layout(rect=(.04,.10,.98,.92),pad=2)
        fig.savefig(FIG/f"{name}.png",dpi=180)
        fig.savefig(FIG/f"{name}.svg")
        figures.append(fig)

    names={"uso_visa":"Uso de Visa", "debitos_visa":"Débitos automáticos Visa", "haberes":"Acreditación de haberes",
           "prestamos_positivos":"Préstamos personales > 0", "rentabilidad_negativa":"Rentabilidad negativa"}
    mat=traits.reset_index().pivot(index="rasgo",columns="cluster",values="pct_total").loc[list(names)]
    fig,ax=plt.subplots(figsize=(12,6))
    ax.imshow(mat,vmin=0,vmax=100,cmap="Blues",aspect="auto")
    ax.set_xticks(range(5),[f"C{i}\nn={sizes[i]:,}" for i in range(1,6)])
    ax.set_yticks(range(len(mat)),list(names.values()))
    for i in range(len(mat)):
        for j in range(5):
            v=mat.iloc[i,j]; ax.text(j,i,f"{v:.1f}%",ha="center",va="center",color="white" if v>55 else "#152332")
    finish(fig,"01_rasgos_baja2","Rasgos observados en el mes BAJA+2","Una fila por cliente. Porcentajes sobre el total del cluster; los faltantes no se imputan.")

    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,(v,title) in zip(axes.flat,[("ctrx_quarter","Movimientos voluntarios en 90 días"),("mcuentas_saldo","Saldo de cuentas (pesos)"),
                                     ("mtarjeta_visa_consumo","Consumo Visa mensual (pesos)"),("mprestamos_personales","Deuda en préstamos personales (pesos)")]):
        med=[stat(c,v) for c in range(1,6)]
        ax.bar(range(5),med,color=COLORS)
        ax.set_xticks(range(5),[f"C{i}" for i in range(1,6)])
        ax.set_title(title,fontsize=11)
        ax.axhline(0,color="#333333",lw=.6)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f"{x:,.0f}"))
        for i,value in enumerate(med):
            ax.annotate(f"{value:,.0f}",(i,value),xytext=(0,4 if value>=0 else -13),textcoords="offset points",ha="center",fontsize=9)
        ax.margins(y=.23)
    finish(fig,"02_medianas_baja2","Las medianas distinguen uso, saldos y deuda","Mes BAJA+2 de cada cliente. Valores originales, sin mezclar meses. Cantidades y pesos nominales de 2021.")

    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for ax,v in zip(axes,["Visa_status","Master_status"]):
        subset=cats[cats.variable.eq(v)].copy()
        cat=subset.pivot(index="cluster",columns="valor",values="porcentaje").reindex(index=range(1,6)).fillna(0)
        bottom=np.zeros(5)
        for code,label,color in [("0","Abierta","#2a78d6"),("6","En cierre","#eda100"),("7","Cierre avanzado","#eb6834"),("9","Cerrada","#af3145"),("FALTANTE","Sin dato","#d5d9dc")]:
            value=cat[code].values if code in cat else np.zeros(5)
            ax.bar(range(5),value,bottom=bottom,color=color,label=label); bottom+=value
        ax.set_xticks(range(5),[f"C{i}" for i in range(1,6)])
        ax.set_ylim(0,100); ax.set_ylabel("% del total del cluster"); ax.set_title(v)
    axes[1].legend(loc="upper center",bbox_to_anchor=(.5,-.10),ncol=3,fontsize=9,frameon=False)
    finish(fig,"03_estados_tarjetas","C4: predominan los estados de tarjeta sin dato","Mes BAJA+2. El cierre es un estado de cuenta; la mora se mide por delinquency en tablas separadas.")

    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for c,color in enumerate(COLORS,1):
        g=panel_summary[panel_summary.cluster.eq(c)]
        n=int(g.n.iloc[0])
        for ax,v in zip(axes,["mediana_ctrx","mediana_rentabilidad"]):
            ax.plot(g.mes_relativo,g[v],marker="o",color=color,label=f"C{c} (n={n})")
    for ax,title in zip(axes,["Mediana de movimientos en 90 días","Mediana de rentabilidad mensual (pesos)"]):
        ax.set_title(title,fontsize=11); ax.set_xticks([-1,0,1],["-1 mes","BAJA+2","+1 mes: BAJA+1"])
        ax.grid(axis="y",alpha=.2)
    axes[1].legend(fontsize=9,frameon=False)
    finish(fig,"04_evolucion_mismos_clientes","Evolución con una cohorte fija por cluster","Solo clientes presentes en los tres momentos. Cambios de mediana del panel; cambios individuales en cambios_pareados.csv.")

    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for c,color in enumerate(COLORS,1):
        g=s[s.cluster.eq(c)]
        x=np.sort(g.mprestamos_personales.dropna())
        axes[0].step(x,np.arange(1,len(x)+1)/len(x)*100,where="post",color=color,label=f"C{c}")
    axes[0].set_xscale("symlog",linthresh=1000)
    axes[0].set_xticks([0,1000,10000,100000,1000000],["0","1.000","10.000","100.000","1.000.000"])
    axes[0].set_xlabel("Deuda en pesos (escala simétrica logarítmica)")
    axes[0].set_ylabel("% acumulado de clientes"); axes[0].legend(frameon=False); axes[0].set_title("Distribución de deuda en BAJA+2")
    values=[c5.loc["mprestamos_personales","mediana"],c5.loc["mprestamos_personales","mediana_sin_top1"],c5.loc["mprestamos_personales","mediana_sin_top5"]]
    axes[1].bar(["Completo\nn=223","Sin top 1%\nn=220","Sin top 5%\nn=211"],values,color=COLORS[4])
    for i,v in enumerate(values): axes[1].text(i,v+3000,f"{v:,.0f}",ha="center")
    axes[1].set_ylim(0,max(values)*1.18); axes[1].set_title("C5: mediana de deuda sin los extremos"); axes[1].set_ylabel("Pesos")
    finish(fig,"05_prestamos_sensibilidad","El perfil de préstamos de C5 persiste sin los extremos","Exclusión temporal por ranking de deuda. Top 1%=3 clientes; top 5%=12. Sin modificaciones al dataset.")

    fig,axes=plt.subplots(1,3,figsize=(14,6))
    l=losses[losses.cluster.eq(5)].sort_values("mes")
    x=np.arange(2)
    axes[0].bar(x-.18,l.rentabilidad_media,.36,label="Media",color="#e87ba4")
    axes[0].bar(x+.18,l.rentabilidad_mediana,.36,label="Mediana",color="#8056b3")
    axes[0].axhline(0,color="black",lw=.7); axes[0].set_xticks(x,["Junio","Julio"]); axes[0].set_ylabel("Pesos"); axes[0].legend(frameon=False)
    axes[1].bar(x,l.pct_negativos,color=["#2a78d6","#eb6834"])
    axes[1].set_xticks(x,["Junio","Julio"]); axes[1].set_ylim(0,100); axes[1].set_ylabel("% con rentabilidad negativa")
    for i,v in enumerate(l.pct_negativos): axes[1].text(i,v+2,f"{v:.0f}%",ha="center")
    july=h[(h.cluster==5)&(h.foto_mes==202107)].set_index(ID).mrentabilidad
    june_ids=h[(h.cluster==5)&(h.foto_mes==202106)][ID]
    loss=(-july.loc[july.index.intersection(june_ids)]).clip(lower=0).sort_values(ascending=False)
    axes[2].plot(np.arange(1,len(loss)+1)/len(loss)*100,loss.cumsum()/loss.sum()*100,color="#e87ba4",lw=2)
    axes[2].set_xlabel("% de clientes, de mayor a menor pérdida"); axes[2].set_ylabel("% acumulado de pérdidas de julio")
    axes[2].set_xlim(0,100); axes[2].set_ylim(0,100); axes[2].grid(alpha=.2)
    finish(fig,"06_rentabilidad_pareada","C5: la caída de julio también ocurre en los mismos clientes","Panel junio-julio: 150 clientes. Pérdidas brutas = máximo(-rentabilidad, 0); no se compensan con ganancias.")

    stages=["kmeans_matriz_fija","bosque_muestra_fija","procedimiento_completo"]
    labels=["KMeans\nmatriz fija (10)","Bosque\nmuestra fija (3)","Procedimiento\ncompleto (3)"]
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for i,stage in enumerate(stages):
        vals=stab[stab.etapa.eq(stage)].ARI.to_numpy()
        axes[0].scatter(np.linspace(i-.12,i+.12,len(vals)),vals,color=COLORS[i],s=45)
    axes[0].set_xticks(range(3),labels); axes[0].set_ylim(0,1.03); axes[0].set_ylabel("ARI respecto de la corrida original"); axes[0].grid(axis="y",alpha=.2)
    hm=sg.groupby(["cluster_base","etapa"]).jaccard.mean().unstack().reindex(columns=stages)
    axes[1].imshow(hm,vmin=0,vmax=1,cmap="Blues",aspect="auto")
    axes[1].set_xticks(range(3),["KMeans","Bosque","Completo"]); axes[1].set_yticks(range(5),[f"C{i}" for i in range(1,6)])
    axes[1].set_title("Jaccard medio tras emparejar grupos",fontsize=11)
    for i in range(5):
        for j in range(3): axes[1].text(j,i,f"{hm.iloc[i,j]:.3f}",ha="center",va="center",color="white" if hm.iloc[i,j]>.55 else "black")
    finish(fig,"07_estabilidad","Estabilidad: separar KMeans, bosque y muestreo","Emparejamiento uno a uno por máxima intersección (Hungarian). ARI es invariante a los números de cluster.")
    with PdfPages(OUT/"graficos_comparativos_k5.pdf") as pdf:
        for fig in figures: pdf.savefig(fig); plt.close(fig)
        extra = FIG / "08_target_fila_y_cohorte.png"
        if extra.exists():
            fig = plt.figure(figsize=(12,6))
            ax = fig.add_axes([0,0,1,1])
            ax.imshow(plt.imread(extra)); ax.axis("off")
            pdf.savefig(fig); plt.close(fig)

    recurrence=rec[rec.cluster.eq(1)]
    r_n=int(recurrence.recurrente_sin_haberes_baja2.sum())
    eligible=int(recurrence.n_evaluables.ge(2).sum())
    st=stab.groupby("etapa").ARI.agg(["min","max"])
    july5=l[l.mes.eq(202107)].iloc[0]
    # Conteos de primer cierre: no confundir primera observación con inicio real.
    closure_text=[]
    for v in ["Visa_status","Master_status"]:
        q=onset4[onset4.variable.eq(v)]
        ever=int(q.alguna_vez_cierre.sum())
        cens=int(q.ya_cierre_primera_observacion_valida.sum())
        qtr=tc[tc.variable.eq(v)]
        closure_text.append(f"{v}: {ever}/559 tienen algún estado de cierre observado; en {cens} ya estaba presente en la primera observación válida. Hay {int(qtr.abierta_a_cierre.sum())} transiciones consecutivas abierta→cierre y {int(qtr.cierre_a_abierta.sum())} cierre→abierta.")
    concentration_text=[]
    for v,label in [("cprestamos_personales","Número de préstamos"),("mprestamos_personales","Deuda en pesos")]:
        r=c5.loc[v]
        concentration_text.append(f"| {label} | {fmt(r.mediana)} | {fmt(r.p90)} | {fmt(r.p99)} | {fmt(r.maximo)} | {fmt(r.top1_pct_total)}% | {fmt(r.top5_pct_total)}% | {fmt(r.mediana_sin_top5)} |")
    report=f'''# Validación de los cinco perfiles de clientes BAJA+2

## Resultado

La segmentación se reprodujo exactamente: **C1=1.281, C2=1.089, C3=915, C4=559 y C5=223** (4.067 clientes). K=5 sigue siendo una elección provisional: reproducibilidad y estabilidad no demuestran que sea el número óptimo ni que los grupos respondan a una acción comercial.

| Cluster | Clientes | % de las bajas | Descripción revisada |
|---|---:|---:|---|
| C1 | 1.281 | {fmt(1281/4067*100)}% | Uso de Visa y débitos automáticos, con escasa acreditación de haberes |
| C2 | 1.089 | {fmt(1089/4067*100)}% | Mayor actividad transaccional y saldos; haberes y relación amplia en subgrupos |
| C3 | 915 | {fmt(915/4067*100)}% | Productos y límites registrados, bajo uso efectivo de tarjetas |
| C4 | 559 | {fmt(559/4067*100)}% | Escaso uso, saldos negativos y datos de tarjetas mayormente faltantes |
| C5 | 223 | {fmt(223/4067*100)}% | Préstamos personales generalizados; fuerte deterioro de rentabilidad en julio |

## Población, tiempo y controles

- Fuente: `competencia_01.csv`, diccionario oficial `dmeyf2026-9c6f_DiccionarioDatos_2026.ods`, hoja Diccionario y consideraciones generales. Los hashes y versiones están en `metadatos.json`.
- El dataset tiene **983.061 filas, 169.727 clientes y cero claves cliente-mes duplicadas**.
- Parámetros originales: semilla 214363, RF de 300 árboles, mínimo de 50 observaciones por hoja, `max_features=sqrt`, pesos balanceados; KMeans con k=5 y 20 inicializaciones. Se conserva la implementación original.
- RF usa 4.067 clientes que alguna vez son BAJA+2 y 4.067 fieles: 38.713 filas. Los clusters se calculan solo para los 4.067 BAJA+2.
- Cada uno tiene **un único mes BAJA+2**. La historia usada por el bosque tiene 14.311 filas: 6.148 CONTINUA, 4.067 BAJA+2, **4.067 BAJA+1** y 29 sin target. Incluye observaciones posteriores a BAJA+2 y reapariciones.
- La cohorte está presente en marzo/agosto con 4.044, 4.059, 3.106, 1.975, 1.110 y **17** clientes, respectivamente. Los 17 de agosto reaparecieron después de su baja; ninguno tiene target conocido en agosto. **La exclusión automática de agosto no está justificada por ausencia de historia**. El PDF `_th` lo incluye y advierte su escasa representatividad.
- Tiempo relativo: 0=BAJA+2, +1=BAJA+1; −1 a −3 son meses previos. No hay observaciones en +2; las de +3 a +5 son reapariciones, no continuidad de una misma trayectoria. Los conteos por estado y cliente están exportados.
- Perfiles principales: una fila por cliente en BAJA+2. Las tablas mensuales y relativas nunca mezclan todos los cliente-mes en una sola media. BAJA+2 alinea la etapa, pero mezcla cohortes de marzo-junio: los importes son pesos nominales y no están ajustados por inflación.
- El bosque conoce la historia posterior al evento. Esta es una segmentación retrospectiva; **no valida un modelo predictivo previo a la baja ni identifica causas**. El OOB accuracy no se usa como validación de clusters.

## Qué se confirma y qué cambia

**C1 — respaldada con matices.** En BAJA+2, {fmt(trait(1,'uso_visa'))}% usa Visa, {fmt(trait(1,'debitos_visa'))}% tiene débitos automáticos Visa y {fmt(trait(1,'sin_haberes'))}% no registra haberes. Los tres rasgos aparecen simultáneamente en {int(trait(1,'C1_visa_debitos_sin_haberes','n_cumplen'))}/1.281 ({fmt(trait(1,'C1_visa_debitos_sin_haberes'))}%). Para hablar de recurrencia, {r_n}/1.281 ({fmt(r_n/1281*100)}%) tiene uso y débitos en al menos dos meses de la ventana [−2,0], además de no registrar haberes en BAJA+2; entre los {eligible} clientes con al menos dos meses evaluables representa {fmt(r_n/eligible*100)}%. La ventana incompleta limita esa comparación.

**C2 — requiere matices.** Mediana de 78 movimientos voluntarios en 90 días, frente a 26 en C1; saldo mediano de $16.562,87. La mayor actividad se refiere a los otros clusters de bajas, no a toda la cartera CONTINUA. Pero solo {fmt(trait(2,'haberes'))}% registra haberes y la mediana de `mpayroll` es cero. La combinación estricta de haberes, saldo positivo, uso de tarjetas, pagos y más de un movimiento alcanza {int(trait(2,'C2_relacion_amplia','n_cumplen'))}/1.089 ({fmt(trait(2,'C2_relacion_amplia'))}%). No describir al cliente típico como alguien que reúne todas las dimensiones.

**C3 — respaldada con matices.** Mediana de 6 productos y límite Visa mediano de $140.760 entre los 839 clientes con dato; {fmt(stat(3,'Visa_mlimitecompra','faltantes_pct'))}% faltante. Solo {fmt(trait(3,'uso_visa'))}% usa Visa. La mediana de movimientos es 6; por eso “poco uso” no equivale a inactividad absoluta. La regla estricta de ≥3 productos, algún límite positivo, cero transacciones en ambas tarjetas y ≤1 movimiento alcanza {int(trait(3,'C3_productos_limites_poco_uso','n_cumplen'))}/915 ({fmt(trait(3,'C3_productos_limites_poco_uso'))}%). Un límite registrado no demuestra disponibilidad efectiva para operar.

**C4 — escasa actividad respaldada; cierre mayoritario no respaldado.** En BAJA+2 no se observa consumo ni transacciones Visa y la mediana de movimientos es 3. Visa_status falta en 529/559 (94,63%) y Master_status en 517/559 (92,49%). Entre los válidos hay cierre en 29/30 Visa (96,67%) y 37/42 Master (88,10%), pero sobre todo C4 son 5,19% y 6,62%. Algún cierre confirmado aparece en 48/559 (8,59%); baja actividad estricta y cierre simultáneo, en 18/559 (3,22%). El faltante no acredita cierre. Alguna mora confirmada aparece en 11/559 (1,97%), con muchos casos desconocidos: **cierre y mora son distintos**.

**C5 — perfil de préstamos respaldado; rentabilidad depende del momento.** 222/223 (99,55%) tienen préstamos y deuda positiva. En BAJA+2 la mediana de rentabilidad es $2.283,29 y la media $3.738,16; {fmt(trait(5,'rentabilidad_negativa'))}% tiene rentabilidad negativa. Préstamos, deuda y pérdida simultáneos aparecen en 58/223 (26,01%). No caracterizar a todo C5 como deficitario en BAJA+2.

## C4: cuándo aparecen los cierres

{' '.join(closure_text)} La primera aparición del código no establece la fecha real de inicio cuando ya estaba presente al entrar en la ventana o faltan observaciones. `c4_momento_primer_cierre.csv` muestra el desglose por mes relativo y censura a izquierda; `c4_transiciones_cierre.csv` muestra cambios observados entre meses consecutivos. Los estados 6, 7 y 9 se mantienen separados en las tablas categóricas. Los códigos de mora se analizan por separado, sin promediar estados de tarjetas.

## C5: extremos y caída de julio

| Variable, BAJA+2 | Mediana | P90 | P99 | Máximo | Concentración top 1% | Top 5% | Mediana sin top 5% |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(concentration_text)}

Top 1% significa 3 clientes y top 5%, 12 (redondeo hacia arriba). Se ordena y recorta cada variable por separado. Sin el top 5%, la media de préstamos es {fmt(c5.loc['cprestamos_personales','media_sin_top5'])} y la deuda media ${fmt(c5.loc['mprestamos_personales','media_sin_top5'])}: el perfil persiste. El diccionario llama a estas cantidades préstamos vigentes; el máximo 257 es inusual, se conserva y no se corrige sin evidencia externa.

En el panel fijo de **150 clientes con junio y julio**, la rentabilidad media pasa de **$3.411,51 a −$11.920,17**, y la mediana de **$2.380,565 a −$6.006,825**. La proporción negativa pasa de **42/150 (28%) a 126/150 (84%)**. Las pérdidas brutas de julio suman **$1.872.079,84**; los 2 mayores casos concentran {fmt(july5.perdidas_top1_pct_total)}% y los 8 mayores, {fmt(july5.perdidas_top5_pct_total)}%. La pérdida alcanza a una mayoría, aunque los extremos agravan el promedio.

La caída de la media de C5 usando todos los presentes es −$15.643,25; se descompone exactamente en **−$15.331,68 dentro de los mismos clientes** y **−$311,57 por composición**. Por tanto, la caída no se explica principalmente por el cambio de integrantes. No se infiere su causa contable a partir de estas variables.

Esos 150 clientes están en BAJA+2 en junio y BAJA+1 en julio. En esta comparación coinciden el avance de la baja y el cambio de mes: no puede separarse un efecto específico de julio de un efecto de etapa. El panel relativo de −1/0/+1 aporta la comparación complementaria con las otras cohortes.

## Internet y estabilidad

`internet` toma **0, 1, 2, 3 y 4 en el dataset completo**. El diccionario describe el concepto, pero no decodifica esos valores. Se preservan como categorías sin imponer una interpretación binaria. En C5/BAJA+2 se observan 0/1/2/3, con conteos 49, 144, 25 y 5. El bosque original los utilizó numéricamente; se conserva ese tratamiento para reproducir la corrida, lo cual limita su interpretación.

- KMeans sobre representación fija, 10 semillas adicionales: ARI **{st.loc['kmeans_matriz_fija','min']:.4f}–{st.loc['kmeans_matriz_fija','max']:.4f}** respecto de la base; también se exportan los 55 pares entre las 11 corridas.
- Bosque con la misma muestra y tres semillas, KMeans fijo: ARI **{st.loc['bosque_muestra_fija','min']:.4f}–{st.loc['bosque_muestra_fija','max']:.4f}**.
- Procedimiento completo, tres semillas que cambian fieles, bosque y KMeans: ARI **{st.loc['procedimiento_completo','min']:.4f}–{st.loc['procedimiento_completo','max']:.4f}**.

Los grupos se emparejan por máxima intersección uno a uno. Se exportan recuperación, precisión, Jaccard, confusiones y coincidencia total. Estas repeticiones miden sensibilidad a la aleatoriedad; no evalúan otro período, otro banco, otras variables o valores de k. Un grupo estable puede seguir teniendo una descripción comercial incorrecta.

KMeans prácticamente reproduce los grupos; la mayor variación aparece al reconstruir el bosque. Al repetir todo el procedimiento coincide aproximadamente el 92% de las asignaciones tras emparejar. C5 tiene el Jaccard más bajo en esas repeticiones (0,801–0,827): su perfil agregado de préstamos es claro, pero sus fronteras no son completamente estables.

## Cómo leer y reproducir los entregables

- `asignaciones_clientes.csv`: una fila por cliente, ID y cluster.
- `perfiles_baja2.csv`, `perfiles_mensual.csv`, `perfiles_relativo.csv`: válidos, faltantes, media, mediana, P25/P75/P90/P95/P99, mínimo/máximo y proporción 1 para indicadores binarios. Los estados e internet están exclusivamente en `categorias_*.csv`, con porcentajes sobre el total y faltantes separados.
- `rasgos_*.csv`: numerador, total, evaluables y desconocidos. `pct_total` es una prevalencia confirmada sobre toda la cohorte; `pct_evaluables` cambia el denominador. No convertir desconocidos en ausencia del rasgo.
- `cambios_pareados.csv`: clientes presentes en ambos momentos y pares válidos por variable; medias/medianas individuales y proporción que sube o baja. El gráfico 4 usa el mismo panel en −1/0/+1; no demuestra que cada cliente siga la curva de la mediana.
- `tabla_evidencia.csv`: afirmación, evaluación, variable, cifra exacta, población, momento y limitación. Los valores de este informe están redondeados para lectura; los CSV conservan precisión.
- `graficos/`: siete gráficos PNG y SVG. `graficos_comparativos_k5.pdf` los reúne. El PDF `../pdf/clusters_tendencias_k5_th.pdf` incorpora el diccionario para cada atributo y la cobertura de agosto; estados de tarjetas e internet se muestran como distribuciones categóricas, sin promediar sus códigos.
- Fuente de unidades: el diccionario indica pesos argentinos, incluso para campos referidos a dólares (convertidos al cierre de cada mes). Hay una diferencia de nombre documentada: `mttarjeta_visa_debitos_automaticos` en el CSV corresponde a `mtarjeta_visa_debitos_automaticos` en el diccionario.
- Reproducción completa: ejecutar, en orden, `validacion_clusters_k5_th.py`, `comparacion_clase_ternaria_k5_th.py`, `haberes_mantenimiento_k5_th.py` e `informe_clusters_k5_th.py`, todos en `dmeyf2026/monday/`, con Python del entorno virtual. Para el PDF de atributos: `python dmeyf2026/monday/z501_cluster_rf_th.py --k 5 --out output/pdf/clusters_tendencias_k5_th.pdf`. `--reuse` del primer script solo reutiliza muestra/representación si coinciden hashes y versiones. El script original permanece separado.

### Definiciones operativas de rasgos conjuntos

Haberes: `cpayroll_trx>0` o `mpayroll>0` o `mpayroll2>0`. Uso Visa/Master: transacciones >0. Débitos Visa: cantidad >0. Baja actividad estricta: `active_quarter=0` y `ctrx_quarter<=1`. Cierre: algún estado 6/7/9; mora: alguna delinquency=1. C1 combina uso Visa, débitos Visa y ausencia de haberes; C2 combina haberes, saldo positivo, uso de alguna tarjeta, pagos positivos y más de un movimiento; C3 combina ≥3 productos, algún límite positivo, cero transacciones en ambas tarjetas y ≤1 movimiento; C4 combina baja actividad estricta y cierre; C5 combina préstamos/deuda positivos y rentabilidad negativa. Son umbrales transparentes elegidos para contrastar las afirmaciones, no definiciones universales del cliente típico ni reglas optimizadas. La lógica conserva desconocidos cuando los datos no permiten resolver el rasgo.
'''
    if (OUT/"comparacion_clase_ternaria.md").exists():
        report = report.replace("siete gráficos", "ocho gráficos")
        report += '''
## Comparación con el target y la cartera CONTINUA

Se agregó el [contraste con clase_ternaria](comparacion_clase_ternaria.md), distinguiendo el target de cada fila de la cohorte de clientes que alguna vez fue BAJA+2. Se comparan BAJA+1, BAJA+2 y CONTINUA en marzo-junio, con denominador igual a toda la cartera de cada mes. Julio/agosto tienen targets incompletos y no se usan para estimar la proporción BAJA+2/CONTINUA.

La referencia primaria usa todas las filas CONTINUA del mismo mes, aunque esos clientes puedan ser BAJA+2 en otro momento. Los 4.067 fieles balanceados se usan para el bosque: **no se consideran representativos de la cartera ni se calculan tasas poblacionales sobre esa muestra**.

El contraste calendario también matiza C2: su media de movimientos es 94,07, frente a 120,25 de CONTINUA ponderado con el mismo calendario. En C5 la deuda media de $247.503,72 contrasta con $33.983,77 de esa referencia. Los pesos mensuales, válidos y faltantes se exportan; no se promedian percentiles. El gráfico 8 separa los denominadores de cartera y cohorte.
'''
    if (OUT/"haberes_mantenimiento.md").exists():
        report += '''
## Acreditación de haberes y mantenimiento

Se agregó el [análisis de haberes y mantenimiento](haberes_mantenimiento.md), con tablas por cluster/mes y la referencia completa CONTINUA. `mpayroll` mide acreditaciones de empleadores acreditados; `mcomisiones_mantenimiento` agrega el mantenimiento de productos. El diccionario no demuestra una condición de bonificación contractual.

En CONTINUA/marzo-junio, alrededor del 96% con mpayroll positivo tiene mantenimiento cero, frente al 32–37% con mpayroll=0. La asociación es heterogénea entre clusters y en C4/C5 hay pocos casos con haberes. Se conservan faltantes y negativos separados. Al empezar o dejar de acreditar, los cambios del mismo cliente y del mes siguiente no siguen una regla universal; se exportan pares válidos, reversión/persistencia y pérdidas de seguimiento. **Asociación no equivale a condición contractual ni a causalidad.**
'''
    (OUT/"informe_validacion_k5.md").write_text(report,encoding="utf-8")
    print("Informe, evidencia y gráficos comparativos generados.")


if __name__=="__main__":
    main()
