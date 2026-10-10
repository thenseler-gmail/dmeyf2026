"""TabPFN combinado vs BAJA+2; abril->mayo, LightGBM combinado fijo, sin Bot."""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
import lightgbm as lgb
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
    sel=np.asarray(p)>.025;n=int(sel.sum());tp=int((sel&y).sum());g=tp*1100000-n*27500
    assert int(np.where(y,1072500,-27500)[sel].sum())==g
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4)

def plot(pivot,seeds,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained');pos=np.arange(5)
    for ax,scale,title in [(axes[0],1e6,'Ganancia total'),(axes[1],4e6,'25% de referencia local')]:
        ax.bar(pos-.18,pivot.control_tab_baja2/scale,.36,label='Control: TabPFN BAJA+2',color='#337b9d')
        ax.bar(pos+.18,pivot.ambos_combinado/scale,.36,label='Ambos combinados',color='#cf8b38')
        ax.set(xticks=pos,xticklabels=seeds,ylabel='Millones de pesos',title=title,xlabel='Semilla LightGBM')
        ax.tick_params(axis='x',labelrotation=25);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.legend(loc='outside lower center',ncol=2);fig.suptitle('Abril → mayo, 202 variables, mezcla 50/50, corte 2,5%')
    fig.savefig(out/'comparacion_targets.png',dpi=160);plt.close(fig)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--reanudar',type=Path)
    ap.add_argument('--ejecutar-api',action='store_true');ap.add_argument('--max-creditos',type=int,default=80000)
    ap.add_argument('--sin-grafico',action='store_true');args=ap.parse_args()
    src=SAL/'01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238'
    ref=json.loads((src/'manifest.json').read_text(encoding='utf-8-sig'));cols=ref['features_lightgbm'];seeds=ref['semillas']
    assert ref['validacion_train']==[202104] and ref['validacion_eval']==202105 and len(cols)==202
    control=pd.read_csv(src/'predicciones_mayo.csv')
    assert sha(src/'predicciones_mayo.csv')==ref['hashes_resultados']['predicciones_mayo.csv']
    config=json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(ROOT/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105) ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.eq(202104)].reset_index(drop=True)
    valid=raw.loc[raw.foto_mes.eq(202105)].reset_index(drop=True)
    assert len(train)==163284 and len(valid)==163768 and not raw.duplicated(KEYS).any()
    pd.testing.assert_frame_equal(valid[KEYS+['clase_ternaria']],control[KEYS+['clase_ternaria']])
    xt=preparar(train,cols)[0];xv=preparar(valid,cols)[0]
    yt=train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
    yv=valid.clase_ternaria.eq('BAJA+2').to_numpy()
    signature=dict(features=cols,semillas=seeds,model_version='v3.5-fast',n_estimators=2,seed_tabpfn=214363,
        train=[202104],evaluacion=202105,target_tabpfn='BAJA+1/BAJA+2',target_lightgbm='BAJA+1/BAJA+2',
        train_matrix_sha256=hashlib.sha256(xt.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        valid_matrix_sha256=hashlib.sha256(xv.to_numpy(dtype=np.float32).tobytes()).hexdigest(),
        target_sha256=hashlib.sha256(yt.tobytes()).hexdigest(),source_sha256=sha(src/'predicciones_mayo.csv'),
        codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['58_validar_tabpfn_combinado.py','features.py','baseline.py']})
    if args.reanudar:
        out=args.reanudar;m=json.loads((out/'manifest.json').read_text());assert m['firma']==signature
    else:
        out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('validacion_tabpfn_combinado_%Y%m%d_%H%M%S');out.mkdir()
        m=dict(estado='preparando',firma=signature,umbral=.025,operador='>',peso_tabpfn=.5,api=False,creditos=0,
            fuente_control=str(src),nuevos_fits_lightgbm=0,junio_leido=False,agosto_leido=False,
            limitaciones='Mayo/semillas reutilizados, no test independiente. Abril->mayo no disponibilidad prospectiva completa del target BAJA+2. Misma configuracion del control de entrega8, no evaluacion del fit final abril+mayo. Ambos targets combinados producen score que incluye BAJA+1; ganancia premia solo BAJA+2.')
    # Se completa todo control local antes de llamada API.
    for s in seeds:
        model=lgb.Booster(model_file=str(src/'modelos_validacion'/f'seed{s}.txt'))
        assert model.feature_name()==cols and model.num_trees()==273
        np.testing.assert_allclose(model.predict(xv,validate_features=True),control[f'p_seed{s}'],rtol=0,atol=1e-15)
    m['control_lightgbm_reproducido']=5
    save(out/'manifest.json',m);print('Salida:',out,flush=True)
    path=out/'predicciones_mayo.csv'
    pred=pd.read_csv(path) if path.exists() else control[KEYS+['clase_ternaria']+[f'p_seed{s}' for s in seeds]].copy()
    pd.testing.assert_frame_equal(pred[KEYS+['clase_ternaria']],valid[KEYS+['clase_ternaria']])
    pred['p_tabpfn_baja2']=control.p_tabpfn
    pred.to_csv(path,index=False)
    if 'p_tabpfn_combinado' not in pred and args.ejecutar_api:
        if not os.environ.get('TABPFN_TOKEN'):raise RuntimeError('Falta credencial en memoria')
        from tabpfn_client import TabPFNClassifier,estimate_cost,get_api_usage
        m['cuota_antes']=str(get_api_usage())
        quote=estimate_cost(xt,xv,model_version='v3.5-fast',n_estimators=2)
        m['cotizacion']=quote.model_dump(mode='json');save(out/'manifest.json',m)
        print('Creditos estimados:',quote.estimated_cost,flush=True)
        if quote.estimated_cost>args.max_creditos:raise RuntimeError('Cotizacion supera limite; no inferencia')
        model=TabPFNClassifier.create_default_for_version('v3.5-fast',n_estimators=2,random_state=214363,
            fit_mode='fit_preprocessors',inference_precision='autocast',
            categorical_features_indices=[cols.index(c) for c in ['Visa_status','Master_status','tcuentas']],
            inference_config={'SUBSAMPLE_SAMPLES':None})
        m['estado']='ejecutando_api';save(out/'manifest.json',m)
        model.fit(xt.to_numpy(dtype=np.float32),yt)
        prob=model.predict_proba(xv.to_numpy(dtype=np.float32))[:,list(model.classes_).index(1)]
        assert np.isfinite(prob).all() and ((prob>=0)&(prob<=1)).all()
        pred['p_tabpfn_combinado']=prob;pred.to_csv(path,index=False)
        m.update(api=True,cuota_despues=str(get_api_usage()),creditos_estimados=quote.estimated_cost)
        m['creditos']=int(re.search(r'used (\d+)',m['cuota_despues']).group(1))-int(re.search(r'used (\d+)',m['cuota_antes']).group(1))
        save(out/'manifest.json',m)
    if 'p_tabpfn_combinado' not in pred:
        m['estado']='preparado_api_pendiente';save(out/'manifest.json',m)
        print('Preparacion local verificada. API pendiente; sin credito/submits.',flush=True);return
    results=[]
    for s in seeds:
        for variant,col in [('control_tab_baja2','p_tabpfn_baja2'),('ambos_combinado','p_tabpfn_combinado')]:
            q=(pred[f'p_seed{s}']+pred[col])/2
            assert q.between(0,1).all() and np.isfinite(q).all()
            results.append(dict(variante=variant,seed=s,**medir(yv,q)))
    ind=pd.DataFrame(results);ind.to_csv(out/'resultados_semillas.csv',index=False)
    summary=ind.groupby('variante')[['contactos','tp','fp','fn','ganancia','ganancia_25pct']].mean()
    summary.to_csv(out/'comparacion_media5.csv')
    solo=pd.DataFrame([dict(variante=v,**medir(yv,pred[c])) for v,c in [('TabPFN_BAJA2','p_tabpfn_baja2'),('TabPFN_combinado','p_tabpfn_combinado')]])
    solo.to_csv(out/'tabpfn_solo.csv',index=False)
    avg=pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    pd.DataFrame([dict(variante=v,**medir(yv,(avg+pred[c])/2)) for v,c in [('control_tab_baja2','p_tabpfn_baja2'),('ambos_combinado','p_tabpfn_combinado')]]).to_csv(out/'lista_promedio5.csv',index=False)
    pivot=ind.pivot(index='seed',columns='variante',values='ganancia').loc[seeds]
    delta=pivot.ambos_combinado-pivot.control_tab_baja2
    if not args.sin_grafico:plot(pivot,seeds,out)
    m.update(estado='completo_verificado',delta_media_total=float(delta.mean()),delta_media_25pct=float(delta.mean()/4),
        semillas_mejoran=int((delta>0).sum()),supera_control_local=bool(delta.mean()>0),
        decision='Solo explorar localmente; no preparar entrega final/API agosto en este ensayo.',
        archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},comparacion=summary.reset_index().to_dict('records'))
    save(out/'manifest.json',m)
    save(out/'verificacion.json',dict(estado='verificado',control_modelos_reproducidos=5,ganancias_directas=14,
        target_tabpfn_combinado=True,fit_solo_abril=True,labels_mayo_no_en_fit=True,creditos=m['creditos'],junio=False,agosto=False))
    report=['# Ambos modelos con target combinado','',
        'LightGBM combinado202 y cinco semillas conservados. Solo cambia TabPFN BAJA+2 -> BAJA+1/BAJA+2, misma versionFast2/seed214363, trainabril->mayo,50/50,p>2.5%. Recompensa solo BAJA+2. No entrenamiento final agosto ni submit.','',
        '| Variante | Contactos medios | Ganancia total media5 | 25% local |','|---|---:|---:|---:|']
    for name,r in summary.iterrows():report.append(f'| {name} | {r.contactos:,.1f} | ${r.ganancia:,.0f} | ${r.ganancia_25pct:,.0f} |')
    report+=['',f'Delta total ${delta.mean():,.0f}; 25% ${delta.mean()/4:,.0f}; mejoran {(delta>0).sum()}/5 semillas.',
        '',m['limitaciones'],'',f'Creditos consumidos: {m["creditos"]}. No submits.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string());print('Delta:',delta.mean(),'mejoran:',int((delta>0).sum()),'creditos:',m['creditos'],flush=True)

if __name__=='__main__':main()
