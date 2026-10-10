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


## 39. Primera prediccion de agosto para Zulip - 2026-10-04

Se creo y ejecuto `13_submit_tabpfn.py`, con autorizacion explicita para enviar a PriorLabs las variables de agosto y las variables/etiquetas de mayo y junio. Fast v3.5, 2 estimadores, seed 214363, 202 features (152 originales + 50 historicas), sin muestreo. Train mayo+junio: 327.882 filas; agosto: 164.647. Historia de meses calendario anteriores, sin targets auxiliares. El cambio a meses recientes de train no es una nueva validacion: la ganancia de junio no garantiza el resultado de agosto.

Umbral fijo 0,025: 10.151 contactos. CSV validado sin encabezado ni indice, IDs enteros unicos pertenecientes a agosto, sin notacion cientifica. Archivo: `tp_primera_entrega/salidas/TabPFNHist_20261004_223836/TabPFNHist_20261004_223836.csv`. Probabilidades de todos los clientes, manifiesto, hashes y mensaje guardados en la misma carpeta. Cotizacion: 74.370 creditos; no se consulto el saldo posterior. No se envio a Zulip desde esta sesion; pendiente envio manual y respuesta del bot. Mensaje: `submit TabPFNHist_20261004_223836`. Primera prueba con un archivo, no comparacion de multiples semillas ni entrega definitiva.


## 40. Respuesta publica de TabPFN y prueba LightGBM con historia - 2026-10-04

Tomas informo la respuesta del bot al submit TabPFNHist_20261004_223836: Public gain mean 92.2625, std dev 0.0000. Equivale a 92.262.500 pesos en el subconjunto publico de agosto (aprox. 25%), sin escalar. Un archivo explica la desviacion cero; no mide incertidumbre del modelo. El puntaje publico no permite conocer el privado.

Se creo y ejecuto `14_lightgbm_catedra_historicas.py`, inspirado en z601, con 202 variables (152 originales + 50 historicas), sin eliminar columnas. Todo local con CPU, sin API ni creditos. Dos targets: BAJA+2 y BAJA+1/BAJA+2. Diez trials por target (primera busqueda, no exhaustiva), cinco splits estratificados 70/30 en abril, hasta 1000 rounds. Espacio de parametros de z601, max_bin 31, bagging_freq 1 para activar bagging, semilla base 189293. Early stopping por fold evalua ganancia de BAJA+2 real para ambos targets; rounds finales son mediana de best_iter, una diferencia explicita frente al CV agregado del notebook. No se modifica el notebook ni su base SQLite.

Los cinco mejores trials internos de cada target se evaluaron temporalmente en mayo con tres semillas comunes, train abril. Se seleccionaron parametros, target y contactos sobre una grilla 8000..15000 cada 500. Es seleccion en mayo ya reutilizado, no evaluacion independiente. Mejor BAJA+2: 249.700.000 pesos medios, 9000 contactos. Elegido: target combinado, trial 8, 28 hojas, learning_rate 0.10468457153013469, min_data_in_leaf 892, feature_fraction 0.5259183807371636, bagging_fraction 0.7756493894058875, 59 rounds y 8500 contactos. Mayo: media 275.550.000, std muestral 3.966.106,40 (tres semillas). Esto no prueba el aporte causal de historia porque no se corrio control original bajo este protocolo.

Configuracion congelada antes de junio. Comprobacion exploratoria con train abril/mayo: ganancias 353.650.000, 347.050.000 y 343.750.000; media 348.150.000 pesos. No se cambio configuracion ni contactos a partir de junio. Junio estaba expuesto y se considera exploratorio.

Agosto: train mayo/junio, 20 semillas tomadas como en z601 (np.random.seed(17), choice sin reemplazo), resto de parametros identicos. Historia usa meses calendario anteriores sin targets auxiliares; ID, foto_mes y target excluidos de features. Se generaron 20 archivos de 8500 clientes cada uno, con IDs enteros unicos de agosto, sin encabezado, indice ni notacion cientifica. Validacion de pertenencia, formato, cantidades y hashes completada. Artefactos: `salidas/lgbm_catedra_hist_20261004_225654/`; adjuntos exclusivamente en `adjuntos_zulip/`. Mensaje: `submit LGBMHist20261004225654`. No se envio a Zulip desde esta sesion; puntaje pendiente y entrega definitiva no elegida.

Configuracion portable: `config_submit_lightgbm_historicas.json`; versiones exactas: `requirements-lightgbm-submit.txt`. Se agrego `15_reproducir_submit_lightgbm.py` para reentrenar directamente los modelos congelados y comparar los hashes, sin repetir Optuna. Los datos y outputs siguen fuera de Git. El README incluye instrucciones de busqueda y reproduccion.

Verificacion final completada el 2026-10-05: se reentrenaron los 20 modelos mediante el script 15, sin repetir Optuna; los 20 CSV regenerados coincidieron byte por byte (SHA-256) con los originales. Evidencia en `salidas/reproduccion_lgbm_20261004_225654/verificacion.json`. Esto verifica reproduccion en el ambiente local registrado, no garantiza identicos resultados bajo otro sistema o versiones.

## 41. Respuesta publica de LightGBM con historicas - 2026-10-05

Tomas informo Public gain mean 88.4304, std dev 3.2891; Submission ID: `1617-1791214407036171`. Para los 20 archivos de LGBMHist20261004225654: media $88.430.400 y desviacion entre semillas $3.289.100 en el publico de agosto. Media inferior a TabPFN ($92.262.500) por $3.832.100 (-4,15%). No permite afirmar significacion estadistica ni conocer el privado. Junio medio $348.150.000: su 25% es $87.037.500, cercano al publico observado (+1,60%).

Entregas archivadas en `tp_primera_entrega/salidas/01_entregas_bot/`, con prefijos 1_ y 2_. Respuesta guardada en la segunda carpeta como `RESULTADO_BOT.txt`. No se cambiaron parametros ni se eligio entrega definitiva.
## 42. Ensemble exploratorio en junio - 2026-10-05

Se registro stacking LightGBM -> TabPFN como idea pendiente en `tp_primera_entrega/NEXT_STEPS_IDEAS.md`, sin ejecutar API. A pedido de Tomas se creo y ejecuto `16_ensemble_junio.py`: 20 semillas LightGBM con configuracion congelada, train abril/mayo; TabPFN historico guardado, train marzo/abril. Junio completo, 164.114 clientes. Sin tuning ni API. Mezclas fijas 50/50 de probabilidades y de rankings; cortes previos 8500 y 9953, sin buscar maximo en junio. Targets distintos, bajas en LightGBM y BAJA+2 en TabPFN; protocolos de entrenamiento distintos.

A 9953 contactos: TabPFN $380.792.500, LightGBM promedio $387.392.500, mezcla probabilidades $396.192.500, mezcla rankings $398.392.500. A 8500: $369.050.000, $365.750.000, $388.850.000 y $376.750.000 respectivamente. Mezcla probabilidades a 9953 mejora $15.400.000 (+4,04%) frente a TabPFN; rankings $17.600.000 (+4,62%). No seleccionar pesos/corte por este junio expuesto ni interpretar como test independiente.

Verificado: coincide universo/etiquetas, reproduce tres ganancias individuales anteriores de LightGBM y $380.792.500 de TabPFN. Salida: `tp_primera_entrega/salidas/ensemble_junio_20261005_124204/` con manifest, probabilidades de todas las semillas y comparacion. No se genero entrega de agosto ni se envio al bot.
## 43. Tuning LightGBM solo BAJA+2 - 2026-10-05

Tomas pidio tunear primero LightGBM para BAJA+2. Se extendio el script 14 con --target y --solo-seleccion (defaults mantienen ambos targets y flujo completo). Se ejecuto --target baja2 --trials 30 --solo-seleccion. Solo datos hasta mayo: 202 features, CV abril cinco particiones 70/30, top cinco comparados abril -> mayo con tres semillas y grilla de contactos previa 8000..15000. Sin API ni consulta a junio/agosto. No se modificaron features/baseline ni entregas existentes.

Ganador trial 26: 19 hojas, learning_rate 0.005464960369410817, min_data_in_leaf 819, feature_fraction 0.34831495439756677, bagging_fraction 0.7349360668340227, 796 rounds, 8000 contactos. Mayo ganancias $261.800.000, $269.500.000, $261.800.000; media $264.366.666,67 y std muestral $4.445.597,07. Mejora 5,87% sobre BAJA+2 anterior ($249.700.000), pero sigue debajo del target combinado anterior ($275.550.000). Son resultados de seleccion sobre mayo reutilizado, no prueba independiente ni comparacion causal de targets.

Salida `tp_primera_entrega/salidas/lgbm_catedra_hist_20261005_124441/`: estudios, candidatos, parametros, predicciones_mayo.csv y verificacion.json. Recalculadas ganancias desde CSV, 163768 clientes unicos, probabilidades validas. El comando PowerShell reporto exit 1 por stderr informativo de Optuna; el manifest final y la verificacion independiente confirman finalizacion correcta. Pendiente comprobar junio con configuracion congelada y ensemble BAJA+2 + TabPFN; no se generan submits en esta etapa.
## 44. Junio del LightGBM BAJA+2 ajustado - 2026-10-05

A pedido de Tomas, se evaluo la configuracion congelada del tuning BAJA+2 (trial 26, 796 rounds), entrenando abril/mayo con las mismas 20 semillas. Se reutilizaron probabilidades historicas TabPFN de junio. Sin API, sin nuevos pesos/cortes: 50/50 y cortes 8000 (elegido en mayo), 8500 y 9953 (comparaciones previas). Se generalizo el script 16 con --fuente.

A 9953 contactos: TabPFN $380.792.500; LightGBM BAJA+2 promedio $345.592.500; mezcla probabilidades $380.792.500; mezcla rankings $378.592.500. Ensemble anterior con target combinado: LightGBM $387.392.500, mezcla probabilidades $396.192.500, rankings $398.392.500. El nuevo LightGBM pierde $41.800.000 (-10,79%) y su mezcla de probabilidades $15.400.000 (-3,89%) respecto de los anteriores al mismo corte. Igual ganancia mezcla/TabPFN no implica identicos clientes seleccionados.

A 8000 contactos: TabPFN $369.600.000, nuevo LightGBM $323.400.000, mezcla probabilidades $371.800.000, rankings $358.600.000. A 8500: $369.050.000, $331.650.000, $373.450.000, $359.150.000. La mejora seleccionada en mayo no se sostuvo en junio. No demuestra que BAJA+2 sea siempre peor, porque tambien cambiaron parametros/rounds; junio expuesto sigue exploratorio. Se mantienen artefactos anteriores y no se genera submit.

Salida: `tp_primera_entrega/salidas/ensemble_junio_20261005_125848/`, con manifest, CSV probabilidades, comparacion y verificacion independiente. Verificados 164114 clientes unicos, promedio de 20 semillas, mezcla 50/50 y todas las ganancias recalculadas desde CSV.
## 45. Correccion del protocolo: siempre p > 0.025 - 2026-10-05

Tomas establecio siempre umbral 2,5%, no top N, y pidio recalcular y revisar seleccion. Se documento en PROTOCOLO_GANANCIA.md, incluyendo informar total y 25% en conversaciones. Script 14 ahora selecciona candidatos, diagnostica junio y genera agosto con p > 0.025. Script 16 usa por defecto umbral fijo y excluye rankings. Script 15 permanece como reproduccion historica de los envios anteriores. No se sobrescribieron entregas.

Script 17 recalculo junio guardado y reevaluo 15 candidatos existentes (cinco BAJA+2 del primer estudio, cinco combinados, cinco BAJA+2 del estudio ampliado) en mayo con tres semillas. Sin repetir Optuna; sus estudios originales usaron >=0.025 internamente, mientras esta seleccion usa >0.025. BAJA+2 ganador trial 29: media mayo $259.856.666,67, referencia 25% $64.964.166,67. Combinado ganador trial 6: $250.442.500, 25% $62.610.625. Configuraciones congeladas antes de junio; no elegir usando junio.

Junio con 20 semillas y p > 0.025: TabPFN $380.792.500 (25% $95.198.125), 9953 contactos. BAJA+2 LightGBM $321.420.000 (25% $80.355.000), 7792 contactos; mezcla 50/50 $374.935.000 (25% $93.733.750), 8966. Combinado LightGBM $407.495.000 (25% $101.873.750), 12742; mezcla 50/50 $412.747.500 (25% $103.186.875), 11711. Mejora mezcla combinada vs TabPFN $31.955.000, 8,39%. Targets diferentes y train TabPFN marzo/abril vs LightGBM abril/mayo: limitaciones. Junio sigue exploratorio.

Recálculo de configuraciones anteriores con umbral, sin reseleccion: LightGBM combinado $386.952.500 (25% $96.738.125), mezcla $403.342.500 (25% $100.835.625). BAJA+2 trial26 $320.457.500 (25% $80.114.375), mezcla $372.707.500 (25% $93.176.875).

Salida revision `salidas/revision_umbral_20261005_131001/`. Junio nuevo en `ensemble_junio_20261005_131229/` (BAJA+2) y `ensemble_junio_20261005_131355/` (combinado). Script 18 verifico 45 evaluaciones de semillas mayo y ocho resultados junio desde probabilidades, 20 semillas por target, clientes/etiquetas, promedio y mezcla. Sin API, creditos, submits nuevos ni envio al bot.
## 46. Tercera entrega: ensemble con umbral fijo - 2026-10-05

Tomas autorizo preparar tambien agosto. Script 19 entreno LightGBM target combinado trial6 elegido en mayo con p > 0.025, 273 rounds, 20 semillas, train mayo/junio; promedio mezclado 50/50 con las probabilidades TabPFN guardadas de la primera entrega. Sin API ni creditos. Agosto 164647 clientes, seleccion estricta p > 0.025: 12083 contactos.

Carpeta `tp_primera_entrega/salidas/01_entregas_bot/3_EnsembleHist_20261005_131953/`; adjunto `EnsembleHist_20261005_131953.csv`, mensaje `submit EnsembleHist_20261005_131953`. Manifest, probabilidades de todas las semillas, hashes y verificacion guardados. Verificacion independiente: promedio de 20 semillas, mezcla 50/50, IDs enteros unicos, pertenencia a agosto, sin encabezado/indice y seleccion exactamente equivalente a p > 0.025.

Referencia junio: total $412.747.500 y 25% $103.186.875; no garantiza ganancia de agosto. No enviado al bot desde esta sesion ni respuesta publica conocida.
## 47. Respuesta publica del ensemble 50/50 - 2026-10-05

Tomas informo Public gain mean 93.5825, std dev 0.0000 para la tercera entrega EnsembleHist_20261005_131953. Equivale a $93.582.500 publicos; un archivo, 12083 contactos. Submission ID no informado. Supera TabPFN ($92.262.500) por $1.320.000 (+1,43%). Es la mayor ganancia publica observada entre las tres entregas, sin afirmar superioridad estadistica ni resultado privado. Std cero corresponde a un unico archivo.

Referencia junio total $412.747.500 y 25% $103.186.875; el publico observado queda 9,31% debajo de esa referencia proporcional. La mejora local no se traslado con igual magnitud al publico de agosto. No permite atribuir diferencia a overfitting por si sola. Resultado guardado en la carpeta 3_ como RESULTADO_BOT.txt. Sin nuevas corridas ni cambios de parametros.
## 48. Correccion supervisada de probabilidades y graficos - 2026-10-05

Tomas autorizo aprender la frecuencia de BAJA+2 a partir de las probabilidades de ambos modelos y graficarla. Script 20 ajusto regresion logistica sobre logit de dos probabilidades, estandarizacion, C=1, sin balanceo ni tuning. Mayo: LightGBM combinado trial6 promedio tres semillas y TabPFN historico guardado; cinco folds estratificados para predicciones OOF del calibrador. Luego ajuste en mayo completo y evaluacion en junio usando 20 semillas LightGBM y TabPFN guardado. Umbral siempre >0.025. No descompone explicitamente la probabilidad de BAJA+1; aprende una combinacion para BAJA+2.

Mayo OOF calibrador: ganancia $261.360.000, 25% $65.340.000; promedio $258.747.500, 25% $64.686.875. Mayo ya se uso para seleccionar modelos base, por lo que OOF del calibrador no elimina el sesgo de seleccion previo.

Junio promedio: 11711 contactos, 668 TP, 11043 FP, total $412.747.500, 25% $103.186.875. Correccion: 7643 contactos, 538 TP, 7105 FP, total $381.617.500, 25% $95.404.375. Reduccion neta de 3938 FP y 130 TP; ganancia baja $31.130.000 (-7,54%). Mejora Brier/log loss ligeramente pero no ganancia; no recomendar reemplazar tercera entrega por este modelo. Cambio temporal y numero de semillas entre mayo/junio son limitaciones; junio expuesto sigue exploratorio.

Salida `salidas/calibracion_20261005_133516/`: calibrador.joblib, probabilidades mayo/junio, comparacion, manifest, bins y graficos calibracion.png y dos_senales.png. Graficos inspeccionados visualmente; verificacion independiente del calibrador guardado y ganancias junio desde CSV completa. Sin API, creditos ni nueva entrega al bot.
## 49. Experimento separado de umbrales - 2026-10-05

Tomas autorizo explorar ganancia vs umbral en mayo y comprobar junio. Script 21 calculo todos los cortes empiricos, agrupando empates, operador >; eligio exclusivamente en mayo (OOF del calibrador para corregida) y guardo cortes antes de leer junio. No modifica protocolo fijo ni entregas. Grafico detalle 1%-5%, maximo calculado en rango completo.

Promedio 50/50: corte mayo 3,1188% aprox, total mayo $276.732.500, 25% $69.183.125. Junio corte congelado: 9735 contactos, 620 TP, 9115 FP, total $414.287.500, 25% $103.571.875; fijo 2,5%: $412.747.500 y 25% $103.186.875. Mejora $1.540.000 (+0,37%); 1928 FP menos y 48 TP menos.

Correccion: corte mayo 2,1143% aprox, total mayo $278.465.000, 25% $69.616.250. Junio: 9450 contactos, 611 TP, 8839 FP, total $412.225.000, 25% $103.056.250; fijo 2,5% $381.617.500 y 25% $95.404.375. Corte empirico mejora corregida pero queda cerca/debajo del promedio fijo. No calcular ni elegir maximo de junio. Mayo reutilizado y maximizacion sobre muchos cortes optimista; junio exploratorio, mejora pequena no demuestra superioridad general.

Salida final `salidas/umbrales_20261005_134305/`, curvas completas CSV, comparacion, manifest y grafico ganancia_umbrales_mayo.png inspeccionado. Primera salida 134235 conserva resultados identicos y grafico inicial sustituido visualmente por zoom en salida final. Sin creditos ni nuevos submits.
## 50. Alineacion temporal de LightGBM con TabPFN en junio - 2026-10-05

Tomas autorizo el primer paso propuesto: alinear entrenamiento. Se actualizo script16 con --train-meses, por defecto marzo/abril. Se ejecuto fuente revision_umbral/bajas (target combinado trial6, 273 rounds), mismas 20 semillas, 202 features, peso 50/50 y p > 0.025, sin tuning. Entrenamiento 326184 filas marzo/abril, igual que TabPFN guardado. Mayo tiene target excluido en SQL y solo aporta historia auxiliar; marzo conservado sin febrero. Permanece limitacion de historia desigual entre train/evaluacion y seleccion retrospectiva en mayo ya expuesto.

Junio alineado: TabPFN 9953 contactos, 595 TP, 9358 FP, ganancia $380.792.500 (25% $95.198.125). LightGBM 12674 contactos, 683 TP, 11991 FP, $402.765.000 (25% $100.691.250). Mezcla 11714 contactos, 668 TP, 11046 FP, $412.665.000 (25% $103.166.250).

Frente a referencia abril/mayo: LightGBM anterior $407.495.000 (25% $101.873.750), caida $4.730.000 (-1,16%). Mezcla anterior $412.747.500 (25% $103.186.875), caida $82.500 (-0,02%), igual cantidad TP y tres FP netos adicionales. La estabilidad del agregado no implica mismos clientes. Mezcla alineada supera TabPFN por $31.872.500 (+8,37%). No prueba generalizacion independiente, junio reutilizado.

Salida `salidas/ensemble_junio_20261005_134901/`. Verificacion independiente de 20 probabilidades, promedio, mezcla, ganancias y entrenamiento registrado completa. Actualizado PROTOCOLO_GANANCIA.md. Sin API ni creditos; no se toca tercera entrega, que ya entrenaba ambos modelos con mayo/junio para agosto.
## 51. Features de interrupcion y caida conjunta; trabajo local desatendido - 2026-10-05

Tomas autorizo avanzar desatendido con el paso 2 y consulto permisos. Se explico que la preparacion, entrenamiento y comprobacion local no requiere permisos adicionales. Sin agentes delegados, API ni mensajes externos.

Se creo features_abandono.py independiente, conservando features.py/baseline.py y hashes. Bloque completo de 13 columnas: ocho transiciones positivo -> cero (actividad/canales/consumos/haberes), reduccion de productos, conteo/fraccion de siete actividades en caida, conteo de tres frentes y caida simultanea. Estricto mes calendario, NaN si fuentes desconocidas; no usa targets. Pruebas sinteticas verifican huecos, ceros/faltantes e independencia de futuros cambios. Tendencias de dos caidas pendientes: train marzo/abril no tiene ejemplos con dos meses previos observables.

Script22 comparo target combinado trial6, 273 rounds, mismos parametros, 3 semillas abril->mayo y 20 semillas marzo/abril->junio; TabPFN fijo y mezcla 50/50 p >0.025. Control de una semilla por etapa reprodujo probabilidades guardadas. Mayo base mezcla $258.747.500 (25% $64.686.875), bloque completo $254.787.500 (25% $63.696.875). Junio base $412.665.000 (25% $103.166.250), bloque completo $420.475.000 (25% $105.118.750). Resultado mixto, no elegir solo por junio.

Script23 comparo familias en mayo: haberes sola $271.892.500 (25% $67.973.125), actividades a cero $260.425.000 (25% $65.106.250), caidas conjuntas $269.005.000 (25% $67.251.250). Elegida exclusivamente en mayo: abandono_pasa_a_cero_mpayroll (previo positivo y actual cero), total203features. Luego script22 comprobo junio20semillas: LightGBM $410.905.000 (25% $102.726.250), mezcla $416.735.000 (25% $104.183.750), 11686 contactos, 671TP, 11015FP. Respecto control mezcla +$4.070.000 (+0,986%), 3TP mas y31FP menos; mayo +5,08%. No prueba significacion ni causalidad: modelos base seleccionados en mayo reutilizado, junio expuesto, nuevas columnas tambien cambian muestreo de variables.

Salidas bloque completo `salidas/abandono_20261005_145518/`, familias mayo `salidas/abandono_familias_20261005_150004/`, haberes junio `salidas/abandono_20261005_150102/`. Script24 verifico 33 resultados bloque completo y25 haberes desde CSV; familias seis resultados verificados aparte. Informe en carpeta familias como INFORME.md y reglas en VARIABLES_ABANDONO.md.

Se generalizo script19 con --abandono-manifest y preparo candidato local agosto: train mayo/junio, 20semillas LightGBM203features, mezcla con TabPFN guardado, p >0.025. Carpeta `salidas/candidatos_pendientes/EnsembleHaberes_20261005_155145/`, CSV y mensaje `submit EnsembleHaberes_20261005_155145`, 12089 contactos. Verificacion independiente de mezcla, IDs unicos, claves agosto, probabilidades, umbral y hash. No se envio al bot; no se numeró como entrega efectuada ni se modificaron entregas existentes. Ganancia agosto desconocida; referencia junio total $416.735.000 y25% $104.183.750.
## 52. TabPFN con senal de haberes: preparado, API bloqueada - 2026-10-05

Tomas pidio agregar TabPFN con nuevos features y consumir creditos de ser necesario. Se preparo script25 para Fast v3.5, dos estimadores, seed214363, 203features (202previas + senal de haberes elegida en mayo), sin muestreo. Desarrollo abril->mayo (163284/163768 filas); junio marzo/abril->junio (326184/164114), mezcla50/50 y p>0.025. Reutiliza controles202features y LightGBM203 de ambas etapas; compara cruces para aislar aporte de cada modelo. Preparacion local verificada, salida `salidas/tabpfn_haberes_20261005_155707/`.

