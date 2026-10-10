"""Audita alineacion de fuentes y ganancias de mezcla sin fits ni API."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
KEYS=['numero_de_cliente','foto_mes','clase_ternaria','parte_cliente']
SEEDS=[541440,408476,741961,248865,717444]
CONTROL='control_16_LGB189_Tab202_50_50'
MIX='mix_LGB189_Tab202_Cat202_40_40_20'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['train']==[202104] and m['evaluacion']==202105 and m['semillas']==SEEDS
    assert m['weights']==dict(lightgbm=.4,tabpfn=.4,catboost=.2)
    assert m['features_lightgbm']==189 and m['features_catboost']==m['features_tabpfn']==202
    assert m['target_lightgbm']=='BAJA+1/BAJA+2' and m['target_catboost']==m['target_tabpfn']=='BAJA+2'
    assert m['umbral']==.025 and m['operador']=='>' and m['nuevos_fits']==m['creditos']==m['submits']==0
    assert not m['api'] and not m['junio_leido'] and not m['agosto_leido'] and not m['fit_eval_set']
    assert sha(Path(__file__).parent/'68_mix_hist189_catboost_local.py')==m['codigo_sha256']
    for name,h in m['source_hashes'].items():assert sha(ROOT/name)==h
    for name,h in m['archivos_sha256'].items():assert sha(out/name)==h
    light=ROOT/m['fuente_lightgbm'];cat=ROOT/m['fuente_catboost']
    lp=pd.read_csv(light/'historia_1_mes/predicciones_mayo.csv');cp=pd.read_csv(cat/'predicciones_mayo.csv')
    p=pd.read_csv(out/'predicciones_mayo.csv')
    pd.testing.assert_frame_equal(lp[KEYS],cp[KEYS]);pd.testing.assert_frame_equal(p[KEYS],lp[KEYS])
    assert len(p)==m['filas_mayo']==163768 and p.foto_mes.eq(202105).all() and not p.numero_de_cliente.duplicated().any()
    assert p.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    np.testing.assert_allclose(p.p_tabpfn,lp.p_tabpfn,rtol=0,atol=1e-15)
    np.testing.assert_allclose(p.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
    scores={};parts=p.parte_cliente.to_numpy();y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    assert y.sum()==870
    for seed in SEEDS:
        np.testing.assert_allclose(p[f'p_lgb189_seed{seed}'],lp[f'p_seed{seed}'],rtol=0,atol=1e-15)
        np.testing.assert_allclose(p[f'p_cat202_seed{seed}'],cp[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        values=np.column_stack([lp[f'p_seed{seed}'],cp.p_tabpfn,cp[f'p_cat_seed{seed}']])
        scores[(CONTROL,seed)]=values@np.array([.5,.5,0.])
        scores[(MIX,seed)]=values@np.array([.4,.4,.2])
        for v,col in [(CONTROL,f'score_control_seed{seed}'),(MIX,f'score_mix_seed{seed}')]:
            np.testing.assert_allclose(scores[(v,seed)],p[col],rtol=0,atol=1e-15)
            np.testing.assert_array_equal(scores[(v,seed)]>.025,p[col]>.025)
    def check(r,sel):
        tp=int((sel&y).sum());fp=int((sel&~y).sum());g=1072500*tp-27500*fp
        assert g==r.ganancia and r.ganancia_25pct==g/4
        assert r.tp==tp and r.fp==fp and r.contactos==tp+fp
    r=pd.read_csv(out/'resultados_semillas.csv');assert len(r)==10
    for row in r.itertuples():check(row,scores[(row.variante,row.seed)]>.025)
    pr=pd.read_csv(out/'resultados_partes_mayo.csv');assert len(pr)==40
    for row in pr.itertuples():check(row,(scores[(row.variante,row.seed)]>.025)&(parts==row.parte))
    changes=pd.read_csv(out/'cambios_contactos.csv');assert len(changes)==10
    for row in changes.itertuples():
        old=scores[(CONTROL,row.seed)]>.025;new=scores[(row.variante,row.seed)]>.025
        add=new&~old;remove=old&~new
        assert add.sum()==row.agregados and remove.sum()==row.retirados
        assert (add&y).sum()==row.agregados_baja2 and (remove&y).sum()==row.retirados_baja2
        assert (add&~y).sum()==row.agregados_fp and (remove&~y).sum()==row.retirados_fp
        delta=1072500*((new&y).sum()-(old&y).sum())-27500*((new&~y).sum()-(old&~y).sum())
        assert delta==(row.agregados_baja2-row.retirados_baja2)*1100000-(row.agregados-row.retirados)*27500
    summary=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
    means=r.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean()
    np.testing.assert_allclose(summary[means.columns],means.loc[summary.index],rtol=0,atol=1e-8)
    assert summary.loc[CONTROL,'ganancia']==266420000
    pivot=r.pivot(index='seed',columns='variante',values='ganancia').loc[SEEDS]
    dif=pivot[MIX]-pivot[CONTROL]
    partsmean=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    for v,row in summary.iterrows():
        assert row.delta_total==row.ganancia-266420000 and row.delta_25pct==row.delta_total/4
        assert row.semillas_mejoran==(pivot[v]>pivot[CONTROL]).sum()
        assert row.partes_mejoran==(partsmean[v]>partsmean[CONTROL]).sum()
    differences=pd.read_csv(out/'diferencias_semillas.csv').set_index('seed')
    np.testing.assert_allclose(dif,differences.loc[SEEDS,'delta_total'],rtol=0,atol=0)
    assert m['supera_control_16_local']==bool(summary.loc[MIX,'ganancia']>266420000)
    avg=pd.read_csv(out/'lista_promedio5.csv')
    meanlb=lp[[f'p_seed{s}' for s in SEEDS]].mean(axis=1).to_numpy()
    meancb=cp[[f'p_cat_seed{s}' for s in SEEDS]].mean(axis=1).to_numpy()
    for row in avg.itertuples():
        q=(meanlb+cp.p_tabpfn.to_numpy())/2 if row.variante==CONTROL else np.column_stack(
            [meanlb,cp.p_tabpfn,meancb])@np.array([.4,.4,.2])
        check(row,q>.025)
    verification=dict(estado='verificado',alineacion_id_mes_target_parte=True,predicciones_fuente_verificadas=True,
        score_y_selecciones_independientes=True,ganancias_semillas=10,ganancias_partes=40,cambios_contactos=10,
        listas_promedio5=2,control16_local_reproducido=True,nuevos_fits=0,creditos=0,submits=0,
        catboost_features=202,lightgbm_features=189,codigo_verificador_sha256=sha(Path(__file__)))
    (out/'verificacion_independiente.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    m['estado']='completo_verificado'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(verification,indent=2),flush=True)


if __name__=='__main__':main()
