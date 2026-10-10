"""Verifica mezcla, fuentes, ganancias, adjuntos y prediccion local de un modelo."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar


def main():
    out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text())
    assert m['estado']=='completo' and not m['enviado'] and m['creditos']==0
    assert m['train_final']==[202105,202106]
    assert m['validacion_train']==[202104] and m['validacion_eval']==202105
    for p,h in m['fuentes'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    for name,h in m['hashes_resultados'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h
    seeds=m['semillas']; results=pd.read_csv(out/'comparacion_mayo.csv')
    assert len(results)==13
    for month in ['mayo','agosto']:
        p=pd.read_csv(out/f'predicciones_{month}.csv')
        assert not p.numero_de_cliente.duplicated().any()
        probs=p.filter(regex='^(p_|probabilidad)')
        assert np.isfinite(probs).all().all() and ((probs>=0)&(probs<=1)).all().all()
        np.testing.assert_allclose(p.p_lightgbm,p[[f'p_seed{s}' for s in seeds]].mean(axis=1),rtol=0,atol=1e-15)
        np.testing.assert_allclose(p.probabilidad,(p.p_lightgbm+p.p_tabpfn)/2,rtol=0,atol=1e-15)
        for seed in seeds:
            np.testing.assert_allclose(p[f'p_mezcla_seed{seed}'],(p[f'p_seed{seed}']+p.p_tabpfn)/2,rtol=0,atol=1e-15)
        if month=='mayo':
            for r in results.itertuples(index=False):
                sel=p[r.modelo]>.025;y=p.clase_ternaria.eq('BAJA+2')
                tp=int((sel&y).sum());fp=int((sel&~y).sum());gain=tp*1072500-fp*27500
                assert (r.contactos,r.tp,r.fp,r.ganancia,r.ganancia_25pct)==(tp+fp,tp,fp,gain,gain/4)
            val=p
        else:
            assert len(p)==164647 and p.foto_mes.eq(202108).all()
            for f in m['archivos']:
                path=out/f['archivo']; ids=path.read_text(encoding='ascii').splitlines()
                assert all(s.isdigit() for s in ids) and len(ids)==len(set(ids))==f['contactos']
                expected=p.loc[p[f['columna']]>.025].sort_values([f['columna'],'numero_de_cliente'],ascending=[False,True])
                assert list(map(int,ids))==expected.numero_de_cliente.astype(int).tolist()
                assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
            assert len(list((out/'adjuntos_semillas').glob('*.csv')))==5
            assert len(list((out/'adjuntos_promedio5').glob('*.csv')))==1
    root=Path(__file__).resolve().parents[1]
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    datos,_=importlib.import_module('33_reentrenar_lightgbm_haberes').cargar_desarrollo(config)
    xp=preparar(datos.loc[datos.foto_mes.eq(202105)],m['features_lightgbm'])[0]
    model=lgb.Booster(model_file=str(out/'modelos_validacion'/f'seed{seeds[0]}.txt'))
    assert model.num_trees()==m['elegido']['num_boost_round'] and model.feature_name()==m['features_lightgbm']
    np.testing.assert_allclose(model.predict(xp,validate_features=True),val[f'p_seed{seeds[0]}'],rtol=0,atol=1e-15)
    v=dict(estado='verificado',ganancias_reconstruidas=13,adjuntos=6,semillas=5,prediccion_modelo_reproducida=seeds[0],umbral=.025,creditos=0)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':
    main()
