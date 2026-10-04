# Diccionario de las 50 variables históricas de TabPFN

Fecha: 2026-10-04. Implementación: [features.py](features.py), funciones `agregar_historicas` y `agregar_historicas_ampliadas`. Experimentos: [11_tabpfn_historicas.py](11_tabpfn_historicas.py).

Se agregan 50 variables a las 152 originales: **202 variables en total**. El bloque ampliado incluye las 9 históricas básicas; no son 50 adicionales a esas 9.

## Cómo leer las fórmulas

`t` es el mes de la foto del cliente. `t−1`, `t−2` y `t−3` son meses calendario anteriores del mismo cliente, no sus últimas tres filas disponibles. Si falta abril, el lag de mayo no toma marzo en su lugar. Las unidades monetarias y la definición temporal de cada fuente se conservan: un lag no convierte automáticamente una variable trimestral en una mensual.

No se utilizan etiquetas, probabilidades de otros modelos ni datos futuros. Las diferencias y ratios incluyen el valor actual, disponible al momento de predecir.

## Variables originales utilizadas como fuentes

| Fuente | Significado operativo |
|---|---|
| `ctrx_quarter` | Actividad/transacciones registradas en ctrx_quarter; se conserva la definición de la variable original, que ya tiene referencia trimestral. |
| `mpayroll` | Monto de acreditación de haberes registrado en la foto. |
| `mcuentas_saldo` | Saldo de cuentas registrado en la foto. |
| `cproductos` | Cantidad de productos del cliente. |
| `Visa_mconsumototal` | Consumo total Visa registrado en la foto. |
| `Master_mconsumototal` | Consumo total Master registrado en la foto. |
| `ctarjeta_visa_transacciones` | Cantidad de transacciones con tarjeta Visa. |
| `ctarjeta_master_transacciones` | Cantidad de transacciones con tarjeta Master. |
| `chomebanking_transacciones` | Cantidad de transacciones por homebanking. |
| `cmobile_app_trx` | Cantidad de transacciones por aplicación móvil. |
| `ctarjeta_visa` | Cantidad de tarjetas Visa registrada; no se interpreta automáticamente como cantidad de tarjetas activas. |
| `ctarjeta_master` | Cantidad de tarjetas Master registrada; no se interpreta automáticamente como cantidad de tarjetas activas. |

Las descripciones remiten a las columnas del dataset; no añaden una interpretación causal ni confirman actividad de tarjetas a partir de su cantidad.

## Inventario completo

