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

## 22. Primera entrega: decisiones, resultados y errores — 2026-10-01

Tomás pidió registrar tanto resultados positivos como negativos. Esta sección es el registro de continuidad; los archivos `salidas/*/manifest.json` contienen evidencia y parámetros de cada corrida. No confundir propuestas con resultados ejecutados.

### Organización y Git

- Se actualizó `main` desde `origin/main` al commit `54ad3bf`, conservando cambios locales con un stash. Se resolvió el conflicto de `z402_Feature_Engineering_en_SQL.ipynb` conservando ruta Windows y validación de archivo remota.
- Se creó y subió `77a9c7c` con 18 archivos; ocho PDFs fueron excluidos del commit a pedido de Tomás antes del push. El stash quedó como respaldo. No asumir que contiene el trabajo nuevo del TP.
- Se creó `tp_primera_entrega/`. A pedido de Tomás, los dos notebooks iniciales fueron convertidos a `.py` con bloques `# %%`, y se eliminaron esas copias `.ipynb`. Los notebooks originales de `monday/` se conservaron.
- Scripts actuales: `01_feature_discovery.py`, `02_modelado_evaluacion.py`, `baseline.py`, `features.py`, `03_comparar_intrames.py`, `04_comparar_historicas.py`, `validar_entrega.py`. Se agregó LightGBM 4.7.0 a `.venv` y `requirements.txt`.
- Los modelos y predicciones quedan en `tp_primera_entrega/salidas/`, excluida de Git. No se sobrescribe `data/competencia_01.csv`.

### Objetivo y entrega

- Fecha indicada por Tomás: domingo 11 de octubre de 2026.
- SUPUESTO HISTÓRICO REEMPLAZADO el 2 de octubre (ver sección 23): septiembre de 2021 se había usado como objetivo provisional. Se corrigieron mensajes que lo habían marcado indebidamente como confirmado. El objetivo vigente es agosto de 2021.
- Bajo aquel supuesto, BAJA+2 de la foto septiembre significaba presente en octubre y ausente en noviembre, y faltaba la foto septiembre en el CSV. Esa limitación del universo ya no aplica a la entrega confirmada de agosto, cuya foto sí está disponible.
- Formato propuesto: CSV de dos columnas `id,clase_ternaria`, etiquetas exactas `CONTINUA`, `BAJA+1`, `BAJA+2`. Los encabezados no están confirmados por plantilla oficial. Se creó `ejemplo_formato_entrega.csv` con IDs ficticios 1, 2, 3, no una entrega real.
- `validar_entrega.py` controla encabezados, etiquetas, unicidad y cobertura de IDs del mes de la foto. Se verificó que rechaza etiquetas con espacios, duplicados, faltantes, extras y columna adicional.

### Target y ganancia confirmados por evidencia

- Ejercicio original: `monday/z101_target_sql.ipynb`; resolución: `monday/tomas_target_sql.ipynb`. El notebook registra 983.061 filas comparadas y cero diferencias entre LEAD y joins a meses calendario; es un resultado guardado, no una nueva ejecución en esta sesión.
- Para una foto presente: ausencia en t+1 -> BAJA+1; presencia en t+1 y ausencia en t+2 -> BAJA+2; presencia en ambos -> CONTINUA; futuro insuficiente -> NULL cuando no puede determinarse.
- Dataset actual: marzo–agosto de 2021, 155 columnas. Marzo–junio tienen target completo; julio tiene 163.245 de 164.348 filas sin target; agosto, 164.647 sin target.
- Captura del PDF aportada por Tomás: seleccionar un BAJA+2 suma 1.072.500 NETOS; seleccionar BAJA+1 o CONTINUA resta 27.500; no seleccionar aporta cero. No descontar el costo dos veces. Se comprobaron las nueve celdas de la matriz.
- Umbral teórico 0,025 con probabilidades calibradas. Se usa fijo en los primeros experimentos. No se buscó el mejor corte en mayo.
- Para optimizar esta matriz basta clasificación binaria BAJA+2 contra el resto. La discusión inicial sobre necesitar multiclase se corrigió al conocer la matriz.

### Protocolo y límites reconocidos

- Principal acordado: train marzo, validación mayo; eventual reentrenamiento marzo + abril y test junio. No se ejecutó aún ese reentrenamiento ni la evaluación de junio.
- La disponibilidad del target de marzo al cierre de mayo y del target de abril al cierre de junio justifica esos conjuntos de entrenamiento. Sin embargo, seleccionar parámetros con etiquetas de mayo (disponibles en julio) y evaluar junio sigue siendo retrospectivo. Se corrigió la afirmación incompleta de que todo el proceso simulaba disponibilidad en tiempo real.
- Mayo ya se usó en experimentos anteriores; junio fue explorado en el EDA. No llamar al test completamente inédito. No optimizar usando junio.
- Para estudiar historia, Tomás autorizó un experimento SEPARADO: train abril, validación mayo. Tiene fuga de disponibilidad temporal respecto de una predicción real al cierre de mayo, porque usa targets de abril conocidos en junio. No modifica `config.json` ni se presenta como prueba prospectiva.
- No se balancean clases ni se divide aleatoriamente el panel completo. Todas las variantes de una comparación usan las mismas filas. Las diferencias entre train marzo y train abril no se atribuyen a las features.

### EDA y preparación mínima

- Actividad baja, falta de haberes y poco uso de canales están asociados descriptivamente con bajas. Ejemplo marzo–junio: mediana `ctrx_quarter` 17–25 en BAJA+2 vs 105–106 en CONTINUA. Asociación no demuestra mejora predictiva ni causalidad.
- `cmobile_app_trx` observado como 0/1. No tratarlo como volumen. No eliminar columnas de mora por porcentaje de nulos solamente.
- Se mantienen ceros y faltantes distintos; no se recortan montos negativos automáticamente. Se excluyen ID, foto_mes y target de predictores.
- Vencimiento del plástico en días: valores menores que -36.500 pasan a NaN como regla conservadora explícita, no como código especial confirmado. Afectó 466 Visa en marzo y 458 en mayo; ningún Master en esas particiones.
- Visa_status, Master_status y tcuentas se declaran categóricas. LightGBM conserva NaN. La logística imputa mediana, agrega indicadores, estandariza numéricas y usa one-hot; todo ajustado solo con train.

