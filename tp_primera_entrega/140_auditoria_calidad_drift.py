"""Auditoria de predictores sin etiquetas, fits ni cambios del CSV fuente."""
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TP = ROOT / 'tp_primera_entrega'
OUT = TP / 'salidas/auditoria_calidad_drift_20261010_v3'
FIELDS = ['ccajas_depositos', 'ccajas_transacciones', 'ccajas_extracciones',
          'cprestamos_personales', 'mprestamos_personales',
          'Master_Finiciomora', 'Visa_Finiciomora', 'Master_status', 'Visa_status',
          'Master_Fvencimiento', 'Visa_Fvencimiento', 'Master_fultimo_cierre',
          'Visa_fultimo_cierre', 'Master_fechaalta', 'Visa_fechaalta',
          'Master_msaldototal', 'Visa_msaldototal', 'Master_mpagominimo', 'Visa_mpagominimo',
          'ctarjeta_master', 'ctarjeta_visa']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def dictionary(path):
    ns = {'t': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
          'x': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    with zipfile.ZipFile(path) as z:
        tree = ET.fromstring(z.read('content.xml'))
    result = {}
    for row in tree.findall('.//t:table-row', ns):
        cells = [' '.join(''.join(p.itertext()) for p in c.findall('x:p', ns))
                 for c in row.findall('t:table-cell', ns)]
        if len(cells) >= 4 and cells[1] in FIELDS:
            result[cells[1]] = {'unidad': cells[2], 'descripcion': cells[3]}
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    config = json.loads((TP / 'config.json').read_text(encoding='utf-8-sig'))
    source = ROOT / config['dataset']
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    dic = ROOT / 'dmeyf2026-9c6f_DiccionarioDatos_2026.ods'
    defs = dictionary(dic)
    codepaths = [Path(__file__), TP / 'calidad_datos.py', TP / 'baseline.py',
                 TP / '63_experimentos_features_local.py', TP / '66_preparar_entrega_hist189.py',
                 ROOT / 'monday/z701_drifting.ipynb', ROOT / 'arboles/z0607_ParadigmShift.ipynb', dic]
    plan = {'estado': 'plan_congelado_antes_de_resultados', 'fecha': '2026-10-10',
            'fuente': config['dataset'], 'fuente_bytes_mtime': before,
            'campos': FIELDS, 'meses': [202103, 202104, 202105, 202106, 202107, 202108],
            'referencia_psi': 202104, 'bins_psi': 'deciles abril finitos, extremos infinitos, bin faltante aparte; suavizado1e-6',
            'objetivo': 'Auditar nulos, ceros, negativos, dominio y distribuciones; distinguir indicios de errores confirmados.',
            'etiquetas_leidas': False, 'fits': 0, 'api': False,
            'correcciones_automaticas': False,
            'codigo_material_sha256': {str(p.relative_to(ROOT)): sha(p) for p in codepaths}}
    save(OUT / 'PLAN.json', plan)
    save(OUT / 'DICCIONARIO_CAMPOS.json', defs)
    with duckdb.connect() as con:
        con.execute('SET threads=2')
        con.read_csv(str(source)).create_view('datos')
        schema = [r[0] for r in con.sql('DESCRIBE datos').fetchall()]
        assert set(FIELDS).issubset(schema), set(FIELDS) - set(schema)
        # Projection explicitement excludes labels, including June and August.
        query = 'SELECT numero_de_cliente,foto_mes,' + ','.join(FIELDS) + ' FROM datos ORDER BY foto_mes,numero_de_cliente'
        data = con.sql(query).df()
    assert 'clase_ternaria' not in data
    assert not data.duplicated(['numero_de_cliente', 'foto_mes']).any()
    assert sorted(data.foto_mes.unique().tolist()) == plan['meses']
    rows = []
    for month, frame in data.groupby('foto_mes'):
        for field in FIELDS:
            x = frame[field].to_numpy(dtype=float)
            finite = x[np.isfinite(x)]
            q = np.quantile(finite, [.01, .5, .99]) if finite.size else [None] * 3
            row = dict(campo=field, mes=int(month), filas=len(x), nulos=int(np.isnan(x).sum()),
                       no_finitos_no_nulos=int((~np.isfinite(x) & ~np.isnan(x)).sum()),
                       ceros=int((x == 0).sum()), negativos=int((x < 0).sum()),
                       fraccionarios=int((finite != np.floor(finite)).sum()),
                       minimo=float(finite.min()) if finite.size else None,
                       maximo=float(finite.max()) if finite.size else None,
                       q01=q[0], mediana=q[1], q99=q[2],
                       pct_nulos=float(np.isnan(x).mean() * 100), pct_ceros=float((x == 0).mean() * 100))
            if field in ['Master_status', 'Visa_status']:
                row['fuera_dominio_documentado'] = int((~np.isin(finite, [0, 6, 7, 9])).sum())
            elif field.startswith('c'):
                row['fuera_dominio_documentado'] = int(((finite < 0) | (finite != np.floor(finite))).sum())
            else:
                row['fuera_dominio_documentado'] = None
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / 'distribuciones_mensuales.csv', index=False)
    psirows = []
    reference = data.loc[data.foto_mes.eq(202104)]
    for field in FIELDS:
        x = reference[field].to_numpy(dtype=float)
        finite = x[np.isfinite(x)]
        edges = np.r_[-np.inf, np.unique(np.quantile(finite, np.arange(1, 10) / 10)), np.inf]

        def histogram(values):
            a = values.to_numpy(dtype=float)
            counts = np.r_[np.histogram(a[np.isfinite(a)], bins=edges)[0], (~np.isfinite(a)).sum()]
            assert counts.sum() == len(a)
            rates = counts / counts.sum()
            rates = np.maximum(rates, 1e-6)
            return rates / rates.sum()

        p = histogram(reference[field])
        for month, frame in data.groupby('foto_mes'):
            q = histogram(frame[field])
            psirows.append(dict(campo=field, mes=int(month), referencia=202104,
                                psi=float(((q - p) * np.log(q / p)).sum()), bins_numericos=len(edges) - 1))
    pd.DataFrame(psirows).to_csv(OUT / 'psi_abril_fijo.csv', index=False)
    # Compare retained clients to April to diagnose population composition.
    pairs = []
    for month in [202103, 202105, 202106, 202107, 202108]:
        joined = reference.merge(data.loc[data.foto_mes.eq(month)], on='numero_de_cliente',
                                 suffixes=('_abril', '_otro'), validate='one_to_one')
        for field in ['ccajas_depositos', 'Master_Finiciomora', 'Visa_Finiciomora']:
            a = joined[field + '_abril']; b = joined[field + '_otro']
            pairs.append(dict(campo=field, mes=month, clientes_comunes=len(joined),
                              abril_nulos=int(a.isna().sum()), otro_nulos=int(b.isna().sum()),
                              abril_ceros=int(a.eq(0).sum()), otro_ceros=int(b.eq(0).sum()),
                              pasa_no_cero_a_cero=int((a.notna() & a.ne(0) & b.eq(0)).sum()),
                              pasa_nulo_a_cero=int((a.isna() & b.eq(0)).sum())))
    pd.DataFrame(pairs).to_csv(OUT / 'clientes_comunes_abril.csv', index=False)
    strata = []
    for month, frame in data.groupby('foto_mes'):
        for brand in ['Master', 'Visa']:
            for status, sub in frame.groupby(brand + '_status', dropna=False):
                x = sub[brand + '_Finiciomora']
                strata.append(dict(mes=int(month), tarjeta=brand,
                                   status=None if pd.isna(status) else float(status), filas=len(sub),
                                   nulos=int(x.isna().sum()), ceros=int(x.eq(0).sum()),
                                   negativos=int(x.lt(0).sum()), positivos=int(x.gt(0).sum())))
    pd.DataFrame(strata).to_csv(OUT / 'mora_por_estado.csv', index=False)
    # Verify the established correction without mutating the source or baseline.
    from calidad_datos import corregir_datos
    sample = data[['numero_de_cliente', 'foto_mes', 'ccajas_depositos']].copy()
    corrected, audit = corregir_datos(sample)
    may = sample.foto_mes.eq(202105)
    assert sample.loc[may, 'ccajas_depositos'].eq(0).all()
    assert corrected.loc[may, 'ccajas_depositos'].isna().all()
    pd.testing.assert_frame_equal(sample.loc[~may], corrected.loc[~may], check_dtype=False)
    pd.testing.assert_frame_equal(corrected, corregir_datos(corrected)[0])
    assert before == (source.stat().st_size, source.stat().st_mtime_ns)
    sourcehash = sha(source)
    assert before == (source.stat().st_size, source.stat().st_mtime_ns)
    manifest = dict(estado='auditoria_completa_verificada', plan_sha256=sha(OUT / 'PLAN.json'),
                    fuente_sha256=sourcehash, filas=len(data), consulta=query,
                    etiquetas_leidas=False, fits=0, api=False, creditos=0,
                    correccion_ccajas_verificada=audit,
                    artefactos_sha256={p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
                    limitaciones='PSI y cambios de distribución no demuestran error ni ganancia; meses ya expuestos. Ninguna corrección nueva aplicada.')
    save(OUT / 'manifest.json', manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
