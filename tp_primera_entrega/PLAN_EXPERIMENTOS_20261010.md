# Plan de experimentos — 10 de octubre de 2026

Estado: pasos1 y2 completados; paso3 pendiente. No ejecutar pruebas por el hecho de leer este documento. Sustituye el orden de prioridades de anotaciones históricas en NEXT_STEPS_IDEAS.md. Cada ejecución registra su plan antes de mirar el resultado y conserva los artefactos anteriores.

Actualización paso2: las cuatro señales de débitos/pagos mejoran la lista promedio5 en mayo por solo$137.500 total (25%$34.375), pero pierden$7.018.000 en la media de listas individuales y mejoran1/5semillas. No superan la puerta fijada: no se ejecuta junio ni se prepara una entrega. [Conclusión](salidas/servicios_recurrentes_20261010/CONCLUSION.md). Cinco fits locales nuevos, sin API/créditos/submits. Siguiente pendiente: auditoría del paso3.

Actualización: paso1 ejecutado y verificado el10/10/2026, por autorización de Tomás. Cortes segmentados seleccionados en mayo perdieron en junio $19.607.500 de ganancia local total frente al corte fijo2,75% (25%−$4.901.875); ninguna de las cinco semillas mejora frente al fijo. Superan al corte global3,25% por$1.265.000 total, pero eso no basta para pasar la puerta. Se cierra esta versión de cortes segmentados; no nueva entrega. [Informe y controles](salidas/cortes_segmentos_junio_20261010/MINI_INFORME.md). Paso2 queda como siguiente prueba pendiente; pasos2–4 no ejecutados por este encargo.

## Objetivo y referencia

Buscar una mejora reproducible sobre la entrega36, sin elegir candidatos únicamente por el público. Referencia pública $98.175.000, una lista de10.420clientes; faltan $1.825.000 para el objetivo público de$100millones.

Referencia de configuración: LightGBM189 target BAJA+1/BAJA+2, parámetros de entrega16,273árboles, cinco semillas541440/408476/741961/248865/717444; TabPFN202 BAJA+2 guardado; promedio de las cinco probabilidades LightGBM, mezcla50/50 y corte estricto>2,75%. Los scores mezclan targets diferentes y no son probabilidades calibradas de BAJA+2.

Control local abril→mayo de esta configuración: lista promedio5 total$275.385.000,25%$68.846.250,9.906contactos y498BAJA+2. No es la ganancia pública del modelo final ni una predicción de agosto. Conservar preparación de datos original de este control para aislar cada cambio; cualquier corrección adicional va en su propio brazo.

## Qué ya se probó

Importes siguientes son diferencias de ganancia local total de la lista promedio contra control comparable, no ganancias públicas. No volver a lanzar la misma prueba sin cambiar una hipótesis concreta.

| Prueba | Diferencia | Estado |
| --- | ---: | --- |
| Promedio20 en lugar de5 | −$5.555.000 | Completa; no promover |
| Ocho señales de vínculos recurrentes,189→197 | −$3.162.500 | Completa; no promover el bloque completo |
| Cluster como columna,189→190, dentro del ensemble | −$6.435.000 | Completa; no promover esta representación |
| Cuatro modelos especialistas dentro del ensemble | −$9.597.500 | Completa; no promover |
| Mezcla general/especialista50/50 dentro de LightGBM | −$1.402.500 | Completa; no promover |
| Elegir general/especialista/mezcla por segmento, por cruces | −$1.127.500 | Completa; no promover |
| Pesos por segmento, por cruces | −$3.410.000 | Completa; no promover |
| Cortes por segmento, por cruces | +$11.440.000 | Evidencia mixta; revisar estabilidad |
| Corte global elegido con los mismos cruces | +$11.742.500 | Supera a cortes segmentados por$302.500; eligió3,25%, que ya perdió en público |

La primera prueba108 fue LightGBM solo, con otras ventanas; no es el ensayo122 dentro del ensemble. Agregar un cluster, entrenar especialistas y cambiar decisiones por segmento son tres hipótesis distintas.

