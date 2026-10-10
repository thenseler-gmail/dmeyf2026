"""Mezcla local LGB189/Tab202/Cat202 40/40/20; predicciones ya verificadas."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
LIGHT=SAL/'features_local_20261006_140702'
CAT=SAL/'catboost_local_20261006_004259'
KEYS=['numero_de_cliente','foto_mes','clase_ternaria','parte_cliente']
SEEDS=[541440,408476,741961,248865,717444]
VARIANTS=['control_16_LGB189_Tab202_50_50','mix_LGB189_Tab202_Cat202_40_40_20']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def cargar():
    lm=json.loads((LIGHT/'manifest.json').read_text(encoding='utf-8'))
    cm=json.loads((CAT/'manifest.json').read_text(encoding='utf-8'))
    for path,meta in [(LIGHT,lm),(CAT,cm)]:
        assert meta['estado']=='completo_verificado'
        assert meta['train']==[202104] and meta['evaluacion']==202105
        assert meta['firma']['seeds']==SEEDS and not meta['fit_eval_set']
        assert json.loads((path/'verificacion_independiente.json').read_text())['estado']=='verificado'
        for f,h in meta['firma']['codigo_sha256'].items():assert sha(Path(__file__).parent/f)==h
        for f,h in meta['archivos_sha256'].items():assert sha(path/f)==h
    lightpath=LIGHT/'historia_1_mes/predicciones_mayo.csv';catpath=CAT/'predicciones_mayo.csv'
    lp=pd.read_csv(lightpath);cp=pd.read_csv(catpath)
    assert len(lp)==len(cp)==163768 and lp.foto_mes.eq(202105).all()
    assert not lp.numero_de_cliente.duplicated().any() and not cp.numero_de_cliente.duplicated().any()
    pd.testing.assert_frame_equal(lp[KEYS],cp[KEYS])
    assert lp.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    np.testing.assert_allclose(lp.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
    assert len(lm['firma']['variants']['historia_1_mes']['features'])==189
    assert len(cm['firma']['features'])==202 and cm['firma']['target']=='BAJA+2'
    assert lm['firma']['target_train']=='BAJA+1/BAJA+2'
    for seed in SEEDS:
        lpath=LIGHT/'historia_1_mes'/f'seed{seed}.txt'
        cpath=CAT/'modelos'/f'seed{seed}.cbm'
        assert sha(lpath)==lm['modelos_sha256'][str(lpath.relative_to(LIGHT))]
        assert sha(cpath)==cm['modelos_sha256'][cpath.name]
    return lm,cm,lp,cp


def score(p,seed,variant,mean=False):
    lb=p[[f'p_lgb189_seed{s}' for s in SEEDS]].mean(axis=1) if mean else p[f'p_lgb189_seed{seed}']
    cb=p[[f'p_cat202_seed{s}' for s in SEEDS]].mean(axis=1) if mean else p[f'p_cat202_seed{seed}']
    return (lb+p.p_tabpfn)/2 if variant==VARIANTS[0] else .4*lb+.4*p.p_tabpfn+.2*cb


def metric(y,p):
    sel=np.asarray(p)>.025;n=int(sel.sum());tp=int((sel&y).sum())
    g=int(np.where(y,1072500,-27500)[sel].sum())
    assert g==tp*1100000-n*27500
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)


def main():
    lm,cm,lp,cp=cargar()
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('mix_hist189_catboost_%Y%m%d_%H%M%S')
    out.mkdir()
    p=lp[KEYS+['p_tabpfn']].copy()
    for seed in SEEDS:
        p[f'p_lgb189_seed{seed}']=lp[f'p_seed{seed}']
        p[f'p_cat202_seed{seed}']=cp[f'p_cat_seed{seed}']
        p[f'score_control_seed{seed}']=score(p,seed,VARIANTS[0]) if seed==SEEDS[-1] else (lp[f'p_seed{seed}']+lp.p_tabpfn)/2
        p[f'score_mix_seed{seed}']=.4*lp[f'p_seed{seed}']+.4*lp.p_tabpfn+.2*cp[f'p_cat_seed{seed}']
    p.to_csv(out/'predicciones_mayo.csv',index=False)
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();parts=p.parte_cliente.to_numpy()
    rows=[];partrows=[];changes=[]
    for seed in SEEDS:
        base=score(p,seed,VARIANTS[0])>.025
        for v in VARIANTS:
            q=score(p,seed,v);rows.append(dict(variante=v,seed=seed,**metric(y,q)))
            for k in range(4):
                mask=parts==k;partrows.append(dict(variante=v,seed=seed,parte=k,**metric(y[mask],q[mask])))
            sel=q>.025;add=sel&~base;remove=base&~sel
            changes.append(dict(variante=v,seed=seed,agregados=int(add.sum()),retirados=int(remove.sum()),
                agregados_baja2=int((add&y).sum()),retirados_baja2=int((remove&y).sum()),
                agregados_fp=int((add&~y).sum()),retirados_fp=int((remove&~y).sum())))
    r=pd.DataFrame(rows);r.to_csv(out/'resultados_semillas.csv',index=False)
    pr=pd.DataFrame(partrows);pr.to_csv(out/'resultados_partes_mayo.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    pivot=r.pivot(index='seed',columns='variante',values='ganancia').loc[SEEDS]
    dif=pivot[VARIANTS[1]]-pivot[VARIANTS[0]]
    pd.DataFrame(dict(seed=SEEDS,control_total=pivot[VARIANTS[0]],control_25pct=pivot[VARIANTS[0]]/4,
                      mix_total=pivot[VARIANTS[1]],mix_25pct=pivot[VARIANTS[1]]/4,
                      delta_total=dif,delta_25pct=dif/4)).to_csv(out/'diferencias_semillas.csv',index=False)
    summary=r.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean().loc[VARIANTS]
    summary['desvio_ganancia_semillas']=r.groupby('variante').ganancia.std(ddof=1)
    summary['delta_total']=summary.ganancia-summary.loc[VARIANTS[0],'ganancia']
    summary['delta_25pct']=summary.delta_total/4
    summary['delta_pct']=summary.delta_total/summary.loc[VARIANTS[0],'ganancia']*100
    summary['semillas_mejoran']=[0,int((dif>0).sum())]
    ps=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['partes_mejoran']=[0,int((ps[VARIANTS[1]]>ps[VARIANTS[0]]).sum())]
    summary.to_csv(out/'comparacion_media5.csv')
    pd.DataFrame([dict(variante=v,**metric(y,score(p,SEEDS[0],v,True))) for v in VARIANTS]).to_csv(out/'lista_promedio5.csv',index=False)
    assert summary.loc[VARIANTS[0],'ganancia']==266420000
    winner=bool(summary.loc[VARIANTS[1],'delta_total']>0)
    m=dict(estado='completo_pendiente_verificacion',train=[202104],evaluacion=202105,semillas=SEEDS,
        weights=dict(lightgbm=.4,tabpfn=.4,catboost=.2),control_weights=dict(lightgbm=.5,tabpfn=.5),
        features_lightgbm=189,features_tabpfn=202,features_catboost=202,
        target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',target_catboost='BAJA+2',
        filas_mayo=len(p),umbral=.025,operador='>',api=False,creditos=0,submits=0,nuevos_fits=0,
        junio_leido=False,agosto_leido=False,fit_eval_set=False,supera_control_16_local=winner,
        fuente_lightgbm=str(LIGHT.relative_to(ROOT)),fuente_catboost=str(CAT.relative_to(ROOT)),
        source_hashes={str(path.relative_to(ROOT)):sha(path) for path in
                      [LIGHT/'manifest.json',CAT/'manifest.json',LIGHT/'historia_1_mes/predicciones_mayo.csv',
                       CAT/'predicciones_mayo.csv',LIGHT/'verificacion_independiente.json',CAT/'verificacion_independiente.json']},
        archivos_sha256={path.name:sha(path) for path in out.glob('*.csv')},
        codigo_sha256=sha(Path(__file__)),resultados=summary.reset_index().to_dict('records'),
        control_publico_actual=dict(entrega=16,mean=96.9210,std_dev=1.7816),
        decision='Mejora local: candidato para revisar; no preparar ni enviar automaticamente.' if winner else
                 'No supera control16 local: no preparar submit de esta mezcla.',
        limitaciones='Mayo y semillas reutilizados: no test independiente ni garantia publica. Partes mismo mes, no meses nuevos. '
                     'CatBoost conserva202variables y parametros fijos; no se probo CatBoost189 ni Optuna. '
                     'Pesos40/40/20 y corte congelados, sin barrido de pesos. Mezcla targets distintos es score, no P(BAJA+2) calibrada.')
    save(out/'manifest.json',m)
    print('Salida:',out,flush=True);print(summary.to_string(),flush=True)


if __name__=='__main__':main()