### Resultados ejecutados antes de Optuna

Todos con semilla 214363 y umbral 0,025. Validación mayo: 163.768 filas, 870 BAJA+2. Ganancias recalculadas desde predicciones, no copiadas de una interpretación visual.

| Experimento | Train | Variables | Ganancia mayo | TP | FP |
|---|---|---:|---:|---:|---:|
| Logística múltiple L2, C=1 | Marzo | 152 fuentes, 202 coeficientes | 189.392.500 | 400 | 8.713 |
| LightGBM original | Marzo | 152 | 241.807.500 | 416 | 7.431 |
| LightGBM + actividad | Marzo | 154 | 233.420.000 | 411 | 7.541 |
| LightGBM + totales tarjetas | Marzo | 155 | 239.195.000 | 415 | 7.487 |
| LightGBM + utilización tarjetas | Marzo | 156 | 235.867.500 | 412 | 7.491 |
| LightGBM original | Abril | 152 | 252.862.500 | 451 | 8.394 |
| LightGBM + históricas | Abril | 161 | 248.380.000 | 451 | 8.557 |

- Evidencia: `salidas/baseline_20261001_175959/`, `salidas/intrames_20261001_182431_130565/`, `salidas/historicas_20261001_182842_721867/`.
- LightGBM mejoró frente a logística en esta comparación. Logística convergió en 40 iteraciones sin advertencias. Sus coeficientes no son efectos causales ni selección universal para árboles; no hay p-valores. Se decidió conservarla como referencia y no profundizar Elastic Net por ahora.
- Resultado NEGATIVO: ningún bloque intrames mejoró a parámetros fijos. No se combinaron bloques. Las nueve históricas bajaron 4.482.500: mismos 451 TP, 163 FP adicionales. No atribuir significación a una sola configuración y semilla.
- Historia: lag exacto de un mes y delta para actividad, haberes, saldo y productos, más indicador de presencia previa. Se mantienen todos los clientes: 1.403 filas de abril y 1.448 de mayo no tienen mes previo. No usar una fila de dos meses atrás como lag de un mes. Se verificaron ceros, nulos, divisiones, cambio de año, orden y ausencia de uso del futuro.
- Antecedente en el notebook de RF: los agregados intrames tampoco mejoraron consistentemente; historia tuvo mejora media inestable. No comparar esas ganancias directamente con este protocolo.

### Decisiones de modelos y trabajo pendiente

- LightGBM principal; TabPFN segunda opción, prueba acotada pendiente. No se instaló ni ejecutó TabPFN, ni se crearon recursos cloud. Se discutió uso académico local y alternativas Google Cloud/Colab, sujetos a versión, hardware, créditos y cuota GPU; no prometer gratuidad del futuro dataset grande.
- Optuna autorizado. Se inicia `05_optuna_historicas_rf.py`: dos estudios TPE de 30 trials cada uno, originales vs históricas, ambos abril -> mayo. Mismo espacio, semilla, filas y umbral; igual cantidad de intentos, no igual tiempo. Incluye baseline como primer trial. Las sugerencias pueden divergir por los resultados de cada estudio.
- Espacio: 100–400 árboles, learning_rate 0,015–0,12, hojas {7,15,31,63}, mínimo hoja 30–500, L2 0,0001–20, fracción de columnas y filas 0,7–1. Sin early stopping ni pruning. La ganancia en mayo es la función objetivo.
- Se incluye un RF de referencia sin tuning: 300 árboles, profundidad 12, mínimo hoja 50, max_features=sqrt; originales, imputación y one-hot aprendidos en abril. No tiene presupuesto equivalente a los estudios de LightGBM; no será una prueba definitiva de superioridad de familia.
- Resultados de Optuna/RF pendientes al iniciar esta entrada. Se anexarán al finalizar, incluyendo trials fallidos si los hubiera. La mejor ganancia entre muchos intentos es optimista sobre mayo; junio sigue reservado.

### Cierre de Optuna y Random Forest — 2026-10-02

Corrida: `tp_primera_entrega/salidas/optuna_20261001_183546_498714/`. Ambos estudios terminaron con 30 trials COMPLETE, cero FAIL y cero RUNNING. Los primeros trials reprodujeron exactamente los baselines de abril. `verificacion.json` registra las comprobaciones sobre los 163.768 clientes de mayo y las ganancias recalculadas desde predicciones.

| Variante, train abril / validación mayo | Ganancia | Contactos | TP | FP |
|---|---:|---:|---:|---:|
| LightGBM original sin tuning | 252.862.500 | 8.845 | 451 | 8.394 |
| LightGBM histórico sin tuning | 248.380.000 | 9.008 | 451 | 8.557 |
| LightGBM originales, mejor de 30 trials | 263.257.500 | 8.147 | 443 | 7.704 |
| LightGBM históricas, mejor de 30 trials | 266.667.500 | 8.703 | 460 | 8.243 |
| Random Forest originales, referencia sin tuning | 222.475.000 | 10.150 | 456 | 9.694 |

- Resultado positivo: Optuna mejoró originales en 10.395.000 y el bloque histórico en 18.287.500 respecto de sus configuraciones iniciales. Tras tuning, la mejor histórica superó a la mejor original en 3.410.000 (aprox. 1,30 %). Es una diferencia pequeña seleccionada en el mismo mayo, no evidencia independiente ni prueba de significación.
- Resultado negativo: este RF fijo no mejoró a LightGBM. No se concluye que ningún RF pueda hacerlo: solo se probó una configuración de RF frente a estudios optimizados de LightGBM.
- Mejor original: trial interno 2 (tercer intento), 350 árboles, learning_rate 0,0192597512, 31 hojas, min_child_samples 35, reg_lambda 0,3529863235, colsample_bytree 0,82230158, subsample 0,70750315.
- Mejor histórica: trial interno 27 (intento 28), 250 árboles, learning_rate 0,0186181623, 31 hojas, min_child_samples 264, reg_lambda 0,0004384335, colsample_bytree 0,9934872065, subsample 0,8018887403. En ambos se activa subsample_freq=1; el resto parte de crear_lightgbm.
- Incidencia operativa: hubo pausas del entorno y pérdida del canal de seguimiento. Se informó inicialmente una interrupción al observar un trial RUNNING, pero el proceso original continuó y completó los 60 trials. Al recuperar, ya estaban completos; no se reintentó ni falló ningún trial. RF se ejecutó nuevamente con los mismos parámetros y reprodujo el resultado. Los tiempos de pared incluyen pausas largas: no presentarlos como horas de cómputo efectivo.
- Se conserva base SQLite, todos los trials, modelos mejores, parámetros, versiones, predicciones e importancias. `recuperacion_*.json` documenta la recuperación y su resultado observado. No se lanzó TabPFN ni se evaluó junio; tampoco se aplicó aún Optuna al protocolo principal train marzo.

