"""EDA descriptivo local. No modifica los CSV ni entrena modelos."""
from pathlib import Path
import html
import json
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'monday' / 'reporte_clase04'


def familia(nombre):
    if nombre in ('numero_de_cliente', 'foto_mes'): return 'Identificación y tiempo'
    if nombre == 'clase_ternaria': return 'Objetivo'
    if nombre.startswith(('Visa_', 'Master_')) or 'tarjeta' in nombre: return 'Tarjetas'
    if 'prestamo' in nombre: return 'Préstamos'
    if any(x in nombre for x in ('inversion', 'plazo_fijo', 'forex')): return 'Inversiones y cambios'
    if any(x in nombre for x in ('rentabilidad', 'comision', 'margen')): return 'Rentabilidad y comisiones'
    if any(x in nombre for x in ('payroll', 'transferencia', 'cheque', 'pagode', 'pagomis')): return 'Haberes, transferencias y pagos'
    if any(x in nombre for x in ('seguro', 'seguridad')): return 'Seguros y caja de seguridad'
    if any(x in nombre for x in ('cuenta', 'caja_ahorro', 'descubierto')): return 'Cuentas y saldos'
    if any(x in nombre for x in ('cliente_', 'cproductos', 'active_quarter')): return 'Perfil y vinculación'
    return 'Canales y actividad'


def orientacion(nombre):
    exact = {'numero_de_cliente': 'Identificador; no es una medida de comportamiento.',
             'foto_mes': 'Mes de la observación en formato AAAAMM.',
             'clase_ternaria': 'Categoría construida con presencia en los dos meses siguientes.',
             'ctrx_quarter': 'Actividad transaccional trimestral; no interpretar como conteo exclusivamente mensual.',
             'mpayroll': 'Monto de haberes; validar definición y unidad con el diccionario.',
             'mcuentas_saldo': 'Saldo de cuentas; validar alcance con el diccionario.'}
    if nombre in exact: return exact[nombre]
    campo = nombre.split('_', 1)[1] if nombre.startswith(('Visa_', 'Master_')) else nombre
    if campo.startswith('m'): return 'Monto o saldo según el nombre; moneda, escala y período pendientes de confirmar.'
    if campo.startswith('c'): return 'Conteo o indicador según el nombre; confirmar codificación.'
    if campo.startswith('t') or campo in ('status', 'delinquency'): return 'Tipo, estado o indicador; no asumir magnitud numérica continua.'
    if campo.startswith('F') or campo in ('fechaalta', 'fultimo_cierre'): return 'Campo asociado a fecha; confirmar si representa fecha o distancia temporal.'
    return 'Atributo o indicador; definición exacta pendiente de diccionario.'


