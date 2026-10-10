"""Prepara cinco CSV de control213 marzo-junio + TabPFN16 guardado."""
import importlib
import json
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

pipe = importlib.import_module('89_catedra_pipeline')


def main():
    src = pipe.SAL/'catedra_implementacion_20261006_205501/control16_actualizado_marzo_junio'
    ref = pipe.SAL/'01_entregas_bot/16_EnsembleHist1895_20261006_143235'
    meta = json.loads((src/'manifest.json').read_text(encoding='utf-8'))
    original = json.loads((ref/'manifest.json').read_text(encoding='utf-8'))
    assert meta['estado']=='completo_verificado'
    assert meta['params']==original['firma']['params'] and meta['rounds']==273
    assert meta['train']==[202103,202104,202105,202106] and len(meta['features'])==213
    assert pipe.sha(src/'predicciones_agosto.csv')==meta['predicciones_sha256']
    p = pd.read_csv(src/'predicciones_agosto.csv',float_precision='round_trip')
    old = pd.read_csv(ref/'predicciones_agosto.csv',float_precision='round_trip')
    pd.testing.assert_frame_equal(p[pipe.KEYS],old[pipe.KEYS])
    np.testing.assert_array_equal(p.p_tab202,old.p_tabpfn)
    assert len(p)==164647 and p.numero_de_cliente.is_unique and p.foto_mes.eq(202108).all()
    bot=pipe.SAL/'01_entregas_bot'
    number=max(int(d.name.split('_')[0]) for d in bot.iterdir() if d.is_dir())+1
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleControl213Tab165_%Y%m%d_%H%M%S')
    out=bot/f'{number}_{name}';out.mkdir();(out/'adjuntos_semillas').mkdir();(out/'modelos').mkdir()
    pred=p[pipe.KEYS].copy();pred['p_tabpfn']=p.p_tab202
    files=[]
    for seed in pipe.SEEDS:
        path=src/f'seed{seed}.txt'
        model=pipe.lgb.Booster(model_file=str(path))
        assert model.num_trees()==273 and model.feature_name()==meta['features']
        shutil.copy2(path,out/'modelos'/path.name)
        pred[f'p_lgb_seed{seed}']=p[f'p_lgb_seed{seed}']
        q=(pred[f'p_lgb_seed{seed}']+pred.p_tabpfn)/2
        np.testing.assert_allclose(q,p[f'score_mix_seed{seed}'],rtol=0,atol=1e-15)
        assert np.isfinite(q).all() and q.between(0,1).all()
        pred[f'score_seed{seed}']=q
        selected=pred.loc[q>.025].sort_values([f'score_seed{seed}','numero_de_cliente'],ascending=[False,True])
        target=out/'adjuntos_semillas'/f'{name}_seed{seed}.csv'
        target.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
        files.append(dict(seed=seed,archivo=str(target.relative_to(out)),contactos=len(selected),sha256=pipe.sha(target)))
    pred.to_csv(out/'predicciones_agosto.csv',index=False)
    manifest=dict(estado='completo_verificado_preparado_pendiente',entrega=number,submit=name+'_semillas',enviado=False,
        train_final=meta['train'],futuro=202108,features_lightgbm=213,features_tabpfn=202,
        target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',pesos=dict(lightgbm=.5,tabpfn=.5),umbral=.025,operador='>',
        archivos=files,api=False,creditos=0,nuevos_fits_lightgbm=0,nuevos_fits_tabpfn=0,
        firma=dict(params=meta['params'],rounds=273,seeds=pipe.SEEDS,features=meta['features'],
                   codigo_sha256={f:pipe.sha(pipe.TP/f) for f in ['112_preparar_control213_tab16.py','93_reentrenar_control16_orden2.py','89_catedra_pipeline.py','features_catedra.py','features.py','calidad_datos.py','baseline.py']}),
        fuente_predicciones=str((src/'predicciones_agosto.csv').relative_to(pipe.ROOT)),fuente_manifest_sha256=pipe.sha(src/'manifest.json'),
        fuente_predicciones_sha256=pipe.sha(src/'predicciones_agosto.csv'),tabpfn16_sha256=pipe.sha(ref/'predicciones_agosto.csv'),
        predicciones_sha256=pipe.sha(out/'predicciones_agosto.csv'),modelos_sha256={f.name:pipe.sha(f) for f in (out/'modelos').glob('*.txt')},
        validacion_local=dict(candidato_total=262267500,control16_total=266420000,delta_total=-4152500,semillas_superan16=1),
        limitacion='Exploración pública autorizada pese a perder localmente. Local marzo+abril a mayo; final marzo-junio a agosto. TabPFN16 abril+mayo original. Resultado público desconocido.')
    pipe.save(out/'manifest.json',manifest)
    (out/'MENSAJE_SEMILLAS.txt').write_text('submit '+manifest['submit']+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVÍO MANUAL. Cinco adjuntos en una corrida.\n',encoding='utf-8')
    (out/'INFORME.md').write_text('# Control213 + TabPFN16\n\nCinco LightGBM213, parámetros16, 273 árboles, entrenados marzo–junio; TabPFN202 original de16 entrenado abril+mayo. Mezcla50/50, corte >2,5%.\n\nLocal mayo: $262.267.500 total frente16 $266.420.000; delta −$4.152.500. Ventanas distintas. Usuario autoriza probar en Bot pese a perder localmente. Resultado público pendiente.\n\nComando: `submit '+manifest['submit']+'`. Adjuntar los cinco CSV de adjuntos_semillas en una sola corrida. Sin nuevos fits ni API.\n',encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(out,['112_preparar_control213_tab16.py'])
    print(out)
    print('submit '+manifest['submit'])
    print([(f['seed'],f['contactos']) for f in files])


if __name__=='__main__':
    main()
