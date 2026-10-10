"""Verifica las ganancias de una revision desde sus CSV de probabilidades."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from importlib import import_module


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('revision',type=Path)
    args=parser.parse_args()
    args.revision=args.revision.resolve()
    metricas=import_module('17_revisar_umbral').metricas
    revision=json.loads((args.revision/'manifest.json').read_text())
    assert revision['estado']=='completo'
    detalles=pd.read_csv(args.revision/'seleccion_mayo_semillas.csv')
    for nombre,filas in detalles.groupby('candidato'):
        df=pd.read_csv(args.revision/(nombre+'_mayo.csv'))
        assert len(df)==163768 and not df.duplicated(['numero_de_cliente','foto_mes']).any()
        for fila in filas.itertuples():
            m=metricas(df,df[f'p_seed{fila.seed}'])
            assert m['ganancia']==fila.ganancia and m['contactos']==fila.contactos
    sal=args.revision.parent
    junio=[]
    for carpeta in sal.glob('ensemble_junio_*'):
        m=json.loads((carpeta/'manifest.json').read_text())
        if Path(m['fuente_lightgbm']).parent!=args.revision:
            continue
        df=pd.read_csv(carpeta/'predicciones_junio.csv')
        assert len(df)==164114 and not df.duplicated(['numero_de_cliente','foto_mes']).any()
        columnas=[c for c in df if c.startswith('p_seed')]
        assert len(columnas)==20
        assert np.isfinite(df[columnas]).all().all()
        assert ((df[columnas]>=0)&(df[columnas]<=1)).all().all()
        assert np.allclose(df[columnas].mean(axis=1),df.p_lightgbm)
        assert np.allclose((df.p_lightgbm+df.p_tabpfn)/2,df.mezcla_probabilidades)
        for fila in pd.read_csv(carpeta/'comparacion.csv').itertuples():
            col='p_tabpfn' if fila.modelo=='tabpfn_umbral_0.025' else fila.modelo
            v=metricas(df,df[col])
            assert v['ganancia']==fila.ganancia and v['contactos']==fila.contactos
            junio.append(dict(target=m['elegido']['target'],modelo=fila.modelo,**v))
    assert len(junio)==8
    pd.DataFrame(junio).to_csv(args.revision/'comparacion_junio_final.csv',index=False)
    (args.revision/'verificacion.json').write_text(json.dumps(dict(estado='verificado',candidatos_mayo=detalles.candidato.nunique(),evaluaciones_semillas_mayo=len(detalles),resultados_junio=len(junio)),indent=2))
    print(pd.DataFrame(junio).to_string(index=False))


if __name__=='__main__':
    main()
