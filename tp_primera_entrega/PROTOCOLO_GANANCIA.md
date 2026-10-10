# Actualizacion vigente: corte del score (2026-10-05)

Tomas autorizo explorar la segunda opcion: tratar el ensemble como score y seleccionar un corte en historicos. El2.5% sigue como referencia y se conserva en entregas anteriores. Experimento11 usa3.3% sobre modelos202 de entrega8, seleccionado solo con mayo; no junio ni scorepublico. No representa P(BAJA+2) calibrada. El corte no se traslada automaticamente a otras configuraciones. Las instrucciones antiguas de corte siempre fijo, debajo, quedan como historial para este experimento.

# Criterio vigente

## Cambio de estrategia del 2026-10-05

Por instrucción de Tomás: pausar TabPFN y desarrollar LightGBM u otros modelos locales de código abierto. Objetivo confirmado para el domingo 11 de octubre: **$100.000.000 en el subconjunto público del Bot**. Una ganancia local total de $400.000.000 tiene un 25% de $100.000.000, pero no garantiza el puntaje público de agosto.

Junio deja de ser el criterio único de comprobación/selección. La preocupación por el aguinaldo motiva examinar la distribución de haberes; no demuestra por sí sola que junio sea inválido ni que deba excluirse del entrenamiento final.

Protocolo nuevo en `config_validacion_lightgbm.json`:

- Desarrollo: cuatro folds por cliente, con evaluación separada en abril y mayo. Para cada mes, el fit solo usa filas de otros clientes de marzo hasta ese mismo mes. Todas las filas de un cliente comparten fold. Es CV retrospectivo: las etiquetas de otros clientes del mes evaluado pueden entrar al fit; no simula predicción prospectiva ni mide drift temporal.
- Chequeo temporal: marzo -> mayo, dos meses de distancia, igual que junio -> agosto para la ventana más reciente. Marzo carece de febrero: no puede aprender el mismo historial que tendrá el modelo final. Mayo fue reutilizado: tampoco es un test independiente.
- Abril -> mayo queda como control retrospectivo con historia de entrenamiento observable; no reproduce la disponibilidad prospectiva de etiquetas BAJA+2 al cierre de mayo.
- Junio queda como prueba de estrés estacional, sin promover configuraciones solo por su ganancia allí. Julio tiene etiquetas incompletas y agosto no tiene target: no sirven como test completo.

Target principal: BAJA+2. El target combinado se conserva como control histórico; su salida estima BAJA+1/BAJA+2, no P(BAJA+2). La ganancia siempre premia únicamente BAJA+2. Mantener el umbral y no confundir una mejora de ordenamiento con calibración correcta.

Piloto `30_validacion_lightgbm.py`: parámetros congelados, sin Optuna, sin API ni agosto. Guarda particiones, auditoría por cliente/mes, predicciones y ganancias totales y su 25%. Una semilla inicial permite revisar el protocolo; los finalistas requieren más semillas antes de interpretar diferencias pequeñas.

Reentrenamiento solicitado con históricas y la señal de haberes: `33_reentrenar_lightgbm_haberes.py`, resultado `salidas/lgbm_haberes_particiones_20261005_191807/`. Misma asignación de clientes del piloto, tres semillas comunes, parámetros congelados; compara202 vs203variables para ambos targets. BAJA+2 con haberes: CVabril $520.657.500 total/25% $130.164.375,9.387 contactos; CVmayo $268.317.500 total/25% $67.079.375,8.363 contactos. Frente a históricas solas: abril -0,48%,mayo +2,34%. No se ajustaron hiperparámetros ni corte; resultados exploratorios.

Candidato solicitado BAJA+2/haberes: `salidas/01_entregas_bot/5_LightGBMHaberesBaja2_20261005_192751/`, marcado pendiente de envío. Entrenamiento final mayo+junio,20semillas,203variables,9.447 contactos agosto,p>2,5%. Junio no se usó para elegir esta configuración; entra como fuente de etiquetas del entrenamiento final. Ganancia agosto desconocida. Verificado por script34, incluyendo reproducción desde un modelo guardado. `adjuntos_bot/` contiene el promedio (1 CSV); `adjuntos_semillas/` las20listas individuales. Tomás confirmó máximo20archivos por corrida: dos corridas separadas para medir ambos resultados. No enviado ni promovido automáticamente por un puntaje local.