Fuentes: [promedio20](salidas/promedio20_hist189_20261010/MINI_INFORME.md), [vínculos](salidas/vinculos_recurrentes_20261010/MINI_INFORME.md), [columna cluster](salidas/cluster_columna_ensemble_20261010/MINI_INFORME.md), [especialistas](salidas/estrategias_segmentos_20261010/MINI_INFORME.md), [políticas](salidas/estrategias_segmentos_20261010/INFORME_POLITICAS.md), [elección de modelo](salidas/estrategias_segmentos_20261010/INFORME_SELECCION_MODELOS.md).

## Orden de trabajo

### 1. Estabilidad temporal de decisiones por segmento

Pregunta: ¿los cortes segmentados aportan algo que se sostenga fuera de mayo y más allá de ajustar un único corte?

- Reutilizar el segmentador119 aprendido solo en abril; conservar sus números de grupo, no interpretar el cluster0 de un nuevo ajuste como el mismo segmento.
- Elegir una política definitiva usando mayo y la grilla ya fijada en120; mantener dos alternativas: un corte global y cortes por segmento. Registrar estas políticas antes de consultar su resultado de junio. No seleccionar nuevas alternativas con junio.
- Entrenar control LightGBM189 marzo+abril→junio, cinco semillas y parámetros16 originales. Mayo se usa exclusivamente como historia auxiliar, sin sus etiquetas para entrenar LightGBM. Las reglas de decisión sí fueron seleccionadas con mayo; declararlo explícitamente.
- Reutilizar TabPFN202 BAJA+2 marzo+abril→junio, dos estimadores, de `salidas/tabpfn_historicas_20261004_172322_339836/`. Verificar manifest, hashes, features, claves, universo y etiquetas; no usar predicciones de otra ventana ni crear una nueva API por defecto.
- Comparar en junio: regla fija50/50/>2,75%, corte global seleccionado en mayo y cortes por segmento seleccionados en mayo. Mismas probabilidades para los tres brazos; medir diferencias por grupo y semilla.
- Costo previsto: hasta cinco fits LightGBM nuevos; reusar solo modelos189 de la misma preparación/ventana si sus firmas y predicciones coinciden. Ningún fit TabPFN.
- Cerrar esta rama si la regla segmentada no mejora al control fijo y al ajuste global comparable, o si la mejora depende de muy pocos clientes/inestabilidad entre grupos. El objetivo no es volver a probar3,25% en el Bot.

Junio ya fue expuesto y tiene aguinaldo: es una comprobación exploratoria de estabilidad, no un test independiente. El cambio de tamaño y separación temporal del entrenamiento también limita comparaciones entre meses. La segmentación en junio debe usar solo sus predictores, no etiquetas.

### 2. Vínculos recurrentes: separar actividad de tenencia

Pregunta: ¿débitos y pagos aportan señal, mientras cancelaciones normales de préstamos/inversiones perjudican el bloque completo?

- Primera y única variante inicial: agregar cuatro señales a las189 actuales: pérdida de débitos, pérdida de pagos, cantidad actual de servicios de débitos/pagos positivos y cambio de esa cantidad frente al mes calendario anterior. Son cuatro columnas de `features_vinculos.py`, sin conteos que incluyan préstamos/inversiones.
- Comparar189→193 en abril→mayo, cinco semillas,273árboles, mismos parámetros, TabPFN202 guardado,50/50 y>2,75%. No agregar el cluster ni corregir otras columnas simultáneamente.
- Faltantes desconocidos; ausencia requiere todas las fuentes conocidas y en cero. Positivos parciales permiten establecer presencia. No buscar retrospectivamente el mejor subconjunto entre las ocho señales.
- Costo inicial: cinco fits locales nuevos. Si supera la puerta local, congelar el bloque y repetir marzo+abril→junio con el mismo control y TabPFN del paso1: otros cinco fits. Si pierde en mayo, cerrar esta rama; no generar variantes automáticamente.
- Préstamos/inversiones quedan fuera de esta primera variante porque representan tenencia y su caída puede ser una cancelación normal. Eso es una hipótesis a probar, no una causa demostrada del resultado anterior.

