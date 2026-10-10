"""Cierra la auditoria con trazabilidad de modelos guardados; sin fits/targets."""
import hashlib
import json
from pathlib import Path
import lightgbm as lgb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TP = ROOT / 'tp_primera_entrega'
OUT = TP / 'salidas/auditoria_calidad_drift_20261010_v3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    for name, h in manifest['artefactos_sha256'].items():
        assert sha(OUT / name) == h
    local = TP / 'salidas/features_local_20261006_140702'
    lm = json.loads((local / 'manifest.json').read_text(encoding='utf-8'))
    seeds = [541440, 408476, 741961, 248865, 717444]
    focus = ['ccajas_depositos', 'Visa_Finiciomora', 'Master_Finiciomora',
             'cprestamos_personales', 'mprestamos_personales']
    modelrows = []
    for seed in seeds:
        p = local / 'historia_1_mes' / f'seed{seed}.txt'
        key = str(p.relative_to(local))
        assert sha(p) == lm['modelos_sha256'][key]
        model = lgb.Booster(model_file=str(p))
        assert len(model.feature_name()) == 189 and model.num_trees() == 273
        gain = model.feature_importance('gain'); split = model.feature_importance('split')
        for field in focus:
            i = model.feature_name().index(field)
            modelrows.append(dict(seed=seed, campo=field, splits=int(split[i]),
                                  gain_porcentaje=float(100 * gain[i] / gain.sum()), modelo_sha256=sha(p)))
    pd.DataFrame(modelrows).to_csv(OUT / 'uso_modelos189_guardados.csv', index=False)
    findings = [
        {'campo': 'ccajas_depositos', 'mes': '202105',
         'anomalia': '163.768/163.768 filas cero; abril1,332% y agosto3,540% positivos.',
         'evidencia': 'CSV agregado, aviso de catedra registrado en config y auditoria88; 2.164 clientes comunes con abril pasan de positivo a cero.',
         'regla': 'Regla ya existente: convertir a NA solamente mayo antes de historicos. Probar aisladamente sobre189; no presentarla como descubrimiento nuevo.',
         'estado': 'correccion_conocida_verificada_no_aplicada_al_control189'},
        {'campo': 'Visa_Finiciomora', 'mes': '202105 / 202108',
         'anomalia': '3.222 / 3.249 ceros frente a cero en abril; nulos bajan99,126% a97,347% /97,472%.',
         'evidencia': 'En clientes comunes abril->mayo:3.162 nulos pasan a cero y48 no ceros pasan a cero. Mayo3.209 ceros en cuentas abiertas.',
         'regla': 'No convertir automaticamente ceros a NA. El diccionario no documenta codigo cero; pedir o localizar evidencia adicional antes de una correccion.',
         'estado': 'cambio_confirmado_semantica_no_confirmada'},
        {'campo': 'Master_Finiciomora', 'mes': '202103–202108',
         'anomalia': 'Mayormente nulo; solamente1 cero en junio. No replica el salto de Visa.',
         'evidencia': 'Diccionario dice dias desde inicio de mora para Master y dias para inicio para Visa; diferencias mensuales no prueban error.',
         'regla': 'Preservar faltantes; no aplicar a Master una regla de Visa ni rellenar por cero.',
         'estado': 'sin_regla_nueva_sustentada'},
        {'campo': 'cprestamos_personales / mprestamos_personales', 'mes': '202103–202108',
         'anomalia': 'Prestamos positivos bajan22,010% a20,685%; monto q99 sube521.516 a586.500.',
         'evidencia': 'Notebook arboles/z0607 celdas38/60 elimina ambos por drift; cuaderno z701 analiza distribucion y target. No demuestra error de captura.',
         'regla': 'No limpiar ni eliminar automaticamente. Sin nueva ablacion: sin_prestamos ya se probo en script63 y carpeta features_local.',
         'estado': 'drift_exploratorio_ablacion_ya_existente'},
        {'campo': 'Visa_Fvencimiento / Master_Fvencimiento', 'mes': 'varios / 202108',
         'anomalia': 'Extremos de aproximadamente-2,9millones de dias, incompatibles con vencimiento de plastico.',
         'evidencia': 'Diccionario indica dias; baseline.preparar ya reemplaza valores<-36.500 por NA.',
         'regla': 'Mantener regla conservadora existente, no nueva candidata. No borrar todos los negativos.',
         'estado': 'tratamiento_existente_no_codigo_especial_confirmado'},
        {'campo': 'conteos auditados y status de tarjetas', 'mes': '202103–202108',
         'anomalia': 'Sin conteos negativos/fraccionarios ni status fuera{0,6,7,9}; sin infinitos en21campos auditados.',
         'evidencia': 'Tabla distribuciones_mensuales.csv; alcance limitado a21predictores, no todo el dataset.',
         'regla': 'Sin correccion nueva.', 'estado': 'dominios_verificados'}]
    pd.DataFrame(findings).to_csv(OUT / 'campo_mes_evidencia_regla.csv', index=False)
    text = '# Auditoría de calidad y drift — 10 de octubre de 2026\n\n'
    text += ('Auditoría inicial completa: 983.061 filas, seis meses y21predictores. Sin etiquetas, entrenamientos, API ni créditos. '
             'La primera prueba recomendada es aislar la corrección conocida de `ccajas_depositos` de mayo sobre LightGBM189. '
             'No hay sustento suficiente para corregir automáticamente los ceros de mora.\n\n')
    text += '| Campo | Mes | Hallazgo | Evidencia y regla |\n|---|---|---|---|\n'
    for f in findings:
        text += f"| {f['campo']} | {f['mes']} | {f['anomalia']} | {f['evidencia']} {f['regla']} |\n"
    text += ('\nLa base189 conserva la preparación histórica de scripts63/66 (`baseline.preparar`), sin la corrección mayo de caja. '
             'Los ensayos de cátedra89/99/101 y segmentación108 sí usan `calidad_datos`; eso no equivale a una comparación aislada de esa corrección en189. '
             'La entrega43 y las demás fuentes históricas permanecen intactas.\n\n'
             'PSI: abril como referencia fija, deciles finitos con extremos infinitos y bin faltante separado, suavizado1e-6. '
             'Campos discretos o con muchos ceros tienen menos bins. PSI alto no demuestra error; PSI bajo no garantiza estabilidad del vínculo con churn. '
             'No se usaron etiquetas para investigar ese vínculo. El uso de splits/gain de modelos guardados indica participación predictiva, no dinero ni causalidad.\n\n'
             'Próxima comparación congelada: abril→mayo, mismos cinco modelos189 guardados, TabPFN202 guardado, pesos50/50 y corte>2,75%; '
             'único cambio `ccajas_depositos=NA` en mayo. Abril no cambia y ccajas no pertenece a las fuentes históricas, por lo que se pueden reutilizar los modelos abril sin reentrenar. '
             'Reproducir primero el control$275.385.000 y reportar lista promedio5, cinco listas individuales y cuatro partes. '
             'Es una sensibilidad de inferencia local; no mide el efecto de reentrenar abril+mayo corregidos para agosto. '
             'No ajustar cortes ni tocar TabPFN ni borrar mora/préstamos en esa comparación.\n\n'
             'Intentos previos conservados: el primero detuvo por cuatro nombres de columnas incorrectos antes de leer filas; '
             'el segundo detuvo en una verificación de dtype entero→float al introducir NA. La versión3 verificó igualdad de valores fuera de mayo y regla idempotente. '
             'No se alteró la hipótesis según ganancias: ninguno consultó etiquetas.\n\n'
             'Artefactos: campo_mes_evidencia_regla.csv, distribuciones_mensuales.csv, mora_por_estado.csv, clientes_comunes_abril.csv, '
             'psi_abril_fijo.csv, uso_modelos189_guardados.csv, PLAN.json y manifest.json.\n')
    (OUT / 'INFORME.md').write_text(text, encoding='utf-8')
    conclusion = dict(estado='auditoria_inicial_completa_verificada', informe=str((OUT / 'INFORME.md').relative_to(ROOT)),
                      informe_sha256=sha(OUT / 'INFORME.md'), codigo_cierre_sha256=sha(Path(__file__)),
                      fits=0, creditos=0, etiquetas_leidas=False, hallazgos=findings,
                      proxima_prueba='sensibilidad_ccajas_mayo_en189_aislada_con_modelos_guardados',
                      final_agosto=False)
    save(OUT / 'CONCLUSION.json', conclusion)
    configpath = TP / 'config_validacion_lightgbm.json'
    config = json.loads(configpath.read_text(encoding='utf-8-sig'))
    config['auditoria_calidad_drift_20261010'] = conclusion
    save(configpath, config)
    nextpath = TP / 'NEXT_STEPS_IDEAS.md'
    old = nextpath.read_text(encoding='utf-8-sig')
    prefix = '# Auditoría calidad/drift completa — 2026-10-10\n\n'
    prefix += ('21predictores y seis meses, sin etiquetas/fits/API. Corrección conocida ccajas de mayo no está en control189; '
               'mora Visa cambia nulo→cero en mayo/agosto pero sin semántica confirmada, no corregir automáticamente. '
               'Próxima prueba: sensibilidad ccajas=NA en mayo con cinco modelos189 y TabPFN guardados, sin cambiar mezcla/corte. '
               'Sin entrenamiento final ni entrega nueva. [Informe](salidas/auditoria_calidad_drift_20261010_v3/INFORME.md).\n\n')
    if not old.startswith(prefix):
        nextpath.write_text(prefix + old, encoding='utf-8')
        with (ROOT / 'BITACORA_DMEYF.md').open('a', encoding='utf-8') as f:
            f.write('\n' + text)
        with (TP / 'PLAN_EXPERIMENTOS_20261010.md').open('a', encoding='utf-8') as f:
            f.write('\n## Paso3: auditoría inicial completa — 2026-10-10\n\n' + prefix.split('\n\n', 1)[1])
    print(json.dumps({'estado': conclusion['estado'], 'informe': conclusion['informe'],
                      'uso_modelos': modelrows}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