Estado actualizado por variante: lote20 enviado por Tomás,media pública $93.549.500,std$2.313.100; promedio20 sin resultado informado. Top5 solicitadas elegidas por ganancia media OOFabril/mayo pesos50/50 (desempate mayo yseed),tras evaluar20con los mismos grupos:541440,408476,741961,248865,717444. Ranking verificado en `salidas/top5_semillas_20261005_194616/`. Adjuntos_top5 contiene cincoCSV independientes; MENSAJE_TOP5.txt es el mensaje,pendientes de envío. La selección entre20 en meses reutilizados no constituye validación independiente ni garantiza resultado público.

## Reglas de ganancia y referencias históricas

Por instruccion de Tomas del 2026-10-05, seleccionar siempre clientes con probabilidad estrictamente mayor que 0.025. La cantidad de contactos es un resultado del umbral; no optimizarla ni reemplazarla por un top N.

Aplicar el criterio a LightGBM, TabPFN y promedio de probabilidades. No aplicar 0.025 a rankings: no representan probabilidades.

Al comunicar ganancias locales, informar ganancia total, 25% de referencia y contactos. El 25% local es una referencia proporcional, no una prediccion garantizada del publico de agosto. Los puntajes del bot ya corresponden a su subconjunto publico.

Protocolo anterior: selección con mayo y comprobación con junio. Sustituido por el desarrollo y chequeos detallados arriba; se conservan sus resultados como referencias exploratorias. Preservar las entregas historicas que se enviaron al bot, aunque usaran top N. El script 15 reproduce esas entregas historicas; no es el protocolo para generar nuevas entregas.

Revision vigente: `salidas/revision_umbral_20261005_131001/`. Se reevaluaron 15 candidatos existentes con tres semillas en mayo, sin repetir Optuna. Ganadores: BAJA+2 trial 29 y bajas combinadas trial 6. Comprobacion de junio con 20 semillas y mezcla fija 50/50.

Correccion temporal del 2026-10-05: para comprobar junio, entrenar ambos modelos con marzo + abril. Mayo aporta solo predictores para historia auxiliar. Reproduce la distancia temporal de mayo + junio -> agosto. El script 16 usa marzo/abril por defecto; abril/mayo queda disponible explicitamente como referencia retrospectiva anterior. La seleccion de parametros en mayo ya reutilizado permanece exploratoria.

Referencia alineada: `salidas/ensemble_junio_20261005_134901/`. LightGBM combinado trial6, 20 semillas, sin ajustar parametros: ganancia $402.765.000, 25% $100.691.250; mezcla 50/50 $412.665.000, 25% $103.166.250. La tercera entrega de agosto ya entrenaba ambos modelos con mayo/junio y no requiere regenerarse por esta correccion de evaluacion.


## Entrega combinada7 preparada (2026-10-05)

Decision vigente: junio puede usarse en entrenamiento final, no como validacion/criterio de seleccion. Retomado LightGBM BAJA+1/BAJA+2 + TabPFN BAJA+2,202features/peso50/50/umbral>0.025/cincosemillas. Carpeta `salidas/01_entregas_bot/7_EnsembleCombinadoTabPFN5_20261005_210238/`, PENDIENTE envio. Validacion alineada abril->mayo, no nuevosfoldsCVTabPFN. Agosto mayo/junio->agosto ya guardado; sin API. Informe/adjuntos_semillas(5)/adjuntos_promedio5(1) separados. No reemplaza automaticamente control ni acredita100millones publico.


## Optuna combinado completado (2026-10-05)

30trials y5finalistas por5semillas,202features,targetcombinado,p>0.025. Ninguna finalista mejora abril->mayo:mejor nueva total$243.347.500/25%$60.836.875 vscontrol$263.120.000/$65.780.000. Chequeomarzo->mayo mejora pero contradice; no promocion automatica. Conservartrial6/273rounds. Fuente `salidas/optuna_combinado_20261005_214007/INFORME.md`. Nojunio/agosto ni API; no entrega nueva. Siguiente investigacion: revisar criterio temporal de busqueda antes de aumentar trials.


