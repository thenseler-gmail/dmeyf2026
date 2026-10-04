# %% [markdown]
# # TP - Primera entrega - Modelado y evaluación
#
# Objetivo binario: **BAJA+2**. Ejecutar este archivo entrena los baselines
# LightGBM y logística múltiple con marzo y evalúa mayo. No evalúa junio.

# %% [markdown]
# ## 1. Configuración compartida

# %%
from pathlib import Path
import json

# Localiza el proyecto desde este archivo o desde la consola interactiva.
BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
ROOT = next((p for p in [BASE, *BASE.parents]
             if (p / "tp_primera_entrega" / "config.json").is_file()), None)
if ROOT is None:
    raise FileNotFoundError("No se encuentra la carpeta tp_primera_entrega en el repositorio.")
CONFIG = json.loads((ROOT / "tp_primera_entrega/config.json").read_text(encoding="utf-8"))
DATASET = ROOT / CONFIG["dataset"]
assert DATASET.is_file(), f"No se encontró {DATASET}"

# %% [markdown]
# ### Ganancia confirmada con la matriz de la cátedra
# G = 1.072.500 * verdaderos positivos - 27.500 * falsos positivos.
# Solo predecir BAJA+2 produce una ganancia o un costo; las otras predicciones
# aportan cero. El premio de 1.072.500 ya es neto: no restar otro costo.
# Con probabilidades calibradas y sin restricciones adicionales, seleccionar
# cuando p(BAJA+2) > 27.500 / (1.072.500 + 27.500) = 0,025.
# Ese umbral es una referencia teórica; cualquier ajuste se hace en validación.

# %%
def calcular_ganancia(y_real, y_predicha):
    """Suma la matriz oficial sobre etiquetas ternarias, en el mismo orden."""
    reales, predichas = list(y_real), list(y_predicha)
    if len(reales) != len(predichas):
        raise ValueError("Reales y predichas deben tener la misma longitud.")
    clases = {"BAJA+2", "BAJA+1", "CONTINUA"}
    if any(x not in clases for x in reales + predichas):
        raise ValueError("Se requieren etiquetas ternarias válidas, sin faltantes.")
    matriz = CONFIG["ganancia"]
    return sum(
        matriz["acierto"] if real == "BAJA+2" else matriz["error"]
        for real, predicha in zip(reales, predichas)
        if predicha == "BAJA+2"
    )


UMBRAL_TEORICO = -CONFIG["ganancia"]["error"] / (
    CONFIG["ganancia"]["acierto"] - CONFIG["ganancia"]["error"]
)

# %% [markdown]
# ## 2. Protocolo temporal
#
# Acuerdo: entrenar marzo y validar mayo; congelar variables, parámetros y
# regla de selección; reentrenar marzo + abril y evaluar junio una vez.
# La ganancia oficial será la métrica principal. No ajustar decisiones con junio.
# Límite: el target de mayo se conoce en julio. Seleccionar parámetros con mayo
# y evaluar junio es retrospectivo; no simula toda la selección en tiempo real.
# Junio ya fue explorado en el EDA y no constituye un test completamente inédito.

# %%
split = CONFIG["split"]
estado_entrega = "provisional" if CONFIG['entrega']['mes_asumido'] else "confirmado"
print(f"Mes de entrega {estado_entrega}: {split['prediccion_mes']}.")
if not split["confirmado"]:
    print("Pendiente: definir y confirmar train, validación y test.")
else:
    grupos = [set(split[k]) for k in ("train_meses", "validacion_meses", "test_meses")]
    assert all(grupos), "Las tres particiones deben tener meses."
    train, validacion, test = grupos
    assert not (train & validacion or train & test or validacion & test)
    assert max(train) < min(validacion) and max(validacion) < min(test)
    reentrenamiento = set(split["reentrenamiento_meses"])
    assert train <= reentrenamiento
    assert not (reentrenamiento & validacion or reentrenamiento & test)
    assert max(reentrenamiento) < min(test)
    print(f"Train: {sorted(train)}; validación: {sorted(validacion)}.")
    print(f"Reentrenamiento: {sorted(reentrenamiento)}; test: {sorted(test)}.")
    print(split["tipo_evaluacion"])

# %% [markdown]
# ## 3. Construir X e y
#
# - Excluir filas sin etiqueta y meses parcialmente etiquetados del entrenamiento/evaluación supervisados.
# - `y = (clase_ternaria == "BAJA+2")` solo después de validar las etiquetas.
# - Conservar `numero_de_cliente` y `foto_mes` para particionar y auditar; no incorporarlos por defecto como predictores.
# - Excluir `clase_ternaria`, cualquier derivado del target y cualquier variable que use el futuro.
# - Usar las features aprobadas en el archivo 01; guardar lista y versión.

# %% [markdown]
# ## 4. Baseline ejecutable
#
# Primer experimento acordado: LightGBM con variables originales, semilla fija y presupuesto acotado. Regresión logística como referencia y TabPFN como segunda opción experimental. Definir el manejo de faltantes dentro del pipeline y ajustarlo con train. No reutilizar el muestreo de los scripts de clustering como evaluación predictiva: esos scripts responden a otro objetivo.
#
# Registrar tiempo de ejecución, configuración, filas, meses, columnas, métricas y predicciones de validación.

