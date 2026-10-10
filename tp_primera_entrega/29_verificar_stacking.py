"""Verifica resultados del stacking desde CSV y auditorias, sin API."""
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
    assert m['features'][-1]=='p_lightgbm_oof'
    pre=Path(m['fuente_preparacion'])
    prep=json.loads((pre/'manifest.json').read_text())
    tabla=pd.read_csv(args.carpeta/'comparacion.csv')
    comprobaciones=0
    for etapa,mes,filas in [('mayo',202105,163768),('junio',202106,164114)]:
        df=pd.read_csv(args.carpeta/f'predicciones_{etapa}.csv')
        assert len(df)==filas and df.foto_mes.eq(mes).all()
        assert not df.duplicated(['numero_de_cliente','foto_mes']).any()
        cols=[c for c in df if c.startswith('p_')]
        assert np.isfinite(df[cols]).all().all() and ((df[cols]>=0)&(df[cols]<=1)).all().all()
        assert np.allclose(df.p_mix_3semillas,(df.p_lightgbm_oof+df.p_tabpfn_control)/2)
        assert np.allclose(df.p_mix_referencia,(df.p_lightgbm_control+df.p_tabpfn_control)/2)
        y=df.clase_ternaria.eq('BAJA+2').to_numpy()
        for fila in tabla.loc[tabla.etapa.eq(etapa)].itertuples():
            seleccionado=df[fila.modelo].to_numpy()>0.025
            contactos=int(seleccionado.sum()); tp=int((y&seleccionado).sum())
            g=tp*1072500-(contactos-tp)*27500
            assert contactos==fila.contactos and tp==fila.tp and contactos-tp==fila.fp
            assert g==fila.ganancia and g/4==fila.ganancia_25pct
            comprobaciones+=1
        oof=pd.read_csv(pre/f'oof_{etapa}.csv')
        assert len(oof)==prep['etapas'][etapa]['filas_train']
        assert oof.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
        assert np.allclose(oof.filter(like='p_oof_seed').mean(axis=1),oof.p_lightgbm_oof)
        assert all(f['max_mes_fit']<=f['mes_predicho'] and f['clientes_solapados']==0 for f in prep['etapas'][etapa]['folds'])
    antes=int(re.search(r'used (\d+)',m['cuota_antes']).group(1))
    despues=int(re.search(r'used (\d+)',m['cuota_despues']).group(1))
    v=dict(estado='verificado',comparaciones=comprobaciones,creditos_consumidos=despues-antes,creditos_cotizados=m['consumo_estimado_total'],oof_y_mezclas_verificados=True)
    (args.carpeta/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':
    main()