## Ventanaabril/mayo completa tras autorizacion (2026-10-05)

BloqueoAPIresuelto poraprobacionexplicitaTomas. Carpeta8_EnsembleAbrilMayo5_20261005_220000:ensemblealineado50/50LightGBMcombinado+TabPFNBAJA+2,202features,trainabril/mayo->agosto,5semillasfijas,p>0.025. Consumo74179creditos. Cincoadjuntos_semillas preparados,PENDIENTEenvio;compararconlote5entrega7media$93.324.000/std$1.361.600. Promedio5de11188clientes separado. Sinlabelsagosto no ganancia local ni25%estimado. Informeactualcompleto yverificacion46.


## Trayectorias: candidatoexperimental9 (2026-10-05)

Auditoria yprueba bloque12 completadas:CVmayo clienteAprMay LightGBMlista promedio5 +5,41%(total$270.545.000/25%$67.636.250 vs$256.657.500/$64.164.375), mediaindividual +1,53%,4/5semillas mejoran. MezclaApr->May -1,65%:evidenciamixta,no breakthroughconfirmado. Cuatrofeatures no observadasenAbrtrain. Fuente `salidas/auditoria_trayectorias_20261005_230058/INFORME.md`. Candidato9_EnsembleTrayectorias5_20261005_230923 en subidas,PENDIENTEenvio,5LightGBM214+TabPFN202guardado,AprMaytrain,50/50/p>0.025.0creditos. Mantener entrega8 como referencia;posible probar9y luego ablarbloques/segmentos sin elegirmodelopublicorepetidamente.


Resultado entrega9, 2026-10-05:

Entrega9, cinco mezclas por semilla: Public gain mean 93.5330, std dev 2.0404. Media publica $93.533.000; desvio $2.040.400. Resultado informado por Tomas el 2026-10-05; Submission ID no informado. Frente a entrega8 ($94.418.500 / std $661.100): -$885.500 (-0,938%). Mantener entrega8 como referencia. El score ya es publico; no dividir por cuatro. Promedio5 y LightGBM solo pendientes.
La mejora del CV por cliente en mayo no se traslado al publico; el chequeo temporal abril->mayo ya habia empeorado. No ajustar el bloque solo buscando mejorar el publico. No se conocen scores individuales para inferir significacion o elegir una semilla. CSVs y modelos conservados sin cambios.


Entrega10 preparada, 2026-10-05:

Tomas solicito incorporar las nuevas columnas tambien a TabPFN. Script52 completa entrega10_EnsembleTrayectoriasTabPFN5_20261005_232428: LightGBM214 combinado reutilizado de entrega9, cinco modelos/predicciones reproducidos; TabPFN214 BAJA+2 nuevo, abril+mayo327052->agosto164647, v3.5-fast/2estimadores/seed214363/sin subsampling. API aprobada, credencial en memoria retirada al terminar, sin IDs/mes/labelsagosto en payload. Cotizacion y consumo real76210creditos; cuota acumulada1248029/20millones. Sin nuevos fits LightGBM, sin etiquetasjunio/validacionjunio.

Cinco mezclas50/50,p>0.025: contactos11374/11502/11353/11384/11290 en orden541440/408476/741961/248865/717444. Promedio5 separado11416; LightGBMsolo identico entrega9. Verificador53 reprodujo cinco modelos, matrices/target train, hashes,11CSV y listas exactas. Estado verificado/preparado, pendiente envio manual Bot. Comando submit EnsembleTrayectoriasTabPFN5_20261005_232428_semillas. Comparacion directa entrega9media93.5330/std2.0404; mejor referencia entrega8media94.4185/std0.6611. Ganancia agosto desconocida. Scripts/documentos guardados, modelos anteriores intactos.