### 3. Calidad y drift: auditoría antes de correcciones

Pregunta: ¿hay una anomalía documentable que provoque un cambio artificial entre meses?

- Revisar nulos, ceros, valores imposibles y distribuciones mensuales, empezando por campos de mora y por la anomalía ya conocida de `ccajas_depositos` en mayo.
- Verificar cada interpretación contra el diccionario/material disponible. Un PSI alto o un cambio temporal por sí solo no demuestra error.
- Entregable inicial: tabla campo/mes/anomalía/evidencia/regla propuesta. Cero entrenamientos durante la auditoría.
- Solo ante una regla sustentada: una corrección por vez, antes de históricos, aplicada igual a train y evaluación. Comparar contra su control idéntico salvo la corrección, cinco semillas; mantener mezcla/corte.
- No sustituir faltantes por cero ni eliminar variables automáticamente. La corrección conocida ya entró en otros ensayos; reconstruir la trazabilidad para no presentarla como nueva.

### 4. Diagnóstico de variables con canaritos — condicionado

Solo si los pasos anteriores no dan una candidata y persiste una sospecha concreta sobre variables. Agregar ruido para medir importancia espuria, sin seleccionar eliminaciones solo por importancia de entrenamiento. Fijar las variables a retirar antes de comprobar otra ventana. No abrir Optuna ni barrer clusters/K/cortes a la vez.

## Reglas de evaluación y avance

1. Métrica principal: ganancia de una sola lista obtenida del promedio5, porque coincide con la forma de la referencia36. Informar también media de cinco listas individuales, delta pareado por semilla, TP/FP/contactos y diferencias por grupo. Nunca intercambiar ambas métricas.
2. Cada comparación usa mismas filas, etiquetas, preparación de datos, ventana, semillas y TabPFN. Un cambio de ventana o corrección exige su propio control. No comparar un control de LightGBM solo con una mezcla.
3. Para candidatos de features: exigir delta positivo tanto en lista promedio como en media de cinco listas en mayo y en la comprobación temporal congelada. Revisar consistencia de semillas y grupos; su desviación no es un intervalo de confianza.
4. Para políticas segmentadas: además superar al ajuste global elegido con el mismo procedimiento. Separar el aporte de segmentar del aporte de cambiar el corte o peso.
5. Los cruces por cliente seleccionan en tres partes y evalúan en la cuarta; eso reduce optimismo directo, pero no vuelve independiente a mayo después de tantos experimentos. Ninguno de los resultados locales equivale a una garantía pública.
6. Preparar entrenamiento final abril+mayo→agosto solo para una candidata que pase las puertas. Conservar la entrega36 y fuentes intactas; una carpeta numerada por nueva entrega, código firmado, modelos/predicciones y reproducción exacta de CSV.
7. No enviar al Bot automáticamente. No gastar créditos TabPFN durante los pasos1–3. La combinación de targets invertidos202 sigue reservada por el usuario para última hora; requiere su propio presupuesto y no forma parte de este plan.

## Presupuesto y entregables

Primera tanda máxima prevista: cinco fits para control junio +cinco para servicios en mayo; si servicios mejora, otros cinco en junio. Hasta15fits locales, cero llamadas nuevas a TabPFN y cero submits. Una auditoría sustentada podría justificar después otra tanda de cinco fits por ventana; no se incluye por anticipado en los15.

No estimar duración exacta hasta reconstruir matrices y medir el primer fit; los fits anteriores fueron cortos, pero lectura del dataset y verificaciones también consumen tiempo. Evitar procesos duplicados o entrenamiento concurrente que compita por memoria.

Cada etapa entrega plan congelado, resultados totales/25%, tabla pareada por semilla/grupo, manifest con hashes, predicciones y verificación. El resumen vigente en NEXT_STEPS enlaza este plan; los apuntes inferiores se mantienen como historia.

