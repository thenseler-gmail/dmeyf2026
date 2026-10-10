"""Busqueda secuencial local: corte para40/40/20 y luego pesos con corte congelado."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas'
SRC=SAL/'mix_hist189_catboost_20261006_145401'
SEEDS=[541440,408476,741961,248865,717444]
GRID=np.arange(10,81)/1000
WEIGHTS=[(i/5,j/5,(5-i-j)/5) for i in range(6) for j in range(6-i)]
BASE=(.4,.4,.2)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(x):return '$'+f'{x:,.0f}'.replace(',','.')

def main():
    m=json.loads((SRC/'manifest.json').read_text(encoding='utf-8'));assert m['estado']=='completo_verificado'
    assert m['train']==[202104] and m['evaluacion']==202105 and m['semillas']==SEEDS
    for f,h in m['archivos_sha256'].items():assert sha(SRC/f)==h
    p=pd.read_csv(SRC/'predicciones_mayo.csv')
    assert len(p)==163768 and p.foto_mes.eq(202105).all() and not p.numero_de_cliente.duplicated().any()
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();assert y.sum()==870
    cash=np.where(y,1072500,-27500);parts=p.parte_cliente.to_numpy()
    lb=p[[f'p_lgb189_seed{s}' for s in SEEDS]].to_numpy()
    cb=p[[f'p_cat202_seed{s}' for s in SEEDS]].to_numpy();tb=p.p_tabpfn.to_numpy()[:,None]
    def score(w):return w[0]*lb+w[1]*tb+w[2]*cb
    base=score(BASE)
    np.testing.assert_allclose(base,p[[f'score_mix_seed{s}' for s in SEEDS]],rtol=0,atol=1e-15)
    def measure(q,u,mask=None):
        sel=q>u
        if mask is not None:sel=sel&mask[:,None]
        n=sel.sum(axis=0);tp=(sel&y[:,None]).sum(axis=0);g=tp*1100000-n*27500
        np.testing.assert_array_equal(g,(sel*cash[:,None]).sum(axis=0))
        return pd.DataFrame(dict(seed=SEEDS,contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4))
    def curve(mask):
        rows=[]
        # Ordenar scores permite evaluar todos los cortes sin71 matrices de seleccion.
        for s in range(5):
            q=base[mask,s];pay=cash[mask];order=np.argsort(q);q=q[order];pay=pay[order]
            cumulative=np.r_[0,np.cumsum(pay,dtype=np.int64)]
            indices=np.searchsorted(q,GRID,side='right');g=cumulative[-1]-cumulative[indices]
            rows.append(g)
        gains=np.array(rows)
        return pd.DataFrame(dict(umbral=GRID,ganancia=gains.mean(axis=0),ganancia_25pct=gains.mean(axis=0)/4,
            **{f'ganancia_seed{s}':gains[i] for i,s in enumerate(SEEDS)}))
    def choose_cut(t):
        best=t.ganancia.max();candidates=t[t.ganancia.eq(best)].copy()
        candidates['distancia']=abs(candidates.umbral-.025)
        return float(candidates.sort_values(['distancia','umbral']).iloc[0].umbral)
    def weights_table(u,mask):
        rows=[]
        for w in WEIGHTS:
            r=measure(score(w),u,mask)
            rows.append(dict(lightgbm=w[0],tabpfn=w[1],catboost=w[2],umbral=u,
                contactos=r.contactos.mean(),tp=r.tp.mean(),fp=r.fp.mean(),ganancia=r.ganancia.mean(),ganancia_25pct=r.ganancia.mean()/4))
        t=pd.DataFrame(rows);t['distancia_a_base']=abs(t.lightgbm-.4)+abs(t.tabpfn-.4)+abs(t.catboost-.2)
        return t.sort_values(['ganancia','distancia_a_base','lightgbm','tabpfn'],ascending=[False,True,True,True]).reset_index(drop=True)
    def choose_weight(t):return tuple(float(t.iloc[0][c]) for c in ['lightgbm','tabpfn','catboost'])
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('corte_pesos_mix17_%Y%m%d_%H%M%S');out.mkdir()
    allmask=np.ones(len(p),dtype=bool);full=curve(allmask);u=choose_cut(full)
    # El corte se congela antes de iniciar la seleccion de pesos.
    table=weights_table(u,allmask);w=choose_weight(table)
    full.to_csv(out/'curva_corte_40_40_20.csv',index=False);table.to_csv(out/'pesos_corte_fijo.csv',index=False)
    near=full[full.ganancia.ge(full.ganancia.max()*.99)]
    apparent=[];aparts=[]
    for name,weights,cut in [('mix17_025',BASE,.025),('mix18_033',BASE,.033),('corte_optimo',BASE,u),('corte_fijo_pesos_elegidos',w,u)]:
        r=measure(score(weights),cut);r['regla']=name;r['umbral']=cut;apparent.append(r)
        for k in range(4):
            a=measure(score(weights),cut,parts==k);a['regla']=name;a['parte']=k;aparts.append(a)
    apparent=pd.concat(apparent,ignore_index=True);aparts=pd.concat(aparts,ignore_index=True)
    summary=apparent.groupby('regla')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    assert summary.loc['mix17_025','ganancia']==269813500 and summary.loc['mix18_033','ganancia']==273190500
    for row in full.itertuples():assert measure(base,row.umbral).ganancia.mean()==row.ganancia
    apparent.to_csv(out/'resultados_aparentes_semillas.csv',index=False);aparts.to_csv(out/'resultados_aparentes_partes.csv',index=False)
    summary.to_csv(out/'resumen_aparente.csv')
    # Auditoria de seleccion: cada cuarto se reserva; corte y pesos se eligen SOLO en los otros3/4.
    cross=[];choices=[]
    for k in range(4):
        train=parts!=k;test=parts==k;t=curve(train);uk=choose_cut(t);wt=weights_table(uk,train);wk=choose_weight(wt)
        t.to_csv(out/f'curva_seleccion_parte{k}.csv',index=False);wt.to_csv(out/f'pesos_seleccion_parte{k}.csv',index=False)
        choices.append(dict(parte=k,umbral=uk,lightgbm=wk[0],tabpfn=wk[1],catboost=wk[2],filas_seleccion=int(train.sum()),filas_evaluacion=int(test.sum())))
        for name,weights,cut in [('mix17_025',BASE,.025),('mix18_033',BASE,.033),('seleccion_corte',BASE,uk),('seleccion_corte_y_pesos',wk,uk)]:
            r=measure(score(weights),cut,test);r['regla']=name;r['parte']=k;r['umbral']=cut;cross.append(r)
    cross=pd.concat(cross,ignore_index=True);cross.to_csv(out/'evaluacion_cruzada_partes.csv',index=False)
    pd.DataFrame(choices).to_csv(out/'elecciones_cruzadas.csv',index=False)
    summed=cross.groupby(['regla','seed'])[['contactos','tp','fp','ganancia','ganancia_25pct']].sum().reset_index()
    summed.to_csv(out/'evaluacion_cruzada_semillas.csv',index=False)
    cs=summed.groupby('regla')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean();cs.to_csv(out/'resumen_cruzado.csv')
    changes=cross.groupby(['regla','parte']).ganancia.mean().unstack('regla')
    positive=int((changes.seleccion_corte_y_pesos>changes.mix17_025).sum())
    dg=float(cs.loc['seleccion_corte_y_pesos','ganancia']-cs.loc['mix17_025','ganancia'])
    audit=dict(estado='completo_verificado',fuente=str(SRC.relative_to(ROOT)),train=[202104],evaluacion=202105,
        semillas=SEEDS,features=dict(lightgbm=189,tabpfn=202,catboost=202),
        grid_corte=GRID.tolist(),grid_pesos=WEIGHTS,pesos_originales=BASE,corte_optimo_local=u,pesos_elegidos=w,
        criterio='Maximo de ganancia media5; empate corte cercano a2,5%, empate pesos cercanos40/40/20. Corte congelado antes de pesos.',
        corte_en_borde=bool(u in (GRID[0],GRID[-1])),banda_1pct=near.umbral.tolist(),
        resultados_aparentes=summary.reset_index().to_dict('records'),resultados_cruzados=cs.reset_index().to_dict('records'),
        elecciones_cruzadas=choices,delta_cruzado_vs17=dg,delta_cruzado_vs17_25pct=dg/4,partes_cruzadas_mejoran_vs17=positive,
        api=False,creditos=0,nuevos_fits=0,submits=0,entrega_nueva_preparada=False,
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [SRC/'manifest.json',SRC/'predicciones_mayo.csv']},
        codigo_sha256=sha(Path(__file__)),archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')},
        limitacion='Mayo y semillas reutilizados, no test temporal independiente. Curvas aparentes optimistas por seleccion. '
                   'Cruce reserva clientes para seleccionar corte y pesos, pero no elimina reutilizacion historica de mayo. '
                   'Pesos nuevos mezclan targets distintos; corte optimo de40/40/20 no tiene por que ser optimo de pesos nuevos. '
                   'No se leyeron junio/agosto ni publico para seleccionar.')
    save(out/'manifest.json',audit)
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    ax=axes[0]
    for s in SEEDS:ax.plot(full.umbral*100,full[f'ganancia_seed{s}']/4e6,alpha=.25,lw=1)
    ax.plot(full.umbral*100,full.ganancia_25pct/1e6,color='#176c9c',label='Media cinco semillas')
    for cut,label,color in [(.025,'2,5%','#777'),(.033,'3,3%','#bd8832'),(u,f'Maximo local {u:.1%}','#a33')]:ax.axvline(cut*100,color=color,linestyle='--',label=label)
    ax.set(xlabel='Corte del score (%)',ylabel='25% de ganancia local (millones $)',title='1. Corte para mezcla 40/40/20');ax.grid(alpha=.2);ax.legend(fontsize=8)
    ax=axes[1];dots=ax.scatter(table.lightgbm*100,table.tabpfn*100,c=table.ganancia_25pct/1e6,cmap='viridis',s=160)
    ax.scatter([w[0]*100],[w[1]*100],s=330,facecolors='none',edgecolors='red',lw=2)
    ax.scatter([40],[40],marker='x',s=150,c='black',lw=2)
    ax.set(xlabel='Peso LightGBM (%)',ylabel='Peso TabPFN (%)',title=f'2. Pesos con corte fijo {u:.1%}');ax.grid(alpha=.2)
    fig.colorbar(dots,ax=ax,label='25% de ganancia local (millones $)')
    fig.suptitle('Abril → mayo: maximos descriptivos; auditoria cruzada en informe')
    fig.savefig(out/'corte_y_pesos.png',dpi=160);plt.close(fig)
    report=['# Corte y pesos de la mezcla17','',
        f'**Corte máximo local para40/40/20: {u:.1%}.** Con ese corte fijo, mejores pesos de la grilla: '
        f'LightGBM {w[0]:.0%}, TabPFN {w[1]:.0%}, CatBoost {w[2]:.0%}.','',
        'Se prueban cortes1%–8% con pasos0,1 puntos porcentuales. Después se congela el corte y se comparan21 proporciones en pasos20 puntos porcentuales, incluidos modelos solos. '
        'Sin optimización conjunta ni refinamiento posterior, cinco semillas fijas, mismos scores y targets.','',
        '| Resultado aparente en mayo | Total medio | 25% |','| --- | ---: | ---: |']
    for name,row in summary.iterrows():report.append(f'| {name} | {money(row.ganancia)} | {money(row.ganancia_25pct)} |')
    report+=['','## Auditoría de selección por clientes','',
        'En cada parte reservada, el corte40/40/20 y después los pesos a ese corte se eligieron únicamente en las otras tres partes. '
        'La suma evalúa una política de selección: usa cuatro cortes/pesos diferentes, no una única entrega con el elegido en mayo completo.','',
        '| Política evaluada fuera de selección | Total medio | 25% |','| --- | ---: | ---: |']
    for name,row in cs.iterrows():report.append(f'| {name} | {money(row.ganancia)} | {money(row.ganancia_25pct)} |')
    report+=['',f'Selección secuencial frente a17: diferencia cruzada {money(dg)}; 25% {money(dg/4)}; mejora en {positive}/4 partes.','',
        'Elecciones por parte: '+str(choices),'',audit['limitacion'],'',
        'Entregas17/18 conservadas y pendientes de envío. No se generó una nueva entrega ni se envió al Bot.','',
        '![Curva de corte y pesos](corte_y_pesos.png)']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    c['busqueda_corte_pesos_mix17']={**audit,'carpeta':str(out.relative_to(ROOT))};save(cfg,c)
    note=(f'**Corte/pesos mezcla17 evaluados:** corte máximo local {u:.1%} para40/40/20; '
          f'con ese corte fijo, pesos elegidos {w}. [Informe](salidas/{out.name}/MINI_INFORME.md). '
          f'Delta cruzado frente17 {money(dg)},25% {money(dg/4)}, {positive}/4 partes. '
          'Entregas17/18 pendientes hasta revisar; cero fits/API/submits.')
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## 105. Optimizacion secuencial corte y pesos mezcla17 - 2026-10-06\n\n'+note+'\n\n'+audit['limitacion']+'\n')
    print('Salida:',out);print('Corte:',u,'Pesos:',w);print('Aparente:');print(summary.to_string());print('Cruzado:');print(cs.to_string());print('Elecciones:',choices)

if __name__=='__main__':main()