Usuario autorizo segunda opcion: tratar mezcla como score y explorar corte, flexibilizando regla2.5% solo en este experimento. Script54 usa predicciones202 combinadas50/50 de ambos modelosApril->May guardadas entrega7, cinco semillasfijas. Grilla1%-6% paso0.1pp; elegir centro inferior de banda contigua mas larga a1% del maximo de ganancia media5listas, empate cercania2.5%. Regla fijada antes de leer scores de ganancia. Cuatroparticionescliente aleatorias seed214363: seleccionar con3/4 y comprobar1/4, excluyendo etiquetasclientesreservados. Cortes3.4/3.3/3.3/3.6%; cuatrofolds mejoran.

Media5individuales, sumareservadosMay: fijo2.5%total$258.368.000/25%$64.592.000,10612.8contactos; seleccioncruzada total$268.422.000/25%$67.105.500,8295.2contactos. Diferencia total+$10.054.000/25%+$2.513.500 (+3.89%). Cadafold usa su cortepropio: no es resultado de un unico3.3%. Mayo completo para congelar corte3.3%, banda2.9%-3.8%; cinco semillas mejoran en ajuste aparente. No nuevo testtemporal: mayo/semillas reutilizados y entrenamiento finalAprilMay distintoApril.

Script55 reprodujo cuatroselecciones, verifico que perturbaretique?tasreservadas no cambia corte, y preparo entrega11_EnsembleAbrilMayoCorte33_20261005_233208 sobre probabilidades entrega8 congeladas: modelos202,trainAprilMay,targetscombinado/BAJA2,50/50,solo corte cambia. CincoCSVverificados,contactos8973/9032/8929/9083/8893; reducciones2142/2117/2135/2103/2143. Ceroentrenamiento/API/creditos. Junio/Bot no leidos para elegir. No aplicar automaticamente a entrega10TabPFN214. Pendienteenvio manual,gananciaagostodesconocida. Comando submit EnsembleAbrilMayoCorte33_20261005_233208_semillas. CurvaPNG revisada, INFORME yCSV en salidas/corte_score_20261005_233108. Config politicaexploratoria agregada,umbralreferencia2.5%preservado.


Resultado Bot entrega11, 2026-10-05:

Entrega11 corte3.3%: media publica $93.335.000, desvio $1.809.600 (Bot93.3350/std1.8096), cinco CSV. Frente a entrega8 mismos modelos/semillas con corte2.5% ($94.418.500/std$661.100): -$1.083.500 (-1,148%). No promover corte3.3%; mantener entrega8 como referencia. Mejora en mayo no se transfirio al publico de agosto; no demuestra que 2.5% sea optimo universal ni que calibracion no ayude. No buscar cortes sucesivos con el publico. Score ya corresponde al subconjunto publico, no dividir por4. SubmissionID no informado; resultado de entrega10TabPFN214 sigue no informado. Modelos y CSV conservados intactos.


Resultado Bot entrega10, 2026-10-05:

Entrega10, cinco mezclas LightGBM214 + TabPFN214, train abril/mayo, 50/50 y corte2.5%: media publica $91.305.500, desvio $4.299.900 (Bot91.3055/std4.2999). Frente a entrega9 LightGBM214 + TabPFN202 ($93.533.000/std$2.040.400), solo cambia TabPFN: -$2.227.500 (-2,382%). Frente a referencia entrega8 ambos202 ($94.418.500/std$661.100): -$3.113.000 (-3,297%). No promover bloque12trayectorias ni en LightGBM ni TabPFN por estos resultados; conservar entrega8 como referencia. Mayor dispersion de cinco listas en esta muestra, no prueba de significacion ni causalidad general de cada feature. Resultado informado por Tomas; SubmissionID desconocido. Score ya publico, no dividir por4. LightGBMsolo y promedio5 de entrega10 siguen pendientes y no reciben este score. CSVs y modelos intactos.


Resultado Bot entrega12, 2026-10-06:

Entrega12 LightGBM solo, cinco semillas, targetcombinado202, trainabril/mayo y corte2.5%: media publica $91.690.500, desvio $2.100.000 (Bot91.6905/std2.1000). Frente a entrega8 mismos LightGBM mezclados50/50 con TabPFN202 ($94.418.500/std$661.100): LightGBMsolo -$2.728.000 (-2,889%); ensemble +2,975% sobre LightGBMsolo. La mezcla beneficia este lote publico y tiene menor dispersion entre cinco listas; sin scores individuales no prueba significacion ni generalizacion. Mantener entrega8 como referencia. No conocemos ganancia TabPFN solo abril/mayo. Score ya publico, no dividir por4. SubmissionID desconocido. Modelos/CSVs intactos.


