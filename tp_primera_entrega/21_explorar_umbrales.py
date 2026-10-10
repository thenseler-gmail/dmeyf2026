"""Experimento separado: corte elegido en mayo, comprobacion congelada junio."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def evaluar(df,p,u):
    s=np.asarray(p)>u
    tp=int((s & df.clase_ternaria.eq('BAJA+2').to_numpy()).sum())
    n=int(s.sum()); g=tp*1072500-(n-tp)*27500
    return dict(umbral=float(u),contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4)


def curva(df,col):
    p=df[col].to_numpy()
    orden=np.argsort(-p,kind='stable')
    q=p[orden]
    pagos=np.where(df.clase_ternaria.eq('BAJA+2'),1072500,-27500)[orden]
    suma=np.cumsum(pagos)
    # Corte estricto: incluir grupos completos de probabilidades iguales.
    finales=np.flatnonzero(np.r_[q[:-1]!=q[1:],True])
    u=np.nextafter(q[finales],-np.inf)
    tabla=pd.DataFrame(dict(umbral=u,contactos=finales+1,ganancia=suma[finales]))
    tabla=pd.concat([tabla,pd.DataFrame([dict(umbral=float(q[0]),contactos=0,ganancia=0)])],ignore_index=True)
    tabla['ganancia_25pct']=tabla.ganancia/4
    # Empates de ganancia: preferir menos contactos, sin mirar junio.
    best=tabla.sort_values(['ganancia','contactos'],ascending=[False,True]).iloc[0]
    assert evaluar(df,p,best.umbral)['ganancia']==int(best.ganancia)
    return tabla,best


def main():
    sal=ROOT/'tp_primera_entrega/salidas'
    fuente=sal/'calibracion_20261005_133516'
    out=sal/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('umbrales_%Y%m%d_%H%M%S')
    out.mkdir()
    mayo=pd.read_csv(fuente/'predicciones_mayo.csv')
    modelos=[('Promedio 50/50','mezcla_probabilidades','mezcla_probabilidades'),('Correccion aprendida','p_corregida_oof','p_corregida')]
    elecciones={}; tablas={}
    for nombre,cm,cj in modelos:
        tabla,best=curva(mayo,cm)
        tablas[nombre]=tabla
        tabla.to_csv(out/(cm+'_curva_mayo.csv'),index=False)
        elecciones[nombre]=dict(columna_mayo=cm,columna_junio=cj,**evaluar(mayo,mayo[cm],best.umbral))
    protocolo=dict(estado='cortes_congelados',fuente=str(fuente),seleccion_mes=202105,evaluacion_mes=202106,
        elecciones=elecciones,notas='Experimento autorizado separado de umbral fijo 2.5%. Maximo empirico exacto en mayo, sin cortes de junio. Mayo reutilizado y calibrador OOF solo de segunda etapa; sesgo de seleccion. Junio expuesto exploratorio.')
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    junio=pd.read_csv(fuente/'predicciones_junio.csv')
    resultados=[]
    for nombre,cm,cj in modelos:
        u=elecciones[nombre]['umbral']
        for mes,df,col in [('mayo',mayo,cm),('junio',junio,cj)]:
            for regla,corte in [('Fijo 2.5%',0.025),('Elegido en mayo',u)]:
                resultados.append(dict(modelo=nombre,mes=mes,regla=regla,**evaluar(df,df[col],corte)))
    resumen=pd.DataFrame(resultados)
    resumen.to_csv(out/'comparacion.csv',index=False)
    fig,axs=plt.subplots(2,1,figsize=(10,9),layout='constrained')
    colores=['#3575c4','#e29427']
    for ax,escala,titulo in [(axs[0],1e6,'Ganancia total en mayo'),(axs[1],4e6,'25% de referencia de la ganancia de mayo')]:
        for (nombre,cm,cj),color in zip(modelos,colores):
            t=tablas[nombre].sort_values('umbral')
            # Ventana explicativa; maximo calculado con todos los cortes.
            t=t.loc[t.umbral.between(0.01,0.05)]
            ax.plot(t.umbral*100,t.ganancia/escala,label=nombre,color=color)
            e=elecciones[nombre]
            ax.scatter(e['umbral']*100,e['ganancia']/escala,color=color,zorder=4)
            ax.annotate(f"{nombre}\n{e['umbral']*100:.3f}% · ${e['ganancia']/escala:.2f} M",(e['umbral']*100,e['ganancia']/escala),xytext=(0.62,0.38 if color==colores[0] else 0.72),textcoords='axes fraction',fontsize=10,color=color,arrowprops=dict(arrowstyle='-',color=color))
        ax.axvline(2.5,color='#666666',linestyle='--',label='Umbral fijo 2,5%')
        ax.set(xlabel='Umbral (%) — se contacta si la probabilidad lo supera',ylabel='Millones de pesos',title=titulo+' (detalle del 1% al 5%)',xlim=(1,5))
        ax.grid(alpha=.2); ax.legend(loc='lower right')
    fig.savefig(out/'ganancia_umbrales_mayo.png',dpi=160); plt.close(fig)
    protocolo.update(estado='completo',resultados=resultados)
    save()
    print(resumen.to_string(index=False))
    print('Salida:',out)


if __name__=='__main__':
    main()
