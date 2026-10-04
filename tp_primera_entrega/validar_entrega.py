"""Valida el formato propuesto de entrega; no evalúa calidad predictiva.

Ejemplo desde la raíz (agosto, mes configurado para la entrega):
    .venv/Scripts/python.exe tp_primera_entrega/validar_entrega.py salidas.csv

Los encabezados y el separador deben confirmarse con la consigna oficial.
"""

import argparse
import csv
from pathlib import Path

CLASES = {"CONTINUA", "BAJA+1", "BAJA+2"}


def validar_entrega(ruta, ids_esperados, columna_id="id",
                    columna_target="clase_ternaria", separador=","):
    """Exige una fila por cliente del mes objetivo, sin faltantes ni extras."""
    esperados = [str(valor) for valor in ids_esperados]
    if not esperados or len(set(esperados)) != len(esperados):
        raise ValueError("El universo esperado está vacío o tiene IDs duplicados.")
    vistos = set()
    conteos = dict.fromkeys(sorted(CLASES), 0)
    with Path(ruta).open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.reader(archivo, delimiter=separador)
        if next(lector, None) != [columna_id, columna_target]:
            raise ValueError(f"Encabezado requerido: {[columna_id, columna_target]}")
        for linea, fila in enumerate(lector, start=2):
            if len(fila) != 2:
                raise ValueError(f"Línea {linea}: se requieren exactamente dos campos.")
            cliente, clase = fila
            if not cliente or cliente != cliente.strip():
                raise ValueError(f"Línea {linea}: ID vacío o con espacios externos.")
            if cliente in vistos:
                raise ValueError(f"Línea {linea}: ID duplicado: {cliente}")
            if clase not in CLASES:
                raise ValueError(f"Línea {linea}: etiqueta inválida: {clase!r}")
            vistos.add(cliente)
            conteos[clase] += 1
    faltantes = set(esperados) - vistos
    extras = vistos - set(esperados)
    if faltantes or extras:
        raise ValueError(f"Clientes incorrectos: {len(faltantes)} faltantes y {len(extras)} extras.")
    return {"filas": len(vistos), "clases": conteos}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--mes", type=int,
                        help="Mes de la foto; por defecto entrega.mes_base_clientes en config.json (202108).")
    parser.add_argument("--columna-id", default="id")
    parser.add_argument("--columna-target", default="clase_ternaria")
    parser.add_argument("--separador", default=",")
    args = parser.parse_args()

    import json
    import duckdb

    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "tp_primera_entrega/config.json").read_text(encoding="utf-8"))
    mes = args.mes if args.mes is not None else config['entrega']['mes_base_clientes']
    if mes is None:
        parser.error('Falta configurar el mes de la foto o indicar --mes.')
    # Solo se lee el universo de clientes: no se copian etiquetas del dataset.
    with duckdb.connect() as con:
        con.read_csv(str(root / config["dataset"])).create_view("datos")
        ids = [fila[0] for fila in con.execute(
            "SELECT numero_de_cliente FROM datos WHERE foto_mes = ?", [mes]
        ).fetchall()]
    resultado = validar_entrega(args.csv, ids, args.columna_id,
                                args.columna_target, args.separador)
    print("Formato y cobertura válidos:", resultado)


if __name__ == "__main__":
    main()