# %%
if __name__ == '__main__':
    # El módulo auxiliar concentra carga, limpieza y modelos para reutilizarlos.
    import sys
    carpeta_trabajo = str(ROOT / 'tp_primera_entrega')
    if carpeta_trabajo not in sys.path:
        sys.path.insert(0, carpeta_trabajo)
    from baseline import ejecutar_baseline
    carpeta_resultados = ejecutar_baseline(ROOT, CONFIG)

# %% [markdown]
# ## 5. Comparar features y modelos - pendiente
#
# Comparación intrames disponible en 03_comparar_intrames.py.
# Comparación con presupuestos iguales de Optuna (originales/intrames/históricas)
# en 06_comparacion_optuna_features.py, train abril y validación mayo.
# features.py contiene los generadores; 04_comparar_historicas.py evalúa historia
# en un experimento retrospectivo separado con train abril y validación mayo.
# Ejecutar por separado para conservar el baseline como referencia.
#
# Optuna será la herramienta de optimización de hiperparámetros.
# En el protocolo principal, train marzo y validación mayo.
# 05_optuna_historicas_rf.py ejecuta un experimento SEPARADO abril -> mayo
# con 30 trials por variante para comparar originales e históricas y un RF fijo.
# Definir antes de la búsqueda la regla de selección de clientes, el espacio
# de parámetros y el presupuesto (trials/tiempo). Junio queda fuera de Optuna.
# Este archivo ejecuta solo el baseline. Optuna se lanza desde el archivo 05.
#
# Comparar originales, originales + intrames y originales + historia con las mismas particiones y semillas. Luego evaluar modelos adicionales y una búsqueda acotada de hiperparámetros. Discutir el presupuesto antes de lanzar corridas largas.
#
# Seleccionar la cantidad de contactos o umbral sobre validación según la ganancia oficial. Mantener la distribución real en validación y test. Registrar variabilidad entre semillas cuando corresponda.
#
# | Experimento | Features | Modelo y parámetros | Meses | Semilla | Ganancia validación | Contactos | Tiempo | Decisión |
# |---|---|---|---|---|---|---|---|---|
# | Pendiente | Originales | Baseline por definir | Pendiente | 214363 | - | - | - | - |

# %% [markdown]
# ## 6. Evaluación final - ejecutada el 2026-10-03
#
# 07_evaluacion_junio.py congeló los mejores parámetros seleccionados en mayo,
# reentrenó marzo + abril y evaluó junio con umbral 0,025, sin nuevo tuning.
# Originales: ganancia 333.410.000; históricas: 332.832.500.
# La ventaja histórica de mayo no se sostuvo en junio (diferencia -577.500).
# Artefactos: salidas/test_junio_20261003_114546_998605/.
# Junio queda expuesto: no reutilizarlo como test independiente para TabPFN.
#
# Congelar configuración y regla de selección antes de abrir el test. Medir ganancia con esa regla fija y métricas complementarias; no elegir retrospectivamente el mejor corte del test como resultado principal. Documentar toda exposición previa al período elegido.

# %% [markdown]
# ## 7. Reentrenamiento y entrega - pendiente
#
# Mes de entrega confirmado por Tomás: agosto de 2021 (foto_mes = 202108).
# El universo es la foto de agosto, disponible en competencia_01.csv.
# BAJA+2 de agosto significa presente en septiembre y ausente en octubre.
# Septiembre y octubre sirven para observar la etiqueta real, no para generar
# features. No necesitamos sus datos para hacer la predicción de agosto.
# Las features históricas de agosto pueden utilizar julio y meses anteriores.
# La ausencia del target de agosto es esperada; no se completa como CONTINUA.
#
# Formato propuesto por Tomás: CSV de dos columnas, ID y etiqueta ternaria.
# Encabezados provisionales: id,clase_ternaria (confirmar con la consigna).
# Etiquetas exactas del dataset: CONTINUA, BAJA+1, BAJA+2; sin espacios.
# La matriz oficial no distingue económicamente predecir BAJA+1 de CONTINUA.
# Para optimizar esta ganancia basta modelar BAJA+2 frente al resto.
# Propuesta de salida binaria con etiquetas ternarias: BAJA+2 para seleccionados
# y CONTINUA para el resto. Esta regla no distingue BAJA+1 de CONTINUA:
# solo codifica la decisión bajo esta matriz.
# validar_entrega.py verifica formato y clientes del mes indicado; no mide
# calidad predictiva ni confirma por sí mismo el contrato de la competencia.
#
# Confirmar plantilla oficial, nombres de columnas y regla de ranking/contactos. Reentrenar solo con etiquetas disponibles a la fecha de predicción. Verificar unicidad de clientes, cantidad de filas y valores válidos antes de exportar a `salidas/`.
#
# No se genera ni envía una entrega desde esta estructura inicial.
