"""Reconstruye lags calendario por MultiIndex, recarga modelos y verifica ganancias."""
import argparse
import importlib
import json
from pathlib import Path
import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_catedra import construir, FUENTES, KEYS

pipe=importlib.import_module('89_catedra_pipeline')
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args();out=args.salida
m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
assert m['estado']=='completo_verificado' and m['firma']['train']==[202103,202104,202105]
assert m['firma']['validacion']==202106 and not m['api'] and m['creditos']==0
config=json.loads((pipe.TP/'config.json').read_text(encoding='utf-8'))
with duckdb.connect() as con:
    con.execute('SET threads=2');con.read_csv(str(pipe.ROOT/config['dataset'])).create_view('datos')
    raw=con.sql('SELECT * FROM datos WHERE foto_mes IN (202103,202104,202105,202106) '
                'ORDER BY foto_mes,numero_de_cliente').df()
hist,audit=construir(raw)
lookup=raw.set_index(KEYS)
previous=raw.foto_mes.map({202103:202101,202104:202102,202105:202103,202106:202104})
index=pd.MultiIndex.from_arrays([raw.numero_de_cliente,previous],names=KEYS)
for c in FUENTES:
    lag=lookup[c].reindex(index).to_numpy()
    np.testing.assert_allclose(hist['lag_2_'+c],lag,rtol=0,atol=0,equal_nan=True)
    np.testing.assert_allclose(hist['delta_2_'+c],raw[c].to_numpy()-lag,rtol=0,atol=0,equal_nan=True)
assert hist.loc[hist.foto_mes.eq(202105),'ccajas_depositos'].isna().all()
va=hist[hist.foto_mes.eq(202106)].reset_index(drop=True);del raw,hist,lookup
p=pd.read_csv(out/'predicciones_junio.csv')
pd.testing.assert_frame_equal(va[KEYS+['clase_ternaria']],p[KEYS+['clase_ternaria']])
rows=[]
for name,features in [('control189',m['firma']['features_control']),('orden2_213',m['firma']['features_orden2'])]:
    xv=preparar(va,features)[0]
    for s in m['firma']['semillas']:
        path=out/name/f'seed{s}.txt'
        assert pipe.sha(path)==m['modelos_sha256'][str(path.relative_to(out))]
        model=lgb.Booster(model_file=str(path));assert model.feature_name()==features and model.num_trees()==273
        q=model.predict(xv,validate_features=True)
        np.testing.assert_allclose(q,p[f'{name}_seed{s}'],rtol=0,atol=1e-15)
        sel=q>.025
        gain=int(np.where(va.clase_ternaria.eq('BAJA+2'),1072500,-27500)[sel].sum())
        rows.append(dict(variante=name,seed=s,ganancia=gain))
saved=pd.read_csv(out/'resultados_semillas.csv')
pd.testing.assert_frame_equal(pd.DataFrame(rows),saved[['variante','seed','ganancia']],check_dtype=False)
diff=saved.pivot(index='seed',columns='variante',values='ganancia')
assert float((diff.orden2_213-diff.control189).mean())==m['delta_total']
pipe.save(out/'verificacion_independiente.json',dict(estado='verificado',
      checks=['24históricos por lookup calendario independiente','ccajas mayo NA',
              'modelos recargados y hashes','predicciones y claves exactas','ganancia por pagos fila a fila'],
      api=False,creditos=0,submits=0))
print('Junio: verificación independiente completa.',flush=True)