## 23. Cambio confirmado de mes de entrega — 2026-10-02

Tomás confirmó: **hay que predecir agosto de 2021, no septiembre**.

- Configuración vigente: `prediccion_mes=202108`, `mes_base_clientes=202108`, `mes_asumido=false`. El horizonte se deriva del target existente: BAJA+2 implica presencia en septiembre y ausencia en octubre.
- El universo de agosto está en `competencia_01.csv`: 164.647 clientes. Las etiquetas desconocidas son esperadas. No se necesita una foto septiembre para generar la predicción de agosto; sí sería necesaria para observar parte de su resultado futuro.
- Actualizados configuración, comentarios de scripts 01/02, README y validador. El validador usa por defecto el mes de entrega de config.json; admite --mes para comprobaciones explícitas de otro período.
- Los manifiestos de corridas ya ejecutadas conservan el supuesto de entrega que regía al correrlas. Son trazabilidad histórica; las métricas corresponden a mayo y no cambian por esta corrección. No reescribirlos para fingir una ejecución bajo otra configuración.
- No se alteran las particiones de los experimentos, no se entrena con agosto ni se genera una entrega ficticia. Encabezados oficiales del CSV y regla final de selección siguen pendientes de validación con la consigna.

## 24. Comparación de features con presupuesto equivalente — 2026-10-02

Tomás autorizó completar la comparación originales/intrames/históricas. Se crea `06_comparacion_optuna_features.py` para agregar lo que faltaba: 30 trials Optuna con las nueve features intrames juntas (dos de actividad, tres totales de tarjetas y cuatro ratios). Se comparan tres alternativas separadas: 152 originales, originales + 9 intrames, originales + 9 históricas. No se combinan intrames con históricas en este experimento.

- Todos entrenan abril y validan mayo con umbral fijo 0,025. No se consultan etiquetas de junio ni se evalúa agosto, cuyo target se desconoce.
- Se reutilizan los 60 trials ya completados de originales/históricas: no cambian por actualizar el mes de entrega. Antes de reutilizar se verifican configuración relevante, versiones, hashes del código de preparación y 30 trials completos por estudio.
- El motor del archivo 05 ahora admite seleccionar variantes y omitir RF. El espacio de hiperparámetros y el sampler TPE con semilla 214363 se conservan. Los resultados de estudios diferentes pueden orientar sugerencias diferentes: igualdad de intentos, no identidad de parámetros ni de tiempo.
- Al consolidar se comprueban distribuciones de búsqueda, referencia inicial, filas y etiquetas de validación, auditorías, columnas y métricas recalculadas desde probabilidades. Los artefactos previos se conservan.
- La recuperación de estudios ya no marca automáticamente un trial RUNNING como fallido: se detiene y exige comprobar el proceso. Esto evita confundir una pausa del entorno con una terminación, como ocurrió en el seguimiento previo.
- Resultados pendientes al iniciar esta entrada; se agregan debajo al finalizar. Siguen siendo máximos seleccionados sobre mayo, de carácter exploratorio y retrospectivo.

### Cierre de la comparación de tres variantes

Corrida intrames y consolidación: `tp_primera_entrega/salidas/optuna_20261002_123603_479131/`. Se completaron los 30 trials nuevos sin fallos: junto con los 60 anteriores, hay 30 intentos por alternativa. Se verificaron compatibilidad de las corridas, igualdad de clientes/etiquetas de mayo, espacio de búsqueda y métricas recalculadas desde las probabilidades guardadas.

| Variante LightGBM, mejor de 30 | Variables | Ganancia mayo | Contactos | TP | FP | Diferencia vs originales |
|---|---:|---:|---:|---:|---:|---:|
| Originales | 152 | 263.257.500 | 8.147 | 443 | 7.704 | 0 |
| Originales + intrames | 161 | 264.467.500 | 8.383 | 450 | 7.933 | +1.210.000 |
| Originales + históricas | 161 | 266.667.500 | 8.703 | 460 | 8.243 | +3.410.000 |

- Resultado positivo: intrames con tuning mejora 14.767.500 respecto de su primer trial (249.700.000) y supera originales optimizados en 1.210.000 (0,46 %). Esto no contradice las pruebas negativas iniciales: aquí se entrenó abril, se combinaron los nueve intrames y se ajustaron hiperparámetros.
- Históricas conserva la mayor ganancia, 2.200.000 por encima de intrames (0,83 %). Es una candidata para el siguiente paso, no una mejora confirmada fuera de validación: se reutilizó mayo para elegir modelos y parámetros, con una sola semilla.
- Mejor intrames: trial interno 20 (intento 21), 300 árboles, learning_rate 0,0233635081, 31 hojas, min_child_samples 30, reg_lambda 19,3518591030, colsample_bytree 0,8760069240, subsample 0,7370028407, subsample_freq=1.
- Se guardaron `comparacion_tres_variantes.csv`, `comparacion_tres_variantes.json` y `predicciones_tres_variantes.csv`, además del estudio intrames, modelo, importancias y parámetros. El consolidado registra agosto como entrega y las rutas de las corridas de origen. Se puede verificar/reconsolidar con `06_comparacion_optuna_features.py --intrames-existente <carpeta>` sin volver a entrenar.
- No se ejecutó RF nuevamente, no se evaluó junio ni se generaron predicciones de agosto. Se conserva el protocolo principal en config.json; esta comparación mantiene el experimento retrospectivo abril -> mayo autorizado.

## 25. Evaluación congelada en junio — 2026-10-03

Tomás autorizó congelar el ganador histórico y evaluarlo en junio, con originales como referencia, y expresó interés en un experimento posterior con TabPFN.