Se intento ejecutar con credencial DPAPI en memoria (sin mostrarla) y cotizacion/cuota antes de inferencia. Revision automatica rechazo la accion antes de crear el proceso: exige autorizacion explicita del payload (variables y etiquetas de clientes) y destino PriorLabs, mas alla de autorizacion para probar TabPFN/consumir creditos. No se ejecutaron llamadas API ni se consumieron creditos. No se intento eludir el bloqueo. Pendiente confirmacion explicita del usuario para subir203features, etiquetas de entrenamiento y variables de evaluacion de estas dos etapas a API PriorLabs.
## 53. TabPFN203 con haberes: API autorizada y completa - 2026-10-05

Tomas confirmo explicitamente enviar a PriorLabs203variables y etiquetas BAJA+2 de entrenamiento, con variables de evaluacion, para abril->mayo y marzo/abril->junio, consumiendo creditos cotizados. Revision aprobo ejecucion tras esa confirmacion. Credencial DPAPI cargada solo en memoria y retirada del proceso al terminar, sin imprimirla.

Script25 ejecuto Fastv3.5, dos estimadores, seed214363,203features incluyendo abandono_pasa_a_cero_mpayroll, sin muestreo; umbral >0.025. Una inferencia por etapa, reutilizando controles202features y LightGBM existentes. Cuota antes867892/20000000; cotizacion114874creditos; cuota despues982766; consumo real114874; saldo19017234.

Mayo TabPFN base $251.267.500 (25% $62.816.875), nuevo $233.970.000 (25% $58.492.500). Mezcla base/base $258.747.500 (25% $64.686.875); Tabbase+LGBhaberes $271.892.500 (25% $67.973.125); Tabnuevo+LGBbase $258.307.500 (25% $64.576.875); ambos nuevos $267.602.500 (25% $66.900.625). Agregar columna a TabPFN empeora mayo; no elegir nueva configuracion por junio.

Junio TabPFN base9953contactos,595TP,9358FP,$380.792.500 (25% $95.198.125); nuevo9830contactos,601TP,9229FP,$390.775.000 (25% $97.693.750). Mezcla base/base11714contactos,$412.665.000 (25% $103.166.250); Tabbase+LGBhaberes11686contactos,671TP,11015FP,$416.735.000 (25% $104.183.750); Tabnuevo+LGBbase11611contactos,$414.397.500 (25% $103.599.375); ambos nuevos11605contactos,672TP,10933FP,$420.062.500 (25% $105.015.625). Mejora ambos nuevos vs soloLGBhaberes $3.327.500 (+0,798%), pero resultado mayo contradictorio; no reemplazo automatico del candidato pendiente elegido en mayo.

Salida `salidas/tabpfn_haberes_20261005_160810/`: manifest, matrices predichas mayo/junio y comparacion. Script26 verifico12comparaciones desde CSV, claves/etiquetas,probabilidades,mezclas y consumo real. Preparacion previa bloqueada queda como antecedente, resuelta por autorizacion explicita y esta corrida completa. Sin agosto adicional ni envio al bot. Mayo/junio reutilizados: exploratorio.
## 54. Cuarta entrega: haberes LightGBM + TabPFN anterior, empate publico - 2026-10-05

**CORRECCION:** Tomas aclaro despues que habia adjuntado el archivo anterior. El resultado $93.582.500 de esta entrada no corresponde a la cuarta entrega y el empate queda invalidado. Resultado correcto de la cuarta entrega: $93.390.000, registrado en la entrada 55. Se conserva el relato inicial como antecedente.

Tomas informo Public gain mean93.5825, std0.0000 al probar EnsembleHaberes_20261005_155145. Publico $93.582.500: empate exacto reportado con tercera entrega. Submission ID no informado. Una lista de12089contactos; seis mas netos que tercera. Comparacion CSV confirmo11792clientes comunes,297entran,291salen: no son listas identicas. Igual ganancia no implica igual cantidad de aciertos/contactos en publico, ni mismo privado. No evidencia mejora publica de esta feature en esta prueba.

Por instruccion previa de archivar entregas enviadas con numeracion, se movio carpeta de candidatos_pendientes a `salidas/01_entregas_bot/4_EnsembleHaberes_20261005_155145/`, sin cambiar CSV/probabilidades. Respuesta guardada RESULTADO_BOT.txt. Referencia junio total $416.735.000 y25% $104.183.750. No nuevas corridas, creditos ni eleccion definitiva entre tercero/cuarto.

## 55. Cuarta entrega: respuesta correcta y correccion del empate - 2026-10-05

Tomas aclaro que el supuesto empate93.5825 correspondia al archivo anterior adjuntado por error; se invalida su atribucion a la cuarta entrega (entrada54 anotada como corregida). Tras probar el CSV correcto, informo Public gain mean93.3900, std0.0000, equivalente a $93.390.000 para EnsembleHaberes_20261005_155145. Submission ID no informado.

Tercera entrega $93.582.500: cuarta pierde $192.500 (-0,206%). La mejora local de la senal de haberes no se sostuvo en este publico. Junio cuarta total $416.735.000 y25% $104.183.750. Diferencia publica pequena, no prueba significacion ni superioridad privada. Tercera sigue como mejor puntaje publico observado. RESULTADO_BOT.txt de carpeta4 actualizado con resultado correcto y aclaracion historica. Sin nuevas corridas ni creditos.
## 56. Stacking LightGBM -> TabPFN: preparado, API bloqueada - 2026-10-05

Tomas pidio ejecutar stacking. Se crearon scripts27_preparar_stacking.py y28_ejecutar_stacking.py. LightGBM combinado trial6 congelado,202features sin haberes; nueva feature p_lightgbm_oof. Cinco grupos por cliente, tres semillas originales por grupo. Cada prediccion OOF excluye todas las filas del cliente; para marzo no usa abril. Desarrollo trainabril/evalmayo; comprobacion trainmarzo+abril/evaljunio.45modelosOOF en total. Validacion usa promedio de tres modelos fit completo; un control full-fit por etapa reprodujo el CSV anterior. Se conserva mezcla con20semillas como referencia adicional, sin confundirla con la nueva columna de3semillas.

OOF interno es retrospectivo con etiquetas de otros clientes del mismo mes, no backtest prospectivo fila a fila. Parametros LightGBM previamente seleccionados en mayo; mayo/junio reutilizados. OOF train usa80%clientes y eval100%, diferencia de cobertura y distribucion documentada. Sin ajuste de pesos/corte: sigue p>0.025.

Preparacion `salidas/stacking_preparado_20261005_163123/`, con CSV OOF train y evaluacion, cache de modelos/predicciones por fold (archivos.npy son predicciones, no pesos), auditoria de grupos/meses, hashes y versiones. Verificacion independiente:489468filas OOF entre etapas, un fold por cliente, medias de semillas reproducidas, cobertura completa, ningun mes posterior en el fit interno. Entradas API verificadas por script28, 203columnas, sin ID/foto_mes como features, ni etiquetas de evaluacion enviadas.

Solicitud de ejecucion API rechazada por revision automatica antes de crear proceso: requiere autorizacion explicita para nuevo payload derivado, la probabilidad OOF de LightGBM, aunque el usuario pidio stacking y antes autorizo PriorLabs. No se intento eludir. No cotizaciones ni inferencias ejecutadas, creditos cero. Preparacion local API `salidas/stacking_tabpfn_20261005_163553/` marcada bloqueada. Pendiente confirmacion del usuario de envio a PriorLabs de202features+probabilidadOOF y etiquetasBAJA+2 de train para abril->mayo y marzo/abril->junio. Tope local250000creditos y consulta/cuota/cotizacion previstas antes de inferir. Sin agosto ni submit.

## 57. Stacking autorizado en PriorLabs, completo y verificado - 2026-10-05

Tomas confirmo "si, enviar" a la solicitud explicita de envio a PriorLabs de 202 variables + probabilidad derivada OOF LightGBM y etiquetas BAJA+2 de train, con variables de evaluacion, para abril->mayo y marzo/abril->junio. Revision automatica aprobo ejecucion tras confirmacion. Credencial DPAPI cargada solo en memoria y retirada al terminar, sin imprimirla. Cotizacion total 114874 creditos, bajo tope autorizado 250000; consumo real 114874. Uso antes 982766, despues 1097640 de 20000000; saldo 18902360.

Script28 ejecuto TabPFN v3.5-fast, dos estimadores, seed214363, 203 columnas, sin muestreo. La nueva columna proviene de LightGBM combinado trial6,273 rondas, tres semillas y cinco folds por cliente, preparado en entrada56. Umbral fijo p>0.025, sin ajuste de pesos/corte, sin haberes ni limpieza de columnas. Probabilidades pagadas guardadas antes de calcular comparaciones.

Mayo TabPFN solo:9143 contactos,457TP,8686FP,$251.267.500 (25% $62.816.875). Mezcla 50/50 tres semillas (igual a referencia mayo):10631 contactos,501TP,10130FP,$258.747.500 (25% $64.686.875). Stacking:9546 contactos,481TP,9065FP,$266.585.000 (25% $66.646.250). Mejora stacking vs mezcla $7.837.500 (25% $1.959.375),+3,03%; pierde20TP y evita1065FP.

Junio TabPFN solo:9953 contactos,595TP,9358FP,$380.792.500 (25% $95.198.125). Mezcla tres semillas:11632 contactos,669TP,10963FP,$416.020.000 (25% $104.005.000). Mezcla referencia20semillas:11714 contactos,668TP,11046FP,$412.665.000 (25% $103.166.250). Stacking:8327 contactos,549TP,7778FP,$374.907.500 (25% $93.726.875). Stacking pierde $37.757.500 (25% $9.439.375),-9,15%, frente a referencia; pierde119TP y evita3268FP. Frente a mezcla mismas tres semillas pierde $41.112.500 (25% $10.278.125),-9,88%. Menos falsos positivos no compensa premios perdidos. Resultado mayo no se sostiene en junio: no promover a nueva entrega. La mejora tres vs veinte semillas en junio tampoco se elige automaticamente por mes reutilizado.

Salida `salidas/stacking_tabpfn_20261005_163829/`: manifest completo, predicciones mayo/junio, comparacion, verificacion.json, INFORME.md y comparacion_ganancia.png. Script29 verifico ocho comparaciones desde CSV, ganancias y25%, promedios, claves/probabilidades, auditoria OOF y consumo real. NEXT_STEPS_IDEAS.md registra experimento ejecutado y limpieza historicas pendiente. Limitaciones OOF retrospectivo,80% vs100%clientes, historia desigual, parametros seleccionados previamente en mayo y meses reutilizados permanecen documentadas. Sin agosto ni envio al Bot; entrega3 sigue mejor publico observado.

## 58. LightGBM local, objetivo publico100millones y nuevas particiones - 2026-10-05

Tomas cuestiono validacion unica en junio por aguinaldo, pidio pausar TabPFN y avanzar con LightGBM/otro modelo abierto. Confirmo explicitamente que el corte es $100.000.000 en el25% publico del Bot, para domingo11deoctubre. Referencia local equivalente total $400.000.000,25% $100.000.000, sin garantia de agosto. Sin llamadas API ni creditos.

Inventario recalculado del CSV: etiquetas completas marzo-junio; julio1103BAJA+1 y163245desconocidas; agosto164647desconocidas. Mediana mpayroll>0 mayo105773,49,junio156529,81,julio117300,agosto119223,96. Salto junio/mayo aproximado48%, consistente con preocupacion estacional pero no prueba causal. No se elimina junio automaticamente de train.

Config nueva `config_validacion_lightgbm.json` y PROTOCOLO_GANANCIA.md actualizado. Desarrollo cuatro grupos fijos por cliente, seed214363, evaluar abril y mayo por separado. Fit usa marzo hasta el mismo mes evaluado de otros grupos; excluye todas las filas del cliente evaluado y ningun mes posterior. CV retrospectivo, no backtest prospectivo. Control temporal marzo->mayo con dos meses de distancia; abril->mayo solo control retrospectivo de un mes. Junio prueba de estres, no criterio unico de seleccion. Mayo reutilizado/marzo sin febrero impiden reclamar test independiente.

Script30 piloto congelado,202features, una semilla189293, targetBAJA+2 trial29/192rondas y combinado trial6/273rondas,20fits, p>0.025. CVabril BAJA+2:9474contactos,713TP,8761FP,$523.765.000 (25% $130.941.250); combinado12668contactos,776TP,11892FP,$505.230.000 (25% $126.307.500). CVmayo BAJA+2:8353contactos,452TP,7901FP,$267.492.500 (25% $66.873.125); combinado13395contactos,563TP,12832FP,$250.937.500 (25% $62.734.375). Temporalmarzo->mayo BAJA+2:$245.905.000 (25% $61.476.250),8258contactos; combinado:$232.622.500 (25% $58.155.625),12061contactos. Retrospectivoabril->mayo BAJA+2:$259.242.500 (25% $64.810.625),9013contactos; combinado:$243.347.500 (25% $60.836.875),11591contactos. BAJA+2 mejor en piloto, sin promocion por una semilla ni por ganancia altaabril. Cambiar split no garantiza mejora del Bot.

Salida `salidas/validacion_lgbm_20261005_190758/`, CSV particiones/predicciones/comparacion/detalles,manifest,verificacion,INFORME.md,grafico. Script31 verifico8comparaciones,16folds,clientes disjuntos,fit sin meses posteriores,probabilidades/medias,ganancias y25%,hashes. Dispersión de folds no se presenta como intervalo independiente por entrenamiento solapado. Referencia metodologica documentacion primaria scikit-learn sobre grupos y tiempo.

Script32 preparo referencia local LightGBM puro sin entrenar: extrae promedio20semillas guardadas de tercera entrega, sin usar columnaTabPFN. Config combinado trial6,202features,trainmayo+junio,p>0.025; candidato `salidas/candidatos_pendientes/LightGBMHistSolo_20261005_191202/`,13454contactos. Ganancia referenciajunio recalculada:$402.765.000,25% $100.691.250,12674contactos; agosto desconocida. No ganador nuevoCV ni garantia superar corte publico. Verificacion independienteIDs,umbral,hash,promedio y gananciasjunio. Mensaje manual `submit LightGBMHistSolo_20261005_191202`. Sin envio ni numeracion como entregaefectuada. Conservadas entregas1-4. TabPFN pausado, prioridad siguiente tuning LightGBM varias particiones/semillas, limpieza/normalizacion estacional y ventanas/pesos de train.

## 59. Reentrenamiento LightGBM con historicas y haberes, nuevas particiones - 2026-10-05

Tomas pidio reentrenar con las nuevas particiones, historicas y el otro feature anterior. Se identifico como abandono_pasa_a_cero_mpayroll: haberes positivos el mes calendario anterior y cero actual; faltantes se mantienen NaN. Configuracion solicitada203variables (152originales+50historicas+senalhaberes); control202. Script33 conserva parametros BAJA+2 trial29/192rondas y combinado trial6/273rondas, umbral p>0.025. No se hizo Optuna ni ajuste de corte. Tres semillas comunes189293,107584,408287. Se reutilizo la primera semilla del piloto202 tras verificar archivos,orden,claves/labels y grupos;20fits previos reutilizados,100fits nuevos de validacion y20finales (120entrenamientos nuevos).

Particiones exactamente las del piloto: cuatro grupos fijos por cliente; CVabril trainmarzo+abril de los otros grupos, CVmayo trainmarzo+abril+mayo; exclusion de todas las filas del cliente evaluado y ningun mes posterior en fit. Control marzo->mayo dos meses; abril->mayo retrospectivo un mes. Junio no usado para elegir configuracion. CV retrospectivo,mayo reutilizado,parametros antes seleccionados en mayo; no es test independiente ni backtest prospectivo. Marzo sin febrero tiene haberes/historicas no observables: el control marzo->mayo no aprende esa nueva senal. Cambiar202 a203 tambien cambia muestreo de columnas,no atribucion causal exclusiva.

BAJA+2, promedio3: CVabril202=9415contactos,711TP,8704FP,$523.187.500 (25% $130.796.875);203=9387contactos,708TP,8679FP,$520.657.500 (25% $130.164.375),-0,48%. CVmayo202=8346contactos,447TP,7899FP,$262.185.000 (25% $65.546.250);203=8363contactos,453TP,7910FP,$268.317.500 (25% $67.079.375),+2,34%. Diferencia mayo +$6.132.500 total (25% +$1.533.125),6TP y11FP mas. Temporalmarzo->mayo202=8160contactos,$247.500.000 (25% $61.875.000);203=8155contactos,$254.237.500 (25% $63.559.375). Retrospectivoabril->mayo202=9070contactos,$256.575.000 (25% $64.143.750);203=9051contactos,$262.597.500 (25% $65.649.375). Resultado mixto entreabril/mayo,no gran salto demostrado.

Combinado,promedio3: CVabril202=$519.090.000 (25% $129.772.500),12804contactos;203=$519.585.000 (25% $129.896.250),12866contactos. CVmayo202=$260.232.500 (25% $65.058.125),13577contactos;203=$258.060.000 (25% $64.515.000),13576contactos. Temporal202=$230.587.500 (25% $57.646.875),12215contactos;203=$237.022.500 (25% $59.255.625),12061contactos. Retrospectivo202=$259.847.500 (25% $64.961.875),11551contactos;203=$263.945.000 (25% $65.986.250),11562contactos. BAJA+1 siempre cuenta como error; la salida combinada no representa P(BAJA+2).

Salida `salidas/lgbm_haberes_particiones_20261005_191807/`: particiones,featurecruda,16comparaciones promedio,48resultados individuales,32folds,cachepredicciones,manifest,informe y grafico. Script34 verifico ganancias/25%,claves/probabilidades/medias,hashes,grupos,mesesfit y feature recalculada con mpayroll crudo. Script35 genero informe/grafico y cobertura. Sin API ni creditos.

Entrenamiento final solicitado: BAJA+2 con203variables, mismas192rondas,20semillas originales,trainmayo+junio327882filas -> agosto164647. Junio entra solo ahora como fuente de etiquetas final,no seleccion. Candidato `salidas/candidatos_pendientes/LightGBMHaberesBaja2_20261005_192751/`,9447contactos,promedio de probabilidades y p>0.025; CSV y mensaje manual `submit LightGBMHaberesBaja2_20261005_192751`.20modelos guardados y probabilidades por semilla. Verificador reviso todos los modelos,columna/rounds,IDs/universoagosto,umbral/hash y reprodujo semilla107584 desdemodelo+features deagosto. Ganancia agosto desconocida;no garantia100millones publico. No enviado ni numerado como entrega. ReferenciaLightGBMHistSolo previa preservada;entregas1-4 sin cambios. PROTOCOLO/NEXT_STEPS/README actualizados.

## 60. Candidato LightGBM haberes listo para adjuntar al Bot - 2026-10-05

Tomas pidio prepararlo para el Bot. Se creo `adjuntos_bot/` dentro de `salidas/candidatos_pendientes/LightGBMHaberesBaja2_20261005_192751/`, con copia exclusiva del CSV de9447IDs, sin encabezado. Hash verificado contra manifest y archivo original; IDs numericos y unicos, contenido intacto. Mensaje exacto `submit LightGBMHaberesBaja2_20261005_192751` guardado en MENSAJE_ZULIP.txt; instrucciones en PARA_ENVIAR_BOT.txt. Sin entrenamientos nuevos ni API. Pendiente de envio manual por Tomas; no numerado como quinta entrega efectuada ni movido a entregas_bot. Ganancia agosto desconocida.

## 61. Adjuntos de las20semillas LightGBM haberes - 2026-10-05

Tomas consulto conveniencia de subir semillas independientes. Se revisaron resultados individuales de las tres semillas evaluadas: CVmayo haberesBAJA+2 individuales $266.310.000 (25% $66.577.500),$264.247.500 (25% $66.061.875),$266.392.500 (25% $66.598.125),8356/8351/8353contactos respectivamente; promedio3 $268.317.500 (25% $67.079.375),8363contactos. El promedio supera las tres en ese CV, pero no todas las particiones: controlabril->mayo mejor individual $265.540.000 (25% $66.385.000),9024contactos,frente a promedio $262.597.500 (25% $65.649.375),9051contactos. No garantia del futuro ni eleccion de semilla por publico.

Se prepararon20CSV independientes desde p_seed guardadas, cada uno con umbral>0.025, en `salidas/candidatos_pendientes/LightGBMHaberesBaja2_20261005_192751/adjuntos_semillas/`. IDs unicos,numericos,sin encabezados; cada lista coincide exactamente con su probabilidad/umbral. Manifiesto de hashes y resumen de contactos fuera de carpeta de adjuntos. Mensaje `submit LightGBMHaberesBaja2Semillas_20261005_192751` en MENSAJE_SEMILLAS.txt. El CSV promedio20 se conserva aparte en adjuntos_bot,9447contactos. Diferenciar promedio de ganancias de listas individuales de ganancia de una lista por promedio de probabilidades. No asumir computo del cupo diario para lote20; no envio al Bot ni entrenamiento/API/creditos.

## 62. Limite20archivos confirmado y carpeta5 lista para subidas - 2026-10-05

Tomas confirmo que cada corrida del Bot admite hasta20archivos. Se aclararon dos resultados distintos: lote20semillas (media/desvio de ganancias individuales) y unCSVensemble (ganancia de lista por promedio de probabilidades), dos corridas si prueba ambos. Prioridad ensemble, diagnostico semillas adicional.

Tomas pidio ubicacion en directorio de subidas. Se movio el candidato completo desde candidatos_pendientes a `salidas/01_entregas_bot/5_LightGBMHaberesBaja2_20261005_192751/`, tras verificar rutas absolutas dentro del workspace y destino inexistente. Numerado5por organizacion, explicitamente PENDIENTE en ESTADO_ENVIO.txt y manifest: no significa quinta entrega efectuada. Promedio en adjuntos_bot(1CSV/9447contactos), individuales en adjuntos_semillas(20CSV); mensajes preservados. Hashes de todos21adjuntos coinciden con originales, sin reentrenar ni cambiar listas. Ruta del candidato actualizada en manifest del reentrenamiento para verificador; referencias activas README/PROTOCOLO/NEXT_STEPS actualizadas. Sin envio al Bot ni resultados nuevos.

## 63. Seleccion local top5 en curso y resultado del lote20 enviado por Tomas - 2026-10-05

Tomas pidio elegir cinco mejores entre20semillas por ganancia y preparar susCSV. Se declaro antes de evaluar el criterio: ganancia media OOF abril/mayo con pesos50/50, cuatro grupos por cliente, mismas203features/targetBAJA+2/parametros/umbral>0.025. Solo tres semillas tenian esta validacion; script36 reutiliza esas y evalua17restantes (136fits nuevos). Ranking no usa etiquetas/agosto ni junio. Chequeo independiente preparado en script37. Top5 pendiente mientras termina evaluacion.

Durante esa corrida Tomas informo que envio las20semillas al Bot: Public gain mean93.5495,stddev2.3131. Media publica $93.549.500,desvio entre20listas $2.313.100; no dividir por4. SubmissionID no informado. Diferencia frente a tercera entrega50/50 $93.582.500: -$33.000 (-0,035%); media de20listas no es misma metrica que unCSVensemble ni prueba empate privado. Objetivo100millones publico: faltan$6.450.500. Resultado del promedio de probabilidades20 no informado. Respuesta en RESULTADO_BOT_SEMILLAS20.txt y manifest_adjuntos_semillas marcado enviado. Se conserva tarea top5 autorizada: mensaje no cancela pedido previo. Metadatos generales de variantes se reconciliaran al terminar script36 para evitar que proceso sobrescriba estado contemporaneo.

## 64. Top5 de20 semillas por abril/mayo, listo y verificado - 2026-10-05

Script36 completo:17semillas nuevas evaluadas con136fits; reutilizadas3semillas/24fits previos para total20. Mismas203features,BAJA+2trial29/192rondas,cuatro grupos por cliente, p>0.025. Ranking media50/50 de ganancias OOF mensuales completas abril/mayo, desempate mayo yseed. No elegido por el resumen publico ni junio ni etiquetas agosto. Seleccionadas,ordenadas:541440,408476,741961,248865,717444.

