# Bitácora de trabajo — DMEyF 2026

Esta bitácora documenta la preparación del proyecto de Tomás para la comisión de los lunes. El objetivo es poder reproducir el ambiente en Windows y posteriormente en macOS.

## Objetivo

Construir de forma reproducible la variable `clase_ternaria` del archivo `competencia_01_crudo.csv`, siguiendo primero la notebook oficial de la comisión Monday:

```text
monday/z101_target_sql.ipynb
```

La solución usa Python, Jupyter y SQL mediante DuckDB.

## Estado actual

- Repositorio oficial clonado.
- Fork personal configurado como remoto `origin`.
- Repositorio oficial configurado como remoto `upstream`.
- Rama de trabajo creada: `feature/clase-ternaria`.
- Notebook oficial preservada sin modificaciones.
- Copia de trabajo creada: `monday/tomas_target_sql.ipynb`.
- Ambiente virtual creado en `.venv/`.
- Dependencias instaladas y comprobadas.
- Rutas de Google Colab reemplazadas en la copia por rutas locales portátiles.
- Dataset oficial descargado en `data/competencia_01_crudo.csv`.
- Lógica SQL de `clase_ternaria` ejecutada y validada mediante conteo total y `PIVOT`.

## 1. Clonar el repositorio oficial

Desde la carpeta que contendrá el proyecto:

```bash
git clone https://github.com/dmecoyfin/dmeyf2026.git
cd dmeyf2026
```

Remoto oficial verificado:

```text
https://github.com/dmecoyfin/dmeyf2026.git
```

## 2. Crear una rama de trabajo

```bash
git switch -c feature/clase-ternaria
```

La rama permite conservar `main` igual al material docente.

En el entorno aislado de Codex fue necesario pasar `safe.directory` en algunos comandos de Git porque Codex usa otro usuario de Windows. Esto no debería ser necesario en una terminal normal:

```powershell
git -c safe.directory='C:/ruta/al/repositorio/dmeyf2026' status
```

No se modificó la configuración global de Git.

## 2.1. Configurar el fork personal

Como los alumnos normalmente no tienen permisos para publicar ramas en el repositorio de la cátedra, se creó este fork:

```text
https://github.com/thenseler-gmail/dmeyf2026
```

Los remotos locales quedaron organizados así:

```text
origin   https://github.com/thenseler-gmail/dmeyf2026.git
upstream https://github.com/dmecoyfin/dmeyf2026.git
```

`origin` se usa para publicar el trabajo personal. `upstream` se usa para consultar y traer futuras actualizaciones de la cátedra.

La configuración se realizó con:

```bash
git remote rename origin upstream
git remote add origin https://github.com/thenseler-gmail/dmeyf2026.git
git remote -v
```

Todavía no se realizó ningún `push`.

## 3. Revisar la notebook oficial

Se leyó completa:

```text
monday/z101_target_sql.ipynb
```

La notebook oficial:

- Descarga `competencia_01_crudo.csv`.
- Usa Jupyter, JupySQL y DuckDB.
- Construye una grilla completa de clientes y períodos.
- Marca presencia por mes mediante `mes_0`.
- Usa `lead()` para obtener `mes_1` y `mes_2`.
- Deja como ejercicio reemplazar `null as clase_ternaria` por la lógica del target.
- Incluye el caso especial de clientes que desaparecen y reaparecen.
- Genera una tabla de cardinalidades por `foto_mes` y clase.
- Exporta el resultado a `competencia_01.csv`.

## 4. Verificar Python

En Windows se encontró:

```text
Python 3.14.6 (64 bits)
pip 26.1.2
```

Comandos de comprobación en Windows:

```powershell
py list
py --version
python --version
```

En macOS se usarán normalmente:

```bash
python3 --version
python3 -m pip --version
```

No se debe copiar `.venv` de Windows a macOS: contiene ejecutables específicos del sistema operativo.

## 5. Ignorar archivos locales y pesados

Se añadieron estas reglas a `.gitignore`:

```gitignore
.venv/
data/
!BITACORA_DMEYF.md
```

El repositorio oficial ya ignoraba los archivos `*.csv` y `*.csv.gz`.

## 6. Crear el ambiente virtual

Windows:

```powershell
py -m venv .venv
```