Comparacion ventanas LightGBM, 2026-10-06:

Tomas autorizo continuar comparando ventanas. Script56 congela202variables, targetcombinado BAJA+1/BAJA+2, trial6/273rondas, cincosemillas541440/408476/741961/248865/717444,corte>2.5%. Junio solo train, sin validacion/criterioseleccion. Tresventanaspredefinidas, sin nuevaOptuna/API/creditos. ReferenciaLightGBMsoloAprilMay entrega12 media publica$91.690.500/std$2.100.000; referenciaensemble8$94.418.500/std$661.100 es otra estrategia.

Entrega13_LightGBMMayoJunio5_20261006_000247: prediccionesp_seed reutilizadasde7 yconfirmadas contrafuente3/hash. CincoCSV exclusivosLightGBM,noTabPFN,contactos13411/13190/12983/13384/13212. Comando submit LightGBMMayoJunio5_20261006_000247_semillas.

Entrega14_LightGBMAbrilMayoJunio5_20261006_000247: cincofitsnuevosAprilMayJune->August,modelosguardados/reproducidos ymatrizagostoidentica hashentrega8. Contactos13988/13981/13995/14323/13981. Comando submit LightGBMAbrilMayoJunio5_20261006_000247_semillas. Ningun modelo/archivo anterior alterado.

Ambas entregasverificadas,pendientes envio manual,cincocsv porcorrida separada. No repetir12. Gananciaagostodesconocida,no equivaler mascontactosamayorganancia. Una carpeta porentrega preservada. Estudio salidas/ventanas_lightgbm_20261006_000247 conplanfijado/comparacioncontactos/INFORME. Verificacionfinal10listasexactas/hashes,fuentes,features/params/seeds; cincoreloadsmodelosiguales antesexport; noAuglabels,noJunvalidation. Configpoliticaventanas guardada. No cambiareferencia8ni mezcla conTabPFNdedistintaventana.


Resultado Bot entrega13, 2026-10-06:

Entrega13, LightGBM solo202,targetcombinado, cinco semillasfijas, trainmayo/junio,corte2.5%: media publica $86.922.000, desvio $4.057.700 (Bot86.9220/std4.0577). Contra entrega12 mismos modelos/configuracion excepto ventana abril/mayo ($91.690.500/std$2.100.000): -$4.768.500 (-5,200%), mayor dispersion entre listas. Mantener abril+mayo como referencia LightGBMsolo. No atribuir causalmente al aguinaldo: sustitucion abril por junio y drift/cobertura pueden influir. Falta entrega14 abril+mayo+junio, sin resultado informado. Referenciaensemble8 sigue $94.418.500/std$661.100, estrategia distinta. Score ya publico, no dividir por4. SubmissionID desconocido, CSV/modelos conservados intactos.


Resultado Bot entrega14, 2026-10-06:

Entrega14 LightGBMsolo202,targetcombinado,cincosemillasfijas,trainabril/mayo/junio,corte2.5%: media publica $89.056.000, desvio $3.568.900 (Bot89.0560/std3.5689). Contra entrega12 abril/mayo $91.690.500/std$2.100.000: -$2.634.500 (-2,873%). Contra entrega13 mayo/junio $86.922.000/std$4.057.700: +$2.134.000 (+2,455%). Comparacion de tresventanas cerrada: mejor ventana evaluada LightGBMsolo abril+mayo. Agregar junio no mejora este lote/configuracion; no atribucion causal definitiva al aguinaldo ni generalizacion a otras configuraciones. Referencia general ensemble8 abril/mayo ambos202 50/50 corte2.5% conserva media$94.418.500/std$661.100. No mas busqueda de ventanas contra publico dentro de esta comparacion. SubmissionID desconocido. Score ya publico,no dividir por4. CSV/modelos intactos.


