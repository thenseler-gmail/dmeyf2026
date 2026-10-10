"""Elegir general/especialista/mezcla por grupo con3partes y medir en la cuarta."""
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
OUT=base.SAL/'estrategias_segmentos_20261010'
NAMES=['general','general50_especialista50','especialistas']
def main():
    plan=dict(estrategias=NAMES,reglas=['modelo_global_elegido','modelo_por_segmento_elegido'],
        seleccion='Ganancia promedio5 a corte2,75%; tres partes para elegir y cuarta para medir; cuatro cruces',
        desempate='Priorizar general, luego mezcla, luego especialistas',api=False,creditos=0,
        codigo_sha256=base.sha(Path(__file__)))
    base.save(OUT/'PLAN_SELECCION_MODELOS.json',plan)
    source=json.loads((OUT/'RESULTADO_LOCAL.json').read_text(encoding='utf-8'))
    assert base.sha(OUT/'predicciones_mayo.csv')==source['predicciones_sha256']
    p=pd.read_csv(OUT/'predicciones_mayo.csv',float_precision='round_trip')
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();pay=np.where(y,1072500,-27500)
    groups=p.segmento.to_numpy();folds=p.parte_cliente.to_numpy()
    seeds=json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))['semillas']
    general=p[[f'p_general_seed{s}' for s in seeds]].to_numpy()
    special=p[[f'p_especialista_seed{s}' for s in seeds]].to_numpy();tab=p.p_tabpfn.to_numpy()[:,None]
    arrays={'general':.5*general+.5*tab,'especialistas':.5*special+.5*tab,
        'general50_especialista50':.25*general+.25*special+.5*tab}
    scores={n:arrays[n].mean(axis=1) for n in NAMES}
    control=base.metric(y,scores['general']);rows=[];rules=[]
    out=p[['numero_de_cliente','foto_mes','clase_ternaria','segmento','parte_cliente']].copy()
    def choose(ix,payoffs):
        gains=[int(payoffs[ix][scores[n][ix]>.0275].sum()) for n in NAMES]
        return NAMES[int(np.argmax(gains))]
    for policy in plan['reglas']:
        segmented='por_segmento' in policy
        q=np.full((len(p),5),np.nan);assigned=np.full(len(p),'',dtype=object)
        for fold in range(4):
            learn=folds!=fold;hold=~learn
            for group in (range(4) if segmented else [-1]):
                train=learn&(groups==group) if segmented else learn
                test=hold&(groups==group) if segmented else hold
                name=choose(train,pay);q[test]=arrays[name][test];assigned[test]=name
                modified=pay.copy();modified[hold]=0
                assert choose(train,modified)==name
                rules.append(dict(politica=policy,fold=fold,segmento=group,modelo=name))
        assert np.isfinite(q).all() and np.all(assigned!='')
        avg=q.mean(axis=1);a=base.metric(y,avg)
        deltas=[base.metric(y,q[:,i])['ganancia_total']-base.metric(y,arrays['general'][:,i])['ganancia_total'] for i in range(5)]
        row=dict(politica=policy,**a,delta_total=a['ganancia_total']-control['ganancia_total'],
            media_delta_semillas=float(np.mean(deltas)),semillas_mejoran=sum(d>0 for d in deltas))
        row['delta25pct']=row['delta_total']/4;rows.append(row)
        out[f'score_{policy}']=avg;out[f'modelo_{policy}']=assigned
    globalrow=rows[0]
    rows[1]['delta_vs_global_elegido']=rows[1]['ganancia_total']-globalrow['ganancia_total']
    out.to_csv(OUT/'predicciones_seleccion_modelos.csv',index=False)
    pd.DataFrame(rows).to_csv(OUT/'comparacion_seleccion_modelos.csv',index=False)
    pd.DataFrame(rules).to_csv(OUT/'modelos_elegidos_por_fold.csv',index=False)
    saved=pd.read_csv(OUT/'predicciones_seleccion_modelos.csv',float_precision='round_trip')
    for row in rows:
        q=saved[f"score_{row['politica']}"].to_numpy()
        assert int(pay[q>.0275].sum())==row['ganancia_total']
    result=dict(estado='completo_verificado',control=control,resumen=rows,
        holdout_no_modifica_reglas=True,api=False,creditos=0,submits=0,
        predicciones_sha256=base.sha(OUT/'predicciones_seleccion_modelos.csv'),
        limitacion='Mayo/semillas reutilizados, no test temporal independiente. No elegir por segmento sobre todos los datos y medir allí mismo.')
    base.save(OUT/'RESULTADO_SELECCION_MODELOS.json',result)
    text='# Elegir estrategia de modelo por segmento\n\nPara cada segmento se elige entre general, especialista y su mezcla50/50, con tres partes de clientes de mayo. Se mide en la cuarta parte y se rota. Pesos LightGBM/TabPFN50/50 y corte2,75% fijos. Comparación adicional con un único modelo elegido globalmente en los mismos cruces.\n\n```text\n'+pd.DataFrame(rows).to_string(index=False)+'\n```\n\nMayo y semillas reutilizados; no test temporal independiente ni garantía pública. No nueva API ni entrenamiento adicional ni entrega. Etiquetas de la parte evaluada no afectan elección; ganancias reconstruidas desde archivos.\n'
    (OUT/'INFORME_SELECCION_MODELOS.md').write_text(text,encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## Elección de modelo por segmento — 2026-10-10\n\n'+text+'\n')
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(text+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