## Cambio autorizado: submits exploratorios — 2026-10-10

Tomás informa que dispone de submits y pide relajar la exigencia de mejora local para probar candidatos cercanos. La puerta estricta anterior se conserva como criterio de evidencia; ya no impide preparar una prueba exploratoria autorizada con resultados mixtos. Registrar explícitamente la excepción, la diferencia en la lista promedio y la media entre semillas; no describir el candidato como una mejora demostrada.

Primera prueba elegida: entrega40, cuatro señales de débitos/pagos, LightGBM193+TabPFN202, promedio5,50/50,>2,75%,abril+mayo→agosto. Local promedio total+$137.500; media de listas individuales−$7.018.000,1/5semillas mejoran. Cinco fits finales nuevos; TabPFN original guardado,ceroAPI/créditos. Una lista de10.386clientes:483agregados y517retirados frente36. CSV y modelos verificados; entrega preparada, sin envío automático ni resultado público. [Informe40](salidas/01_entregas_bot/40_EnsembleServicios193Promedio5Corte275_20261010_093934/INFORME.md).

Referencia36 pública$98.175.000 intacta. Evaluar40 por su resultado público, que ya corresponde al25%; no dividir nuevamente. Esta decisión no autoriza consumo nuevo de TabPFN ni convierte resultados locales en garantía pública. La auditoría del paso3 sigue pendiente.

## Resultado paso2 — 2026-10-10

# Paso2 completado: cuatro señales de débitos/pagos

Abril→mayo, LightGBM189→193, cinco semillas,273árboles,mezcla50/50 con TabPFN202 guardado,corte>2,75%. Control total $275,385,000;25% $68,846,250.0. Candidato total $275,522,500;25% $68,880,625.0. Delta total $137,500;25% $34,375.0;delta medio listas individuales $-7,018,000.0. Mejoran 1/5semillas y 2/4partes.

No supera la puerta de mayo: no ejecutar junio, no entrenamiento final ni nueva entrega. Rama cerrada para este bloque. Cinco fits locales nuevos, cero API/créditos/submits. Mayo reutilizado; no prueba independiente. Referencia36 preservada. Siguiente pendiente del plan: auditoría de calidad/drift, no ejecutada por este encargo.


# Tres submits exploratorios preparados — 2026-10-10

Usuario confirma las tres variantes cercanas. Una lista promedio5 por variante, corte>2,75%, abril+mayo->agosto. Preparadas y verificadas, pendientes de envio manual y resultado publico. Referencia36 $98.175.000 conservada. 20 especialistas finales compartidos entre dos entregas y cinco fits finales de vinculos197; ceroAPI/creditos.

- **41 — Mezcla general/especialistas**: 9,806 clientes. [CSV](salidas/01_entregas_bot/41_EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654/adjuntos/EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654.csv); [informe](salidas/01_entregas_bot/41_EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654/INFORME.md). Comando: `submit EnsembleGeneralEspecialistasPromedio5Corte275_20261010_094654`.
- **42 — Eleccion de modelo por segmento**: 9,972 clientes. [CSV](salidas/01_entregas_bot/42_EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659/adjuntos/EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659.csv); [informe](salidas/01_entregas_bot/42_EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659/INFORME.md). Comando: `submit EnsembleModeloPorSegmentoPromedio5Corte275_20261010_094659`.
- **43 — Ocho vinculos recurrentes**: 10,404 clientes. [CSV](salidas/01_entregas_bot/43_EnsembleVinculos197Promedio5Corte275_20261010_094750/adjuntos/EnsembleVinculos197Promedio5Corte275_20261010_094750.csv); [informe](salidas/01_entregas_bot/43_EnsembleVinculos197Promedio5Corte275_20261010_094750/INFORME.md). Comando: `submit EnsembleVinculos197Promedio5Corte275_20261010_094750`.