Comparacion local targets, 2026-10-06:

Usuario solicita priorizar validacionlocal por escasezsubmits. Script57 ejecuta cambioaislado de targetLightGBMcombinado->BAJA+2,202variables,params/273rondascongelados,cincosemillasfijas,trainabril->evalmayo; TabPFNBAJA+2 guardado misma ventana,50/50,p>0.025. Marzoauxhistoria, noJune/Augdatosleidos, noAPI/creditos, nofinalfit/candidato/submission. CincofitsnuevosLightGBM; cinco controlesguardados reproducidos contra rawMay; cinco nuevossavedmodelsreproducidos.

Media5listas individuales,LightGBMsolo control total$249.810.000/25%$62.452.500 vs BAJA2$200.260.500/$50.065.125. Mezclaactual control total$258.368.000/25%$64.592.000,10612.8contactos,500.2TP/10112.6FP; ambosBAJA2 total$240.757.000/25%$60.189.250,7181.2contactos,398.4TP/6782.8FP. Diferencia total-$17.611.000/25%-$4.402.750 (-6,816%); cero/cincosemillasmejoran, cuatro partesclientesMaytambienpeor. MenosFPpero101.8TPmenos; ahorrocostos insuficiente.

Lista de probabilidadespromedio5,metrica separada: mezclaactual total$262.212.500/25%$65.553.125,10665contactos; nuevo total$241.312.500/$60.328.125,7225contactos. No confundir mediasindividuales/gananciaunicalista ni publicoagosto. Ganancias20individuales+4promedio5 reconstruidas por sumasdirectaspagos; cinco cambioscontactos verifican deltas; partes suman totales. Graficodecomparacionsemillas revisado; INFORME/predicciones/modelos/resultados/hash/verificacion en salidas/validacion_targets_ensemble_20261006_002629.

No preparar submitdeesta configuracion. Parametros provienen del targetcombinado: resultado descarta este cambioaislado, no todas las configuracionesBAJA2. Mayo/semillasreutilizados, April->May no disponibilidadprospectivacompletadelabels: no testtemporalindependiente, no garantiaagosto. Proximaexploracionlocal opcional: parametrospropiosBAJA2, sinBot; noAPI TabPFNtargetcombinadorequerida por este ensayo.


Regla de envio al Bot - 2026-10-06:

Tomas establece puerta de promocion: enviar al Bot solo si candidato supera localmente al control de entrega8. Comparaciones deben usar mismas filas/split/semillas/regla/metricas, sin junio validacion; metrica principal media de cinco listas individuales. Control local disponible abril->mayo de configuracion202/combinado+TabBAJA2/50-50: total$258.368.000/25%$64.592.000. No comparar ese total con scorepublico$94.418.500; son evaluaciones distintas. Control local es configuracion de8 reentrenadaApril, no test del modelo finalAprilMay. No submit de candidatos sin mejora local; mejora local tampoco garantiza publica. Regla guardada config_validacion_lightgbm politica_promocion_bot.


Matriz local de targets, 2026-10-06:

Tomas solicita ambos targetscombinados LightGBM/TabPFN. Script58 preparaApril->May202variables,cincoLightGBMcombinadosguardados/reproducidos,TabPFNFast2seed214363nuevoBAJA1/BAJA2. API aprobada, matrices202abril/mayo sinIDs/mes/labelsMay,payloadtargetcombinadoApril. Estimado/real40736creditos,credencialenmemoria retirada alterminar. Un primerintentoimportMatplotlib fallo antespreparacion/API (priorlabsentorno noMatplotlib); soluciongraficolocal separado,sin nueva instalacion. DatosMarAprilMay solamente,noJun/Aug,0submits.

Amboscombinados mezcla50/50/corte2.5% media5 total$247.885.000/25%$61.971.250,13562contactos,564.4TP/12997.6FP,vscontrol8configApril->May LGBcombinadoTabBAJA2 total$258.368.000/$64.592.000,10612.8contactos,500.2TP/10112.6FP. Delta-$10.483.000/25%-$2.620.750 (-4,057%),1/5semillasmejora. No promover amboscombinados.

