# Prediccion final de churn — entrega 43

Esta carpeta contiene el codigo, los cinco modelos LightGBM y la salida congelada
de TabPFN utilizados para reproducir **exactamente** la prediccion final. El CSV
entregado tiene 10.404 clientes, sin encabezado ni indice, un identificador por
linea. La reproduccion verifica su igualdad byte por byte mediante SHA-256:

```text
4dcf5eff118dafa41953f66999203db6818017975d52010bad33c4881985496e
```

## Instalacion

Descargar o clonar el repositorio y abrir una terminal en esta carpeta. Se verifico
con Python 3.14.6; las versiones exactas de las bibliotecas estan en
`requirements.txt`. Ejemplo en Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En Linux/macOS, crear el entorno con `python3.14 -m venv .venv` y usar
`.venv/bin/python` en los comandos siguientes.

## Corrida principal: inferencia desde el dataset y los modelos

Usar el archivo original `competencia_01.csv` provisto por la catedra, con los
meses marzo a agosto de 2021 y los nombres de columnas originales. El dataset no
se incluye en GitHub. Se puede pasar una ruta absoluta; no requiere moverlo al
repositorio ni modificar configuraciones.

```powershell
.\.venv\Scripts\python.exe reproducir.py --dataset "C:\ruta\competencia_01.csv" --salida resultado_43
```

El script reconstruye las 197 variables de agosto usando historia pasada,
comprueba el hash de la matriz original, carga los cinco modelos guardados y
recalcula sus probabilidades. Luego incorpora las probabilidades originales de
TabPFN, calcula el ensamble, aplica el corte y genera:

- `resultado_43/prediccion_final.csv`: lista final identica a la entregada.
- `resultado_43/VERIFICACION.json`: hash, cantidad de clientes, hash de la matriz
  y diferencias contra las probabilidades historicas de cada modelo.

En una corrida correcta se imprime `estado: identico_byte_por_byte`. La tolerancia
de comparacion de probabilidades es 1e-15; la exigencia para el CSV es igualdad
exacta. Una matriz o lista diferente provoca un error. La inferencia no extrae
etiquetas y no requiere API, credenciales ni consumo de creditos.

## Corrida rapida: reconstruccion desde las probabilidades archivadas

```powershell
.\.venv\Scripts\python.exe reproducir.py --salida resultado_43
```

Esta alternativa no requiere el dataset: recalcula el ensamble y la seleccion
desde sus seis componentes guardados. Permite auditar inmediatamente la lista;
la corrida principal tambien verifica las variables y la inferencia LightGBM.

## Modelo y regla de seleccion

Entrenamiento original: abril y mayo de 2021, 327.052 filas. Prediccion: agosto
de 2021, 164.647 clientes. Los cinco LightGBM usan 197 variables (152 originales,
37 de historia y ocho de vinculos recurrentes), 273 arboles y las semillas
541440, 408476, 741961, 248865 y 717444. Su target es BAJA+1 o BAJA+2. Los parametros
y el orden exacto de las variables estan en `configuracion.json`.

TabPFN usa 202 variables y target BAJA+2; se reutiliza su prediccion original
abril+mayo -> agosto. La mezcla es un score de seleccion:

```text
score = 0.5 * promedio(p_lightgbm_de_las_5_semillas) + 0.5 * p_tabpfn
seleccionar si score > 0.0275
ordenar por score descendente, y por numero_de_cliente ascendente ante empate
```

No hay segmentacion. Las variables historicas y los vinculos se calculan por
mes calendario; los faltantes se preservan. Los valores no finitos se convierten
en faltantes y los vencimientos Visa/Master menores que -36500 se convierten en
faltantes, siguiendo el preprocesamiento original.

## Artefactos y alcance de la reproduccion

- `reproducir.py`: inferencia, ensamble, seleccion y verificacion.
- `features.py`, `features_vinculos.py`: codigo original de las variables.
- `modelos/seed*.txt`: cinco modelos LightGBM originales, sin reentrenamiento.
- `artefactos/predicciones_agosto.csv.gz`: probabilidades originales de los cinco
  LightGBM, TabPFN y el score, con claves para verificar su alineacion.
- `prediccion_final.csv`: referencia exacta de la lista entregada.
- `configuracion.json`, `procedencia.json`, `SHA256SUMS.json`: configuracion,
  procedencia y firmas de integridad.
- `VALIDACION.json`: evidencia de las dos corridas verificadas antes de publicar.

La reproduccion exacta corresponde a **inferencia y seleccion con artefactos
congelados**. TabPFN se ejecuto originalmente en el servicio remoto de Prior Labs;
se incluye su salida para evitar depender de acceso, costo y cambios del servicio.
Este paquete no reentrena TabPFN ni promete que una nueva llamada a ese servicio
genere el mismo resultado. Los modelos LightGBM tambien se incluyen ya entrenados.

Resultado publico informado para esta lista: mean 100.8150, std dev 0.0000
($100.815.000). Fue una unica lista; ese desvio no mide estabilidad entre semillas.
