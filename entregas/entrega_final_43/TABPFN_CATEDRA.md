# TabPFN con cuenta y key propias de la catedra

La catedra crea su propia cuenta de Prior Labs y genera su token desde
[API keys](https://platform.priorlabs.ai/account/api-keys). El SDK recibe esa
credencial mediante `TABPFN_TOKEN`, segun la
[documentacion oficial](https://github.com/PriorLabs/tabpfn-client#authentication).
No es necesario recibir una key del autor de la entrega.

Esta corrida requiere credito suficiente en esa cuenta. La ejecucion original
estimaba 74.179 creditos; la cotizacion actual se consulta antes de ejecutar y
puede cambiar. Crear una key no garantiza que la cuenta disponga de esa cuota.

## Entorno original de TabPFN

Usar un entorno separado del de inferencia LightGBM: los dos componentes se
ejecutaron originalmente con distintas versiones de numpy, pandas y duckdb.
`requirements-tabpfn.txt` conserva las versiones de la corrida TabPFN original,
incluido `tabpfn-client==0.6.1`.

Desde esta carpeta, en PowerShell:

```powershell
py -3.14 -m venv .venv-tabpfn
.\.venv-tabpfn\Scripts\python.exe -m pip install -r requirements-tabpfn.txt
```

Ingresar la key en la terminal con entrada oculta y guardarla solo en el entorno
del proceso, sin escribirla en codigo ni en el repositorio:

```powershell
$tokenCatedra = Read-Host "Key de Prior Labs" -AsSecureString
$env:TABPFN_TOKEN = [System.Net.NetworkCredential]::new('', $tokenCatedra).Password
```

En Linux/macOS, usar `.venv-tabpfn/bin/python` y configurar `TABPFN_TOKEN` en el
entorno de la terminal.

## 1. Verificar los datos localmente

```powershell
.\.venv-tabpfn\Scripts\python.exe recalcular_tabpfn.py --dataset "C:\ruta\competencia_01.csv" --salida resultado_tabpfn
```

Reconstruye las 202 variables originales, las matrices de abril+mayo y agosto y
el target BAJA+2. Comprueba sus tres hashes contra la corrida original. No hace
llamadas a la API y no consume creditos.

## 2. Consultar el costo actual

```powershell
.\.venv-tabpfn\Scripts\python.exe recalcular_tabpfn.py --dataset "C:\ruta\competencia_01.csv" --salida resultado_tabpfn --cotizar
```

La consulta usa dimensiones de las matrices, sin enviar datos reales de clientes.
Revisar `COTIZACION.json` y la cuota de la cuenta antes de la ejecucion.

## 3. Ejecutar TabPFN y comprobar la lista

Ejemplo con limite de 80.000 creditos (elegir el presupuesto autorizado por la
catedra):

```powershell
.\.venv-tabpfn\Scripts\python.exe recalcular_tabpfn.py --dataset "C:\ruta\competencia_01.csv" --salida resultado_tabpfn --ejecutar-api --max-creditos 80000
```

Este comando envia a Prior Labs las 202 variables de 327.052 filas de abril+mayo
y su target BAJA+2, y las 202 variables de 164.647 filas de agosto para predecir.
No envia identificadores, meses ni etiquetas de agosto. Si la cotizacion supera
el limite, no ejecuta la inferencia. El limite es una comprobacion del script,
no un limite configurado por key en el proveedor.

Se fija `v3.5-fast`, dos estimadores, semilla 214363, `fit_preprocessors`,
`autocast`, las categorias Visa_status/Master_status/tcuentas y
`SUBSAMPLE_SAMPLES=None`, como en la ejecucion original. La configuracion completa
y los hashes estan en `configuracion_tabpfn.json`.

El script guarda:

- `tabpfn_recalculado.csv`: respuesta nueva de TabPFN con claves locales.
- `prediccion_final_api.csv`: ensamble con los cinco componentes LightGBM
  originales y la nueva respuesta de TabPFN, corte estricto >2,75%.
- `COMPARACION.json`: diferencia maxima de probabilidades, cambios de seleccion
  y comparacion del hash de la lista final con la entrega 43.
- `ESTADO_API.json`: registro del intento, para evitar repetir consumo por error.

`csv_identico_byte_por_byte: true` confirma reproduccion exacta de la lista.
Si es falso, el programa termina con error y conserva los resultados para
inspeccion. Una misma version y semilla son controles de reproduccion; no se
afirma igualdad de la nueva respuesta del servicio hasta verificarla. La corrida
con artefactos archivados del README sigue reproduciendo la 43 exactamente.

Si hubo un error despues de iniciar la API, revisar el consumo antes de reintentar.
Una nueva corrida necesita otra carpeta de salida; no se reintenta automaticamente.
Al finalizar, limpiar la credencial de esta terminal:

```powershell
Remove-Item Env:TABPFN_TOKEN
$tokenCatedra = $null
```

El modo local de preparacion fue probado; el modo de inferencia remota de este
script no se ejecuto durante el armado del paquete y requiere la cuenta, credito
y autorizacion de la catedra.