Activación en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Comprobación sin activar el ambiente en Windows:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip --version
```

## 7. Instalar las dependencias de la notebook

Con el ambiente activado:

```bash
python -m pip install jupyterlab notebook duckdb pandas jupysql duckdb-engine requests
```

En macOS, si el ambiente no está activado, usar el ejecutable correspondiente:

```bash
.venv/bin/python -m pip install jupyterlab notebook duckdb pandas jupysql duckdb-engine requests
```

Versiones instaladas inicialmente en Windows:

```text
Python          3.14.6
JupyterLab      4.6.3
Notebook        7.6.2
DuckDB          1.5.5
pandas          3.0.5
JupySQL         0.11.1
duckdb-engine   0.17.0
requests        2.34.2
SQLAlchemy      2.0.52
```

Se verificaron las importaciones principales y la consulta DuckDB `select 1`.

## 8. Crear una copia de trabajo de la notebook

Se preservó el original y se creó:

```text
monday/tomas_target_sql.ipynb
```

Inicialmente se comprobó mediante SHA-256 que ambas notebooks eran idénticas. Todas las adaptaciones posteriores se hicieron solamente en la copia.

## 9. Adaptar las rutas para Windows y macOS

La notebook oficial usaba esta ruta de Google Colab:

```text
/content/drive/MyDrive/DMEyF/2026/notebooks/data/
```

La copia de trabajo ahora:

- Detecta la raíz del repositorio buscando `.git` en el directorio actual o en su padre.
- Usa la carpeta relativa `data/`.
- Crea `data/` cuando se ejecuta la celda de descarga.
- Define una ruta para el archivo crudo y otra para el resultado.
- Convierte las rutas a formato aceptado por SQL mediante `Path.as_posix()`.

Archivos previstos:

```text
dmeyf2026/
├── data/
│   ├── competencia_01_crudo.csv
│   └── competencia_01.csv
└── monday/
    ├── z101_target_sql.ipynb
    └── tomas_target_sql.ipynb
```

La notebook modificada fue validada como JSON y su primera celda Python fue compilada sin errores.

## Próximos pasos

1. Clonar la rama en la Mac, recrear `.venv` y transferir o volver a descargar el dataset.

## 10. Descargar el dataset oficial

Se ejecutó únicamente la celda de descarga de `monday/tomas_target_sql.ipynb`. El archivo quedó en:

```text
data/competencia_01_crudo.csv
```

Validaciones realizadas:

```text
Tamaño: 492769580 bytes (469.94 MiB)
Primera columna: numero_de_cliente
Segunda columna: foto_mes
```

Git confirmó que el archivo está ignorado por la regla `data/`. El CSV no se publicará en el fork y deberá descargarse nuevamente o transferirse por separado al trabajar en la Mac.

## 11. Cargar y validar el CSV con DuckDB

Se reprodujo la carga indicada por la notebook en una conexión DuckDB en memoria:

```sql
create or replace table competencia_01_crudo as
select *
from read_csv_auto('data/competencia_01_crudo.csv');
```

La tabla tiene 154 columnas y 983061 registros. La consulta de cardinalidades mensuales produjo:

| foto_mes | cantidad |
|---:|---:|
| 202103 | 162900 |
| 202104 | 163284 |
| 202105 | 163768 |
| 202106 | 164114 |
| 202107 | 164348 |
| 202108 | 164647 |

La conexión usada para esta comprobación fue temporal; no se creó aún un archivo de base de datos. Estos son los totales mensuales observados directamente en el CSV crudo.

## 12. Incorporar la lógica de `clase_ternaria`

En la copia de la notebook se reemplazó el `NULL` que la cátedra dejó como ejercicio por:

```sql
case
    when mes_1 is null then null
    when mes_1 = 0 then 'BAJA+1'
    when mes_2 is null then null
    when mes_2 = 0 then 'BAJA+2'
    else 'CONTINUA'
