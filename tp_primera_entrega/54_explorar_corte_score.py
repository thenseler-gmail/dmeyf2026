"""Corte de score: seleccion cruzada por cliente en mayo, sin junio/API."""
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

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT/'tp_primera_entrega/salidas'
SEEDS = [541440,408476,741961,248865,717444]
# Grilla y regla fijadas antes de leer ganancias. Sin optimizacion exacta por cliente.
GRID = np.arange(10,61,dtype=float)/1000

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def curves(scores,y):
    rows=[]
    for u in GRID:
        sel=scores>u
        tp=(sel & y[:,None]).sum(axis=0)
        n=sel.sum(axis=0)
        gain=tp*1100000-n*27500
        rows.append(dict(umbral=float(u),ganancia_media=float(gain.mean()),
                         ganancia_25pct=float(gain.mean()/4),contactos_media=float(n.mean())))
    return pd.DataFrame(rows)

def choose(t):
    g=t.ganancia_media.to_numpy();best=g.max()
    good=np.flatnonzero(g>=best-.01*abs(best))
    groups=np.split(good,np.flatnonzero(np.diff(good)>1)+1)
    band=sorted(groups,key=lambda a:(-len(a),abs(float(t.umbral.iloc[a].mean())-.025),int(a[0])))[0]
    idx=int(band[(len(band)-1)//2])
    return float(t.umbral.iloc[idx]),dict(inicio=float(t.umbral.iloc[band[0]]),
         fin=float(t.umbral.iloc[band[-1]]),maximo_empirico=float(t.umbral.iloc[int(g.argmax())]),
         tolerancia_relativa=.01)

def measure(scores,y,u):
    sel=scores>u;tp=(sel & y[:,None]).sum(axis=0);n=sel.sum(axis=0)
    return pd.DataFrame(dict(seed=SEEDS,contactos=n,tp=tp,fp=n-tp,
                            ganancia=tp*1100000-n*27500,
                            ganancia_25pct=(tp*1100000-n*27500)/4))

def main():
    src=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    m=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    assert m['validacion_train']==[202104] and m['validacion_eval']==202105
    p=pd.read_csv(src/'predicciones_mayo.csv')
    assert p.foto_mes.eq(202105).all() and not p.numero_de_cliente.duplicated().any()
    y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    assert p.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    scores=np.column_stack([(p[f'p_seed{s}']+p.p_tabpfn)/2 for s in SEEDS])
    assert np.isfinite(scores).all() and ((scores>=0)&(scores<=1)).all()
    for i,s in enumerate(SEEDS):
        np.testing.assert_allclose(scores[:,i],p[f'p_mezcla_seed{s}'],rtol=0,atol=1e-15)
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('corte_score_%Y%m%d_%H%M%S')
    out.mkdir()
    perm=np.random.default_rng(214363).permutation(len(p))
    fold=np.empty(len(p),dtype=int);fold[perm]=np.arange(len(p))%4
    asignacion=p[['numero_de_cliente','foto_mes']].copy();asignacion['fold']=fold
    asignacion.to_csv(out/'particiones_clientes.csv',index=False)
    results=[];choices=[];test_curves=[]
    for k in range(4):
        train=fold!=k;test=fold==k
        t=curves(scores[train],y[train]);u,band=choose(t)
        t.to_csv(out/f'curva_seleccion_fold{k}.csv',index=False)
        tc=curves(scores[test],y[test]);tc['fold']=k;test_curves.append(tc)
        choices.append(dict(fold=k,umbral=u,filas_seleccion=int(train.sum()),filas_evaluacion=int(test.sum()),**band))
        for rule,corte in [('fijo_025',.025),('elegido_sin_clientes_evaluacion',u)]:
            r=measure(scores[test],y[test],corte);r['fold']=k;r['regla']=rule;r['umbral']=corte
            results.append(r)
    result=pd.concat(results,ignore_index=True);result.to_csv(out/'evaluacion_cruzada.csv',index=False)
    sums=result.groupby(['regla','seed'])[['contactos','tp','fp','ganancia','ganancia_25pct']].sum().reset_index()
    sums.to_csv(out/'resumen_semillas.csv',index=False)
    summary=sums.groupby('regla')[['contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    summary.to_csv(out/'resumen.csv')
    full=curves(scores,y);u,band=choose(full);full.to_csv(out/'curva_mayo.csv',index=False)
    apparent=pd.concat([measure(scores,y,.025).assign(regla='fijo_025',umbral=.025),
                        measure(scores,y,u).assign(regla='corte_final_aparente',umbral=u)])
    apparent.to_csv(out/'resultado_aparente.csv',index=False)
    pd.DataFrame(choices).to_csv(out/'cortes_por_fold.csv',index=False)
    pd.concat(test_curves).to_csv(out/'curvas_evaluacion.csv',index=False)
    # Verificacion independiente por sumas directas de pagos y predicciones cruzadas.
    payments=np.where(y,1072500,-27500)
    for row in result.itertuples():
        mask=(fold==row.fold)&(scores[:,SEEDS.index(row.seed)]>row.umbral)
        assert int(payments[mask].sum())==row.ganancia and int(mask.sum())==row.contactos
    cross=scores>np.array([choices[k]['umbral'] for k in fold])[:,None]
    np.testing.assert_array_equal((cross*payments[:,None]).sum(axis=0),
        sums.loc[sums.regla.eq('elegido_sin_clientes_evaluacion')].set_index('seed').loc[SEEDS].ganancia)
    # Toda seleccion excluye clientes de su evaluacion; agosto/Bot no se leen hasta aqui.
    differences=result.groupby(['fold','regla']).ganancia.mean().unstack()
    positive=int((differences.elegido_sin_clientes_evaluacion>differences.fijo_025).sum())
    delta=float(summary.loc['elegido_sin_clientes_evaluacion','ganancia']-summary.loc['fijo_025','ganancia'])
    viable=delta>0 and positive>=3
    meta=dict(estado='verificado',fuente=str(src/'predicciones_mayo.csv'),fuente_sha256=sha(src/'predicciones_mayo.csv'),
        codigo_sha256=sha(Path(__file__)),semillas=SEEDS,grid=GRID.tolist(),regla='Media de ganancia de cinco listas; banda contigua mas larga a <=1% del maximo, centro inferior; empate mas cercano a 2.5%.',
        cortes=choices,corte_final=u,banda_final=band,delta_cruzado_total=delta,
        delta_cruzado_25pct=delta/4,folds_mejoran=positive,candidato_viable=viable,
        api=False,creditos=0,train_modelos=[202104],mes_evaluacion=202105,
        limitacion='Un solo mes reutilizado. Semillas previamente seleccionadas por abril/mayo. Particion cliente valida seleccion de corte, no es un nuevo test temporal. Train final abril+mayo distinto de abril; transferencia del corte incierta. No validar TabPFN214 con estos datos202.',
        lectura_junio=False,resultado_cruzado=summary.reset_index().to_dict('records'))
    (out/'manifest.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    fig,axs=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    for ax,scale,title in [(axs[0],1e6,'Ganancia total: media de cinco listas'),(axs[1],4e6,'25% de referencia local')]:
        for i in range(5):
            g=[measure(scores[:,[i]*5],y,t).ganancia.iloc[0] for t in GRID]
            ax.plot(GRID*100,np.array(g)/scale,alpha=.25,linewidth=1)
        ax.plot(full.umbral*100,full.ganancia_media/scale,color='#176c9c',label='Media cinco semillas')
        ax.axvspan(band['inicio']*100,band['fin']*100,color='#3fa777',alpha=.16,label='Banda a 1% del máximo')
        ax.axvline(2.5,color='#666',linestyle='--',label='Corte 2,5%')
        ax.axvline(u*100,color='#ae4932',label=f'Corte elegido {u*100:.1f}%')
        ax.set(xlabel='Corte del score (%)',ylabel='Millones de pesos',title=title)
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Abril → mayo: curva descriptiva; selección cruzada por clientes en el informe')
    fig.savefig(out/'ganancia_por_corte.png',dpi=160);plt.close(fig)
    report=['# Exploracion del corte del score','',
      'Se usan modelos202 entrenados en abril y evaluados en mayo. Target LightGBM combinado y TabPFN BAJA+2, mezcla50/50. Sin junio/API/creditos. Se optimiza media de cinco listas, no una lista de probabilidades promedio.',
      '',f'Corte final exploratorio: **{u*100:.1f}%**. Banda de mayo a 1% del maximo: **{band["inicio"]*100:.1f}%–{band["fin"]*100:.1f}%**.',
      '', 'Seleccion cruzada: elegir en 3/4 clientes y evaluar en 1/4, cuatro veces; la suma reconstruye mayo. Cada fold utiliza su corte propio, no simula una entrega con un unico corte.',
      '', '| Regla | Contactos medios | Ganancia total media | 25% local |','|---|---:|---:|---:|']
    for rule,r in summary.iterrows():
        report.append(f'| {rule} | {r.contactos:,.1f} | ${r.ganancia:,.0f} | ${r.ganancia_25pct:,.0f} |')
    report+=['',f'Diferencia cruzada: total ${delta:,.0f}; 25% ${delta/4:,.0f}. Mejoran {positive}/4 particiones.',
        '',meta['limitacion'],'','Ganancia agosto desconocida. No elegir cortes con el publico. Corte2.5% preservado en entregas anteriores.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Salida:',out);print(summary.to_string());print('Corte:',u,'banda:',band,'delta:',delta,'folds mejoran:',positive,'viable:',viable)

if __name__=='__main__':main()
