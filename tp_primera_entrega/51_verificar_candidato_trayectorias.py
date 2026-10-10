"""Reconstruye cinco modelos finales y las once listas del candidato."""
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
from features_trayectorias import FEATURES,FUENTES,KEYS,agregar_trayectorias


def main():
    root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text())
    assert m['train']==[202104,202105] and m['futuro']==202108 and not m['enviado']
    assert len(m['features_lightgbm'])==214 and len(m['features_tabpfn'])==202
    assert m['creditos']==0 and not m['api']
    for n,h in m['archivos_sha256'].items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    with duckdb.connect() as con:
        con.execute('SET threads=2');con.read_csv(str(root/config['dataset'])).create_view('datos')
        raw=con.sql('SELECT * EXCLUDE(clase_ternaria) FROM datos ORDER BY foto_mes,numero_de_cliente').df()
    h=agregar_historicas_ampliadas(raw[KEYS+HISTORICAS+HISTORICAS_EXTRA].copy());hc=[c for c in h if c not in KEYS+HISTORICAS+HISTORICAS_EXTRA]
    raw=raw.merge(h[KEYS+hc],on=KEYS,validate='one_to_one',sort=False)
    raw=raw.merge(agregar_trayectorias(raw[KEYS+FUENTES]),on=KEYS,validate='one_to_one',sort=False)
    august=raw.loc[raw.foto_mes.eq(202108)].reset_index(drop=True)
    p=pd.read_csv(out/'predicciones_agosto.csv');pd.testing.assert_frame_equal(august[KEYS],p[KEYS])
    assert len(p)==164647 and not p.numero_de_cliente.duplicated().any()
    xp=preparar(august,m['features_lightgbm'])[0]
    for seed in m['semillas']:
        file=out/'modelos'/f'seed{seed}.txt'
        assert hashlib.sha256(file.read_bytes()).hexdigest()==m['modelos_sha256'][file.name]
        model=lgb.Booster(model_file=str(file));assert model.feature_name()==m['features_lightgbm'] and model.num_trees()==273
        np.testing.assert_allclose(model.predict(xp,validate_features=True),p[f'p_seed{seed}'],rtol=0,atol=1e-15)
    assert hashlib.sha256(Path(m['fuente_tabpfn']).read_bytes()).hexdigest()==m['fuente_tabpfn_sha256']
    tab=pd.read_csv(m['fuente_tabpfn']);pd.testing.assert_frame_equal(p[KEYS],tab[KEYS])
    np.testing.assert_allclose(p.p_tabpfn,tab.p_tabpfn,rtol=0,atol=1e-15)
    np.testing.assert_allclose(p.p_lightgbm,p[[f'p_seed{s}' for s in m['semillas']]].mean(axis=1),rtol=0,atol=1e-15)
    np.testing.assert_allclose(p.probabilidad,(p.p_lightgbm+p.p_tabpfn)/2,rtol=0,atol=1e-15)
    for f in m['archivos']:
        if f['variante']=='promedio5':prob=p.probabilidad
        else:
            prob=p[f"p_{f['label']}"]
            if f['variante']=='semillas':prob=(prob+p.p_tabpfn)/2
        assert np.isfinite(prob).all() and prob.between(0,1).all()
        expected=p.loc[prob>.025,['numero_de_cliente']].copy();expected['p']=prob[prob>.025]
        expected=expected.sort_values(['p','numero_de_cliente'],ascending=[False,True])
        file=out/f['archivo'];ids=file.read_text(encoding='ascii').splitlines()
        assert all(i.isdigit() for i in ids) and len(ids)==len(set(ids))==f['contactos']
        assert list(map(int,ids))==expected.numero_de_cliente.astype(int).tolist()
        assert hashlib.sha256(file.read_bytes()).hexdigest()==f['sha256']
    assert len(list((out/'adjuntos_semillas').glob('*.csv')))==5 and len(m['archivos'])==11
    v=dict(estado='verificado',modelos_finales_reproducidos=5,adjuntos=11,tabpfn_guardado_misma_ventana=True,umbral=.025,nuevos_creditos=0)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(v)


if __name__=='__main__':main()
