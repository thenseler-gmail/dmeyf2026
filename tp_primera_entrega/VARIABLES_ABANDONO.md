# Senales de interrupcion y caida conjunta

Implementacion aislada en `features_abandono.py`. Se conservan sin cambios `features.py` y `baseline.py`, para poder reproducir las referencias.

Todas las comparaciones usan el mismo cliente y el mes calendario inmediatamente anterior. Un hueco mensual no toma como anterior el ultimo registro disponible. NaN significa informacion desconocida, no ausencia de actividad. No se usan etiquetas ni datos futuros.

El bloque completo agrega 13 columnas a las 202 actuales:

- Ocho banderas de paso a cero: valor anterior positivo y actual exactamente cero, para ctrx_quarter, consumo Visa y Master, transacciones Visa y Master, homebanking, app y mpayroll.
- Bandera de reduccion de cantidad de productos.
- Cantidad y fraccion de siete actividades en caida. La fraccion es una transformacion equivalente del conteo; no aporta informacion independiente.
- Cantidad de frentes en caida: ctrx_quarter, consumo total Visa+Master y saldo de cuentas. La suma de consumos y el conteo requieren todos sus componentes conocidos.
- Bandera de caida simultanea de los tres frentes.

Las banderas son 0/1 solo si ambos valores son conocidos. Los conteos son faltantes si falta algun componente. Un consumo o saldo menor no prueba abandono ni identifica su causa. `ctrx_quarter` conserva su significado trimestral original; la comparacion entre fotos no lo transforma en una medicion mensual independiente.

No se agregaron tendencias de dos caidas consecutivas: el entrenamiento alineado marzo/abril no tiene ejemplos con dos meses anteriores observables. En marzo falta febrero y en abril falta enero/febrero para esos patrones. Crear columnas completamente faltantes en train no permitiria aprender su efecto.

Comparacion por familias en mayo, con abril como train y tres semillas: haberes (una bandera); actividades que pasan a cero (siete banderas); caidas conjuntas (cuatro columnas, sin duplicar conteo con fraccion). La familia se elige por ganancia de mezcla 50/50 en mayo, luego se comprueba en junio con train marzo/abril y veinte semillas. Parametros y umbral > 0.025 fijos.

La bandera de haberes detecta acreditacion registrada que pasa de positiva a cero; no confirma que el cliente dejo de trabajar ni que cerro su cuenta.
