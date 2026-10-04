# TP - Primera entrega - BAJA+2

Entrega indicada: domingo 11 de octubre de 2026.
Fuente: `data/competencia_01.csv` (se conserva sin modificar).

## Archivos de trabajo

### Estado del workspace al 2026-10-04

- TabPFN API: Fast con 2 estimadores e históricas ampliadas (202 variables)
  obtuvo 380.792.500 en junio, frente a 354.227.500 con originales de 2.
  Junio está expuesto: comparación exploratoria. No hay predicción final de agosto.
- `11_tabpfn_historicas.py`: comparación originales/históricas; por defecto
  prepara localmente. `--bloque ampliadas --model-version v3.5-fast` selecciona
  el bloque de 50 históricas. `--ejecutar-api` realiza inferencias y consume cuota.
  `--etapa junio --validacion-existente <carpeta>` verifica la referencia de mayo.
- `12_auditar_features_tabpfn.py`: auditoría local, sin API ni eliminación de
  columnas. Se conservan las 202 variables.
- [Diccionario de históricas](VARIABLES_HISTORICAS_TABPFN.md): 50 nombres,
  fórmulas, faltantes y cobertura temporal. Bitácora: secciones 29–38.
- Credenciales, entornos virtuales, dataset y `salidas/` quedan fuera de Git.
  Los comandos que reutilizan corridas necesitan esos artefactos locales.
  El repositorio de trabajo todavía no constituye una entrega final reproducible.
- Pendiente consultar a la cátedra si acepta API externa y credencial temporal
  privada o acceso a un entorno preparado en Google Cloud. No publicar claves.

1. `01_feature_discovery.py`: auditoría, hipótesis y futura implementación de features.
2. `02_modelado_evaluacion.py`: particiones, baseline, experimentos, test y entrega.
3. `config.json`: rutas relativas, target, semilla y decisiones compartidas.
4. `validar_entrega.py`: verifica el CSV propuesto (dos columnas, etiquetas exactas, IDs únicos y cobertura de agosto según configuración; `--mes` permite otro mes explícito). Encabezados provisionales: `id,clase_ternaria`; separador coma. Confirmar los encabezados con la consigna antes de entregar.
5. `ejemplo_formato_entrega.csv`: tres IDs ficticios con las tres etiquetas; ilustra el formato, no contiene predicciones ni constituye una entrega real.
6. `features.py`: generadores intrames e históricos con reglas explícitas de faltantes.
7. `03_comparar_intrames.py`: compara bloques intrames con el baseline LightGBM, usando marzo y mayo.
8. `04_comparar_historicas.py`: experimento retrospectivo separado, train abril y validación mayo, con y sin historia. No modifica `config.json` ni evalúa junio.
9. `05_optuna_historicas_rf.py`: dos estudios Optuna de 30 trials (originales/históricas, abril -> mayo) y RF de referencia sin tuning. Los parámetros, trials, modelos y predicciones se guardan en una carpeta nueva de `salidas/`.
10. `06_comparacion_optuna_features.py`: completa un estudio de 30 trials con las nueve intrames juntas y consolida originales/intrames/históricas, reutilizando los estudios anteriores tras verificar su compatibilidad. No vuelve a ejecutar RF.

La bitácora de continuidad, con aciertos, resultados negativos y correcciones, es `../BITACORA_DMEYF.md`, secciones 22–24.

Agosto de 2021 es el mes de entrega confirmado por Tomás el 2 de octubre (`prediccion_mes = 202108`, `mes_base_clientes = 202108`). Reemplaza el supuesto anterior de septiembre. La foto de agosto ya está disponible en el CSV: 164.647 clientes, todos sin target conocido.

Con la definición del target implementada, BAJA+2 de agosto significa presente en agosto y septiembre, ausente en octubre. Septiembre y octubre permitirían observar la etiqueta real, pero no se requieren para construir las predicciones. Las features usan agosto y, si corresponde, julio y meses anteriores. Los targets faltantes de agosto no se convierten en negativos.

