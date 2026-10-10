"""Ablación 5 frente 20 semillas: configuración16, pesos50/50, corte2,75%."""
import hashlib
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd

TP=Path(__file__).resolve().parent
ROOT=TP.parent
SAL=TP/'salidas'
BOT=SAL/'01_entregas_bot'
D16=BOT/'16_EnsembleHist1895_20261006_143235'
D36=BOT/'36_Ensemble16Promedio5Corte275_20261009_192946'
LOCAL=SAL/'features_local_20261006_140702'
OUT=SAL/'promedio20_hist189_20261010'
CUT=.0275
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def metric(y,q):
    selected=q>CUT
    tp=int((selected&y).sum());n=int(selected.sum())
    gain=int(np.where(y,1072500,-27500)[selected].sum())
    assert gain==1100000*tp-27500*n
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia_total=gain,ganancia_25pct=gain/4)
def run_models(xt,xp,y,seeds,params,folder,reuse,expected,prefix):
    folder.mkdir(exist_ok=True);values=[];hashes={}
    for s in seeds:
        start=time.perf_counter();original=reuse/f'seed{s}.txt';path=original if original.exists() else folder/f'seed{s}.txt'
        if original.exists():assert sha(original)==expected[path.name]
        if path.exists():model=lgb.Booster(model_file=str(path))
        else:
            model=lgb.train(dict(params,seed=s),lgb.Dataset(xt,label=y),num_boost_round=273)
            model.save_model(str(path))
        assert model.feature_name()==list(xt) and model.num_trees()==273
        q=model.predict(xp,validate_features=True,num_threads=4)
        np.testing.assert_array_equal(q,lgb.Booster(model_file=str(path)).predict(xp,validate_features=True,num_threads=4))
        assert np.isfinite(q).all() and ((q>=0)&(q<=1)).all()
        values.append(q);hashes[str(path.relative_to(ROOT))]=sha(path)
        print(prefix,s,'reutilizado' if original.exists() else 'nuevo',round(time.perf_counter()-start,2),'s',flush=True)
    return np.column_stack(values),hashes
