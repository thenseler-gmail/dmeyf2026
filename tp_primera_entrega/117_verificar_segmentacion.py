"""Reconstruye segmentos y predicciones, verifica ganancias y resume la ablación108."""
import importlib
import json
from pathlib import Path
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar

mod=importlib.import_module('108_segmentos_local')
pipe=mod.pipe
OUT=pipe.SAL/'segmentos_local_20261008'
def metric(y,q,cut):
    selected=np.asarray(q)>cut;y=np.asarray(y)
    n=int(selected.sum());tp=int((selected&y).sum())
    gain=int(np.where(y,1072500,-27500)[selected].sum())
    assert gain==1100000*tp-27500*n
    return dict(contactos=n,tp=tp,fp=n-tp,ganancia=gain,ganancia_25pct=gain/4)
def main():
    meta=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    assert meta['estado']=='completo' and meta['clusters']==4 and meta['fit_solo_train']
    plan=json.loads((OUT/'PLAN_EJECUCION_20261010.json').read_text(encoding='utf-8'))
    for f,h in plan['codigo_sha256'].items():assert pipe.sha(pipe.TP/f)==h
    raw,_=pipe.leer(final=True);_,cols=pipe.fuentes()
    result=pd.read_csv(OUT/'resultados.csv')
    summary=[];hashes={};paired=[]
    for month,training in [(202105,[202103,202104]),(202106,[202103,202104,202105])]:
        folder=OUT/str(month)
        tr=raw.loc[raw.foto_mes.isin(training)].reset_index(drop=True)
        va=raw.loc[raw.foto_mes.eq(month)].reset_index(drop=True)
        assert tr.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
        assert va.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all()
        p=pd.read_csv(folder/'predicciones.csv',float_precision='round_trip')
        pd.testing.assert_frame_equal(p[pipe.KEYS+['clase_ternaria']],va[pipe.KEYS+['clase_ternaria']])
        segment=joblib.load(folder/'segmentador.joblib')
        assert segment['sources']==mod.SOURCES and segment['cluster'].n_clusters==4
        assert all(c not in mod.SOURCES for c in pipe.KEYS+['clase_ternaria'])
        # Verify the fitted preprocessing statistics using training data alone.
        imp=mod.SimpleImputer(strategy='median',add_indicator=True)
        z=imp.fit_transform(mod.transform(tr))
        np.testing.assert_array_equal(imp.statistics_,segment['imputer'].statistics_)
        np.testing.assert_array_equal(imp.indicator_.features_,segment['imputer'].indicator_.features_)
        scale=mod.StandardScaler().fit(z)
        np.testing.assert_array_equal(scale.mean_,segment['scaler'].mean_)
        np.testing.assert_array_equal(scale.scale_,segment['scaler'].scale_)
        zv=np.clip(segment['scaler'].transform(segment['imputer'].transform(mod.transform(va))),-5,5)
        gv=segment['cluster'].predict(zv)
        saved=pd.read_csv(folder/'segmentos_validacion.csv')
        pd.testing.assert_frame_equal(saved[pipe.KEYS],va[pipe.KEYS])
        np.testing.assert_array_equal(gv,saved.segmento)
        x=preparar(va,cols)[0];y=va.clase_ternaria.eq('BAJA+2').to_numpy()
        means={};perseed={}
        for variant in ['control189','segmento190']:
            xv=x.copy()
            if variant=='segmento190':xv['segmento_cliente']=pd.Series(gv,dtype=pd.CategoricalDtype([0,1,2,3]))
            for s in pipe.SEEDS:
                path=folder/f'{variant}_{s}.txt';model=lgb.Booster(model_file=str(path))
                assert model.feature_name()==list(xv) and model.num_trees()==273
                for key,value in meta['params'].items():
                    actual=model.params['boosting' if key=='boosting_type' else key]
                    if key=='metric':
                        assert value=='None' and actual==['custom']
                        continue
                    if isinstance(value,(int,float)) and not isinstance(value,bool):np.testing.assert_allclose(actual,value,rtol=1e-5,atol=1e-8)
                    else:assert str(actual).lower()==str(value).lower(),(key,actual,value)
                assert model.params['seed']==s
                q=model.predict(xv,validate_features=True,num_threads=4)
                np.testing.assert_allclose(q,p[f'{variant}_{s}'],rtol=0,atol=1e-15)
                expected=result.loc[result.mes.eq(month)&result.variante.eq(variant)&result.seed.eq(str(s))]
                assert len(expected)==1
                for key,value in metric(y,q,.025).items():assert expected.iloc[0][key]==value
                perseed[variant,s]=q
            means[variant]=p[[f'{variant}_{s}' for s in pipe.SEEDS]].mean(axis=1).to_numpy()
        for cut in [.025,.0275]:
            a=metric(y,means['control189'],cut);b=metric(y,means['segmento190'],cut)
            ds=[]
            for s in pipe.SEEDS:
                c=metric(y,perseed['control189',s],cut);d=metric(y,perseed['segmento190',s],cut)
                ds.append(d['ganancia']-c['ganancia'])
                paired.append(dict(mes=month,corte=cut,seed=s,control=c['ganancia'],segmento=d['ganancia'],delta=d['ganancia']-c['ganancia']))
            summary.append(dict(mes=month,corte=cut,control_total=a['ganancia'],control25pct=a['ganancia_25pct'],
                segmento_total=b['ganancia'],segmento25pct=b['ganancia_25pct'],delta_total=b['ganancia']-a['ganancia'],
                delta25pct=(b['ganancia']-a['ganancia'])/4,control_contactos=a['contactos'],segmento_contactos=b['contactos'],
                control_tp=a['tp'],segmento_tp=b['tp'],semillas_mejoran=sum(d>0 for d in ds),
                media_delta_semillas=float(np.mean(ds))))
        for path in folder.iterdir():
            if path.is_file():hashes[str(path.relative_to(OUT))]=pipe.sha(path)
        print('Verificado mes',month,flush=True)
    pd.DataFrame(summary).to_csv(OUT/'comparacion_verificada.csv',index=False)
    pd.DataFrame(paired).to_csv(OUT/'deltas_pareados_semillas.csv',index=False)
    primary=[r for r in summary if r['corte']==.025]
    consistent=all(r['delta_total']>0 and r['media_delta_semillas']>0 for r in primary)
    verdict='Justifica siguiente ensayo alineado con el ensemble36' if consistent else 'No hay mejora consistente para promover; conservar referencia36'
    verification=dict(estado='verificado',meses=[202105,202106],resumen=summary,decision=verdict,
        archivos_sha256=hashes,codigo_sha256={Path(__file__).name:pipe.sha(Path(__file__))},api=False,creditos=0,submits=0,
        limitacion='LightGBM solo; ventanas y corrección distintas de ensemble36. Mayo/junio reutilizados, no tests independientes.')
    pipe.save(OUT/'verificacion_independiente.json',verification)
    text='# Segmentación: comparación verificada\n\nCuatro segmentos aprendidos solo con train; variable categórica adicional en LightGBM. Mismos parámetros, 273 árboles, cinco semillas y corrección de datos en ambos brazos.\n\n'
    text+='Marzo–abril → mayo; marzo–mayo → junio. Métrica principal corte2,5%; 2,75% diagnóstico fijado antes de resultados. Ganancia de una lista de probabilidades promedio y delta medio de listas individuales separados.\n\n```text\n'+pd.DataFrame(summary).to_string(index=False)+'\n```\n\n'+verdict+'.\n\n'
    text+='No es una comparación directa con la entrega36 ni una ganancia pública. Mayo/junio reutilizados; junio tiene aguinaldo. Sin API, créditos, scoring agosto ni nueva entrega. Predicciones reconstruidas desde modelos, segmentos y preprocesamiento verificados; ganancias recalculadas desde pagos por cliente.\n'
    (OUT/'INFORME_VERIFICADO.md').write_text(text,encoding='utf-8')
    pipe.save(OUT/'estado.json',dict(estado='completo_verificado',decision=verdict,api=False,creditos=0))
    note='\n## Segmentación ejecutada y verificada — 2026-10-10\n\n'+text+'\n'
    with (pipe.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write(note)
    steps=pipe.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(note.lstrip()+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(verification['resumen'],ensure_ascii=False,indent=2),flush=True)
    print(verdict,flush=True)
if __name__=='__main__':main()
