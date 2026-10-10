"""Registra diagnostico143 y unica ablacion144; verifica hashes y metricas."""
import importlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

base = importlib.import_module('116_promedio20_hist189')
DIAG = base.SAL / 'canaritos189_20261010'
ABL = base.SAL / 'ablacion_canaritos181_20261010'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    d = read(DIAG / 'RESULTADO_LOCAL.json'); a = read(ABL / 'RESULTADO_LOCAL.json')
    assert d['bloque_debil'] == a['bloque_retirado'] and d['control']['ganancia_total'] == a['control']['ganancia_total'] == 275385000
    for folder, r in [(DIAG, d), (ABL, a)]:
        plan = read(folder / 'PLAN.json')
        for p, h in plan['fuentes_sha256'].items():
            assert base.sha(base.ROOT / p) == h
        for f, h in plan['codigo_sha256'].items():
            assert base.sha(base.TP / f) == h
        for p, h in r['modelos_sha256'].items():
            modelpath = folder / 'modelos_mayo' / p if folder == DIAG else base.ROOT / p
            assert base.sha(modelpath) == h
        p = folder / 'predicciones_mayo.csv'; assert base.sha(p) == r['predicciones_sha256']
        frame = pd.read_csv(p, float_precision='round_trip'); y = frame.clase_ternaria.eq('BAJA+2').to_numpy()
        candidate = 'score_canaritos' if folder == DIAG else 'score_181'
        assert base.metric(y, frame.score_control.to_numpy())['ganancia_total'] == 275385000
        assert base.metric(y, frame[candidate].to_numpy())['ganancia_total'] == r['con_canaritos' if folder == DIAG else 'candidato']['ganancia_total']
        assert sum(row['delta_total'] for row in r['partes']) == r['delta_total']
        base.save(folder / 'VERIFICACION_FINAL.json', dict(estado='verificado', codigo_verificacion_sha256=base.sha(Path(__file__)),
            archivos_sha256={p.name: base.sha(p) for p in folder.iterdir() if p.is_file()}, modelos_sha256=r['modelos_sha256']))
    imp = pd.read_csv(DIAG / 'importancias_semilla.csv')
    rank = pd.read_csv(DIAG / 'ranking_diagnostico.csv')
    gain_noise = imp.loc[imp.canarito].groupby('seed').gain_pct.sum()
    count_weak = int((~rank.canarito & rank.semillas_debajo_ruido.ge(4)).sum())
    perm = pd.DataFrame([{k: v for k, v in row.items() if k not in ['campos', 'metricas']} for row in d['permutaciones']])
    perm.to_csv(DIAG / 'resumen_permutaciones.csv', index=False)
    fmt = lambda value: ('$' + f'{value:,.0f}').replace(',', '.')
    report = '# Canaritos: diagnóstico y comparación de un bloque\n\n'
    decision = 'La ablación mejora las dos métricas locales, pero requiere comprobación temporal antes de promoverla.' if a['evidencia_local_positiva'] else 'No promover el bloque retirado: no mejora simultáneamente la lista promedio5 y la media de cinco listas individuales. Mantener LightGBM189 + TabPFN202.'
    report += decision + '\n\n'
    report += '| Variante | Ganancia total mayo, lista promedio5 | Diferencia vs189 | Media diferencia en listas individuales |\n|---|---:|---:|---:|\n'
    report += f"| Control189 | {fmt(a['control']['ganancia_total'])} | {fmt(0)} | {fmt(0)} |\n"
    report += f"| 189 +19canaritos (diagnóstico) | {fmt(d['con_canaritos']['ganancia_total'])} | {fmt(d['delta_total'])} | {fmt(d['media_delta_listas'])} |\n"
    report += f"| 181, sin el bloque de8, sin canaritos | {fmt(a['candidato']['ganancia_total'])} | {fmt(a['delta_total'])} | {fmt(a['media_delta_listas'])} |\n\n"
    report += f"Ablación181: mejoran {a['semillas_mejoran']}/5 semillas y {a['partes_mejoran']}/4 partes. Contactos {a['control']['contactos']}→{a['candidato']['contactos']}; BAJA+2 {a['control']['tp']}→{a['candidato']['tp']}. Agregados {a['cambios_lista']['agregados']}, retirados {a['cambios_lista']['retirados']}.\n\n"
    report += '## Diagnóstico\n\n'
    report += f"Los19canaritos uniformes recibieron entre{gain_noise.min():.2f}% y{gain_noise.max():.2f}% del gain de entrenamiento (media{gain_noise.mean():.2f}%). Es importancia de splits, no dinero ni información real sobre churn. {count_weak}/189 variables quedaron por debajo de la mediana de ruido en al menos cuatro semillas. No retirar esas{count_weak} variables: ruido continuo tiene más oportunidades de corte que muchos conteos/indicadores y existe redundancia entre variables.\n\n"
    report += 'La regla fijada antes de observar ganancias eligió solamente las ocho primeras variables por mediana de gain y nombre, con al menos4/5 semillas debajo de ruido:\n\n'
    report += '\n'.join('- `' + c + '`' for c in d['bloque_debil']) + '\n\n'
    report += 'El bloque se congeló a partir del entrenamiento abril antes de las permutaciones de mayo; no se probaron otros bloques según su ganancia.\n\n'
    for block in ['debil', 'canaritos']:
        rows = perm.loc[perm.bloque.eq(block)]
        report += f"Permutación conjunta bloque{block}, tres órdenes fijos en mayo: pérdida AP combinado media{rows.perdida_ap_combinado.mean():.8f}; pérdida AP BAJA+2 media{rows.perdida_ap_baja2.mean():.8f}; pérdida ganancia media{fmt(rows.perdida_ganancia_total.mean())}. Pérdida positiva significa que permutar empeora; son variaciones exploratorias, no significancia.\n\n"
    report += ('No elegir el orden aleatorio que produjo mayor ganancia ni promover probabilidades permutadas: los canaritos no contienen señal por construcción y las variaciones ilustran sensibilidad al azar. '
               'La caída al agregar ruido tampoco se atribuye únicamente a sobreajuste: agregar columnas cambia la competencia de variables con feature_fraction fijo.\n\n')
    report += '## Comparación181 sin ruido\n\n| Semilla | Diferencia total |\n|---|---:|\n'
    for row in a['pareados']:
        report += f"| {row['seed']} | {fmt(row['delta_total'])} |\n"
    report += ('\nDos planes separados congelados:143 para el diagnóstico,144 para una única ablación. Abril→mayo, target LightGBM combinado, TabPFN202 BAJA+2 guardado,273árboles y mismos parámetros/semillas, pesos50/50, corte>2,75%. '
               'No se aplicó la corrección ccajas ni otras limpiezas para aislar la retirada de columnas. Control189, filas, modelos, código, matrices, probabilidades y ganancias verificados. '
               'Cinco fits diagnósticos y cinco fits181; cero API/créditos/submits y ningún entrenamiento agosto. Modelos originales y entrega43 preservados.\n\n'
               'Mayo y semillas ya reutilizados; no test independiente. Los valores son ganancia total mayo, no Public gain. '
               'No podar automáticamente ni convertir estos resultados en garantía pública.\n')
    (DIAG / 'INFORME.md').write_text(report, encoding='utf-8')
    record = dict(estado='diagnostico_y_ablacion_completos', fecha='2026-10-10',
        bloque=d['bloque_debil'], canaritos=19, gain_ruido_media_pct=float(gain_noise.mean()),
        variables_debajo_ruido_4de5=count_weak, delta_ruido_total=d['delta_total'],
        delta_ablacion_total=a['delta_total'], media_delta_ablacion_listas=a['media_delta_listas'],
        semillas_mejoran=a['semillas_mejoran'], partes_mejoran=a['partes_mejoran'],
        evidencia_local_positiva=a['evidencia_local_positiva'], nuevos_fits=10, creditos=0, api=False,
        final_agosto=False, decision=decision, informe=str((DIAG / 'INFORME.md').relative_to(base.ROOT)),
        informe_sha256=base.sha(DIAG / 'INFORME.md'))
    base.save(DIAG / 'CONCLUSION.json', record)
    configpath = base.TP / 'config_validacion_lightgbm.json'; config = read(configpath)
    config['canaritos189_diagnostico_ablacion'] = record; base.save(configpath, config)
    nextpath = base.TP / 'NEXT_STEPS_IDEAS.md'; old = nextpath.read_text(encoding='utf-8-sig')
    prefix = '# Canaritos y única ablación completados — 2026-10-10\n\n' + decision + '\n\n'
    prefix += f"Diagnóstico19ruidos: delta total{fmt(d['delta_total'])}. Ablación189→181: delta total{fmt(a['delta_total'])}, media listas{fmt(a['media_delta_listas'])};{a['semillas_mejoran']}/5 semillas mejoran. Diez fits locales, ceroAPI/créditos/submits. [Informe](salidas/canaritos189_20261010/INFORME.md).\n\n"
    if not old.startswith(prefix):
        nextpath.write_text(prefix + old, encoding='utf-8')
        with (base.ROOT / 'BITACORA_DMEYF.md').open('a', encoding='utf-8') as f:
            f.write('\n' + report)
        with (base.TP / 'PLAN_EXPERIMENTOS_20261010.md').open('a', encoding='utf-8') as f:
            f.write('\n## Paso4 completado: canaritos y una ablación — 2026-10-10\n\n' + prefix.split('\n\n', 1)[1])
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
