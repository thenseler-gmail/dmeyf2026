"""Verifica estudio, OOF, seleccion, semillas y candidato sin reentrenar."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from baseline import preparar


def score(df,p):
    p=np.asarray(p);assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    sel=p>.025;y=df.clase_ternaria.eq('BAJA+2').to_numpy()
    tp=int((sel&y).sum());fp=int((sel&~y).sum());gain=tp*1072500-fp*27500
    return dict(contactos=tp+fp,tp=tp,fp=fp,ganancia=gain,ganancia_25pct=gain/4)


def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text());assert m['estado']=='completo'
    for name,h in m['archivos_sha256'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h
    assert m['umbral']==.025 and m['operador']=='>' and m['creditos']==0
    assert len(m['firma']['features'])==202 and len(m['firma']['semillas'])==5
    seeds=m['firma']['semillas'];groups=pd.read_csv(out/'asignacion_folds.csv')
    assert set(groups.foto_mes)=={202103,202104,202105}
    assert groups.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
    study=optuna.load_study(study_name='combinado',storage='sqlite:///'+(out/'estudio.db').as_posix())
    trials=[t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
    assert len(trials)==m['trials_solicitados']==30
    april=groups.loc[groups.foto_mes.eq(202104)].reset_index(drop=True)
    for t in trials:
        df=pd.read_csv(out/f'trial{t.number}_oof_abril.csv')
        pd.testing.assert_frame_equal(df[['numero_de_cliente','foto_mes','clase_ternaria']],april[['numero_de_cliente','foto_mes','clase_ternaria']])
        sc=score(df,df.probabilidad)
        assert sc['ganancia']==t.value and sc['ganancia_25pct']==t.user_attrs['ganancia_25pct']
        assert t.user_attrs['rounds']==int(np.median(t.user_attrs['fold_rounds']))
        assert sc['ganancia']==sum(r['ganancia'] for r in t.user_attrs['fold_metrics'])
    audit=pd.read_csv(out/'auditoria_busqueda.csv');assert len(audit)==120
    for a in audit.itertuples(index=False):
        it=groups.loc[(groups.foto_mes<=202104)&groups.fold_cliente.ne(a.fold)]
        iv=groups.loc[groups.foto_mes.eq(202104)&groups.fold_cliente.eq(a.fold)]
        assert set(it.numero_de_cliente).isdisjoint(set(iv.numero_de_cliente))
        assert (len(it),len(iv),it.foto_mes.max())==(a.filas_train,a.filas_eval,a.max_mes_train)
    top=sorted(trials,key=lambda t:(-t.value,t.number))[:5]
    assert [t.number for t in top]==m['top5']
    selected=pd.read_csv(out/'seleccion_mayo.csv')
    assert len(selected)==5 and set(selected.trial)==set(m['top5'])
    singles=pd.read_csv(out/'semillas_mayo.csv');assert len(singles)==35
    baseline=pd.read_csv(Path(m['referencia'])/'predicciones_mayo.csv')
    count=0
    for name in [f'trial{n}' for n in m['top5']]+['control_temporal','ganador_temporal']:
        df=pd.read_csv(out/f'{name}_mayo.csv')
        pd.testing.assert_frame_equal(df[['numero_de_cliente','foto_mes','clase_ternaria']],baseline[['numero_de_cliente','foto_mes','clase_ternaria']])
        for seed in seeds:
            r=singles.loc[singles.configuracion.eq(name)&singles.seed.eq(seed)].iloc[0]
            sc=score(df,df[f'p_seed{seed}'])
            for k,v in sc.items(): assert r[k]==v
            np.testing.assert_allclose(df[f'p_seed{seed}'],np.load(out/'cache'/f'{name}_{seed}.npy'),rtol=0,atol=1e-15)
            model=lgb.Booster(model_file=str(out/'modelos'/f'{name}_{seed}.txt'))
            assert model.feature_name()==m['firma']['features']
            count+=1
        np.testing.assert_allclose(df.p_lightgbm,df[[f'p_seed{s}' for s in seeds]].mean(axis=1),rtol=0,atol=1e-15)
        if name.startswith('trial'):
            n=int(name[5:]);row=selected.loc[selected.trial.eq(n)].iloc[0]
            for k,v in score(df,df.p_lightgbm).items():assert row[k]==v
            np.testing.assert_allclose(df.p_tabpfn,baseline.p_tabpfn,rtol=0,atol=0)
            np.testing.assert_allclose(df.p_mezcla,(df.p_lightgbm+df.p_tabpfn)/2,rtol=0,atol=1e-15)
            assert row.ganancia_mezcla==score(df,df.p_mezcla)['ganancia']
            ind=singles.loc[singles.configuracion.eq(name),'ganancia']
            np.testing.assert_allclose([row.media_individual,row.std_individual],[ind.mean(),ind.std(ddof=1)],rtol=1e-12)
    sorted_rows=selected.sort_values(['ganancia','media_individual','std_individual','trial'],ascending=[False,False,True,True])
    assert int(sorted_rows.iloc[0].trial)==m['elegido']['trial']
    control=score(baseline,baseline.p_lightgbm)
    assert control['ganancia']==m['control_mayo']['ganancia']
    assert sorted_rows.iloc[0].ganancia-control['ganancia']==m['mejora_mayo']
    root=Path(__file__).resolve().parents[1]
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    datos,cols=importlib.import_module('33_reentrenar_lightgbm_haberes').cargar_desarrollo(config)
    assert cols==m['firma']['features']
    xp=preparar(datos.loc[datos.foto_mes.eq(202105)],cols)[0]
    name=f"trial{m['elegido']['trial']}"
    saved=lgb.Booster(model_file=str(out/'modelos'/f'{name}_{seeds[0]}.txt'))
    original=pd.read_csv(out/f'{name}_mayo.csv')
    np.testing.assert_allclose(saved.predict(xp,validate_features=True),original[f'p_seed{seeds[0]}'],rtol=0,atol=1e-15)
    candidate_files=0
    if 'candidato' in m:
        candidate=Path(m['candidato']);cm=json.loads((candidate/'manifest.json').read_text())
        assert cm['train']==[202105,202106] and cm['futuro']==202108 and not cm['enviado']
        assert cm['elegido']==m['elegido'] and cm['features']==m['firma']['features']
        p=pd.read_csv(candidate/'predicciones_agosto.csv')
        assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any()
        np.testing.assert_allclose(p.p_lightgbm,p[[f'p_seed{s}' for s in seeds]].mean(axis=1),rtol=0,atol=1e-15)
        np.testing.assert_allclose(p.p_mezcla,(p.p_lightgbm+p.p_tabpfn)/2,rtol=0,atol=1e-15)
        tab=pd.read_csv(cm['fuente_tabpfn'])
        pd.testing.assert_frame_equal(p[['numero_de_cliente','foto_mes']],tab[['numero_de_cliente','foto_mes']])
        np.testing.assert_allclose(p.p_tabpfn,tab.probabilidad,rtol=0,atol=0)
        for f in cm['archivos']:
            file=candidate/f['archivo'];ids=file.read_text(encoding='ascii').splitlines()
            prob=p[f"p_seed{f['seed']}"]
            if f['variante']=='mezcla':prob=(prob+p.p_tabpfn)/2
            expected=p.loc[prob>.025,['numero_de_cliente']].copy();expected['p']=prob[prob>.025]
            expected=expected.sort_values(['p','numero_de_cliente'],ascending=[False,True])
            assert all(i.isdigit() for i in ids) and len(ids)==len(set(ids))==f['contactos']
            assert list(map(int,ids))==expected.numero_de_cliente.astype(int).tolist()
            assert hashlib.sha256(file.read_bytes()).hexdigest()==f['sha256']
            candidate_files+=1
        assert candidate_files==10
    v=dict(estado='verificado',trials=30,folds=120,seleccion_semillas_reconstruida=count,finalistas=5,adjuntos_candidato=candidate_files,api=False,creditos=0)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    if 'candidato' in m:
        (Path(m['candidato'])/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':main()
