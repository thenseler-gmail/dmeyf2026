"""Consulta cuota y estima consumo de PriorLabs sin subir datos ni inferir.

Requiere TABPFN_TOKEN y tabpfn-client, duckdb y numpy.
Cotiza una solicitud por etapa; si se usan lotes, hay que recotizarlos.
No garantiza elegibilidad: contrastar las dimensiones con los límites API.
"""
from pathlib import Path
import json
import os


def main():
    if not os.environ.get("TABPFN_TOKEN"):
        raise SystemExit("Falta TABPFN_TOKEN. Configurala en la terminal sin guardarla en el código.")

    import duckdb
    import numpy as np
    from tabpfn_client import estimate_cost, get_api_usage

    root = Path(__file__).resolve().parents[1]
    config = json.loads(
        (root / "tp_primera_entrega/config.json").read_text(encoding="utf-8")
    )
    dataset = root / config["dataset"]
    if not dataset.is_file():
        raise SystemExit(f"No se encontró {dataset}")

    with duckdb.connect() as con:
        con.read_csv(str(dataset)).create_view("datos")
        excluidas = {config["id_col"], config["mes_col"], config["target_col"]}
        columnas = [
            columna[0] for columna in con.execute("DESCRIBE datos").fetchall()
            if columna[0] not in excluidas
        ]
        mes_col = '"' + config["mes_col"].replace('"', '""') + '"'
        filas_por_mes = dict(con.execute(
            f"SELECT {mes_col}, COUNT(*) FROM datos "
            f"WHERE {mes_col} IN (202103, 202104, 202105, 202106) "
            f"GROUP BY {mes_col}"
        ).fetchall())

    etapas = [
        ("Validación: marzo -> mayo", [202103], 202105),
        ("Evaluación exploratoria: marzo + abril -> junio", [202103, 202104], 202106),
    ]
    if not columnas or any(not filas_por_mes.get(m) for m in [202103, 202104, 202105, 202106]):
        raise SystemExit("Faltan variables o filas para alguno de los meses requeridos.")

    print("Cuota de tu cuenta:", flush=True)
    print(get_api_usage(), flush=True)
    total = 0
    for nombre, meses_train, mes_evaluacion in etapas:
        n_train = sum(filas_por_mes[mes] for mes in meses_train)
        n_eval = filas_por_mes[mes_evaluacion]
        n_features = len(columnas)
        print(f"\n{nombre}", flush=True)
        print(f"Train: {n_train:,}; evaluación: {n_eval:,}; variables: {n_features}")
        print(f"Celdas train: {n_train * n_features:,}")
        print(f"Celdas evaluación: {n_eval * n_features:,}")
        print(f"Pares train/evaluación: {n_train * n_eval:,}", flush=True)

        # Solo tamaños: no contienen los valores del dataset.
        x_train = np.zeros((n_train, n_features), dtype=np.uint8)
        x_eval = np.zeros((n_eval, n_features), dtype=np.uint8)
        cotizacion = estimate_cost(
            x_train, x_eval, model_version="v3.5-fast", n_estimators=1,
        )
        print("Consumo estimado:", cotizacion.estimated_cost)
        print("Versión de precios:", cotizacion.pricing_version)
        print("Configuración cotizada:", cotizacion.inputs, flush=True)
        total += cotizacion.estimated_cost
        del x_train, x_eval

    print("\nTotal estimado de ambas etapas:", total)
    print("Comparar con el saldo diario/mensual y los límites efectivos del modelo.")
    print("Cotización sin lotes ni caché; el consumo final puede variar.")


if __name__ == "__main__":
    main()