- Se creó y ejecutó `tp_primera_entrega/07_evaluacion_junio.py`. La configuración se guardó antes de consultar junio, usando los parámetros exactos guardados por Optuna, subsample_freq=1, semilla 214363 y umbral fijo 0,025.
- Reentrenamiento marzo + abril: 326.184 filas. Se conserva marzo sin febrero: historia faltante e indicador cero. Para junio se leen exclusivamente claves y cuatro predictores de mayo como historia auxiliar, sin etiquetas de mayo.
- Originales: ganancia 333.410.000, 7.716 contactos, 496 TP, 7.220 FP. Históricas: 332.832.500, 8.537 contactos, 516 TP, 8.021 FP. Históricas queda -577.500 (-0,17 %) frente a originales. La ventaja seleccionada en mayo no se sostuvo; no se infiere significación de una semilla.
- Corrida `tp_primera_entrega/salidas/test_junio_20261003_114546_998605/`. Finalizó sin errores. Se verificaron cobertura, claves, etiquetas y ganancias recalculadas desde las probabilidades del CSV exportado. Se guardaron modelos, importancias, parámetros completos, versiones y hashes.
- Junio fue evaluado y queda expuesto. No hubo nuevo tuning, búsqueda de umbral, predicciones de agosto ni cambio de candidato basado en el test. TabPFN es el próximo experimento previsto; desarrollar en mayo y tratar futuras comparaciones en junio como exploratorias, no como test independiente.

## 26. Preparación de TabPFN — 2026-10-03

- Tomás pidió instalar y probar TabPFN, inicialmente marzo -> junio y marzo + abril -> julio. Se explicó que julio carece de 163.245 de 164.348 etiquetas; confirmó por respuesta explícita marzo -> mayo y evaluación exploratoria junio tras reentrenar marzo + abril.
- Instalados en `.venv`: torch 2.11.0+cu128 y tabpfn 9.1.0. GPU verificada por nvidia-smi: RTX 5070 Ti Laptop, 12.227 MiB, driver 591.97. PyTorch reconoce CUDA 12.8 y ejecutó multiplicación matricial en GPU. pip check: sin dependencias rotas.
- Creado `08_experimento_tabpfn.py`: TabPFN-3.5 explícito, originales, entrenamiento completo, sin muestreo ni balanceo, un estimador inicial, modo low_memory, inferencia por lotes, umbral fijo 0,025. Etapas separadas; test requiere validación completa y mismas versiones/código/configuración. Guarda manifiesto y errores, predicciones y métricas verificadas al completar. Cachés en salidas; credenciales nunca se guardan en manifiestos.
- `requirements-tabpfn.txt` registra versiones opcionales y el índice CUDA; no se fuerza instalar GPU para quienes solo ejecuten LightGBM. Compilación del script e importación verificadas.
- Intento real `salidas/tabpfn_validacion_20261003_120017_081423/`: 162.900 filas de marzo y 163.768 de mayo, 152 variables. Se detuvo antes de entrenar con TabPFNLicenseError: falta aceptación personal de licencia e inicio de sesión en PriorLabs para descargar pesos; el login automático está desactivado. No se evaluó memoria efectiva del entrenamiento ni se produjo ganancia de TabPFN.
- Se pidió al usuario aceptar la licencia en https://ux.priorlabs.ai y configurar TABPFN_TOKEN localmente, sin enviarlo en el chat. Pendiente reanudar validación y luego junio. No se envió el dataset a una API de inferencia ni se generó entrega de agosto.



## 27. TabPFN local: pesos y corrida prolongada - 2026-10-03

- Usuario descargo pesos v3.5 (876027932 bytes) y confirmo licencia aceptada. Carga local exitosa.
- Intento completo de marzo: fit exitoso, predict falla por CUDA sin memoria. Precision float16 forzada descartada por advertencias de overflow. Autocast con cache en CPU completa fit pero primer lote de 100 filas demora varios minutos. Se conservan manifiestos de intentos.
- Se descargaron pesos v3.5-fast (334181708 bytes). Fast completa fit; inferencia tambien lenta con entrenamiento completo.
- Usuario eligio explicitamente mantener todas las filas y permitir una corrida prolongada, potencialmente de horas. Sin muestreo.
- Se agrego etapa secuencia, guardado de probabilidades parciales por lote y manejo de interrupciones. Se reinicio con logs persistentes en salidas/tabpfn_secuencia_20261003_123841/, PID inicial 25356. Modelo v3.5-fast, 1 estimador, autocast, cache en CPU, lotes 1000, semilla 214363, umbral 0.025.
- Secuencia automatica: marzo -> mayo, y solo tras validacion completa y verificada, marzo+abril -> junio exploratorio. No se usa julio ni se genera agosto. Resultados aun pendientes; consultar proceso y logs antes de reanudar o duplicar.


## 28. Cancelacion de TabPFN - 2026-10-04

Usuario solicito detener la corrida por tiempo excesivo. Se detuvieron los procesos identificados de 08_experimento_tabpfn.py (25356 y 40708). Se conservan logs, pesos y 5000 probabilidades parciales de mayo. Manifest marcado cancelado_por_usuario. No se completo mayo ni se ejecuto junio; no hay metricas del universo completo.

## 29. TabPFN vía API gratuita de PriorLabs — 2026-10-04

Tomás autorizó adaptar el script 08 y ejecutar mediante PriorLabs tras comprobar límites y cuota gratuita. Ambas etapas finalizaron; sus manifiestos registran estado completo y ganancia recalculada desde los CSV de predicciones.

- `08_experimento_tabpfn.py` usa ahora `tabpfn-client` 0.6.1 en `.venv-priorlabs`, sin GPU local. Se agregó `09_consultar_cuota_priorlabs.py` para cotizar sin subir valores ni consumir cuota, y `requirements-priorlabs.txt` para las dependencias. Adaptación verificada con API simulada para validación, test y bloqueo por presupuesto antes de las corridas reales.
- Configuración: TabPFN-3.5-Fast (`v3.5-fast_default`), 152 variables originales, un estimador, semilla 214363, autocast, `fit_preprocessors`, `SUBSAMPLE_SAMPLES=None`, sin muestreo ni balanceo, sin escalado ni one-hot. Umbral fijo 0,025; una solicitud de predicción por etapa. Se conserva la limpieza de `preparar` del baseline. Se enviaron features y etiquetas de entrenamiento, sin ID ni mes; las etiquetas de evaluación permanecieron locales.
- Las dimensiones de ambas etapas entraron en los límites API: hasta 1.000.000 de filas, 20.000 columnas, 200.000.000 de celdas por partición y 250.000.000.000 de pares train/evaluación. La cuota mensual consultada fue de 20.000.000 de créditos, inicialmente sin consumo.

