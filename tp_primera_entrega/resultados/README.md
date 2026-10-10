# Resultados y validacion

Esta carpeta conserva los resultados del Bot y las verificaciones finales de las entregas, junto con el informe de la reproduccion43 en ambiente limpio y sus dependencias resueltas.

Entrega final elegida: **43**, ganancia publica historica **$100.815.000**. El paquete reproducible completo se encuentra en [entregas/entrega_final_43](../../entregas/entrega_final_43/README.md).

La validacion en limpio uso un clon nuevo del commit6ea5f3dc13b4e5f7e83953bbf478997a17cd8218 y dos entornos vacios Python3.14.6. Se reprodujo exactamente el CSV de10.404clientes, con diferencia0 en los cinco LightGBM. Las matrices y el target de TabPFN se verificaron; se omitio por decision de Tomas una nueva inferencia remota, con consumo0creditos.

Los scripts originales conservan sus rutas historicas bajo tp_primera_entrega/salidas/. Esta carpeta es un registro de resultados; los datasets y artefactos intermedios grandes permanecen locales. El paquete final incluye los modelos y probabilidades necesarios para la reproduccion43.
