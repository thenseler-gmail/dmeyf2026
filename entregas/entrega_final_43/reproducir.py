"""Reproduce la lista 43 desde modelos congelados o probabilidades guardadas."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
KEYS = ['numero_de_cliente', 'foto_mes']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verificar_archivos():
    hashes = json.loads((ROOT / 'SHA256SUMS.json').read_text(encoding='utf-8'))
    for name, expected in hashes.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f'Artefacto modificado: {name}')


def inferir(dataset, ref, config):
    import duckdb
    import lightgbm as lgb
    from features import HISTORICAS, HISTORICAS_EXTRA, agregar_historicas_ampliadas
    from features_vinculos import FUENTES, agregar_vinculos

    # Las etiquetas no se extraen para inferencia, ni siquiera las de agosto.
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(dataset)).create_view('datos')
        raw = con.sql('SELECT * EXCLUDE(clase_ternaria) FROM datos '
                      'WHERE foto_mes=202108 ORDER BY foto_mes,numero_de_cliente').df()
        columns = list(dict.fromkeys(KEYS + HISTORICAS + HISTORICAS_EXTRA + FUENTES))
        history = con.sql('SELECT ' + ','.join(columns) + ' FROM datos '
                          'WHERE foto_mes BETWEEN 202103 AND 202108 '
                          'ORDER BY foto_mes,numero_de_cliente').df()
    if raw.duplicated(KEYS).any() or history.duplicated(KEYS).any():
        raise ValueError('Claves cliente-mes duplicadas')
    hist = agregar_historicas_ampliadas(history[KEYS + HISTORICAS + HISTORICAS_EXTRA])
    derived = [c for c in hist if c not in KEYS + HISTORICAS + HISTORICAS_EXTRA]
    raw = raw.merge(hist[KEYS + derived], on=KEYS, validate='one_to_one', sort=False)
    raw = raw.merge(agregar_vinculos(history[KEYS + FUENTES]), on=KEYS,
                    validate='one_to_one', sort=False)
    pd.testing.assert_frame_equal(raw[KEYS], ref[KEYS])
    # Mismas reglas fijas de baseline.preparar; sin imputacion ni correccion posterior.
    x = raw[config['features_lightgbm']].astype(float).copy()
    x = x.replace([np.inf, -np.inf], np.nan)
    for c in ['Visa_Fvencimiento', 'Master_Fvencimiento']:
        x.loc[x[c] < -36500, c] = np.nan
    matrix_hash = hashlib.sha256(x.to_numpy(dtype=np.float32).tobytes()).hexdigest()
    if matrix_hash != config['matriz_agosto_sha256']:
        raise ValueError('La matriz de agosto difiere de la utilizada en la entrega 43')
    probabilities = []
    errors = {}
    for seed in config['semillas']:
        model = lgb.Booster(model_file=str(ROOT / 'modelos' / f'seed{seed}.txt'))
        if model.feature_name() != config['features_lightgbm'] or model.num_trees() != 273:
            raise ValueError('Modelo incompatible')
        p = model.predict(x, validate_features=True, num_threads=4)
        expected = ref[f'p_lgb_seed{seed}'].to_numpy()
        np.testing.assert_allclose(p, expected, rtol=0, atol=1e-15)
        errors[str(seed)] = float(np.max(np.abs(p - expected)))
        probabilities.append(p)
    return np.column_stack(probabilities), matrix_hash, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, help='competencia_01.csv original: recalcula LightGBM')
    parser.add_argument('--salida', type=Path, default=Path('resultado_43'))
    args = parser.parse_args()
    verificar_archivos()
    config = json.loads((ROOT / 'configuracion.json').read_text(encoding='utf-8'))
    ref = pd.read_csv(ROOT / 'artefactos' / 'predicciones_agosto.csv.gz', float_precision='round_trip')
    if len(ref) != 164647 or not ref.foto_mes.eq(202108).all() or ref.numero_de_cliente.duplicated().any():
        raise ValueError('Referencia de agosto incompatible')
    matrix_hash, errors = None, {}
    if args.dataset:
        probabilities, matrix_hash, errors = inferir(args.dataset.resolve(), ref, config)
    else:
        probabilities = ref[[f'p_lgb_seed{s}' for s in config['semillas']]].to_numpy()
    score = .5 * probabilities.mean(axis=1) + .5 * ref.p_tabpfn.to_numpy()
    if not np.isfinite(score).all() or ((score < 0) | (score > 1)).any():
        raise ValueError('Scores invalidos')
    np.testing.assert_allclose(score, ref.score_promedio5, rtol=0, atol=1e-15)
    ids = ref.numero_de_cliente.to_numpy()
    selected = np.lexsort((ids, -score))
    selected = selected[score[selected] > config['umbral']]
    content = ''.join(f'{int(ids[i])}\n' for i in selected).encode('ascii')
    result_hash = hashlib.sha256(content).hexdigest()
    if result_hash != config['prediccion_final_sha256'] or len(selected) != 10404:
        raise ValueError('La lista generada no coincide exactamente con la entrega 43')
    args.salida.mkdir(parents=True, exist_ok=True)
    output = args.salida / 'prediccion_final.csv'
    # Nunca sobrescribir un artefacto firmado del paquete.
    if output.resolve().is_relative_to(ROOT) and output.resolve() == (ROOT / 'prediccion_final.csv').resolve():
        raise ValueError('Elegir otra carpeta de salida')
    output.write_bytes(content)
    report = dict(estado='identico_byte_por_byte', contactos=len(selected), sha256=result_hash,
                  modo='modelos_y_dataset' if args.dataset else 'probabilidades_guardadas',
                  matriz_agosto_sha256=matrix_hash, error_maximo_por_modelo=errors,
                  api=False, creditos=0)
    (args.salida / 'VERIFICACION.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
