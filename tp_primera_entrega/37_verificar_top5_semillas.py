"""Reconstruye ranking20 y verifica los5 CSV exportados, sin entrenar."""
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
    m=json.loads((out/'manifest.json').read_text())
    assert m['estado']=='completo' and m['umbral']==.025 and m['operador']=='>'
    for file,h in m['archivos_sha256'].items():
        assert hashlib.sha256((out/file).read_bytes()).hexdigest()==h
    semillas=m['firma']['semillas']; assert len(semillas)==len(set(semillas))==20
    grupos=pd.read_csv(out/'asignacion_folds.csv')
    assert grupos.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
    assert set(grupos.foto_mes)=={202103,202104,202105}
    for a in m['auditoria_folds']:
        tr=grupos[grupos.foto_mes.le(a['mes'])&grupos.fold_cliente.ne(a['fold'])]
        va=grupos[grupos.foto_mes.eq(a['mes'])&grupos.fold_cliente.eq(a['fold'])]
        assert len(tr)==a['filas_fit'] and len(va)==a['filas_eval']
        assert tr.foto_mes.max()==a['max_mes_fit']<=a['mes']
        assert set(tr.numero_de_cliente).isdisjoint(set(va.numero_de_cliente))
    assert len(m['auditoria_folds'])==160 and m['entrenamientos_nuevos']==136
    resultados=pd.read_csv(out/'resultados_por_mes.csv')
    assert len(resultados)==40 and not resultados.duplicated(['seed','mes']).any()
    for mes in [202104,202105]:
        df=pd.read_csv(out/f'oof_{mes}.csv')
        ref=grupos[grupos.foto_mes.eq(mes)].reset_index(drop=True)
        pd.testing.assert_frame_equal(df[['numero_de_cliente','foto_mes','clase_ternaria','fold_cliente']],ref)
        cols=[f'p_seed{s}' for s in semillas]
        assert np.isfinite(df[cols]).all().all() and ((df[cols]>=0)&(df[cols]<=1)).all().all()
        for r in resultados[resultados.mes.eq(mes)].itertuples():
            s=df[f'p_seed{r.seed}'].gt(.025); y=df.clase_ternaria.eq('BAJA+2')
            tp=int((s&y).sum()); fp=int((s&~y).sum()); gain=tp*1072500-fp*27500
            assert (len(df),int(s.sum()),tp,fp,gain,gain/4)==(r.filas,r.contactos,r.tp,r.fp,r.ganancia,r.ganancia_25pct)
    previo=pd.read_csv(Path(m['fuente'])/'resultados_semillas.csv')
    previo=previo[previo.variante.eq('haberes')&previo.target.eq('baja2')&previo.etapa.eq('cv_cliente')]
    for r in previo.itertuples():
        q=resultados[resultados.seed.eq(r.seed)&resultados.mes.eq(r.mes)].iloc[0]
        assert q.ganancia==r.ganancia and q.contactos==r.contactos
    ranking=pd.read_csv(out/'ranking_semillas.csv')
    recomputado=resultados.pivot(index='seed',columns='mes',values='ganancia').rename(columns={202104:'ganancia_abril',202105:'ganancia_mayo'})
    recomputado['ganancia_media']=recomputado.mean(axis=1)
    for c in ['ganancia_abril','ganancia_mayo','ganancia_media']:
        recomputado[c+'_25pct']=recomputado[c]/4
    recomputado=recomputado.reset_index().sort_values(['ganancia_media','ganancia_mayo','seed'],ascending=[False,False,True]).reset_index(drop=True)
    recomputado.insert(0,'puesto',np.arange(1,21)); recomputado.columns.name=None
    pd.testing.assert_frame_equal(ranking,recomputado,check_dtype=False)
    assert ranking.head(5).seed.tolist()==m['semillas_elegidas']
    candidato=Path(m['candidato']); tm=json.loads((candidato/'manifest_top5.json').read_text())
    assert tm['semillas']==m['semillas_elegidas'] and len(tm['archivos'])==5
    final=candidato/'predicciones_agosto.csv'
    assert hashlib.sha256(final.read_bytes()).hexdigest()==tm['fuente_probabilidades_sha256']
    agosto=pd.read_csv(final)
    assert len(agosto)==164647 and agosto.foto_mes.eq(202108).all() and not agosto.numero_de_cliente.duplicated().any()
    for a in tm['archivos']:
        f=candidato/'adjuntos_top5'/a['archivo']
        assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']
        lines=f.read_text(encoding='ascii').splitlines()
        assert all(s.isdigit() for s in lines)
        ids=list(map(int,lines))
        assert len(ids)==len(set(ids))==a['contactos']
        assert set(ids)==set(agosto.loc[agosto[f'p_seed{a["seed"]}']>.025,'numero_de_cliente'])
    assert len(list((candidato/'adjuntos_top5').glob('*.csv')))==5
    assert (candidato/'MENSAJE_TOP5.txt').read_text()=='submit '+tm['submit']
    v=dict(estado='verificado',semillas_evaluadas=20,resultados_reconstruidos=40,folds_auditados=160,
        ranking_media_abril_mayo=True,archivos_exportados=5,semillas_elegidas=m['semillas_elegidas'],
        origen_agosto='predicciones ya guardadas, sin etiquetas',api=False,creditos=0)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    (candidato/'verificacion_top5.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(v)


if __name__=='__main__':
    main()
