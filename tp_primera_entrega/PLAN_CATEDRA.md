# Implementación de recomendaciones de la cátedra

Actualización7 de octubre: el usuario autoriza junio como evaluación para medir orden2. Ensayo marzo–mayo→junio completado/verificado, parámetros16 congelados,189 vs213 con cinco semillas. El bloque24 pierde$2.106.500 total (25%$526.625), gana1/5 semillas. Informe: `salidas/orden2_junio_20261007_153616/MINI_INFORME.md`. Esta autorización sustituye las restricciones de junio de las secciones originales para este diagnóstico; Optuna AUC permanece en mayo. No ampliar automáticamente al tuning con junio ni atribuir esta prueba de LightGBM solo al ensemble completo16.

Plan acordado. Implementación iniciada; las etapas siguientes no se consideran completas hasta sus verificaciones. Fecha del plan: 2026-10-06.

Avance: features orden2 implementados/verificados; A0/A1/A2 completos y reproducidos independientemente. TabPFN226 local autorizado por el usuario hasta50.000 créditos, consumo43.438, ensemble local verificado. Optuna20 trials activo y continuación automática preparada en script95. Directorio: `salidas/catedra_implementacion_20261006_205501`. Marzo/abril carecen de lag2: la búsqueda temporal no aprende esos24 predictores; diagnóstico por clientes de mayo preparado para comprobarlos con historia observable. TabPFN final requiere decisión y autorización separadas. Cotizaciones: ventana abril+mayo78.242 créditos; marzo–junio173.599.

## Referencia y objetivo

Entrega16: LightGBM189, target BAJA+1/BAJA+2, más TabPFN202, target BAJA+2, pesos 50/50 y score > 0,025. Entrenamiento final original abril+mayo. Cinco listas por semilla; media pública $96.921.000, desvío $1.781.600. Referencia local abril→mayo: total medio $266.420.000, 25% $66.605.000. Preservar modelos, listas y scripts originales.

Objetivo: superar la referencia pública y acercarse a $100 millones. No asumir que superar mayo garantiza mejorar agosto. El agregado de CatBoost en17 perdió públicamente; queda fuera de este piloto.

## 1. Datos e históricos

- Aplicar `calidad_datos.corregir_datos` antes de cualquier histórico: ccajas_depositos = NA solamente en 202105. Regla ya verificada sobre 163.768 filas; otras correcciones actuales se conservan.
- Agregar lag2 y delta2 a las mismas doce fuentes históricas del control: ctrx_quarter, mpayroll, mcuentas_saldo, cproductos, Visa_mconsumototal, Master_mconsumototal, ctarjeta_visa_transacciones, ctarjeta_master_transacciones, chomebanking_transacciones, cmobile_app_trx, ctarjeta_visa, ctarjeta_master.
- Definición: lag1 = valor del mes calendario anterior; lag2 = valor de dos meses antes; delta1 = actual − lag1; delta2 = actual − lag2. Revisar el script de la cátedra antes de implementar para confirmar esa definición de delta2.
- Conservar las 189 variables del control LightGBM y agregar esas 24: 213 variables. No reincorporar automáticamente los trece resúmenes descartados. Ampliar los históricos a todas las variables sería otro experimento posterior.
- Unir por cliente y mes calendario, validar claves únicas y orden. Mes faltante implica NA, nunca reemplazar por la fila anterior. Marzo carece de historia; abril carece de lag2. Informar cobertura por mes; agosto puede usar junio/julio sin etiquetas como historia.
- No usar ID, mes ni target como predictores. Verificar ejemplos de clientes con huecos, NA y corrección de mayo antes de entrenar.

## 2. Validación y ablación de la entrega16

Reproducir primero el control local de16 con el código histórico, sin alterarlo. Mismo entrenamiento abril, evaluación mayo, cinco semillas fijas y predicciones compatibles de TabPFN202.

| Prueba | Cambio respecto del control | TabPFN | Parámetros/ventana/pesos/corte |
| --- | --- | --- | --- |
| A0 | Ninguno; reproducir16 | Guardado202 | Originales |
| A1 | Corrección de ccajas_depositos | Guardado202 | Originales |
| A2 | Corrección + lag2/delta2 en LightGBM | Guardado202 | Originales |

Comparar LightGBM solo y mezcla 50/50 en cada prueba. El TabPFN guardado permite medir el cambio de LightGBM sin créditos; todavía no incorpora la corrección. Reportar ganancia total y25%, AUC por target, contactos, BAJA+2 detectadas, falsos positivos, resultados por semilla y mismas cuatro partes de clientes. Estas partes no son meses independientes.

Mayo ya se utilizó repetidamente: es validación de desarrollo, no test independiente. Agregar como diagnóstico marzo→abril si las matrices y cobertura lo permiten; no elegir con junio ni con etiquetas de agosto. Las evaluaciones con etiquetas históricas representan un backtest retrospectivo; documentar cuándo se conoce BAJA+2 para no presentarlas como simulación prospectiva perfecta.

## 3. LightGBM según la cátedra

Sin undersampling ni balanceo añadido: todas las filas disponibles de cada ventana. Conservar el target combinado en el primer piloto para comparar con16; evaluar premio exclusivamente por BAJA+2.