Esperar resultados de estas entregas antes de seguir con experimentos. Pendiente posterior: paso3, auditoria de calidad/drift. No ejecutado en esta tanda. Cada ganancia publica ya corresponde al25%; no dividir otra vez. Todas son pruebas exploratorias, no mejoras demostradas.

## Resultado publico41 — 2026-10-10

Mezcla general/especialistas: **$97.075.000**, desvio $0, una sola lista. Queda $1.100.000 por debajo de36 ($98.175.000). Referencia36 conservada; faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. El desvio cero proviene de una sola lista y no mide estabilidad. Importes ya publicos del25%, sin volver a dividir. Esperar resultados42 y43 antes de continuar con experimentos;40 sigue sin resultado informado. Sin nuevos fits, APIs, creditos ni envios automaticos.

## Resultado publico42 — 2026-10-10

Eleccion de modelo por segmento: **$96.415.000**, desvio $0, una sola lista. Queda $1.760.000 por debajo de36 ($98.175.000) y $660.000 debajo de41 ($97.075.000). Ambas estrategias de especialistas probadas pierden contra36 en este publico; el resultado no descarta todas las formas de segmentacion. Referencia36 conservada: faltan $1.825.000 desde la mejor entrega para llegar a $100 millones. El desvio cero proviene de una sola lista y no mide estabilidad. Importes ya publicos del25%, sin volver a dividir. Esperar resultado43 antes de continuar con experimentos;40 sigue sin resultado informado. Sin nuevos fits, APIs, creditos ni envios automaticos.

## Nueva mejor entrega43: objetivo publico100M alcanzado — 2026-10-10

**43, ocho vinculos recurrentes: $100.815.000**, desvio $0, una sola lista de10.404clientes. Supera36 ($98.175.000) en **$2.640.000**,41 ($97.075.000) en $3.740.000 y42 ($96.415.000) en $4.400.000. **Objetivo publico $100 millones alcanzado, con $815.000 de excedente.** Nueva referencia43: LightGBM197 con ocho vinculos recurrentes y TabPFN202 guardado, promedio de cinco probabilidades, pesos50/50, corte>2,75%, abril+mayo->agosto. Segmentacion y especialistas no forman parte de43. Referencia36 y artefactos originales conservados.

La lista promedio perdia $3.162.500 en mayo y la media de cinco listas perdia $5.934.500; la prueba exploratoria autorizada mejora en el publico de agosto. Mantener ambos resultados; no reescribir la validacion local ni presentar el publico como garantia privada. Public gain ya corresponde al25%; no dividir otra vez. Desvio cero significa una sola lista.

Tanda41/42/43 completada, todos los resultados registrados.40 sigue sin resultado informado. Siguiente trabajo pendiente: retomar plan desde auditoria de calidad/drift, usando43 como referencia vigente y36 para medir el aporte de los ocho vinculos. No se ejecutan nuevos experimentos por este registro. Cero nuevos fits, APIs, creditos o envios automaticos.

## Cinco listas de43 preparadas — 2026-10-10

Entrega44, cinco CSV por las semillas originales. Misma mezcla50/50 y corte>2,75%; modelos y predicciones reutilizados, cero fits/API/creditos. Adjuntar cinco archivos juntos con `submit EnsembleVinculos197Semillas5Corte275_20261010_095402`. Pendiente envio manual y resultado. La media de ganancias de cinco listas difiere de la ganancia de la lista promedio43, que sigue como referencia publica $100.815.000. [Informe](salidas/01_entregas_bot/44_EnsembleVinculos197Semillas5Corte275_20261010_095402/INFORME.md).

## Cinco ensembles completos de43 preparados — 2026-10-10

Entrega45: cinco CSV, cada uno promedia cinco LightGBM197 y mezcla50/50 con TabPFN202 guardado,corte>2,75%. Grupo1 identico a43, cuatro grupos nuevos con semillas disjuntas y congeladas.20fitsLightGBM nuevos,ceroAPI/creditos. Pedido corregido respecto de44 (unLightGBM por lista). Usar solo los cinco archivos de45 con `submit EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912`; pendientes de envio manual y resultado. Mejor publica43 $100.815.000 preservada. [Informe](salidas/01_entregas_bot/45_EnsembleVinculos197CincoEnsemblesCorte275_20261010_095912/INFORME.md).

