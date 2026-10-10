"""Compara las ocho mezclas guardadas, sin fits, API ni envios."""
import hashlib
import itertools
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
OLD=SAL/'catboost_local_20261006_004259'
NEW=SAL/'todos189_local_20261006_150519'
KEYS=['numero_de_cliente','foto_mes']
SEEDS=[541440,408476,741961,248865,717444]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(x):return '$'+f'{x:,.0f}'.replace(',','.')

def main():
    for d in [OLD,NEW]:
        m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
        assert m['estado']=='completo_verificado'
        assert json.loads((d/'verificacion_independiente.json').read_text())['estado']=='verificado'
        for f,h in m['archivos_sha256'].items():assert sha(d/f)==h
    a=pd.read_csv(OLD/'predicciones_mayo.csv');b=pd.read_csv(NEW/'predicciones_mayo.csv')
    pd.testing.assert_frame_equal(a[KEYS+['clase_ternaria','parte_cliente']],b[KEYS+['clase_ternaria','parte_cliente']])
    np.testing.assert_allclose(a.p_tabpfn,b.p_tab202,rtol=0,atol=1e-15)
    assert len(b)==163768 and b.foto_mes.eq(202105).all() and not b.numero_de_cliente.duplicated().any()
    for seed in SEEDS:
        np.testing.assert_allclose(a[f'p_cat_seed{seed}'],b[f'p_cat202_seed{seed}'],rtol=0,atol=1e-15)
        b[f'p_lgb202_seed{seed}']=a[f'p_lgb_seed{seed}']
    y=b.clase_ternaria.eq('BAJA+2').to_numpy();assert y.sum()==870
    parts=b.parte_cliente.to_numpy();payments=np.where(y,1072500,-27500)
    rows=[];prows=[];avg=[]
    def metric(q,mask=None):
        sel=q>.025
        if mask is not None:sel=sel&mask
        n=int(sel.sum());tp=int((sel&y).sum());g=tp*1100000-n*27500
        assert g==payments[sel].sum()
        return dict(contactos=n,tp=tp,fp=n-tp,ganancia=g,ganancia_25pct=g/4)
    for l,t,c in itertools.product([189,202],repeat=3):
        name=f'LGB{l}_Tab{t}_Cat{c}';qs=[]
        for seed in SEEDS:
            lb=b[f'p_lgb{l}_seed{seed}'].to_numpy();tb=b[f'p_tab{t}'].to_numpy();cb=b[f'p_cat{c}_seed{seed}'].to_numpy()
            q=.4*lb+.4*tb+.2*cb
            independent=np.column_stack([lb,tb,cb])@np.array([.4,.4,.2])
            np.testing.assert_array_equal(q>.025,independent>.025)
            assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
            rows.append(dict(variante=name,lightgbm=l,tabpfn=t,catboost=c,seed=seed,**metric(q)))
            for k in range(4):prows.append(dict(variante=name,seed=seed,parte=k,**metric(q,parts==k)))
            qs.append(q)
        avg.append(dict(variante=name,**metric(np.mean(qs,axis=0))))
    r=pd.DataFrame(rows);pr=pd.DataFrame(prows)
    summary=r.groupby(['variante','lightgbm','tabpfn','catboost'])[['contactos','tp','fp','ganancia','ganancia_25pct']].mean().reset_index()
    pivot=r.pivot(index='seed',columns='variante',values='ganancia')
    control='LGB189_Tab202_Cat202'
    groups=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    summary['delta_vs17_total']=summary.ganancia-269813500;summary['delta_vs17_25pct']=summary.delta_vs17_total/4
    summary['semillas_mejoran_vs17']=[int((pivot[v]>pivot[control]).sum()) for v in summary.variante]
    summary['partes_mejoran_vs17']=[int((groups[v]>groups[control]).sum()) for v in summary.variante]
    summary=summary.sort_values(['ganancia','variante'],ascending=[False,True]).reset_index(drop=True)
    idx=summary.set_index('variante')
    assert idx.loc[control,'ganancia']==269813500
    assert idx.loc['LGB202_Tab202_Cat202','ganancia']==261833000
    prev=pd.read_csv(NEW/'comparacion_media5.csv').set_index('variante')
    for name,v in [('LGB189_Tab189_Cat189','todos189_40_40_20'),('LGB189_Tab202_Cat189','cat189_tab202'),
                   ('LGB189_Tab189_Cat202','cat202_tab189'),(control,'mix17_40_40_20')]:
        assert idx.loc[name,'ganancia']==prev.loc[v,'ganancia']
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('combinaciones189_202_%Y%m%d_%H%M%S');out.mkdir()
    r.to_csv(out/'resultados_semillas.csv',index=False);pr.to_csv(out/'resultados_partes_mayo.csv',index=False)
    summary.to_csv(out/'comparacion_media5.csv',index=False);pd.DataFrame(avg).to_csv(out/'lista_promedio5.csv',index=False)
    best=summary.iloc[0].to_dict()
    m=dict(estado='completo_verificado',train=[202104],evaluacion=202105,semillas=SEEDS,
           pesos=dict(lightgbm=.4,tabpfn=.4,catboost=.2),umbral=.025,operador='>',
           targets=dict(lightgbm='BAJA+1/BAJA+2',tabpfn='BAJA+2',catboost='BAJA+2'),
           criterio='Mayor ganancia media de cinco listas individuales, no mejor semilla ni lista promedio.',
           mejor=best,resultados=summary.to_dict('records'),nuevos_fits=0,api=False,creditos=0,submits=0,
           source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [OLD/'manifest.json',OLD/'predicciones_mayo.csv',
               NEW/'manifest.json',NEW/'predicciones_mayo.csv',NEW/'verificacion_independiente.json']},
           archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},codigo_sha256=sha(Path(__file__)),
           limitacion='Mayo y semillas reutilizados. Ocho comparaciones retrospectivas, no test independiente ni garantia del publico.')
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',filas=163768,baja2=870,
        claves_etiquetas_partes_iguales=True,seleccion_equivalente_producto_matricial=True,
        ganancias_tp_fp_verificadas=40,ganancias_partes_verificadas=160,controles_previos_reproducidos=5))
    report=['# Ocho combinaciones de 189 y 202 variables','',
        f'**Mejor local: {best["variante"]}**, total medio {money(best["ganancia"])}; 25% {money(best["ganancia_25pct"])}.','',
        'Abril → mayo; cinco semillas fijas; LightGBM combinado y TabPFN/CatBoost BAJA+2. Pesos 40/40/20; corte estricto >0,025. Predicciones guardadas; cero fits, API, créditos y envíos.','',
        '| LightGBM | TabPFN | CatBoost | Total medio | 25% | Delta total vs17 | 25% del delta | Semillas mejores vs17 |',
        '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in summary.itertuples():report.append(f'| {row.lightgbm} | {row.tabpfn} | {row.catboost} | {money(row.ganancia)} | {money(row.ganancia_25pct)} | {money(row.delta_vs17_total)} | {money(row.delta_vs17_25pct)} | {row.semillas_mejoran_vs17}/5 |')
    report+=['',m['limitacion'],'',
        'La métrica principal es la media de cinco ganancias, como el lote de cinco CSV del Bot. La lista única por promedio de predicciones figura aparte; no se usa para elegir la ganadora.','',
        'Fuentes verificadas por hashes y alineación exacta de clientes, mes, etiquetas y partes. Selecciones reproducidas con producto matricial y ganancias calculadas por TP/FP y pagos individuales. Junio y agosto no se leen para esta comparación.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string(index=False));print('Salida:',out);print('Mejor:',best['variante'])

if __name__=='__main__':main()
