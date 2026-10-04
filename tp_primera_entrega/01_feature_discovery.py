# %% [markdown]
# # TP - Primera entrega - Feature discovery
#
# Objetivo: predecir **BAJA+2** a partir de `data/competencia_01.csv`.
# Foto a predecir confirmada: agosto de 2021 (202108).
# Fecha de entrega indicada: **domingo 11 de octubre de 2026**.
#
# Este archivo reúne la auditoría, hipótesis y definiciones. No modifica el
# dataset. El experimento predictivo usa marzo como train y mayo como validación.

# %% [markdown]
# ## 1. Configuración y acceso al dataset

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

# %%
import duckdb

con = duckdb.connect()
con.execute("SET threads=2")
con.execute("SET memory_limit='2GB'")
con.read_csv(str(DATASET)).create_view("datos")
esquema = con.sql("DESCRIBE datos").df()
print(esquema.to_string(index=False))

# %% [markdown]
# ## 2. Cobertura y calidad de las etiquetas
#
# Auditoría estructural de todo el archivo; no seleccionar variables o modelos con estos resultados. No convertir targets faltantes en negativos. `BAJA+1` es negativo para el objetivo binario BAJA+2 solamente en las filas que forman parte de una muestra completamente etiquetada.

# %%
cobertura = con.sql("""
SELECT foto_mes, count(*) AS filas,
       count(*) FILTER (WHERE clase_ternaria IS NULL) AS sin_target
FROM datos GROUP BY 1 ORDER BY 1
""").df()
print(cobertura.to_string(index=False))

duplicados = con.sql("""
SELECT count(*) FROM (
    SELECT numero_de_cliente, foto_mes FROM datos
    GROUP BY 1, 2 HAVING count(*) > 1
)
""").fetchone()[0]
assert duplicados == 0, f"Hay {duplicados} claves cliente-mes duplicadas"
clases = {r[0] for r in con.sql(
    "SELECT DISTINCT clase_ternaria FROM datos WHERE clase_ternaria IS NOT NULL"
).fetchall()}
assert clases <= {"BAJA+1", "BAJA+2", "CONTINUA"}, clases

# %% [markdown]
# ## 3. Definir el protocolo antes de explorar contra el target
#
# Protocolo en config.json: train marzo, validación mayo, test junio reservado.
# Julio tiene etiquetas parciales y agosto no tiene target: no son evaluaciones completas.
#
# - Verificar cuándo está disponible cada etiqueta: BAJA+2 requiere observar meses futuros. Para simular una predicción real, las etiquetas de entrenamiento deben estar disponibles en la fecha de predicción.
# - Evitar una división aleatoria de filas como evaluación principal: el mismo cliente aparece en varios meses.
# - Mayo ya fue utilizado en experimentos previos según la bitácora; no presentarlo como test independiente sin reconocer ese uso.
# - Reservar el test para una evaluación final; seleccionar features, parámetros y cantidad de clientes a contactar usando train/validación.
# - La entrega usa agosto (202108), con target desconocido. No usar sus
#   etiquetas para selección; las features usan agosto y su pasado disponible.

# %% [markdown]
# ## 4. Inventario e hipótesis de variables
#
# Revisar el diccionario y `monday/z402_Feature_Engineering_en_SQL_TH.ipynb` antes de implementar. Los reportes de `monday/reporte_clase04/` son antecedentes descriptivos.
#
# | Familia | Hipótesis candidata | Definición a precisar | Estado |
# |---|---|---|---|
# | Actividad | Caída de transacciones anticipa baja | `ctrx_quarter`: nivel, lag y delta; confirmar ventana trimestral | Pendiente |
# | Haberes | Interrupción de acreditaciones anticipa baja | `mpayroll`: presencia y cambios; distinguir cero y faltante | Pendiente |
# | Saldos | Reducción de vinculación financiera | Saldos por producto, moneda y evolución | Pendiente |
# | Productos | Menor uso o tenencia anticipa baja | Indicadores comparables y diversidad de uso | Pendiente |
# | Historia | Cambios respecto del comportamiento propio | Lags, deltas, medias y tendencias con pasado disponible | Pendiente |
#
# Para cada variable registrar fórmula, columnas fuente, unidad, ventana, tratamiento de nulos/ceros, disponibilidad temporal y resultado frente al baseline. Son hipótesis, no mejoras demostradas.

# %% [markdown]
# ## 5. Features implementadas en features.py
#
# ACTIVIDAD (2): actividad_por_producto y cantidad_canales_activos.
# TARJETAS (3): suma Visa + Master de saldo, consumo y límite, todos en pesos.
# UTILIZACIÓN (4): saldo/límite y consumo/límite para cada tarjeta.
# Un total con algún componente desconocido queda NaN. Un ratio con denominador
# <= 0 queda NaN. Un conteo de canales incompleto queda NaN. Ceros conocidos se
# conservan. Estas reglas no aprenden parámetros de mayo ni del test.
#
# La comparación se ejecuta con 03_comparar_intrames.py: baseline y tres bloques
# separados, mismo modelo, semilla y umbral. Solo combina bloques si al menos
# dos mejoran individualmente; esa combinación sigue siendo exploratoria.
#
# HISTÓRICAS: experimento separado en 04_comparar_historicas.py.
# agregar_historicas(datos) calcula lag de un mes calendario y delta actual-lag
# para ctrx_quarter, mpayroll, mcuentas_saldo y cproductos, más un indicador
# de presencia en el mes anterior. Requiere incluir la historia auxiliar antes
# de separar las filas objetivo; no confundir ausencia de fila con valor cero.
# No incluye target ni información futura en las features.
# Marzo no tiene febrero: no podemos aprender estas features con train marzo.
# El experimento retrospectivo acordado entrena abril usando marzo como historia
# y valida mayo usando abril como historia. El target de abril se conoce en junio:
# no es una simulación de disponibilidad en tiempo real. No cambia las particiones
# principales ni evalúa junio. Resultados en README.md.
#
# Usar solamente el mes observado y su pasado. Un lag debe respetar el mes calendario; un registro previo puede estar separado por varios meses. Marzo no tiene historia anterior en este archivo. No usar target, presencia futura, pertenencia a grupos construidos con bajas futuras ni estadísticas calculadas con meses posteriores.
#
# Las transformaciones aprendidas (imputación, codificación, selección) se ajustarán únicamente con train. Las features se compararán en las mismas filas, meses y semillas, incluyendo un baseline con variables originales.

# %% [markdown]
# ## 6. Decisiones y resultados
#
# Ver README.md y salidas/intrames_*/manifest.json para resultados, fórmulas
# en features.py, parámetros y hashes del código. Las features son candidatas:
# no reemplazan automáticamente el baseline ni modifican competencia_01.csv.