## Resultado44 y cinco ensembles completos45 — 2026-10-10

44: media publica **$94.495.500**, desvio entre cinco listas **$2.864.200**. Queda $6.319.500 debajo de43 ($100.815.000), que conserva la mejor referencia y el objetivo publico alcanzado. Resultado repetido por el usuario con mismos valores; registrado una sola vez. 44 usa una semilla LightGBM197 y TabPFN compartido por lista;43 usa el promedio de cinco LightGBM antes del corte. No intercambiar estas dos metricas ni interpretar el desvio44 como desvio de la lista fija43.

El pedido corregido de cinco ensembles completos ya esta preparado como45: cada uno promedia cinco LightGBM197, mezcla50/50 con el mismo TabPFN y corte>2,75%. Grupo1 reproduce43 exactamente; otros cuatro usan veinte semillas nuevas congeladas. Pendiente envio manual de los cinco CSV de45 juntos y resultado. Public gain ya corresponde al25%, sin volver a dividir. Este registro no agrega fits/API/creditos/envios.

## Resultado45: cinco ensembles completos — 2026-10-10

**Media publica $96.838.500, desvio $2.037.600**, cinco ensembles completos. Resultado atribuido a45 por contexto inmediato; el usuario no repite numero. Media $3.976.500 debajo de43 ($100.815.000) y $1.336.500 debajo de36 ($98.175.000). Frente a44 (media $94.495.500/desvio $2.864.200), la media es $2.343.000 mayor y el desvio $826.600 menor. Las tandas usan grupos distintos: no es comparacion pareada que aisle la agregacion.

Grupo1 reproduce43; grupos2-5 promedian cinco LightGBM197 con semillas nuevas, todos mezclados50/50 con el mismo TabPFN202 y corte>2,75%. La lista43 conserva la mejor referencia publica y el objetivo publico alcanzado; su $100.815.000 no representa la media entre replicas observada. Primera replica seleccionada previamente por score; nuevas replicas sin seleccion por rendimiento. No hay resultados individuales informados para identificar la mejor de las cuatro nuevas. Desvio entre cinco ensembles no es intervalo de confianza ni garantia privada.

Tanda de distribucion completada. Proximo trabajo pendiente: retomar plan de experimentos, preservando43 y reportando estabilidad ademas del mejor resultado.40 sigue sin resultado informado. Public gain ya corresponde al25%, sin volver a dividir. Registro sin nuevos fits/API/creditos/envios.

## Control pareado de vinculos preparado — 2026-10-10

Entrega46: cinco ensembles sin las ocho features vinculos, mismos grupos y resto configuracion que45.20fitsLightGBM nuevos,5reutilizados,ceroAPI/creditos. Grupo1 CSV identico a36. Bot solo muestra resumen: comparar aporte promedio = $96.838.500 -mediaControl; no cambios individuales ni desvio pareado calculables. Pendiente envio manual de cinco CSV juntos con `submit ControlHist189CincoEnsemblesPareados45_20261010_100721` y resultado. [Informe](salidas/01_entregas_bot/46_ControlHist189CincoEnsemblesPareados45_20261010_100721/INFORME.md). Mejor publica43 preservada.

## Control46: aporte promedio de vinculos completado — 2026-10-10

| Variante | Entrega | Media publica | Desvio entre cinco ensembles |
|---|---:|---:|---:|
| Con ocho vinculos197 |45|$96.838.500|$2.037.600|
| Sin ocho vinculos189 |46|$96.690.000|$943.700|

