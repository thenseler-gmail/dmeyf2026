"""Cinco listas por semilla de43 a corte2,75%; reutiliza probabilidades guardadas."""
import importlib
import json
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

base = importlib.import_module('116_promedio20_hist189')
SOURCE = base.BOT/'43_EnsembleVinculos197Promedio5Corte275_20261010_094750'
LOCAL = base.SAL/'vinculos_recurrentes_20261010'
OUT = base.SAL/'distribucion43_semillas_20261010'
KEYS = ['numero_de_cliente','foto_mes']


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    OUT.mkdir(exist_ok=True)
    ref = read(SOURCE/'manifest.json')
    assert ref['enviado'] and ref['entrega']==43 and ref['features_lightgbm']==197
    assert ref['umbral']==.0275 and ref['pesos']==dict(lightgbm=.5,tabpfn=.5)
    assert read(SOURCE/'RESULTADO_BOT.json')['media_publica_pesos']==100815000
    seeds = ref['semillas']
    assert seeds==[541440,408476,741961,248865,717444]
    original = [SOURCE/'manifest.json', SOURCE/'predicciones_agosto.csv', SOURCE/'RESULTADO_BOT.json',
                SOURCE/'verificacion_independiente.json', LOCAL/'RESULTADO_LOCAL.json', LOCAL/'predicciones_mayo.csv']
    original += [SOURCE/e['archivo'] for e in ref['archivos']]
    signature = dict(fuente_entrega=str(SOURCE.relative_to(base.ROOT)),
        fuentes_sha256={str(p.relative_to(base.ROOT)):base.sha(p) for p in original},
        codigo_sha256={f:base.sha(base.TP/f) for f in ['131_preparar_cinco_listas43.py',
            '116_promedio20_hist189.py','104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']},
        train_final=ref['train_final'], futuro=202108, semillas=seeds, umbral=.0275, operador='>',
        pesos=ref['pesos'], agregacion='cinco_listas_individuales',
        regla='Un CSV por semilla: 0.5*p_lgb_seed +0.5*p_tabpfn; mismo TabPFN en los cinco',
        api=False, creditos=0, nuevos_fits=0, submit_automatico=False,
        autorizacion='Usuario pide distribucion de43 enviando cinco archivos en lugar de uno')
    if (OUT/'PLAN.json').exists():
        assert read(OUT/'PLAN.json')==signature
    else:
        base.save(OUT/'PLAN.json',signature)
    assert base.sha(SOURCE/'predicciones_agosto.csv')==ref['predicciones_sha256']
    for path,h in ref['modelos_sha256'].items():
        assert base.sha(base.ROOT/path)==h
    p = pd.read_csv(SOURCE/'predicciones_agosto.csv',float_precision='round_trip')
    assert len(p)==164647 and p.numero_de_cliente.is_unique and p.foto_mes.eq(202108).all()
    pred = p.copy()
    for s in seeds:
        pred[f'score_seed{s}']=.5*p[f'p_lgb_seed{s}']+.5*p.p_tabpfn
    scorecols = [f'score_seed{s}' for s in seeds]
    np.testing.assert_allclose(pred[scorecols].mean(axis=1),p.score_promedio5,rtol=0,atol=1e-15)
    np.testing.assert_array_equal(pred[scorecols].mean(axis=1).to_numpy()>.0275,p.score_promedio5.to_numpy()>.0275)
    avglist = p.loc[p.score_promedio5>.0275].sort_values(['score_promedio5','numero_de_cliente'],ascending=[False,True])
    original_csv = SOURCE/ref['archivos'][0]['archivo']
    assert base.sha(original_csv)==ref['archivos'][0]['sha256']
    assert original_csv.read_bytes()==''.join(f'{int(i)}\n' for i in avglist.numero_de_cliente).encode('ascii')
    assert len(avglist)==10404
    if (OUT/'ENTREGA.json').exists():
        loc = read(OUT/'ENTREGA.json')
    else:
        number=max(int(d.name.split('_')[0]) for d in base.BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
        stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
        name='EnsembleVinculos197Semillas5Corte275_'+stamp
        loc=dict(entrega=number,submit=name,carpeta=str((base.BOT/f'{number}_{name}').relative_to(base.ROOT)))
        base.save(OUT/'ENTREGA.json',loc)
    delivery=base.ROOT/loc['carpeta']
    delivery.mkdir(exist_ok=True);(delivery/'adjuntos').mkdir(exist_ok=True)
    assert not (delivery/'RESULTADO_BOT.json').exists()
    if (delivery/'manifest.json').exists():
        assert not read(delivery/'manifest.json')['enviado']
    entries=[];changes=[];sets={};refids=set(avglist.numero_de_cliente)
    for s in seeds:
        col=f'score_seed{s}'
        selected=pred.loc[pred[col]>.0275].sort_values([col,'numero_de_cliente'],ascending=[False,True])
        ids=set(selected.numero_de_cliente);sets[s]=ids
        path=delivery/'adjuntos'/f'{loc["submit"]}_seed{s}.csv'
        path.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
        entries.append(dict(seed=s,score_columna=col,archivo=str(path.relative_to(delivery)),contactos=len(selected),sha256=base.sha(path)))
        changes.append(dict(seed=s,contactos=len(ids),comunes_con43=len(ids&refids),agregados_vs43=len(ids-refids),retirados_vs43=len(refids-ids)))
    assert len(set(e['sha256'] for e in entries))==5
    pd.DataFrame(changes).to_csv(delivery/'comparacion_listas_vs43.csv',index=False)
    overlaps=[dict(seed_a=a,seed_b=b,comunes=len(sets[a]&sets[b]),union=len(sets[a]|sets[b]),
                   jaccard=len(sets[a]&sets[b])/len(sets[a]|sets[b])) for i,a in enumerate(seeds) for b in seeds[i+1:]]
    pd.DataFrame(overlaps).to_csv(delivery/'solapamiento_listas.csv',index=False)
    pred.to_csv(delivery/'predicciones_agosto.csv',index=False)
    lr=read(LOCAL/'RESULTADO_LOCAL.json')
    assert base.sha(LOCAL/'predicciones_mayo.csv')==lr['predicciones_sha256']
    lp=pd.read_csv(LOCAL/'predicciones_mayo.csv',float_precision='round_trip')
    assert lp.foto_mes.eq(202105).all() and lp.numero_de_cliente.is_unique
    y=lp.clase_ternaria.eq('BAJA+2').to_numpy()
    local_scores=np.column_stack([.5*lp[f'p_vinculos_seed{s}']+.5*lp.p_tabpfn for s in seeds])
    local_rows=[]
    for i,s in enumerate(seeds):
        metrics=base.metric(y,local_scores[:,i])
        assert metrics==next(r['candidato'] for r in lr['pareados'] if r['seed']==s)
        local_rows.append(dict(seed=s,**metrics))
    assert base.metric(y,local_scores.mean(axis=1))==lr['candidato']
    mean=float(np.mean([r['ganancia_total'] for r in local_rows]))
    controlmean=float(np.mean([r['control']['ganancia_total'] for r in lr['pareados']]))
    assert mean-controlmean==lr['media_delta_semillas']
    pd.DataFrame(local_rows).to_csv(delivery/'resultados_locales.csv',index=False)
    validation=dict(media_ganancias_cinco_listas_total=mean,media_ganancias_cinco_listas_25pct=mean/4,
        desvio_poblacional_ganancias_local_total=float(np.std([r['ganancia_total'] for r in local_rows],ddof=0)),
        control_media_cinco_listas_total=controlmean,delta_media_cinco_listas_total=mean-controlmean,
        ganancia_lista_promedio_probabilidades_total=lr['candidato']['ganancia_total'],
        lista_promedio_probabilidades_publica43=100815000,
        limite='Mayo reutilizado; ganancia publica media de estas cinco listas desconocida')
    manifest=dict(**loc,estado='preparado_pendiente_verificacion',enviado=False,firma=signature,
        fuente_entrega=str(SOURCE.relative_to(base.ROOT)),fuente_modelos_finales=ref['fuente_modelos_finales'],
        train_final=ref['train_final'],futuro=202108,semillas=seeds,features_lightgbm=197,features_tabpfn=202,
        target_lightgbm=ref['target_lightgbm'],target_tabpfn=ref['target_tabpfn'],
        pesos=ref['pesos'],umbral=.0275,operador='>',agregacion='cinco_listas_individuales',
        archivos=entries,predicciones_sha256=base.sha(delivery/'predicciones_agosto.csv'),
        modelos_sha256=ref['modelos_sha256'],comparacion_vs43=changes,validacion_local=validation,
        api=False,creditos=0,nuevos_fits=0,nuevos_fits_tabpfn=0,submit_automatico=False,
        limitacion='Cinco semillas de LightGBM con el mismo TabPFN. Media/desvio de ganancias de listas individuales, '
            'no intervalo de confianza de43, ni distribucion de su lista de probabilidades promediadas. '
            '43 original y su resultado $100.815.000 se preservan; publica44 desconocida.')
    base.save(delivery/'manifest.json',manifest)
    saved=pd.read_csv(delivery/'predicciones_agosto.csv',float_precision='round_trip')
    for e in entries:
        s=e['seed'];q=saved[[f'p_lgb_seed{s}','p_tabpfn']].to_numpy()@np.array([.5,.5])
        np.testing.assert_allclose(q,saved[e['score_columna']],rtol=0,atol=1e-15)
        np.testing.assert_array_equal(q>.0275,saved[e['score_columna']].to_numpy()>.0275)
    subprocess.run([sys.executable,str(base.TP/'105_reproducir_csv_entrega.py'),'--entrega',str(delivery),
                    '--salida',str(OUT/'reproduccion_csv')],check=True)
    base.save(delivery/'verificacion_independiente.json',dict(estado='verificado',archivos=5,
        mezcla_reconstruida=True,csv_reproducidos_hash_identico=True,lista43_reproducida=True,
        fuente43_preservada=True,validacion_local_reproducida=True,api=False,creditos=0))
    manifest['estado']='completo_verificado_preparado_pendiente';base.save(delivery/'manifest.json',manifest)
    (delivery/'MENSAJE_BOT.txt').write_text('submit '+loc['submit']+'\n',encoding='ascii')
    (delivery/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. Pendiente envio manual al Bot: adjuntar los cinco CSV juntos. Resultado publico desconocido.\n',encoding='utf-8')
    note=f"# Entrega{loc['entrega']}: cinco listas de43\n\nUna lista por semilla de LightGBM197, mezclada50/50 con el mismo TabPFN202 guardado. Cinco semillas originales, corte>2,75%, abril+mayo->agosto. Reutiliza probabilidades y modelos finales de43: cero entrenamiento, API o creditos.\n\n```text\n"+pd.DataFrame(changes).to_string(index=False)+f"\n```\n\nComando: `submit {loc['submit']}`. Adjuntar los CINCO CSV de `adjuntos/` en la misma entrega, sin encabezado ni indice. No adjuntar predicciones_agosto.csv ni el CSV original de43. No enviado automaticamente.\n\nEl Bot informa media/desvio de cinco GANANCIAS, una por lista.43 obtuvo $100.815.000 con UNA lista construida promediando probabilidades antes del corte. Esta nueva media puede ser distinta; no es una estimacion del desvio de aquella lista fija. Solo varia LightGBM; TabPFN es compartido. Sin intervalo de confianza ni garantia de private.\n\nMayo: media de cinco listas total ${mean:,.0f}, equivalente25% ${mean/4:,.0f}; lista de probabilidades promediadas total ${lr['candidato']['ganancia_total']:,.0f}. Mayo reutilizado. Cinco scores reconstruidos desde archivos, todos los CSV reproducidos con hash identico y codigo firmado archivado.43 y sus fuentes permanecen intactas y siguen siendo la mejor referencia publica.\n"
    (delivery/'INFORME.md').write_text(note,encoding='utf-8')
    importlib.import_module('104_archivar_codigo_entrega').archivar(delivery)
    for p,h in signature['fuentes_sha256'].items():assert base.sha(base.ROOT/p)==h
    result=dict(**loc,estado='completo_verificado_preparado_pendiente',archivos=entries,
        comando='submit '+loc['submit'],api=False,creditos=0,nuevos_fits=0)
    base.save(OUT/'RESULTADO.json',result)
    summary=f"## Cinco listas de43 preparadas — 2026-10-10\n\nEntrega{loc['entrega']}, cinco CSV por las semillas originales. Misma mezcla50/50 y corte>2,75%; modelos y predicciones reutilizados, cero fits/API/creditos. Adjuntar cinco archivos juntos con `submit {loc['submit']}`. Pendiente envio manual y resultado. La media de ganancias de cinco listas difiere de la ganancia de la lista promedio43, que sigue como referencia publica $100.815.000. [Informe]({delivery.relative_to(base.TP).as_posix()}/INFORME.md).\n"
    steps=base.TP/'NEXT_STEPS_IDEAS.md';steps.write_text(summary+'\n'+steps.read_text(encoding='utf-8'),encoding='utf-8')
    with (base.ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write('\n'+summary.replace('(salidas/','(tp_primera_entrega/salidas/')+'\n'+note)
    with (base.TP/'PLAN_EXPERIMENTOS_20261010.md').open('a',encoding='utf-8') as f:f.write('\n'+summary)
    cfgpath=base.TP/'config_validacion_lightgbm.json';cfg=read(cfgpath)
    cfg['distribucion_cinco_listas_entrega43']=result
    assert cfg['mejor_publico_registrado']['entrega']==43
    base.save(cfgpath,cfg)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
