"""Comparacion solicitada de dos cortes fijos para mix17, sin busqueda ni API."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas'
SOURCE=SAL/'mix_hist189_catboost_20261006_145401'
SEEDS=[541440,408476,741961,248865,717444]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def money(x):return '$'+f'{x:,.0f}'.replace(',','.')

def main():
    m=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo_verificado' and m['train']==[202104] and m['evaluacion']==202105
    assert m['semillas']==SEEDS and m['weights']==dict(lightgbm=.4,tabpfn=.4,catboost=.2)
    for f,h in m['archivos_sha256'].items():assert sha(SOURCE/f)==h
    p=pd.read_csv(SOURCE/'predicciones_mayo.csv')
    assert len(p)==163768 and p.foto_mes.eq(202105).all() and not p.numero_de_cliente.duplicated().any()
    y=p.clase_ternaria.eq('BAJA+2').to_numpy();assert y.sum()==870
    cash=np.where(y,1072500,-27500);rows=[];parts=[];changes=[];scores=[]
    def metric(mask):
        tp=int((mask&y).sum());n=int(mask.sum());g=int(cash[mask].sum())
        assert g==1072500*tp-27500*(n-tp)
        return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)
    for seed in SEEDS:
        q=.4*p[f'p_lgb189_seed{seed}']+.4*p.p_tabpfn+.2*p[f'p_cat202_seed{seed}']
        np.testing.assert_allclose(q,p[f'score_mix_seed{seed}'],rtol=0,atol=1e-15)
        z=np.column_stack([p[f'p_lgb189_seed{seed}'],p.p_tabpfn,p[f'p_cat202_seed{seed}']])@np.array([.4,.4,.2])
        for cut in [.025,.033]:
            mask=np.asarray(q)>cut;np.testing.assert_array_equal(mask,z>cut)
            rows.append(dict(seed=seed,umbral=cut,**metric(mask)))
            for k in range(4):
                area=p.parte_cliente.eq(k).to_numpy();v=metric(mask&area);v['fn']=int((y&area).sum())-v['tp']
                parts.append(dict(seed=seed,umbral=cut,parte=k,**v))
        removed=(np.asarray(q)>.025)&~(np.asarray(q)>.033)
        changes.append(dict(seed=seed,retirados=int(removed.sum()),baja2_retirados=int((removed&y).sum()),
            falsos_positivos_retirados=int((removed&~y).sum()),delta_total=-int(cash[removed].sum()),delta_25pct=-int(cash[removed].sum())/4))
        scores.append(np.asarray(q))
    r=pd.DataFrame(rows);part=pd.DataFrame(parts);ch=pd.DataFrame(changes)
    summary=r.groupby('umbral')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean()
    assert summary.loc[.025,'ganancia']==269813500
    summary['delta_total_vs25']=summary.ganancia-269813500;summary['delta_25pct_vs25']=summary.delta_total_vs25/4
    assert summary.loc[.033,'delta_total_vs25']==ch.delta_total.mean()
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('corte33_mix17_%Y%m%d_%H%M%S');out.mkdir()
    r.to_csv(out/'resultados_semillas.csv',index=False);part.to_csv(out/'resultados_partes.csv',index=False)
    summary.to_csv(out/'comparacion_media5.csv');ch.to_csv(out/'contactos_retirados.csv',index=False)
    pd.DataFrame([dict(umbral=c,**metric(np.mean(scores,axis=0)>c)) for c in [.025,.033]]).to_csv(out/'lista_promedio5.csv',index=False)
    new=summary.loc[.033];wins=int(ch.delta_total.gt(0).sum())
    pv=part.groupby(['umbral','parte']).ganancia.mean().unstack('umbral');wp=int((pv[.033]>pv[.025]).sum())
    result=dict(estado='completo_verificado',train=[202104],evaluacion=202105,semillas=SEEDS,
        pesos=m['weights'],umbrales=[.025,.033],operador='>',comparacion=summary.reset_index().to_dict('records'),
        semillas_mejoran=wins,partes_mejoran=wp,mejora_vs17=bool(new.ganancia>269813500),
        supera_control16=bool(new.ganancia>266420000),nuevos_fits=0,api=False,creditos=0,submits=0,
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [SOURCE/'manifest.json',SOURCE/'predicciones_mayo.csv']},
        archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')},codigo_sha256=sha(Path(__file__)),
        limitaciones='Dos cortes fijos solicitados; no optimizacion del corte de esta mezcla. Mayo y semillas reutilizados; no test independiente ni garantia publica.')
    save(out/'manifest.json',result)
    note=(f'**Prueba de corte3,3% para mix17 completa:** total medio {money(new.ganancia)}, '
          f'25% {money(new.ganancia_25pct)}; diferencia frente a2,5% {money(new.delta_total_vs25)}, '
          f'25% {money(new.delta_25pct_vs25)}. Mejora en {wins}/5 semillas y {wp}/4 partes. '
          f'[Informe](salidas/{out.name}/MINI_INFORME.md). Sin fits/API/submits. '
          'El3,3% proviene de otra mezcla anterior; no es un optimo probado para17.')
    report=['# Mix17: corte 2,5% frente a 3,3%','',note,'',
        '| Corte | Contactos medios | BAJA+2 detectados | Falsos positivos | Ganancia total media | 25% |',
        '| ---: | ---: | ---: | ---: | ---: | ---: |']
    for cut,row in summary.iterrows():report.append(f'| {cut:.1%} | {row.contactos:.1f} | {row.tp:.1f} | {row.fp:.1f} | {money(row.ganancia)} | {money(row.ganancia_25pct)} |')
    report+=['',f'Al subir el corte se retiran en promedio {ch.retirados.mean():.1f} clientes, incluidos {ch.baja2_retirados.mean():.1f} BAJA+2 y {ch.falsos_positivos_retirados.mean():.1f} falsos positivos.',
        '',result['limitaciones'],'',
        'Mismos modelos y predicciones: LightGBM189 combinado/TabPFN202 BAJA+2/CatBoost202 BAJA+2, pesos40/40/20. Solo cambia la decisión de contacto. '
        'Se reconstruyeron scores y selecciones por producto matricial; ganancia verificada con pagos individuales y TP/FP. '
        'No se leyeron junio/agosto ni se generaron nuevos CSV para el Bot en esta comparación. '
        'La entrega17 original y sus listas al2,5% permanecen intactas. El3,3% no se considera un optimo de esta configuración.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    c['corte33_mix17_local']={**result,'fuente':str(out.relative_to(ROOT))};save(cfg,c)
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(s.replace(marker,marker+'\n'+note+'\n',1),encoding='utf-8')
    bit=ROOT/'BITACORA_DMEYF.md'
    with bit.open('a',encoding='utf-8') as f:f.write('\n## 103. Corte3,3% de mezcla17 evaluado localmente - 2026-10-06\n\n'+note+'\n\n'+result['limitaciones']+'\n')
    print(summary.to_string());print('Semillas mejoran:',wins,'Partes mejoran:',wp);print('Retirados medios:',ch.mean(numeric_only=True).to_dict());print('Salida:',out)

if __name__=='__main__':main()