Parámetros fijos: metric=auc, max_bin=31, min_data_in_leaf=0, feature_fraction=0.50, feature_fraction_bynode=0.20, learning_rate=0.005. Añadir feature_pre_filter=False para evitar filtrado incompatible con la búsqueda; conservar controles de reproducibilidad y recursos.

Optuna maximiza AUC de validación del target combinado. Buscar solamente num_iterations, num_leaves y min_sum_hessian_in_leaf. Rangos iniciales propuestos: 1.000–12.000 árboles (pasos de500), 16–256 hojas, Hessiano mínimo1–100 logarítmico. Revisar costo mediante una corrida piloto antes de lanzar el estudio. No fijar 273 árboles con learning_rate=0.005.

Primero presupuesto de20 trials, ampliable si no quedan diez configuraciones válidas o si los ganadores llegan a los límites. Comparar una semilla común durante búsqueda; verificar los candidatos con las cinco semillas históricas antes de entrenamiento final. No multiplicar todas las configuraciones por cinco desde el comienzo.

Congelar las diez mejores configuraciones distintas por AUC antes del scoring público; informar también ganancia y estabilidad sin cambiar retrospectivamente el objetivo Optuna. Ganar AUC del target combinado no garantiza ganar premio BAJA+2. Guardar parámetros, número de árboles efectivo, matrices, versiones, seeds y predicciones.

Validación principal de búsqueda: marzo+abril→mayo, sin filas futuras. Recalcular el control con esa misma ventana para compararlo justamente. El control histórico abril→mayo sigue siendo una referencia aparte. La disponibilidad de lag2 difiere entre meses y se debe informar.

## 4. Entrenamiento final y ensembles

Congelar features y parámetros antes de usar junio en el ajuste final. Entrenar al menos diez modelos con hiperparámetros distintos y todos los clientes de 202103,202104,202105,202106, sin undersampling. Verificar etiquetas de esos meses. Julio aporta historia, no etiquetas al entrenamiento. Aplicar a202108.

Primero promediar probabilidades LightGBM por numero_de_cliente con peso igual por configuración. Una semilla fija por configuración en el primer ensemble final; cinco semillas adicionales solamente si el costo y la evidencia lo justifican. Reproducir este mismo promedio por configuración en validación: no compararlo con la media de ganancias de listas individuales como si fueran iguales.

Dos candidatos iniciales:

1. LightGBM de la cátedra solo: promedio de diez o más configuraciones.
2. El mismo promedio LightGBM + TabPFN BAJA+2, inicialmente 50/50 como16.

Con TabPFN guardado se hace primero la comparación local sin costo. La mezcla final con TabPFN original abril+mayo sirve como diagnóstico, pero no es una versión con ambos modelos actualizados.

Para reentrenar ambos componentes, proponer TabPFN con corrección y lag2/delta2 sobre sus202 variables originales (226 variables en esta extensión), primero abril→mayo y después ventana final definida. Cotizar, verificar límites de filas/features y capacidad de la API; obtener autorización específica para cualquier nuevo envío/presupuesto no cubierto. La autorización anterior de189 variables abril→mayo no cubre automáticamente226 variables ni marzo–junio. No asumir que todos esos registros caben en una sola llamada. Si no es viable, conservar TabPFN existente y documentar la ventana distinta.

La actualización completa cambia datos, hiperparámetros y ventana respecto de16: identificarla como nuevo candidato derivado de16, no como reproducción exacta. Antes del ajuste final, comparar localmente modelos con/sin marzo usando la misma evaluación de mayo; junio no se utiliza para elegir ventanas.

## 5. Ranking, cortes y entrega

Generar desde el mismo score promedio listas topN para N=10.000,10.500,11.000,11.500,12.000. Explorar localmente un rango más amplio si el máximo cae en un borde. Orden descendente de score y desempate por ID ascendente; cinco cortes son cinco políticas del mismo ranking, no cinco semillas.

Medir el corte original >2,5% como control. Con targets distintos, la mezcla es un score, no una probabilidad calibrada de BAJA+2. Elegir un rango estable de contactos localmente, no solamente el máximo puntual. Si los tamaños de las poblaciones difieren, informar además la fracción contactada.

Preparar una carpeta por entrega/configuración de ensemble, con subcarpeta de adjuntos topN, manifiesto, corte, pesos, ventanas, features, hashes, informe y comando. Nunca mezclar CSV de diferentes estrategias sin identificarlos. Como hay pocos submits, seleccionar uno o dos candidatos locales para el Bot; el usuario realiza el envío. El promedio/desvío del Bot de varios cortes no mide varianza entre semillas.

## Orden de ejecución

1. Implementar y verificar históricos orden2; reproducir A0 y ejecutar A1/A2 sin API.
2. Piloto de costo y Optuna LightGBM AUC; evaluar promedio de configuraciones solo y con TabPFN guardado.
3. Revisar resultados y cotización TabPFN antes de cualquier envío nuevo.
4. Reentrenar candidatos seleccionados, generar agosto/topN y mini informe con referencias16.
5. Preparar nueva entrega trazable; no enviar automáticamente ni prometer mejora pública.
