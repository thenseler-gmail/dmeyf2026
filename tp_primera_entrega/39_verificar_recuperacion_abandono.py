"""Reconstruccion independiente de ganancias, promedios, folds y caches."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    out = Path(sys.argv[1])
    m = json.loads((out/'manifest.json').read_text())
    assert m['estado'] == 'completo'
    seeds = m['semillas']; ref = Path(m['referencia'])
    assert len(seeds) == len(set(seeds)) == 5
    for f, h in m['archivos_sha256'].items():
        assert hashlib.sha256((out/f).read_bytes()).hexdigest() == h
    grupos = pd.read_csv(out/'asignacion_folds.csv')
    assert grupos.groupby('numero_de_cliente').fold_cliente.nunique().max() == 1
    resultados = pd.read_csv(out/'comparacion.csv')
    individuales = pd.read_csv(out/'resultados_semillas.csv')
    assert len(resultados) == 12 and len(individuales) == 60
    n = 0
    for row in resultados.itertuples(index=False):
        p = pd.read_csv(out/f'{row.variante}_{row.etapa}_{row.mes}.csv')
        g = grupos.loc[grupos.foto_mes.eq(row.mes)].reset_index(drop=True)
        pd.testing.assert_frame_equal(p[['numero_de_cliente','foto_mes','clase_ternaria']], g[['numero_de_cliente','foto_mes','clase_ternaria']])
        assert not p.numero_de_cliente.duplicated().any()
        y = p.clase_ternaria.eq('BAJA+2').to_numpy()
        def check(prob, r):
            assert np.isfinite(prob).all() and ((prob >= 0) & (prob <= 1)).all()
            sel = prob > .025
            tp = int((sel & y).sum()); fp = int((sel & ~y).sum())
            gain = tp*1072500-fp*27500
            assert (r.contactos, r.tp, r.fp, r.ganancia, r.ganancia_25pct) == (tp+fp,tp,fp,gain,gain/4)
        for seed in seeds:
            prob = p[f'p_seed{seed}'].to_numpy()
            r = individuales.loc[individuales.variante.eq(row.variante) & individuales.etapa.eq(row.etapa) & individuales.mes.eq(row.mes) & individuales.seed.eq(seed)]
            assert len(r) == 1
            check(prob, r.iloc[0])
            if row.variante == 'control_haberes' and row.etapa == 'cv_cliente':
                old = pd.read_csv(ref/f'oof_{row.mes}.csv')
                np.testing.assert_allclose(prob, old[f'p_seed{seed}'], rtol=0, atol=0)
            elif row.etapa == 'cv_cliente':
                for fold in range(4):
                    cp = out/'cache'/f'{row.variante}_{row.etapa}_{row.mes}_{fold}_{seed}.npy'
                    np.testing.assert_allclose(prob[g.fold_cliente.eq(fold)], np.load(cp), rtol=0, atol=1e-15)
            else:
                cp = out/'cache'/f'{row.variante}_{row.etapa}_{row.mes}_-1_{seed}.npy'
                np.testing.assert_allclose(prob, np.load(cp), rtol=0, atol=1e-15)
            n += 1
        np.testing.assert_allclose(p.probabilidad, p[[f'p_seed{s}' for s in seeds]].mean(axis=1), rtol=0, atol=1e-15)
        check(p.probabilidad.to_numpy(), row)
        control = resultados.loc[resultados.variante.eq('control_haberes') & resultados.etapa.eq(row.etapa) & resultados.mes.eq(row.mes)].iloc[0]
        assert row.diferencia_control == row.ganancia-control.ganancia
        assert row.diferencia_control_25pct == row.diferencia_control/4
    audit = pd.read_csv(out/'auditoria_fits.csv')
    assert len(audit) == m['entrenamientos_nuevos'] == 140
    for a in audit.itertuples(index=False):
        if a.etapa == 'cv_cliente':
            it = grupos.loc[(grupos.foto_mes <= a.mes) & grupos.fold_cliente.ne(a.fold)]
            iv = grupos.loc[grupos.foto_mes.eq(a.mes) & grupos.fold_cliente.eq(a.fold)]
            assert set(it.numero_de_cliente).isdisjoint(set(iv.numero_de_cliente))
        else:
            it = grupos.loc[grupos.foto_mes.eq(202103)]
            iv = grupos.loc[grupos.foto_mes.eq(202105)]
            assert it.foto_mes.max() < iv.foto_mes.min()
        assert (len(it),len(iv),it.foto_mes.max()) == (a.filas_fit,a.filas_eval,a.max_mes_fit)
    verification = dict(estado='verificado', resultados_individuales=n, ensembles=12, fits_auditados=len(audit), umbral=.025, creditos=0)
    (out/'verificacion.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
    print(verification)


if __name__ == '__main__':
    main()