Se completa cuarta combinaciongratis con5LightGBMBAJA2 guardados experimento57,misma ventana/202features/params273 y semillas,keys/targets/alineacion/hash verificados. LGBBAJA2+Tabcombinado total$261.684.500/25%$65.421.125,10716.2contactos,505.8TP/10210.4FP; contra control +$3.316.500/25%+$829.125 (+1,284%),5/5semillasmejoran. Deltasporseed541440/408476/741961/248865/717444:990000/4950000/3602500/2585000/4455000. AmbosBAJA2 anterior$240.757.000/$60.189.250. Matriz4targets guardada yvalidada,no pesos/corte ajustados.

Salida salidas/validacion_tabpfn_combinado_20261006_003126, modelosLGBfuentes preservados,predicciones/CSVcomparacion/gr?ficorevisado/verificacion/manifest/INFORME. Gananciasdirectasrecalculadas,20resultadosadicionalesmatriz,metadata payload/checkpoints. GananciaAgostodesconocida/no fitsfinales/candidatosBot en esteensayo. La combinacioninvertida es candidataexploratoria; mejora peque?aenmayo reusado,semillas seleccionadas conAprilMay,no test temporal independiente,nogarantia publica. Soloha cumplidorequisitomejora local en esa comparacion.


CatBoost local, tres pruebas - 2026-10-06:

Usuario autoriza correr trescomparacionesCatBoostlocal ymini informe mientrasduerme. CatBoost1.2.10/graphviz0.21 instalados desdePyPI en .venv proyecto; primerintentosinred falla, escalacioninstalacion aprobada (descarga solo,sin datosclientes). Requirementscatboost fijado1.2.10. Script59: cincoCatBoostBAJA2 trainApril163284/evalMay163768,202variables,trescategoricasVisa_status/Master_status/tcuentas,params800trees/depth6/lr0.05/L2=5/Bernoulli0.8/rsm0.8/CPU4hilos,fijos,sinearlystoppingevalMay. ReusaLightGBMcombinado202 yTabPFNBAJA2control7April->May, mismo controlconfig8. Cortestricto2.5%,5semillasfijas.

Tresvariantesprespecificadas: CatBoostsolo,CatBoost+Tab50/50,LightGBM40/Tab40/Cat20. Son cincofitsnuevos,reutilizadospara3comparaciones,0API/creditos/submits,noJune/Augleidos ni fitsfinales. Medias5listas: control total$258.368.000/25%$64.592.000,10612.8contactos; CatBoostsolo $247.274.500/$61.818.625,8808.2contactos,delta-4.294%,0/5mejoran; Cat+Tab $254.760.000/$63.690.000,8928contactos,delta-1.396%,0/5; tres40/40/20 $261.833.000/$65.458.250,10326.8contactos,delta+$3.465.000/25%+$866.250 (+1.341%),5/5mejoran.

Mezclatres TP496.2/FP9830.6 vscontrol500.2/10112.6: net4TPmenos/282FPmenos. Agregados3.6TP180.2FP;retirados7.6TP462.2FP. Tres/cuatropartesMaymejoran,no mesesindependientes. Stdlocal5listas mezcla$3.175.708 vscontrol$2.684.837. Mayo/semillas reutilizados,nuevoconfigsinOptuna,no pruebaindependiente/nogarantiaBot. No preparar/enviarBotduranteestetrabajo; mezcla pasa requisito local pero pendiente revisionma?ana yCatfinalAprilMay->August. Candidatoinvertidoreservadoultimahora intacto.

Artefactos salidas/catboost_local_20261006_004259,MINI_INFORME.md contabla/conclusion/limites,parametros,cambiosTPFP,costos0. CincoCBM/modelos/predicciones/metricas/hashes/manifest/grafico revisado. Script60 verifica rawmatrices/target+5modelosCBreproducidos,20scores individuales,4listaspromedio5,80partes,20cambiosIDs/pagos,control258368000. Fuente LightGBM5reproducidaen59. Verificacion_independiente.jsonestadoverificado. Politicaconfiglocal actualizada; referenciaspublicas8 intactas. Sin procesosrestantes.