Scores de media mensualCV total/25%:541440=$400.455.000/$100.113.750;408476=$399.533.750/$99.883.437,50;741961=$398.048.750/$99.512.187,50;248865=$396.880.000/$99.220.000;717444=$395.862.500/$98.965.625. Media de esas cinco puntuaciones locales total $398.156.000,25% $99.539.000. No ganancia publica: fechas reutilizadas,CVretrospectivo y seleccion maximosentre20 es optimista; futuro desconocido.

Archivos agosto exportados de las mismas20predicciones ya guardadas, cinco listas individuales, en `salidas/01_entregas_bot/5_LightGBMHaberesBaja2_20261005_192751/adjuntos_top5/`,mensaje `submit LightGBMHaberesBaja2Top5_20261005_192751` en MENSAJE_TOP5.txt. No se genera promedio5 ni se reentrena agosto. Fuente completa `salidas/top5_semillas_20261005_194616/`:40ganancias,160folds,OOF20,ranking,manifest,cache,informe yverificacion. Script37 reconstruyo40ganancias/25%,ranking/empates,3semillas previas,grupos/meses de160folds,IDs/agosto/umbral/hash y exactamente cincoCSV. Sin API/creditos. Top5 pendientes de envio; lote20 enviado por Tomas y registrado $93.549.500 publico,std$2.313.100; promedio20 pendiente de resultado. Se reconciliaron manifest/ESTADO_ENVIO por variante tras finalizar proceso para preservar respuesta contemporanea. Modelos y otrosadjuntos preservados.

## 65. Cinco semillas fijas para explorar configuraciones - 2026-10-05

Tomas aprobo mantener las mismas cinco semillas en todas las proximas pruebas:541440,408476,741961,248865,717444. Seleccionadas por ganancia media OOF abril/mayo entre20; registrar sesgo de seleccion, no test independiente. Politica en config_validacion_lightgbm.json y NEXT_STEPS_IDEAS.md. Exploracion con5; confirmacion con20 solo cuando haya una configuracion prometedora. No se reentrenaron modelos ni modificaron CSV/corridas existentes. Umbral p>0.025 y target BAJA+2 preservados.


## 66. Recuperacion de bloques de abandono con cinco semillas - 2026-10-05

Usuario confirmo recuperar actividad a cero y caidas conjuntas. Script38 compara control203, actividad210, caidas207 y ambos214, con BAJA+2/192rondas/parametros congelados/p>0.025 y cinco semillas fijas. CVabril/mayo por cliente identico al control top5 guardado; chequeo marzo->mayo adicional. 140fits nuevos,40predicciones de fitsCV control reutilizadas. Fuente salidas/recuperar_abandono_20261005_202954; primer intento202928 fallo por columnas predict y fue reemplazado tras corregir. Sin API/creditos, junio/agosto ni nuevas entregas.

Control CVabril total $528.742.500/25% $132.185.625; CVmayo $276.402.500/$69.100.625; temporal $249.260.000/$62.315.000. Ambos bloques CVabril $534.490.000/$133.622.500; CVmayo $275.632.500/$68.908.125; temporal $247.390.000/$61.847.500. Actividad y caidas separadas pierden ambos mesesCV; actividad mejora temporal pero marzo sin historia limita atribucion. No mejora consistente: mantener control, no generar submit nuevo. Informe y consistencia por semilla guardados. CVretrospectivo/fechas reutilizadas/seleccion semillas optimista; columnas extras cambian feature_fraction.
Script39 verificado: reconstruccion de60resultados individuales,12ensembles y140fits; control guardado, cache y promedios coinciden. Nota: en marzo->mayo las cinco semillas de ambos bloques mejoran individualmente, pero su lista por promedio de probabilidades pierde; distinguir las dos metricas.


## 67. Ensemble LightGBM BAJA+2 cinco semillas + TabPFN guardado - 2026-10-05

Tomas confirmo permitidoTabPFN y solicito ensemble. Se habilito nuevamente en configuracion. Script40 mezcla50/50 LightGBM203targetBAJA+2trial29/192rondas,5semillasfijas,con TabPFN202Fast2BAJA+2 guardado. Ambos trainfinalmayo/junio->agosto, sin inferencia API/creditos. Se informo reutilizacion y que no se reentreno TabPFN en los nuevos folds. Validacion alineada abril->mayo con5fits nuevosLightGBM; TabPFN guardado mismas filas/train. LightGBM total $258.390.000/25% $64.597.500; TabPFN $251.267.500/$62.816.875; mezcla $253.632.500/$63.408.125. Mezcla pierde total$4.757.500/25%$1.189.375,1,84%. No declarada ganadora; validacion retrospectiva reutilizada, no CVcliente ni testindependiente.

Preparados cincoCSVmezclas individuales (TabPFN compartido) y unCSVmezcla de promedio5 (9815IDs), separados, en salidas/01_entregas_bot/6_EnsembleBaja2TabPFN5_20261005_204425. Numeracion6organizativa,PENDIENTE de envio, no enviado automaticamente. Comandos MENSAJE_SEMILLAS y MENSAJE_PROMEDIO5,manifest/hash/predicciones/modelosvalidacion/informe. Seleccion p>0.025.


## 68. Nueva entrega combinada: junio solo train final - 2026-10-05

Tomas pidio retomar ensembleLightGBMcombinado+TabPFNBAJA+2 y aclaro que junio puede entrar en train, pero no validacion; luego autorizo generar nueva entrega. Script42 restaura targetcombinado,202features originales/historicas sinhaberes,trial6/273rondas,cinco semillasfijas,TabPFN202Fast2BAJA+2guardado,peso50/50,p>0.025. Validacion abril->mayo alineada con5fits locales nuevos; no usa junio para evaluar/seleccionar. Agosto reusa probabilidades guardadas de entrega3 yTabPFN1,ambos mayo/junio->agosto, sin API/creditos ni nuevo entrenamiento final. No nuevoCVporcliente ni tuning; advertido en informe.

Mayo TabPFN total$251.267.500/25%$62.816.875; LightGBMpromedio5 $263.120.000/$65.780.000; mezclapromedio5 $262.212.500/$65.553.125. Cada mezclaindividual supera suLightGBMsemilla, pero promedio5mezcla pierde$907.500/25%$226.875 (0,35%) antepromedioLightGBM. Futurodesconocido; fechas/semillasreutilizadas, no testindependiente.

Preparacion carpeta7_EnsembleCombinadoTabPFN5_20261005_210238 en salidas/01_entregas_bot, PENDIENTEenvio; cincoCSVmezclas individuales en adjuntos_semillas, mensaje submit EnsembleCombinadoTabPFN5_20261005_210238Semillas. Alternativaunica adjuntos_promedio5,12076IDs, separada. No envio automatico; no confundir carpeta6BAJA+2 con7combinado.
Verificador41 completo:13ganancias reconstruidas,6adjuntos exactos,5semillas,modelo541440 reproducido con273rondas/202features. Configuracionjunio actualizada:solo trainfinal,no validacion/seleccion. git diff --check sin errores.


## 69. Resultado Bot entrega7: cinco mezclas combinadas - 2026-10-05

Tomas informo mean93.3240,stddev1.3616 tras subircincoCSVcombinado+TabPFN. Media publica$93.324.000,desvio$1.361.600,SubmissionID no informado. Resultado publico ya corresponde al subconjunto, no dividir por4. Gap a objetivo100millones:$6.676.000. Diferencia ante lote20LightGBMBAJA+2 previo media$93.549.500: -$225.500 (-0,241%); desvio inferior a$2.313.100,pero lotes difieren en target,numero/seleccion de semillas yTabPFN compartido, no comparacion causal ni evidencia de significacion. Frente a ensemble3unCSV$93.582.500:-$258.500; media5listas y unCSVson diferentes metricas. Manifest/ESTADO_ENVIO/RESULTADO_BOT actualizados porvariante;promedio5pendiente. No modelos/CSVmodificados.


## 70. Optuna combinado30trials con5finalistas/5semillas: sin mejora consistente - 2026-10-05

Usuario autorizo optimizacion. Script43 local en entorno .venv existente,Optuna4.9/LightGBM4.7. Datos solo marzo/abril/mayo;202features,sinhaberes,targetBAJA+1/BAJA+2,recompensaBAJA+2,p>0.025. Busqueda30configuraciones conseed541440,cuatrofolds porcliente enabril,fitmarzo/abril excluyendoclientesvalidacion; earlystopping75paciencia/max1000 y roundsmediana. Espacio cincohiperparametros anteriores maslambdaL1/L2. Parametrosanteriores enqueuedcomo trial0. EstudioSQLite yOOFguardados.

Top5porabril trials3/16/12/29/25, evaluadas abril->mayo con5semillasfijas. Ganadora entre nuevasporganancia lista promedio5:trial29,17rondas,68hojas,learning_rate0.03124357146713535,minleaf471,feature_fraction0.802468184123957,bagging_fraction0.8420379364519728,L1 0.3066626971803135,L2 0.6883182822542415. Mayo total$243.347.500/25%$60.836.875,10151contactos,475TP/9676FP; controltrial6/273rounds $263.120.000/$65.780.000,11592contactos,529TP/11063FP. Pierde$19.772.500/25%$4.943.125,7,51%. Ninguna nuevamezcla50/50conTabPFN supera control.

Chequeo marzo->mayo posterior y congelado:control total$235.537.500/25%$58.884.375;trial29 $247.005.000/$61.751.250 (+4,87%), pero marzo sin historia; evidencia contradictoria,no promocion porchequeo. Conservarcontrol; no nuevosCSV/trainfinaljunio/agosto. Total155fits nuevos,0API/creditos. Artefactos salidas/optuna_combinado_20261005_214007,informe/modelos/cache/estudio/seleccion. CVretrospectivo y fechas/semillas reutilizadas, no testindependiente.
Verificador44 completo:30trials/120folds/35resultados individuales y reproduccion del modelo ganador; cero adjuntos nuevos. git diff --check sin errores.


## 71. Ventana abril/mayo->agosto: LightGBM listo, API pendiente aprobacionpayload - 2026-10-05

Tomas autorizo probar abril+mayo->agosto. Script45 prepara ensayo de ventana con5semillasfijas,202features,combinado trial6/273rounds,p>0.025,sin otroscambios. Train327052filas,agosto164647. Cinco fits locales y5CSVsoloLightGBM en carpeta8_EnsembleAbrilMayo5_20261005_220000/adjuntos_lightgbm (12479/12689/12581/12754/12412contactos). Historiaagosto conserva junio/juliosinetiquetas; cambio exclusivamenteventana. Sin validacionlocalposterior apropiada sinjunio,gananciaagostodesconocida.

Para mantenerTabPFNalineado se preparoAPI Fast2BAJA+2 con202variables y etiquetasAprilMay, variablesagosto sinID/mes/target. Se intento llamadaescalada concredencialDPAPIenmemoria,limit150000creditos y cotizacionantesinferencia. Auto_review rechazoaccion antes de proceso: requiere aprobacionexplicita payloadsensible/destinoPriorLabs. No workaround/reintento;0creditos/0API. Ensemble no completo. Trabajo localcompletado,verificador46preparado/reproduccion5modelos. Usuario debe autorizar payload explicito para continuar; no pedir autorizaciongeneralduplicada. ModeloTabPFNprevio mayo/junio no reutilizado para no contaminar comparaciondeventana.


## 72. API autorizada y ventanaabril/mayo->agosto completa - 2026-10-05

Tomas respondio "si,autorizo" al payload202features/etiquetasBAJA+2abril-mayo y featuresagosto aPriorLabs,sinID/mes/labelsagosto,max150000creditos. Revisionaprobollamadaescalada;45reanudo carpeta8,reutilizo5LightGBM,TabPFNFast2BAJA+2train327052abril/mayo->agosto164647. Cotizado74179,consumoreal74179pordiferenciacuotas. CredencialDPAPIenmemoria,envretiradaalterminar;noexpuesta. Bloqueoprevioarchivado/resuelto.

Ensemble50/50/p>0.025 completo. CincoCSV en adjuntos_semillas,contactos11115/11149/11064/11186/11036 en orden541440/408476/741961/248865/717444. Mensaje submit EnsembleAbrilMayo5_20261005_220000_semillas. Promedio5separado11188contactos;cincoLightGBMsoloalternativosconservados. Gananciaagostodesconocida;sintrainJunlabels/sinvalidacionJun;JunJulauxiliareshistoricosconservados. InformecomparacionIDs frente7 ymanifestcuotas/estadoactualizados. PENDIENTEenvio manual, no enviadoautomaticamente. Referenciapublicalote5comparable7:$93.324.000,std$1.361.600.


## 73. Resultado Bot entrega8 abril/mayo - 2026-10-05

Tomas informo94.4185,stddev0.6611. Media publica $94.418.500,desvio $661.100. Frente a lote5 entrega7 mayo/junio $93.324.000/std$1.361.600: mejora $1.094.500 (+1,173%). Mismas cinco semillas,targets/features/hiperparametros/pesos/umbral; cambia ventana de ambos modelos. Desvio menor entre listas de este lote, no evidencia de estabilidad en otros meses ni prueba de significacion sin scores individuales/subconjuntos. Gap al objetivo100millones publico:$5.581.500. No dividir resultados publicos por4. Promedio5probabilidades no evaluado por este resultado; LightGBMsolo tampoco. SubmissionID no informado. Manifest/resultado/ESTADO_ENVIO actualizados porvariante;ningun modelo oCSV modificado.


## 74. Resultado Bot promedio5 entrega8 - 2026-10-05

Tomas informo93.1975,std0. CSV promedio5 de probabilidades enviado: ganancia publica $93.197.500,std0 con un solo archivo. Queda $1.221.000 (-1,293%) debajo de la media de5listas $94.418.500; son estrategias y metricas distintas, no implica que sepamos la mejor semilla individual. Tambien queda $385.000 debajo del anteriorCSVensemble3 $93.582.500. Desvio0 por una sola lista no demuestra ausencia de incertidumbre ni estabilidad. Mejor media registrada sigue lote5abril/mayo $94.418.500; mejor CSVunico informado sigue entrega3 $93.582.500. Para escoger una semilla se requieren scores individuales, no disponibles con el resumen. GapCSVpromedio5 al objetivo publico100millones:$6.802.500. No dividir score publico por4. LightGBMsoloabril/mayo sigue pendiente. SubmissionID no informado. Estado/manifest actualizados porvariante;CSV/modelos intactos.


## 75. Auditoria de errores y bloque de trayectorias: evidencia mixta, candidato9 - 2026-10-05

Tomas acepto auditoria previa yprueba bloque pequeno. Script47auditaMaypred7trainApr:505TP,365FN,10160FP (947BAJA1/9213CONTINUA). FNmedianaactividad63vsTP13,canales3vs1.802/870BAJA2mpayroll0;grupo mpayrollpositivo baja2prevalencia0,076%. Asociaciones,no causalidad. features_trayectorias predefine12features:canalesactivos/perdidos/delta,4ratiosmaxprevio2+coverage,4caidassostenidas2. Solo calendario anterior,no labels,faltantesno0. Marzo/abril/mayo auxpara desarrollo,Junnoeval.

CVmayo4foldcliente,poolAprMay excluyendoclientes,5semillasfijas yparametroscombinados congelados273rondas:control202 total$256.657.500/25%$64.164.375,549TP/12078FP/12627contactos;tray214 $270.545.000/$67.636.250,563TP/12119FP/12682contactos:+5,41%lista promedio5. Mediaindividual $253.451.000/$63.362.750 vs$257.323.000/$64.330.750:+1,53%,4/5mejoran.40fits nuevos,verificador48reproduce40modelos/10scores/2ensembles/clienteexcluido/futura perturbacion. Mesreutilizado/no testtemporal.

Script50chequeoApr->May5fits,sinMaylabelsfit:Lightcontrol$263.120.000/25%$65.780.000 vsnuevo$247.582.500/$61.895.625 (-5,91%);mezclacontrol$262.212.500/$65.553.125 vsnuevo$257.895.000/$64.473.750 (-1,65%). CuatrocaidassostenidasNaNtrainabril,soloMaypuedeaprenderlas;resultadomixto,no promoverautomaticamente.

Script49prepara5LightGBM214AprMay->Aug yTabPFN202reutilizado de8alineado,0API/creditos. Candidato experimental,50/50,p>0.025;movido desdecandidatos_pendientes a01_entregas_bot/9_EnsembleTrayectorias5_20261005_230923 trasverificar rutasabsolutasdentro workspace/destinonuevo. Cincoadjuntos_semillas contactos11059/11227/11040/11047/10965;promedio5separado11100. Verificador51reproduce5modelosfinales y11CSV/hash/sourceTab. Reporte salidas/auditoria_trayectorias_20261005_230058/INFORME.md. Total50fitslocales. PENDIENTE envio;no nuevoenviobot ni reemplazoentrega8.


## 76. Resultado Bot entrega9: trayectorias no mejora - 2026-10-05

Entrega9, cinco mezclas por semilla: Public gain mean 93.5330, std dev 2.0404. Media publica $93.533.000; desvio $2.040.400. Resultado informado por Tomas el 2026-10-05; Submission ID no informado. Frente a entrega8 ($94.418.500 / std $661.100): -$885.500 (-0,938%). Mantener entrega8 como referencia. El score ya es publico; no dividir por cuatro. Promedio5 y LightGBM solo pendientes.
La mejora del CV por cliente en mayo no se traslado al publico; el chequeo temporal abril->mayo ya habia empeorado. No ajustar el bloque solo buscando mejorar el publico. No se conocen scores individuales para inferir significacion o elegir una semilla. CSVs y modelos conservados sin cambios.


## 77. TabPFN214 con trayectorias y ensemble preparado - 2026-10-05

Tomas solicito incorporar las nuevas columnas tambien a TabPFN. Script52 completa entrega10_EnsembleTrayectoriasTabPFN5_20261005_232428: LightGBM214 combinado reutilizado de entrega9, cinco modelos/predicciones reproducidos; TabPFN214 BAJA+2 nuevo, abril+mayo327052->agosto164647, v3.5-fast/2estimadores/seed214363/sin subsampling. API aprobada, credencial en memoria retirada al terminar, sin IDs/mes/labelsagosto en payload. Cotizacion y consumo real76210creditos; cuota acumulada1248029/20millones. Sin nuevos fits LightGBM, sin etiquetasjunio/validacionjunio.

Cinco mezclas50/50,p>0.025: contactos11374/11502/11353/11384/11290 en orden541440/408476/741961/248865/717444. Promedio5 separado11416; LightGBMsolo identico entrega9. Verificador53 reprodujo cinco modelos, matrices/target train, hashes,11CSV y listas exactas. Estado verificado/preparado, pendiente envio manual Bot. Comando submit EnsembleTrayectoriasTabPFN5_20261005_232428_semillas. Comparacion directa entrega9media93.5330/std2.0404; mejor referencia entrega8media94.4185/std0.6611. Ganancia agosto desconocida. Scripts/documentos guardados, modelos anteriores intactos.


## 78. Corte de score exploratorio sin junio: candidato3.3% - 2026-10-05

Usuario autorizo segunda opcion: tratar mezcla como score y explorar corte, flexibilizando regla2.5% solo en este experimento. Script54 usa predicciones202 combinadas50/50 de ambos modelosApril->May guardadas entrega7, cinco semillasfijas. Grilla1%-6% paso0.1pp; elegir centro inferior de banda contigua mas larga a1% del maximo de ganancia media5listas, empate cercania2.5%. Regla fijada antes de leer scores de ganancia. Cuatroparticionescliente aleatorias seed214363: seleccionar con3/4 y comprobar1/4, excluyendo etiquetasclientesreservados. Cortes3.4/3.3/3.3/3.6%; cuatrofolds mejoran.

Media5individuales, sumareservadosMay: fijo2.5%total$258.368.000/25%$64.592.000,10612.8contactos; seleccioncruzada total$268.422.000/25%$67.105.500,8295.2contactos. Diferencia total+$10.054.000/25%+$2.513.500 (+3.89%). Cadafold usa su cortepropio: no es resultado de un unico3.3%. Mayo completo para congelar corte3.3%, banda2.9%-3.8%; cinco semillas mejoran en ajuste aparente. No nuevo testtemporal: mayo/semillas reutilizados y entrenamiento finalAprilMay distintoApril.

Script55 reprodujo cuatroselecciones, verifico que perturbaretique?tasreservadas no cambia corte, y preparo entrega11_EnsembleAbrilMayoCorte33_20261005_233208 sobre probabilidades entrega8 congeladas: modelos202,trainAprilMay,targetscombinado/BAJA2,50/50,solo corte cambia. CincoCSVverificados,contactos8973/9032/8929/9083/8893; reducciones2142/2117/2135/2103/2143. Ceroentrenamiento/API/creditos. Junio/Bot no leidos para elegir. No aplicar automaticamente a entrega10TabPFN214. Pendienteenvio manual,gananciaagostodesconocida. Comando submit EnsembleAbrilMayoCorte33_20261005_233208_semillas. CurvaPNG revisada, INFORME yCSV en salidas/corte_score_20261005_233108. Config politicaexploratoria agregada,umbralreferencia2.5%preservado.


## 79. Resultado Bot corte3.3%: sin mejora - 2026-10-05

Entrega11 corte3.3%: media publica $93.335.000, desvio $1.809.600 (Bot93.3350/std1.8096), cinco CSV. Frente a entrega8 mismos modelos/semillas con corte2.5% ($94.418.500/std$661.100): -$1.083.500 (-1,148%). No promover corte3.3%; mantener entrega8 como referencia. Mejora en mayo no se transfirio al publico de agosto; no demuestra que 2.5% sea optimo universal ni que calibracion no ayude. No buscar cortes sucesivos con el publico. Score ya corresponde al subconjunto publico, no dividir por4. SubmissionID no informado; resultado de entrega10TabPFN214 sigue no informado. Modelos y CSV conservados intactos.


## 80. Resultado Bot entrega10: trayectorias en TabPFN empeora - 2026-10-05

Entrega10, cinco mezclas LightGBM214 + TabPFN214, train abril/mayo, 50/50 y corte2.5%: media publica $91.305.500, desvio $4.299.900 (Bot91.3055/std4.2999). Frente a entrega9 LightGBM214 + TabPFN202 ($93.533.000/std$2.040.400), solo cambia TabPFN: -$2.227.500 (-2,382%). Frente a referencia entrega8 ambos202 ($94.418.500/std$661.100): -$3.113.000 (-3,297%). No promover bloque12trayectorias ni en LightGBM ni TabPFN por estos resultados; conservar entrega8 como referencia. Mayor dispersion de cinco listas en esta muestra, no prueba de significacion ni causalidad general de cada feature. Resultado informado por Tomas; SubmissionID desconocido. Score ya publico, no dividir por4. LightGBMsolo y promedio5 de entrega10 siguen pendientes y no reciben este score. CSVs y modelos intactos.


## 81. Carpeta dedicada para LightGBM solo - 2026-10-05

Se separa LightGBMsolo AprilMay de entrega8 en carpeta dedicada 12_LightGBMAbrilMayo5_20261005_235459. CincoCSV con contenido/hashidentico, modelos202,targetcombinado,corte>2.5%,semillasfijas. Sin nuevosfits/API/creditos. Nuevo comando submit LightGBMAbrilMayo5_20261005_235459_semillas. Pendienteenvio manual y resultado. Fuente/modelos/predicciones preservados; estado8 redirige nueva entrega. Politica solicitada: una carpeta por entrega futura.


## 82. Resultado Bot LightGBM solo entrega12 - 2026-10-06

Entrega12 LightGBM solo, cinco semillas, targetcombinado202, trainabril/mayo y corte2.5%: media publica $91.690.500, desvio $2.100.000 (Bot91.6905/std2.1000). Frente a entrega8 mismos LightGBM mezclados50/50 con TabPFN202 ($94.418.500/std$661.100): LightGBMsolo -$2.728.000 (-2,889%); ensemble +2,975% sobre LightGBMsolo. La mezcla beneficia este lote publico y tiene menor dispersion entre cinco listas; sin scores individuales no prueba significacion ni generalizacion. Mantener entrega8 como referencia. No conocemos ganancia TabPFN solo abril/mayo. Score ya publico, no dividir por4. SubmissionID desconocido. Modelos/CSVs intactos.


## 83. Ventanas LightGBM congeladas: entregas13 y14 preparadas - 2026-10-06

