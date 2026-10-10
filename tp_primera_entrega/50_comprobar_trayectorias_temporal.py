"""Chequeo abril->mayo del bloque; cuatro caidas sostenidas NaN en train."""
import importlib
import json
import sys
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_trayectorias import FEATURES,FUENTES,KEYS,agregar_trayectorias


def main():
    root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text())
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    datos,cols=importlib.import_module('33_reentrenar_lightgbm_haberes').cargar_desarrollo(config)
    datos=datos.merge(agregar_trayectorias(datos[KEYS+FUENTES]),on=KEYS,validate='one_to_one',sort=False)
    it=np.flatnonzero(datos.foto_mes.eq(202104).to_numpy());iv=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy())
    columns=cols+FEATURES;x=preparar(datos,columns)[0];y=datos.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    base=pd.read_csv(m['fuente_errores']);pred=datos.iloc[iv][KEYS+['clase_ternaria']].reset_index(drop=True)
    pd.testing.assert_frame_equal(pred,base[pred.columns])
    spec=m['elegido'];metric=importlib.import_module('30_validacion_lightgbm').medir
    results=[]
    for seed in m['semillas']:
        model=lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it],label=y[it]),num_boost_round=spec['num_boost_round'])
        path=out/'modelos'/f'temporal_{seed}.txt';model.save_model(str(path))
        p=model.predict(x.iloc[iv],validate_features=True)
        check=lgb.Booster(model_file=str(path)).predict(x.iloc[iv],validate_features=True)
        np.testing.assert_allclose(p,check,rtol=0,atol=0)
        pred[f'p_seed{seed}']=p
        for name,prob in [('control',base[f'p_seed{seed}']),('trayectorias',p)]:
            results.append(dict(variante=name,seed=seed,**metric(pred,prob)))
        print('Temporal semilla',seed,'lista',flush=True)
    pred['p_lightgbm']=pred[[f'p_seed{s}' for s in m['semillas']]].mean(axis=1)
    pred['p_tabpfn']=base.p_tabpfn;pred['probabilidad']=(pred.p_lightgbm+pred.p_tabpfn)/2
    pred.to_csv(out/'temporal_predicciones_mayo.csv',index=False)
    for name,frame in [('control',base),('trayectorias',pred)]:
        for model,column in [('LightGBM','p_lightgbm'),('mezcla50/50','probabilidad')]:
            results.append(dict(variante=name,modelo=model,seed='promedio5',**metric(frame,frame[column])))
    pd.DataFrame(results).to_csv(out/'temporal_comparacion.csv',index=False)
    check=dict(estado='verificado',train=[202104],evaluacion=202105,etiquetas_evaluacion_en_fit=False,modelos_reproducidos=5,
               limitacion='Cuatro caidas sostenidas son NaN en abril; nuevo bloque añade columnas y cambia muestreo de features. Mayo reutilizado.')
    (out/'temporal_verificacion.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
    print(pd.DataFrame(results).tail(4).to_string(index=False),flush=True)


if __name__=='__main__':main()