| Etapa | Filas train | Filas evaluación | Ganancia | Contactos | TP | FP | Precisión | Recall | ROC AUC | Average precision | Log loss | Segundos | Créditos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Marzo → mayo | 162.900 | 163.768 | 255.695.000 | 8.902 | 455 | 8.447 | 0,051112 | 0,522989 | 0,892415 | 0,054004 | 0,026288 | 46,34 | 17.522 |
| Marzo + abril → junio, exploratoria | 326.184 | 164.114 | 373.945.000 | 8.442 | 551 | 7.891 | 0,065269 | 0,501821 | 0,899065 | 0,064595 | 0,031597 | 71,99 | 32.709 |

- Los saldos posteriores confirman consumo real acumulado de 17.522 y luego 50.231 créditos, coincidente con las cotizaciones: 0,251155 % de la cuota mensual. Ambas corridas se completaron dentro del servicio gratuito. Los tiempos registrados corresponden a fit y predicción, sin incluir carga, preparación y cotización previas.
- En junio, TabPFN supera LightGBM originales (333.410.000) en 40.535.000 (+12,16 %) y LightGBM históricas (332.832.500) en 41.112.500 (+12,35 %). Comparación con las mismas particiones de marzo + abril → junio y umbral 0,025; LightGBM había sido optimizado con Optuna, TabPFN usa la configuración indicada sin tuning.
- Junio ya estaba expuesto: este resultado es exploratorio, con una sola semilla; no constituye un test independiente ni prueba de superioridad general. No se ajustaron umbral ni parámetros con junio. La comparación de mayo con los estudios Optuna de la sección 24 no tiene idéntico entrenamiento (marzo frente a abril). No se generaron predicciones ni entrega de agosto.
- Artefactos: `tp_primera_entrega/salidas/tabpfn_api_validacion_20261004_160420_775408/` y `tp_primera_entrega/salidas/tabpfn_api_test_20261004_160607_599793/`. Incluyen manifiestos, probabilidades, CSV, métricas, cuotas, cotizaciones, versiones y hashes. El test referencia la validación completa y comprueba compatibilidad de código, versiones y configuración. El alias del checkpoint depende del servidor y no garantiza reproducibilidad exacta entre fechas.


## 30. Comparaci?n de estimadores de TabPFN Fast ? 2026-10-04

Tom?s autoriz? probar distintos estimadores. Se cre? y ejecut? `10_comparar_estimadores_tabpfn.py`: Fast con 1, 2, 4 y 8, train marzo (162.900 filas), validaci?n mayo (163.768), 152 variables originales, semilla 214363, umbral 0,025 y todas las filas. Se reutiliz? la corrida completa de un estimador; se ejecutaron tres nuevas. Se verificaron versiones, hashes, configuraci?n, igualdad de clientes/etiquetas y m?tricas recalculadas desde CSV. No se consult? junio ni agosto.

| Estimadores | Ganancia mayo | Diferencia vs 1 | Contactos | TP | FP | Segundos fit/predict | Cr?ditos reales |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1, referencia reutilizada | 255.695.000 | 0 | 8.902 | 455 | 8.447 | 46,34 | 17.522, ya consumidos |
| 2 | 258.747.500 | +3.052.500 | 8.511 | 448 | 8.063 | 41,05 | 35.045 |
| 4 | 256.217.500 | +522.500 | 8.483 | 445 | 8.038 | 73,57 | 70.090 |
| 8 | 258.307.500 | +2.612.500 | 8.407 | 445 | 7.962 | 121,27 | 140.180 |

- Dos estimadores obtuvo la mayor ganancia en mayo: +1,19 % frente a uno y 440.000 por encima de ocho. M?s estimadores no mejoraron mon?tonamente la ganancia. La mejora frente a uno viene de reducir 384 FP a costa de perder 7 TP. Es selecci?n sobre mayo, ya reutilizado, con una semilla; no demuestra superioridad general ni permite atribuir significaci?n a la diferencia.
- Consumo nuevo real, confirmado por saldos: 245.315 cr?ditos, coincidente con las cotizaciones. Acumulado mensual: 295.546 de 20.000.000 (1,47773 %); quedan 19.704.454. Los tiempos incluyen latencia variable del servicio, por lo que 2 m?s r?pido que 1 no establece una ventaja sistem?tica de velocidad.
- Consolidado: `tp_primera_entrega/salidas/tabpfn_estimadores_20261004_161951_317808/`, con `comparacion.csv` y `comparacion.json`. Nuevas corridas: `tabpfn_api_validacion_20261004_161951_730008/` (2), `tabpfn_api_validacion_20261004_162039_319484/` (4) y `tabpfn_api_validacion_20261004_162157_425606/` (8), bajo `tp_primera_entrega/salidas/`.
- La clave se carg? desde un archivo cifrado con DPAPI, sin imprimirla ni guardarla en texto plano; fue necesario ejecutar fuera del aislamiento para descifrar con el usuario de Windows. Se retir? la variable del proceso al finalizar. No se alter? el script 08 ni sus hashes congelados. No se reentren? para junio ni se gener? entrega de agosto en esta comparaci?n.


## 31. TabPFN-3.5 est?ndar con 2 estimadores ? 2026-10-04

Tom?s autoriz? ejecutar tras cotizar 69.304 cr?ditos. Corrida completa marzo ? mayo: 162.900 filas train, 163.768 evaluaci?n, 152 variables originales, todas las filas, semilla 214363 y umbral 0,025. Se us? `08_experimento_tabpfn.py --etapa validacion --model-version v3.5 --n-estimators 2`, manteniendo el resto de la configuraci?n API del experimento Fast.

