"""Verificacion independiente desde probabilidades exportadas."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('carpeta',type=Path)
    args=parser.parse_args()
    m=json.loads((args.carpeta/'manifest.json').read_text())
    assert m['estado']=='completo'
    tabla=pd.read_csv(args.carpeta/'comparacion.csv')
    comprobaciones=0
    for etapa in tabla.etapa.unique():
        d=pd.read_csv(args.carpeta/f'predicciones_{etapa}.csv')
        esperado=163768 if etapa=='mayo' else 164114
        assert len(d)==esperado and not d.duplicated(['numero_de_cliente','foto_mes']).any()
        columnas=[c for c in d if c.startswith('p_nuevo_seed')]
        base=[c for c in d if c.startswith('p_base_seed')]
        assert len(columnas)==len(base)==(3 if etapa=='mayo' else 20)
        assert np.isfinite(d[columnas+base]).all().all()
        assert ((d[columnas+base]>=0)&(d[columnas+base]<=1)).all().all()
        assert np.allclose(d[columnas].mean(axis=1),d.p_nuevo)
        assert np.allclose(d[base].mean(axis=1),d.p_base)
        assert np.allclose((d.p_nuevo+d.p_historicas)/2,d.p_mezcla_nueva)
        assert np.allclose((d.p_base+d.p_historicas)/2,d.p_mezcla_base)
        cols={'TabPFN':'p_historicas','LightGBM base promedio':'p_base','LightGBM nuevo promedio':'p_nuevo','50/50 base':'p_mezcla_base','50/50 nuevo':'p_mezcla_nueva'}
        y=d.clase_ternaria.eq('BAJA+2').to_numpy()
        for fila in tabla.loc[tabla.etapa.eq(etapa)].itertuples():
            c=f'p_nuevo_seed{int(fila.seed)}' if fila.modelo=='LightGBM nuevo individual' else cols[fila.modelo]
            s=d[c].to_numpy()>0.025
            tp=int((s&y).sum()); n=int(s.sum()); g=tp*1072500-(n-tp)*27500
            assert n==fila.contactos and tp==fila.tp and n-tp==fila.fp
            assert g==fila.ganancia and g/4==fila.ganancia_25pct
            comprobaciones+=1
    v=dict(estado='verificado',evaluaciones=comprobaciones,features_nuevas=m['features_nuevas'],control_reproducido=m['control_base_reproducido'])
    (args.carpeta/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':
    main()