El validador usa por defecto los IDs de agosto. Los manifiestos de experimentos anteriores conservan la configuración que existía al ejecutarlos; no se reescriben esos registros históricos. Esas corridas entrenaron con marzo/abril y validaron mayo, por lo que cambiar el mes de entrega no cambia sus métricas. Todavía no se generó una entrega real para agosto.

Los archivos usan bloques `# %%`: podés ejecutarlos por partes en VS Code con el intérprete de `.venv`, o completos desde la terminal. El primero consulta el CSV con DuckDB. El segundo ejecuta `baseline.py`: entrena logística y LightGBM con marzo y evalúa mayo. Cada ejecución guarda una carpeta nueva en `salidas/`. No evalúa junio ni ejecuta Optuna.

Desde la raíz del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe .\tp_primera_entrega\01_feature_discovery.py
.\.venv\Scripts\python.exe .\tp_primera_entrega\02_modelado_evaluacion.py
```

Los bloques de comentarios conservan las hipótesis y los pasos pendientes del trabajo.

## Situación verificada el 1 de octubre

El CSV tiene 155 columnas y meses de marzo a agosto de 2021. Marzo a junio tienen target completo; julio tiene 163.245 de 164.348 filas sin target y agosto tiene todas las etiquetas faltantes. Train: marzo; validación: mayo; futuro reentrenamiento: marzo + abril; test: junio. La selección con mayo es retrospectiva porque su target se conoce en julio. Agosto es el mes de entrega confirmado. Mayo fue utilizado en experimentos previos y junio fue explorado en el EDA.

## Orden de trabajo

Acordar el protocolo temporal y la ganancia; revisar variables existentes y diccionario; implementar un baseline; evaluar hipótesis de features y modelos en validación; congelar decisiones; evaluar el test; preparar la entrega según la plantilla oficial.

Los notebooks de `monday/` son antecedentes. Esta carpeta concentra el nuevo trabajo sin modificarlos. Los artefactos generados van a `salidas/`, excluida de Git. Se agregó `lightgbm==4.7.0` a `requirements.txt` y al entorno `.venv`.

## Ganancia oficial

Matriz de la captura del PDF aportada por Tomás: predecir BAJA+2 suma 1.072.500 si la clase real es BAJA+2 y resta 27.500 en otro caso. Predecir BAJA+1 o CONTINUA aporta cero. El premio es neto. Umbral teórico con probabilidades calibradas: 0,025. La función `calcular_ganancia` está en `02_modelado_evaluacion.py`.

## Primera comparación ejecutada

Resultados en `salidas/baseline_20261001_175959/`. Train: 162.900 filas; validación: 163.768 filas con 870 BAJA+2. Se usaron las 152 variables originales, sin balancear clases ni optimizar hiperparámetros. Regla fija: seleccionar probabilidades mayores a 0,025. No se estimó un umbral óptimo con mayo.

| Modelo | Ganancia mayo | Seleccionados | BAJA+2 detectados | Falsos positivos | Recall | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| Logística múltiple L2 | 189.392.500 | 9.113 | 400 | 8.713 | 45,98 % | 0,04785 |
| LightGBM | 241.807.500 | 7.847 | 416 | 7.431 | 47,82 % | 0,05523 |

Limpieza: los vencimientos de plástico menores a -36.500 días pasan a faltante. Es una regla conservadora basada en la unidad del diccionario, no un código especial confirmado. Afectó 466 Visa en marzo y 458 en mayo; ningún Master en esas particiones. Los demás negativos, ceros y faltantes se conservan. No se sobrescribió el CSV original.

Logística: imputación por mediana, indicadores de faltante y estandarización numérica ajustadas solo en marzo. Visa_status, Master_status y tcuentas se codifican con one-hot y una categoría de referencia; LightGBM las recibe como categóricas. La logística convergió en 40 iteraciones sin advertencias. Sus coeficientes numéricos son por desvío estándar después de imputar; los categóricos comparan contra la referencia registrada en `manifest.json`. Las magnitudes de ambos tipos no se comparan directamente. No son efectos causales ni pruebas de significación.

En LightGBM dominan ctrx_quarter, mcuentas_saldo y mpayroll por ganancia de splits (no ganancia monetaria ni importancia medida fuera de entrenamiento). En logística, actividad y haberes tienen asociaciones negativas ajustadas con BAJA+2. Los estados abiertos de tarjetas se comparan contra estado faltante: no interpretar como un efecto causal de abrir una tarjeta.

Se guardaron predicciones, modelos, coeficientes, importancias, versiones y parámetros. Las ganancias se recalcularon desde las predicciones y se verificó cobertura de mayo. Es una comparación de una configuración y semilla: no demuestra superioridad universal o significación estadística. Junio permanece sin evaluar.

## Primera comparación intrames

Ejecutar: `.venv/Scripts/python.exe tp_primera_entrega/03_comparar_intrames.py`.
Corrida: `salidas/intrames_20261001_182431_130565/`. Mismos clientes, parámetros, semilla y corte 0,025 que el baseline. Las probabilidades del baseline se reprodujeron exactamente.

| Variante | Variables | Ganancia en mayo | Diferencia contra baseline |
|---|---:|---:|---:|
| Originales | 152 | 241.807.500 | 0 |
| + Actividad | 154 | 233.420.000 | -8.387.500 |
| + Totales de tarjetas | 155 | 239.195.000 | -2.612.500 |
| + Utilización de tarjetas | 156 | 235.867.500 | -5.940.000 |

Actividad agrega transacciones trimestrales/productos y un conteo de ocho componentes de uso (canales y tarjetas, como el notebook previo). Tarjetas suma Visa + Master para saldo, consumo y límite: las tres fuentes se expresan en pesos según el diccionario. Utilización agrega saldo/límite y consumo/límite para cada marca. Las sumas exigen ambos componentes conocidos; los ratios requieren denominador positivo; el conteo exige conocer los ocho indicadores. No se rellenan faltantes con cero.

Ningún bloque mejoró la ganancia en esta corrida, por lo que no se combinaron ni se reemplazó el baseline. No es evidencia definitiva de inutilidad: corresponde a una semilla, configuración y umbral. Se conservan generadores, predicciones e importancias para comparar posteriormente con presupuestos equivalentes de optimización. No se evaluó junio.

## Features históricas preparadas

`agregar_historicas` calcula lags de un mes calendario y diferencias para actividad (`ctrx_quarter`), haberes (`mpayroll`), saldo (`mcuentas_saldo`) y productos (`cproductos`), más un indicador de presencia en el mes anterior. Si falta el mes exacto, el lag y delta quedan desconocidos, aunque exista una fila más antigua. Se verificaron meses omitidos, cambio de año, orden de filas y ausencia de uso del futuro.

Marzo no tiene febrero y estas columnas quedarían vacías para el train principal. Por eso se evaluaron en el experimento separado descrito a continuación, con train abril. El protocolo principal conserva marzo como train.

## Experimento retrospectivo de históricas: abril a mayo

Ejecutar: `.venv/Scripts/python.exe tp_primera_entrega/04_comparar_historicas.py`.
Corrida: `salidas/historicas_20261001_182842_721867/`.

Entrenamiento con 163.284 filas de abril y validación con las mismas 163.768 filas de mayo en ambos modelos. Marzo aporta historia para abril y abril para mayo. Se incorporan nueve features: cuatro lags, cuatro deltas y presencia en el mes previo. No se excluyen clientes sin historia. Se mantienen hiperparámetros, semilla y umbral 0,025; no se agregan features intrames ni se hace Optuna.

| Modelo entrenado con abril | Variables | Ganancia mayo | Detectados | Falsos positivos |
|---|---:|---:|---:|---:|
| Originales | 152 | 252.862.500 | 451 | 8.394 |
| Originales + históricas | 161 | 248.380.000 | 451 | 8.557 |

Las históricas redujeron la ganancia en 4.482.500 en esta corrida. Detectaron igual cantidad de BAJA+2 y agregaron 163 falsos positivos. No se reemplaza el baseline principal. Las diferencias contra el baseline entrenado en marzo no se atribuyen a las features, porque cambia también el entrenamiento.

Limitación acordada: el target de abril se conoce en junio. Entrenar abril y validar mayo es retrospectivo y no simula disponibilidad real al cierre de mayo. Solo se cargan filas de marzo, abril y mayo; el target no entra en el generador histórico. Junio sigue sin evaluar. Resultados de una sola configuración y semilla, sin afirmación de significación estadística.

## Optuna y Random Forest

Corrida: `salidas/optuna_20261001_183546_498714/`. Train abril y validación mayo en el experimento retrospectivo; 30 trials completos por variante LightGBM, cero fallidos. Mismo espacio y umbral fijo 0,025. RF se ejecutó como referencia de 300 árboles, sin tuning.

| Modelo | Ganancia mayo | Contactos | BAJA+2 detectados |
|---|---:|---:|---:|
| LightGBM originales, mejor de 30 | 263.257.500 | 8.147 | 443 |
| LightGBM históricas, mejor de 30 | 266.667.500 | 8.703 | 460 |
| Random Forest originales, sin tuning | 222.475.000 | 10.150 | 456 |

Las históricas superaron a originales en 3.410.000 después del ajuste, una ventaja exploratoria pequeña. RF no mejoró a los LightGBM probados; no tuvo el mismo presupuesto de optimización. Las ganancias máximas se seleccionaron sobre mayo y son optimistas; junio sigue reservado. La corrida tuvo pausas del entorno y RF se repitió con igual resultado; los tiempos de pared no reflejan cómputo efectivo. Detalles completos y correcciones en la bitácora, sección 22.

## Evaluación congelada de junio — 2026-10-03

### Experimento posterior con TabPFN

Comparación de estimadores autorizada el 2026-10-04:
`10_comparar_estimadores_tabpfn.py` compara Fast con 1, 2, 4 y 8 estimadores,
solo marzo → mayo, a umbral 0,025. Reutiliza validaciones completas compatibles
y verifica las métricas desde sus CSV y la igualdad de clientes y etiquetas.
Las nuevas corridas usan el script 08 sin modificar sus hashes congelados.
Guarda `comparacion.csv` y `comparacion.json` después de cada resultado.
Si se interrumpe, volver a ejecutar reutiliza las etapas completas; no lanzar
otra copia mientras la anterior siga activa. El tope estimado por corrida
es 200.000 créditos; no representa un límite garantizado del consumo final.

```powershell
.\.venv-priorlabs\Scripts\python.exe tp_primera_entrega/10_comparar_estimadores_tabpfn.py
# Consolidar resultados disponibles sin nuevas inferencias:
.\.venv-priorlabs\Scripts\python.exe tp_primera_entrega/10_comparar_estimadores_tabpfn.py --solo-consolidar
```

Actualización del 2026-10-04: `08_experimento_tabpfn.py` ahora usa la API
de PriorLabs mediante `tabpfn-client`, sin GPU local. Las notas de corridas
locales que siguen son antecedentes. Instalar `requirements-priorlabs.txt`
en `.venv-priorlabs` y configurar `TABPFN_TOKEN` en la misma terminal.
La ejecución transmite features y etiquetas de entrenamiento, sin ID ni mes;
las etiquetas de evaluación permanecen locales. Mantiene todas las filas
(`SUBSAMPLE_SAMPLES=None`), un estimador, variante v3.5-fast y umbral 0,025.
Por defecto hace una solicitud de predicción por etapa (`--batch-size 0`),
cotiza antes de subir datos y detiene la etapa si supera el tope estimado
de 100.000 créditos (`--max-creditos`). El servidor aplica además sus cuotas
y límites efectivos. Guarda cotización, versiones, hashes, predicciones,
métricas y ganancia verificada en `salidas/tabpfn_api_<etapa>_<fecha>/`.
No reutilizar una validación local para el test API. La semilla y versión
solicitadas quedan registradas; el alias del servidor puede cambiar su
checkpoint y no garantiza reproducibilidad exacta entre fechas.

```powershell
.\.venv-priorlabs\Scripts\python.exe -m pip install -r tp_primera_entrega/requirements-priorlabs.txt
.\.venv-priorlabs\Scripts\python.exe tp_primera_entrega/08_experimento_tabpfn.py --etapa validacion
# Tras revisar la validación completa (junio sigue siendo exploratorio):
.\.venv-priorlabs\Scripts\python.exe tp_primera_entrega/08_experimento_tabpfn.py --etapa test --validacion-existente <carpeta_validacion_api>
```

Verificación de la adaptación: sintaxis e integración con API simulada para
validación, test y bloqueo por presupuesto; sin inferencia real en esa prueba.

Tomás autorizó mantener todas las filas y una corrida prolongada. Se lanzó en segundo plano `08_experimento_tabpfn.py --etapa secuencia`: validación marzo -> mayo, luego reentrenamiento marzo + abril -> junio únicamente si la validación completa y sus verificaciones pasan. Variante TabPFN-3.5-Fast, un estimador, autocast, caché en RAM y lotes de 1.000. Logs en `salidas/tabpfn_secuencia_20261003_123841/`; las etapas crean sus propias carpetas y manifiestos. Sin métricas completas al iniciar. La corrida puede tardar horas o fallar por memoria; consultar logs y estado del proceso antes de lanzar otra.

Actualización del 2026-10-03: Tomás aceptó la licencia y descargó `tabpfn-v3.5-20260909.safetensors` (876.027.932 bytes) en `salidas/tabpfn_cache/`. Se pudo cargar localmente sin token. El primer intento completó fit pero falló por CUDA sin memoria durante predict. Se descartó precisión float16 forzada por advertencias de overflow; con autocast y caché en CPU el fit de las 162.900 filas completó, pero la inferencia fue muy lenta. Se agregó la variante explícita `--model-version v3.5-fast` (predeterminada para la prueba de viabilidad), autocast, caché en CPU y guardado de probabilidades parciales por lote. Fast también completó fit y se inició predict; aún sin métricas completas. Cualquier muestra de entrenamiento requiere un diseño explícito y su comparación con LightGBM usando la misma muestra, sin reducir el universo evaluado.

Tomás confirmó marzo -> mayo y reentrenamiento marzo + abril -> junio. Junio ya fue evaluado: esta comparación es exploratoria. Se descartó julio como test porque 163.245 de 164.348 etiquetas son desconocidas; las conocidas no permiten evaluar el universo del mes.

Se instaló TabPFN 9.1.0 y PyTorch 2.11.0+cu128 en `.venv`; CUDA 12.8 funciona con la RTX 5070 Ti Laptop de 12 GB. Dependencias opcionales en `requirements-tabpfn.txt`. `08_experimento_tabpfn.py` utiliza TabPFN-3.5, 152 variables originales, todas las filas, sin balanceo, escalado ni one-hot, un estimador inicial y umbral fijo 0,025. La configuración y los errores se guardan; el test exige una validación completa y mismas versiones, código y configuración. No se ha comprobado aún que el conjunto completo quepa en memoria.

El primer intento llegó a la carga del modelo y se detuvo por `TabPFNLicenseError`: falta iniciar sesión en PriorLabs y aceptar la licencia de los pesos. No hay métricas de TabPFN ni test ejecutado. La aceptación es una acción personal en https://ux.priorlabs.ai; no pegar tokens en el chat. Una vez configurado `TABPFN_TOKEN` localmente, ejecutar:

```powershell
.\.venv\Scripts\python.exe .\tp_primera_entrega\08_experimento_tabpfn.py --etapa validacion
# Tras completar la validación, usar su carpeta de resultados:
.\.venv\Scripts\python.exe .\tp_primera_entrega\08_experimento_tabpfn.py --etapa test --validacion-existente <carpeta_validacion>
```

La descarga y la inferencia son locales; no se configuró inferencia alojada. La caché de modelos y de skrub se ubica en `salidas/`. Acceso a pesos y límites por versión: https://docs.priorlabs.ai/models.

`07_evaluacion_junio.py` guarda la configuración antes de consultar junio. Reentrena marzo + abril (326.184 filas) con los mejores parámetros de originales e históricas seleccionados en mayo. Mantiene el umbral 0,025, sin tuning ni selección de corte en junio. Marzo no tiene febrero: lags/deltas faltantes e indicador cero; junio usa predictores de mayo, sin sus etiquetas.

| Variante | Ganancia junio | Contactos | TP | FP |
|---|---:|---:|---:|---:|
| Originales optimizados, referencia | 333.410.000 | 7.716 | 496 | 7.220 |
| Históricas optimizadas, candidata congelada | 332.832.500 | 8.537 | 516 | 8.021 |

Históricas queda 577.500 por debajo (0,17 %): los 20 TP adicionales no compensan los 801 FP adicionales. No se sostuvo la ventaja observada en mayo; una semilla no establece superioridad general. No se cambian parámetros ni umbral a partir de junio. Artefactos en `salidas/test_junio_20261003_114546_998605/`: configuración congelada, modelos, importancias, predicciones, comparación, versiones, hashes y ganancias verificadas desde el CSV. El siguiente experimento previsto es TabPFN, con desarrollo en mayo; junio ya está expuesto y cualquier comparación posterior allí será exploratoria. No se generó entrega de agosto.

## Comparación completa: originales, intrames e históricas

Consolidado: `salidas/optuna_20261002_123603_479131/`. El archivo `06_comparacion_optuna_features.py` agregó 30 trials con los nueve intrames juntos y reutilizó los 60 trials anteriores tras verificar compatibilidad. Las tres alternativas entrenan abril y validan mayo, con el mismo espacio de búsqueda, semilla y umbral 0,025. Son 30 intentos por alternativa, no igual tiempo de ejecución. Los 90 trials terminaron sin fallos.

| Variante LightGBM, mejor de 30 | Variables | Ganancia mayo | Contactos | BAJA+2 detectados |
|---|---:|---:|---:|---:|
| Originales | 152 | 263.257.500 | 8.147 | 443 |
| Originales + intrames | 161 | 264.467.500 | 8.383 | 450 |
| Originales + históricas | 161 | 266.667.500 | 8.703 | 460 |

Intrames mejoró 14.767.500 respecto de su configuración inicial y 1.210.000 frente a originales optimizados. Históricas conserva una ventaja de 2.200.000 frente a intrames. Estas diferencias son pequeñas y exploratorias: se seleccionaron máximos sobre mayo con una sola semilla. El experimento es retrospectivo; no cambia el protocolo principal. No se combinaron intrames e históricas.

Se verificaron filas, etiquetas y métricas desde las predicciones. El consolidado guarda la configuración de entrega de agosto y las referencias a los estudios previos. Junio continúa sin evaluar; todavía no se generó una entrega de agosto. Para verificar y regenerar el consolidado sin entrenar:

```powershell
.\.venv\Scripts\python.exe .\tp_primera_entrega\06_comparacion_optuna_features.py --intrames-existente .\tp_primera_entrega\salidas\optuna_20261002_123603_479131
```
