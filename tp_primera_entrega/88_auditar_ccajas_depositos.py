"""Verifica la corrección de mayo sin consultar etiquetas ni alterar el CSV."""
from datetime import datetime
from pathlib import Path
import json
import duckdb
import pandas as pd
from calidad_datos import corregir_datos, preparar_corregido


def main():
    proyecto = Path(__file__).resolve().parent
    config = json.loads((proyecto / 'config.json').read_text(encoding='utf-8'))
    fuente = proyecto.parent / config['dataset']
    antes = (fuente.stat().st_size, fuente.stat().st_mtime_ns)
    with duckdb.connect() as con:
        con.read_csv(str(fuente)).create_view('datos')
        original = con.execute('SELECT numero_de_cliente, foto_mes, ccajas_depositos '
                               'FROM datos ORDER BY foto_mes, numero_de_cliente').df()
    corregido, auditoria = corregir_datos(original)
    mayo = original.foto_mes.eq(202105)
    assert mayo.any()
    assert original.loc[mayo, 'ccajas_depositos'].eq(0).all(), 'Revisar diagnóstico de mayo'
    assert corregido.loc[mayo, 'ccajas_depositos'].isna().all()
    pd.testing.assert_frame_equal(original.loc[~mayo], corregido.loc[~mayo], check_dtype=False)
    pd.testing.assert_frame_equal(original[['numero_de_cliente', 'foto_mes']],
                                  corregido[['numero_de_cliente', 'foto_mes']])
    matriz, _ = preparar_corregido(original, ['ccajas_depositos'])
    assert matriz.loc[mayo, 'ccajas_depositos'].isna().all()
    segunda, _ = corregir_datos(corregido)
    pd.testing.assert_frame_equal(corregido, segunda)
    assert antes == (fuente.stat().st_size, fuente.stat().st_mtime_ns)
    resumen = []
    for mes, datos in original.groupby('foto_mes'):
        valores = datos.ccajas_depositos
        resumen.append({'mes': int(mes), 'filas': len(datos),
                        'ceros_originales': int(valores.eq(0).sum()),
                        'nulos_originales': int(valores.isna().sum()),
                        'nulos_corregidos': int(corregido.loc[datos.index, 'ccajas_depositos'].isna().sum())})
    salida = proyecto / 'salidas' / ('correccion_ccajas_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    salida.mkdir()
    pd.DataFrame(resumen).to_csv(salida / 'auditoria_meses.csv', index=False)
    (salida / 'verificacion.json').write_text(json.dumps({'estado': 'verificado',
        'fuente': str(fuente), 'regla': 'ccajas_depositos = NA solamente en foto_mes 202105',
        'auditoria': auditoria, 'meses': resumen,
        'checks': ['mayo originalmente todo cero', 'mayo corregido todo NA',
                   'otros meses idénticos', 'claves y orden idénticos', 'regla idempotente',
                   'wrapper de preparación verificado', 'CSV fuente sin modificación']},
        indent=2, ensure_ascii=False), encoding='utf-8')
    (salida / 'INFORME.md').write_text(
        '# Corrección de ccajas_depositos\n\n'
        f'Confirmado: las {int(mayo.sum()):,} filas de mayo de 2021 tienen cero. '
        'La regla convierte todos esos valores a NA. Los otros meses y las claves permanecen iguales.\n\n'
        'Aplicar `calidad_datos.corregir_datos` antes de generar históricos y '
        '`calidad_datos.preparar_corregido` al preparar nuevas matrices. '
        'No modifica el CSV fuente ni los scripts y entregas históricas. '
        'No se entrenaron modelos: el impacto sobre la ganancia aún no se midió.\n', encoding='utf-8')
    print(json.dumps({'salida': str(salida), 'auditoria': auditoria, 'meses': resumen}, ensure_ascii=False))


if __name__ == '__main__':
    main()
