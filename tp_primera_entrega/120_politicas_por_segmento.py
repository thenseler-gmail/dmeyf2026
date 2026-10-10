"""Pesos o cortes por segmento: selección con3partes de mayo y evaluación en la cuarta."""
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
ROOT=base.ROOT;TP=base.TP;OUT=base.SAL/'estrategias_segmentos_20261010'
WEIGHTS=[.25,.375,.5,.625,.75]
CUTS=[.02,.0225,.025,.0275,.03,.0325,.035]
POLICIES=['pesos_globales','pesos_por_segmento','corte_global','cortes_por_segmento']
def freeze():
    OUT.mkdir(exist_ok=True)
    plan=dict(pesos_lightgbm=WEIGHTS,cortes=CUTS,politicas=POLICIES,
        fuente='LightGBM general189 + TabPFN202; segmentos aprendidos solo en abril',
        evaluacion='Cuatro partes preexistentes por cliente; elegir con3, evaluar cuarta; rotar',
        separacion='Optimizar solo peso a corte2,75% fijo o solo corte con pesos50/50',
        desempate='Regla más cercana a referencia36, luego valor menor',
        baseline=dict(peso=.5,corte=.0275),minimo_clientes_seleccion_grupo=500,
        criterio='Superar regla fija y regla global seleccionada con mismas partes',
        limitacion='Mayo reutilizado; cruces por cliente no son un test temporal independiente',
        api=False,creditos=0,submits=0,codigo_sha256=base.sha(Path(__file__)))
    p=OUT/'PLAN_POLITICAS.json'
    if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==plan
    else:base.save(p,plan)
    return plan
def choose(y,lgb,tab,ix,kind):
    baseline=.5 if kind=='peso' else .0275
    candidates=WEIGHTS if kind=='peso' else CUTS
    records=[]
    for value in candidates:
        w=value if kind=='peso' else .5;cut=.0275 if kind=='peso' else value
        select=(w*lgb[ix]+(1-w)*tab[ix])>cut
        gain=int(np.where(y[ix],1072500,-27500)[select].sum())
        records.append((gain,-abs(value-baseline),-value,value))
    return max(records)[3]
