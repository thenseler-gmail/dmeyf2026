"""Ablación temporal de un segmento categórico, sin API ni envío al Bot."""
import argparse
import importlib
import json
import os
import time
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '4')
import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from baseline import preparar

pipe = importlib.import_module('89_catedra_pipeline')
SOURCES = ['mpayroll', 'cproductos', 'ctrx_quarter', 'mcuentas_saldo',
           'chomebanking_transacciones', 'cmobile_app_trx',
           'ctarjeta_visa_transacciones', 'ctarjeta_master_transacciones',
           'delta_1_mpayroll', 'delta_1_ctrx_quarter', 'delta_1_mcuentas_saldo']


def transform(frame):
    a = frame[SOURCES].to_numpy(dtype=float, copy=True)
    a[~np.isfinite(a)] = np.nan
    return np.sign(a) * np.log1p(np.abs(a))


def run(out):
    raw, audit = pipe.leer(final=True)
    _, cols = pipe.fuentes()
    ref = json.loads((pipe.SAL / '01_entregas_bot/16_EnsembleHist1895_20261006_143235/manifest.json').read_text(encoding='utf-8'))
    rows = []
    for month, training in [(202105, [202103, 202104]), (202106, [202103, 202104, 202105])]:
        folder = out / str(month)
        folder.mkdir(exist_ok=True)
        tr = raw[raw.foto_mes.isin(training)].reset_index(drop=True)
        va = raw[raw.foto_mes.eq(month)].reset_index(drop=True)
        imputer = SimpleImputer(strategy='median', add_indicator=True)
        scaler = StandardScaler()
        zt = scaler.fit_transform(imputer.fit_transform(transform(tr)))
        zv = scaler.transform(imputer.transform(transform(va)))
        # Limit extreme values using a fixed bound, independent of validation.
        zt = np.clip(zt, -5, 5)
        zv = np.clip(zv, -5, 5)
        cluster = MiniBatchKMeans(n_clusters=4, random_state=214363, n_init=10,
                                 batch_size=4096, max_iter=100)
        gt = cluster.fit_predict(zt)
        gv = cluster.predict(zv)
        assert set(gt) == {0, 1, 2, 3}
        joblib.dump(dict(imputer=imputer, scaler=scaler, cluster=cluster,
                         sources=SOURCES, log_signed=True, clip=5), folder / 'segmentador.joblib')
        profile = tr[SOURCES].assign(segmento=gt).groupby('segmento').median()
        profile['clientes_train'] = pd.Series(gt).value_counts()
        profile.to_csv(folder / 'perfil_segmentos.csv')
        va[pipe.KEYS].assign(segmento=gv).to_csv(folder / 'segmentos_validacion.csv', index=False)
        xt = preparar(tr, cols)[0]
        xv = preparar(va, cols)[0]
        y = tr.clase_ternaria.ne('CONTINUA').astype(int)
        pred = va[pipe.KEYS + ['clase_ternaria']].copy()
        for variant in ['control189', 'segmento190']:
            a, b = xt.copy(), xv.copy()
            if variant == 'segmento190':
                dtype = pd.CategoricalDtype(categories=[0, 1, 2, 3])
                a['segmento_cliente'] = pd.Series(gt, dtype=dtype)
                b['segmento_cliente'] = pd.Series(gv, dtype=dtype)
            for seed in pipe.SEEDS:
                pipe.save(out / 'estado.json', dict(estado='entrenando', mes=month,
                          variante=variant, seed=seed, api=False, creditos=0))
                q, rounds, seconds = pipe.fit_cached(folder / f'{variant}_{seed}.txt',
                        a, y, b, dict(ref['firma']['params'], seed=seed), 273)
                pred[f'{variant}_{seed}'] = q
                rows.append(dict(mes=month, variante=variant, seed=seed,
                       **pipe.metric(va.clase_ternaria.eq('BAJA+2'), q, va.numero_de_cliente)))
                pred.to_csv(folder / 'predicciones.csv', index=False)
            avg = pred[[f'{variant}_{s}' for s in pipe.SEEDS]].mean(axis=1)
            for n in [None, 10000, 10500, 11000, 11500, 12000]:
                rows.append(dict(mes=month, variante=variant, seed='promedio5',
                        corte='p>.025' if n is None else f'top{n}',
                        **pipe.metric(va.clase_ternaria.eq('BAJA+2'), avg, va.numero_de_cliente, n)))
    result = pd.DataFrame(rows)
    result.to_csv(out / 'resultados.csv', index=False)
    summary = result[result.seed.eq('promedio5')]
    text = ['# Segmentación: validación local', '',
            'Cuatro clusters aprendidos sin etiquetas ni datos de validación. '
            'Se agrega únicamente su identidad categórica al LightGBM189. '
            'Mismos parámetros, 273 árboles y cinco semillas en ambos brazos. '
            'Corrección ccajas_depositos aplicada a ambos. Target combinado; premio solo BAJA+2.', '',
            'Marzo–abril → mayo y marzo–mayo → junio. '
            'Meses reutilizados: esto es una comparación exploratoria, no un test independiente. '
            'Los cortes son diagnósticos; no se elige retrospectivamente uno para declarar victoria.', '',
            'Ganancia total y su 25%; promedio de probabilidades de cinco semillas:', '',
            '```text', summary.to_string(index=False), '```', '',
            'No se entrenó TabPFN, no se puntuó agosto ni se generaron entregas. '
            'Una mejora consistente en ambos meses justifica la siguiente prueba; '
            'no implica superar el resultado público de la entrega16.']
    (out / 'MINI_INFORME.md').write_text('\n'.join(text) + '\n', encoding='utf-8')
    pipe.save(out / 'manifest.json', dict(estado='completo', fuentes=SOURCES, clusters=4,
                fit_solo_train=True, semillas=pipe.SEEDS, params=ref['firma']['params'],
                rounds=273, auditoria=audit, api=False, creditos=0, enviado_bot=False,
                codigo_sha256=pipe.sha(Path(__file__))))
    pipe.save(out / 'estado.json', dict(estado='completo', api=False, creditos=0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', type=Path, required=True)
    ap.add_argument('--esperar-catedra', type=Path)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    try:
        if args.esperar_catedra:
            pipe.save(args.salida / 'estado.json', dict(estado='esperando_catedra', api=False, creditos=0))
            while True:
                state = json.loads((args.esperar_catedra / 'continuacion_estado.json').read_text(encoding='utf-8'))
                if str(state['estado']).startswith('error'):
                    raise RuntimeError(str(state))
                if state['estado'] == 'etapas_locales_completas_tabpfn_pendiente':
                    break
                import psutil
                alive = False
                for proc in psutil.process_iter(['cmdline']):
                    try:
                        if any(Path(arg).name == '95_continuar_catedra.py'
                               for arg in (proc.info['cmdline'] or [])):
                            alive = True
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                if not alive:
                    raise RuntimeError('La continuación de cátedra no está activa ni completa')
                time.sleep(10)
        run(args.salida)
    except Exception as error:
        pipe.save(args.salida / 'estado.json', dict(estado='error', error=str(error)))
        raise


if __name__ == '__main__':
    main()