def main():
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='2GB'")
    con.execute('SET threads=1')
    con.execute('SET preserve_insertion_order=false')
    con.read_csv(str(ROOT / 'data/competencia_01.csv')).create_view('datos')
    schema = con.sql('DESCRIBE datos').df()
    names = schema.column_name.tolist()
    summary = pd.concat([con.sql('SUMMARIZE SELECT '+','.join('"'+v+'"' for v in names[i:i+12])+' FROM datos').df() for i in range(0,len(names),12)],ignore_index=True)
    counts = con.sql('SELECT count(*) n, count(distinct numero_de_cliente) clientes FROM datos').fetchone()
    n, clientes = counts
    meses = con.sql('SELECT foto_mes, count(*) filas, count(distinct numero_de_cliente) clientes, count(*) FILTER(WHERE clase_ternaria IS NULL) objetivo_faltante FROM datos GROUP BY 1 ORDER BY 1').df()
    target = con.sql("SELECT foto_mes, coalesce(clase_ternaria, 'SIN OBJETIVO') clase, count(*) cantidad FROM datos GROUP BY 1,2 ORDER BY 1,2").df()
    hist = con.sql('SELECT meses_observados, count(*) clientes FROM (SELECT numero_de_cliente, count(*) meses_observados FROM datos GROUP BY 1) GROUP BY 1 ORDER BY 1').df()
    gaps = con.sql('WITH t AS (SELECT foto_mes, foto_mes//100*12+foto_mes%100-lag(foto_mes//100*12+foto_mes%100) OVER(PARTITION BY numero_de_cliente ORDER BY foto_mes) distancia FROM datos) SELECT foto_mes, count(*) FILTER(WHERE distancia=1) con_mes_anterior, count(*) FILTER(WHERE distancia>1) con_salto, count(*) FILTER(WHERE distancia IS NULL) primera_observacion FROM t GROUP BY 1 ORDER BY 1').df()
    duplicados = con.sql('SELECT count(*) FROM (SELECT numero_de_cliente, foto_mes FROM datos GROUP BY 1,2 HAVING count(*)>1)').fetchone()[0]
    expresiones = []
    for nombre, tipo in schema[['column_name', 'column_type']].itertuples(index=False, name=None):
        q = '"' + nombre.replace('"', '""') + '"'
        expresiones += [f'count(*) FILTER(WHERE {q} IS NULL)', f'count(DISTINCT {q})']
        expresiones += [f'count(*) FILTER(WHERE {q}=0)', f'count(*) FILTER(WHERE {q}<0)', f'count(*) FILTER(WHERE NOT isfinite({q}))'] if tipo != 'VARCHAR' else ['NULL', 'NULL', 'NULL']
    valores = tuple(v for i in range(0,len(expresiones),60) for v in con.sql('SELECT ' + ','.join(expresiones[i:i+60]) + ' FROM datos').fetchone())
    inventory = summary[['column_name','column_type','min','max','avg','std','q25','q50','q75']].copy()
    inventory.columns = ['columna','tipo','minimo','maximo','media','desvio','p25_aprox','mediana_aprox','p75_aprox']
    for j,k in enumerate(['nulos','distintos','ceros','negativos','no_finitos']): inventory[k] = list(valores[j::5])
    inventory['nulos_pct'] = (inventory.nulos * 100/n).round(2)
    inventory['ceros_pct'] = (inventory.ceros * 100/n).round(2)
    inventory.insert(1,'familia',inventory.columna.map(familia))
    inventory['lectura_orientativa'] = inventory.columna.map(orientacion)
    families = inventory.groupby('familia').size().reset_index(name='columnas')
    monthly_null = con.sql('SELECT foto_mes, ' + ','.join('round(100.0*count(*) FILTER(WHERE "'+v+'" IS NULL)/count(*),2) AS "'+v+'"' for v in inventory.columna) + ' FROM datos GROUP BY 1 ORDER BY 1').df()
    for nombre,df in [('inventario_columnas',inventory),('resumen_mensual',meses),('objetivo_por_mes',target),('historial_clientes',hist),('faltantes_por_mes',monthly_null),('saltos_temporales',gaps)]: df.to_csv(OUT/(nombre+'.csv'),index=False,encoding='utf-8-sig')
    def tabla(df): return df.to_html(index=False,border=0,na_rep='—',float_format=lambda x:f'{x:,.2f}')
    partes = [f'<h1>Reporte del dataset · Clase 04</h1><p>Fuente: data/competencia_01.csv. Análisis descriptivo de todo el archivo, sin entrenamiento ni selección de variables por ganancia.</p><div class="cards"><b>{n:,} filas</b><b>{clientes:,} clientes</b><b>{len(schema)} columnas</b><b>{duplicados} claves duplicadas</b></div>',
        '<h2>Cómo leer los datos</h2><p>La unidad de observación es cliente-mes. Una misma persona puede aparecer varias veces. El archivo crudo tiene 154 columnas; la versión utilizada agrega clase_ternaria. De las 155 columnas, dos son claves y una es el objetivo: quedan 152 campos candidatos a estudiar.</p>',
        '<h2>Cobertura mensual</h2>'+tabla(meses),
        '<p>Marzo a junio tienen objetivo completo. Julio tiene etiquetas parciales y agosto no tiene objetivo. No reemplazar objetivos faltantes por CONTINUA ni entrenar con julio como si fuera una muestra completamente etiquetada.</p>',
        '<h2>Mapa de columnas</h2><p>Agrupación orientativa por nombres, no diccionario oficial. Los prefijos m, c y t suelen orientar hacia montos, conteos y tipos, pero no garantizan la semántica. No sumar pesos y dólares ni interpretar códigos o fechas como cantidades sin validar sus unidades.</p>'+tabla(families),
        '<h2>Faltantes: 20 columnas con mayor proporción</h2>'+tabla(inventory.sort_values('nulos_pct',ascending=False)[['columna','nulos','nulos_pct']].head(20)),
        '<p>Un nulo puede representar ausencia de producto, dato no informado u otra situación. El porcentaje solo no permite distinguirlas. Revisar en conjunto con indicadores de tenencia y por mes.</p>',
        '<h2>Ceros: 20 columnas con mayor proporción</h2>'+tabla(inventory.sort_values('ceros_pct',ascending=False)[['columna','ceros','ceros_pct']].head(20)),
        '<h2>Columnas constantes o completamente vacías</h2>'+tabla(inventory[inventory.distintos<=1][['columna','distintos','nulos_pct','minimo','maximo']]),
        '<h2>Historial disponible</h2>'+tabla(hist)+tabla(gaps),
        '<p>Marzo no tiene pasado disponible en este archivo. Junio puede usar marzo, abril y mayo. Un registro anterior no siempre equivale al mes calendario anterior. La primera observación disponible tampoco prueba que ese sea el mes de alta.</p>',
        '<h2>Objetivo por mes</h2>'+tabla(target),
        '<p>El objetivo usa información futura para etiquetar; esa información no debe incorporarse a los predictores. Su observabilidad depende de disponer de los meses posteriores.</p>',
        '<h2>Inventario completo: 155 columnas</h2><p>Filtrá por nombre o familia. Los cuantiles son aproximados (SUMMARIZE de DuckDB). Mínimos, máximos, faltantes, ceros y cardinalidades se calcularon sobre todo el archivo. Las medias globales mezclan meses y no reemplazan un análisis temporal.</p><input id="buscar" placeholder="Buscar columna o familia" oninput="filtrar()"><div class="scroll" id="inventario">'+tabla(inventory)+'</div>',
        '<h2>Próximo paso, sin crear variables todavía</h2><p>Recorrer perfil del cliente, cuentas, tarjetas, actividad, haberes y otros productos. Para cada campo: confirmar significado y unidad, observar distribución y faltantes por mes, y recién después discutir una transformación. El inventario incluye valores negativos y no finitos para facilitar esa revisión; no son automáticamente errores.</p>']
    page='<!doctype html><html lang="es"><meta charset="utf-8"><title>EDA · Clase 04</title><style>body{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 24px;color:#203040;background:#f7f9fb}h1,h2{color:#12395a}h2{margin-top:36px}p{line-height:1.6}table{border-collapse:collapse;background:white;font-size:13px;width:100%;margin:16px 0}th,td{padding:9px;border-bottom:1px solid #dce3e8;text-align:left}th{background:#dfebf3;position:sticky;top:0}.cards{display:flex;gap:14px;flex-wrap:wrap}.cards b{padding:20px;background:#dfebf3;border-radius:8px}.scroll{overflow:auto;max-height:650px}input{padding:12px;width:380px;max-width:90%}</style>'+''.join(partes)+'<script>function filtrar(){const q=document.getElementById("buscar").value.toLowerCase();document.querySelectorAll("#inventario tbody tr").forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?"":"none")}</script></html>'
    (OUT/'reporte_dataset.html').write_text(page,encoding='utf-8')
    print(json.dumps({'filas':n,'clientes':clientes,'columnas':len(schema),'duplicados':duplicados,'familias':families.to_dict('records'),'top_nulos':inventory.sort_values('nulos_pct',ascending=False)[['columna','nulos_pct']].head(6).to_dict('records'),'constantes':inventory[inventory.distintos<=1].columna.tolist(),'reporte':str(OUT/'reporte_dataset.html')},ensure_ascii=False))


if __name__ == '__main__':
    main()
