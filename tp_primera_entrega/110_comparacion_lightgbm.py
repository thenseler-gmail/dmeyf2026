"""Matriz189/213 × parámetros control/nuevos, cinco semillas, mayo/junio.

Configuración y árboles congelados antes de junio. Sin API ni Bot.
"""
import argparse
import importlib
import json
import shutil
import time
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from baseline import preparar

pipe = importlib.import_module('89_catedra_pipeline')
STUDY = pipe.SAL / 'catedra_implementacion_20261006_205501'
JUNE = pipe.SAL / 'orden2_junio_20261007_153616'
GRID = list(range(5000, 15001, 500))
VARIANTS = ['control189', 'control213', 'nuevo189', 'nuevo213']


def plan(out):
    ref = json.loads((pipe.SAL / '01_entregas_bot/16_EnsembleHist1895_20261006_143235/manifest.json').read_text(encoding='utf-8'))
    frozen = json.loads((STUDY / 'top10_congelado.json').read_text(encoding='utf-8'))
    best = sorted(frozen['configuraciones'], key=lambda x: (-x['auc'], x['trial']))[0]
    _, cols = pipe.fuentes()
    settings = dict(semillas=pipe.SEEDS, control_params=ref['firma']['params'],
                    control_rounds=273, nuevo_params=dict(pipe.FIXED, **{
                    k:v for k,v in best['params'].items() if k != 'num_iterations'}),
                    nuevo_rounds=best['effective_rounds'], trial_congelado=best,
                    features189=cols, features213=cols+pipe.ORDEN2,
                    train_mayo=[202103,202104], train_junio=[202103,202104,202105],
                    grid_contactos=GRID, target='BAJA+1/BAJA+2', premio='BAJA+2',
                    undersampling=False, seleccion_corte='Solo mayo, promedio5, grilla500',
                    junio='Sin tuning ni early stopping', api=False, creditos=0,
                    codigo={f:pipe.sha(pipe.TP/f) for f in [
                        '110_comparacion_lightgbm.py','89_catedra_pipeline.py',
                        'features_catedra.py','features.py','calidad_datos.py','baseline.py']})
    path = out / 'PLAN.json'
    if path.exists():
        assert json.loads(path.read_text(encoding='utf-8')) == settings, 'Cambió el plan congelado'
    else:
        pipe.save(path, settings)
        code = out / 'codigo'
        code.mkdir(exist_ok=True)
        for f in settings['codigo']:
            shutil.copy2(pipe.TP/f, code/f)
    return settings


def curve(y, q, ids):
    order = np.lexsort((np.asarray(ids), -np.asarray(q)))
    return np.r_[0, np.cumsum(np.asarray(y)[order])] * 1100000 - np.arange(len(q)+1)*27500


def reuse(month, variant, seed, dest, xv, va):
    if month == 202105 and variant == 'control189':
        model = STUDY / 'control_temporal' / f'seed{seed}.txt'
        saved = pd.read_csv(STUDY / 'control_temporal/predicciones_mayo.csv', float_precision='round_trip')
        col = f'p_seed{seed}'
    elif month == 202106 and variant in ['control189','control213']:
        original = 'control189' if variant == 'control189' else 'orden2_213'
        model = JUNE / original / f'seed{seed}.txt'
        saved = pd.read_csv(JUNE / 'predicciones_junio.csv', float_precision='round_trip')
        col = f'{original}_seed{seed}'
    else:
        return
    if dest.exists():
        return
    pd.testing.assert_frame_equal(va[pipe.KEYS+['clase_ternaria']], saved[pipe.KEYS+['clase_ternaria']])
    booster = lgb.Booster(model_file=str(model))
    assert booster.feature_name() == list(xv)
    assert booster.num_trees() == 273
    np.testing.assert_allclose(booster.predict(xv, validate_features=True), saved[col], atol=1e-12, rtol=0)
    shutil.copy2(model, dest)
    assert pipe.sha(model) == pipe.sha(dest)