end as clase_ternaria
```

Los controles explícitos de valores nulos conservan sin target los períodos para los que no existe suficiente información futura. La ejecución y sus cardinalidades se documentan en la sección siguiente.

## 13. Ejecutar y validar el target

La celda `CREATE OR REPLACE TABLE competencia_01` terminó con estado `SUCCESS` en la notebook.

La primera verificación interna confirmó que la tabla resultante conserva las 983061 filas originales:

```sql
select count(*) from competencia_01;
```

El `PIVOT` por mes y clase produjo:

| foto_mes | BAJA+1 | BAJA+2 | CONTINUA |
|---:|---:|---:|---:|
| 202103 | 1019 | 960 | 160921 |
| 202104 | 964 | 1139 | 161181 |
| 202105 | 1143 | 870 | 161755 |
| 202106 | 874 | 1098 | 162142 |
| 202107 | 1103 | 0 | 0 |
| 202108 | 0 | 0 | 0 |

Los conteos de 202103 a 202106 son los resultados observados al ejecutar nuestra lógica; no fueron publicados como controles oficiales por la cátedra. En 202107 solo se puede identificar `BAJA+1`; el resto queda con target nulo porque falta 202109. En 202108 todas las clases quedan nulas porque no existe información futura.

## 14. Revisar las proporciones de las clases

Se calcularon las proporciones solamente para los meses con horizonte completo:

| foto_mes | clase_ternaria | cantidad | porcentaje |
|---:|---|---:|---:|
| 202103 | BAJA+1 | 1019 | 0.6255% |
| 202103 | BAJA+2 | 960 | 0.5893% |
| 202103 | CONTINUA | 160921 | 98.7851% |
| 202104 | BAJA+1 | 964 | 0.5904% |
| 202104 | BAJA+2 | 1139 | 0.6976% |
| 202104 | CONTINUA | 161181 | 98.7121% |
| 202105 | BAJA+1 | 1143 | 0.6979% |
| 202105 | BAJA+2 | 870 | 0.5312% |
| 202105 | CONTINUA | 161755 | 98.7708% |
| 202106 | BAJA+1 | 874 | 0.5326% |
| 202106 | BAJA+2 | 1098 | 0.6690% |
| 202106 | CONTINUA | 162142 | 98.7984% |

Cada mes suma aproximadamente 100%; las diferencias mínimas se deben al redondeo. La clase accionable `BAJA+2` representa aproximadamente entre 0.53% y 0.70% de cada mes, por lo que el problema tiene un target fuertemente desbalanceado.

## 15. Validación independiente mediante joins calendario

Se volvió a construir la clase por un segundo método, sin utilizar la grilla ni la función `LEAD`. La implementación alternativa vinculó cada fila con el mismo cliente uno y dos meses calendario hacia adelante mediante `LEFT JOIN`.

Luego se compararon ambas clases fila por fila usando `IS DISTINCT FROM`, que contempla correctamente los valores nulos. El resultado fue:

```text
filas_comparadas = 983061
diferencias = 0
```

Esta comprobación no depende de cardinalidades externas: dos implementaciones distintas de la misma definición produjeron exactamente el mismo target para cada cliente-mes.

## 16. Exportar y validar `competencia_01.csv`

La celda `COPY` terminó con estado `SUCCESS` y creó:

```text
data/competencia_01.csv
```

La primera versión de la celda tenía `%%sql` y la consulta en la misma línea, lo que JupySQL interpretó como una magia de celda sin cuerpo. Se ejecutó correctamente colocando `%%sql` solo en la primera línea y `COPY` en las líneas siguientes.

El archivo exportado se volvió a leer directamente desde disco con una conexión DuckDB nueva. La validación produjo:

```text
Tamaño: 581940592 bytes (554.98 MiB)
Filas: 983061
Columnas: 155
Última columna: clase_ternaria
Clases no nulas: BAJA+1, BAJA+2, CONTINUA
Targets nulos: 327892
```

Los targets nulos se ubican únicamente donde falta horizonte suficiente: 163245 casos de 202107 y los 164647 casos de 202108. Git confirmó que el CSV está ignorado por la regla `data/`.

## 17. Registrar dependencias reproducibles

Se creó `requirements.txt` con las dependencias directas y versiones comprobadas:

```text
duckdb==1.5.5
duckdb-engine==0.17.0
ipykernel==7.3.0
jupysql==0.11.1
jupyterlab==4.6.3
notebook==7.6.2
pandas==3.0.5
requests==2.34.2
```

Se registró Python 3.14.6 como la versión utilizada en Windows. No se incluyó el resultado completo de `pip freeze`, para evitar fijar dependencias transitivas o específicas de Windows que podrían impedir la instalación en macOS.

Las comprobaciones `pip check` y `pip install --dry-run -r requirements.txt` finalizaron sin dependencias rotas ni instalaciones pendientes.

## 18. Revisión previa al commit

Se guardó la versión actual de la notebook desde VS Code y se realizó una revisión estructural. Antes del commit se corrigieron:

- La celda de instalación `%%bash`, que no funciona en PowerShell, se reemplazó por instrucciones portátiles basadas en `requirements.txt`.
- Los textos heredados con codificación incorrecta se restauraron desde la notebook oficial mediante los identificadores de celda, sin alterar los outputs ni las celdas adaptadas.
- Los comentarios de la validación independiente se normalizaron a UTF-8.
- La explicación de proporciones se ubicó antes de su consulta.
- La magia de exportación quedó con `%%sql` en una línea y `COPY` en el cuerpo de la celda.
- Se eliminó una celda Markdown vacía.

Validaciones finales:

```text
Notebook nbformat válida: sí
Celdas: 40
Celdas de código ejecutadas: 18
Outputs de error guardados: 0
Caracteres de reemplazo o mojibake: 0
Rutas personales o secretos detectados: 0
```

Los únicos archivos pendientes de versionar son `.gitignore`, `BITACORA_DMEYF.md`, `requirements.txt` y `monday/tomas_target_sql.ipynb`. `.venv/` y `data/` permanecen ignorados.

## 19. Crear el commit local

Se creó el commit principal en la rama `feature/clase-ternaria` con el mensaje:

```text
feat: construir clase ternaria con DuckDB
```

El commit incluye exclusivamente `.gitignore`, `BITACORA_DMEYF.md`, `requirements.txt` y `monday/tomas_target_sql.ipynb`.

## 20. Publicar la rama en el fork

La rama se publicó en el fork personal mediante:

```bash
git push -u origin feature/clase-ternaria
```

El seguimiento quedó configurado así:

```text
feature/clase-ternaria -> origin/feature/clase-ternaria
```

No se abrió un pull request y no se modificó el repositorio oficial de la cátedra.

## Resultados observados del target (no oficiales)

| foto_mes | BAJA+1 | BAJA+2 | CONTINUA | Total |
|---:|---:|---:|---:|---:|
| 202103 | 1019 | 960 | 160921 | 162900 |
| 202104 | 964 | 1139 | 161181 | 163284 |
| 202105 | 1143 | 870 | 161755 | 163768 |
| 202106 | 874 | 1098 | 162142 | 164114 |

Estos conteos provienen de nuestra ejecución y también aparecen en el SQL generado previamente mediante ChatGPT Web. No constituyen una validación independiente ni fueron confirmados como valores oficiales de la cátedra. La corrección debe sostenerse mediante la definición del target y verificaciones internas: conservación de filas, unicidad cliente-mes, clases permitidas, coherencia del horizonte temporal y tratamiento explícito de valores nulos y reapariciones.


## 21. Contexto compartido del TP: churn y Clase 04 — 2026-09-09

Esta sección amplía la bitácora existente como punto de continuidad entre Codex de escritorio y Codex de VS Code. No se creó un CONTEXTO_TP.md separado para evitar duplicar la memoria del proyecto. Las secciones anteriores se conservan como registro histórico: sus estados de Git, dependencias y pendientes no deben asumirse actuales sin verificar.

### Objetivo y forma de trabajo acordada

- Objetivo final declarado por Tomás: predecir churn bancario.
- Etapa actual: tarea de Clase 04, Feature Engineering (FE) intrames e histórico, evaluación con Random Forest y preparación para clustering.
- Tomás quiere trabajar paso a paso, entender las variables y discutir la propuesta antes de implementar un bloque grande o ejecutar experimentos largos.
- Codex de VS Code lleva el notebook, datos y experimentos; Codex de escritorio puede consultar Zulip y otras fuentes cuando el primero no pueda acceder.
- Mantener este archivo actualizado con decisiones, resultados verificados y pendientes. Distinguir propuestas de acuerdos, y relatos previos de resultados comprobados.
- Conservar originales y guardar entregables separados. No publicar mensajes, subir archivos ni hacer push por el solo hecho de actualizar este contexto.

### Consigna verificada en Zulip

Fuente: hilo Lunes: Material + Tareas → Clase 04, leído por Codex de escritorio el 2026-09-09.

Alejandro Bolaños, 4 de septiembre de 2026, pidió crear variables intrames e históricas, tenerlas listas para clustering, ejecutar un Random Forest sobre el dataset ampliado y analizar las variables históricas.

https://uba26.zulip.rebelare.com/#narrow/channel/1062-Lunes.3A-Material-.2B-Tareas/topic/Clase.2004/near/186530

En ese hilo no se encontró un mínimo de variables, formato de entrega ni fecha explícita. El docente indicó que la clase estaba en GitHub; no se verificó aquí el contenido completo del material docente. No confundir esa ausencia en el hilo con ausencia de requisitos en otras fuentes.

Joaquín Sebastian Tschopp, 9 de septiembre de 2026, remarcó la necesidad de revisar minuciosamente cómo se comparan los experimentos y conservar las funciones de FE aunque inicialmente no mejoren. Respondía a una compañera que había probado sumas, ratios, lags, deltas, medias móviles y slopes. Esos ejemplos de la compañera no constituyen una lista obligatoria.

https://uba26.zulip.rebelare.com/#narrow/channel/1062-Lunes.3A-Material-.2B-Tareas/topic/Clase.2004/near/187096

### Archivos encontrados en el proyecto

Existencia verificada el 2026-09-09; no se auditó su implementación en esta actualización:

- `monday/z402_Feature_Engineering_en_SQL.ipynb`
- `monday/z402_Feature_Engineering_en_SQL_TH.ipynb`
- `monday/EDA_clase04_TH.ipynb`
- `monday/z301_Sobre_la_incertidumbre_TH.ipynb`
- `monday/EDA_target.ipynb`
- `monday/tomas_target_sql.ipynb`
- `monday/z101_target_sql.ipynb`

Inspeccionar estos archivos antes de crear notebooks, variables o experimentos nuevos. No inferir cuál es el notebook activo solo por su nombre.

La bitácora previa documenta datos de marzo a agosto de 2021, identificadores `numero_de_cliente` y `foto_mes`, y target `clase_ternaria` con BAJA+1, BAJA+2 y CONTINUA. Documenta BAJA+2 como clase accionable. Esto proviene del registro anterior, no de una nueva lectura del dataset. Verificar definición, horizonte, función de ganancia y archivos actualmente utilizados.

Punto a resolver: si los datos disponibles comienzan en marzo, no existe historial anterior para generar lags de marzo con ese archivo. Confirmar si hay otra fuente histórica o si corresponde rediseñar los meses de entrenamiento y evaluación; nunca completar el pasado con meses futuros.

### Trabajo anterior reportado por Tomás

Fuente: texto aportado por el usuario en la conversación de escritorio del 2026-09-09; no auditado contra el notebook en esta actualización.

- Corrió 100 trials y comparó las cinco mejores configuraciones en las mismas 30 particiones de marzo (70% entrenamiento, 30% validación).
- Comparó diferencias pareadas con Wilcoxon y reportó no encontrar evidencia suficiente de superioridad.
- Entrenó luego con todo marzo y evaluó mayo. Simuló 100 divisiones público/privado (30%/70%) con modelos fijos y los mismos grupos para todos.
- Reportó diferencias pequeñas e inversiones frecuentes entre público y privado.
- Revisar cuánto se usó mayo para seleccionar configuraciones antes de presentarlo como test independiente.

### Bibliografía local y síntesis

Los PDF se movieron desde Downloads a la raíz de este proyecto, conservando nombres y contenido.

#### Lemos, Silva y Tabak (2022)

[Propension to customer churn in a financial institution: a machine learning approach](521_2022_Article_7067.pdf)

DOI: https://doi.org/10.1007/s00521-022-07067-x

- Banco brasileño, muestra de 500.000 clientes balanceada artificialmente: 250.000 con churn y 250.000 sin churn.
- Churn: cierre de cuenta o inactividad durante seis meses.
- Predictores: agosto de 2018 a enero de 2019; horizonte objetivo: febrero a julio de 2019.
- FE: productos, transacciones, inversiones, crédito y rentabilidad, con valores anteriores y variaciones absolutas y porcentuales a seis meses; también sueldo y débitos automáticos.
- Comparación de árbol, KNN, logística, elastic net, SVM y RF. Holdout de 10%; selección mediante validación cruzada de diez folds repetida diez veces sobre entrenamiento.
- RF: AUC 0,9015, accuracy 82,8%, precision 84,4% y recall 80,2%. Ensamble: AUC 0,9018, sin superioridad significativa sobre RF (tablas 7–8, páginas 12–13 del PDF).
- Límites: no aísla el aporte del FE histórico frente a un modelo sin FE; muestra balanceada altera la interpretación de precision y accuracy en población; ahorros son proyecciones, no resultados observados de campañas. Asociaciones entre productos y permanencia no prueban causalidad.
- Secciones útiles: 3.2 y tabla 1 (variables), 3.4 (evaluación), 4–5 (resultados y conclusiones).

#### Kaya y otros (2018)

[Behavioral attributes and financial churn prediction](s13688-018-0165-5.pdf)

DOI: https://doi.org/10.1140/epjds/s13688-018-0165-5

- Cuatro datasets derivados de dos muestras de una misma institución, con aproximadamente 42.000–55.000 clientes después de los filtros; no son cuatro bancos independientes.
- Ventanas de observación de nueve o doce meses y de etiquetado de tres o cinco meses. La etiqueta principal es inactividad durante toda la ventana posterior.
- FE: diversidad espacial y temporal, concentración en lugares/horarios habituales (llamada loyalty, no fidelidad directa al banco), regularidad entre corto y largo plazo, y entropía de comercios/categorías/destinatarios.
- RF de 500 árboles, validación cruzada estratificada de ocho folds y SVM-SMOTE. Importancias mediante permutación sobre la parte de evaluación de cada fold.
- A1: AUC 0,779 con comportamiento frente a 0,513 con demografía. Comportamiento supera significativamente a demografía en los cuatro datasets. Agregar demografía a comportamiento no aporta una mejora significativa (figura 2, página 10).
- Límites: comparación central contra demografía, no contra un baseline bancario completo; requiere detalle transaccional no necesariamente disponible en nuestro dataset; no demuestra causalidad ni éxito de una campaña de retención.
- Secciones útiles: 2.2 (variables), 2.3–2.4 (target y evaluación), 3–4 (resultados y límites).

Los resúmenes provienen de la lectura de los PDF por Codex de escritorio el 2026-09-09. Consultar originales antes de replicar fórmulas o citar detalles. Las métricas de ambos papers no son directamente comparables entre sí ni con nuestro TP.

### Referencia explorada en Hugging Face

https://huggingface.co/ash001/bank-churn-ann

Notebook: https://colab.research.google.com/drive/1ubzL_5BlJwnAVtqoko7IlZjYa0V8913r

Lectura del notebook por Codex de escritorio: ANN de 64 y 32 neuronas, entradas tabulares sin historial mensual documentado, split 8.000/2.000, escalado, early stopping y accuracy reportada 86,4%. Usa los mismos 2.000 casos para early stopping y evaluación final: es validación, no test independiente. Es una referencia de implementación; no una demostración de superioridad ni fuente central de FE para esta tarea.

### Propuesta de próximos pasos (pendiente de discutir e implementar)

1. Revisar el notebook activo y el trabajo ya realizado; no duplicarlo.
2. Identificar datos e historia disponibles y verificar target, horizonte y ganancia.
3. Proponer una tabla de hipótesis, columnas reales, fórmulas, ventanas, tratamiento de faltantes y fuente de inspiración. Distinguir variables equivalentes ya implementadas.
4. Empezar con pocos cambios interpretables: lags y diferencias; actividad actual frente a promedios previos; meses consecutivos de caída; interrupción de usos habituales; diversidad de productos efectivamente usados, si existen datos.
5. Estas son hipótesis propias inspiradas en los papers, no mejoras demostradas para nuestro dataset. Discutir con Tomás antes de corridas largas.
6. Comparar originales vs. originales + intrames vs. originales + intrames + histórico usando las mismas particiones, semillas, criterio de ganancia e inicialmente hiperparámetros. Ajustar el protocolo si la disponibilidad temporal impide esa comparación y documentar la decisión.
7. Evitar fuga temporal y del objetivo. Distinguir mes calendario previo de registro previo, historial incompleto de actividad cero; tratar ceros, nulos e infinitos explícitamente. Ajustar transformaciones aprendidas solo sobre entrenamiento.
8. No copiar balanceo/SMOTE automáticamente. Evaluar sobre distribución real y considerar el efecto del muestreo sobre probabilidades y umbrales.
9. Conservar funciones y resultados negativos. Analizar ganancia y variabilidad, sin equiparar importancia con mejora real.
10. Registrar experimentos verificados aquí con referencias a archivos y preparar un resumen para Zulip cuando haya resultados. La publicación no está autorizada por este contexto.