- Ganancia: 262.405.000; contactos: 9.058; TP: 465; FP: 8.593. Precisi?n 0,051336; recall 0,534483; average precision 0,054401; ROC AUC 0,895741; log loss 0,026096. Tiempo fit/predict: 61,87 segundos.
- Frente a Fast con 2 estimadores (258.747.500), mejora 3.657.500 (+1,41 %): detecta 17 TP adicionales y suma 530 FP. Se verificaron igualdad de clientes/etiquetas y ganancia recalculada desde el CSV. Mejora seleccionada sobre mayo, con una semilla; no demuestra superioridad general.
- Artefactos: `tp_primera_entrega/salidas/tabpfn_api_validacion_20261004_162942_034225/`. Manifiesto completo, predicciones, configuraci?n, versiones, hashes y cotizaci?n. Consumo real confirmado por saldos: 69.304 cr?ditos; acumulado mensual 364.850 de 20.000.000, saldo 19.635.150. La clave cifrada se us? en memoria sin mostrarse y la variable del proceso se retir? al finalizar.
- No se consult? junio ni agosto. Esta corrida queda disponible como referencia de est?ndar con 2 estimadores; no se cambi? el umbral ni se gener? entrega.


## 32. Evaluaci?n exploratoria de est?ndar con 2 estimadores en junio ? 2026-10-04

Tom?s autoriz? evaluar en junio la configuraci?n elegida en mayo, sin nuevos ajustes. Se reentren? marzo + abril (326.184 filas) y se predijo junio completo (164.114), con TabPFN-3.5 est?ndar, 2 estimadores, 152 variables originales, semilla 214363 y umbral fijo 0,025. El script 08 verific? compatibilidad con la validaci?n `tabpfn_api_validacion_20261004_162942_034225/`. No se cambi? el c?digo ni se utiliz? agosto.

- Ganancia: 357.115.000; contactos: 8.694; TP: 542; FP: 8.152. Precisi?n 0,062342; recall 0,493625; average precision 0,065910; ROC AUC 0,903065; log loss 0,031269. Tiempo fit/predict: 133,20 segundos.
- Frente a Fast con 1 estimador en junio (373.945.000), queda 16.830.000 por debajo (-4,50 %): 9 TP menos y 261 FP m?s. Frente a LightGBM originales (333.410.000), mejora 23.705.000 (+7,11 %); frente a hist?ricas (332.832.500), mejora 24.282.500 (+7,30 %). No es una comparaci?n aislada de la arquitectura, porque est?ndar usa 2 estimadores y Fast 1. La mejor ganancia seleccionada en mayo no garantiz? el mejor resultado en junio. AUC mayor tampoco implic? mayor ganancia.
- CSV verificado: mismos clientes y etiquetas que la corrida Fast de junio; ganancia recalculada coincidente. Artefactos: `tp_primera_entrega/salidas/tabpfn_api_test_20261004_163559_022545/`.
- Consumo real: 142.330 cr?ditos, igual a la cotizaci?n. Acumulado mensual 507.180 de 20.000.000; saldo 19.492.820. Se fij? tope estimado de 200.000 por etapa para admitir esta corrida; no se cambi? la configuraci?n predictiva.
- Junio ya estaba expuesto y esta evaluaci?n sigue siendo exploratoria, con una semilla. No se ajust? ning?n par?metro ni umbral con el resultado, no se cambia autom?ticamente el candidato por ganar en junio y no se gener? entrega de agosto.

## 33. Pruebas pendientes y próximos pasos — 2026-10-04

Tomás decidió postergar nuevas corridas para reservar créditos. Esta sección documenta propuestas pendientes: no autoriza su ejecución automática ni nuevas llamadas de inferencia. Saldo de la última consulta: 19.492.820 créditos mensuales disponibles, con 507.180 consumidos de 20.000.000; consultar nuevamente cuota diaria y mensual y cotizar antes de retomar.

### Completar la comparación de estimadores y variantes

- **Fast con 2 estimadores en junio:** reentrenar marzo + abril y evaluar junio con la configuración seleccionada en mayo, todas las filas, mismas variables y umbral 0,025. Usar la validación completa de Fast con 2 (`tabpfn_api_validacion_20261004_161951_730008/`). Permitiría comparar Fast de 1 frente a 2 y Fast frente a estándar con el mismo número de estimadores. Pendiente; junio está expuesto y la evaluación será exploratoria.
- **Estándar con 1, 2, 4 y 8 estimadores en mayo:** entrenar marzo y validar mayo, manteniendo semilla, features y umbral. Es una búsqueda de un hiperparámetro, no una optimización general de la red. Reutilizar la corrida estándar con 2 (`tabpfn_api_validacion_20261004_162942_034225/`), previa verificación de compatibilidad; faltan 1, 4 y 8. Seleccionar según ganancia de mayo, registrar consumo y tiempos, y congelar antes de cualquier evaluación posterior.
- **Interpretación vigente:** 2 fue el mejor número entre 1, 2, 4 y 8 para Fast en mayo, con una semilla. No está establecido como óptimo general ni como mejor número para estándar: esta última solo se probó con 2. La comparación actual de junio mezcla Fast de 1 con estándar de 2; no permite aislar el efecto de la variante. No elegir configuraciones buscando maximizar repetidamente junio.

### Otras vías de mejora discutidas

- **Features históricas:** probar cambios de saldo, consumo y actividad respecto de meses previos. Definir particiones y tratamiento de historia faltante antes de correr (marzo carece de febrero en el dataset); usar solo historia disponible hasta cada foto. Comparar originales frente a históricas con iguales meses, filas, semilla y configuración.
- **Mezcla TabPFN + LightGBM:** comparar unos pocos pesos prefijados (por ejemplo, 25 %, 50 % y 75 % de TabPFN) sobre probabilidades de los mismos clientes y con el mismo protocolo de entrenamiento. Verificar compatibilidad antes de reutilizar artefactos; no mezclar directamente resultados de marzo → mayo con abril → mayo. Evaluar ganancia, sin asumir mejora por combinar modelos.
- **Regla de selección:** estudiar en mayo la ganancia frente a umbral o cantidad de contactos usando predicciones guardadas, sin nueva inferencia ni créditos API. Mantener 0,025 como referencia teórica bajo probabilidades calibradas; buscar una zona estable de buenos resultados y no presentar el máximo exacto seleccionado en mayo como rendimiento independiente. Congelar cualquier cambio antes de evaluar otro período.
- **Estabilidad entre semillas:** si se retoman las pruebas, medir si las diferencias pequeñas se sostienen con semillas adicionales, bajo presupuesto previamente definido. No tratar una única corrida como evidencia de superioridad general.

