"""Curvas de ganancia de rankings guardados; sin entrenamiento ni API."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'salidas/catedra_implementacion_20261006_205501'
OUT = SOURCE / 'curvas_ganancia'
OUT.mkdir(exist_ok=True)
new = pd.read_csv(SOURCE / 'predicciones_top10_mayo.csv', float_precision='round_trip')
old = pd.read_csv(SOURCE / 'control_temporal/predicciones_mayo.csv', float_precision='round_trip')
keys = ['numero_de_cliente', 'foto_mes', 'clase_ternaria']
pd.testing.assert_frame_equal(new[keys], old[keys])
assert new.numero_de_cliente.is_unique and new.foto_mes.eq(202105).all()
seeds = [541440, 408476, 741961, 248865, 717444]
control = old[[f'p_seed{s}' for s in seeds]].mean(axis=1)
scores = {'LightGBM nuevo (10 configuraciones)': new.p_lgb_top10,
          'LightGBM control (5 semillas)': control,
          'Nuevo + TabPFN 50/50': new.score_mix50,
          'Control + TabPFN 50/50': (control + new.p_tabpfn) / 2}
colors = ['#1769aa', '#64748b', '#e07a1f', '#9437a8']
fig, (ax, marginal) = plt.subplots(2, 1, figsize=(12, 9), sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1]}, layout='constrained')
rows, blocks, maxima = [], [], []
for (name, score), color in zip(scores.items(), colors):
    assert np.isfinite(score).all()
    order = np.lexsort((new.numero_de_cliente.to_numpy(), -np.asarray(score)))
    labels = new.clase_ternaria.eq('BAJA+2').to_numpy()[order]
    tp = np.r_[0, np.cumsum(labels)]
    n = np.arange(len(tp))
    gain = tp * 1100000 - n * 27500
    # Independent cash-flow formula and recorded top10k comparison.
    assert gain[10000] == np.where(labels[:10000], 1072500, -27500).sum()
    window = np.arange(3000, 15001)
    best = int(window[np.argmax(gain[window])])
    maxima.append(dict(modelo=name, contactos_maximo_explorado=best,
                       ganancia=int(gain[best]), ganancia_25pct=float(gain[best]/4),
                       contactos_10000_ganancia=int(gain[10000])))
    ax.plot(n[:20001], gain[:20001]/1e6, label=name, color=color, linewidth=1.7)
    ax.scatter([best], [gain[best]/1e6], color=color, s=32)
    for k in range(0, 20001, 100):
        rows.append(dict(modelo=name, contactos=k, tp=int(tp[k]), fp=int(k-tp[k]),
                         ganancia=int(gain[k]), ganancia_25pct=float(gain[k]/4)))
    for start in range(0, 20000, 500):
        rate = labels[start:start+500].mean()
        blocks.append(dict(modelo=name, desde=start+1, hasta=start+500,
                          proporcion_baja2=float(rate),
                          ganancia_bloque=int(gain[start+500]-gain[start])))
    if name.startswith('LightGBM nuevo'):
        marginal.plot(np.arange(250, 20000, 500),
                      [labels[k:k+500].mean()*100 for k in range(0,20000,500)],
                      color=color, marker='o', markersize=3, label='BAJA+2 en cada bloque de 500 (nuevo)')
ax.axvline(10000, color='#334155', linestyle='--', alpha=.55, label='10.000 contactos: referencia')
ax.set_ylabel('Ganancia total ($ millones)')
ax.set_title('Mayo: ganancia al contactar los primeros N clientes del ranking\n'
             'Misma ventana marzo–abril → mayo; puntos = máximos exploratorios entre 3.000 y 15.000')
ax.grid(alpha=.2)
ax.legend(loc='lower right', fontsize=9)
secondary = ax.secondary_yaxis('right', functions=(lambda v:v/4, lambda v:v*4))
secondary.set_ylabel('25% de la ganancia ($ millones)')
marginal.axhline(2.5, color='#b91c1c', linestyle='--', label='Equilibrio económico: 2,5% BAJA+2 real')
marginal.set_ylabel('BAJA+2 observado (%)')
marginal.set_xlabel('Cantidad de clientes contactados, ordenados por score')
marginal.set_xlim(0, 20000)
marginal.grid(alpha=.2)
marginal.legend(fontsize=9)
fig.savefig(OUT / 'ganancia_mayo.png', dpi=160)
fig.savefig(OUT / 'ganancia_mayo.svg')
pd.DataFrame(rows).to_csv(OUT / 'curvas_mayo.csv', index=False)
pd.DataFrame(blocks).to_csv(OUT / 'bloques_marginales_mayo.csv', index=False)
pd.DataFrame(maxima).to_csv(OUT / 'maximos_exploratorios.csv', index=False)
report = ['# Curvas de ganancia en mayo', '',
          'Comparación de rankings con la misma ventana de entrenamiento. '
          'El control conserva parámetros16, pero no es la evaluación pública de16. '
          'Mayo se usó para elegir las configuraciones: máximos optimistas, no evidencia independiente.', '',
          '```text', pd.DataFrame(maxima).to_string(index=False), '```', '',
          'Los bloques de500 muestran si agregar contactos compensa: proporción BAJA+2 real '
          'mayor al2,5% aporta ganancia. No es un umbral aplicable directamente al score combinado.', '',
          'No hay predicciones en junio del ensemble Optuna nuevo. Las guardadas para junio '
          'corresponden a otros parámetros; no se superponen como si fueran este mismo modelo. '
          'Para comprobar estabilidad temporal de este ensemble hace falta entrenar las10 '
          'configuraciones congeladas en marzo–mayo y evaluarlas en junio.', '',
          'No se cambia ningún candidato ni se envía al Bot.']
(OUT / 'INFORME.md').write_text('\n'.join(report)+'\n', encoding='utf-8')
print(json.dumps(maxima, ensure_ascii=False, indent=2))
print('Grafico:', OUT / 'ganancia_mayo.png')