Tomas autorizo continuar comparando ventanas. Script56 congela202variables, targetcombinado BAJA+1/BAJA+2, trial6/273rondas, cincosemillas541440/408476/741961/248865/717444,corte>2.5%. Junio solo train, sin validacion/criterioseleccion. Tresventanaspredefinidas, sin nuevaOptuna/API/creditos. ReferenciaLightGBMsoloAprilMay entrega12 media publica$91.690.500/std$2.100.000; referenciaensemble8$94.418.500/std$661.100 es otra estrategia.

Entrega13_LightGBMMayoJunio5_20261006_000247: prediccionesp_seed reutilizadasde7 yconfirmadas contrafuente3/hash. CincoCSV exclusivosLightGBM,noTabPFN,contactos13411/13190/12983/13384/13212. Comando submit LightGBMMayoJunio5_20261006_000247_semillas.

Entrega14_LightGBMAbrilMayoJunio5_20261006_000247: cincofitsnuevosAprilMayJune->August,modelosguardados/reproducidos ymatrizagostoidentica hashentrega8. Contactos13988/13981/13995/14323/13981. Comando submit LightGBMAbrilMayoJunio5_20261006_000247_semillas. Ningun modelo/archivo anterior alterado.

Ambas entregasverificadas,pendientes envio manual,cincocsv porcorrida separada. No repetir12. Gananciaagostodesconocida,no equivaler mascontactosamayorganancia. Una carpeta porentrega preservada. Estudio salidas/ventanas_lightgbm_20261006_000247 conplanfijado/comparacioncontactos/INFORME. Verificacionfinal10listasexactas/hashes,fuentes,features/params/seeds; cincoreloadsmodelosiguales antesexport; noAuglabels,noJunvalidation. Configpoliticaventanas guardada. No cambiareferencia8ni mezcla conTabPFNdedistintaventana.


## 84. Resultado Bot entrega13 mayo+j??unio - 2026-10-06

Entrega13, LightGBM solo202,targetcombinado, cinco semillasfijas, trainmayo/junio,corte2.5%: media publica $86.922.000, desvio $4.057.700 (Bot86.9220/std4.0577). Contra entrega12 mismos modelos/configuracion excepto ventana abril/mayo ($91.690.500/std$2.100.000): -$4.768.500 (-5,200%), mayor dispersion entre listas. Mantener abril+mayo como referencia LightGBMsolo. No atribuir causalmente al aguinaldo: sustitucion abril por junio y drift/cobertura pueden influir. Falta entrega14 abril+mayo+junio, sin resultado informado. Referenciaensemble8 sigue $94.418.500/std$661.100, estrategia distinta. Score ya publico, no dividir por4. SubmissionID desconocido, CSV/modelos conservados intactos.


## 85. Resultado Bot entrega14 y cierre ventanas - 2026-10-06

Entrega14 LightGBMsolo202,targetcombinado,cincosemillasfijas,trainabril/mayo/junio,corte2.5%: media publica $89.056.000, desvio $3.568.900 (Bot89.0560/std3.5689). Contra entrega12 abril/mayo $91.690.500/std$2.100.000: -$2.634.500 (-2,873%). Contra entrega13 mayo/junio $86.922.000/std$4.057.700: +$2.134.000 (+2,455%). Comparacion de tresventanas cerrada: mejor ventana evaluada LightGBMsolo abril+mayo. Agregar junio no mejora este lote/configuracion; no atribucion causal definitiva al aguinaldo ni generalizacion a otras configuraciones. Referencia general ensemble8 abril/mayo ambos202 50/50 corte2.5% conserva media$94.418.500/std$661.100. No mas busqueda de ventanas contra publico dentro de esta comparacion. SubmissionID desconocido. Score ya publico,no dividir por4. CSV/modelos intactos.


## 86. Validacion local ambos BAJA+2: cambio aislado no mejora - 2026-10-06

Usuario solicita priorizar validacionlocal por escasezsubmits. Script57 ejecuta cambioaislado de targetLightGBMcombinado->BAJA+2,202variables,params/273rondascongelados,cincosemillasfijas,trainabril->evalmayo; TabPFNBAJA+2 guardado misma ventana,50/50,p>0.025. Marzoauxhistoria, noJune/Augdatosleidos, noAPI/creditos, nofinalfit/candidato/submission. CincofitsnuevosLightGBM; cinco controlesguardados reproducidos contra rawMay; cinco nuevossavedmodelsreproducidos.

Media5listas individuales,LightGBMsolo control total$249.810.000/25%$62.452.500 vs BAJA2$200.260.500/$50.065.125. Mezclaactual control total$258.368.000/25%$64.592.000,10612.8contactos,500.2TP/10112.6FP; ambosBAJA2 total$240.757.000/25%$60.189.250,7181.2contactos,398.4TP/6782.8FP. Diferencia total-$17.611.000/25%-$4.402.750 (-6,816%); cero/cincosemillasmejoran, cuatro partesclientesMaytambienpeor. MenosFPpero101.8TPmenos; ahorrocostos insuficiente.

Lista de probabilidadespromedio5,metrica separada: mezclaactual total$262.212.500/25%$65.553.125,10665contactos; nuevo total$241.312.500/$60.328.125,7225contactos. No confundir mediasindividuales/gananciaunicalista ni publicoagosto. Ganancias20individuales+4promedio5 reconstruidas por sumasdirectaspagos; cinco cambioscontactos verifican deltas; partes suman totales. Graficodecomparacionsemillas revisado; INFORME/predicciones/modelos/resultados/hash/verificacion en salidas/validacion_targets_ensemble_20261006_002629.

No preparar submitdeesta configuracion. Parametros provienen del targetcombinado: resultado descarta este cambioaislado, no todas las configuracionesBAJA2. Mayo/semillasreutilizados, April->May no disponibilidadprospectivacompletadelabels: no testtemporalindependiente, no garantiaagosto. Proximaexploracionlocal opcional: parametrospropiosBAJA2, sinBot; noAPI TabPFNtargetcombinadorequerida por este ensayo.


## 87. Regla de promocion: superar control local de entrega8 - 2026-10-06

Tomas establece puerta de promocion: enviar al Bot solo si candidato supera localmente al control de entrega8. Comparaciones deben usar mismas filas/split/semillas/regla/metricas, sin junio validacion; metrica principal media de cinco listas individuales. Control local disponible abril->mayo de configuracion202/combinado+TabBAJA2/50-50: total$258.368.000/25%$64.592.000. No comparar ese total con scorepublico$94.418.500; son evaluaciones distintas. Control local es configuracion de8 reentrenadaApril, no test del modelo finalAprilMay. No submit de candidatos sin mejora local; mejora local tampoco garantiza publica. Regla guardada config_validacion_lightgbm politica_promocion_bot.


## 88. TabPFN combinado local y matriz completa de targets - 2026-10-06

Tomas solicita ambos targetscombinados LightGBM/TabPFN. Script58 preparaApril->May202variables,cincoLightGBMcombinadosguardados/reproducidos,TabPFNFast2seed214363nuevoBAJA1/BAJA2. API aprobada, matrices202abril/mayo sinIDs/mes/labelsMay,payloadtargetcombinadoApril. Estimado/real40736creditos,credencialenmemoria retirada alterminar. Un primerintentoimportMatplotlib fallo antespreparacion/API (priorlabsentorno noMatplotlib); soluciongraficolocal separado,sin nueva instalacion. DatosMarAprilMay solamente,noJun/Aug,0submits.

Amboscombinados mezcla50/50/corte2.5% media5 total$247.885.000/25%$61.971.250,13562contactos,564.4TP/12997.6FP,vscontrol8configApril->May LGBcombinadoTabBAJA2 total$258.368.000/$64.592.000,10612.8contactos,500.2TP/10112.6FP. Delta-$10.483.000/25%-$2.620.750 (-4,057%),1/5semillasmejora. No promover amboscombinados.

Se completa cuarta combinaciongratis con5LightGBMBAJA2 guardados experimento57,misma ventana/202features/params273 y semillas,keys/targets/alineacion/hash verificados. LGBBAJA2+Tabcombinado total$261.684.500/25%$65.421.125,10716.2contactos,505.8TP/10210.4FP; contra control +$3.316.500/25%+$829.125 (+1,284%),5/5semillasmejoran. Deltasporseed541440/408476/741961/248865/717444:990000/4950000/3602500/2585000/4455000. AmbosBAJA2 anterior$240.757.000/$60.189.250. Matriz4targets guardada yvalidada,no pesos/corte ajustados.

Salida salidas/validacion_tabpfn_combinado_20261006_003126, modelosLGBfuentes preservados,predicciones/CSVcomparacion/gr?ficorevisado/verificacion/manifest/INFORME. Gananciasdirectasrecalculadas,20resultadosadicionalesmatriz,metadata payload/checkpoints. GananciaAgostodesconocida/no fitsfinales/candidatosBot en esteensayo. La combinacioninvertida es candidataexploratoria; mejora peque?aenmayo reusado,semillas seleccionadas conAprilMay,no test temporal independiente,nogarantia publica. Soloha cumplidorequisitomejora local en esa comparacion.


## 89. Candidato invertido reservado para ultima hora - 2026-10-06

Tomas pide anotar para hacer a ultima hora la combinacion invertida: LightGBM BAJA+2 + TabPFN BAJA+1/BAJA+2, ambos202variables, trainfinalabril+mayo, cincosemillasfijas, parametrosLGBtrial6/273rondasdelensayo,50/50,corte>2.5%. LocalApril->May media5 total$261.684.500/25%$65.421.125,vscontrol+$3.316.500/25%+$829.125 (+1,284%),5/5mejoran. Pendiente: cincofitsLGBfinales, nuevaAPI TabPFNcombinadoAprilMay->August, cotizacion/limitecreditos, cincoCSV y carpeta numeradaexclusiva/verificacion/comandos. Por instruccion no ejecutar ahora ni programar automaticamente; solo anotado, no preparado/enviado, no consumo adicional. Fuente salidas/validacion_tabpfn_combinado_20261006_003126. Mejora exploratoria en mayo reutilizado,sin garantia publica.


## 90. Tres pruebas CatBoost locales completas y mini informe - 2026-10-06

Usuario autoriza correr trescomparacionesCatBoostlocal ymini informe mientrasduerme. CatBoost1.2.10/graphviz0.21 instalados desdePyPI en .venv proyecto; primerintentosinred falla, escalacioninstalacion aprobada (descarga solo,sin datosclientes). Requirementscatboost fijado1.2.10. Script59: cincoCatBoostBAJA2 trainApril163284/evalMay163768,202variables,trescategoricasVisa_status/Master_status/tcuentas,params800trees/depth6/lr0.05/L2=5/Bernoulli0.8/rsm0.8/CPU4hilos,fijos,sinearlystoppingevalMay. ReusaLightGBMcombinado202 yTabPFNBAJA2control7April->May, mismo controlconfig8. Cortestricto2.5%,5semillasfijas.

Tresvariantesprespecificadas: CatBoostsolo,CatBoost+Tab50/50,LightGBM40/Tab40/Cat20. Son cincofitsnuevos,reutilizadospara3comparaciones,0API/creditos/submits,noJune/Augleidos ni fitsfinales. Medias5listas: control total$258.368.000/25%$64.592.000,10612.8contactos; CatBoostsolo $247.274.500/$61.818.625,8808.2contactos,delta-4.294%,0/5mejoran; Cat+Tab $254.760.000/$63.690.000,8928contactos,delta-1.396%,0/5; tres40/40/20 $261.833.000/$65.458.250,10326.8contactos,delta+$3.465.000/25%+$866.250 (+1.341%),5/5mejoran.

Mezclatres TP496.2/FP9830.6 vscontrol500.2/10112.6: net4TPmenos/282FPmenos. Agregados3.6TP180.2FP;retirados7.6TP462.2FP. Tres/cuatropartesMaymejoran,no mesesindependientes. Stdlocal5listas mezcla$3.175.708 vscontrol$2.684.837. Mayo/semillas reutilizados,nuevoconfigsinOptuna,no pruebaindependiente/nogarantiaBot. No preparar/enviarBotduranteestetrabajo; mezcla pasa requisito local pero pendiente revisionma?ana yCatfinalAprilMay->August. Candidatoinvertidoreservadoultimahora intacto.

Artefactos salidas/catboost_local_20261006_004259,MINI_INFORME.md contabla/conclusion/limites,parametros,cambiosTPFP,costos0. CincoCBM/modelos/predicciones/metricas/hashes/manifest/grafico revisado. Script60 verifica rawmatrices/target+5modelosCBreproducidos,20scores individuales,4listaspromedio5,80partes,20cambiosIDs/pagos,control258368000. Fuente LightGBM5reproducidaen59. Verificacion_independiente.jsonestadoverificado. Politicaconfiglocal actualizada; referenciaspublicas8 intactas. Sin procesosrestantes.


## 91. Revisi?n de papers de churn y propuestas pr?cticas - 2026-10-06

Usuario solicita revisar papers descargados. Encontrados ocho PDF en carpeta hermana DMEyF/Papers: siete trabajos completos y Lariviere solo portada. Extra?dos textos por p?gina y revisadas visualmente siete p?ginas clave; originales preservados/hash verificado. Informe salidas/revision_papers_20261006/REVISION_PAPERS.md; ?ndice/textos/vistas trazables. Lectura de m?todos/resultados/conclusiones relevantes, no de todas las demostraciones/referencias. pypdf6.19.0/pypdfium2 5.14.0 instalados en .venv para lectura/render, descarga autorizada, sin enviar documentos.

Ideas registradas pendientes en NEXT_STEPS: peque?o bloque ocho se?ales de v?nculo recurrente (d?bitos/pagos/pr?stamos/inversiones) con historia calendario de un mes y faltantes desconocidos; dos ablaciones hist?ricas control202?189 (quitar13 res?menes de hasta3meses) y177 (adem?s quitar12 relativos). Cantidades verificadas en manifest7. Distinguir historia de predictores de ventana de etiquetas train. No repetir abandono/canales ni trayectorias rechazadas; no inferir de papers superioridad universal de RF, utilidad de SMOTE o uplift aplicable sin tratamiento/control. CatBoost Optuna propuesta separada, no ejecutada.

Protocolo propuesto soloLGBcombinado nuevo+TabBAJA2 guardado50/50, mismas cinco semillas/corte>0.025/abril?mayo, controlmedia5 total$258.368.000/25%$64.592.000. Junio nunca valida, mayo/semillas reutilizados/no testindependiente. Solo promover si supera control local8. No nuevasfeatures/modelos implementados,0fits/API/cr?ditos/submits; ninguna nueva carpeta numeradaBot; candidato invertido ?ltima hora intacto.


## 92. Revisi?n de scripts de c?tedra y auditor?a descriptiva - 2026-10-06

Usuario solicita revisar indicios en scripts docentes. Inventario/extracci?n fuente24notebooks, lectura detallada secciones pertinentes z402/z701/z601/z0607/z494/z470/z440/z401/CazaTalentos y contrastes con nuestro pipeline. No ejecuci?n notebooks, originales24 hashes preservados; versioneslocales contienen adaptaciones/tareasTH, no atribuir todos los comentarios al profesor. Informe salidas/revision_catedra_20261006/REVISION_CATEDRA.md.

Pista expl?cita z0607 excluye cprestamos_personales/mprestamos_personales por drift; modelos actuales las incluyen. Auditor?a sin extraer etiquetas/filasjunio, diezfeatures abril/mayo/agosto y cinco modelosguardadosApril->May: pr?stamosgain3.556%sumado, no dinero/causalidad. Visa_Finiciomora ceroabril0%,mayo1.967%,agosto1.973%, cambio confirmado causa/significado no confirmado; mora gainbajo0.044% ambas. C?digo auditar_indicios.py y salidas uso/distribuciones/hash trazables. Noevidencia nueva de ganancia.

Ideas pendientes: ablaci?n202->200 quitar solo pr?stamos deLightGBM+Tabguardado; tresrangosmensuales monetarios mpayroll/mcuentas_saldo/mrentabilidad como contextolote sinlabels; revisar nulos/ceros; canaritosdiagn?stico posterior sin trasladarhackpodaRpart aLightGBM. Prioridadantesampliar v?nculos papers a pr?stamos. Advertencias concretasdelectura: PSI notebooknormaliza binsnumericos sinnull ynull sobretotal; rangos no arreglanconceptdrift; ventanasSQLincluyenactual ylagregistro puede saltar meses; funcionesAUC no equivalenganancia; combinadoBAJA1 sigueFP econ?mico. Optuna43 yaincluyeL1/L2.

Mantener pruebasaisladas par?metros/target/semillasfijas5/mezcla50-50/>.025/abril->mayo; controlmedia5 total$258.368.000/25%$64.592.000. Cero nuevosfits/API/cr?ditos/submits/entregasBot. Junio no valida; mayo reutilizado/notestindependiente; candidatoinvertido ?ltimahora preservado; OptunaCatBoost pendiente separado. NEXT_STEPS actualizado.


## 93. Plan consolidado de ideas y primera tanda propuesta - 2026-10-06

Usuario pide anotar todas las ideas y elegir que probar. NEXT_STEPS_IDEAS.md ahora abre con plan vigente consolidado; conserva historial anterior y enlaza revisiones papers/catedra y CatBoost. Estados diferenciados: pruebas pendientes, auditorias realizadas, ensayos ya completos, reservas de menor prioridad, ideas sin datos y candidato invertido reservado ultima hora.

Primera tanda recomendada, no ejecutada: quitar dos prestamos personales LightGBM202->200; agregar tres rangosmensuales202->205; reducir historicas202->189 y202->177. Cuatrovariantes contra control original, cinco semillas=20fits si se autoriza/solicita correr tanda. Cantidadesverificadas contra manifest7, enlacesnuevosvalidos. Misma config/targetcombinado/April->May/TabBAJA2guardado50-50/corte>.025. Cero nuevosfits/API/submits en esta actualizacion.

Registradas ademas vinculosrecurrentes con familiasprestamos separadas, OptunaCatBoost, mora/calidad/PSI, canaritos, ampliarbusquedaLightGBM, objetivoeconomico/MPM, muestreo/pesos/SMOTE, curvaslargas, entropia no replicable, uplift sintratamiento, calibracion/corte yaensayados. CatBoost40-40-20 localtotal$261.833.000/25%$65.458.250 y targetinvertidolocal$261.684.500/25%$65.421.125 permanecen candidatos sin fitfinal. Controltotal$258.368.000/25%$64.592.000; junio no valida,mayo/semillas reutilizados,sin testindependiente. Promocion solo mejora local comparable; mejorpublico8$94.418.500 ya es publico. No entrenamiento nuevo por una pregunta de priorizacion.

## 94. Entrega 15 CatBoost preparada y verificada - 2026-10-06

Tomás autoriza preparar el submit con CatBoost. Cinco nuevos fits CatBoost BAJA+2, abril+mayo 2021 (327.052 filas) para agosto (164.647 clientes), 202 variables incluidas 50 históricas. Conservan parámetros locales: 800 árboles, depth6, lr0,05, L2=5, Bernoulli/subsample0,8, rsm0,8, random_strength1, border_count128, CPU4. Semillas541440/408476/741961/248865/717444. Sin Optuna, early stopping, eval_set ni features nuevas. Una pausa larga en la ejecución no obligó a repetir los cuatro primeros fits guardados.

Reutiliza cinco LightGBM combinados BAJA+1/BAJA+2 y TabPFN BAJA+2 de entrega8, ambos entrenados abril+mayo. Mezcla40/40/20 por semilla, score>.025, no una lista promedio de semillas. Junio no valida; junio/julio solo historia de features; etiquetas extraídas solo abril/mayo. Cero API/créditos, cero fits LGB/Tab nuevos, no envío automático.

Carpeta exclusiva salidas/01_entregas_bot/15_EnsembleCatBoost5_20261006_085026; cinco CSV de IDs sin encabezado en adjuntos_semillas. Contactos por semilla:10542/10600/10524/10633/10464. Mensaje: submit EnsembleCatBoost5_20261006_085026_semillas. Incluye INFORME.md, manifest, modelos, predicciones agosto, cambios de contactos, comando y estado pendiente. No resultado público aún. Referencia pública8 $94.418.500/std$661.100 intacta. Target invertido reservado última hora y tanda de features siguen pendientes.

Promoción respaldada por piloto abril→mayo: control media5 total$258.368.000/25%$64.592.000; candidato$261.833.000/25%$65.458.250, delta+$3.465.000/25%+$866.250,5/5mejoran. Mayo/semillas reutilizados, no test independiente ni garantía pública.

Script61 prepara, script62 reconstruye desde raw matrices float32/categóricas y target, reproduce cinco CatBoost y cinco LightGBM, verifica TabPFN guardado, pesos, corte estricto, IDs/orden/hash de cinco adjuntos y cambios contra8. Verificación final exitosa; se aceptan finales de línea Windows CRLF además de LF. Manifest completo_verificado_preparado_pendiente. NEXT_STEPS y config actualizados; fuentes anteriores preservadas.

## 95. Tanda de features local completada: préstamos, rangos e historia - 2026-10-06

Tomás autoriza seguir con las otras ideas mientras se ausenta. Cuatro variantes aisladas desde control202: sin cprestamos_personales/mprestamos_personales200; tres rangos mensuales205; quitar13 resúmenes de hasta tres meses189; quitar además12 relativos177. Veinte nuevos fits LightGBM, mismas cinco semillas541440/408476/741961/248865/717444, targetcombinado, trial6/273rondas, sin tuning ni early stopping. Abril train163284/mayo eval163768; marzo solo historia sin etiquetas; junio/agosto no leídos. TabPFN BAJA+2 guardado fuente7/controlconfig8, mezcla50/50,corteestricto>.025. Cero API/créditos/submits; no nueva carpeta de entrega Bot.

Media cinco listas (total /25%): control202 $258.368.000/$64.592.000; sin préstamos200 $244.123.000/$61.030.750,delta-$14.245.000/25%-$3.561.250,0/5mejoran; rangos205 $263.549.000/$65.887.250,delta+$5.181.000/25%+$1.295.250,4/5semillas y3/4partes; historia189 $266.420.000/$66.605.000,delta+$8.052.000/25%+$2.013.000 (+3,116%),5/5semillas4/4partes; historia177 $262.042.000/$65.510.500,delta+$3.674.000/25%+$918.500,4/5semillas3/4partes. Mejor189 conserva12variaciones relativas y disponibilidad de un mes; 152originales+37históricas. Retira contador3meses y media/delta_media/conteos3meses de cuatrofuentes,13columnas.

Mejor189 contactos10624/TP507.8/FP10116.2 versuscontrol10612.8/500.2/10112.6: +7.6TP,+3.6FP,+11.2contactos medios. Rangos computados por cada mes completo con rankmedio/nválidos; nulos preservados, ceros/negativos válidos. No etiquetas en features ni combinación automática de cambios. Lista promedio5 separada: controltotal$262.212.500/25%$65.553.125;189total$268.317.500/25%$67.079.375. La métrica primaria sigue media de cinco listas.

Artefactos salidas/features_local_20261006_140702: MINI_INFORME.md y gráfico revisado,20modelos,4prediccionesvariantes+control,25ganancias,100partes,25cambiosIDs y5listaspromedio5. Script63 ejecuta;64 reconstruye datos/modelos y rangos por frecuencias independiente, verifica params TXT usando seis cifras significativas del serializador LGB y predicciones exactas. Verificación exitosa,estado completo_verificado. Script65 genera informe/gráfico. NEXT_STEPS/config actualizados; entrega15 y fuentes preservadas.

Recomendación pendiente de revisión: entrenar LightGBM189 abril+mayo→agosto + TabPFN202 guardado y preparar nueva entrega numerada. No se entrenó final ni se generaron CSVsBot en esta tanda. Combinar189+tresrangos192 aún no probado. Mayo/semillas reutilizados/no test independiente; cobertura histórica de agosto mayor que abril/mayo, no garantía pública ni prueba causal de overfitting. OptunaCatBoost, vínculos recurrentes y target invertido reservado última hora permanecen pendientes.

## 96. Entregas 15 y 16 listas para envío manual separado - 2026-10-06

Tomás pide preparar ambas y esperar resultados para decidir un mix. Entrega15 existente verificada sin reentrenar/modificar modelos ni CSV: hashes/documentos/predicciones/score40-40-20/corte>.025/listasIDs/comando intactos, cinco archivos10542/10600/10524/10633/10464contactos. Mensaje submit EnsembleCatBoost5_20261006_085026_semillas.

