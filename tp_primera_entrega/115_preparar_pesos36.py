"""Pesos LGB/Tab40/60 y60/40; promedio5 y umbral36 congelados."""
import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

TP = Path(__file__).resolve().parent
ROOT = TP.parent
SAL = TP/'salidas'
BOT = SAL/'01_entregas_bot'
SOURCE = BOT/'16_EnsembleHist1895_20261006_143235'
CONTROL = BOT/'36_Ensemble16Promedio5Corte275_20261009_192946'
CUT = .0275


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    ref = json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    control = json.loads((CONTROL/'manifest.json').read_text(encoding='utf-8'))
    sourcehash = ref.get('predicciones_sha256') or ref['archivos_sha256']['predicciones_agosto.csv']
    assert sha(SOURCE/'predicciones_agosto.csv') == sourcehash
    assert sha(CONTROL/'predicciones_agosto.csv') == control['predicciones_sha256']
    assert control['umbral'] == CUT
    original = CONTROL/control['archivos'][0]['archivo']
    assert sha(original) == control['archivos'][0]['sha256']
    p = pd.read_csv(SOURCE/'predicciones_agosto.csv',float_precision='round_trip')
    c = pd.read_csv(CONTROL/'predicciones_agosto.csv',float_precision='round_trip')
    keys = ['numero_de_cliente','foto_mes']
    pd.testing.assert_frame_equal(p[keys],c[keys])
    assert len(p)==164647 and p.numero_de_cliente.is_unique and p.foto_mes.eq(202108).all()
    seeds = control['semillas']
    columns = [f'p_lgb_seed{s}' for s in seeds]
    lgb = p[columns].mean(axis=1)
    np.testing.assert_allclose((lgb+p.p_tabpfn)/2,c.score_promedio5,rtol=0,atol=1e-15)
    baseids = set(int(i) for i in original.read_text(encoding='ascii').splitlines())
    assert set(p.loc[(lgb+p.p_tabpfn)/2>CUT,'numero_de_cliente']) == baseids
    localpath = SAL/'features_local_20261006_140702/historia_1_mes/predicciones_mayo.csv'
    assert sha(localpath)==json.loads((BOT/'35_Ensemble16Promedio5Corte30_20261009_192311/manifest.json').read_text(encoding='utf-8'))['fuente_local_sha256']
    local = pd.read_csv(localpath,float_precision='round_trip')
    locallgb = local[[f'p_seed{s}' for s in seeds]].mean(axis=1)
    payoff = np.where(local.clase_ternaria.eq('BAJA+2'),1072500,-27500)
    localbaseline = int(payoff[((locallgb+local.p_tabpfn)/2>CUT).to_numpy()].sum())
    first = max(int(d.name.split('_')[0]) for d in BOT.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
    stamp = datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
    results = []
    for number, (weight, label) in enumerate([(.4,'L40T60'),(.6,'L60T40')],start=first):
        name = f'Ensemble16Promedio5{label}Corte275_{stamp}'
        out = BOT/f'{number}_{name}'
        out.mkdir(); (out/'adjuntos').mkdir()
        pred = p[keys+['p_tabpfn']+columns].copy()
        pred['p_lgb_promedio5'] = lgb
        pred['score_promedio5'] = weight*lgb+(1-weight)*p.p_tabpfn
        independent = np.mean(weight*p[columns].to_numpy()+(1-weight)*p.p_tabpfn.to_numpy()[:,None],axis=1)
        np.testing.assert_allclose(pred.score_promedio5,independent,rtol=0,atol=1e-15)
        assert np.isfinite(pred.score_promedio5).all() and pred.score_promedio5.between(0,1).all()
        selected = pred.loc[pred.score_promedio5>CUT].sort_values(['score_promedio5','numero_de_cliente'],ascending=[False,True])
        ids = set(selected.numero_de_cliente)
        target = out/'adjuntos'/f'{name}.csv'
        target.write_bytes(''.join(f'{int(i)}\n' for i in selected.numero_de_cliente).encode('ascii'))
        pred.to_csv(out/'predicciones_agosto.csv',index=False)
        localgain = int(payoff[(weight*locallgb+(1-weight)*local.p_tabpfn>CUT).to_numpy()].sum())
        meta = {k:control[k] for k in ['train_final','futuro','semillas','agregacion','features_lightgbm','features_tabpfn','target_lightgbm','target_tabpfn']}
        meta.update(estado='preparado_pendiente_verificacion',entrega=number,submit=name,enviado=False,
            fuente_entrega=str(SOURCE.relative_to(ROOT)),fuente_control=str(CONTROL.relative_to(ROOT)),
            fuente_manifest_sha256=sha(SOURCE/'manifest.json'),fuente_predicciones_sha256=sourcehash,
            fuente_control_manifest_sha256=sha(CONTROL/'manifest.json'),
            predicciones_sha256=sha(out/'predicciones_agosto.csv'),pesos=dict(lightgbm=weight,tabpfn=1-weight),
            umbral=CUT,operador='>',archivos=[dict(score_columna='score_promedio5',archivo=str(target.relative_to(out)),contactos=len(selected),sha256=sha(target))],
            cambios_vs36=dict(agregados=len(ids-baseids),retirados=len(baseids-ids)),
            referencia_publica36=98175000,api=False,creditos=0,nuevos_fits=0,
            validacion_local=dict(ganancia_total=localgain,ganancia_25pct=localgain/4,control36_total=localbaseline,delta_total=localgain-localbaseline),
            fuente_local_sha256=sha(localpath),firma=dict(codigo_sha256={Path(__file__).name:sha(Path(__file__))}),
            limitacion='Pesos predefinidos por usuario, corte fijo2,75%. Mayo reutilizado, ganancia local diagnóstica. Una sola lista; resultado público pendiente.')
        save(out/'manifest.json',meta)
        subprocess.run([sys.executable,str(TP/'105_reproducir_csv_entrega.py'),'--entrega',str(out),'--salida',str(SAL/f'reproduccion_{number}')],check=True)
        meta['estado']='completo_verificado_preparado_pendiente';save(out/'manifest.json',meta)
        (out/'MENSAJE_BOT.txt').write_text('submit '+name+'\n',encoding='ascii')
        (out/'ESTADO_ENVIO.txt').write_text('PREPARADO Y VERIFICADO. PENDIENTE ENVÍO MANUAL. Un CSV en corrida separada.\n',encoding='utf-8')
        (out/'INFORME.md').write_text(
            f'# Entrega {number}: {label}\n\nModelos16 guardados, promedio de cinco LightGBM. Pesos LightGBM {weight:.0%}, TabPFN {1-weight:.0%}. '
            f'Corte estricto >2,75%. {len(selected)} clientes; {len(ids-baseids)} agregados y {len(baseids-ids)} retirados frente36.\n\n'
            f'Mayo: ganancia total ${localgain:,.0f}, delta frente score36 ${localgain-localbaseline:,.0f}. Mayo reutilizado, diagnóstico local.\n\n'
            f'Comando: `submit {name}`. Un CSV de adjuntos en corrida separada.\n\n'
            'Score verificado mediante dos formas equivalentes de promediar; CSV reproducido con hash idéntico. Sin nuevos fits ni API. Público pendiente.\n',encoding='utf-8')
        importlib.import_module('104_archivar_codigo_entrega').archivar(out)
        results.append(dict(entrega=number,carpeta=str(out.relative_to(ROOT)),comando='submit '+name,contactos=len(selected),pesos=meta['pesos']))
    assert sha(SOURCE/'predicciones_agosto.csv') == sourcehash
    note='\n## Pesos alrededor de36 preparados — 2026-10-09\n\n'
    for r in results:note+=f"Entrega{r['entrega']}: {r['comando']}; {r['contactos']}clientes, pesos {r['pesos']}. UnCSV; pendiente envío manual.\n\n"
    note+='Promedio5, corte>2,75% fijo; modelos16 guardados. DosCSV reproducidos con hashes idénticos; sin fits/API/créditos.\n'
    with (ROOT/'BITACORA_DMEYF.md').open('a',encoding='utf-8') as f:f.write(note)
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