Cambiar una dimensión por vez y mantener todas las filas, según la preferencia vigente. La métrica principal sigue siendo la ganancia oficial; AUC y log loss son complementarias. Mayo ya fue reutilizado para selección y junio ya fue evaluado: no queda un test independiente dentro de esos períodos. Agosto continúa siendo el mes de entrega sin etiquetas conocidas; no evaluar su calidad inventando targets ni usar información futura para features. Ninguna de estas pruebas pendientes se ejecutó al agregar esta sección.

## 34. Preparación local de históricas para TabPFN — 2026-10-04

Tomás pidió agregar las históricas. Se creó `11_tabpfn_historicas.py`, separado del script 08 para conservar los hashes de sus corridas. La restricción de reservar créditos sigue vigente: se ejecutó únicamente preparación local, sin llamadas API ni inferencias.

- Reutiliza `features.py`: lag de un mes calendario y delta actual menos anterior de `ctrx_quarter`, `mpayroll`, `mcuentas_saldo` y `cproductos`, más indicador de historia disponible (9 nuevas, 161 totales).
- Experimento propuesto: estándar con 2 estimadores, abril → mayo, originales frente a originales + historia. Marzo aporta historia para abril; abril para mayo. Marzo no tiene febrero y por eso no se usa como train en esta comparación. No comparar directamente su ganancia con las corridas marzo → mayo ni atribuir al bloque histórico un cambio causado por entrenar otro mes. Es retrospectivo: la etiqueta de abril se conoce en junio.
- Preparación verificada sobre el dataset completo: train 163.284 filas, validación 163.768; sin mes anterior 1.403 y 1.448, respectivamente. Se conservan esas filas con faltantes e indicador cero. La historia auxiliar solo lee claves y cuatro predictores; no lee targets históricos ni consulta junio/agosto. Prueba sintética verifica unión por mes calendario, faltantes y que cambiar mayo no altere features de marzo/abril.
- Manifiesto local: `tp_primera_entrega/salidas/tabpfn_historicas_20261004_164544_743217/`. Registra dimensiones, faltantes, auditorías, versiones y hashes. Por defecto, ejecutar el script solo prepara. `--ejecutar-api` lanzaría ambas variantes, cotizando primero el total y aplicando un tope estimado de 200.000 créditos. Las inferencias siguen pendientes y requieren autorización posterior; todavía no hay métricas de este experimento.

## 35. Fast con 2 estimadores: históricas, abril → mayo — 2026-10-04

Tomás autorizó ejecutar Fast con 2 estimadores, entrenando abril y validando mayo. Se compararon originales frente a originales + las 9 históricas preparadas en el experimento separado. El script 11 admite ahora `--model-version`; se ejecutó con `v3.5-fast` y `--ejecutar-api`.

| Variante | Variables | Ganancia mayo | Contactos | TP | FP | Segundos fit/predict |
|---|---:|---:|---:|---:|---:|---:|
| Originales | 152 | 246.537.500 | 9.515 | 462 | 9.053 | 85,41 |
| Originales + históricas | 161 | 248.270.000 | 9.412 | 461 | 8.951 | 54,15 |

- Mismas filas: 163.284 de abril, 163.768 de mayo; semilla 214363, umbral 0,025, 2 estimadores, todas las filas, sin balanceo ni tuning. Se conservaron 1.403 clientes de train y 1.448 de validación sin mes anterior. Marzo aporta predictores para historia de abril, sin etiquetas auxiliares; no se consultaron junio ni agosto.
- Históricas mejora 1.732.500 (+0,70 %), por 102 FP menos y un TP menos. Mejora pequeña sobre validación reutilizada y una semilla: no se infiere significación ni generalización. Las ganancias no se comparan directamente con marzo → mayo para atribuir diferencias a historia, porque cambió el mes de entrenamiento. Los tiempos tienen latencia variable de API y no prueban que historia sea más rápida.
- ROC AUC: 0,889458 originales, 0,890787 históricas; average precision: 0,049415 y 0,049941; log loss: 0,026923 y 0,026768. Cobertura, unicidad y ganancias verificadas nuevamente desde el CSV guardado.
- Cotización y consumo real total: 71.225 créditos, confirmados por saldos (507.180 → 578.405 consumidos). Saldo mensual restante: 19.421.595 de 20.000.000. Artefactos: `tp_primera_entrega/salidas/tabpfn_historicas_20261004_164740_418254/`, con manifiesto completo, predicciones, comparación y cuotas. No se cambió la regla de selección ni se generó entrega de agosto.

## 36. Históricas ampliadas con Fast de 2 estimadores — 2026-10-04

Tomás autorizó agregar más historia y probar nuevamente. Se incorporó `agregar_historicas_ampliadas` en `features.py` y `--bloque ampliadas` en el script 11, conservando el bloque básico como opción. Se ejecutó abril → mayo, Fast con 2 estimadores, todas las filas, semilla 214363 y umbral 0,025. No se consultó junio ni agosto.

- Bloque ampliado: 50 históricas en total (41 adicionales al bloque de 9), 202 variables con originales. Añade lags y deltas de consumo Visa/Master, transacciones de tarjetas, homebanking y app, y cantidad de tarjetas; variaciones relativas sobre valor absoluto anterior (faltante cuando el denominador es cero); medias de hasta tres meses anteriores de actividad, sueldo, saldo y productos, diferencias respecto de esas medias y conteos de observaciones. Registra cobertura temporal y conserva faltantes.
- Historia realmente disponible: abril solo tiene marzo; mayo tiene marzo y abril. Los promedios no representan tres meses completos ni una tendencia prolongada. Los conteos permiten distinguir coberturas. Prueba sintética verifica media previa, variaciones relativas, cobertura y ausencia de influencia futura. Se mantuvieron 163.284 filas train y 163.768 de validación, sin excluir clientes sin historia.