Mismos cinco grupos de semillas, datos abril+mayo->agosto,target combinado,273arboles, params,TabPFN202,pesos50/50 y corte>2,75%. **Aporte promedio de vinculos: +$148.500**, aproximadamente0,154% frente al control. Desvio marginal observado mayor con vinculos; no confundir diferencia de desvios marginales con desvio de diferencias pareadas.

**Grupo1 conocido:**43 $100.815.000 contra36 $98.175.000,delta+$2.640.000. **Otros cuatro grupos:** media con vinculos derivada aprox.$95.844.375, sin vinculos aprox.$96.318.750,delta promedio aprox.**-$474.375**. Derivacion: (5*delta promedio total -delta grupo1)/4. Aproximado por redondeo de agregados. La gran ventaja del grupo1 no se sostuvo en promedio en los cuatro grupos nuevos. No sabemos que grupos particulares mejoran ni cuantos: Bot solo devuelve resumen. No inferir significancia o intervalo de confianza sin resultados individuales/covarianza.

Conservar43 como mejor lista publica y objetivo100M alcanzado, sin atribuir su valor al rendimiento tipico. No declarar ocho vinculos como mejora consistente. Control189 de46 queda disponible para proximas comparaciones; conservar ambos lados y mismos grupos. Publico reutilizado y primer grupo previamente elegido; evaluacion exploratoria, no test independiente. Resultado46 atribuido por contexto inmediato. Registro sin nuevos fits/API/creditos/envios; public gain ya corresponde al25%, sin volver a dividir.40 sin resultado informado.

## Paso3: auditoría inicial completa — 2026-10-10

21predictores y seis meses, sin etiquetas/fits/API. Corrección conocida ccajas de mayo no está en control189; mora Visa cambia nulo→cero en mayo/agosto pero sin semántica confirmada, no corregir automáticamente. Próxima prueba: sensibilidad ccajas=NA en mayo con cinco modelos189 y TabPFN guardados, sin cambiar mezcla/corte. Sin entrenamiento final ni entrega nueva. [Informe](salidas/auditoria_calidad_drift_20261010_v3/INFORME.md).


## Sensibilidad ccajas189 completada ? 2026-10-10

Delta total$0, cinco modelos guardados sin cambios en probabilidades. Correcci?n conocida v?lida; esta sensibilidad no aporta ganancia. Reentrenar con mayo corregido sigue sin medir. [Informe](salidas/sensibilidad_ccajas189_20261010_v2/INFORME.md). Sin fits/API/cr?ditos ni nueva entrega.

## Paso4 completado: canaritos y una ablación — 2026-10-10

No promover el bloque retirado: no mejora simultáneamente la lista promedio5 y la media de cinco listas individuales. Mantener LightGBM189 + TabPFN202.

Diagnóstico19ruidos: delta total$-8.167.500. Ablación189→181: delta total$-16.225.000, media listas$-10.312.500;1/5 semillas mejoran. Diez fits locales, ceroAPI/créditos/submits. [Informe](salidas/canaritos189_20261010/INFORME.md).


## Resultado publico40 registrado — 2026-10-10

Cuatro señales de débitos/pagos, LightGBM193 +TabPFN202, promedio5,50/50,corte>2,75%: **$97.185.000**, desvio0, una lista. Frente36($98.175.000), **-$990.000**; frente43($100.815.000), **-$3.630.000**. No mejora al control36; bloque servicios193 cerrado tras prueba exploratoria pública. Conservar evidencia local: lista promedio+$137.500 total, media listas individuales-$7.018.000. Mejor entrega pública43 y base de comparación189+TabPFN202 conservadas. Desvio0 por única lista, no estabilidad. Importes públicos ya25%, no dividir otra vez. Pendiente40 resuelto. Plan segmentación/vínculos/calidad/canaritos completado; targets invertidos202 sigue reservado, reentrenamiento con mayo corregido sin evaluar, semántica de ceros mora sin confirmar. Registro sin nuevos fits/API/créditos/envíos.

# Targets invertidos202, corte2,75% preparados ? 2026-10-10

