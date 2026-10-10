"""Entrena CatBoost ganador abril+mayo y prepara mezcla40/40/20 si supera16 local."""
import argparse
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier,Pool
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas';BOT=SAL/'01_entregas_bot'
D16=BOT/'16_EnsembleHist1895_20261006_143235'
D17=BOT/'17_EnsembleHist189CatBoost5_20261006_145854'
SEEDS=[541440,408476,741961,248865,717444];KEYS=['numero_de_cliente','foto_mes']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--local',type=Path,required=True);ap.add_argument('--reanudar',type=Path);args=ap.parse_args()
    local=args.local.resolve();m=json.loads((local/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo_verificado' and m['supera16'] and m['semillas']==SEEDS
    assert json.loads((local/'verificacion.json').read_text())['estado']=='verificado'
    for f,h in m['archivos_sha256'].items():assert sha(local/f)==h
    for f,h in m['source_hashes'].items():assert sha(ROOT/f)==h
    frozen=json.loads((local/'seleccion_congelada.json').read_text(encoding='utf-8'))
    assert frozen['params']==m['params_elegidos'] and frozen['seleccionado_solo_abril']
    assert m['params_elegidos']!=m['firma']['base'],'Ganador igual al baseline: usar entrega17 existente, no duplicar.'
    # Reusa constructor final ya verificado para202 y categorias; solo etiquetas abril/mayo.
    loader=importlib.import_module('61_preparar_ensemble_catboost')
    ref,unused,cols,seeds,xt,xp,y,keys,old=loader.cargar()
    assert seeds==SEEDS and cols==m['firma']['features'] and len(xt)==327052 and len(xp)==164647
    lm=json.loads((D16/'manifest.json').read_text(encoding='utf-8'))
    assert lm['train_final']==[202104,202105] and lm['futuro']==202108 and lm['target_lightgbm']=='BAJA+1/BAJA+2'
    assert json.loads((D16/'verificacion_independiente.json').read_text())['estado']=='verificado'
    for f,h in lm['archivos_sha256'].items():assert sha(D16/f)==h
    for f,h in lm['modelos_sha256'].items():assert sha(D16/'modelos'/f)==h
    lgb=pd.read_csv(D16/'predicciones_agosto.csv');pd.testing.assert_frame_equal(keys,lgb[KEYS])
    np.testing.assert_allclose(lgb.p_tabpfn,old.p_tabpfn,rtol=0,atol=1e-15)
    old17=pd.read_csv(D17/'predicciones_agosto.csv');pd.testing.assert_frame_equal(keys,old17[KEYS])
    signature=dict(features=cols,params=m['params_elegidos'],seeds=SEEDS,
        matriz_train_catboost_sha256=loader.hash_frame(xt),matriz_agosto_catboost_sha256=loader.hash_frame(xp),
        target_sha256=hashlib.sha256(y.tobytes()).hexdigest(),local_manifest_sha256=sha(local/'manifest.json'),
        lgb16_predictions_sha256=sha(D16/'predicciones_agosto.csv'),codigo_sha256=sha(Path(__file__)))
    if args.reanudar:
        out=args.reanudar.resolve();meta=json.loads((out/'manifest.json').read_text());assert meta['firma']==signature
    else:
        number=max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
        name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleCatBoostOptuna5_%Y%m%d_%H%M%S')
        out=BOT/f'{number}_{name}';out.mkdir()
        meta=dict(estado='entrenando_final',entrega=number,submit=name+'_semillas',enviado=False,firma=signature,
            train_final=[202104,202105],futuro=202108,features_lightgbm=189,features_tabpfn=202,features_catboost=202,
            target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',target_catboost='BAJA+2',
            semillas=SEEDS,pesos=dict(lightgbm=.4,tabpfn=.4,catboost=.2),umbral=.025,operador='>',
            local_trial=m['trial_elegido'],fuente_local=str(local.relative_to(ROOT)),fuente_lightgbm_tabpfn=str(D16.relative_to(ROOT)),
            source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [local/'manifest.json',local/'seleccion_congelada.json',D16/'manifest.json',D16/'predicciones_agosto.csv',D17/'predicciones_agosto.csv']},
            nuevos_fits_catboost=5,api=False,creditos=0,submits=0,fit_eval_set=False,etiquetas_extraidas=[202104,202105],
            junio_julio_solo_historia=True,semillas_completadas=[],validacion_local=m['resultados'],
            limitacion=m['limitacion'])
    save(out/'manifest.json',meta);md=out/'modelos_catboost';md.mkdir(exist_ok=True)
    trpool=Pool(xt,label=y,cat_features=m['firma']['cat_features']);vp=Pool(xp,cat_features=m['firma']['cat_features'])
    pred=keys.copy();pred['p_tabpfn']=lgb.p_tabpfn
    print('Salida final:',out,flush=True)
    for seed in SEEDS:
        path=md/f'seed{seed}.cbm'
        if not path.exists():
            model=CatBoostClassifier(**m['params_elegidos'],random_seed=seed);model.fit(trpool,verbose=200);model.save_model(str(path))
        model=CatBoostClassifier();model.load_model(str(path))
        assert model.feature_names_==cols and model.tree_count_==m['params_elegidos']['iterations']
        assert model.get_all_params()['random_seed']==seed and model.classes_.tolist()==[0,1]
        pred[f'p_cat_seed{seed}']=model.predict_proba(vp)[:,1];pred[f'p_lgb_seed{seed}']=lgb[f'p_lgb_seed{seed}']
        pred[f'score_seed{seed}']=.4*pred[f'p_lgb_seed{seed}']+.4*pred.p_tabpfn+.2*pred[f'p_cat_seed{seed}']
        pred.to_csv(out/'predicciones_agosto.csv',index=False);meta['semillas_completadas']=list(SEEDS[:SEEDS.index(seed)+1]);save(out/'manifest.json',meta)
        print('Final semilla',seed,'completa',flush=True)
    adj=out/'adjuntos_semillas';adj.mkdir(exist_ok=True);files=[];changes=[]
    for seed in SEEDS:
        q=pred[f'score_seed{seed}'];ids=pred.loc[q>.025,KEYS].copy();ids['score']=q[q>.025]
        ids=ids.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=adj/f'{meta["submit"]}_seed{seed}.csv';path.write_bytes(''.join(f'{int(v)}\n' for v in ids.numero_de_cliente).encode('ascii'))
        files.append(dict(seed=seed,archivo=str(path.relative_to(out)),contactos=len(ids),sha256=sha(path)))
        baseline=(lgb[f'p_lgb_seed{seed}']+lgb.p_tabpfn)/2>.025;sel=q>.025
        changes.append(dict(seed=seed,contactos=int(sel.sum()),contactos16=int(baseline.sum()),
            agregados_vs16=int((sel&~baseline).sum()),retirados_vs16=int((baseline&~sel).sum()),
            diferentes_vs17=int((sel!=(old17[f'score_seed{seed}']>.025)).sum())))
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    # Auditoria desde disco: modelos recargados, pesos por producto matricial, corte y IDs exactos.
    disk=pd.read_csv(out/'predicciones_agosto.csv');pd.testing.assert_frame_equal(disk[KEYS],keys)
    assert len(disk)==164647 and disk.numero_de_cliente.is_unique and disk.foto_mes.eq(202108).all() and 'clase_ternaria' not in disk
    for f in files:
        seed=f['seed'];model=CatBoostClassifier();model.load_model(str(md/f'seed{seed}.cbm'))
        np.testing.assert_allclose(model.predict_proba(vp)[:,1],disk[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        q=np.column_stack([disk[f'p_lgb_seed{seed}'],disk.p_tabpfn,disk[f'p_cat_seed{seed}']])@np.array([.4,.4,.2])
        np.testing.assert_array_equal(q>.025,disk[f'score_seed{seed}']>.025)
        ids=disk.loc[q>.025,['numero_de_cliente',f'score_seed{seed}']].sort_values([f'score_seed{seed}','numero_de_cliente'],ascending=[False,True])
        assert (out/f['archivo']).read_bytes()==''.join(f'{int(v)}\n' for v in ids.numero_de_cliente).encode('ascii')
        assert len(ids)==ids.numero_de_cliente.nunique()==f['contactos']
    for f,h in meta['source_hashes'].items():assert sha(ROOT/f)==h
    meta.update(estado='completo_verificado_preparado_pendiente',archivos=files,modelos_sha256={f.name:sha(f) for f in md.glob('*.cbm')},
        archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')})
    save(out/'manifest.json',meta)
    save(out/'verificacion_independiente.json',dict(estado='verificado',modelos_reproducidos=5,adjuntos_verificados=5,
        seleccion_matricial=True,fuentes_preservadas=True,fit_abril_mayo=True,sin_etiquetas_agosto=True,api=False,enviado=False))
    (out/'MENSAJE_SEMILLAS.txt').write_text('submit '+meta['submit']+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVIO MANUAL. Cinco CSV en adjuntos_semillas.\n',encoding='utf-8')
    report=[f'# Entrega{meta["entrega"]}: ensemble con CatBoost optimizado','',
        '**Preparada y verificada. Pendiente envío manual.**','',
        '```text','submit '+meta['submit'],'```','',
        'LightGBM189 combinado/TabPFN202 BAJA+2/CatBoost202 BAJA+2,40/40/20,corte>.025,cinco semillas. '
        'CatBoost elegido por CV3 abril y comprobado en mayo; fit final abril+mayo,agosto sin etiquetas. '
        'Los otros dos modelos reutilizados de16. No nuevos créditos.','',
        'Parámetros CatBoost: `'+str(m['params_elegidos'])+'`.','',
        '| Variante local | Total medio5 | 25% |','| --- | ---: | ---: |']
    for v in m['resultados']:report.append(f'| {v["variante"]} | ${v["ganancia"]:,.0f} | ${v["ganancia_25pct"]:,.0f} |')
    report+=['',m['limitacion'],'','| Semilla | Contactos agosto |','| --- | ---: |']
    report += [f'| {f["seed"]} | {f["contactos"]} |' for f in files]
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    # No cambiar manifest local utilizado como fuente hash de entrega final.
    save(local/'entrega_preparada.json',dict(entrega=meta['entrega'],carpeta=str(out.relative_to(ROOT)),submit=meta['submit'],enviado=False))
    print('LISTO',out,flush=True);print('submit '+meta['submit'],flush=True);print('Contactos:',[f['contactos'] for f in files],flush=True)

if __name__=='__main__':main()
