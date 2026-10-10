"""Comparación local contra16 con TabPFN original, sin entrenamiento ni API."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

SAL = Path(__file__).resolve().parent / 'salidas'
BASE = SAL / 'features_local_20261006_140702/historia_1_mes/predicciones_mayo.csv'
NEW = SAL / 'comparacion_lightgbm_20261008/202105/predicciones.csv'
OUT = SAL / 'control213_tab16_local_20261009'
SEEDS = [541440, 408476, 741961, 248865, 717444]


def metric(y, score):
    mask = np.asarray(score) > .025
    contacts = int(mask.sum())
    tp = int((mask & y).sum())
    gain = tp * 1100000 - contacts * 27500
    return dict(contactos=contacts, tp=tp, ganancia=gain, ganancia_25pct=gain/4)


def main():
    OUT.mkdir(exist_ok=True)
    base = pd.read_csv(BASE, float_precision='round_trip')
    new = pd.read_csv(NEW, float_precision='round_trip')
    keys = ['numero_de_cliente', 'foto_mes', 'clase_ternaria']
    pd.testing.assert_frame_equal(base[keys], new[keys])
    assert base.numero_de_cliente.is_unique
    y = base.clase_ternaria.eq('BAJA+2').to_numpy()
    rows, parts = [], []
    scores = base[keys+['p_tabpfn']].copy()
    variants = {'entrega16': (base, 'p_seed{}'),
                'control189_marzo_abril': (new, 'control189_seed{}'),
                'control213_marzo_abril': (new, 'control213_seed{}')}
    for variant, (frame, pattern) in variants.items():
        for seed in SEEDS:
            score = (frame[pattern.format(seed)].to_numpy()+base.p_tabpfn.to_numpy())/2
            assert np.isfinite(score).all()
            scores[f'{variant}_seed{seed}'] = score
            rows.append(dict(variante=variant, seed=seed, **metric(y, score)))
            for part in range(4):
                mask = base.parte_cliente.eq(part).to_numpy()
                parts.append(dict(variante=variant, seed=seed, parte=part,
                                  **metric(y[mask], score[mask])))
    individual = pd.DataFrame(rows)
    individual['delta16'] = individual.ganancia - individual.seed.map(
        individual[individual.variante.eq('entrega16')].set_index('seed').ganancia)
    summary = individual.groupby('variante')[['contactos','tp','ganancia','ganancia_25pct']].mean()
    assert summary.loc['entrega16','ganancia'] == 266420000
    summary['delta16_total'] = summary.ganancia-summary.loc['entrega16','ganancia']
    summary['delta16_25pct'] = summary.delta16_total/4
    summary['semillas_superan16'] = individual.groupby('variante').delta16.apply(lambda x: int((x>0).sum()))
    paired = pd.DataFrame(parts)
    partmean = paired.groupby(['variante','parte']).ganancia.mean().unstack(0)
    for variant in variants:
        summary.loc[variant,'partes_superan16'] = int((partmean[variant]>partmean.entrega16).sum())
    individual.to_csv(OUT/'resultados_semillas.csv',index=False)
    paired.to_csv(OUT/'resultados_partes.csv',index=False)
    summary.to_csv(OUT/'resumen.csv')
    scores.to_csv(OUT/'scores_mayo.csv',index=False)
    manifest = dict(estado='completo_verificado', mes=202105, mezcla=[.5,.5],
                    corte='score > 0.025, por semilla; media de cinco ganancias',
                    fuentes={str(p.relative_to(SAL)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [BASE,NEW]}, api=False,creditos=0,submits=0,
                    control16_total_reproducido=266420000,
                    limitacion='16: abril a mayo; nuevos LGB: marzo+abril a mayo, corrección ccajas. Mayo reutilizado. Sin TabPFN junio ni resultado público nuevo.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report = ['# Control213 + TabPFN original contra entrega16','',
              'Mismos clientes de mayo, mismo TabPFN202 original, mezcla50/50 y corte estricto >2,5%. '
              'Se informa la media de ganancias de cinco listas individuales, igual que16.', '',
              '```text',summary.to_string(),'```','',
              'Entrega16: LightGBM entrenado en abril. Los dos controles nuevos: marzo+abril, '
              'corrección ccajas aplicada. Control189 nuevo permite comparar189/213 a igual ventana. '
              'No se cambian pesos ni corte. Mayo reutilizado; no es una validación independiente '
              'ni un resultado público. Sin entrenamiento, API, créditos ni envío al Bot.']
    (OUT/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(summary.to_string())


if __name__ == '__main__':
    main()