LightGBM202 BAJA+2 +TabPFN202 BAJA+1/BAJA+2; promedio cinco LightGBM y mezcla50/50, score estricto>0,0275 fijado por el usuario. Cinco modelos finales abril+mayo?agosto completos y verificados. Se conserva la preparaci?n202 hist?rica, sin v?nculos ni nueva correcci?n ccajas.

Local abril?mayo: control202 total$267,217,500; invertido202 total$268,702,500; diferencia$1,485,000; media diferencias en cinco listas$4,691,500.0. Frente al control189 actual de$275.385.000, diferencia$-6,682,500; esa comparaci?n tambi?n cambia features. Valores totales de mayo, no Public gain. Mayo/semillas reutilizados.

Payload API: matriz327.052?202 abril+mayo y target combinado;164.647?202 agosto. Sin ID/mes/labelsagosto. Cotizaci?n74.179cr?ditos; l?mite propuesto80.000. Autorizaci?n espec?fica solicitada, todav?a pendiente; no nuevos datos enviados a inferencia ni cr?ditos consumidos.

Despu?s de autorizar: script148 --ejecutar y script149 generan una ?nica lista promedio5 de cinco modelos, comparable en agregaci?n/corte con43. Resultado p?blico desconocido. Fuentes y mejor43 conservadas.

## Resultado público47: targets invertidos202 — 2026-10-10

**$99.110.000**, desvio0, una lista promedio5 de10.609clientes. LightGBM202 BAJA+2 +TabPFN202 combinado,50/50,>2,75%,abril+mayo→agosto. Frente36($98.175.000): **+$935.000**. Frente43($100.815.000): **-$1.705.000**. Esta entrega queda$890.000 por debajo de100M; el objetivo ya se alcanzó con43, que sigue como mejor pública. No interpretar desvio0 como estabilidad. Comparación contra36 cambia también189→202, por lo que no aisla efecto de los targets. Conservar local: invertido202$268.702.500 total, control202$267.217.500,delta+$1.485.000; contra189$275.385.000,delta-$6.682.500. Importes públicos ya25%, no dividir nuevamente. Candidato reservado resuelto en esta configuración; no nuevas API/créditos/fits/envíos por registro. Historial, CSV, modelos y mejor43 preservados. Reentrenar con mayo corregido sigue sin evaluar; semántica de ceros mora sigue sin confirmar.

## Entrega 48: TabPFN v3.5 frente a43

Cambio exclusivo de version TabPFN v3.5-fast a v3.5;202variables,targetBAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. Cinco LightGBM197 originales de43, targetcombinado; mezcla50/50,promedio5,corteestricto>2,75%. 10834clientes; 10192comunes con43,642agregados,212retirados. Consumo real 151033creditos, limiteautorizado160.000. Sin validacion local nueva para esta version; resultado publico pendiente. Paquete43 publicado y mejorpublica100.815M conservados. Una lista no mide distribucion entre ensembles. Sin envio automatico al Bot.

Comando: `submit EnsembleVinculos197TabPFN35Promedio5Corte275_20261010_172925`. Adjuntar solo `adjuntos/EnsembleVinculos197TabPFN35Promedio5Corte275_20261010_172925.csv`.

## Resultado publico48: TabPFN v3.5 — 2026-10-10

**$98.862.500**, desvio0, una lista promedio5 de10.834clientes. Frente43($100.815.000): **-$1.952.500**; frente47($99.110.000): -$247.500; frente36($98.175.000): +$687.500. Cambio exclusivo de version TabPFN v3.5-fast a v3.5,202variables,BAJA+2,dosestimadores,semilla214363,abril+mayo->agosto. Se reutilizaron los cinco LightGBM197 de43,mezcla50/50,corte>2,75%. Consumo151.033creditos; no mejoro la referencia43 en este publico. No generalizar a superioridad de una version ni interpretar desvio0 como estabilidad. Prueba cerrada. Mejor43 y su paquete GitHub se conservan como final elegida; sin nuevas API,fits,creditos o envios por este registro.