Nueva entrega16 salidas/01_entregas_bot/16_EnsembleHist1895_20261006_143235. Cinco LightGBM189 targetBAJA+1/BAJA+2 entrenados abril+mayo327052 para agosto164647. Params trial6/273árboles y semillas541440/408476/741961/248865/717444 congelados. Retira13resúmenes3meses, conserva152originales+37históricas de un mes incluidas12variacionesrelativas y disponibilidad. Mezcla50/50 con TabPFN202 BAJA+2 abril+mayo→agosto guardado de entrega8. Sin CatBoost, rangos nuevos, Optuna ni ajuste de corte. Contactos11037/11243/11103/11189/11154. CincoCSVsinencabezado en adjuntos_semillas, mensaje submit EnsembleHist1895_20261006_143235_semillas.

Script66 prepara/verifica15;67 reconstruye historia de un mes con join calendario independiente, compara matrices/target/modelos/probabilidades/IDs/corte/orden/hashes y confirma15preservada. Verificación final exitosa; modelos273features189 reproducidos5/5. INFORME.md/manifest/predicciones/cambioscontactos/comando/estado/documentación conservados. Solo etiquetasabril/mayo, junio no valida, junio/juliofeaturesaux sin etiquetas; cero API/créditos/submitsautomáticos, cinco fitsLGBnuevos,cero fitsTab/Catnuevos.

Evidencia16 localabril→mayo media5 total$266.420.000/25%$66.605.000 vscontrol$258.368.000/$64.592.000,delta+$8.052.000/25%+$2.013.000,5/5semillas4/4partes. Evidencia15local$261.833.000/25%$65.458.250. Ambas retrospectivas,mayo/semillas reutilizados, nogarantíaagosto, resultadospúblicosdesconocidos. Dos corridasBot separadas con cincoadjuntos por carpeta; usuarioenvía. NEXT_STEPS/config actualizados. Mix189+CatBoost y tuningCatBoost pendientes hasta revisar resultados15/16; no nuevoexperimentoenesteencargo.

## 97. Resultado público entrega15 registrado - 2026-10-06

Tomás informa entrega15 mean93.9895/std2.2615: media pública$93.989.500/desvíoentresemillas$2.261.500,cincoarchivos,submissionIDnoinformado. Frente a referencia8 $94.418.500/std$661.100,delta-$429.000. Faltan$6.010.500paraobjetivopúblico100millones. Estos importes ya corresponden al público25%,no dividir nuevamente ni extrapolar ganancia total agosto. Mejora local15 $261.833.000/25%$65.458.250 no se confirmó frente al control público; mayor variación entre semillas. Agregados no permiten significancia ni comparación pública pareada por semilla.

Manifest15 marcado enviado/resultados_bot,RESULTADO_BOT.json,ESTADO_ENVIO,INFORME,NEXT_STEPS/configactualizados. Manifest/documentosprevios preservados en15/pre_envio para trazabilidad del hash de auditoría de preparación16; modelos/predicciones/CSV15intactos. Entrega16sinresultadoinformado; referencia8permanece mejor. Esperar16antesdecidir mix/tuning; cero nuevosfits/API/submitsporregistro.

## 98. Entrega16 nuevo máximo público registrado - 2026-10-06

Tomás informa entrega16 mean96.9210/std1.7816: media pública$96.921.000/desvíoentresemillas$1.781.600, lote5CSV,submissionIDnoinformado. Nuevo mejor resultado informado; mejora+$2.502.500vs8 y+$2.931.500vs15. Faltan$3.079.000paraobjetivopúblico$100millones. Valores ya del público25%,sinvolveradividir ni extrapolar totalagosto. Mayorstdque8/menorque15; agregados no permiten pareado ni significancia.

Referencia actual LightGBM189 targetcombinado + TabPFN202 BAJA2 al50/50,abril+mayo→agosto,mismas5semillas,score>.025. Control local asociado abril→mayo totalmedio$266.420.000/25%$66.605.000. La reducción13resúmenes3meses mejoró local y este público; no demuestra causalmente overfitting ni garantía de futuros resultados. Modelos/predicciones/CSV16preservados y hashes comprobados. RESULTADO_BOT.json,manifestenviado,ESTADO_ENVIO,INFORME,NEXT_STEPS y configactualizados. Snapshotprevioen16/pre_envio.

Configregistra mejor_publico_registrado16 y mejor_referencia_disponible para futuras comparaciones locales; conserva política original y sus referencias históricas8. Mix189+CatBoost y tuningCatBoost pendientes de decisión/evaluación local, no ejecutados al recibir resultado. Cero nuevosfits/API/submitsautomáticos.

## 99. Mix LightGBM189/TabPFN202/CatBoost202 evaluado localmente - 2026-10-06

Tomás pide probar mixCatBoostcon189. Se aclara alcance: LightGBM189,TabPFN202,CatBoost202, pesos40/40/20; no entrenarCat189 niOptuna. Fuentes verificadas localabril→mayo features_local_20261006_140702/historia_1_mes ycatboost_local_20261006_004259; mismas5semillas,163768filasMay,870BAJA2, igualID/mes/label/parte, mismoTabguardado, corte>.025. Cero fits/API/créditos/submits, noJune/Augleídos, no barrido pesos/corte.

Media5: control16localtotal$266.420.000/25%$66.605.000; mix$269.813.500/25%$67.453.375. Delta+$3.393.500/25%+$848.375 (+1,2737%),4/5semillas3/4partes. Delta por semilla541440+$3.795.000/25%+$948.750;408476+$6.847.500/25%+$1.711.875;741961+$4.867.500/25%+$1.216.875;248865-$467.500/25%-$116.875;717444+$1.925.000/25%+$481.250. Contactos10364.6vs10624 (-259.4),TP504.4vs507.8 (-3.4),FP9860.2vs10116.2 (-256). ReduceFPsuficientesparaganancia+ peseaTPmenos. Desvíolocal$2.727.398vs$4.247.526, no intervalo de confianza.

Lista única promedio5 separada: controltotal$268.317.500/25%$67.079.375,mix$271.150.000/25%$67.787.500, no sustituye media5. Salidas mix_hist189_catboost_20261006_145401 conMINI_INFORME,manifest,probabilidades/scoreMay,10ganancias40partes10cambios2listaspromedio5. Script68ejecuta,69verifica hashesfuente/igualdadclaves/scoresporproducto-matriz y selecciones exactas/gananciasTP-FP/medias/deltas. Estado completo_verificado. Mayo/semillas reutilizados,sin testindependiente,nogarantíaBot. Público mejor16$96.921.000ya del25%.

Mix pasa control16local: candidato pendiente generarCSVfinales/agosto/nuevacarpetaBot desdeprobabilidades15/16 entrenadasAprilMay. No preparado/enviadoactual. CatBoost189 yOptunaseparados pendientes; referencia16no reemplazadaenpúblico. NEXT_STEPS/configactualizados, fuentes15/16 yfuenteslocales preservadas.

## 100. Entrega17 mix189 con CatBoost preparada y verificada - 2026-10-06

Tomás acepta continuar tras ensayo mixlocal. Nueva carpeta17_EnsembleHist189CatBoost5_20261006_145854 en salidas/01_entregas_bot. Mezcla LightGBM189combinado40% + TabPFN202BAJA2 40% + CatBoost202BAJA2 20%, corte>.025,mismas5semillas. Reutiliza exclusivamente probabilidades finales abril+mayo→agosto de16/15,igualdadID/mes/Tab comprobada. CatBoost202800árboles yLightGBM189273árboles intactos; noCat189 niOptuna. No nuevaslecturasdataset/etiquetas, cero nuevosfits/API/créditos/submitsautomáticos.

CincoCSV IDs sin encabezado, orden scoredesc/IDasc y LF, contactos10492/10657/10556/10629/10556. Mensaje submit EnsembleHist189CatBoost5_20261006_145854_semillas. Script70 prepara;71 verifica hashesfuentes/modelos/predicciones/IDsclaves, reconstruye mezcla por producto matricial independiente, umbral/listasexactas, cambioscontactos frente16 y requisito local269813500vs266420000. Estado completo_verificado_preparado_pendiente. Informe,manifest,CSVprobabilidades/cambios,verificación ycomando conservados; fuentes15/16/locales preservadas.

Respaldolocal: totalmix$269.813.500/25%$67.453.375 vs16$266.420.000/$66.605.000,delta+$3.393.500/25%+$848.375,4/5semillas3/4partes. Mayo/semillas reutilizados,nogarantíapública. Mejorpúblico16$96.921.000desvío$1.781.600intacto. Entrega17 pendienteenvíomanual/resultado; NEXT_STEPS/configactualizados. Noexperimentos adicionales.

## 101. Los tres modelos con189 evaluados localmente - 2026-10-06

**Ensayo de los tres modelos con 189 variables completo y verificado:** [mini informe](salidas/todos189_local_20261006_150519/MINI_INFORME.md). Abril → mayo, mismas cinco semillas, pesos LightGBM/TabPFN/CatBoost 40/40/20 y corte >0,025. Total medio $269.632.000; 25% $67.408.000. Delta frente a16: $3.212.000; 25% $803.000. Delta frente al mix17: $-181.500; 25% $-45.375. Cinco CatBoost nuevos y una inferencia TabPFN189 (39,272 créditos); LightGBM reutilizado. Sin Optuna, sin entrenamiento final ni nuevo submit. Entrega17 conservada y postergada por pedido del usuario. Mejor público sigue16: $96.921.000. Mayo reutilizado; no garantiza mejora en agosto.

PriorLabs inicialmente bloqueado por revisión automática antes de crear el proceso, cero créditos. Usuario autorizó explícitamente payload189 de abril con BAJA+2 y mayo sin etiquetas/IDs/mes, máximo80.000 créditos. Cotización y consumo39.272; aprobación registrada. Modelos800árboles de CatBoost y matrices reconstruidos independientemente; 30 ganancias individuales,120 por partes y6 listas de promedio verificadas. No junio/agosto, no etiquetas de mayo en entrenamiento/API. Fuentes y entrega17 preservadas.

## 102. Ocho combinaciones189/202 y seleccion entrega17 - 2026-10-06

**Ocho combinaciones 189/202 completas:** [informe](salidas/combinaciones189_202_20261006_152106/MINI_INFORME.md). Mejor local LightGBM189 + TabPFN202 + CatBoost202 40/40/20: total medio $269.813.500; 25% $67.453.375. Es exactamente la entrega17 existente; sus cinco CSV fueron verificados nuevamente. Elegida para el siguiente envío manual, sin duplicar carpeta, reentrenar ni consumir créditos. Mensaje: `submit EnsembleHist189CatBoost5_20261006_145854_semillas`. Sin resultado público informado. Mayo y semillas reutilizados; selección entre ocho variantes no es test independiente.

Usuario autoriza completar todas las combinaciones y elegir la mejor para el Bot. Script75 evalúa40 listas individuales/160 partes/8 listas promedio desde fuentes guardadas, valida hashes/alineación/selección por producto matricial y reproduce cinco controles previos. Script76 comprueba gananciasTP/FP y medias guardadas. Parámetros,targets,pesos,corte y semillas congelados; cero lecturasdataset/fits/API/créditos/submits. Tres nuevas combinaciones conLGB202 pierden contra17. Script71 vuelve a verificar los cinco adjuntos finales,probabilidades fuente,IDs/orden/corte y hashes. Se conserva17, no se crea18 duplicada. Mejor público sigue16$96.921.000; el envío queda a cargo de Tomás como en las entregas anteriores.

## 103. Corte3,3% de mezcla17 evaluado localmente - 2026-10-06

**Prueba de corte3,3% para mix17 completa:** total medio $273.190.500, 25% $68.297.625; diferencia frente a2,5% $3.377.000, 25% $844.250. Mejora en 4/5 semillas y 2/4 partes. [Informe](salidas/corte33_mix17_20261006_152412/MINI_INFORME.md). Sin fits/API/submits. El3,3% proviene de otra mezcla anterior; no es un optimo probado para17.

Dos cortes fijos solicitados; no optimizacion del corte de esta mezcla. Mayo y semillas reutilizados; no test independiente ni garantia publica.

## 104. Entrega18 mezcla17 corte3,3% preparada - 2026-10-06

Entrega18 corte3,3% preparada/verificada desde17, mismos modelos, cinco CSV. Carpeta tp_primera_entrega\salidas\01_entregas_bot\18_EnsembleHist189CatBoostCorte33_20261006_152510. Mensaje submit EnsembleHist189CatBoostCorte33_20261006_152510_semillas. Cero fits/API/créditos/envíos;17 preservada.

## 105. Optimizacion secuencial corte y pesos mezcla17 - 2026-10-06

**Corte/pesos mezcla17 evaluados:** corte máximo local 3.1% para40/40/20; con ese corte fijo, pesos elegidos (0.4, 0.4, 0.2). [Informe](salidas/corte_pesos_mix17_20261006_152839/MINI_INFORME.md). Delta cruzado frente17 $3.905.000,25% $976.250, 3/4 partes. Entregas17/18 pendientes hasta revisar; cero fits/API/submits.

Mayo y semillas reutilizados, no test temporal independiente. Curvas aparentes optimistas por seleccion. Cruce reserva clientes para seleccionar corte y pesos, pero no elimina reutilizacion historica de mayo. Pesos nuevos mezclan targets distintos; corte optimo de40/40/20 no tiene por que ser optimo de pesos nuevos. No se leyeron junio/agosto ni publico para seleccionar.

## 106. Entrega19 corte3,1% preparada - 2026-10-06

Entrega19 elegida por el usuario:40/40/20,corte3,1%,cincoCSV verificados. Carpeta tp_primera_entrega\salidas\01_entregas_bot\19_EnsembleHist189CatBoostCorte31_20261006_153041; mensaje submit EnsembleHist189CatBoostCorte31_20261006_153041_semillas. Pendiente envío manual;17/18 preservadas, sin fits/API/créditos.

## 107. Resultado publico entrega19 atribuido por contexto - 2026-10-06

**Resultado público atribuido a entrega19:** media $93.659.500, desvío entre semillas $1.898.900. Por debajo de entrega16 en $3.261.500. Mejor público sigue16$96.921.000; faltan$6.340.500 para objetivo100millones en esta corrida. Importes ya públicos del25%, sin volver a dividir. Usuario no explicitó número; atribución a19 por contexto. No distingue efecto del corte frente al agregado de CatBoost/pesos distintos:17/18 no tienen resultado informado. Mayo reutilizado y ajuste de score pueden no transferir a agosto; no demuestra causa ni significancia con agregados. 17/18 guardadas sin envío, conforme decisión previa del usuario; no nuevo submit automático.

Snapshot pre_envio conservado; hashes de cinco adjuntos y probabilidades intactos. Cero fits/API/creditos/submits por registro.

## 108. Target invertido con LightGBM189 evaluado - 2026-10-06

**Target invertido189 completo:** total medio $262.823.000,25% $65.705.750; delta frente16 $-3.597.000,25% $-899.250; 1/5 semillas,0/4 partes. [Informe](salidas/target_invertido189_20261006_153550/MINI_INFORME.md). Cinco fitsLightGBM189BAJA2, TabPFN202 combinado reutilizado. Cero API/créditos/submits/fitsfinales. Mayo reutilizado; sin garantía pública.

## 109. LightGBM192 historia y rangos evaluado - 2026-10-06

**LightGBM192 historia+rango completo:** total medio $261.860.500,25% $65.465.125; delta frente16 $-4.559.500,25% $-1.139.875; 1/5 semillas,0/4 partes. [Informe](salidas/hist192_rangos_20261006_153843/MINI_INFORME.md). Cinco fits nuevos; cero API/créditos/submits. Mayo reutilizado.

## 110. Optuna CatBoost CV abril y ensemble mayo - 2026-10-06

**Optuna CatBoost completo y verificado:** trial4; ensemble40/40/20,2,5%: total medio $268.845.500,25% $67.211.375; delta frente16 $2.425.500,25% $606.375; frente17 $-968.000,25% $-242.000. [Informe](salidas/optuna_catboost_20261006_154705/MINI_INFORME.md). CV3 abril; ganador congelado y cinco semillas mayo. Sin créditos; vínculos recurrentes mañana7 de octubre sobre el mejor modelo disponible.

CV por clientes de abril no es test temporal; se selecciona por CatBoost solo y su aporte al ensemble se comprueba despues. Mayo/semillas reutilizados: no validacion independiente ni garantia publica. No hay OOF compatibles de TabPFN en abril para optimizar el ensemble sin nuevas inferencias; no usar sus predicciones in-sample para tuning.

## 111. Entrega20 CatBoost ajustado preparada y verificada - 2026-10-06

**Entrega20 CatBoost ajustado preparada/verificada:** [informe](salidas/01_entregas_bot/20_EnsembleCatBoostOptuna5_20261006_195723/INFORME.md). Cinco CatBoost finales abril+mayo, 800 árboles/profundidad4, LightGBM189 y TabPFN202 guardados de16;40/40/20,corte2,5%. Local total$268.845.500,25%$67.211.375: supera16 por$2.425.500,25%$606.375 (4/5 semillas,3/4 partes), pero pierde contra17 por$968.000,25%$242.000 (mejora2/5 semillas,1/4 partes). Se preparó según condición del usuario de superar16; no presentar como mejora demostrada frente17. Mensaje `submit EnsembleCatBoostOptuna5_20261006_195723_semillas`. Pendiente envío manual, sin resultado público. Cero créditos/API/submits automáticos. Mañana7 de octubre: vínculos recurrentes sobre mejor modelo disponible.

Script85 usa constructor final61, verifica matrices/target de abril+mayo, fuente16/17, CatBoost ganadorCV3abril y cinco semillas. Scores comprobados por producto matricial y selección/listasIDs exactas desde archivos, modelos recargados; archivos fuente preservados. No se usaron etiquetas junio/julio/agosto. Script87 comprueba hashes finales/adjuntos/modelos/comando y registra estado.

## 112. Correcci?n confirmada de ccajas_depositos ? 2026-10-06

`ccajas_depositos`: las 163.768 filas de 202105 son cero. Nueva regla en `calidad_datos.py`: convertir a NA solamente ese mes, antes de generar hist?ricos; usar `preparar_corregido` para nuevas matrices. Auditor?a [verificada](salidas/correccion_ccajas_20261006_204529/INFORME.md): otros meses, claves y orden conservados; CSV original intacto. Scripts hist?ricos conservados para reproducibilidad. Las corridas anteriores no se corrigieron retroactivamente y el impacto en ganancia requiere reentrenar.

Script88 verifica todos los meses sin leer etiquetas. No entrenamiento, API ni submit en esta tarea.

## 113. Resultado publico entrega17 - 2026-10-06

Entrega17 enviada: media publica $94.726.500, desvio entre semillas $2.614.900. Frente a16 ($96.921.000), baja $2.194.500. Mejor publico sigue16; faltan $5.273.500 para100millones en17. Son importes publicos (25%); no dividir otra vez. Localmente17 superaba16: total $269.813.500 (25% $67.453.375) frente $266.420.000 (25% $66.605.000). La mejora local no se traslado al publico. Comparacion de mezcla 50/50 frente40/40/20 con CatBoost; no demuestra causa ni significancia a partir de medias y desvios agregados. No incorpora la correccion reciente de ccajas_depositos.

Manifest previo archivado; adjuntos y predicciones intactos. Sin nuevos entrenamientos ni envios automaticos.

## 114. Plan de recomendaciones de la catedra - 2026-10-06

Plan en tp_primera_entrega/PLAN_CATEDRA.md y prioridad actual en NEXT_STEPS_IDEAS.md. Ablaciones del control16, lag2/delta2 y correccion de mayo, Optuna AUC sin undersampling, diez configuraciones LightGBM, mezcla TabPFN y topN. Final marzo-junio a agosto; junio sin seleccion. Plan solamente: no entrenamientos ni API ni entregas nuevas.

## 115. Implementacion catedra y primeras ablaciones - 2026-10-07

Directorio tp_primera_entrega/salidas/catedra_implementacion_20261006_205501. Nuevos features_catedra.py y scripts89-93. Orden2 verificado por calendario, huecos, NA y cambio de anio; +24 columnas. A0 reproducido: mezcla total266420000,25%66605000. A1 correccion misma ganancia/listas. A2 mezcla265743500,25%66435875; delta-676500,25%-169125. Abril no tiene febrero: no puede aprender lag2. Optuna AUC en curso, sin undersampling, marzo+abril a mayo; diagnostico por clientes mayo preparado. Final junio solo fit. Cotizacion con dimensiones local226=43438 y final=173599, sin datos enviados. Autorizacion local propuesta50000 pendiente; no inferencia ni creditos.

## 116. TabPFN226 local autorizado y verificado - 2026-10-07

Autorizacion explicita 50.000creditos para226features abril con targetBAJA2, mayo sin labels/ID/mes. Consumo43.438. Mezcla LGB189+Tab226 localtotal268367000,25%67091750,delta16total1947000,25%486750. LGB213+Tab226total264913000,25%66228250. Sin final/API adicional ni Bot. Abril no tiene lag2: no atribuir ganancia a aprendizaje de esos lags. Optuna y continuacion local siguen activos.

## 117. Hist?ricos orden2, marzo-mayo a junio - 2026-10-07

Usuario autoriza junio para verificar lag2, sustituyendo restriccion previa para este diagn?stico. Script99,10fits cinco semillas189/213, par?metros16 fijos273?rboles, sin undersampling, correccion mayo en ambos. Controltotal393756000,25%98439000; orden2total391649500,25%97912375; delta-2106500,25%-526625; mejora1/5semillas y1/4partes. LightGBM solo targetcombinado y premioBAJA2, no ensembleTab ni resultadoBot. Script100 verifica lags por lookup independiente, hashes/modelos/predicciones y pagos por fila. Optuna interrumpido para memoria; trials completos conservados; se reanuda despu?s.

## 118. Actualizacion final TabPFN del ensemble16 preparada - 2026-10-07

Script101 prepara327052registros abril+mayo226features y BAJA2,164647clientes agosto226features sinlabels/ID/mes. Matrices locales autorizadas preservadas, orden y labels comprobados; cinco modelosLGB16 recargados y scoresagosto reproducidos exactamente. Paquete salidas/tabpfn226_agosto_20261007_203700. Cotizacion78242,limitepropuesto80000 adicionales; autorizacionfinal pendiente. Scripts102inferenciay103preparacioncincoCSVslistos. No API final ni Bot. Se actualiza soloTabPFN, conservaLGB189 y su tratamiento anterior en train.

## 119. TabPFN226 final y entrega21 completos - 2026-10-07

Autorizacion explicita final80.000creditos; consumo78.242. Abril+mayo327052filas226variables BAJA2, agosto164647filas sinlabels/ID/mes. CincoLightGBM189 congelados16, targetcombinado; mezcla50/50,corte>.025. Entrega21_EnsembleLGB189Tab2265_20261007_205130, cincoCSV verificados por rankinglexsort independiente. Localmedia268367000,25%67091750,delta16total1947000,25%486750,5/5semillas y4/4partes. No gananciaagosto disponible ni envioBot. Fuente preparada archivada pre_inferencia; hashes actualizados al estado final.

## 120. Archivo de codigo por entrega y reproduccion exacta - 2026-10-08

Se agrego codigo/ en entregas16 y21. Script66 y dependencias16 coinciden con hashes historicos. Inventario recorre manifests fuente, guarda scripts firmados, snapshotmanifest, configuracion registrada, README y reproductorCSV. Scripts21 no firmados historicamente se separan como capturados_al_archivar. Se regeneraron cincoCSV16 y cincoCSV21 con hashes identicos, preservando CRLF/LF. Modelos, predicciones, manifiestos y adjuntos originales intactos. Script104 permite archivar otra entrega y reporta faltantes/mismatches;105 regenera listas sinfit niAPI. Script103 futuro archiva automaticamente el codigo al preparar entregas.

## 121. Resultado publico entrega21 - 2026-10-08