def main():
    OUT.mkdir(exist_ok=True)
    m16=json.loads((D16/'manifest.json').read_text(encoding='utf-8'))
    m36=json.loads((D36/'manifest.json').read_text(encoding='utf-8'))
    lm=json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8'))
    seeds=m16['firma']['seeds'].copy()
    rng=np.random.default_rng(20261010)
    while len(seeds)<20:
        s=int(rng.integers(1,1000000))
        if s not in seeds:seeds.append(s)
    plan=dict(semillas=seeds,regla_semillas='Cinco actuales +15 de default_rng(20261010), sin selección por ganancia',
        params=m16['firma']['params'],rounds=273,features=m16['firma']['features'],pesos=dict(lightgbm=.5,tabpfn=.5),umbral=CUT,
        train_local=[202104],eval_local=202105,train_final=[202104,202105],futuro=202108,
        criterio_promocion='Ganancia de única lista promedio20 superior a promedio5, mismo corte y mismas filas de mayo',
        api=False,creditos=0,fuentes={str(p.relative_to(ROOT)):sha(p) for p in [D16/'manifest.json',D36/'manifest.json',LOCAL/'manifest.json']},
        codigo_sha256={Path(__file__).name:sha(Path(__file__))})
    if (OUT/'PLAN.json').exists():assert json.loads((OUT/'PLAN.json').read_text(encoding='utf-8'))==plan
    else:save(OUT/'PLAN.json',plan)
    save(OUT/'estado.json',dict(estado='validacion_local',semillas=seeds))
    mod=importlib.import_module('63_experimentos_features_local')
    _,oldseeds,train,valid,xt,xv,_=mod.cargar()
    cols=plan['features'];xt=xt[cols];xv=xv[cols]
    assert mod.matrix_sha(xt)==lm['firma']['variants']['historia_1_mes']['train_sha256']
    assert mod.matrix_sha(xv)==lm['firma']['variants']['historia_1_mes']['mayo_sha256']
    lp=LOCAL/'historia_1_mes/predicciones_mayo.csv'
    assert sha(lp)==lm['archivos_sha256']['historia_1_mes\\predicciones_mayo.csv']
    p=pd.read_csv(lp,float_precision='round_trip')
    pd.testing.assert_frame_equal(p[mod.KEYS+['clase_ternaria']],valid[mod.KEYS+['clase_ternaria']])
    expected={f'seed{s}.txt':lm['modelos_sha256'][f'historia_1_mes\\seed{s}.txt'] for s in oldseeds}
    values,localhash=run_models(xt,xv,train.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int),seeds,plan['params'],OUT/'modelos_mayo',LOCAL/'historia_1_mes',expected,'Mayo')
    np.testing.assert_allclose(values[:,:5],p[[f'p_seed{s}' for s in oldseeds]],rtol=0,atol=1e-15)
    q5=.5*values[:,:5].mean(axis=1)+.5*p.p_tabpfn.to_numpy()
    q20=.5*values.mean(axis=1)+.5*p.p_tabpfn.to_numpy()
    y=p.clase_ternaria.eq('BAJA+2').to_numpy()
    control=metric(y,q5);candidate=metric(y,q20)
    assert control['ganancia_total']==275385000
    result=dict(control5=control,candidato20=candidate,delta_total=candidate['ganancia_total']-control['ganancia_total'],
        modelos_sha256=localhash,partes=[])
    for part in sorted(p.parte_cliente.unique()):
        sel=p.parte_cliente.to_numpy()==part
        a=metric(y[sel],q5[sel]);b=metric(y[sel],q20[sel])
        result['partes'].append(dict(parte=int(part),control5=a,candidato20=b,delta_total=b['ganancia_total']-a['ganancia_total']))
    assert sum(r['delta_total'] for r in result['partes'])==result['delta_total']
    pred=p[mod.KEYS+['clase_ternaria','parte_cliente','p_tabpfn']].copy()
    for i,s in enumerate(seeds):pred[f'p_lgb_seed{s}']=values[:,i]
    pred['score_promedio5']=q5;pred['score_promedio20']=q20
    pred.to_csv(OUT/'predicciones_mayo.csv',index=False)
    reread=pd.read_csv(OUT/'predicciones_mayo.csv',float_precision='round_trip')
    assert metric(y,reread.score_promedio20.to_numpy())==candidate
    result['predicciones_sha256']=sha(OUT/'predicciones_mayo.csv');save(OUT/'RESULTADO_LOCAL.json',result)
    print('RESULTADO_LOCAL',json.dumps(result,ensure_ascii=False),flush=True)
    note=f"# Promedio de20 semillas\n\nControl5: total ${control['ganancia_total']:,};25% ${control['ganancia_25pct']:,}. Candidato20: total ${candidate['ganancia_total']:,};25% ${candidate['ganancia_25pct']:,}. Delta total ${result['delta_total']:,};25% ${result['delta_total']/4:,}.\n\nPesos50/50 y corte>2,75% congelados. Mayo y las cinco semillas originales reutilizados; no test independiente ni garantía pública. TabPFN guardado, cero API/créditos.\n"
    if result['delta_total']<=0:
        save(OUT/'estado.json',dict(estado='completo_verificado_no_promovido',delta_total=result['delta_total']))
        note+='\nNo supera el control local. Sin entrenamiento final ni nueva entrega.\n'
        (OUT/'MINI_INFORME.md').write_text(note,encoding='utf-8')
    else:
        del xt,xv,train,valid,values,p,pred,reread
        save(OUT/'estado.json',dict(estado='entrenamiento_final',delta_total=result['delta_total']))
        final=importlib.import_module('66_preparar_entrega_hist189')
        _,_,fcols,_,_,ft,fa,fy,keys,_=final.cargar()
        assert fcols==cols and final.matrix_sha(ft)==m16['firma']['matriz_train_sha256'] and final.matrix_sha(fa)==m16['firma']['matriz_agosto_sha256']
        assert hashlib.sha256(fy.tobytes()).hexdigest()==m16['firma']['target_train_sha256']
        old=pd.read_csv(D16/'predicciones_agosto.csv',float_precision='round_trip')
        assert sha(D16/'predicciones_agosto.csv')==m16['archivos_sha256']['predicciones_agosto.csv']
        pd.testing.assert_frame_equal(keys,old[mod.KEYS])
        fv,fh=run_models(ft,fa,fy,seeds,plan['params'],OUT/'modelos_agosto',D16/'modelos',m16['modelos_sha256'],'Agosto')
        np.testing.assert_allclose(fv[:,:5],old[[f'p_lgb_seed{s}' for s in oldseeds]],rtol=0,atol=1e-15)
        controlpred=pd.read_csv(D36/'predicciones_agosto.csv',float_precision='round_trip')
        assert sha(D36/'predicciones_agosto.csv')==m36['predicciones_sha256']
        pd.testing.assert_frame_equal(keys,controlpred[mod.KEYS])
        np.testing.assert_allclose(.5*fv[:,:5].mean(axis=1)+.5*old.p_tabpfn,controlpred.score_promedio5,rtol=0,atol=1e-15)
        number=max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
        name='EnsembleHist189Promedio20Corte275_20261010';delivery=BOT/f'{number}_{name}'
        delivery.mkdir();(delivery/'adjuntos').mkdir()
        apred=keys.copy();apred['p_tabpfn']=old.p_tabpfn
        for i,s in enumerate(seeds):apred[f'p_lgb_seed{s}']=fv[:,i]
        apred['score_promedio20']=.5*fv.mean(axis=1)+.5*old.p_tabpfn
        np.testing.assert_allclose(apred.score_promedio20,np.mean(.5*fv+.5*old.p_tabpfn.to_numpy()[:,None],axis=1),rtol=0,atol=1e-15)
        selected=apred.loc[apred.score_promedio20>CUT].sort_values(['score_promedio20','numero_de_cliente'],ascending=[False,True])
        csv=delivery/'adjuntos'/f'{name}.csv';csv.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
        apred.to_csv(delivery/'predicciones_agosto.csv',index=False)
        meta=dict(estado='preparado_pendiente_verificacion',enviado=False,entrega=number,submit=name,
            firma=plan,semillas=seeds,train_final=[202104,202105],futuro=202108,features_lightgbm=189,features_tabpfn=202,
            target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',agregacion='promedio_probabilidades20',pesos=plan['pesos'],umbral=CUT,operador='>',
            fuente_entrega=str(D16.relative_to(ROOT)),fuente_control=str(D36.relative_to(ROOT)),fuente_validacion=str(OUT.relative_to(ROOT)),
            predicciones_sha256=sha(delivery/'predicciones_agosto.csv'),modelos_sha256=fh,validacion_local=result,
            api=False,creditos=0,nuevos_fits_lightgbm=30,nuevos_fits_tabpfn=0,
            archivos=[dict(score_columna='score_promedio20',archivo=str(csv.relative_to(delivery)),contactos=len(selected),sha256=sha(csv))],
            limitacion='Mayo reutilizado; cinco semillas originales seleccionadas previamente. Sin garantía pública, referencia36 preservada.')
        save(delivery/'manifest.json',meta)
        subprocess.run([sys.executable,str(TP/'105_reproducir_csv_entrega.py'),'--entrega',str(delivery),'--salida',str(OUT/'reproduccion')],check=True)
        meta['estado']='completo_verificado_preparado_pendiente';save(delivery/'manifest.json',meta)
        (delivery/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
        (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envío manual, un solo CSV.\n',encoding='utf-8')
        note+=f'\nEntrega{number} preparada: {len(selected)}clientes. Comando `submit {name}`. Resultado público pendiente.\n'
        (delivery/'INFORME.md').write_text(note,encoding='utf-8');(OUT/'MINI_INFORME.md').write_text(note,encoding='utf-8')
        importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
        save(OUT/'estado.json',dict(estado='completo_verificado_entrega_preparada',entrega=number,carpeta=str(delivery.relative_to(ROOT))))
    for f in [ROOT/'BITACORA_DMEYF.md',TP/'NEXT_STEPS_IDEAS.md']:
        with f.open('a',encoding='utf-8') as stream:stream.write('\n## Promedio20 semillas — 2026-10-10\n\n'+note+'\n')
    for path,h in plan['fuentes'].items():assert sha(ROOT/path)==h
    print('COMPLETO',flush=True)
if __name__=='__main__':main()