def metric(y,q,cut):
    sel=q>cut;n=int(sel.sum());tp=int((sel&y).sum())
    gain=int(np.where(y,1072500,-27500)[sel].sum());assert gain==1100000*tp-27500*n
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia_total=gain,ganancia_25pct=gain/4)
def main():
    plan=freeze()
    result=json.loads((OUT/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    path=OUT/'predicciones_mayo.csv';assert base.sha(path)==result['predicciones_sha256']
    p=pd.read_csv(path,float_precision='round_trip')
    seeds=json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))['semillas']
    probabilities=p[[f'p_general_seed{s}' for s in seeds]].to_numpy()
    lgb=probabilities.mean(axis=1);tab=p.p_tabpfn.to_numpy();y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    groups=p.segmento.to_numpy();folds=p.parte_cliente.to_numpy()
    assert set(groups)==set(folds)=={0,1,2,3}
    baseline_score=.5*lgb+.5*tab;control=metric(y,baseline_score,.0275)
    assert control['ganancia_total']==275385000
    selections=[];summary=[];diagnostic=[];foldresults=[]
    pred=p[['numero_de_cliente','foto_mes','clase_ternaria','segmento','parte_cliente']].copy()
    for policy in POLICIES:
        kind='peso' if policy.startswith('pesos') else 'corte'
        segmented='por_segmento' in policy
        weights=np.full(len(p),np.nan);cuts=np.full(len(p),np.nan)
        for fold in range(4):
            hold=folds==fold;learn=~hold
            for group in (range(4) if segmented else [-1]):
                train=learn&(groups==group) if segmented else learn
                test=hold&(groups==group) if segmented else hold
                value=choose(y,lgb,tab,train,kind) if train.sum()>=500 else (.5 if kind=='peso' else .0275)
                w=value if kind=='peso' else .5;cut=.0275 if kind=='peso' else value
                weights[test]=w;cuts[test]=cut
                selections.append(dict(politica=policy,fold_evaluado=fold,segmento=group,clientes_seleccion=int(train.sum()),peso_lgb=w,corte=cut))
        assert np.isfinite(weights).all() and np.isfinite(cuts).all()
        score=weights*lgb+(1-weights)*tab
        pred[f'peso_{policy}']=weights;pred[f'corte_{policy}']=cuts;pred[f'score_{policy}']=score
        row=dict(politica=policy,**metric(y,score,cuts))
        row['delta_fijo_total']=row['ganancia_total']-control['ganancia_total'];row['delta_fijo25pct']=row['delta_fijo_total']/4
        individual=[metric(y,weights*probabilities[:,i]+(1-weights)*tab,cuts)['ganancia_total'] for i in range(5)]
        individual0=[metric(y,.5*probabilities[:,i]+.5*tab,.0275)['ganancia_total'] for i in range(5)]
        row['media_delta_semillas']=float(np.mean(individual)-np.mean(individual0));row['semillas_mejoran']=sum(a>b for a,b in zip(individual,individual0))
        for group in range(4):
            ix=groups==group;a=metric(y[ix],baseline_score[ix],.0275);b=metric(y[ix],score[ix],cuts[ix])
            diagnostic.append(dict(politica=policy,segmento=group,**b,delta_total=b['ganancia_total']-a['ganancia_total']))
        for fold in range(4):
            ix=folds==fold;a=metric(y[ix],baseline_score[ix],.0275);b=metric(y[ix],score[ix],cuts[ix])
            foldresults.append(dict(politica=policy,fold=fold,delta_total=b['ganancia_total']-a['ganancia_total']))
        row['partes_mejoran']=sum(r['delta_total']>0 for r in foldresults if r['politica']==policy)
        assert sum(r['delta_total'] for r in diagnostic if r['politica']==policy)==row['delta_fijo_total']
        summary.append(row)
    for row in summary:
        peer='pesos_globales' if row['politica'].startswith('pesos') else 'corte_global'
        globalrow=next(r for r in summary if r['politica']==peer)
        row['delta_vs_global_equivalente']=row['ganancia_total']-globalrow['ganancia_total']
    pred.to_csv(OUT/'predicciones_politicas_crossfit.csv',index=False)
    pd.DataFrame(summary).to_csv(OUT/'comparacion_politicas_crossfit.csv',index=False)
    pd.DataFrame(selections).to_csv(OUT/'reglas_por_fold.csv',index=False)
    pd.DataFrame(diagnostic).to_csv(OUT/'politicas_por_segmento.csv',index=False)
    pd.DataFrame(foldresults).to_csv(OUT/'politicas_por_fold.csv',index=False)
    # Recalculate rules from three parts after permuting labels in the held-out part.
    rng=np.random.default_rng(214363)
    for r in selections:
        fold=r['fold_evaluado'];group=r['segmento'];train=folds!=fold
        if group!=-1:train &= groups==group
        altered=y.copy();altered[folds==fold]=rng.permutation(altered[folds==fold])
        kind='peso' if r['politica'].startswith('pesos') else 'corte'
        value=choose(altered,lgb,tab,train,kind)
        assert value==(r['peso_lgb'] if kind=='peso' else r['corte'])
    saved=pd.read_csv(OUT/'predicciones_politicas_crossfit.csv',float_precision='round_trip')
    for row in summary:
        name=row['politica'];a=metric(y,saved[f'score_{name}'].to_numpy(),saved[f'corte_{name}'].to_numpy())
        assert all(row[k]==v for k,v in a.items())
    eligible=[r['politica'] for r in summary if 'por_segmento' in r['politica'] and r['delta_fijo_total']>0 and r['delta_vs_global_equivalente']>0 and r['media_delta_semillas']>0]
    output=dict(estado='completo_verificado',control=control,resumen=summary,candidatos=eligible,
        etiquetas_holdout_no_cambian_reglas=True,api=False,creditos=0,submits=0,
        predicciones_sha256=base.sha(OUT/'predicciones_politicas_crossfit.csv'),fuente_sha256=result['predicciones_sha256'],
        limitacion=plan['limitacion'])
    base.save(OUT/'RESULTADO_POLITICAS.json',output)
    text='# Pesos y cortes por segmento\n\nCuatro segmentos aprendidos en abril. En cada cruce se eligen pesos o cortes con tres partes de clientes de mayo y se aplican a la cuarta. Se comparan también reglas globales elegidas de la misma forma. No optimizar peso y corte simultáneamente.\n\nControl fijo total $275.385.000;25% $68.846.250.\n\n```text\n'+pd.DataFrame(summary).to_string(index=False)+'\n```\n\n'
    text+=f'Candidatos que mejoran regla fija, regla global equivalente y media de semillas: {eligible}.\n\n'
    text+='Modificar etiquetas de la parte evaluada no cambia la regla elegida; ganancias reconstruidas desde archivos. Mayo y semillas reutilizados, no test temporal independiente. Los cruces por cliente no eliminan todo el sesgo histórico. Sin API, créditos ni nuevo submit. No elegir retrospectivamente la combinación perfecta por segmento con todos los datos y presentar esa ganancia como validada.\n'
    (OUT/'INFORME_POLITICAS.md').write_text(text,encoding='utf-8')
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Políticas por segmento — 2026-10-10\n\n'+text+'\n')
    steps=TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