Entrega21: media publica $92.647.500, desvio entre semillas $1.599.500. Pierde $4.273.500 frente16 ($96.921.000); mejor publico sigue16. Faltan $7.352.500 para100millones en21. Estos importes ya son publicos del25%, no dividir otra vez ni inferir totalagosto. La mejora local ($268.367.000 total,25%$67.091.750 frente16 $266.420.000,25%$66.605.000) no se traslado al Bot. LGB16 congelado; cambio de TabPFN incluye correccion mayo y24historicos. No permite separar causas de esos cambios. Mantener16 como referencia.

Estado anterior archivado pre_envio; adjuntos y scores intactos, hashes verificados. Inventariocodigo conserva snapshotanterior y referencia manifiestoactual. Sin entrenamiento, API ni envios nuevos.

## 122. Diez pruebas de Optuna programadas - 2026-10-08

Usuario confirma17submits/dia y autoriza preparar comparaciones LGBsolo/mezcla y cortes. Estudio aun en curso,16trials completos al inicio. Script106 preparara diez entregas de unCSV: promedio10configuraciones LGB, solo o50/50 conTab202original16, top10000/10500/11000/11500/12000. Script107 espera finalverificado, prepara, archiva codigo y reproduceCSVconhashesexactos. Ranking local con total/25% y delta frentecontrol misma ventana/corte; no recomendar candidatos perdedores automaticamente. Sin nuevaAPI ni envioBot.


## Segmentación local autorizada (2026-10-08)

Preparada ablación pareada de cuatro segmentos, script108, cinco semillas y validaciones mayo/junio. En cola tras cátedra; no inferencia remota ni envío al Bot.


## Comparación factorial LightGBM (2026-10-08)

Usuario autoriza organizar experimentos con varias semillas. Plan110 congelado:189/213 × control/trial12, cinco semillas comunes, mayo y junio, cortes elegidos con mayo.40 modelos,15 controles reutilizables con verificación,25 fits nuevos. Clusters diferidos. SinAPI, créditos ni envíos.

## Entrega32 Control213 + TabPFN16 ? resultado p?blico 2026-10-09

Enviada por Tomas. Media p?blica $94.864.000; desv?o $3.472.800. Delta frente16: ?$2.057.000; mejor referencia16 $96.921.000. LGB213 marzo-junio, par?metros16/273?rboles, TabPFN202 original16, mezcla50/50, corte>2,5%, cinco semillas. Local mayo $262.267.500 frente16 $266.420.000; ventanas distintas. Manifest pre-env?o archivado; hashes de adjuntos y predicciones comprobados. Sin nuevos fits/API/env?os.

## Variantes de entrega16 preparadas — 2026-10-09

Entrega33: submit Ensemble16Promedio5Corte25_20261009_192311; 1 CSV; pendiente envío manual. Carpeta tp_primera_entrega\salidas\01_entregas_bot\33_Ensemble16Promedio5Corte25_20261009_192311.

Entrega34: submit Ensemble16SemillasCorte30_20261009_192311; 5 CSV; pendiente envío manual. Carpeta tp_primera_entrega\salidas\01_entregas_bot\34_Ensemble16SemillasCorte30_20261009_192311.

Entrega35: submit Ensemble16Promedio5Corte30_20261009_192311; 1 CSV; pendiente envío manual. Carpeta tp_primera_entrega\salidas\01_entregas_bot\35_Ensemble16Promedio5Corte30_20261009_192311.

Promedio5 a2,5%, cinco listas a3%, promedio5 a3%. Mismos modelos16 y mezcla50/50. Siete CSV reproducidos con hashes idénticos. Sin fits/API/créditos.

## Entrega33 ? resultado p?blico 2026-10-09

Promedio de cinco scores16, mezcla50/50, corte>2,5%, una lista. P?blico $96.112.500, desv?o0 por ?nicoCSV. Delta frente media16: -$808.500; referencia16 sigue $96.921.000. Entregas34/35 pendientes de resultado. Manifest pre-env?o archivado y hashes verificados.

## Entrega34 ? resultado p?blico 2026-10-09

Cinco listas16, mezcla50/50, corte>3%. P?blico medio $94.572.500, desv?o $1.781.900. Delta frente16: -$2.348.500; referencia16 sigue $96.921.000. Subir corte empeor? p?blico pese a mejora local. Entrega35 pendiente de resultado. Manifest pre-env?o archivado y hashes verificados.

## Entrega35 ? resultado p?blico 2026-10-09

Promedio de probabilidades de cinco semillas16, mezcla50/50, corte>3%, una lista. P?blico $97.047.500; desv?o0 por ?nicoCSV. Delta frente media16: +$126.500; frente33: +$935.000. Faltan $2.952.500 para100millones. Referencia operativa35, control16 conservado; comparaci?n de una lista contra media de cinco, no se conocen resultados individuales16. Entregas33/34/35 completadas. Hashes verificados, manifest pre-env?o archivado.

## Dos cortes alrededor de35 preparados — 2026-10-09

Entrega36: corte>2.75%, 10420 clientes, unCSV. submit Ensemble16Promedio5Corte275_20261009_192946. Pendiente envío manual.

Entrega37: corte>3.25%, 9134 clientes, unCSV. submit Ensemble16Promedio5Corte325_20261009_192946. Pendiente envío manual.

Mismos scores35, promedio5 y mezcla50/50. CSV reproducidos con hashes idénticos; cero fits/API/créditos.

## Entrega36 ? resultado p?blico 2026-10-09

Promedio5 de16, mezcla50/50, corte>2,75%, una lista de10.420clientes. P?blico $98.175.000, desv?o0 por ?nicoCSV. Delta35 +$1.127.500; delta media16 +$1.254.000; faltan $1.825.000 para100millones. Referencia operativa36;37 pendiente. Hashes verificados y manifest pre-env?o archivado.

## Entrega37 y cierre de cortes ? resultado p?blico 2026-10-09

Entrega37: promedio5 de16, mezcla50/50, corte>3,25%, 9.134clientes. P?blico $94.187.500; desv?o0 por ?nicoCSV. Delta36 -$3.987.500. Tanda completa:33/2,5%=$96.112.500;36/2,75%=$98.175.000;35/3%=$97.047.500;37/3,25%=$94.187.500. Mejor probado2,75%; referencia36, faltan $1.825.000 para100millones. Hashes verificados y manifest pre-env?o archivado.

## Pesos alrededor de36 preparados — 2026-10-09

Entrega38: submit Ensemble16Promedio5L40T60Corte275_20261009_193816; 10047clientes, pesos {'lightgbm': 0.4, 'tabpfn': 0.6}. UnCSV; pendiente envío manual.

Entrega39: submit Ensemble16Promedio5L60T40Corte275_20261009_193816; 10756clientes, pesos {'lightgbm': 0.6, 'tabpfn': 0.4}. UnCSV; pendiente envío manual.

Promedio5, corte>2,75% fijo; modelos16 guardados. DosCSV reproducidos con hashes idénticos; sin fits/API/créditos.

## Entrega38 ? resultado p?blico 2026-10-09

Promedio5, LGB/Tab40/60, corte>2,75%, una lista de10.047clientes. P?blico $95.040.000, desv?o0 por ?nicoCSV. Delta36 -$3.135.000. Referencia36 $98.175.000;39/60-40 pendiente. Hashes verificados, manifest pre-env?o archivado.

## Resultado p?blico entrega39 ? 2026-10-10

Promedio5, LightGBM/TabPFN60/40, corte>2,75%, una lista de10.756clientes. P?blico $96.525.000, desv?o0 por ?nicoCSV. Delta36 -$1.650.000. Tanda de pesos cerrada:40/60=$95.040.000;50/50=$98.175.000;60/40=$96.525.000. Mantener referencia36, faltan $1.825.000 para100millones. Son importes p?blicos del25%, sin dividir nuevamente. Desv?o0 no mide estabilidad. Manifest pre-env?o archivado; hashes de adjunto y predicciones verificados. Sin nuevos fits/API/env?os.

## Promedio20 semillas — 2026-10-10

# Promedio de20 semillas

Control5: total $275,385,000;25% $68,846,250.0. Candidato20: total $269,830,000;25% $67,457,500.0. Delta total $-5,555,000;25% $-1,388,750.0.

Pesos50/50 y corte>2,75% congelados. Mayo y las cinco semillas originales reutilizados; no test independiente ni garantía pública. TabPFN guardado, cero API/créditos.

No supera el control local. Sin entrenamiento final ni nueva entrega.


## Segmentación ejecutada y verificada — 2026-10-10

# Segmentación: comparación verificada

Cuatro segmentos aprendidos solo con train; variable categórica adicional en LightGBM. Mismos parámetros, 273 árboles, cinco semillas y corrección de datos en ambos brazos.

Marzo–abril → mayo; marzo–mayo → junio. Métrica principal corte2,5%; 2,75% diagnóstico fijado antes de resultados. Ganancia de una lista de probabilidades promedio y delta medio de listas individuales separados.

```text
   mes  corte  control_total  control25pct  segmento_total  segmento25pct  delta_total  delta25pct  control_contactos  segmento_contactos  control_tp  segmento_tp  semillas_mejoran  media_delta_semillas
202105 0.0250      256162500    64040625.0       251185000     62796250.0     -4977500  -1244375.0              13245               13186         564          558                 3             2981000.0
202105 0.0275      262680000    65670000.0       258967500     64741875.0     -3712500   -928125.0              12368               12263         548          542                 4             1512500.0
202106 0.0250      397485000    99371250.0       391407500     97851875.0     -6077500  -1519375.0              13586               13767         701          700                 1           -10945000.0
202106 0.0275      401692500   100423125.0       396467500     99116875.0     -5225000  -1306250.0              12673               12783         682          680                 2            -7722000.0
```

No hay mejora consistente para promover; conservar referencia36.

No es una comparación directa con la entrega36 ni una ganancia pública. Mayo/junio reutilizados; junio tiene aguinaldo. Sin API, créditos, scoring agosto ni nueva entrega. Predicciones reconstruidas desde modelos, segmentos y preprocesamiento verificados; ganancias recalculadas desde pagos por cliente.


## Vínculos recurrentes — 2026-10-10

# Vínculos recurrentes: piloto verificado

Ocho señales, 189→197 variables; resto configuración16 congelado. Abril→mayo, cinco semillas, TabPFN202 guardado,50/50,corte>2,75%.

Control promedio5 total $275,385,000;25% $68,846,250.0;9906 contactos,498 bajas. Candidato total $272,222,500;25% $68,055,625.0;10021 contactos,498 bajas. Delta total $-3,162,500;25% $-790,625.0.

Mejoran 1/5 semillas y 2/4 partes; delta medio listas individuales $-5,934,500.0. Supera puerta local: False.

Mes calendario, nulos desconocidos, ausencia requiere todas las fuentes en cero, positivos parciales establecen presencia. Préstamos pueden cancelarse normalmente. Features reconstruidas por lookup independiente y toy de huecos/año/nulos/negativos; modelos recargados y ganancias reproducidas. Mayo y semillas reutilizados; no test independiente ni garantía pública. Sin API/créditos/submit. Referencia pública36 preservada.


## Estrategias por segmento — 2026-10-10

# Estrategias por segmento

La prueba previa108 agregó una variable categórica; no evaluó especialistas ni cortes/pesos por grupo. Este ensayo entrena cuatro modelos especializados, cinco semillas cada uno, y asigna a cada cliente el modelo de su grupo. Segmentación aprendida solo en abril, sin etiquetas.

Control general189 frente especialistas189, y mezcla predefinida50/50 de general/especialista dentro del componente LightGBM. TabPFN202 guardado, pesos LightGBM/Tab50/50 y corte>2,75% fijos. Abril→mayo, sin nueva API ni scoring agosto.

```text
              estrategia  contactos  tp   fp  ganancia_total  ganancia_25pct  media_ganancia_semillas  delta_total  delta_25pct  delta_media_semillas  semillas_mejoran
                 general       9906 498 9408       275385000      68846250.0              272464500.0            0          0.0                   0.0                 0
           especialistas       9135 470 8665       265787500      66446875.0              259215000.0     -9597500   -2399375.0           -13249500.0                 0
general50_especialista50       9557 488 9069       273982500      68495625.0              271810000.0     -1402500    -350625.0             -654500.0                 1
```

Diagnóstico por segmento:

```text
              estrategia  segmento  clientes  bajas  contactos  tp   fp  ganancia_total  ganancia_25pct  delta_total
                 general         0     34118     46         19   1   18          577500        144375.0            0
                 general         1     50155    328       3137 152 2985        80932500      20233125.0            0
                 general         2     51136     33          9   0    9         -247500        -61875.0            0
                 general         3     28359    463       6741 345 6396       194122500      48530625.0            0
           especialistas         0     34118     46          2   0    2          -55000        -13750.0      -632500
           especialistas         1     50155    328       2205 126 2079        77962500      19490625.0     -2970000
           especialistas         2     51136     33          0   0    0               0             0.0       247500
           especialistas         3     28359    463       6928 344 6584       187880000      46970000.0     -6242500
general50_especialista50         0     34118     46          8   1    7          880000        220000.0       302500
general50_especialista50         1     50155    328       2686 142 2544        82335000      20583750.0      1402500
general50_especialista50         2     51136     33          4   0    4         -110000        -27500.0       137500
general50_especialista50         3     28359    463       6859 345 6514       190877500      47719375.0     -3245000
```

Candidatos que superan el control tanto en única lista promedio5 como en media de cinco listas: [].

Mayo y semillas reutilizados; no test independiente ni garantía pública. No se optimizaron cortes ni pesos por segmento ni se eligieron modelos ganadores por segmento con mayo. El resultado no descarta todas las estrategias segmentadas. Modelos recargados y scores/ganancias reconstruidos desde archivos; fuentes y referencia36 preservadas.


## Políticas por segmento — 2026-10-10

# Pesos y cortes por segmento

Cuatro segmentos aprendidos en abril. En cada cruce se eligen pesos o cortes con tres partes de clientes de mayo y se aplican a la cuarta. Se comparan también reglas globales elegidas de la misma forma. No optimizar peso y corte simultáneamente.

Control fijo total $275.385.000;25% $68.846.250.

```text
           politica  contactos  tp   fp  ganancia_total  ganancia_25pct  delta_fijo_total  delta_fijo25pct  media_delta_semillas  semillas_mejoran  partes_mejoran  delta_vs_global_equivalente
     pesos_globales      10123 498 9625       269417500      67354375.0          -5967500       -1491875.0            -1903000.0                 1               0                            0
 pesos_por_segmento       9670 489 9181       271975000      67993750.0          -3410000        -852500.0            -1006500.0                 3               1                      2557500
       corte_global       8639 477 8162       287127500      71781875.0          11742500        2935625.0             1441000.0                 3               4                            0
cortes_por_segmento       8650 477 8173       286825000      71706250.0          11440000        2860000.0            -1380500.0                 2               4                      -302500
```

Candidatos que mejoran regla fija, regla global equivalente y media de semillas: [].

Modificar etiquetas de la parte evaluada no cambia la regla elegida; ganancias reconstruidas desde archivos. Mayo y semillas reutilizados, no test temporal independiente. Los cruces por cliente no eliminan todo el sesgo histórico. Sin API, créditos ni nuevo submit. No elegir retrospectivamente la combinación perfecta por segmento con todos los datos y presentar esa ganancia como validada.


## Elección de modelo por segmento — 2026-10-10

# Elegir estrategia de modelo por segmento

Para cada segmento se elige entre general, especialista y su mezcla50/50, con tres partes de clientes de mayo. Se mide en la cuarta parte y se rota. Pesos LightGBM/TabPFN50/50 y corte2,75% fijos. Comparación adicional con un único modelo elegido globalmente en los mismos cruces.

```text
                   politica  contactos  tp   fp  ganancia_total  ganancia_25pct  delta_total  media_delta_semillas  semillas_mejoran  delta25pct  delta_vs_global_elegido
      modelo_global_elegido       9748 490 9258       270930000      67732500.0     -4455000            -1584000.0                 1  -1113750.0                      NaN
modelo_por_segmento_elegido       9547 488 9059       274257500      68564375.0     -1127500            -1375000.0                 2   -281875.0                3327500.0
```

Mayo y semillas reutilizados; no test temporal independiente ni garantía pública. No nueva API ni entrenamiento adicional ni entrega. Etiquetas de la parte evaluada no afectan elección; ganancias reconstruidas desde archivos.


## Columna cluster en ensemble — 2026-10-10

# Columna cluster dentro del ensemble

Ablación alineada abril→mayo: LightGBM189 contra190 con cluster categórico; mismo target combinado,273árboles,cinco semillas,TabPFN202 guardado,pesos50/50,corte>2,75%. Cluster aprendido solo en abril, sin etiquetas; no estrategias por grupo.

Control total $275,385,000;25% $68,846,250.0;9906contactos,498bajas. Candidato total $268,950,000;25% $67,237,500.0;9860contactos,491bajas. Delta total $-6,435,000;25% $-1,608,750.0. Mejoran 2/5 semillas y 1/4 partes. Delta medio listas individuales $-6,022,500.0. Supera puerta local:False.

Modelos recargados, categorías verificadas, cluster reproducido contra archivos119; scores reconstruidos mediante producto matricial y ganancias desde pagos por cliente. Mayo/semillas reutilizados; no test independiente ni garantía pública. Sin API/créditos/submit. Referencia36 preservada.


## Plan de experimentos consolidado — 2026-10-10

Por pedido de Tomas de ordenar las ideas, se creo tp_primera_entrega/PLAN_EXPERIMENTOS_20261010.md y se actualizo el encabezado de NEXT_STEPS_IDEAS.md. Plan preparado, sin nuevas ejecuciones. Orden: estabilidad de cortes segmentados frente ajuste global en junio con reglas congeladas en mayo; bloque de cuatro senales de debitos/pagos sin prestamos/inversiones; auditoria de calidad/drift; canaritos condicionado. Hasta15fits locales para primera tanda, cero API/creditos/submits. TabPFN202 marzo+abril->junio existente verificado por lectura de manifest, disponible para comprobacion sin nueva inferencia; hashes y universo se verificaran al ejecutar. Junio ya expuesto: comprobacion exploratoria, no test independiente. Control local lista promedio5 $275.385.000,25%$68.846.250; referencia publica36 $98.175.000 intacta. Puertas: mejora de lista promedio y media de listas individuales, control de igual ventana y comparacion global equivalente para politicas segmentadas. No repetir variantes completas que perdieron, no mezclar correcciones ni usar el publico para seleccionar automaticamente.

## Paso1: cortes segmentados en junio — 2026-10-10

# Cortes por segmento: comprobación congelada en junio

Reglas elegidas únicamente con mayo antes de leer resultados de junio:

```json
{
  "fijo": 0.0275,
  "global_mayo": 0.0325,
  "segmentados_mayo": {
    "0": 0.035,
    "1": 0.03,
    "2": 0.02,
    "3": 0.0325
  }
}
```

LightGBM189 marzo+abril→junio,cinco semillas,273árboles,parámetros16; TabPFN202 BAJA+2 de la misma ventana,guardado,50/50. Mismas probabilidades para todos los brazos. Cluster119 aprendido en abril se conserva; mayo solo aporta historia al entrenamiento, sus etiquetas eligieron las reglas.

```text
        politica  contactos  tp    fp  ganancia_total  ganancia_25pct  media_ganancia_semillas  delta_vs_fijo  delta_vs_fijo25pct  delta_vs_global  delta_media_vs_fijo  delta_media_vs_global  semillas_mejoran_fijo  semillas_mejoran_global
            fijo      10748 649 10099       418330000     104582500.0              402369000.0              0                 0.0         20872500                  0.0              8723000.0                      0                        5
     global_mayo       9307 594  8713       397457500      99364375.0              393646000.0      -20872500          -5218125.0                0           -8723000.0                    0.0                      0                        0
segmentados_mayo       9621 603  9018       398722500      99680625.0              394724000.0      -19607500          -4901875.0          1265000           -7645000.0              1078000.0                      0                        4
```

Cerrar rama actual: cortes segmentados no superan ambos controles y métricas.

Diagnóstico por segmento:

```text
        politica  segmento  clientes  bajas  corte  contactos  tp   fp  ganancia_total  ganancia_25pct  delta_vs_fijo  delta_vs_global
            fijo         0     30911     54 0.0275         43   2   41         1017500        254375.0              0           715000
            fijo         1     39644    383 0.0275       3781 212 3569       129222500      32305625.0              0          5500000
            fijo         2     68264     41 0.0275         10   0   10         -275000        -68750.0              0           -55000
            fijo         3     25295    620 0.0275       6914 435 6479       288365000      72091250.0              0         14712500
     global_mayo         0     30911     54 0.0325         29   1   28          302500         75625.0        -715000                0
     global_mayo         1     39644    383 0.0325       3101 190 2911       123722500      30930625.0       -5500000                0
     global_mayo         2     68264     41 0.0325          8   0    8         -220000        -55000.0          55000                0
     global_mayo         3     25295    620 0.0325       6169 403 5766       273652500      68413125.0      -14712500                0
segmentados_mayo         0     30911     54 0.0350         20   1   19          550000        137500.0        -467500           247500
segmentados_mayo         1     39644    383 0.0300       3411 199 3212       125097500      31274375.0       -4125000          1375000
segmentados_mayo         2     68264     41 0.0200         21   0   21         -577500       -144375.0        -302500          -357500
segmentados_mayo         3     25295    620 0.0325       6169 403 5766       273652500      68413125.0      -14712500                0
```

Junio ya expuesto y con aguinaldo; no test independiente ni garantía pública. No ajustar reglas con junio ni producir un nuevo CSV del Bot en esta comprobación. TabPFN: manifest,ventana,features,claves,labels,nulos y ganancia histórica comprobados; su CSV no tenía hash histórico en el manifest, por lo que se congeló checksum actual y se contrastó con una segunda copia histórica. Modelos recargados,scores reconstruidos por producto matricial,selecciones y pagos verificados; fuentes intactas. Sin API ni créditos. Referencia36 preservada.


## Vínculos recurrentes — 2026-10-10

# Vínculos recurrentes: piloto verificado

Cuatro señales de debitos/pagos, 189→193 variables; resto configuración16 congelado. Abril→mayo, cinco semillas, TabPFN202 guardado,50/50,corte>2,75%.

Control promedio5 total $275,385,000;25% $68,846,250.0;9906 contactos,498 bajas. Candidato total $275,522,500;25% $68,880,625.0;9901 contactos,498 bajas. Delta total $137,500;25% $34,375.0.

Mejoran 1/5 semillas y 2/4 partes; delta medio listas individuales $-7,018,000.0. Supera puerta local: False.

Mes calendario, nulos desconocidos, ausencia requiere todas las fuentes en cero, positivos parciales establecen presencia. Préstamos pueden cancelarse normalmente. Features reconstruidas por lookup independiente y toy de huecos/año/nulos/negativos; modelos recargados y ganancias reproducidas. Mayo y semillas reutilizados; no test independiente ni garantía pública. Sin API/créditos/submit. Referencia pública36 preservada.


## Paso2: servicios separados — 2026-10-10

# Paso2 completado: cuatro señales de débitos/pagos

Abril→mayo, LightGBM189→193, cinco semillas,273árboles,mezcla50/50 con TabPFN202 guardado,corte>2,75%. Control total $275,385,000;25% $68,846,250.0. Candidato total $275,522,500;25% $68,880,625.0. Delta total $137,500;25% $34,375.0;delta medio listas individuales $-7,018,000.0. Mejoran 1/5semillas y 2/4partes.

No supera la puerta de mayo: no ejecutar junio, no entrenamiento final ni nueva entrega. Rama cerrada para este bloque. Cinco fits locales nuevos, cero API/créditos/submits. Mayo reutilizado; no prueba independiente. Referencia36 preservada. Siguiente pendiente del plan: auditoría de calidad/drift, no ejecutada por este encargo.


## Submit exploratorio autorizado — 2026-10-10

# Entrega40: servicios193, submit exploratorio

LightGBM193 abril+mayo→agosto,cinco semillas,273árboles. Cuatro señales de débitos/pagos añadidas; TabPFN202 de16 guardado. Promedio5,50/50,corte>2,75%;10386clientes en una sola lista. Sin cambios de pesos/target/corte/ventana ni nueva API.

Mayo: control total$275.385.000/25%$68.846.250; candidato total$275.522.500/25%$68.880.625; delta total+$137.500/25%+$34.375. Media de listas individuales pierde$7.018.000,mejora1/5semillas. No pasa puerta estricta; usuario autoriza un submit exploratorio el10/10. No presentar como mejora demostrada. Junio no evaluado y mayo reutilizado.

