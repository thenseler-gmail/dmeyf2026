"""Recalcula ganancias y mezclas desde las probabilidades guardadas, sin API."""
import argparse
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('carpeta',type=Path)
    args=parser.parse_args()
    m=json.loads((args.carpeta/'manifest.json').read_text())
    assert m['estado']=='completo' and len(m['features'])==203
    r=pd.read_csv(args.carpeta/'comparacion.csv')
    comprobaciones=0
    for etapa,mes,n in [('mayo',202105,163768),('junio',202106,164114)]:
        df=pd.read_csv(args.carpeta/f'predicciones_{etapa}.csv')
        assert len(df)==n and df.foto_mes.eq(mes).all()
        assert not df.duplicated(['numero_de_cliente','foto_mes']).any()
        cols=[c for c in df if c.startswith('p_')]
        assert np.isfinite(df[cols]).all().all() and ((df[cols]>=0)&(df[cols]<=1)).all().all()
        for tb in ['base','nuevo']:
            for lb in ['base','nuevo']:
                assert np.allclose(df[f'p_mezcla_tab_{tb}_lgb_{lb}'],(df[f'p_tabpfn_{tb}']+df[f'p_lgb_{lb}'])/2)
        y=df.clase_ternaria.eq('BAJA+2').to_numpy()
        for fila in r.loc[r.etapa.eq(etapa)].itertuples():
            seleccion=df[fila.modelo].to_numpy()>0.025
            tp=int((y&seleccion).sum()); contactos=int(seleccion.sum())
            gain=tp*1072500-(contactos-tp)*27500
            assert tp==fila.tp and contactos==fila.contactos and contactos-tp==fila.fp
            assert gain==fila.ganancia and gain/4==fila.ganancia_25pct
            comprobaciones+=1
    antes=int(re.search(r'used (\d+)',m['cuota_antes']).group(1))
    despues=int(re.search(r'used (\d+)',m['cuota_despues']).group(1))
    v=dict(estado='verificado',comparaciones=comprobaciones,creditos_cotizados=m['consumo_estimado_total'],creditos_consumidos=despues-antes)
    (args.carpeta/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':
    main()
