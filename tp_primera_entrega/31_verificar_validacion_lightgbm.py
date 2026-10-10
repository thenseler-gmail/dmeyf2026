"""Audita particiones y resultados del piloto30; local, sin entrenamiento."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta',type=Path)
    out=parser.parse_args().carpeta
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo' and m['umbral']==0.025 and m['operador']=='>'
    assert len(m['features'])==202
    assert not set(['numero_de_cliente','foto_mes','clase_ternaria'])&set(m['features'])
    for name,h in m['archivos_sha256'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h,name
    grupos=pd.read_csv(out/'asignacion_folds.csv')
    assert not grupos.duplicated(['numero_de_cliente','foto_mes']).any()
    assert set(grupos.foto_mes)=={202103,202104,202105}
    assert grupos.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
    assert set(grupos.fold_cliente)=={0,1,2,3}
    assert len(grupos)==m['filas'] and grupos.numero_de_cliente.nunique()==m['clientes']
    for a in m['auditoria_folds']:
        tr=grupos[grupos.foto_mes.le(a['mes_eval']) & grupos.fold_cliente.ne(a['fold'])]
        va=grupos[grupos.foto_mes.eq(a['mes_eval']) & grupos.fold_cliente.eq(a['fold'])]
        assert len(tr)==a['filas_train'] and len(va)==a['filas_eval']
        assert tr.foto_mes.max()==a['max_mes_train']<=a['mes_eval']
        assert set(tr.numero_de_cliente).isdisjoint(set(va.numero_de_cliente))
    comparacion=pd.read_csv(out/'comparacion.csv')
    detalles=pd.read_csv(out/'detalle_folds.csv')
    assert len(comparacion)==8 and len(detalles)==16
    for r in comparacion.itertuples():
        name=f'cv_{r.target}_{r.mes}.csv' if r.etapa=='cv_cliente' else f'{r.etapa}_{r.target}.csv'
        df=pd.read_csv(out/name)
        referencia=grupos[grupos.foto_mes.eq(r.mes)].reset_index(drop=True)
        pd.testing.assert_frame_equal(df[['numero_de_cliente','foto_mes','clase_ternaria']].reset_index(drop=True),referencia[['numero_de_cliente','foto_mes','clase_ternaria']])
        seeds=[f'p_seed{s}' for s in m['semillas']]
        assert np.isfinite(df[seeds+['probabilidad']]).all().all()
        assert ((df[seeds+['probabilidad']]>=0)&(df[seeds+['probabilidad']]<=1)).all().all()
        assert np.allclose(df[seeds].mean(axis=1),df.probabilidad)
        s=df.probabilidad.gt(.025); y=df.clase_ternaria.eq('BAJA+2')
        tp=int((s&y).sum()); fp=int((s&~y).sum())
        g=tp*1072500-fp*27500
        assert (len(df),int(s.sum()),tp,fp,g,g/4)==(r.filas,r.contactos,r.tp,r.fp,r.ganancia,r.ganancia_25pct)
        if r.etapa=='cv_cliente':
            assert df.fold_cliente.equals(referencia.fold_cliente)
            for f in detalles[detalles.target.eq(r.target)&detalles.mes.eq(r.mes)].itertuples():
                ix=df.fold_cliente.eq(f.fold)
                foldgain=int((s&y&ix).sum())*1072500-int((s&~y&ix).sum())*27500
                fraction=ix.sum()/len(df)
                assert foldgain==f.ganancia and ix.sum()==f.filas
                assert np.isclose(fraction,f.fraccion_evaluada)
                assert np.isclose(foldgain/fraction,f.ganancia_equivalente_mes)
                assert np.isclose(foldgain/fraction/4,f.ganancia_equivalente_mes_25pct)
    ver=dict(estado='verificado',comparaciones=8,folds_auditados=len(m['auditoria_folds']),
        clientes_disjuntos=True,fit_sin_meses_posteriores=True,ganancias_reconstruidas=True,
        api=False,creditos=0,piloto_semillas=len(m['semillas']),test_independiente=False)
    (out/'verificacion.json').write_text(json.dumps(ver,indent=2),encoding='utf-8')
    print(ver)


if __name__=='__main__':
    main()
