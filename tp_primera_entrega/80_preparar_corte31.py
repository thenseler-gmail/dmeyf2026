"""Entrega19 autorizada: mezcla40/40/20 con corte >0.031. Envio manual."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas';BOT=SAL/'01_entregas_bot'
SRC=BOT/'17_EnsembleHist189CatBoost5_20261006_145854'
LOCAL=SAL/'corte_pesos_mix17_20261006_152839'
SEEDS=[541440,408476,741961,248865,717444]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    m=json.loads((SRC/'manifest.json').read_text(encoding='utf-8'))
    audit=json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8'))
    assert m['train_final']==[202104,202105] and m['futuro']==202108 and m['semillas']==SEEDS
    assert m['pesos']==dict(lightgbm=.4,tabpfn=.4,catboost=.2)
    assert audit['estado']=='completo_verificado' and audit['corte_optimo_local']==.031 and audit['pesos_elegidos']==[.4,.4,.2]
    assert json.loads((SRC/'verificacion_independiente.json').read_text())['estado']=='verificado'
    for d,meta in [(SRC,m),(LOCAL,audit)]:
        for f,h in meta['source_hashes'].items():assert sha(ROOT/f)==h
        for f,h in meta['archivos_sha256'].items():assert sha(d/f)==h
    for f in m['archivos']:assert sha(SRC/f['archivo'])==f['sha256']
    p=pd.read_csv(SRC/'predicciones_agosto.csv')
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any() and 'clase_ternaria' not in p
    n=max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    assert n==19
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHist189CatBoostCorte31_%Y%m%d_%H%M%S')
    out=BOT/f'{n}_{name}';out.mkdir();adj=out/'adjuntos_semillas';adj.mkdir();files=[];changes=[]
    for seed in SEEDS:
        q=.4*p[f'p_lgb189_seed{seed}']+.4*p.p_tabpfn+.2*p[f'p_cat202_seed{seed}']
        np.testing.assert_allclose(q,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        chosen=p.loc[q>.031,['numero_de_cliente']].copy();chosen['score']=q[q>.031]
        chosen=chosen.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=adj/f'{name}_semillas_seed{seed}.csv'
        path.write_bytes(''.join(f'{int(v)}\n' for v in chosen.numero_de_cliente).encode('ascii'))
        files.append(dict(seed=seed,archivo=str(path.relative_to(out)),contactos=len(chosen),sha256=sha(path)))
        changes.append(dict(seed=seed,contactos_025=int((q>.025).sum()),contactos_031=int((q>.031).sum()),
            contactos_033=int((q>.033).sum()),retirados_vs025=int(((q>.025)&~(q>.031)).sum())))
    (out/'predicciones_agosto.csv').write_bytes((SRC/'predicciones_agosto.csv').read_bytes())
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    submit=name+'_semillas';(out/'MENSAJE_SEMILLAS.txt').write_text('submit '+submit+'\n',encoding='ascii')
    # Verificar desde disco con producto matricial y scores fuente preservados.
    disk=pd.read_csv(out/'predicciones_agosto.csv');pd.testing.assert_frame_equal(disk,p)
    for f in files:
        seed=f['seed'];q=np.column_stack([disk[f'p_lgb189_seed{seed}'],disk.p_tabpfn,disk[f'p_cat202_seed{seed}']])@np.array([.4,.4,.2])
        np.testing.assert_array_equal(q>.031,disk[f'score_seed{seed}']>.031)
        ids=disk.loc[q>.031,['numero_de_cliente',f'score_seed{seed}']].sort_values([f'score_seed{seed}','numero_de_cliente'],ascending=[False,True])
        path=out/f['archivo'];assert path.read_bytes()==''.join(f'{int(v)}\n' for v in ids.numero_de_cliente).encode('ascii')
        assert len(ids)==ids.numero_de_cliente.nunique()==f['contactos'] and sha(path)==f['sha256']
    meta=dict(estado='completo_verificado_preparado_pendiente',entrega=19,submit=submit,enviado=False,
        train_final=[202104,202105],futuro=202108,semillas=SEEDS,filas_agosto=len(p),
        features_lightgbm=189,features_tabpfn=202,features_catboost=202,
        target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',target_catboost='BAJA+2',
        pesos=m['pesos'],umbral=.031,operador='>',archivos=files,
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [SRC/'manifest.json',SRC/'predicciones_agosto.csv',LOCAL/'manifest.json']},
        archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')},codigo_sha256=sha(Path(__file__)),
        fuente_entrega=str(SRC.relative_to(ROOT)),fuente_validacion=str(LOCAL.relative_to(ROOT)),
        api=False,creditos=0,nuevos_fits=0,submits=0,validacion_aparente_total=276078000,
        validacion_aparente_25pct=69019500,limitaciones=audit['limitacion'])
    save(out/'manifest.json',meta)
    save(out/'verificacion_independiente.json',dict(estado='verificado',adjuntos_verificados=5,
        seleccion_producto_matricial=True,predicciones_identicas_entrega17=True,fuentes_preservadas=True,
        corte=.031,pesos=m['pesos'],api=False,enviado=False))
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO, PENDIENTE ENVIO MANUAL.\nAdjuntar cinco CSV de adjuntos_semillas. Sin resultado publico.\n',encoding='utf-8')
    report=['# Entrega19: 40/40/20 con corte 3,1%','',
        '**Preparada y verificada para envío manual.** Adjuntar solo los cinco CSV de adjuntos_semillas.','',
        '```text','submit '+submit,'```','',
        'LightGBM189 combinado + TabPFN202 BAJA+2 + CatBoost202 BAJA+2. Pesos40/40/20, score estrictamente >0,031. '
        'Mismas probabilidades finales abril+mayo → agosto y cinco semillas de17; solo cambia la selección de contactos.','',
        'Ganancia local aparente abril → mayo: **$276.078.000 total; 25% $69.019.500**. '
        'Frente a2,5%: +$6.264.500 total; 25% +$1.566.125. '
        'Frente a3,3%: +$2.887.500 total; 25% +$721.875.','',
        'Máximo de grilla1%–8% en pasos0,1 puntos; pesos40/40/20 ganaron21 proporciones con corte3,1% fijo. '
        'La selección cruzada usa cuatro cortes/pesos propios, no mide este3,1% fijo fuera de muestra. '
        'Mayo y semillas reutilizados: resultado retrospectivo optimista; no garantiza mejora en agosto.','',
        '| Semilla | Contactos agosto |','| --- | ---: |']
    report += [f'| {f["seed"]} | {f["contactos"]} |' for f in files]
    report+=['','Cero fits/API/créditos/envíos.17 y18 intactas. Mejor público sigue16$96.921.000.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    c['busqueda_corte_pesos_mix17'].update(entrega_seleccionada=19,carpeta_entrega=str(out.relative_to(ROOT)),submit=submit,enviado=False)
    save(cfg,c)
    note=f'Entrega19 elegida por el usuario:40/40/20,corte3,1%,cincoCSV verificados. Carpeta {out.relative_to(ROOT)}; mensaje submit {submit}. Pendiente envío manual;17/18 preservadas, sin fits/API/créditos.'
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## 106. Entrega19 corte3,1% preparada - 2026-10-06\n\n'+note+'\n')
    nxt=TP/'NEXT_STEPS_IDEAS.md';s=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(s.replace(marker,marker+'\n**Entrega19 preparada y seleccionada:** '+note+'\n',1),encoding='utf-8')
    print('Salida:',out);print('submit '+submit);print('Contactos:',[f['contactos'] for f in files])

if __name__=='__main__':main()