| Nº | Variable histórica | Fuente | Fórmula | Interpretación | Faltantes y condiciones |
|---:|---|---|---|---|---|
| 1 | `lag_1_ctrx_quarter` | `ctrx_quarter` | ctrx_quarter(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 2 | `delta_1_ctrx_quarter` | `ctrx_quarter` | ctrx_quarter(t) − ctrx_quarter(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 3 | `lag_1_mpayroll` | `mpayroll` | mpayroll(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 4 | `delta_1_mpayroll` | `mpayroll` | mpayroll(t) − mpayroll(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 5 | `lag_1_mcuentas_saldo` | `mcuentas_saldo` | mcuentas_saldo(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 6 | `delta_1_mcuentas_saldo` | `mcuentas_saldo` | mcuentas_saldo(t) − mcuentas_saldo(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 7 | `lag_1_cproductos` | `cproductos` | cproductos(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 8 | `delta_1_cproductos` | `cproductos` | cproductos(t) − cproductos(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 9 | `lag_1_Visa_mconsumototal` | `Visa_mconsumototal` | Visa_mconsumototal(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 10 | `delta_1_Visa_mconsumototal` | `Visa_mconsumototal` | Visa_mconsumototal(t) − Visa_mconsumototal(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 11 | `lag_1_Master_mconsumototal` | `Master_mconsumototal` | Master_mconsumototal(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 12 | `delta_1_Master_mconsumototal` | `Master_mconsumototal` | Master_mconsumototal(t) − Master_mconsumototal(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 13 | `lag_1_ctarjeta_visa_transacciones` | `ctarjeta_visa_transacciones` | ctarjeta_visa_transacciones(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 14 | `delta_1_ctarjeta_visa_transacciones` | `ctarjeta_visa_transacciones` | ctarjeta_visa_transacciones(t) − ctarjeta_visa_transacciones(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 15 | `lag_1_ctarjeta_master_transacciones` | `ctarjeta_master_transacciones` | ctarjeta_master_transacciones(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 16 | `delta_1_ctarjeta_master_transacciones` | `ctarjeta_master_transacciones` | ctarjeta_master_transacciones(t) − ctarjeta_master_transacciones(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 17 | `lag_1_chomebanking_transacciones` | `chomebanking_transacciones` | chomebanking_transacciones(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 18 | `delta_1_chomebanking_transacciones` | `chomebanking_transacciones` | chomebanking_transacciones(t) − chomebanking_transacciones(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 19 | `lag_1_cmobile_app_trx` | `cmobile_app_trx` | cmobile_app_trx(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 20 | `delta_1_cmobile_app_trx` | `cmobile_app_trx` | cmobile_app_trx(t) − cmobile_app_trx(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 21 | `lag_1_ctarjeta_visa` | `ctarjeta_visa` | ctarjeta_visa(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 22 | `delta_1_ctarjeta_visa` | `ctarjeta_visa` | ctarjeta_visa(t) − ctarjeta_visa(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 23 | `lag_1_ctarjeta_master` | `ctarjeta_master` | ctarjeta_master(t−1) | Valor de esta variable en el mes calendario anterior. Permite comparar el nivel actual con el previo. | NaN si falta la fila anterior o su valor. |
| 24 | `delta_1_ctarjeta_master` | `ctarjeta_master` | ctarjeta_master(t) − ctarjeta_master(t−1) | Cambio absoluto: positivo indica aumento; negativo, disminución. En cantidades de tarjetas/productos, una caída registra una reducción, sin identificar su causa. | NaN si falta el valor actual o anterior. |
| 25 | `historial_mes_anterior_disponible` | `Claves cliente/mes` | 1 si existe fila del cliente en t−1; 0 si no | Disponibilidad de la fila previa, independientemente de que sus predictores estén completos. | Siempre 0 o 1; no implica que todos los valores previos estén presentes. |
| 26 | `variacion_relativa_1_ctrx_quarter` | `ctrx_quarter` | [ctrx_quarter(t) − ctrx_quarter(t−1)] / abs(ctrx_quarter(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 27 | `variacion_relativa_1_mpayroll` | `mpayroll` | [mpayroll(t) − mpayroll(t−1)] / abs(mpayroll(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 28 | `variacion_relativa_1_mcuentas_saldo` | `mcuentas_saldo` | [mcuentas_saldo(t) − mcuentas_saldo(t−1)] / abs(mcuentas_saldo(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 29 | `variacion_relativa_1_cproductos` | `cproductos` | [cproductos(t) − cproductos(t−1)] / abs(cproductos(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 30 | `variacion_relativa_1_Visa_mconsumototal` | `Visa_mconsumototal` | [Visa_mconsumototal(t) − Visa_mconsumototal(t−1)] / abs(Visa_mconsumototal(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 31 | `variacion_relativa_1_Master_mconsumototal` | `Master_mconsumototal` | [Master_mconsumototal(t) − Master_mconsumototal(t−1)] / abs(Master_mconsumototal(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 32 | `variacion_relativa_1_ctarjeta_visa_transacciones` | `ctarjeta_visa_transacciones` | [ctarjeta_visa_transacciones(t) − ctarjeta_visa_transacciones(t−1)] / abs(ctarjeta_visa_transacciones(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 33 | `variacion_relativa_1_ctarjeta_master_transacciones` | `ctarjeta_master_transacciones` | [ctarjeta_master_transacciones(t) − ctarjeta_master_transacciones(t−1)] / abs(ctarjeta_master_transacciones(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 34 | `variacion_relativa_1_chomebanking_transacciones` | `chomebanking_transacciones` | [chomebanking_transacciones(t) − chomebanking_transacciones(t−1)] / abs(chomebanking_transacciones(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 35 | `variacion_relativa_1_cmobile_app_trx` | `cmobile_app_trx` | [cmobile_app_trx(t) − cmobile_app_trx(t−1)] / abs(cmobile_app_trx(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 36 | `variacion_relativa_1_ctarjeta_visa` | `ctarjeta_visa` | [ctarjeta_visa(t) − ctarjeta_visa(t−1)] / abs(ctarjeta_visa(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 37 | `variacion_relativa_1_ctarjeta_master` | `ctarjeta_master` | [ctarjeta_master(t) − ctarjeta_master(t−1)] / abs(ctarjeta_master(t−1)) | Cambio relativo respecto de la magnitud anterior: 0,20 significa aumento equivalente al 20 % de esa magnitud. No se recorta a [0,1]. | NaN si el anterior es cero, falta una fuente o el resultado no es finito. |
| 38 | `historial_meses_previos_3` | `Claves cliente/mes` | Suma de filas disponibles en t−1, t−2 y t−3 | Cantidad de meses calendario previos con registro del cliente. Distingue cobertura temporal, no antigüedad total. | Entero 0..3; cuenta filas aunque sus predictores estén faltantes. |
| 39 | `media_previa_3_ctrx_quarter` | `ctrx_quarter` | Media de valores disponibles de ctrx_quarter en t−1, t−2 y t−3 | Nivel histórico reciente del propio cliente. Excluye el mes actual; puede representar uno, dos o tres valores. | Ignora NaN; NaN si no hay ningún valor previo. |
| 40 | `delta_media_previa_3_ctrx_quarter` | `ctrx_quarter` | ctrx_quarter(t) − media_previa_3_ctrx_quarter | Desviación actual respecto de su promedio previo: positiva si está por encima y negativa si está por debajo. | NaN si falta el actual o no hay media previa. |
| 41 | `observaciones_previas_3_ctrx_quarter` | `ctrx_quarter` | Cantidad de valores no nulos de ctrx_quarter en t−1, t−2 y t−3 | Cobertura efectiva del promedio de esta variable. Puede ser menor que la cantidad de filas previas. | Entero 0..3. |
| 42 | `media_previa_3_mpayroll` | `mpayroll` | Media de valores disponibles de mpayroll en t−1, t−2 y t−3 | Nivel histórico reciente del propio cliente. Excluye el mes actual; puede representar uno, dos o tres valores. | Ignora NaN; NaN si no hay ningún valor previo. |
| 43 | `delta_media_previa_3_mpayroll` | `mpayroll` | mpayroll(t) − media_previa_3_mpayroll | Desviación actual respecto de su promedio previo: positiva si está por encima y negativa si está por debajo. | NaN si falta el actual o no hay media previa. |
| 44 | `observaciones_previas_3_mpayroll` | `mpayroll` | Cantidad de valores no nulos de mpayroll en t−1, t−2 y t−3 | Cobertura efectiva del promedio de esta variable. Puede ser menor que la cantidad de filas previas. | Entero 0..3. |
| 45 | `media_previa_3_mcuentas_saldo` | `mcuentas_saldo` | Media de valores disponibles de mcuentas_saldo en t−1, t−2 y t−3 | Nivel histórico reciente del propio cliente. Excluye el mes actual; puede representar uno, dos o tres valores. | Ignora NaN; NaN si no hay ningún valor previo. |
| 46 | `delta_media_previa_3_mcuentas_saldo` | `mcuentas_saldo` | mcuentas_saldo(t) − media_previa_3_mcuentas_saldo | Desviación actual respecto de su promedio previo: positiva si está por encima y negativa si está por debajo. | NaN si falta el actual o no hay media previa. |
| 47 | `observaciones_previas_3_mcuentas_saldo` | `mcuentas_saldo` | Cantidad de valores no nulos de mcuentas_saldo en t−1, t−2 y t−3 | Cobertura efectiva del promedio de esta variable. Puede ser menor que la cantidad de filas previas. | Entero 0..3. |
| 48 | `media_previa_3_cproductos` | `cproductos` | Media de valores disponibles de cproductos en t−1, t−2 y t−3 | Nivel histórico reciente del propio cliente. Excluye el mes actual; puede representar uno, dos o tres valores. | Ignora NaN; NaN si no hay ningún valor previo. |
| 49 | `delta_media_previa_3_cproductos` | `cproductos` | cproductos(t) − media_previa_3_cproductos | Desviación actual respecto de su promedio previo: positiva si está por encima y negativa si está por debajo. | NaN si falta el actual o no hay media previa. |
| 50 | `observaciones_previas_3_cproductos` | `cproductos` | Cantidad de valores no nulos de cproductos en t−1, t−2 y t−3 | Cobertura efectiva del promedio de esta variable. Puede ser menor que la cantidad de filas previas. | Entero 0..3. |

## Composición del bloque

| Familia | Cantidad |
|---|---:|
| Valores del mes anterior: 12 fuentes | 12 |
| Diferencias respecto del mes anterior: 12 fuentes | 12 |
| Indicador de fila anterior disponible | 1 |
| Variaciones relativas: 12 fuentes | 12 |
| Cantidad de filas en los tres meses previos | 1 |
| Medias previas: 4 fuentes | 4 |
| Diferencias respecto de medias previas: 4 fuentes | 4 |
| Conteos de valores para esas medias: 4 fuentes | 4 |
| **Total** | **50** |

Las 9 básicas son los 4 lags y 4 deltas de `ctrx_quarter`, `mpayroll`, `mcuentas_saldo`, `cproductos`, más `historial_mes_anterior_disponible`.

## Ejemplo

Si el saldo actual es 80 y el anterior 100: lag = 100, delta = −20 y variación relativa = −0,20. Si los saldos de los tres meses previos son 100, NaN y 120: media = 110, observaciones = 2 y diferencia respecto de la media = −30. La cobertura de filas puede ser 3 aunque solo dos saldos estén disponibles.

## Historia realmente disponible en nuestros experimentos

| Foto | Meses anteriores disponibles en los datos usados | Máximo de meses previos |
|---|---|---:|
| Marzo | No se incluye febrero | 0 |
| Abril | Marzo | 1 |
| Mayo | Marzo y abril | 2 |
| Junio | Marzo, abril y mayo | 3 |

Por ello, en abril las medias previas coinciden con los lags cuando existe el mismo valor observado. En mayo y junio pueden diferir. El nombre `media_previa_3_` describe una ventana de hasta tres meses, no garantiza tres observaciones. Los conteos acompañan esas medias para registrar la cobertura.

Marzo se conservó en el reentrenamiento marzo + abril para junio, con historia faltante e indicadores cero. No se eliminaron clientes por carecer de historia.

## Limpieza y límites de interpretación

Antes de construir la historia, las fuentes no finitas se convierten en NaN. Los ratios evitan dividir por cero; un cero observado no se sustituye por faltante salvo cuando funciona como denominador inválido. Las features pasan luego por `preparar`, que convierte resultados no finitos en NaN. No hay imputación manual a cero de las features históricas.

Las columnas de cantidad permiten observar reducciones, pero no identifican productos específicos cancelados ni sus causas. Las medias y diferencias describen niveles y cambios: no se agregó una pendiente de tendencia ni una bandera explícita de caída durante varios meses consecutivos. No se añadieron cambios históricos de todas las columnas originales.

Algunas columnas coinciden en ciertos meses por la historia disponible o por los datos. La auditoría no eliminó ninguna: el conjunto evaluado en junio mantiene las 202 variables.

## Verificación del documento

Los 50 nombres se contrastaron contra el campo `nuevas` del manifiesto de junio `salidas/tabpfn_historicas_20261004_172322_339836/manifest.json`. Las fórmulas se documentan desde el generador implementado, no desde propuestas pendientes.
