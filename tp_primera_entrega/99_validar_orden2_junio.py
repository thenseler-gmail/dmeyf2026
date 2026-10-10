"""Marzo–mayo→junio: ablación189 vs213 con parámetros16 y cinco semillas.

Junio autorizado explícitamente por el usuario para este diagnóstico temporal.
No tuning con junio, API, scoring agosto ni envío al Bot.
"""
import argparse
import hashlib
import importlib
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from baseline import preparar
from features_catedra import construir, verificar

pipe=importlib.import_module('89_catedra_pipeline')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path);args=ap.parse_args()
    out=args.salida or pipe.SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('orden2_junio_%Y%m%d_%H%M%S')
    out.mkdir(exist_ok=bool(args.salida));print('Salida:',out,flush=True)
    unused,cols=pipe.fuentes();refdir=pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235'
    ref=json.loads((refdir/'manifest.json').read_text(encoding='utf-8'))
    params=ref['firma']['params'];rounds=273
    config=json.loads((pipe.TP/'config.json').read_text(encoding='utf-8'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(pipe.ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105,202106) '
                    'ORDER BY foto_mes,numero_de_cliente').df()
    assert raw.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    raw,audit=construir(raw)
    tr=raw[raw.foto_mes.isin([202103,202104,202105])].reset_index(drop=True)
    va=raw[raw.foto_mes.eq(202106)].reset_index(drop=True)
    assert len(tr)==489952 and len(va)==164114
    del raw
    yt=tr.clase_ternaria.ne('CONTINUA').astype(int)
    yc=va.clase_ternaria.ne('CONTINUA').astype(int)
    y=va.clase_ternaria.eq('BAJA+2').to_numpy()
    permutation=np.random.default_rng(214363).permutation(len(va))
    parts=np.empty(len(va),dtype=int);parts[permutation]=np.arange(len(va))%4
    pred=va[pipe.KEYS+['clase_ternaria']].copy();pred['parte_cliente']=parts
    signature=dict(train=[202103,202104,202105],validacion=202106,params=params,rounds=rounds,
          semillas=pipe.SEEDS,features_control=cols,features_orden2=cols+pipe.ORDEN2,
          audit=audit,undersampling=False,target_train='BAJA+1/BAJA+2',target_premio='BAJA+2',
          codigo={f:pipe.sha(pipe.TP/f) for f in ['99_validar_orden2_junio.py','features_catedra.py','calidad_datos.py','features.py','baseline.py']},
          label_train_sha256=hashlib.sha256(yt.to_numpy().tobytes()).hexdigest(),
          label_junio_sha256=hashlib.sha256(y.tobytes()).hexdigest())
    manifest=out/'manifest.json'
    if manifest.exists():assert json.loads(manifest.read_text(encoding='utf-8'))['firma']==signature
    state=dict(estado='entrenando',firma=signature,api=False,creditos=0,submits=0,
          autorizacion='Usuario: si, usemos junio para verificar si el lag2 nos sirve',
          lag2_observable_train=int(tr.lag_2_ctrx_quarter.notna().sum()),
          lag2_observable_junio=int(va.lag_2_ctrx_quarter.notna().sum()),
          limitacion='Junio con aguinaldo; partes de clientes no son meses independientes. '
                     'Se compara el bloque24 lag2/delta2 en conjunto, no sus efectos separados.')
    pipe.save(manifest,state);rows=[];partrows=[];changes=[];meanrows=[]
    for name,features in [('control189',cols),('orden2_213',cols+pipe.ORDEN2)]:
        md=out/name;md.mkdir(exist_ok=True)
        xt=preparar(tr,features)[0];xv=preparar(va,features)[0]
        state.setdefault('matrices_sha256',{})[name]=dict(train=hashlib.sha256(xt.to_numpy().tobytes()).hexdigest(),
                 valid=hashlib.sha256(xv.to_numpy().tobytes()).hexdigest())
        for s in pipe.SEEDS:
            print('Entrenando',name,s,flush=True)
            q,n,seconds=pipe.fit_cached(md/f'seed{s}.txt',xt,yt,xv,dict(params,seed=s),rounds)
            assert n==rounds
            pred[f'{name}_seed{s}']=q
            rows.append(dict(variante=name,seed=s,auc_combinado=roc_auc_score(yc,q),
                     auc_baja2=roc_auc_score(y,q),segundos=seconds,**pipe.metric(y,q,va.numero_de_cliente)))
            for k in range(4):
                mask=parts==k
                partrows.append(dict(variante=name,seed=s,parte=k,**pipe.metric(y[mask],q[mask],va.numero_de_cliente[mask])))
            if name=='orden2_213':
                old=pred[f'control189_seed{s}'].to_numpy()>.025;new=q>.025
                changes.append(dict(seed=s,agregados=int((new&~old).sum()),retirados=int((old&~new).sum()),
                        ganancia_agregados=int(np.where(y,1072500,-27500)[new&~old].sum()),
                        ganancia_retirados=int(np.where(y,1072500,-27500)[old&~new].sum())))
            pred.to_csv(out/'predicciones_junio.csv',index=False)
            pd.DataFrame(rows).to_csv(out/'resultados_semillas.csv',index=False)
            pipe.save(manifest,state)
        mean=pred[[f'{name}_seed{s}' for s in pipe.SEEDS]].mean(axis=1)
        for n in [None,10000,10500,11000,11500,12000]:
            meanrows.append(dict(variante=name,corte='p>.025' if n is None else 'top'+str(n),
                              **pipe.metric(y,mean,va.numero_de_cliente,n)))
        del xt,xv
    r=pd.DataFrame(rows);pr=pd.DataFrame(partrows)
    summary=r.groupby('variante')[['auc_combinado','auc_baja2','contactos','tp','fp','ganancia','ganancia_25pct']].mean()
    summary.to_csv(out/'resumen.csv');pr.to_csv(out/'resultados_partes.csv',index=False)
    pd.DataFrame(meanrows).to_csv(out/'cortes_promedio5.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    pivot=r.pivot(index='seed',columns='variante',values='ganancia');delta=pivot.orden2_213-pivot.control189
    pd.DataFrame(dict(seed=delta.index,delta_total=delta.to_numpy(),delta_25pct=delta.to_numpy()/4)).to_csv(out/'diferencias_semillas.csv',index=False)
    groups=pr.groupby(['variante','parte']).ganancia.mean().unstack('variante')
    dif=float(summary.loc['orden2_213','ganancia']-summary.loc['control189','ganancia'])
    state.update(estado='completo_verificado',delta_total=dif,delta_25pct=dif/4,
          semillas_mejoran=int((delta>0).sum()),partes_mejoran=int((groups.orden2_213>groups.control189).sum()),
          modelos_sha256={str(p.relative_to(out)):pipe.sha(p) for p in out.glob('*/seed*.txt')})
    pipe.save(manifest,state)
    money=lambda v:'$'+f'{v:,.0f}'.replace(',','.')
    report=['# Históricos orden2: marzo–mayo → junio','',
      'LightGBM solo, target combinado; premio exclusivamente BAJA+2. Mismos parámetros16,273 árboles '
      'y cinco semillas. Sin undersampling ni tuning con junio. Corrección ccajas_depositos mayo en ambos.','',
      '| Variables | Contactos medios | Ganancia total media | 25% |','| --- | ---: | ---: | ---: |']
    for name,row in summary.iterrows():report.append(f'| {name} | {row.contactos:.1f} | {money(row.ganancia)} | {money(row.ganancia_25pct)} |')
    report+=['',f'Diferencia orden2: {money(dif)} total;25% {money(dif/4)}. Mejora {state["semillas_mejoran"]}/5 semillas y '
      f'{state["partes_mejoran"]}/4 partes de junio.','',
      f'Historia orden2 observable para ctrx_quarter: {state["lag2_observable_train"]} filas train, '
      f'{state["lag2_observable_junio"]} junio. Mayo sí permite aprender el bloque nuevo.','',
      'La tabla es media de ganancias de cinco listas, no ganancia del promedio de probabilidades. '
      'Los cortes del promedio están en cortes_promedio5.csv. Junio tiene aguinaldo; no garantiza agosto. '
      'Se modifica el bloque de24 columnas y el muestreo de features; no atribuir causalmente a un lag individual. '
      'No se entrenó TabPFN ni se consumieron créditos ni se envió al Bot.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string(),flush=True);print('Delta',dif,'25%',dif/4,flush=True)


if __name__=='__main__':main()