| Variante | Variables | Ganancia mayo | Contactos | TP | FP |
|---|---:|---:|---:|---:|---:|
| Originales, referencia reproducida | 152 | 246.537.500 | 9.515 | 462 | 9.053 |
| Históricas básicas, corrida previa | 161 | 248.270.000 | 9.412 | 461 | 8.951 |
| Históricas ampliadas | 202 | 251.267.500 | 9.143 | 457 | 8.686 |

- Ampliadas mejora 4.730.000 (+1,92 %) frente a originales y 2.997.500 (+1,21 %) frente a básicas. Respecto de originales pierde 5 TP y reduce 367 FP. Ganancia mejor, pero ROC AUC baja a 0,885025 (originales 0,889458); average precision 0,049537 y log loss 0,026930. No asumir mejora uniforme de todas las métricas ni generalización de una sola semilla en mayo reutilizado.
- La referencia original reprodujo exactamente las métricas observadas; se verificaron clientes/etiquetas y ganancias desde los CSV. Fit/predict: originales 41,66 segundos, ampliadas 61,37. Artefactos: `tp_primera_entrega/salidas/tabpfn_historicas_20261004_165442_887149/`.
- Cotización y consumo real: 75.842 créditos, confirmados por saldos de 578.405 a 654.247 consumidos. Quedan 19.345.753 créditos mensuales. Las dos variantes incluyen una nueva referencia original para controlar la ejecución. No se ajustó umbral, no se evaluó junio y no se generó entrega de agosto. La mejora se interpreta dentro del experimento abril → mayo, no comparándola directamente con entrenamientos de marzo.

## 37. Auditoría local de las 202 features — 2026-10-04

Tomás autorizó auditar y advirtió que quizá no corresponde eliminar nada. Se creó y ejecutó `12_auditar_features_tabpfn.py`, reutilizando la preparación ampliada de abril → mayo. No elimina columnas, no usa etiquetas para selección, no llama a la API y no consume créditos. Conservamos las 202 variables y los resultados previos.

- Abril: 163.284 filas; mayo: 163.768. Ninguna columna está completamente vacía o es constante en abril, considerando también el patrón de faltantes. Tampoco hay columnas con único valor no nulo y faltantes.
- Se detectaron 25 pares exactamente iguales en abril, confirmados por igualdad completa tras agrupar hashes. Trece dejan de coincidir en mayo: lags frente a medias previas, deltas y cobertura histórica. Se explica por un mes de historia en train y hasta dos en validación; no corresponde eliminar automáticamente por igualdad en abril.
- Los 12 pares que permanecen iguales en mayo pertenecen a tres grupos: `Master_mconsumospesos`/`Master_mconsumototal`; `Visa_mconsumospesos`/`Visa_mconsumototal`; y las cinco columnas de cobertura (`historial_meses_previos_3` y cuatro conteos de observaciones). Son coincidencias observadas, no identidad garantizada en otros meses ni evidencia de mejora al quitarlas. Las diferencias semánticas pueden importar con otra historia o faltantes.
- No se realizó selección por correlación, importancia ni target. La auditoría no establece qué variables tienen señal predictiva ni garantiza que una versión reducida mejore la ganancia. Cualquier reducción futura requeriría un experimento separado, reglas definidas en train y autorización de corrida; decisión actual: mantener todo.
- Artefactos: `tp_primera_entrega/salidas/auditoria_features_20261004_170740_881243/`: `informe.md`, `perfil_columnas.csv`, `duplicadas_abril.csv` y `resumen.json`. No se consultó junio ni agosto y no se modificaron generadores ni scripts de inferencia.

## 38. Históricas ampliadas y Fast de 2 estimadores en junio — 2026-10-04

Tomás autorizó evaluar ambas variantes en junio. El script 11 admite `--etapa junio --validacion-existente`, comprobando modelo, bloque histórico, columnas, semilla, umbral, versiones y hashes de features/baseline contra la corrida de mayo `tabpfn_historicas_20261004_165442_887149/`. Se modificó el orquestador para el nuevo período, sin modificar los generadores ni la configuración predictiva. Entrenamiento marzo + abril (326.184 filas); evaluación junio (164.114). Fast, 2 estimadores, semilla 214363, umbral 0,025 y todas las filas.

- Marzo se conserva sin febrero: historia faltante e indicadores cero. Total train sin mes anterior 164.303; evaluación sin mes anterior 1.489. Se leen solo claves y predictores para historia auxiliar de mayo. Junio recibe historia de marzo, abril y mayo; no se usa el target auxiliar ni información de julio/agosto. La cobertura histórica es distinta entre train y evaluación, una limitación del experimento.

| Variante | Variables | Ganancia junio | Contactos | TP | FP | Recall | ROC AUC | Segundos fit/predict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Originales | 152 | 354.227.500 | 8.239 | 528 | 7.711 | 0,480874 | 0,900882 | 73,42 |
| Originales + ampliadas | 202 | 380.792.500 | 9.953 | 595 | 9.358 | 0,541894 | 0,902743 | 106,80 |

- Históricas mejora 26.565.000 (+7,50 %) frente a originales bajo la misma configuración, con 67 TP adicionales y 1.647 FP adicionales. Precisión histórica 0,059781; average precision 0,065796; log loss 0,031190. El mayor número de contactos reduce precisión pero aumenta recall y ganancia.
- Frente a Fast de 1 original registrado previamente en junio (373.945.000), ampliadas con 2 mejora 6.847.500 (+1,83 %). Frente a LightGBM originales (333.410.000), mejora 47.382.500 (+14,21 %). La comparación directa que aísla el bloque histórico es con originales de 2 de esta misma corrida; no atribuir diferencias entre configuraciones al bloque solamente.
- Universo y etiquetas coinciden con los CSV previos de junio; ganancias recalculadas y estado completo verificados. Artefactos: `tp_primera_entrega/salidas/tabpfn_historicas_20261004_172322_339836/`, con comparación, predicciones, manifiesto y cotizaciones.
- Cotización y consumo real total: 139.275 créditos, confirmados por saldos de 654.247 a 793.522 consumidos. Quedan 19.206.478 créditos mensuales. Junio ya estaba expuesto: evaluación exploratoria, una semilla, no prueba independiente. No se ajustaron parámetros ni umbral con este resultado, no se eliminaron columnas y no se generó entrega de agosto.
