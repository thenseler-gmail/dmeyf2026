"""Evaluacion TabPFN210 vs202 con mismos cinco ensembles189 y corte congelado."""
import hashlib
import importlib
import json
import numpy as np
import pandas as pd

base=importlib.import_module('116_promedio20_hist189')
OUT=base.SAL/'tabpfn210_vinculos_local_20261010'


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    plan=read(OUT/'PLAN.json');m=read(OUT/'payload.json');state=read(OUT/'api_estado.json')
    assert state['estado']=='completo_verificado'
    path=OUT/'predicciones_tab210_mayo.csv';assert base.sha(path)==state['predicciones_sha256']
    p=pd.read_csv(path,float_precision='round_trip')
    control=pd.read_csv(OUT/'predicciones_control_mayo.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(p[control.columns],control)
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();rows=[];parts=[];singles=[];outputs=p.copy()
    for i in range(1,6):
        mean=p[[f'p_lgb_seed{s}' for s in plan['grupos_semillas'][str(i)]]].mean(axis=1).to_numpy()
        q0=.5*mean+.5*p.p_tabpfn.to_numpy();q1=.5*mean+.5*p.p_tab210.to_numpy()
        np.testing.assert_allclose(q0,p[f'score_control_ensemble{i}'],rtol=0,atol=1e-15)
        a=base.metric(y,q0);b=base.metric(y,q1)
        rows.append(dict(ensemble=i,control=a,candidato=b,delta_total=b['ganancia_total']-a['ganancia_total']))
        outputs[f'score_tab210_ensemble{i}']=q1
        for part in range(4):
            ix=p.parte_cliente.eq(part).to_numpy();aa=base.metric(y[ix],q0[ix]);bb=base.metric(y[ix],q1[ix])
            parts.append(dict(ensemble=i,parte=part,delta_total=bb['ganancia_total']-aa['ganancia_total']))
        for s in plan['grupos_semillas'][str(i)]:
            a=base.metric(y,.5*p[f'p_lgb_seed{s}'].to_numpy()+.5*p.p_tabpfn.to_numpy())
            b=base.metric(y,.5*p[f'p_lgb_seed{s}'].to_numpy()+.5*p.p_tab210.to_numpy())
            singles.append(dict(seed=s,control_total=a['ganancia_total'],candidato_total=b['ganancia_total'],delta_total=b['ganancia_total']-a['ganancia_total']))
    assert rows[0]['control']['ganancia_total']==275385000
    outputs.to_csv(OUT/'predicciones_evaluadas_mayo.csv',index=False)
    summary=dict(estado='completo_verificado',ensembles=rows,
        media_delta_ensembles=float(np.mean([r['delta_total'] for r in rows])),
        media_delta_grupos2a5=float(np.mean([r['delta_total'] for r in rows[1:]])),
        ensembles_mejoran=sum(r['delta_total']>0 for r in rows),
        desvio_poblacional_delta_ensembles=float(np.std([r['delta_total'] for r in rows],ddof=0)),
        media_delta_listas_individuales=float(np.mean([r['delta_total'] for r in singles])),
        partes=parts,api_estado=state,final_agosto_ejecutado=False,
        limitacion='Mayo reutilizado y API control historica; no test independiente, no garantia publica. No modificar corte por estos resultados.')
    pd.DataFrame(singles).to_csv(OUT/'deltas_listas_individuales.csv',index=False)
    pd.DataFrame(parts).to_csv(OUT/'deltas_partes.csv',index=False)
    base.save(OUT/'RESULTADO_LOCAL.json',summary)
    text='# TabPFN210 vs202 local\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    (OUT/'INFORME_RESULTADO.md').write_text(text,encoding='utf-8')
    base.save(OUT/'estado.json',dict(estado='completo_verificado_piloto_local',media_delta_ensembles=summary['media_delta_ensembles'],final_agosto=False))
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+text)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
