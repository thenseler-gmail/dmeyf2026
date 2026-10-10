"""Cambiar solo TabPFN v3.5-fast a v3.5 en el ensemble final 43."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'entregas/entrega_final_43'
OUT = ROOT / 'tp_primera_entrega/salidas/tabpfn35_contra43_20261010'
sys.path.insert(0, str(PACK))
spec = importlib.util.spec_from_file_location('tab43', PACK / 'recalcular_tabpfn.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--preparar', action='store_true')
    ap.add_argument('--cotizar', action='store_true')
    ap.add_argument('--ejecutar-api', action='store_true')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    helper.verificar_archivos()
    config = read(PACK / 'configuracion_tabpfn.json')
    plan = dict(comparacion='Solo version TabPFN: v3.5 frente a v3.5-fast de43',
                tabpfn=dict(config, model_version='v3.5'),
                lightgbm='Cinco modelos197 de43 guardados, sin nuevos fits',
                pesos=dict(lightgbm=.5, tabpfn=.5), umbral=.0275, operador='>',
                etiquetas_enviadas='Solo BAJA+2 de abril+mayo',
                nuevos_fits_lightgbm=0, nuevos_fits_tabpfn=1,
                codigo_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), PACK/'recalcular_tabpfn.py', PACK/'features.py', PACK/'configuracion_tabpfn.json']})
    pp = OUT/'PLAN.json'
    if pp.exists() and read(pp) != plan:
        raise ValueError('Plan congelado distinto; usar otro experimento')
    save(pp, plan)
    payload_path = OUT/'payload202.npz'
    if args.preparar and not payload_path.exists():
        xt, xp, y, keys = helper.preparar(ROOT/'data/competencia_01.csv', config)
        np.savez_compressed(payload_path, train=xt, predict=xp, target=y)
        keys.to_csv(OUT/'claves_agosto.csv', index=False)
        save(OUT/'PAYLOAD.json', dict(npz_sha256=sha(payload_path), claves_sha256=sha(OUT/'claves_agosto.csv'),
             filas_train=len(xt), filas_predict=len(xp), variables=202,
             matriz_train_sha256=helper.matrix_sha(xt), matriz_agosto_sha256=helper.matrix_sha(xp),
             target_sha256=helper.matrix_sha(y), estado='verificado_contra43', datos_clientes_enviados=False))
        print('Payload202 original verificado y guardado; cero API/creditos.', flush=True)
    if not (args.cotizar or args.ejecutar_api):
        return
    from tabpfn_client import estimate_cost, get_api_usage, TabPFNClassifier
    quote = estimate_cost(np.broadcast_to(np.float32(0),(327052,202)),
                          np.broadcast_to(np.float32(0),(164647,202)), model_version='v3.5', n_estimators=2)
    usage = str(get_api_usage())
    save(OUT/'COTIZACION.json', dict(cotizacion=quote.model_dump(mode='json'), cuota=usage,
          datos_clientes_enviados=False, creditos_consumidos=0))
    print('TabPFN v3.5 cotiza:', quote.estimated_cost, 'creditos. Cuota:', usage, flush=True)
    if not args.ejecutar_api:
        return
    auth = read(OUT/'AUTORIZACION_API.json')
    assert auth['autorizado'] and auth['destino']=='Prior Labs' and auth['model_version']=='v3.5'
    assert auth['target']=='BAJA+2' and quote.estimated_cost<=auth['max_creditos']
    payload = read(OUT/'PAYLOAD.json')
    assert sha(payload_path)==payload['npz_sha256'] and sha(OUT/'claves_agosto.csv')==payload['claves_sha256']
    state_path = OUT/'ESTADO_API.json'
    if state_path.exists():
        raise ValueError('API registrada previamente; revisar consumo antes de reintentar')
    a = np.load(payload_path)
    xt,xp,y = a['train'],a['predict'],a['target']
    assert helper.matrix_sha(xt)==config['matriz_train_sha256']
    assert helper.matrix_sha(xp)==config['matriz_agosto_sha256'] and helper.matrix_sha(y)==config['target_sha256']
    state = dict(estado='iniciando_api', datos_clientes_enviados=True, cuota_antes=usage,
                 cotizacion=quote.model_dump(mode='json'), max_creditos=auth['max_creditos'])
    save(state_path,state)
    try:
        model=TabPFNClassifier.create_default_for_version('v3.5',n_estimators=2,random_state=214363,
            fit_mode=config['fit_mode'],inference_precision=config['inference_precision'],
            categorical_features_indices=[config['features'].index(c) for c in config['categorical_features']],
            inference_config=config['inference_config'])
        start=time.perf_counter();model.fit(xt,y)
        p=np.asarray(model.predict_proba(xp)[:,list(model.classes_).index(1)],dtype=np.float64)
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        ref=pd.read_csv(PACK/'artefactos/predicciones_agosto.csv.gz',float_precision='round_trip')
        keys=pd.read_csv(OUT/'claves_agosto.csv');pd.testing.assert_frame_equal(keys,ref[helper.KEYS])
        score=.5*ref[[f'p_lgb_seed{s}' for s in [541440,408476,741961,248865,717444]]].to_numpy().mean(axis=1)+.5*p
        pred=keys.copy();pred['p_tabpfn35']=p;pred['score_promedio5']=score
        pred.to_csv(OUT/'predicciones_agosto.csv',index=False)
        ids=keys.numero_de_cliente.to_numpy();ix=np.lexsort((ids,-score));ix=ix[score[ix]>.0275]
        csv=OUT/'EnsembleVinculos197TabPFN35Promedio5Corte275.csv'
        csv.write_bytes(''.join(f'{int(ids[i])}\n' for i in ix).encode('ascii'))
        old=ref.score_promedio5.to_numpy()>.0275;new=score>.0275
        state.update(estado='completo_verificado_pendiente_archivo_entrega',segundos=time.perf_counter()-start,
            cuota_despues=str(get_api_usage()),csv_sha256=sha(csv),predicciones_sha256=sha(OUT/'predicciones_agosto.csv'),
            contactos=len(ix),comunes=int((old&new).sum()),agregados=int((new&~old).sum()),retirados=int((old&~new).sum()))
        used=lambda s:int(re.search(r'used (\d+)',s).group(1))
        try:state['creditos_consumidos']=used(state['cuota_despues'])-used(state['cuota_antes'])
        except (AttributeError,ValueError):pass
        save(state_path,state)
        print(json.dumps(state,indent=2),flush=True)
    except Exception:
        state['estado']='error_tras_inicio_revisar_consumo';save(state_path,state);raise


if __name__=='__main__':main()
