"""Nueva entrega18: mismos scores finales17, corte fijo >0.033. Sin API/fits/envios."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];TP=ROOT/'tp_primera_entrega';SAL=TP/'salidas';BOT=SAL/'01_entregas_bot'
SRC=BOT/'17_EnsembleHist189CatBoost5_20261006_145854'
LOCAL=SAL/'corte33_mix17_20261006_152412'
KEYS=['numero_de_cliente','foto_mes']
SEEDS=[541440,408476,741961,248865,717444]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    m=json.loads((SRC/'manifest.json').read_text(encoding='utf-8'))
    local=json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8'))
    assert m['entrega']==17 and m['semillas']==SEEDS and m['train_final']==[202104,202105] and m['futuro']==202108
    assert m['pesos']==dict(lightgbm=.4,tabpfn=.4,catboost=.2) and m['umbral']==.025 and m['operador']=='>'
    assert local['estado']=='completo_verificado' and local['mejora_vs17']
    assert json.loads((SRC/'verificacion_independiente.json').read_text())['estado']=='verificado'
    for d,meta in [(SRC,m),(LOCAL,local)]:
        for f,h in meta['source_hashes'].items():assert sha(ROOT/f)==h
        for f,h in meta['archivos_sha256'].items():assert sha(d/f)==h
    for f in m['archivos']:assert sha(SRC/f['archivo'])==f['sha256']
    p=pd.read_csv(SRC/'predicciones_agosto.csv')
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any() and 'clase_ternaria' not in p
    n=max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    assert n==18
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHist189CatBoostCorte33_%Y%m%d_%H%M%S')
    out=BOT/f'{n}_{name}';out.mkdir();adj=out/'adjuntos_semillas';adj.mkdir();files=[];changes=[]
    for seed in SEEDS:
        q=.4*p[f'p_lgb189_seed{seed}']+.4*p.p_tabpfn+.2*p[f'p_cat202_seed{seed}']
        np.testing.assert_allclose(q,p[f'score_seed{seed}'],rtol=0,atol=1e-15)
        selected=p.loc[q>.033,KEYS].copy();selected['score']=q[q>.033]
        selected=selected.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=adj/f'{name}_semillas_seed{seed}.csv';path.write_bytes(''.join(f'{int(v)}\n' for v in selected.numero_de_cliente).encode('ascii'))
        files.append(dict(seed=seed,archivo=str(path.relative_to(out)),contactos=len(selected),sha256=sha(path)))
        changes.append(dict(seed=seed,contactos17=int((q>.025).sum()),contactos18=int((q>.033).sum()),retirados=int(((q>.025)&~(q>.033)).sum())))
    # Copia exacta de probabilidades ya auditadas: solo cambian las listas.
    (out/'predicciones_agosto.csv').write_bytes((SRC/'predicciones_agosto.csv').read_bytes())
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    submit=name+'_semillas';(out/'MENSAJE_SEMILLAS.txt').write_text('submit '+submit+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVIO MANUAL.\nAdjuntar los cinco CSV de adjuntos_semillas.\nSin resultado publico informado.\n',encoding='utf-8')
    # Auditoria con scores por producto matricial y archivos leidos desde disco.
    disk=pd.read_csv(out/'predicciones_agosto.csv');pd.testing.assert_frame_equal(p,disk)
    for f in files:
        seed=f['seed'];q=np.column_stack([disk[f'p_lgb189_seed{seed}'],disk.p_tabpfn,disk[f'p_cat202_seed{seed}']])@np.array([.4,.4,.2])
        ids=disk.loc[q>.033,KEYS].copy();ids['score']=q[q>.033]
        # Orden se basa en los scores conservados de17 para mantener el desempate reproducible.
        np.testing.assert_array_equal(q>.033,disk[f'score_seed{seed}']>.033)
        ids['score']=disk.loc[q>.033,f'score_seed{seed}'].to_numpy()
        ids=ids.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        path=out/f['archivo'];assert path.read_bytes()==''.join(f'{int(v)}\n' for v in ids.numero_de_cliente).encode('ascii')
        assert len(ids)==ids.numero_de_cliente.nunique()==f['contactos'] and sha(path)==f['sha256']
    meta=dict(estado='completo_verificado_preparado_pendiente',entrega=18,enviado=False,submit=submit,
        train_final=[202104,202105],futuro=202108,semillas=SEEDS,features_lightgbm=189,features_tabpfn=202,features_catboost=202,
        target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',target_catboost='BAJA+2',pesos=m['pesos'],umbral=.033,operador='>',
        fuente_entrega=str(SRC.relative_to(ROOT)),fuente_local=str(LOCAL.relative_to(ROOT)),archivos=files,
        archivos_sha256={f.name:sha(f) for f in out.glob('*.csv')},
        source_hashes={str(f.relative_to(ROOT)):sha(f) for f in [SRC/'manifest.json',SRC/'predicciones_agosto.csv',LOCAL/'manifest.json']},
        codigo_sha256=sha(Path(__file__)),api=False,creditos=0,nuevos_fits=0,submits=0,
        validacion_local=local['comparacion'],semillas_mejoran=4,partes_mejoran=2,
        limitaciones=local['limitaciones'],referencia_publica=dict(entrega=16,media_pesos=96921000))
    save(out/'manifest.json',meta)
    save(out/'verificacion_independiente.json',dict(estado='verificado',adjuntos_verificados=5,
        scores_selecciones_producto_matricial=True,predicciones_identicas_entrega17=True,fuentes_preservadas=True,api=False,enviado=False))
    report=['# Entrega18: mezcla17 con corte 3,3%','',
        '**Preparada y verificada, pendiente de envío manual.** Adjuntar los cinco CSV de adjuntos_semillas.','',
        '```text','submit '+submit,'```','',
        'LightGBM189 combinado + TabPFN202 BAJA+2 + CatBoost202 BAJA+2; pesos40/40/20; mismas cinco semillas. '
        'Probabilidades finales abril+mayo → agosto idénticas a17. Solo cambia el corte estricto: >0,033.','',
        '| Validación abril → mayo | Ganancia total media5 | 25% |','| --- | ---: | ---: |',
        '| Corte2,5% | $269.813.500 | $67.453.375 |','| Corte3,3% | $273.190.500 | $68.297.625 |',
        '| Diferencia | $3.377.000 | $844.250 |','',
        'Mejora4/5 semillas y2/4 partes de mayo. No demuestra que3,3% sea el óptimo; compara dos cortes solicitados. '
        'Mayo y semillas reutilizados, sin test independiente ni garantía pública. La entrega11 anterior con3,3% perdió en el Bot, '
        'pero tenía otra mezcla. No se usa ese resultado para optimizar esta lista.','',
        '| Semilla | Contactos agosto |','| --- | ---: |']
    report += [f'| {f["seed"]} | {f["contactos"]} |' for f in files]
    report+=['','Cero fits/API/créditos/envíos. Entrega17 intacta. Mejor público sigue16: $96.921.000, ya del25%.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cfg=TP/'config_validacion_lightgbm.json';c=json.loads(cfg.read_text(encoding='utf-8'))
    c['corte33_mix17_local'].update(entrega_preparada=18,carpeta_entrega=str(out.relative_to(ROOT)),submit=submit,enviado=False)
    save(cfg,c)
    note=f'Entrega18 corte3,3% preparada/verificada desde17, mismos modelos, cinco CSV. Carpeta {out.relative_to(ROOT)}. Mensaje submit {submit}. Cero fits/API/créditos/envíos;17 preservada.'
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n## 104. Entrega18 mezcla17 corte3,3% preparada - 2026-10-06\n\n'+note+'\n')
    nxt=TP/'NEXT_STEPS_IDEAS.md';text=nxt.read_text(encoding='utf-8');marker='## Plan consolidado vigente — 2026-10-06\n'
    nxt.write_text(text.replace(marker,marker+'\n**Entrega18 lista para envío manual:** '+note+'\n',1),encoding='utf-8')
    print('Salida:',out);print('submit '+submit);print('Contactos:',[f['contactos'] for f in files])

if __name__=='__main__':main()