Frente a36 en agosto: 483clientes agregados,517retirados,9903comunes. Esto no permite conocer TP/FP ni ganancia de agosto. Referencia36 pública$98.175.000 conservada.

Comando:`submit EnsembleServicios193Promedio5Corte275_20261010_093934`. Adjuntar exclusivamente `EnsembleServicios193Promedio5Corte275_20261010_093934.csv` de `adjuntos/`,sin encabezado ni índice. No enviado automáticamente.

Cinco fits finales nuevos,cero fitsTab/ceroAPI/créditos. Modelos recargados,control36 reproducido,features calendario reconstruidas por lookup,mezcla verificada y CSV reproducido con hash idéntico. Código archivado con firmas; modelos finales en `tp_primera_entrega\salidas\servicios_final_exploratorio_20261010/modelos`.


# Tres submits exploratorios preparados — 2026-10-10

Usuario confirma las tres variantes cercanas. Una lista promedio5 por variante, corte>2,75%, abril+mayo->agosto. Preparadas y verificadas, pendientes de envio manual y resultado publico. Referencia36 $98.175.000 conservada. 20 especialistas finales compartidos entre dos entregas y cinco fits finales de vinculos197; ceroAPI/creditos.

- **41 — Mezcla general/especialistas**: 9,806 clientes. [CSV](salidas/01_entregas_bot/41_EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654/adjuntos/EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654.csv); [informe](salidas/01_entregas_bot/41_EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654/INFORME.md). Comando: `submit EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654`.
- **42 — Eleccion de modelo por segmento**: 9,972 clientes. [CSV](salidas/01_entregas_bot/42_EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659/adjuntos/EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659.csv); [informe](salidas/01_entregas_bot/42_EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659/INFORME.md). Comando: `submit EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659`.
- **43 — Ocho vinculos recurrentes**: 10,404 clientes. [CSV](salidas/01_entregas_bot/43_EnsembleVinculos197Promedio5Corte275_20261010_094750/adjuntos/EnsembleVinculos197Promedio5Corte275_20261010_094750.csv); [informe](salidas/01_entregas_bot/43_EnsembleVinculos197Promedio5Corte275_20261010_094750/INFORME.md). Comando: `submit EnsembleVinculos197Promedio5Corte275_20261010_094750`.

Esperar resultados de estas entregas antes de seguir con experimentos. Pendiente posterior: paso3, auditoria de calidad/drift. No ejecutado en esta tanda. Cada ganancia publica ya corresponde al25%; no dividir otra vez. Todas son pruebas exploratorias, no mejoras demostradas.

# Entrega 41: Mezcla general/especialistas

25% general189 +25% especialistas189 +50% TabPFN202.

Abril+mayo -> agosto. Cinco semillas, 273 arboles, corte >2,75%. Una lista de 9,806 clientes. TabPFN202 guardado de16: cero API y creditos.

Validacion local lista promedio: delta total $-1,402,500; equivalente25% $-350,625.0. Delta medio de cinco listas individuales: $-654,500.0. No pasa puerta estricta; submit exploratorio autorizado. Mayo reutilizado, sin garantia publica.

Frente a36: 248 agregados, 862 retirados y 9558 comunes. Referencia36 publica $98.175.000 conservada. Agosto sin etiquetas: ganancia desconocida.

Comando: `submit EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654`. Adjuntar exclusivamente `EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654.csv`, sin encabezado ni indice. No enviado automaticamente.

Modelos finales compartidos en `tp_primera_entrega\salidas\tres_exploratorias_final_20261010`, recargados y firmados. Matrices originales verificadas contra16; selector y segmentador congelados antes de puntuar agosto. Ocho vinculos reconstruidos con mes calendario anterior y lookup independiente. Scores reconstruidos desde archivo y CSV reproducido con hash identico. Codigo archivado.

# Entrega 42: Eleccion de modelo por segmento

Por grupo elegir general, mezcla50/50 o especialista dentro del50% LightGBM;50% TabPFN202 fijo.

Abril+mayo -> agosto. Cinco semillas, 273 arboles, corte >2,75%. Una lista de 9,972 clientes. TabPFN202 guardado de16: cero API y creditos.

Validacion local lista promedio: delta total $-1,127,500; equivalente25% $-281,875.0. Delta medio de cinco listas individuales: $-1,375,000.0. No pasa puerta estricta; submit exploratorio autorizado. Mayo reutilizado, sin garantia publica.

Frente a36: 102 agregados, 550 retirados y 9870 comunes. Referencia36 publica $98.175.000 conservada. Agosto sin etiquetas: ganancia desconocida.

Comando: `submit EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659`. Adjuntar exclusivamente `EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659.csv`, sin encabezado ni indice. No enviado automaticamente.

Modelos finales compartidos en `tp_primera_entrega\salidas\tres_exploratorias_final_20261010`, recargados y firmados. Matrices originales verificadas contra16; selector y segmentador congelados antes de puntuar agosto. Ocho vinculos reconstruidos con mes calendario anterior y lookup independiente. Scores reconstruidos desde archivo y CSV reproducido con hash identico. Codigo archivado.

La validacion informada selecciona con tres partes de mayo y evalua en la cuarta, cuatro cruces. Para desplegar se ajusta el mismo selector con todo mayo; esa seleccion final NO se mide como validacion. Desempate: general, mezcla, especialistas. Segmentador entrenado en abril sin etiquetas, no se reajusta.

```json
{
  "0": {
    "modelo": "general50_especialista50",
    "peso_especialista": 0.5,
    "ganancias_mayo_ajuste": {
      "general": 577500,
      "general50_especialista50": 880000,
      "especialistas": -55000
    }
  },
  "1": {
    "modelo": "general50_especialista50",
    "peso_especialista": 0.5,
    "ganancias_mayo_ajuste": {
      "general": 80932500,
      "general50_especialista50": 82335000,
      "especialistas": 77962500
    }
  },
  "2": {
    "modelo": "especialistas",
    "peso_especialista": 1.0,
    "ganancias_mayo_ajuste": {
      "general": -247500,
      "general50_especialista50": -110000,
      "especialistas": 0
    }
  },
  "3": {
    "modelo": "general",
    "peso_especialista": 0.0,
    "ganancias_mayo_ajuste": {
      "general": 194122500,
      "general50_especialista50": 190877500,
      "especialistas": 187880000
    }
  }
}
```

# Entrega 43: Ocho vinculos recurrentes

50% LightGBM197 con ocho vinculos recurrentes +50% TabPFN202.

Abril+mayo -> agosto. Cinco semillas, 273 arboles, corte >2,75%. Una lista de 10,404 clientes. TabPFN202 guardado de16: cero API y creditos.

Validacion local lista promedio: delta total $-3,162,500; equivalente25% $-790,625.0. Delta medio de cinco listas individuales: $-5,934,500.0. No pasa puerta estricta; submit exploratorio autorizado. Mayo reutilizado, sin garantia publica.

Frente a36: 531 agregados, 547 retirados y 9873 comunes. Referencia36 publica $98.175.000 conservada. Agosto sin etiquetas: ganancia desconocida.

Comando: `submit EnsembleVinculos197Promedio5Corte275_20261010_094750`. Adjuntar exclusivamente `EnsembleVinculos197Promedio5Corte275_20261010_094750.csv`, sin encabezado ni indice. No enviado automaticamente.

Modelos finales compartidos en `tp_primera_entrega\salidas\tres_exploratorias_final_20261010`, recargados y firmados. Matrices originales verificadas contra16; selector y segmentador congelados antes de puntuar agosto. Ocho vinculos reconstruidos con mes calendario anterior y lookup independiente. Scores reconstruidos desde archivo y CSV reproducido con hash identico. Codigo archivado.

## Resultado publico41 — 2026-10-10

Mezcla general/especialistas: **$97.075.000**, desvio $0, una sola lista. Queda $1.100.000 por debajo de36 ($98.175.000). Referencia36 conservada; faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. El desvio cero proviene de una sola lista y no mide estabilidad. Importes ya publicos del25%, sin volver a dividir. Esperar resultados42 y43 antes de continuar con experimentos;40 sigue sin resultado informado. Sin nuevos fits, APIs, creditos ni envios automaticos.

## Resultado publico42 — 2026-10-10

Eleccion de modelo por segmento: **$96.415.000**, desvio $0, una sola lista. Queda $1.760.000 por debajo de36 ($98.175.000) y $660.000 debajo de41 ($97.075.000). Ambas estrategias de especialistas probadas pierden contra36 en este publico; el resultado no descarta todas las formas de segmentacion. Referencia36 conservada: faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. El desvio cero proviene de una sola lista y no mide estabilidad. Importes ya publicos del25%, sin volver a dividir. Esperar resultado43 antes de continuar con experimentos;40 sigue sin resultado informado. Sin nuevos fits, APIs, creditos ni envios automaticos.

## Nueva mejor entrega43: objetivo publico100M alcanzado — 2026-10-10

**43, ocho vinculos recurrentes: $100.815.000**, desvio $0, una sola lista de10.404clientes. Supera36 ($98.175.000) en **$2.640.000**,41 ($97.075.000) en $3.740.000 y42 ($96.415.000) en $4.400.000. **Objetivo publico $100 millones alcanzado, con $815.000 de excedente.** Nueva referencia43: LightGBM197 con ocho vinculos recurrentes y TabPFN202 guardado, promedio de cinco probabilidades, pesos50/50, corte>2,75%, abril+mayo->agosto. Segmentacion y especialistas no forman parte de43. Referencia36 y artefactos originales conservados.

La lista promedio perdia $3.162.500 en mayo y la media de cinco listas perdia $5.934.500; la prueba exploratoria autorizada mejora en el publico de agosto. Mantener ambos resultados; no reescribir la validacion local ni presentar el publico como garantia privada. Public gain ya corresponde al25%; no dividir otra vez. Desvio cero significa una sola lista.

Tanda41/42/43 completada, todos los resultados registrados.40 sigue sin resultado informado. Siguiente trabajo pendiente: retomar plan desde auditoria de calidad/drift, usando43 como referencia vigente y36 para medir el aporte de los ocho vinculos. No se ejecutan nuevos experimentos por este registro. Cero nuevos fits, APIs, creditos o envios automaticos.

## Cinco listas de43 preparadas — 2026-10-10

Entrega44, cinco CSV por las semillas originales. Misma mezcla50/50 y corte>2,75%; modelos y predicciones reutilizados, cero fits/API/creditos. Adjuntar cinco archivos juntos con `submit EnsembleVinculos197Semillas5Corte275_20261010_095402`. Pendiente envio manual y resultado. La media de ganancias de cinco listas difiere de la ganancia de la lista promedio43, que sigue como referencia publica $100.815.000. [Informe](tp_primera_entrega/salidas/01_entregas_bot/44_EnsembleVinculos197Semillas5Corte275_20261010_095402/INFORME.md).

# Entrega44: cinco listas de43

Una lista por semilla de LightGBM197, mezclada50/50 con el mismo TabPFN202 guardado. Cinco semillas originales, corte>2,75%, abril+mayo->agosto. Reutiliza probabilidades y modelos finales de43: cero entrenamiento, API o creditos.

```text
  seed  contactos  comunes_con43  agregados_vs43  retirados_vs43
541440      10328           9655             673             749
408476      10404           9717             687             687
741961      10493           9718             775             686
248865      10257           9621             636             783
717444      10295           9634             661             770
```

Comando: `submit EnsembleVinculos197Semillas5Corte275_20261010_095402`. Adjuntar los CINCO CSV de `adjuntos/` en la misma entrega, sin encabezado ni indice. No adjuntar predicciones_agosto.csv ni el CSV original de43. No enviado automaticamente.

El Bot informa media/desvio de cinco GANANCIAS, una por lista.43 obtuvo $100.815.000 con UNA lista construida promediando probabilidades antes del corte. Esta nueva media puede ser distinta; no es una estimacion del desvio de aquella lista fija. Solo varia LightGBM; TabPFN es compartido. Sin intervalo de confianza ni garantia de private.

Mayo: media de cinco listas total $266,530,000, equivalente25% $66,632,500; lista de probabilidades promediadas total $272,222,500. Mayo reutilizado. Cinco scores reconstruidos desde archivos, todos los CSV reproducidos con hash identico y codigo firmado archivado.43 y sus fuentes permanecen intactas y siguen siendo la mejor referencia publica.

## Cinco ensembles completos de43 preparados — 2026-10-10

Entrega45: cinco CSV, cada uno promedia cinco LightGBM197 y mezcla50/50 con TabPFN202 guardado,corte>2,75%. Grupo1 identico a43, cuatro grupos nuevos con semillas disjuntas y congeladas.20fitsLightGBM nuevos,ceroAPI/creditos. Pedido corregido respecto de44 (unLightGBM por lista). Usar solo los cinco archivos de45 con `submit EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912`; pendientes de envio manual y resultado. Mejor publica43 $100.815.000 preservada. [Informe](tp_primera_entrega/salidas/01_entregas_bot/45_EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912/INFORME.md).

# Entrega45: cinco ensembles completos de43

Cada uno: 50% promedio de cinco LightGBM197 +50% TabPFN202 compartido; corte>2,75%. Grupo1 usa las cinco semillas originales y reproduce exactamente43 ($100.815.000 publico). Otros cuatro grupos usan veinte semillas nuevas de RNG congelado, sin seleccion por rendimiento.25modelosLightGBM totales:5reutilizados y20nuevos,273arboles,abril+mayo->agosto; ceroAPI/creditos/nuevosfitsTabPFN.

```json
{
  "1": [
    541440,
    408476,
    741961,
    248865,
    717444
  ],
  "2": [
    214496,
    872187,
    288806,
    30768,
    114359
  ],
  "3": [
    29607,
    487203,
    291337,
    337684,
    737692
  ],
  "4": [
    690079,
    103262,
    475716,
    351923,
    216890
  ],
  "5": [
    254425,
    205348,
    339033,
    482105,
    455426
  ]
}
```

```text
 ensemble  contactos  comunes_con43  agregados_vs43  retirados_vs43
        1      10404          10404               0               0
        2      10316           9855             461             549
        3      10381           9877             504             527
        4      10390           9897             493             507
        5      10286           9829             457             575
```

Comando: `submit EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912`. Adjuntar los CINCO CSV de `adjuntos/` juntos, sin encabezado ni indice. No adjuntar archivos de44 ni predicciones_agosto.csv. No enviado automaticamente.

44 preparaba cinco listas con un solo LightGBM cada una y TabPFN; esta entrega corresponde al pedido corregido de cinco ensembles completos con cinco LightGBM cada uno.44 se conserva como alternativa y no se incluye en este envio.

El Bot informara media/desvio de cinco ganancias de ensembles. Grupos distintos de semillas pero mismos datos y TabPFN: no es un intervalo de confianza ni garantia privada. Grupo1 ya seleccionado previamente por score publico; las otras cuatro replicas nuevas no fueron seleccionadas por rendimiento. Resultado de nuevos grupos y su media desconocidos. No se ejecuta nueva validacion local: pedido de replicas finales, sin tuning de parametros/corte/pesos ni seleccion de ganadores.

Matrices197 identicas a43, fuentes de vinculos auditadas por lookup independiente, cinco modelos originales reproducidos,25modelos recargados,cinco mezclas reconstruidas por producto matricial y CSV reproducidos con hash identico. Fuente43,modelos y su lista preservados. Codigo firmado archivado.

## Resultado44 y cinco ensembles completos45 — 2026-10-10

44: media publica **$94.495.500**, desvio entre cinco listas **$2.864.200**. Queda $6.319.500 debajo de43 ($100.815.000), que conserva la mejor referencia y el objetivo publico alcanzado. Resultado repetido por el usuario con mismos valores; registrado una sola vez. 44 usa una semilla LightGBM197 y TabPFN compartido por lista;43 usa el promedio de cinco LightGBM antes del corte. No intercambiar estas dos metricas ni interpretar el desvio44 como desvio de la lista fija43.

El pedido corregido de cinco ensembles completos ya esta preparado como45: cada uno promedia cinco LightGBM197, mezcla50/50 con el mismo TabPFN y corte>2,75%. Grupo1 reproduce43 exactamente; otros cuatro usan veinte semillas nuevas congeladas. Pendiente envio manual de los cinco CSV de45 juntos y resultado. Public gain ya corresponde al25%, sin volver a dividir. Este registro no agrega fits/API/creditos/envios.

## Resultado45: cinco ensembles completos — 2026-10-10

**Media publica $96.838.500, desvio $2.037.600**, cinco ensembles completos. Resultado atribuido a45 por contexto inmediato; el usuario no repite numero. Media $3.976.500 debajo de43 ($100.815.000) y $1.336.500 debajo de36 ($98.175.000). Frente a44 (media $94.495.500/desvio $2.864.200), la media es $2.343.000 mayor y el desvio $826.600 menor. Las tandas usan grupos distintos: no es comparacion pareada que aisle la agregacion.

Grupo1 reproduce43; grupos2-5 promedian cinco LightGBM197 con semillas nuevas, todos mezclados50/50 con el mismo TabPFN202 y corte>2,75%. La lista43 conserva la mejor referencia publica y el objetivo publico alcanzado; su $100.815.000 no representa la media entre replicas observada. Primera replica seleccionada previamente por score; nuevas replicas sin seleccion por rendimiento. No hay resultados individuales informados para identificar la mejor de las cuatro nuevas. Desvio entre cinco ensembles no es intervalo de confianza ni garantia privada.

Tanda de distribucion completada. Proximo trabajo pendiente: retomar plan de experimentos, preservando43 y reportando estabilidad ademas del mejor resultado.40 sigue sin resultado informado. Public gain ya corresponde al25%, sin volver a dividir. Registro sin nuevos fits/API/creditos/envios.

## Control pareado de vinculos preparado — 2026-10-10

Entrega46: cinco ensembles sin las ocho features vinculos, mismos grupos y resto configuracion que45.20fitsLightGBM nuevos,5reutilizados,ceroAPI/creditos. Grupo1 CSV identico a36. Bot solo muestra resumen: comparar aporte promedio = $96.838.500 -mediaControl; no cambios individuales ni desvio pareado calculables. Pendiente envio manual de cinco CSV juntos con `submit ControlHist189CincoEnsemblesPareados45_20261010_100721` y resultado. [Informe](tp_primera_entrega/salidas/01_entregas_bot/46_ControlHist189CincoEnsemblesPareados45_20261010_100721/INFORME.md). Mejor publica43 preservada.

# Entrega46: control pareado sin ocho vinculos

Control de45: mismos cinco grupos de cinco semillas, abril+mayo->agosto, LightGBM189 sin ocho features vinculos frente a197 de45. Mismos params273arboles,target combinado, TabPFN202 identico, pesos50/50,corte>2,75%,promediar probabilidades antes del corte en cada grupo. Grupo1 reproduce36 exactamente ($98.175.000 conocido); candidato grupo1 reproduce43 ($100.815.000),delta+$2.640.000. Otros cuatro controles nuevos:20fitsLightGBM,5reutilizados,ceroAPI/creditos.

```text
 ensemble  control_contactos  candidato_contactos  comunes  agregados_por_vinculos  retirados_por_vinculos
        1              10420                10404     9873                     531                     547
        2              10339                10316     9818                     498                     521
        3              10376                10381     9859                     522                     517
        4              10311                10390     9818                     572                     493
        5              10345                10286     9759                     527                     586
```

Adjuntar los CINCO CSV de `adjuntos/` juntos con `submit ControlHist189CincoEnsemblesPareados45_20261010_100721`. Pendiente envio manual; no adjuntar predicciones_agosto.csv.

Metrica primaria: **aporte promedio de vinculos = $96.838.500 (media45) menos media de esta entrega**. Positivo favorece197; negativo favorece189. Bot solo informa media/desvio, confirmado por usuario. Diferencia de medias es media de cinco diferencias pareadas, pero NO conocemos las diferencias individuales ni su desvio. No restar desvios ni calcular intervalo asumiendo independencia; depende de covarianza entre pares.

Grupo1 previamente seleccionado por desempeno; otros cuatro grupos congelados sin elegir por score. Publico reutilizado, resultado exploratorio; no prueba independiente ni garantia privada. No nueva validacion local: control final de replicas publicas. Conservar43 como mejor publica, sin presentar $100.815.000 como rendimiento tipico.

Matrices/target originales verificados, modelos recargados, TabPFN y grupos identicos a45,candidato45 reconstruido,mezclas verificadas por producto matricial y cinco CSV reproducidos con hashes identicos. Grupo1 payload identico a36; fuentes conservadas y codigo firmado archivado.

## Control46: aporte promedio de vinculos completado — 2026-10-10

| Variante | Entrega | Media publica | Desvio entre cinco ensembles |
|---|---:|---:|---:|
| Con ocho vinculos197 |45|$96.838.500|$2.037.600|
| Sin ocho vinculos189 |46|$96.690.000|$943.700|

Mismos cinco grupos de semillas, datos abril+mayo->agosto,target combinado,273arboles, params,TabPFN202,pesos50/50 y corte>2,75%. **Aporte promedio de vinculos: +$148.500**, aproximadamente0,154% frente al control. Desvio marginal observado mayor con vinculos; no confundir diferencia de desvios marginales con desvio de diferencias pareadas.

**Grupo1 conocido:**43 $100.815.000 contra36 $98.175.000,delta+$2.640.000. **Otros cuatro grupos:** media con vinculos derivada aprox.$95.844.375, sin vinculos aprox.$96.318.750,delta promedio aprox.**-$474.375**. Derivacion: (5*delta promedio total -delta grupo1)/4. Aproximado por redondeo de agregados. La gran ventaja del grupo1 no se sostuvo en promedio en los cuatro grupos nuevos. No sabemos que grupos particulares mejoran ni cuantos: Bot solo devuelve resumen. No inferir significancia o intervalo de confianza sin resultados individuales/covarianza.

Conservar43 como mejor lista publica y objetivo100M alcanzado, sin atribuir su valor al rendimiento tipico. No declarar ocho vinculos como mejora consistente. Control189 de46 queda disponible para proximas comparaciones; conservar ambos lados y mismos grupos. Publico reutilizado y primer grupo previamente elegido; evaluacion exploratoria, no test independiente. Resultado46 atribuido por contexto inmediato. Registro sin nuevos fits/API/creditos/envios; public gain ya corresponde al25%, sin volver a dividir.40 sin resultado informado.

# Piloto TabPFN210 preparado — 2026-10-10

TabPFN202 guardado frente a210 con ocho vinculos; abril->mayo,targetBAJA+2,modelo v3.5-fast,dos estimadores,seed214363. LightGBM189 sin vinculos y cinco grupos identicos a45/46;20modelos locales reutilizados y5nuevos. Pesos50/50,corte>2,75%,sin tuning. Payload210 y controles verificados; no nuevas llamadas API ni creditos. Cotizacion/autenticacion pendientes. Limite preventivo local50.000creditos; no etapa final/agosto por este piloto.

Evaluacion prevista: cinco ganancias por ensemble,delta pareado y promedio,grupo1 vsotros cuatro,media de25listas individuales y cuatro partes de clientes. Mayo reutilizado y control202 historico; no garantia publica. Scripts138 cotiza/infiere y139 evalua. Fuente43 conservada como mejor publica; no promover por un solo grupo.

# TabPFN210 vs202 local

