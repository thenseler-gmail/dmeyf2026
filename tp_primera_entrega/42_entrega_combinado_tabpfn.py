"""Entrega combinada: LightGBM BAJA+1/BAJA+2 + TabPFN BAJA+2, cinco semillas.
Junio solo en train final; evaluacion abril->mayo sin junio.
"""
import hashlib
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT/'tp_primera_entrega/salidas'
KEYS = ['numero_de_cliente','foto_mes']
prep = importlib.import_module('33_reentrenar_lightgbm_haberes')
medir = importlib.import_module('30_validacion_lightgbm').medir


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protocolo_path = ROOT/'tp_primera_entrega/config_validacion_lightgbm.json'
    protocolo = json.loads(protocolo_path.read_text())
    seeds = protocolo['politica_semillas_proximas_pruebas']['exploracion']
    assert len(seeds) == 5
    lb = SAL/'01_entregas_bot/3_EnsembleHist_20261005_131953'
    tb = SAL/'01_entregas_bot/1_TabPFNHist_20261004_223836'
    tv = SAL/'tabpfn_historicas_20261004_165442_887149'
    lm = json.loads((lb/'manifest.json').read_text())
    config_lgb = SAL/'revision_umbral_20261005_131001/bajas/manifest.json'
    lm_config = json.loads(config_lgb.read_text())
    assert lm['elegido'] == lm_config['elegido']
    lm['features'] = lm_config['features']
    tm = json.loads((tb/'manifest.json').read_text())
    vm = json.loads((tv/'manifest.json').read_text())
    assert lm['elegido']['target'] == 'bajas' and lm['train_lightgbm'] == tm['train_meses'] == [202105,202106]
    assert vm['train_meses'] == [202104] and vm['evaluacion_mes'] == 202105
    assert vm['config_experimental']['clase_positiva'] == 'BAJA+2'
    assert lm['features'] == tm['features'] == vm['originales']+vm['nuevas']
    for f in ['features.py','baseline.py']:
        assert sha(Path(__file__).parent/f) == tm['codigo_sha256'][f]
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    datos, cols = prep.cargar_desarrollo(config)
    assert cols == lm['features']
    it = np.flatnonzero(datos.foto_mes.eq(202104).to_numpy())
    iv = np.flatnonzero(datos.foto_mes.eq(202105).to_numpy())
    x = preparar(datos,cols)[0]
    y = datos.clase_ternaria.isin(['BAJA+1','BAJA+2']).astype(int).to_numpy()
    name = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleCombinadoTabPFN5_%Y%m%d_%H%M%S')
    # Numeracion organizativa; estado de envio siempre explicitamente pendiente.
    directories = list((SAL/'01_entregas_bot').glob('*'))
    numbers = [int(p.name.split('_')[0]) for p in directories if p.is_dir() and p.name.split('_')[0].isdigit()]
    out = SAL/'01_entregas_bot'/f'{max(numbers)+1}_{name}'
    out.mkdir()
    (out/'modelos_validacion').mkdir()
    meta = dict(estado='evaluando',enviado=False,estado_envio='pendiente',submit=name,semillas=seeds,
                umbral=.025,operador='>',peso_tabpfn=.5,target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',
                train_final=[202105,202106],futuro=202108,validacion_train=[202104],validacion_eval=202105,
                features_lightgbm=cols,features_tabpfn=tm['features'],elegido=lm['elegido'],
                tabpfn_model_version=tm['model_version'],tabpfn_n_estimators=tm['n_estimators'],
                limitaciones='Mayo reutilizado y semillas elegidas por abril/mayo; validacion abril->mayo retrospectiva, no CV por cliente ni test prospectivo independiente. Sin garantía de mejora en agosto.',
                fuentes={str(p):sha(p) for p in [lb/'predicciones_agosto.csv',lb/'manifest.json',
                    tb/'predicciones_agosto.csv',tb/'manifest.json',tv/'predicciones.csv',tv/'manifest.json',config_lgb]},
                api=False,creditos=0,entrenamientos_nuevos=5,
                codigo_sha256={f:sha(Path(__file__).parent/f) for f in ['42_entrega_combinado_tabpfn.py','features.py','features_abandono.py','baseline.py']})
    def save():
        (out/'manifest.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    print('Salida:',out,flush=True)
    pred = datos.iloc[iv][KEYS+['clase_ternaria']].reset_index(drop=True)
    tabval = pd.read_csv(tv/'predicciones.csv')
    pd.testing.assert_frame_equal(pred,tabval[pred.columns])
    pred['p_tabpfn'] = tabval.p_historicas
    spec = lm['elegido']
    for seed in seeds:
        model = lgb.train(dict(spec['params'],seed=seed),lgb.Dataset(x.iloc[it],label=y[it]),num_boost_round=spec['num_boost_round'])
        model.save_model(str(out/'modelos_validacion'/f'seed{seed}.txt'))
        pred[f'p_seed{seed}'] = model.predict(x.iloc[iv],validate_features=True)
        pred[f'p_mezcla_seed{seed}'] = (pred[f'p_seed{seed}']+pred.p_tabpfn)/2
        print('Validacion semilla',seed,'completa',flush=True)
    pred['p_lightgbm'] = pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    pred['probabilidad'] = (pred.p_lightgbm+pred.p_tabpfn)/2
    pred.to_csv(out/'predicciones_mayo.csv',index=False)
    results = [dict(modelo=c,**medir(pred,pred[c])) for c in pred if c.startswith('p_') or c=='probabilidad']
    pd.DataFrame(results).to_csv(out/'comparacion_mayo.csv',index=False)
    august = pd.read_csv(lb/'predicciones_agosto.csv')
    tabaug = pd.read_csv(tb/'predicciones_agosto.csv')
    pd.testing.assert_frame_equal(august[KEYS],tabaug[KEYS])
    assert len(august)==164647 and august.foto_mes.eq(202108).all() and not august.numero_de_cliente.duplicated().any()
    august = august[KEYS+[f'p_seed{s}' for s in seeds]].copy()
    august['p_tabpfn'] = tabaug.probabilidad
    august['p_lightgbm'] = august[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    august['probabilidad'] = (august.p_lightgbm+august.p_tabpfn)/2
    for seed in seeds:
        august[f'p_mezcla_seed{seed}'] = (august[f'p_seed{seed}']+august.p_tabpfn)/2
    august.to_csv(out/'predicciones_agosto.csv',index=False)
    files = []
    for variant, columns in [('semillas',[(f'p_mezcla_seed{s}',f'_seed{s}') for s in seeds]),('promedio5',[('probabilidad','')])]:
        folder = out/f'adjuntos_{variant}';folder.mkdir()
        submit = name+('Semillas' if variant=='semillas' else '')
        for col,suffix in columns:
            sel = august.loc[august[col]>.025].sort_values([col,'numero_de_cliente'],ascending=[False,True])
            path = folder/f'{submit}{suffix}.csv'
            path.write_text(''.join(f'{int(i)}\n' for i in sel.numero_de_cliente),encoding='ascii')
            assert len(sel)==sel.numero_de_cliente.nunique()
            files.append(dict(variante=variant,columna=col,archivo=str(path.relative_to(out)),contactos=len(sel),sha256=sha(path)))
        (out/f'MENSAJE_{variant.upper()}.txt').write_text('submit '+submit,encoding='ascii')
    meta.update(estado='completo',archivos=files,resultados_mayo=results,
                hashes_resultados={p.name:sha(p) for p in out.glob('*.csv')})
    save()
    (out/'ESTADO_ENVIO.txt').write_text('PENDIENTE DE ENVIO POR TOMAS\nCinco mezclas individuales: adjuntos_semillas/\nUna mezcla de TabPFN con promedio LightGBM5: adjuntos_promedio5/\nNo adjuntar ambas variantes en el mismo lote: darian una media de resultados distintos.\n',encoding='utf-8')
    print(pd.DataFrame(results).to_string(index=False),flush=True)
    print('Adjuntos:',files,flush=True)


if __name__=='__main__':
    main()
