"""Audita entrega17 desde probabilidades fuente; sin entrenamiento ni API."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
KEYS=['numero_de_cliente','foto_mes']
SEEDS=[541440,408476,741961,248865,717444]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['entrega']==17 and m['semillas']==SEEDS and m['train_final']==[202104,202105] and m['futuro']==202108
    assert m['pesos']==dict(lightgbm=.4,tabpfn=.4,catboost=.2) and m['umbral']==.025 and m['operador']=='>'
    assert m['features_lightgbm']==189 and m['features_catboost']==m['features_tabpfn']==202
    assert m['target_lightgbm']=='BAJA+1/BAJA+2' and m['target_catboost']==m['target_tabpfn']=='BAJA+2'
    assert m['nuevos_fits']==m['creditos']==m['submits']==0 and not m['api'] and not m['enviado']
    assert not m['nuevas_lecturas_dataset'] and not m['junio_validacion'] and not m['etiquetas_agosto']
    assert sha(Path(__file__).parent/'70_preparar_mix_hist189_bot.py')==m['codigo_sha256']
    for f,h in m['source_hashes'].items():assert sha(ROOT/f)==h
    for f,h in m['archivos_sha256'].items():assert sha(out/f)==h
    ld=ROOT/m['fuente_lightgbm'];cd=ROOT/m['fuente_catboost'];local=ROOT/m['fuente_validacion']
    lm=json.loads((ld/'manifest.json').read_text(encoding='utf-8'))
    cm=json.loads((cd/'manifest.json').read_text(encoding='utf-8'))
    for d,meta,models in [(ld,lm,'modelos'),(cd,cm,'modelos_catboost')]:
        assert meta['train_final']==[202104,202105] and meta['futuro']==202108 and meta['firma']['seeds']==SEEDS
        assert json.loads((d/'verificacion_independiente.json').read_text())['estado']=='verificado'
        for f,h in meta['modelos_sha256'].items():assert sha(d/models/f)==h
        for f,h in meta['archivos_sha256'].items():assert sha(d/f)==h
        for entry in meta['archivos']:assert sha(d/entry['archivo'])==entry['sha256']
    assert len(lm['firma']['features'])==189 and len(cm['firma']['features'])==202
    a=pd.read_csv(ld/'predicciones_agosto.csv');b=pd.read_csv(cd/'predicciones_agosto.csv')
    p=pd.read_csv(out/'predicciones_agosto.csv')
    pd.testing.assert_frame_equal(a[KEYS],b[KEYS]);pd.testing.assert_frame_equal(a[KEYS],p[KEYS])
    assert len(p)==m['filas_agosto']==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any()
    assert all('clase_ternaria' not in frame for frame in [a,b,p])
    np.testing.assert_allclose(a.p_tabpfn,b.p_tabpfn,rtol=0,atol=1e-15)
    np.testing.assert_allclose(p.p_tabpfn,a.p_tabpfn,rtol=0,atol=1e-15)
    assert len(m['archivos'])==len(list((out/'adjuntos_semillas').glob('*.csv')))==5
    assert {str(f.relative_to(out)) for f in (out/'adjuntos_semillas').glob('*.csv')}=={f['archivo'] for f in m['archivos']}
    changes=pd.read_csv(out/'cambios_contactos_agosto.csv').set_index('seed')
    for seed in SEEDS:
        np.testing.assert_allclose(p[f'p_lgb189_seed{seed}'],a[f'p_lgb_seed{seed}'],rtol=0,atol=1e-15)
        np.testing.assert_allclose(p[f'p_cat202_seed{seed}'],b[f'p_cat_seed{seed}'],rtol=0,atol=1e-15)
        # Producto matricial independiente del calculo componente a componente.
        q=np.column_stack([a[f'p_lgb_seed{seed}'],a.p_tabpfn,b[f'p_cat_seed{seed}']])@np.array([.4,.4,.2])
        np.testing.assert_allclose(q,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(q>.025,p[f'score_seed{seed}']>.025)
        selected=p.loc[q>.025,KEYS].copy();selected['score']=q[q>.025]
        selected=selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        f=next(e for e in m['archivos'] if e['seed']==seed);path=out/f['archivo']
        assert path.name==f"{m['submit']}_seed{seed}.csv" and sha(path)==f['sha256']
        assert path.read_bytes()==''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii')
        assert f['contactos']==len(selected)==selected.numero_de_cliente.nunique()
        old=(a[f'p_lgb_seed{seed}']+a.p_tabpfn).to_numpy()/2>.025;new=q>.025;r=changes.loc[seed]
        assert r.contactos_entrega16==old.sum() and r.contactos_mix==new.sum()
        assert r.agregados==(new&~old).sum() and r.retirados==(old&~new).sum()
    vals=p.drop(columns=KEYS).to_numpy();assert np.isfinite(vals).all() and ((vals>=0)&(vals<=1)).all()
    metrics=pd.read_csv(local/'comparacion_media5.csv').set_index('variante')
    assert metrics.loc['control_16_LGB189_Tab202_50_50','ganancia']==m['validacion_local']['control16_total']==266420000
    mix=metrics.loc['mix_LGB189_Tab202_Cat202_40_40_20']
    assert mix.ganancia==m['validacion_local']['mix_total']==269813500 and mix.ganancia>266420000
    assert mix.ganancia_25pct==m['validacion_local']['mix_25pct']==67453375
    assert mix.semillas_mejoran==4 and mix.partes_mejoran==3
    assert json.loads((local/'verificacion_independiente.json').read_text())['estado']=='verificado'
    assert (out/'MENSAJE_SEMILLAS.txt').read_text().strip()=='submit '+m['submit']
    verification=dict(estado='verificado',predicciones_fuente_y_claves_verificadas=True,adjuntos_verificados=5,
        score_y_seleccion_por_producto_matricial=True,filas_agosto=164647,control16_local_superado=True,
        fuentes15_16_preservadas=True,fit_final_fuentes=[202104,202105],api=False,creditos=0,nuevos_fits=0,
        enviado=False,codigo_verificador_sha256=sha(Path(__file__)))
    (out/'verificacion_independiente.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    m['estado']='completo_verificado_preparado_pendiente'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(verification,indent=2),flush=True)


if __name__=='__main__':main()
