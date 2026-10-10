"""Cambio aislado de target LightGBM: abril->mayo, TabPFN BAJA+2 guardado."""
import argparse
import hashlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'
KEYS=['numero_de_cliente','foto_mes']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,m):p.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def medir(y,p):
    selected=np.asarray(p)>.025
    tp=int((selected&y).sum());n=int(selected.sum());gain=tp*1100000-n*27500
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=gain,ganancia_25pct=gain/4)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    src=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    ref=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'))
    assert ref['validacion_train']==[202104] and ref['validacion_eval']==202105
    cols=ref['features_lightgbm'];seeds=ref['semillas'];spec=ref['elegido']
    assert len(cols)==202 and ref['features_tabpfn']==cols and spec['target']=='bajas'
    assert len(seeds)==5 and spec['num_boost_round']==273
    sourcefile=src/'predicciones_mayo.csv'
    assert sha(sourcefile)==ref['hashes_resultados']['predicciones_mayo.csv']
    control=pd.read_csv(sourcefile)
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text(encoding='utf-8-sig'))
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.eq(202104)].reset_index(drop=True)
    valid=raw.loc[raw.foto_mes.eq(202105)].reset_index(drop=True)
    assert not raw.duplicated(KEYS).any() and len(valid)==163768
    pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],control[KEYS+['clase_ternaria']])
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    assert valid.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    xt=preparar(train,cols)[0];xv=preparar(valid,cols)[0]
    y=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy();yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    signature=dict(source_sha256=sha(sourcefile),features=cols,seeds=seeds,params=spec['params'],rounds=273,
        train_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        valid_sha256=hashlib.sha256(xv.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        target_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['57_validar_targets_ensemble.py','features.py','baseline.py']})
    if args.reanudar:
        out=args.reanudar;m=json.loads((out/'manifest.json').read_text());assert m['firma']==signature
    else:
        out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('validacion_targets_ensemble_%Y%m%d_%H%M%S');out.mkdir()
        m=dict(estado='ejecutando',firma=signature,train=[202104],evaluacion=202105,
             historia_auxiliar=[202103],features=cols,semillas=seeds,target_nuevo='BAJA+2',target_control='BAJA+1/BAJA+2',
             target_tabpfn='BAJA+2',peso_tabpfn=.5,umbral=.025,operador='>',api=False,creditos=0,
             nuevos_fits=5,fuente_predicciones=str(sourcefile),junio_leido=False,agosto_leido=False,
             filas_train=len(train),filas_evaluacion=len(valid),versiones={p:importlib.metadata.version(p) for p in ['lightgbm','numpy','pandas','duckdb']},
             limitaciones='Mayo y semillas reutilizados; abril->mayo no replica disponibilidad prospectiva de target BAJA+2. Una ventana, sin test independiente. Parametros congelados optimizados para target combinado: aislar target no compara mejores ajustes de cada target. Partes de mayo no son meses independientes.')
    save(out/'manifest.json',m);md=out/'modelos';md.mkdir(exist_ok=True)
    pred=valid[KEYS+['clase_ternaria']].copy();pred['p_tabpfn']=control.p_tabpfn
    results=[];changes=[];reproduced=[]
    print('Salida:',out,flush=True)
    for s in seeds:
        oldmodel=lgb.Booster(model_file=str(src/'modelos_validacion'/f'seed{s}.txt'))
        assert oldmodel.feature_name()==cols and oldmodel.num_trees()==273
        oldprob=oldmodel.predict(xv,validate_features=True)
        np.testing.assert_allclose(oldprob,control[f'p_seed{s}'],rtol=0,atol=1e-15)
        mp=md/f'seed{s}.txt'
        if mp.exists():model=lgb.Booster(model_file=str(mp))
        else:
            model=lgb.train(dict(spec['params'],seed=s),lgb.Dataset(xt,label=y),num_boost_round=273)
            model.save_model(str(mp))
        newprob=model.predict(xv,validate_features=True)
        reload=lgb.Booster(model_file=str(mp));assert reload.feature_name()==cols and reload.num_trees()==273
        np.testing.assert_allclose(reload.predict(xv,validate_features=True),newprob,rtol=0,atol=0)
        pred[f'p_control_seed{s}']=oldprob;pred[f'p_baja2_seed{s}']=newprob
        for variant,p in [('control_combinado',oldprob),('nuevo_baja2',newprob)]:
            for mode,q in [('LightGBM_solo',p),('mezcla50_50',(p+pred.p_tabpfn.to_numpy())/2)]:
                assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
                results.append(dict(variante=variant,modelo=mode,seed=s,**medir(yv,q)))
        oldsel=(oldprob+pred.p_tabpfn.to_numpy())/2>.025
        newsel=(newprob+pred.p_tabpfn.to_numpy())/2>.025
        added=newsel&~oldsel;removed=oldsel&~newsel
        changes.append(dict(seed=s,agregados=int(added.sum()),agregados_baja2=int((added&yv).sum()),
              retirados=int(removed.sum()),retirados_baja2=int((removed&yv).sum())))
        pred.to_csv(out/'predicciones_mayo.csv',index=False);reproduced.append(s)
        print('BAJA+2 semilla',s,'lista',flush=True)
    individual=pd.DataFrame(results);individual.to_csv(out/'resultados_semillas.csv',index=False)
    summary=individual.groupby(['variante','modelo'])[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean().reset_index()
    summary.to_csv(out/'comparacion_media5.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos.csv',index=False)
    # Ganancia de una lista de probabilidades promedio es una metrica separada.
    avg=[]
    for variant,prefix in [('control_combinado','p_control'),('nuevo_baja2','p_baja2')]:
        prob=pred[[f'{prefix}_seed{s}' for s in seeds]].mean(axis=1)
        for mode,q in [('LightGBM_solo',prob),('mezcla50_50',(prob+pred.p_tabpfn)/2)]:
            avg.append(dict(variante=variant,modelo=mode,**medir(yv,q)))
    pd.DataFrame(avg).to_csv(out/'comparacion_lista_promedio5.csv',index=False)
    # Ganancias en cuatro partes por clientes, sin seleccionar corte ni pesos.
    fold=np.empty(len(pred),dtype=int);perm=np.random.default_rng(214363).permutation(len(pred));fold[perm]=np.arange(len(pred))%4
    parts=[]
    for s in seeds:
        for variant,prefix in [('control_combinado','p_control'),('nuevo_baja2','p_baja2')]:
            q=(pred[f'{prefix}_seed{s}'].to_numpy()+pred.p_tabpfn.to_numpy())/2
            for k in range(4):parts.append(dict(variante=variant,seed=s,parte=k,**medir(yv[fold==k],q[fold==k])))
    pd.DataFrame(parts).to_csv(out/'resultados_partes_mayo.csv',index=False)
    gains=individual.loc[individual.modelo.eq('mezcla50_50')].pivot(index='seed',columns='variante',values='ganancia').loc[seeds]
    delta=gains.nuevo_baja2-gains.control_combinado
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained');pos=np.arange(5)
    for ax,scale,title in [(axes[0],1e6,'Ganancia total'),(axes[1],4e6,'25% de referencia local')]:
        ax.bar(pos-.18,gains.control_combinado/scale,width=.36,label='LGB combinado + Tab BAJA+2',color='#337b9d')
        ax.bar(pos+.18,gains.nuevo_baja2/scale,width=.36,label='Ambos BAJA+2',color='#cf8b38')
        ax.set(xticks=pos,xticklabels=[str(s) for s in seeds],xlabel='Semilla LightGBM',ylabel='Millones de pesos',title=title)
        ax.tick_params(axis='x',labelrotation=25);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.legend(fontsize=8)
    fig.suptitle('Abril → mayo, 202 variables, mezcla 50/50 y corte 2,5%')
    fig.savefig(out/'comparacion_targets.png',dpi=160);plt.close(fig)
    m.update(estado='completo_verificado',delta_mezcla_media_total=float(delta.mean()),
        delta_mezcla_media_25pct=float(delta.mean()/4),semillas_mejoran=int((delta>0).sum()),
        modelos_nuevos_sha256={p.name:sha(p) for p in md.glob('*.txt')},
        archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},
        comparacion_media5=summary.to_dict('records'))
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',modelos_control_reproducidos=5,modelos_nuevos_reproducidos=5,
         fit_solo_abril=True,etiquetas_mayo_no_en_fit=True,junio_leido=False,agosto_leido=False,api=False,creditos=0))
    report=['# Comparacion local de targets','',
        'Cambio aislado: LightGBM combinado -> BAJA+2. TabPFN BAJA+2 guardado y reproducido por referencia. Ambos entrenados en abril; evaluacion mayo. Mismas202variables/273rondas/params/semillas,50/50,p>0.025. Marzo solo predictor historico. Sin API/creditos/submits ni entrenamiento final agosto.','',
        '| Variante | Modelo | Contactos medios | Ganancia total media5 | 25% local |','|---|---|---:|---:|---:|']
    for r in summary.itertuples():report.append(f'| {r.variante} | {r.modelo} | {r.contactos:,.1f} | ${r.ganancia:,.0f} | ${r.ganancia_25pct:,.0f} |')
    report+=['',f'Mezcla: diferencia media total ${delta.mean():,.0f}; 25% ${delta.mean()/4:,.0f}. Mejoran {(delta>0).sum()}/5 semillas.',
      '',m['limitaciones'],'','Archivos de lista promedio5 y partes de mayo son comprobaciones adicionales, no pruebas independientes ni envios al Bot. Ganancias no comparables directamente con publico agosto.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string(index=False));print('Delta mezcla:',delta.mean(),'semillas mejoran:',int((delta>0).sum()),flush=True)

if __name__=='__main__':main()
