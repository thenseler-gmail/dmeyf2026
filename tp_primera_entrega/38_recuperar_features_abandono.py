"""Compara bloques descartados con cinco semillas fijas; no envia al Bot.

CV retrospectiva abril/mayo identica al control guardado y chequeo marzo->mayo.
Sin tuning, junio, etiquetas agosto, API ni exportacion de nuevas entregas.
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
from features_abandono import ACTIVIDAD, FUENTES, agregar_abandono

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT/'tp_primera_entrega/salidas'
KEYS = ['numero_de_cliente', 'foto_mes']
prep = importlib.import_module('33_reentrenar_lightgbm_haberes')
medir = importlib.import_module('30_validacion_lightgbm').medir


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def main():
    protocolo = json.loads((ROOT/'tp_primera_entrega/config_validacion_lightgbm.json').read_text())
    seeds = protocolo['politica_semillas_proximas_pruebas']['exploracion']
    assert seeds == [541440, 408476, 741961, 248865, 717444]
    ref = SAL/'top5_semillas_20261005_194616'
    assert json.loads((ref/'verificacion.json').read_text())['estado'] == 'verificado'
    rm = json.loads((ref/'manifest.json').read_text())
    for name, digest in rm['archivos_sha256'].items():
        assert sha(ref/name) == digest, name
    spec = rm['firma']['elegido']
    config = json.loads((ROOT/'tp_primera_entrega/config.json').read_text())
    datos, originales = prep.cargar_desarrollo(config)
    controlcols = originales + ['abandono_pasa_a_cero_mpayroll']
    assert controlcols == rm['firma']['features']
    nuevas = ['abandono_pasa_a_cero_'+c for c in ACTIVIDAD]
    conjuntas = ['abandono_reduce_productos', 'abandono_cantidad_actividades_en_caida',
                 'abandono_cantidad_frentes_en_caida', 'abandono_caida_tres_frentes']
    extra = agregar_abandono(datos[KEYS+FUENTES])
    datos = datos.merge(extra[KEYS+nuevas+conjuntas], on=KEYS, validate='one_to_one', sort=False)
    variantes = {'control_haberes': controlcols, 'mas_actividad_cero': controlcols+nuevas,
                 'mas_caidas_conjuntas': controlcols+conjuntas,
                 'mas_ambos': controlcols+nuevas+conjuntas}
    grupos = pd.read_csv(ref/'asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']], grupos[KEYS+['clase_ternaria']])
    folds = grupos.fold_cliente.to_numpy()
    y = datos.clase_ternaria.eq('BAJA+2').astype(int).to_numpy()
    x = preparar(datos, variantes['mas_ambos'])[0]
    out = SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('recuperar_abandono_%Y%m%d_%H%M%S')
    out.mkdir()
    cache = out/'cache'; cache.mkdir()
    grupos.to_csv(out/'asignacion_folds.csv', index=False)
    meta = dict(estado='evaluando', semillas=seeds, variantes=variantes, elegido=spec,
                umbral=.025, operador='>', target='BAJA+2', referencia=str(ref),
                criterio='Comparacion por mes y media 50/50 abril/mayo; control temporal marzo->mayo adicional',
                limitaciones='CV retrospectivo, fechas reutilizadas, semillas elegidas en abril/mayo; no test independiente. Marzo sin febrero limita historia del chequeo temporal. Agregar columnas cambia tambien feature_fraction.',
                entrenamientos_nuevos=0, api=False, creditos=0,
                codigo_sha256={f:sha(Path(__file__).parent/f) for f in
                    ['38_recuperar_features_abandono.py', '33_reentrenar_lightgbm_haberes.py',
                     'features.py', 'features_abandono.py', 'baseline.py', '30_validacion_lightgbm.py']},
                referencia_manifest_sha256=sha(ref/'manifest.json'))
    save(out/'manifest.json', meta)
    resultados = []; individuales = []; audit = []
    print('Salida:', out, flush=True)
    for variante, cols in variantes.items():
        for etapa, mes in [('cv_cliente', 202104), ('cv_cliente', 202105), ('temporal_marzo_mayo', 202105)]:
            ivmes = np.flatnonzero(datos.foto_mes.to_numpy() == mes)
            pred = datos.iloc[ivmes][KEYS+['clase_ternaria']].reset_index(drop=True)
            anterior = pd.read_csv(ref/f'oof_{mes}.csv') if etapa == 'cv_cliente' and variante == 'control_haberes' else None
            if anterior is not None:
                pd.testing.assert_frame_equal(pred, anterior[pred.columns])
            for seed in seeds:
                if anterior is not None:
                    pmes = anterior[f'p_seed{seed}'].to_numpy()
                else:
                    prob = np.full(len(datos), np.nan)
                    for fold in (range(4) if etapa == 'cv_cliente' else [-1]):
                        if etapa == 'cv_cliente':
                            it = np.flatnonzero((datos.foto_mes.to_numpy() <= mes) & (folds != fold))
                            iv = np.flatnonzero((datos.foto_mes.to_numpy() == mes) & (folds == fold))
                            assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
                        else:
                            it = np.flatnonzero(datos.foto_mes.to_numpy() == 202103)
                            iv = ivmes
                            assert datos.foto_mes.iloc[it].max() < mes
                        audit.append(dict(variante=variante, etapa=etapa, mes=mes, seed=seed, fold=fold,
                                          filas_fit=len(it), filas_eval=len(iv), max_mes_fit=int(datos.foto_mes.iloc[it].max())))
                        model = lgb.train(dict(spec['params'], seed=seed),
                                          lgb.Dataset(x.iloc[it][cols], label=y[it]),
                                          num_boost_round=spec['num_boost_round'])
                        p = model.predict(x.iloc[iv][cols], validate_features=True)
                        np.save(cache/f'{variante}_{etapa}_{mes}_{fold}_{seed}.npy', p, allow_pickle=False)
                        assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
                        prob[iv] = p
                        meta['entrenamientos_nuevos'] += 1
                        save(out/'manifest.json', meta)
                    pmes = prob[ivmes]
                pred[f'p_seed{seed}'] = pmes
                individuales.append(dict(variante=variante, etapa=etapa, mes=mes, seed=seed, **medir(pred, pmes)))
                print(variante, etapa, mes, 'semilla', seed, 'completa', flush=True)
            pred['probabilidad'] = pred[[f'p_seed{s}' for s in seeds]].mean(axis=1)
            pred.to_csv(out/f'{variante}_{etapa}_{mes}.csv', index=False)
            resultados.append(dict(variante=variante, etapa=etapa, mes=mes, features=len(cols), **medir(pred, pred.probabilidad)))
            pd.DataFrame(resultados).to_csv(out/'comparacion.csv', index=False)
            pd.DataFrame(individuales).to_csv(out/'resultados_semillas.csv', index=False)
            print('PROMEDIO5:', resultados[-1], flush=True)
    pd.DataFrame(audit).to_csv(out/'auditoria_fits.csv', index=False)
    tabla = pd.DataFrame(resultados)
    control = tabla[tabla.variante.eq('control_haberes')][['etapa', 'mes', 'ganancia']].rename(columns={'ganancia':'ganancia_control'})
    tabla = tabla.merge(control, on=['etapa', 'mes'], validate='many_to_one')
    tabla['diferencia_control'] = tabla.ganancia-tabla.ganancia_control
    tabla['diferencia_control_25pct'] = tabla.diferencia_control/4
    tabla.to_csv(out/'comparacion.csv', index=False)
    meta.update(estado='completo', auditoria_fits=len(audit),
                archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    save(out/'manifest.json', meta)
    print(tabla.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