{
  "estado": "completo_verificado",
  "ensembles": [
    {
      "ensemble": 1,
      "control": {
        "contactos": 9906,
        "tp": 498,
        "fp": 9408,
        "ganancia_total": 275385000,
        "ganancia_25pct": 68846250.0
      },
      "candidato": {
        "contactos": 10241,
        "tp": 503,
        "fp": 9738,
        "ganancia_total": 271672500,
        "ganancia_25pct": 67918125.0
      },
      "delta_total": -3712500
    },
    {
      "ensemble": 2,
      "control": {
        "contactos": 9942,
        "tp": 493,
        "fp": 9449,
        "ganancia_total": 268895000,
        "ganancia_25pct": 67223750.0
      },
      "candidato": {
        "contactos": 10234,
        "tp": 503,
        "fp": 9731,
        "ganancia_total": 271865000,
        "ganancia_25pct": 67966250.0
      },
      "delta_total": 2970000
    },
    {
      "ensemble": 3,
      "control": {
        "contactos": 9892,
        "tp": 495,
        "fp": 9397,
        "ganancia_total": 272470000,
        "ganancia_25pct": 68117500.0
      },
      "candidato": {
        "contactos": 10259,
        "tp": 505,
        "fp": 9754,
        "ganancia_total": 273377500,
        "ganancia_25pct": 68344375.0
      },
      "delta_total": 907500
    },
    {
      "ensemble": 4,
      "control": {
        "contactos": 9881,
        "tp": 494,
        "fp": 9387,
        "ganancia_total": 271672500,
        "ganancia_25pct": 67918125.0
      },
      "candidato": {
        "contactos": 10216,
        "tp": 506,
        "fp": 9710,
        "ganancia_total": 275660000,
        "ganancia_25pct": 68915000.0
      },
      "delta_total": 3987500
    },
    {
      "ensemble": 5,
      "control": {
        "contactos": 9974,
        "tp": 498,
        "fp": 9476,
        "ganancia_total": 273515000,
        "ganancia_25pct": 68378750.0
      },
      "candidato": {
        "contactos": 10288,
        "tp": 503,
        "fp": 9785,
        "ganancia_total": 270380000,
        "ganancia_25pct": 67595000.0
      },
      "delta_total": -3135000
    }
  ],
  "media_delta_ensembles": 203500.0,
  "media_delta_grupos2a5": 1182500.0,
  "ensembles_mejoran": 3,
  "desvio_poblacional_delta_ensembles": 3128847.471514072,
  "media_delta_listas_individuales": -1012000.0,
  "partes": [
    {
      "ensemble": 1,
      "parte": 0,
      "delta_total": -3382500
    },
    {
      "ensemble": 1,
      "parte": 1,
      "delta_total": -1732500
    },
    {
      "ensemble": 1,
      "parte": 2,
      "delta_total": -1402500
    },
    {
      "ensemble": 1,
      "parte": 3,
      "delta_total": 2805000
    },
    {
      "ensemble": 2,
      "parte": 0,
      "delta_total": -1815000
    },
    {
      "ensemble": 2,
      "parte": 1,
      "delta_total": 1540000
    },
    {
      "ensemble": 2,
      "parte": 2,
      "delta_total": 1787500
    },
    {
      "ensemble": 2,
      "parte": 3,
      "delta_total": 1457500
    },
    {
      "ensemble": 3,
      "parte": 0,
      "delta_total": -2502500
    },
    {
      "ensemble": 3,
      "parte": 1,
      "delta_total": -2887500
    },
    {
      "ensemble": 3,
      "parte": 2,
      "delta_total": 5830000
    },
    {
      "ensemble": 3,
      "parte": 3,
      "delta_total": 467500
    },
    {
      "ensemble": 4,
      "parte": 0,
      "delta_total": -962500
    },
    {
      "ensemble": 4,
      "parte": 1,
      "delta_total": -907500
    },
    {
      "ensemble": 4,
      "parte": 2,
      "delta_total": 4125000
    },
    {
      "ensemble": 4,
      "parte": 3,
      "delta_total": 1732500
    },
    {
      "ensemble": 5,
      "parte": 0,
      "delta_total": -3080000
    },
    {
      "ensemble": 5,
      "parte": 1,
      "delta_total": -357500
    },
    {
      "ensemble": 5,
      "parte": 2,
      "delta_total": -962500
    },
    {
      "ensemble": 5,
      "parte": 3,
      "delta_total": 1265000
    }
  ],
  "api_estado": {
    "estado": "completo_verificado",
    "datos_enviados": true,
    "cotizacion": {
      "estimated_cost": 41636,
      "pricing_version": "quota_v3",
      "inputs": {
        "train_rows": 163284,
        "raw_columns": 210,
        "test_rows": 163768,
        "model_version": "v3.5-fast",
        "operation": "predict",
        "n_estimators": 2,
        "thinking_effort": null
      }
    },
    "max_creditos": 50000,
    "cuota_antes": "Currently, you have used 1449717 of the allowed limit of 20000000 credits. The limit will reset at 2026-11-01 00:00:00 UTC.",
    "final_agosto": false,
    "cuota_despues": "Currently, you have used 1491353 of the allowed limit of 20000000 credits. The limit will reset at 2026-11-01 00:00:00 UTC.",
    "classes": [
      0,
      1
    ],
    "predicciones_sha256": "d0125ea237a6a24d3a95184ff3327449b6d0646adf8f0d0e3a6c58a8a1801f70"
  },
  "final_agosto_ejecutado": false,
  "limitacion": "Mayo reutilizado y API control historica; no test independiente, no garantia publica. No modificar corte por estos resultados."
}

# Piloto local: ocho v?nculos en TabPFN

Resultado mixto, sin evidencia suficiente para promover TabPFN210 como mejora consistente. Mantener LightGBM189 + TabPFN202 como control para las pr?ximas pruebas y conservar la entrega43 como mejor lista p?blica hist?rica.

| Ensemble | Control TabPFN202 | TabPFN210 con v?nculos | Diferencia total |
|---|---:|---:|---:|
| 1 | $275.385.000 | $271.672.500 | $-3.712.500 |
| 2 | $268.895.000 | $271.865.000 | $2.970.000 |
| 3 | $272.470.000 | $273.377.500 | $907.500 |
| 4 | $271.672.500 | $275.660.000 | $3.987.500 |
| 5 | $273.515.000 | $270.380.000 | $-3.135.000 |

Media control: $272.387.500. Media candidata: $272.591.000. Diferencia: $203.500 (0.075%). Mejoran 3 de 5 ensembles. Otros cuatro grupos, excluyendo el grupo1 hist?rico: diferencia media $1.182.500.

Las 25 listas de una sola semilla empeoran en promedio $-1.012.000. Desv?o poblacional de las cinco diferencias: $3.128.847; es dispersi?n entre grupos, no un intervalo de confianza. La mejora promedio es peque?a frente a esa dispersi?n.

Comparaci?n abril?mayo, target TabPFN BAJA+2, 202 frente a210 variables. LightGBM189 sin v?nculos, cinco grupos de cinco semillas id?nticos a45/46, pesos50/50 y corte estricto >0,0275. Solo se sustituyeron las predicciones de TabPFN. Mayo ya se us? en desarrollo y el control TabPFN es hist?rico; evaluaci?n exploratoria, no test independiente. Los valores de la tabla son ganancias sobre todo mayo, no Public gain del Bot.

Consumo comprobado: 41,636 cr?ditos (cuota 1,449,717 ? 1,491,353); coincide con la cotizaci?n y queda bajo el m?ximo50.000. Env?o expl?citamente autorizado en AUTORIZACION_ENVIO.json. No se ejecut? agosto ni se cre? entrega nueva.

Siguiente paso recomendado: no gastar en agosto de esta variante por ahora; retomar el plan pendiente de calidad/drift. Si se decide explorar el p?blico pese al resultado mixto, cotizar y autorizar por separado la corrida final. No ajustar el corte con este piloto.

Detalle y auditor?a: RESULTADO_LOCAL.json, api_estado.json, deltas_listas_individuales.csv, deltas_partes.csv y predicciones_evaluadas_mayo.csv.

# Auditoría de calidad y drift — 10 de octubre de 2026

Auditoría inicial completa: 983.061 filas, seis meses y21predictores. Sin etiquetas, entrenamientos, API ni créditos. La primera prueba recomendada es aislar la corrección conocida de `ccajas_depositos` de mayo sobre LightGBM189. No hay sustento suficiente para corregir automáticamente los ceros de mora.

| Campo | Mes | Hallazgo | Evidencia y regla |
|---|---|---|---|
| ccajas_depositos | 202105 | 163.768/163.768 filas cero; abril1,332% y agosto3,540% positivos. | CSV agregado, aviso de catedra registrado en config y auditoria88; 2.164 clientes comunes con abril pasan de positivo a cero. Regla ya existente: convertir a NA solamente mayo antes de historicos. Probar aisladamente sobre189; no presentarla como descubrimiento nuevo. |
| Visa_Finiciomora | 202105 / 202108 | 3.222 / 3.249 ceros frente a cero en abril; nulos bajan99,126% a97,347% /97,472%. | En clientes comunes abril->mayo:3.162 nulos pasan a cero y48 no ceros pasan a cero. Mayo3.209 ceros en cuentas abiertas. No convertir automaticamente ceros a NA. El diccionario no documenta codigo cero; pedir o localizar evidencia adicional antes de una correccion. |
| Master_Finiciomora | 202103–202108 | Mayormente nulo; solamente1 cero en junio. No replica el salto de Visa. | Diccionario dice dias desde inicio de mora para Master y dias para inicio para Visa; diferencias mensuales no prueban error. Preservar faltantes; no aplicar a Master una regla de Visa ni rellenar por cero. |
| cprestamos_personales / mprestamos_personales | 202103–202108 | Prestamos positivos bajan22,010% a20,685%; monto q99 sube521.516 a586.500. | Notebook arboles/z0607 celdas38/60 elimina ambos por drift; cuaderno z701 analiza distribucion y target. No demuestra error de captura. No limpiar ni eliminar automaticamente. Sin nueva ablacion: sin_prestamos ya se probo en script63 y carpeta features_local. |
| Visa_Fvencimiento / Master_Fvencimiento | varios / 202108 | Extremos de aproximadamente-2,9millones de dias, incompatibles con vencimiento de plastico. | Diccionario indica dias; baseline.preparar ya reemplaza valores<-36.500 por NA. Mantener regla conservadora existente, no nueva candidata. No borrar todos los negativos. |
| conteos auditados y status de tarjetas | 202103–202108 | Sin conteos negativos/fraccionarios ni status fuera{0,6,7,9}; sin infinitos en21campos auditados. | Tabla distribuciones_mensuales.csv; alcance limitado a21predictores, no todo el dataset. Sin correccion nueva. |

La base189 conserva la preparación histórica de scripts63/66 (`baseline.preparar`), sin la corrección mayo de caja. Los ensayos de cátedra89/99/101 y segmentación108 sí usan `calidad_datos`; eso no equivale a una comparación aislada de esa corrección en189. La entrega43 y las demás fuentes históricas permanecen intactas.

PSI: abril como referencia fija, deciles finitos con extremos infinitos y bin faltante separado, suavizado1e-6. Campos discretos o con muchos ceros tienen menos bins. PSI alto no demuestra error; PSI bajo no garantiza estabilidad del vínculo con churn. No se usaron etiquetas para investigar ese vínculo. El uso de splits/gain de modelos guardados indica participación predictiva, no dinero ni causalidad.

Próxima comparación congelada: abril→mayo, mismos cinco modelos189 guardados, TabPFN202 guardado, pesos50/50 y corte>2,75%; único cambio `ccajas_depositos=NA` en mayo. Abril no cambia y ccajas no pertenece a las fuentes históricas, por lo que se pueden reutilizar los modelos abril sin reentrenar. Reproducir primero el control$275.385.000 y reportar lista promedio5, cinco listas individuales y cuatro partes. Es una sensibilidad de inferencia local; no mide el efecto de reentrenar abril+mayo corregidos para agosto. No ajustar cortes ni tocar TabPFN ni borrar mora/préstamos en esa comparación.

Intentos previos conservados: el primero detuvo por cuatro nombres de columnas incorrectos antes de leer filas; el segundo detuvo en una verificación de dtype entero→float al introducir NA. La versión3 verificó igualdad de valores fuera de mayo y regla idempotente. No se alteró la hipótesis según ganancias: ninguno consultó etiquetas.

Artefactos: campo_mes_evidencia_regla.csv, distribuciones_mensuales.csv, mora_por_estado.csv, clientes_comunes_abril.csv, psi_abril_fijo.csv, uso_modelos189_guardados.csv, PLAN.json y manifest.json.

# Sensibilidad de depósitos de caja sobre LightGBM189

Control promedio5: $275.385.000, 9906 contactos, 498 BAJA+2. Candidato mayo=NA: $275.385.000, 9906 contactos, 498 BAJA+2. Diferencia total: $0; diferencia25%: $0.

Media de diferencias en cinco listas individuales: $0. Mejoran 0/5 semillas y 0/4 partes. Agregados 0, retirados 0.

| Semilla | Diferencia total | Splits ccajas | Probabilidades modificadas |
|---|---:|---:|---:|
| 541440 | $0 | 0 | 0 |
| 408476 | $0 | 0 | 0 |
| 741961 | $0 | 0 | 0 |
| 248865 | $0 | 3 | 0 |
| 717444 | $0 | 2 | 0 |

Único cambio: ccajas_depositos de mayo=NA. Abril idéntico y ccajas no es fuente histórica; cinco modelos273árboles reutilizados con hashes verificados. TabPFN202 guardado sin cambios, pesos50/50, corte estricto>2,75%, mismos clientes/labels/partes. Control$275.385.000 reproducido; matriz idéntica salvo la columna, ganancias verificadas por recarga y producto matricial. Cero fits/API/créditos/submits. Valores totales de mayo y escalado25% ilustrativo, no Public gain del Bot.

Esta sensibilidad no aporta mejora consistente; no promover ni crear entrega. La regla de calidad conocida se conserva, pero el efecto de reentrenar abril+mayo corregidos queda sin medir.

Mayo y semillas ya reutilizados; no test independiente. No se modifica el corte ni se corrigen mora/préstamos. Fuentes históricas y entrega43 preservadas.

Comprobaci?n adicional de ?rboles: tres modelos no usan ccajas; los otros dos tienen cinco splits en total, todos con umbral positivo cercano a cero, decisi?n <= y default_left=True. En estos modelos cambiar cero por NA deja las predicciones exactamente iguales para los 163.768 clientes de mayo. Delta$0 en lista promedio, cinco listas y cuatro partes. No extrapolar a reentrenamiento final.

# Canaritos: diagnóstico y comparación de un bloque

No promover el bloque retirado: no mejora simultáneamente la lista promedio5 y la media de cinco listas individuales. Mantener LightGBM189 + TabPFN202.

| Variante | Ganancia total mayo, lista promedio5 | Diferencia vs189 | Media diferencia en listas individuales |
|---|---:|---:|---:|
| Control189 | $275.385.000 | $0 | $0 |
| 189 +19canaritos (diagnóstico) | $267.217.500 | $-8.167.500 | $-10.439.000 |
| 181, sin el bloque de8, sin canaritos | $259.160.000 | $-16.225.000 | $-10.312.500 |

Ablación181: mejoran 1/5 semillas y 0/4 partes. Contactos 9906→9936; BAJA+2 498→484. Agregados 534, retirados 504.

## Diagnóstico

Los19canaritos uniformes recibieron entre18.81% y20.08% del gain de entrenamiento (media19.51%). Es importancia de splits, no dinero ni información real sobre churn. 152/189 variables quedaron por debajo de la mediana de ruido en al menos cuatro semillas. No retirar esas152 variables: ruido continuo tiene más oportunidades de corte que muchos conteos/indicadores y existe redundancia entre variables.

La regla fijada antes de observar ganancias eligió solamente las ocho primeras variables por mediana de gain y nombre, con al menos4/5 semillas debajo de ruido:

- `ccajas_depositos`
- `ccajeros_propios_descuentos`
- `ccheques_depositados_rechazados`
- `ccheques_emitidos_rechazados`
- `ccuenta_corriente`
- `cliente_vip`
- `cpagodeservicios`
- `cpayroll2_trx`

El bloque se congeló a partir del entrenamiento abril antes de las permutaciones de mayo; no se probaron otros bloques según su ganancia.

Permutación conjunta bloquedebil, tres órdenes fijos en mayo: pérdida AP combinado media0.00003779; pérdida AP BAJA+2 media0.00000746; pérdida ganancia media$36.667. Pérdida positiva significa que permutar empeora; son variaciones exploratorias, no significancia.

Permutación conjunta bloquecanaritos, tres órdenes fijos en mayo: pérdida AP combinado media0.00001014; pérdida AP BAJA+2 media0.00076323; pérdida ganancia media$-4.876.667. Pérdida positiva significa que permutar empeora; son variaciones exploratorias, no significancia.

No elegir el orden aleatorio que produjo mayor ganancia ni promover probabilidades permutadas: los canaritos no contienen señal por construcción y las variaciones ilustran sensibilidad al azar. La caída al agregar ruido tampoco se atribuye únicamente a sobreajuste: agregar columnas cambia la competencia de variables con feature_fraction fijo.

## Comparación181 sin ruido

| Semilla | Diferencia total |
|---|---:|
| 541440 | $715.000 |
| 408476 | $-16.692.500 |
| 741961 | $-17.270.000 |
| 248865 | $-11.137.500 |
| 717444 | $-7.177.500 |

Dos planes separados congelados:143 para el diagnóstico,144 para una única ablación. Abril→mayo, target LightGBM combinado, TabPFN202 BAJA+2 guardado,273árboles y mismos parámetros/semillas, pesos50/50, corte>2,75%. No se aplicó la corrección ccajas ni otras limpiezas para aislar la retirada de columnas. Control189, filas, modelos, código, matrices, probabilidades y ganancias verificados. Cinco fits diagnósticos y cinco fits181; cero API/créditos/submits y ningún entrenamiento agosto. Modelos originales y entrega43 preservados.

Mayo y semillas ya reutilizados; no test independiente. Los valores son ganancia total mayo, no Public gain. No podar automáticamente ni convertir estos resultados en garantía pública.

## Resultado publico40 registrado — 2026-10-10

Cuatro señales de débitos/pagos, LightGBM193 +TabPFN202, promedio5,50/50,corte>2,75%: **$97.185.000**, desvio0, una lista. Frente36($98.175.000), **-$990.000**; frente43($100.815.000), **-$3.630.000**. No mejora al control36; bloque servicios193 cerrado tras prueba exploratoria pública. Conservar evidencia local: lista promedio+$137.500 total, media listas individuales-$7.018.000. Mejor entrega pública43 y base de comparación189+TabPFN202 conservadas. Desvio0 por única lista, no estabilidad. Importes públicos ya25%, no dividir otra vez. Pendiente40 resuelto. Plan segmentación/vínculos/calidad/canaritos completado; targets invertidos202 sigue reservado, reentrenamiento con mayo corregido sin evaluar, semántica de ceros mora sin confirmar. Registro sin nuevos fits/API/créditos/envíos.

# Targets invertidos202, corte2,75% preparados ? 2026-10-10

LightGBM202 BAJA+2 +TabPFN202 BAJA+1/BAJA+2; promedio cinco LightGBM y mezcla50/50, score estricto>0,0275 fijado por el usuario. Cinco modelos finales abril+mayo?agosto completos y verificados. Se conserva la preparaci?n202 hist?rica, sin v?nculos ni nueva correcci?n ccajas.

Local abril?mayo: control202 total$267,217,500; invertido202 total$268,702,500; diferencia$1,485,000; media diferencias en cinco listas$4,691,500.0. Frente al control189 actual de$275.385.000, diferencia$-6,682,500; esa comparaci?n tambi?n cambia features. Valores totales de mayo, no Public gain. Mayo/semillas reutilizados.

Payload API: matriz327.052?202 abril+mayo y target combinado;164.647?202 agosto. Sin ID/mes/labelsagosto. Cotizaci?n74.179cr?ditos; l?mite propuesto80.000. Autorizaci?n espec?fica solicitada, todav?a pendiente; no nuevos datos enviados a inferencia ni cr?ditos consumidos.

Despu?s de autorizar: script148 --ejecutar y script149 generan una ?nica lista promedio5 de cinco modelos, comparable en agregaci?n/corte con43. Resultado p?blico desconocido. Fuentes y mejor43 conservadas.

# Entrega47: targets invertidos202

LightGBM BAJA+2 y TabPFN combinado, ambos202variables, abril+mayo→agosto. Promedio5 LightGBM, mezcla50/50 y score>2,75%. 10609clientes. Un solo CSV; no representa distribucion entre ensembles.

Consumo TabPFN: 74179creditos. Resultado público pendiente. Mejor43 conservada.

Comando: `submit EnsembleInvertidos202Promedio5Corte275_20261010_170851`.

Verificaci?n final47:10.609clientes, CSV reproducido byte a byte, mezcla reconstruida desde componentes y selecci?n id?ntica. Consumo74.179cr?ditos confirmado, m?ximo80.000. Autorizaci?n expl?cita y estado API archivados en la entrega. Cambios contra43: 1109agregados, 904retirados; no garantiza ganancia. Pendiente env?o manual de un solo CSV promedio5. Mejor43 preservada.

## Resultado público47: targets invertidos202 — 2026-10-10

**$99.110.000**, desvio0, una lista promedio5 de10.609clientes. LightGBM202 BAJA+2 +TabPFN202 combinado,50/50,>2,75%,abril+mayo→agosto. Frente36($98.175.000): **+$935.000**. Frente43($100.815.000): **-$1.705.000**. Esta entrega queda$890.000 por debajo de100M; el objetivo ya se alcanzó con43, que sigue como mejor pública. No interpretar desvio0 como estabilidad. Comparación contra36 cambia también189→202, por lo que no aisla efecto de los targets. Conservar local: invertido202$268.702.500 total, control202$267.217.500,delta+$1.485.000; contra189$275.385.000,delta-$6.682.500. Importes públicos ya25%, no dividir nuevamente. Candidato reservado resuelto en esta configuración; no nuevas API/créditos/fits/envíos por registro. Historial, CSV, modelos y mejor43 preservados. Reentrenar con mayo corregido sigue sin evaluar; semántica de ceros mora sigue sin confirmar.

## Entrega 48: TabPFN v3.5 frente a43

Cambio exclusivo de version TabPFN v3.5-fast a v3.5;202variables,targetBAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. Cinco LightGBM197 originales de43, targetcombinado; mezcla50/50,promedio5,corteestricto>2,75%. 10834clientes; 10192comunes con43,642agregados,212retirados. Consumo real 151033creditos, limiteautorizado160.000. Sin validacion local nueva para esta version; resultado publico pendiente. Paquete43 publicado y mejorpublica100.815M conservados. Una lista no mide distribucion entre ensembles. Sin envio automatico al Bot.

Comando: `submit EnsembleVinculos197TabPFN35Promedio5Corte275_20261010_172925`. Adjuntar solo `adjuntos/EnsembleVinculos197TabPFN35Promedio5Corte275_20261010_172925.csv`.

## Resultado publico48: TabPFN v3.5 — 2026-10-10

**$98.862.500**, desvio0, una lista promedio5 de10.834clientes. Frente43($100.815.000): **-$1.952.500**; frente47($99.110.000): -$247.500; frente36($98.175.000): +$687.500. Cambio exclusivo de version TabPFN v3.5-fast a v3.5,202variables,BAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. Se reutilizaron los cinco LightGBM197 de43,mezcla50/50,corte>2,75%. Consumo151.033creditos; no mejoro la referencia43 en este publico. No generalizar a superioridad de una version ni interpretar desvio0 como estabilidad. Prueba cerrada. Mejor43 y su paquete GitHub se conservan como final elegida; sin nuevas API,fits,creditos o envios por este registro.

## Cierre entrega final43 ? 2026-10-10

Tomas responde listo tras la indicacion de reenviar43 como ultima entrega; se registra la confirmacion por contexto. El resultado historico de43 es$100.815.000, sin nuevo resultado del reenvio informado. Paquete GitHub reproducible publicado, con instrucciones de key propia de la catedra. CSV original verificado sin modificaciones.

## Validacion del paquete43 en ambiente limpio ? 2026-10-10

Clon nuevo deGitHub,commit6ea5f3dc13b4e5f7e83953bbf478997a17cd8218;21hashes correctos. Dos entornos Python3.14.6 vacios, instalacion sin cache y pipcheck sin conflictos. Corrida rapida e inferencia197desde dataset generan CSV identico de10.404clientes; error maximo0 en los cincoLightGBM. TabPFN202 reconstruye hashes originales de matrices/target y cotiza74.179creditos; inferenciaAPI nueva no ejecutada, pendiente de autorizacion de costo adicional. Informe en tp_primera_entrega/salidas/validacion_limpia43_20261010/RESULTADO.json.

Validacion limpia43 cerrada por Tomas con las pruebas locales verificadas. Se omite explicitamente la nueva inferencia remota TabPFN; no queda pendiente para esta validacion y no se consumieron creditos de inferencia. CSV final exacto, modelos y preparacion TabPFN comprobados; no se afirma verificacion de una respuesta remota nueva.