def run(out, settings):
    data, audit = pipe.leer(final=True)
    data = data[data.foto_mes.ne(202108)].reset_index(drop=True)
    allrows, curves, meanrows = [], [], []
    for month, train in [(202105,settings['train_mayo']), (202106,settings['train_junio'])]:
        tr = data[data.foto_mes.isin(train)].reset_index(drop=True)
        va = data[data.foto_mes.eq(month)].reset_index(drop=True)
        y = tr.clase_ternaria.ne('CONTINUA').astype(int)
        prize = va.clase_ternaria.eq('BAJA+2').to_numpy()
        pred = va[pipe.KEYS+['clase_ternaria']].copy()
        folder = out / str(month)
        folder.mkdir(exist_ok=True)
        for variant in VARIANTS:
            cols = settings['features213' if variant.endswith('213') else 'features189']
            family = 'control' if variant.startswith('control') else 'nuevo'
            params, rounds = settings[family+'_params'], settings[family+'_rounds']
            xt, xv = preparar(tr,cols)[0], preparar(va,cols)[0]
            for seed in settings['semillas']:
                pipe.save(out/'estado.json', dict(estado='entrenando', mes=month,
                          variante=variant, seed=seed, api=False, creditos=0))
                path = folder/f'{variant}_seed{seed}.txt'
                reuse(month,variant,seed,path,xv,va)
                q, actual, seconds = pipe.fit_cached(path,xt,y,xv,dict(params,seed=seed),rounds)
                assert actual == rounds
                assert np.isfinite(q).all()
                pred[f'{variant}_seed{seed}'] = q
                g = curve(prize,q,va.numero_de_cliente)
                for n in GRID:
                    allrows.append(dict(mes=month,variante=variant,seed=seed,contactos=n,
                                    ganancia=int(g[n]),ganancia_25pct=float(g[n]/4)))
                pred.to_csv(folder/'predicciones.csv',index=False)
                pipe.save(folder/f'{variant}_seed{seed}_auditoria.json', dict(
                       modelo_sha256=pipe.sha(path),arboles=actual,segundos=seconds,
                       auc_combinado=roc_auc_score(va.clase_ternaria.ne('CONTINUA'),q),
                       auc_baja2=roc_auc_score(prize,q)))
            avg = pred[[f'{variant}_seed{s}' for s in settings['semillas']]].mean(axis=1)
            g = curve(prize,avg,va.numero_de_cliente)
            for n in range(0,20001,100):
                curves.append(dict(mes=month,variante=variant,contactos=n,
                                   ganancia=int(g[n]),ganancia_25pct=float(g[n]/4)))
            for n in GRID:
                meanrows.append(dict(mes=month,variante=variant,contactos=n,
                                    ganancia=int(g[n]),ganancia_25pct=float(g[n]/4)))
    individual = pd.DataFrame(allrows)
    avg = pd.DataFrame(meanrows)
    individual.to_csv(out/'ganancias_semillas.csv',index=False)
    avg.to_csv(out/'ganancias_promedio_probabilidades.csv',index=False)
    cuts = {}
    for variant in VARIANTS:
        may = avg[(avg.mes==202105)&(avg.variante==variant)]
        cuts[variant] = int(may.sort_values(['ganancia','contactos'],ascending=[False,True]).iloc[0].contactos)
    control_cut = cuts['control189']
    rows = []
    for variant in VARIANTS:
        for month in [202105,202106]:
            value = avg[(avg.mes==month)&(avg.variante==variant)&(avg.contactos==cuts[variant])].iloc[0]
            base = avg[(avg.mes==month)&(avg.variante=='control189')&(avg.contactos==control_cut)].iloc[0]
            a = individual[(individual.mes==month)&(individual.variante==variant)&(individual.contactos==cuts[variant])].set_index('seed').ganancia
            b = individual[(individual.mes==month)&(individual.variante=='control189')&(individual.contactos==control_cut)].set_index('seed').ganancia
            rows.append(dict(mes=month,variante=variant,corte_elegido_mayo=cuts[variant],
                         ganancia_promedio_probabilidades=int(value.ganancia),
                         ganancia_25pct=float(value.ganancia/4),delta_control=int(value.ganancia-base.ganancia),
                         delta_control_25pct=float((value.ganancia-base.ganancia)/4),
                         semillas_superan_control=int((a>b).sum()),
                         media_ganancias_semillas=float(a.mean()),std_ganancias_semillas=float(a.std(ddof=1))))
    summary = pd.DataFrame(rows)
    summary.to_csv(out/'resumen_corte_mayo_fijo.csv',index=False)
    curves = pd.DataFrame(curves)
    curves.to_csv(out/'curvas.csv',index=False)
    fig, axes = plt.subplots(1,2,figsize=(14,5),layout='constrained')
    for ax, month in zip(axes,[202105,202106]):
        for variant in VARIANTS:
            frame = curves[(curves.mes==month)&(curves.variante==variant)]
            ax.plot(frame.contactos,frame.ganancia/1e6,label=variant)
        ax.set_title(f'{month}: mismas cinco semillas por variante')
        ax.set_xlabel('Clientes contactados');ax.set_ylabel('Ganancia total ($ millones)')
        ax.secondary_yaxis('right',functions=(lambda x:x/4,lambda x:x*4)).set_ylabel('25% ($ millones)')
        ax.grid(alpha=.2);ax.legend()
    fig.savefig(out/'curvas_mayo_junio.png',dpi=160)
    lines=['# Comparación LightGBM: variables y parámetros','',
           '189/213 variables × parámetros control/nuevos, cinco semillas comunes. '
           'Nuevos: mejor configuración por AUC de mayo (trial12), árboles congelados, sin tuning en junio. '
           'No es el ensemble de10 configuraciones. Corrección ccajas aplicada a todos; sin undersampling.', '',
           'Marzo–abril→mayo y marzo–mayo→junio. Corte elegido en mayo en grilla5.000–15.000 '
           'paso500 y aplicado igual en junio. No se informa como resultado principal el máximo retrospectivo de junio.', '',
           '```text',summary.to_string(index=False),'```','',
           'Ganancia del promedio de probabilidades y media de ganancias de semillas son distintas. '
           'La desviación entre semillas no estima incertidumbre temporal. Semillas previamente seleccionadas '
           'por resultados históricos; mayo y junio reutilizados, no tests independientes. '
           'Junio tiene aguinaldo. Control189 temporal distinto del submit16 (abril+mayo→agosto).', '',
           'Considerar candidatos solo con delta positivo en ambos meses y revisar diferencias pareadas '
           'por semilla y curvas a igual cantidad de contactos. No se garantiza la mejor configuración posible. '
           'No API, puntuación agosto ni envío al Bot.']
    (out/'MINI_INFORME.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pipe.save(out/'estado.json',dict(estado='completo',api=False,creditos=0,auditoria=audit))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True)
    ap.add_argument('--solo-plan',action='store_true');ap.add_argument('--esperar-catedra',action='store_true')
    args=ap.parse_args();args.salida.mkdir(parents=True,exist_ok=True)
    settings=plan(args.salida)
    if args.solo_plan:return
    try:
        if args.esperar_catedra:
            pipe.save(args.salida/'estado.json',dict(estado='esperando_catedra',api=False,creditos=0))
            while True:
                state=json.loads((STUDY/'continuacion_estado.json').read_text(encoding='utf-8'))
                if state['estado']=='etapas_locales_completas_tabpfn_pendiente':break
                if state['estado'].startswith('error'):raise RuntimeError(str(state))
                import psutil
                alive=False
                for proc in psutil.process_iter(['cmdline']):
                    try:
                        if any(Path(a).name=='95_continuar_catedra.py' for a in (proc.info['cmdline'] or [])):alive=True
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                if not alive:raise RuntimeError('Continuación cátedra ausente e incompleta')
                time.sleep(10)
        run(args.salida,settings)
    except Exception as e:
        pipe.save(args.salida/'estado.json',dict(estado='error',error=str(e)));raise


if __name__=='__main__':main()
