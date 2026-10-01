"""Perfil descriptivo de actividad por clase, sin entrenar ni seleccionar modelos."""
from pathlib import Path
import json
import duckdb
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'monday/reporte_clase04/actividad'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute('SET threads=2')
    con.read_csv(str(ROOT/'data/competencia_01.csv')).create_view('fuente')
    con.execute('''CREATE TABLE base AS SELECT numero_de_cliente, foto_mes, clase_ternaria,
        active_quarter, ctrx_quarter, cliente_antiguedad, cproductos,
        chomebanking_transacciones, cmobile_app_trx, ctarjeta_debito_transacciones,
        ctarjeta_visa_transacciones, ctarjeta_master_transacciones, ccallcenter_transacciones,
        ccajas_transacciones, catm_trx, mpayroll,
        CASE WHEN ctrx_quarter=0 THEN '0' WHEN ctrx_quarter<=30 THEN '1-30'
             WHEN ctrx_quarter<=60 THEN '31-60' WHEN ctrx_quarter<=120 THEN '61-120' ELSE '121+' END actividad,
        CASE WHEN cliente_antiguedad<=12 THEN '01: hasta 12' WHEN cliente_antiguedad<=60 THEN '02: 13-60'
             WHEN cliente_antiguedad<=120 THEN '03: 61-120' ELSE '04: 121+' END antiguedad
        FROM fuente WHERE foto_mes BETWEEN 202103 AND 202106''')
    features = ['active_quarter','ctrx_quarter','cliente_antiguedad','cproductos',
                'chomebanking_transacciones','cmobile_app_trx','ctarjeta_debito_transacciones',
                'ctarjeta_visa_transacciones','ctarjeta_master_transacciones',
                'ccallcenter_transacciones','ccajas_transacciones','catm_trx','mpayroll']
    profiles = []
    for v in features:
        profiles.append(con.sql(f'''SELECT foto_mes,clase_ternaria,'{v}' AS nombre_variable,count(*) n,
            avg({v}) media, median({v}) mediana, quantile_cont({v},0.25) p25,
            quantile_cont({v},0.75) p75,100.0*count(*) FILTER(WHERE {v}=0)/count(*) cero_pct,
            100.0*count(*) FILTER(WHERE {v} IS NULL)/count(*) nulo_pct
            FROM base GROUP BY 1,2''').df())
    perfil=pd.concat(profiles,ignore_index=True)
    def tasas(dims):
        return con.sql(f'''SELECT {dims},count(*) n,
            count(*) FILTER(WHERE clase_ternaria='BAJA+1') baja1,
            count(*) FILTER(WHERE clase_ternaria='BAJA+2') baja2,
            count(*) FILTER(WHERE clase_ternaria='CONTINUA') continua,
            100.0*count(*) FILTER(WHERE clase_ternaria='BAJA+1')/count(*) baja1_pct,
            100.0*count(*) FILTER(WHERE clase_ternaria='BAJA+2')/count(*) baja2_pct,
            100.0*count(*) FILTER(WHERE clase_ternaria!='CONTINUA')/count(*) baja_total_pct
            FROM base GROUP BY {dims} ORDER BY {dims}''').df()
    mensual=tasas('foto_mes')
    bandas=tasas('foto_mes,actividad')
    activo=tasas('foto_mes,active_quarter')
    cruce=tasas('foto_mes,actividad,antiguedad')
    consistencia=con.sql('SELECT active_quarter, min(ctrx_quarter) minimo, max(ctrx_quarter) maximo,count(*) n FROM base GROUP BY 1').df()
    tablas={'perfil_por_clase':perfil,'tasas_mensuales':mensual,'tasas_por_actividad':bandas,
            'tasas_por_active_quarter':activo,'actividad_por_antiguedad':cruce,'consistencia_indicador':consistencia}
    for name,df in tablas.items(): df.to_csv(OUT/(name+'.csv'),index=False,encoding='utf-8-sig')
    orden=['0','1-30','31-60','61-120','121+']
    colores={'BAJA+1':'#c24935','BAJA+2':'#dd930c','CONTINUA':'#167a85'}
    fig,ax=plt.subplots(figsize=(9,4.5))
    for clase,color in colores.items():
        d=perfil[(perfil.nombre_variable=='ctrx_quarter')&(perfil.clase_ternaria==clase)].sort_values('foto_mes')
        ax.plot(d.foto_mes.astype(str),d.mediana,marker='o',label=clase,color=color)
    ax.set(xlabel='Mes',ylabel='Mediana de ctrx_quarter',title='Actividad trimestral por clase')
    ax.legend(); ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'medianas_actividad.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),sharey=True)
    for ax,col,titulo in zip(axes,['baja1_pct','baja2_pct'],['BAJA+1','BAJA+2']):
        for mes,d in bandas.groupby('foto_mes'):
            d=d.set_index('actividad').reindex(orden)
            ax.plot(orden,d[col],marker='o',label=str(mes))
        ax.set(title=titulo,xlabel='Banda de ctrx_quarter',ylabel='Tasa de baja (%)');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Probabilidad observada de baja dentro de cada banda');fig.tight_layout();fig.savefig(OUT/'tasas_actividad.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    vmax=cruce.baja2_pct.max()
    for ax,(mes,d) in zip(axes.flat,cruce.groupby('foto_mes')):
        pivot=d.pivot(index='actividad',columns='antiguedad',values='baja2_pct').reindex(orden)
        sizes=d.pivot(index='actividad',columns='antiguedad',values='n').reindex(orden)
        im=ax.imshow(pivot,vmin=0,vmax=vmax,cmap='YlOrRd',aspect='auto')
        for i in range(len(pivot)):
            for j in range(len(pivot.columns)):
                val=pivot.iloc[i,j];size=sizes.iloc[i,j]
                if pd.notna(val): ax.text(j,i,f'{val:.2f}%\nn={int(size):,}',ha='center',va='center',fontsize=8)
        ax.set_title(str(mes));ax.set_xticks(range(len(pivot.columns)),[x.split(': ')[1] for x in pivot.columns]);ax.set_yticks(range(5),orden)
        ax.set_xlabel('Antigüedad: valor registrado');ax.set_ylabel('ctrx_quarter')
    fig.suptitle('BAJA+2: actividad × antigüedad · tasa y tamaño de cada grupo')
    fig.tight_layout();fig.savefig(OUT/'cruce_antiguedad.png',dpi=160);plt.close(fig)
    def table(df):return df.to_html(index=False,border=0,float_format=lambda x:f'{x:,.2f}')
    intro='''<h1>Actividad y bajas · EDA Clase 04</h1>
    <p>Comparación descriptiva de marzo a junio de 2021, meses con objetivo completo. BAJA+1 y BAJA+2 se muestran separadas; BAJA total es su suma. Las tasas usan como denominador todos los clientes del grupo, no solamente las bajas.</p>
    <p>Los cortes 0 / 1–30 / 31–60 / 61–120 / 121+ son exploratorios y no se optimizaron contra la ganancia. Los mismos clientes se repiten entre meses: no son observaciones independientes. Las asociaciones no prueban causalidad ni mejora predictiva. No se entrenaron modelos.</p>
    <p><b>Corrección de interpretación:</b> cmobile_app_trx toma solamente 0 y 1 en este dataset; lo tratamos como indicador observado, no como volumen de operaciones. La unidad exacta de antigüedad aún debe validarse. active_quarter y ctrx_quarter pueden contener información redundante.</p>'''
    body=intro+'<h2>Tasas base por mes</h2>'+table(mensual)
    body+='<h2>Actividad típica por clase</h2><img src="medianas_actividad.png">'+table(perfil[perfil.nombre_variable=='ctrx_quarter'])
    body+='<h2>Tasas según nivel de actividad</h2><img src="tasas_actividad.png">'+table(bandas)
    body+='<h2>Indicador active_quarter</h2>'+table(activo)+table(consistencia)
    body+='<h2>Cruce con antigüedad</h2><img src="cruce_antiguedad.png"><p>Leer cada porcentaje junto con su n: grupos chicos pueden producir tasas extremas. El cruce es descriptivo, no un efecto ajustado.</p>'
    body+='<h2>Otros canales, vinculación y haberes</h2>'+table(perfil[perfil.nombre_variable!='ctrx_quarter'])
    page='<!doctype html><html lang="es"><meta charset="utf-8"><title>Actividad y bajas</title><style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px;color:#203040}p{line-height:1.6}table{border-collapse:collapse;font-size:13px;width:100%}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}th{background:#e4eef5}img{width:100%;height:auto}h2{margin-top:38px}</style>'+body+'</html>'
    (OUT/'reporte_actividad.html').write_text(page,encoding='utf-8')
    print('MEDIANAS',perfil[perfil.nombre_variable.isin(['ctrx_quarter','cproductos','chomebanking_transacciones','cmobile_app_trx'])][['foto_mes','clase_ternaria','nombre_variable','mediana','cero_pct']].to_json(orient='records'))
    print('BANDAS',bandas.to_json(orient='records'))
    print('ACTIVO',activo.to_json(orient='records'))
    print('CONSISTENCIA',consistencia.to_json(orient='records'))


if __name__=='__main__':main()
