"""Entrega17: LGB189/Tab202/Cat202 40/40/20 desde fuentes finales15/16."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas';BOT=SAL/'01_entregas_bot'
LOCAL=SAL/'mix_hist189_catboost_20261006_145401'
LGB=BOT/'16_EnsembleHist1895_20261006_143235'
CAT=BOT/'15_EnsembleCatBoost5_20261006_085026'
KEYS=['numero_de_cliente','foto_mes'];SEEDS=[541440,408476,741961,248865,717444]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def source(path):
    m=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    assert m['train_final']==[202104,202105] and m['futuro']==202108
    assert m['firma']['seeds']==SEEDS and m['umbral']==.025 and m['operador']=='>'
    assert json.loads((path/'verificacion_independiente.json').read_text())['estado']=='verificado'
    for name,h in m['archivos_sha256'].items():assert sha(path/name)==h
    modeldir='modelos' if path==LGB else 'modelos_catboost'
    for name,h in m['modelos_sha256'].items():assert sha(path/modeldir/name)==h
    p=pd.read_csv(path/'predicciones_agosto.csv')
    assert len(p)==164647 and p.foto_mes.eq(202108).all() and not p.numero_de_cliente.duplicated().any()
    assert 'clase_ternaria' not in p
    return m,p


def main():
    lm=json.loads((LOCAL/'manifest.json').read_text(encoding='utf-8'))
    assert lm['estado']=='completo_verificado' and lm['supera_control_16_local']
    assert lm['weights']==dict(lightgbm=.4,tabpfn=.4,catboost=.2) and lm['semillas']==SEEDS
    assert json.loads((LOCAL/'verificacion_independiente.json').read_text())['estado']=='verificado'
    for name,h in lm['archivos_sha256'].items():assert sha(LOCAL/name)==h
    metrics=pd.read_csv(LOCAL/'comparacion_media5.csv').set_index('variante')
    assert metrics.loc['control_16_LGB189_Tab202_50_50','ganancia']==266420000
    assert metrics.loc['mix_LGB189_Tab202_Cat202_40_40_20','ganancia']==269813500
    a,lp=source(LGB);b,cp=source(CAT)
    assert len(a['firma']['features'])==189 and len(b['firma']['features'])==202
    assert a['target_lightgbm']=='BAJA+1/BAJA+2' and b['target_catboost']==b['target_tabpfn']=='BAJA+2'
    pd.testing.assert_frame_equal(lp[KEYS],cp[KEYS])
    np.testing.assert_allclose(lp.p_tabpfn,cp.p_tabpfn,rtol=0,atol=1e-15)
    number=max(int(p.name.split('_')[0]) for p in BOT.iterdir() if p.is_dir() and p.name.split('_')[0].isdigit())+1
    assert number==17
    name=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('EnsembleHist189CatBoost5_%Y%m%d_%H%M%S')
    out=BOT/f'{number}_{name}';out.mkdir();adj=out/'adjuntos_semillas';adj.mkdir()
    pred=lp[KEYS+['p_tabpfn']].copy();files=[];changes=[]
    for seed in SEEDS:
        pred[f'p_lgb189_seed{seed}']=lp[f'p_lgb_seed{seed}']
        pred[f'p_cat202_seed{seed}']=cp[f'p_cat_seed{seed}']
        q=.4*pred[f'p_lgb189_seed{seed}']+.4*pred.p_tabpfn+.2*pred[f'p_cat202_seed{seed}']
        pred[f'score_seed{seed}']=q
        chosen=pred.loc[q>.025,KEYS].copy();chosen['score']=q[q>.025]
        chosen=chosen.sort_values(['score','numero_de_cliente'],ascending=[False,True])
        assert len(chosen)==chosen.numero_de_cliente.nunique()
        path=adj/f'{name}_semillas_seed{seed}.csv'
        path.write_bytes(''.join(f'{int(i)}\n' for i in chosen.numero_de_cliente).encode('ascii'))
        files.append(dict(seed=seed,archivo=str(path.relative_to(out)),contactos=len(chosen),sha256=sha(path)))
        old=(lp[f'p_lgb_seed{seed}']+lp.p_tabpfn)/2>.025;new=q>.025
        changes.append(dict(seed=seed,contactos_entrega16=int(old.sum()),contactos_mix=int(new.sum()),
                            agregados=int((new&~old).sum()),retirados=int((old&~new).sum())))
    values=pred.drop(columns=KEYS).to_numpy();assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    pred.to_csv(out/'predicciones_agosto.csv',index=False)
    pd.DataFrame(changes).to_csv(out/'cambios_contactos_agosto.csv',index=False)
    submit=name+'_semillas';(out/'MENSAJE_SEMILLAS.txt').write_text('submit '+submit+'\n',encoding='ascii')
    (out/'ESTADO_ENVIO.txt').write_text('PREPARADO, PENDIENTE ENVIO MANUAL POR TOMAS.\nCincoCSV exclusivos de adjuntos_semillas.\nSin resultado publico informado.\n',encoding='utf-8')
    m=dict(estado='preparado_pendiente_verificacion',entrega=17,submit=submit,enviado=False,
        train_final=[202104,202105],futuro=202108,semillas=SEEDS,filas_agosto=164647,
        features_lightgbm=189,features_tabpfn=202,features_catboost=202,
        target_lightgbm='BAJA+1/BAJA+2',target_tabpfn='BAJA+2',target_catboost='BAJA+2',
        pesos=dict(lightgbm=.4,tabpfn=.4,catboost=.2),umbral=.025,operador='>',
        fuente_lightgbm=str(LGB.relative_to(ROOT)),fuente_catboost=str(CAT.relative_to(ROOT)),
        fuente_validacion=str(LOCAL.relative_to(ROOT)),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [LGB/'manifest.json',CAT/'manifest.json',
            LGB/'predicciones_agosto.csv',CAT/'predicciones_agosto.csv',LOCAL/'manifest.json',LOCAL/'verificacion_independiente.json']},
        archivos=files,archivos_sha256={p.name:sha(p) for p in out.glob('*.csv')},
        codigo_sha256=sha(Path(__file__)),nuevos_fits=0,api=False,creditos=0,submits=0,
        nuevas_lecturas_dataset=False,junio_validacion=False,etiquetas_agosto=False,
        validacion_local=dict(control16_total=266420000,control16_25pct=66605000,mix_total=269813500,
            mix_25pct=67453375,delta_total=3393500,delta_25pct=848375,semillas_mejoran=4,partes_mejoran=3),
        referencia_publica=dict(entrega=16,media_pesos=96921000,desvio_pesos=1781600),
        limitaciones='Mayo y semillas reutilizados: no test independiente ni garantia publica. Score combina targets distintos, '
                     'no P(BAJA+2) calibrada. CatBoost202 fijo, no CatBoost189 ni Optuna; no cambio de pesos/corte.')
    save(out/'manifest.json',m)
    report=['# Entrega17: LightGBM189 + TabPFN202 + CatBoost202','',
        '**Preparada, pendiente de verificación final y envío manual.** Adjuntar los cinco CSV de [adjuntos_semillas](adjuntos_semillas/) en una sola corrida.','',
        '```text','submit '+submit,'```','',
        'Mezcla **40/40/20**, corte estricto **score >0,025**. Cinco semillas541440/408476/741961/248865/717444: LightGBM189 combinado + TabPFN202 BAJA+2 + CatBoost202 BAJA+2. Cada CSV es una lista individual; no se promedian las cinco semillas.','',
        'Reutiliza predicciones finales abril+mayo→agosto: LightGBM189 de16 y CatBoost202/TabPFN202 de15. Mismo TabPFN en ambos archivos, verificado. CatBoost conserva parámetros800árboles/depth6; LightGBM273árboles; sin nuevos rangos, tuning o entrenamiento.','',
        '| Validación abril→mayo | Ganancia total media5 | 25% |','| --- | ---: | ---: |',
        '| Control16 50/50 | $266.420.000 | $66.605.000 |','| Mix40/40/20 | $269.813.500 | $67.453.375 |',
        '| Mejora | $3.393.500 (+1,27%) | $848.375 |','',
        'Mejoró4/5semillas y3/4partes de mayo. Mayo/semillas reutilizados, partes del mismo mes, no test independiente. El resultado público de17 sigue desconocido. Referencia pública16 $96.921.000/desvío$1.781.600: ya corresponde al público25%, no dividir nuevamente. Fuente: [mini informe local](../../mix_hist189_catboost_20261006_145401/MINI_INFORME.md).','',
        '| Semilla | Contactos de agosto |','| --- | ---: |']
    report += [f"| {f['seed']} | {f['contactos']:,} |" for f in files]
    report += ['',
        'CSV de IDs sin encabezado, score descendente y desempate ID ascendente. Archivos predicciones/cambios son auditoría, no adjuntos al Bot.','',
        'Cero nuevos fits/API/créditos/submits automáticos. No se vuelve a leer el dataset ni se usan etiquetas de agosto/junio. Las fuentes conservan entrenamiento abril+mayo, junio/julio solo historia. Entregas15/16 y modelos originales intactos.','',
        'Manifest conserva hashes/fuentes/protocolo. Verificación final: [verificacion_independiente.json](verificacion_independiente.json). Modelo CatBoost189 y Optuna son otros experimentos pendientes.']
    (out/'INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Salida:',out,flush=True);print('submit '+submit,flush=True);print('Contactos:',[f['contactos'] for f in files],flush=True)


if __name__=='__main__':main()
