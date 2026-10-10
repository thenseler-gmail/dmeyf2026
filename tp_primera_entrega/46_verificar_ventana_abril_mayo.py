"""Verifica ventana, modelos y listas; sirve para estado local o ensemble completo."""
import hashlib
import json
import sys
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features import HISTORICAS,HISTORICAS_EXTRA,agregar_historicas_ampliadas


def main():
    root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text())
    assert m['train_final']==[202104,202105] and m['futuro']==202108 and not m['enviado']
    assert m['umbral']==.025 and m['operador']=='>' and len(m['firma']['semillas'])==5
    for name,h in m['firma']['codigo'].items():
        assert hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==h
    config=json.loads((root/'tp_primera_entrega/config.json').read_text());keys=['numero_de_cliente','foto_mes']
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(root/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria), CASE WHEN foto_mes IN (202104,202105) THEN clase_ternaria ELSE NULL END AS clase_ternaria FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    hist=agregar_historicas_ampliadas(raw[keys+HISTORICAS+HISTORICAS_EXTRA].copy())
    hc=[c for c in hist if c not in keys+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(hist[keys+hc],on=keys,validate='one_to_one',sort=False)
    train=raw.loc[raw.foto_mes.isin([202104,202105])]
    august=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    assert len(train)==327052 and len(august)==164647
    assert train.clase_ternaria.isin(['CONTINUA','BAJA+1','BAJA+2']).all() and august.clase_ternaria.isna().all()
    cols=m['firma']['features'];seeds=m['firma']['semillas']
    xt=preparar(train,cols)[0];xp=preparar(august,cols)[0]
    for matrix,name in [(xt,'matriz_train_sha256'),(xp,'matriz_agosto_sha256')]:
        assert hashlib.sha256(matrix.to_numpy(dtype=np.float32).tobytes()).hexdigest()==m['firma'][name]
    yt=train.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    assert hashlib.sha256(yt.tobytes()).hexdigest()==m['firma']['target_tabpfn_sha256']
    p=pd.read_csv(out/'predicciones_agosto.csv');pd.testing.assert_frame_equal(p[keys],august[keys])
    assert not p.numero_de_cliente.duplicated().any()
    assert hashlib.sha256((out/'predicciones_agosto.csv').read_bytes()).hexdigest()==m['predicciones_sha256']
    for seed in seeds:
        path=out/'modelos'/f'seed{seed}.txt'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==m['modelos_sha256'][path.name]
        model=lgb.Booster(model_file=str(path))
        assert model.feature_name()==cols and model.num_trees()==273
        np.testing.assert_allclose(model.predict(xp,validate_features=True),p[f'p_seed{seed}'],rtol=0,atol=1e-15)
    np.testing.assert_allclose(p.p_lightgbm,p[[f'p_seed{s}' for s in seeds]].mean(axis=1),rtol=0,atol=1e-15)
    if 'p_tabpfn' in p:
        assert np.isfinite(p.p_tabpfn).all() and p.p_tabpfn.between(0,1).all()
        np.testing.assert_allclose(p.probabilidad,(p.p_lightgbm+p.p_tabpfn)/2,rtol=0,atol=1e-15)
    count=0
    for variante,files in m['archivos'].items():
        assert len(files)==(1 if variante=='promedio5' else 5)
        assert len(list((out/f'adjuntos_{variante}').glob('*.csv')))==len(files)
        for f in files:
            if variante=='promedio5':prob=p.probabilidad
            else:
                prob=p[f"p_{f['label']}"]
                if variante=='semillas':prob=(prob+p.p_tabpfn)/2
            expected=p.loc[prob>.025,['numero_de_cliente']].copy();expected['p']=prob[prob>.025]
            expected=expected.sort_values(['p','numero_de_cliente'],ascending=[False,True])
            file=out/f['archivo'];ids=file.read_text(encoding='ascii').splitlines()
            assert all(i.isdigit() for i in ids) and len(ids)==len(set(ids))==f['contactos']
            assert list(map(int,ids))==expected.numero_de_cliente.astype(int).tolist()
            assert hashlib.sha256(file.read_bytes()).hexdigest()==f['sha256'];count+=1
    v=dict(estado='verificado',train=[202104,202105],filas_train=327052,filas_agosto=164647,modelos_reproducidos=5,adjuntos=count,
           tabpfn_completo='p_tabpfn' in p,umbral=.025)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(v)


if __name__=='__main__':main()
