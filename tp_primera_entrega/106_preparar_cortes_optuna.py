"""Diez entregas: promedio top10 LightGBM solo o mezcla Tab202, cinco topN.

Un corte por entrega: no agregar distintos cortes en la misma corrida del Bot.
No API, fit ni envío al Bot. Sólo lee resultados finales verificados.
"""
import argparse
import importlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

pipe=importlib.import_module('89_catedra_pipeline')
archive=importlib.import_module('104_archivar_codigo_entrega')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
    source=args.salida.resolve()
    done=json.loads((source/'final_estado.json').read_text(encoding='utf-8'))
    spec=json.loads((source/'top10_congelado.json').read_text(encoding='utf-8'))
    assert done['estado']=='completo_verificado' and done['configuraciones']==10
    path=source/'predicciones_top10_agosto.csv';assert pipe.sha(path)==done['predicciones_sha256']
    pred=pd.read_csv(path,float_precision='round_trip')
    assert len(pred)==164647 and pred.numero_de_cliente.is_unique and pred.foto_mes.eq(202108).all()
    qs=pred[[f"p_trial{x['trial']}" for x in spec['configuraciones']]].to_numpy()
    np.testing.assert_allclose(qs.mean(axis=1),pred.p_lgb_top10,rtol=0,atol=1e-15)
    np.testing.assert_allclose((pred.p_lgb_top10+pred.p_tab202)/2,pred.score_mix50,rtol=0,atol=1e-15)
    assert np.isfinite(qs).all() and ((qs>=0)&(qs<=1)).all()
    local=pd.read_csv(source/'cortes_top10_mayo.csv')
    controls=pd.read_csv(source/'comparacion_misma_ventana.csv')
    roots=pipe.SAL/'01_entregas_bot';registry=source/'entregas_cortes.json'
    records=json.loads(registry.read_text(encoding='utf-8'))['entregas'] if registry.exists() else []
    groups=[('LightGBMOptuna10','p_lgb_top10','lgb_top10'),
            ('MixOptuna10Tab202','score_mix50','mix_top10_tab202')]
    for label,col,variant in groups:
        for n in [10000,10500,11000,11500,12000]:
            if any(r['modelo']==label and r['contactos']==n for r in records):continue
            number=max(int(d.name.split('_')[0]) for d in roots.iterdir() if d.is_dir() and d.name.split('_')[0].isdigit())+1
            stamp=datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y%m%d_%H%M%S')
            tag=f'{label}Top{n}_{stamp}';out=roots/f'{number}_{tag}';out.mkdir()
            adj=out/'adjuntos';adj.mkdir()
            order=np.lexsort((pred.numero_de_cliente.to_numpy(),-pred[col].to_numpy()))
            selected=pred.numero_de_cliente.to_numpy()[order[:n]]
            csv=adj/(tag+'.csv');csv.write_bytes(''.join(str(int(i))+'\n' for i in selected).encode('ascii'))
            np.testing.assert_array_equal(pd.read_csv(csv,header=None)[0],selected)
            score=pred[pipe.KEYS+[col]].copy();score.to_csv(out/'predicciones_agosto.csv',index=False)
            row=local[(local.variante==variant)&local.corte.eq('top'+str(n))].iloc[0]
            control_name='control_mix_promedio5' if label.startswith('Mix') else 'control_lgb_promedio5'
            control=controls[controls.variante.eq(control_name)&controls.corte.eq('top'+str(n))].iloc[0]
            entry=dict(modelo=label,contactos=n,entrega=number,carpeta=str(out.relative_to(pipe.ROOT)),
                 comando='submit '+tag,archivo=str(csv.relative_to(pipe.ROOT)),
                 local_total=int(row.ganancia),local25pct=float(row.ganancia_25pct),
                 control_misma_ventana_total=int(control.ganancia),
                 delta_control_total=int(row.ganancia-control.ganancia),
                 delta_control25pct=float((row.ganancia-control.ganancia)/4))
            manifest=dict(estado='preparado_verificado_pendiente',entrega=number,submit=tag,enviado=False,
                 fuente_estudio=str(source.relative_to(pipe.ROOT)),train=[202103,202104,202105,202106],
                 prediccion=202108,target_lightgbm='BAJA+1/BAJA+2',configuraciones=spec['configuraciones'],
                 features_lightgbm=len(spec['features']),semilla_lightgbm=spec['fixed']['seed'],
                 tabpfn='202 original16,abril+mayo,BAJA+2' if label.startswith('Mix') else None,
                 pesos=dict(lightgbm=.5,tabpfn=.5) if label.startswith('Mix') else dict(lightgbm=1),
                 tipo_corte='top_n',operador='top_n',score_columna=col,contactos=n,
                 adjuntos=[dict(archivo=str(csv.relative_to(out)),score_columna=col,top_n=n,sha256=pipe.sha(csv))],
                 referencia_local=dict(ganancia_total=int(row.ganancia),ganancia25pct=float(row.ganancia_25pct),
                      descripcion='Mayo: ranking promedio10configuraciones, mismo topN; selección Optuna en mayo reutilizado'),
                 referencia_publica16=96921000,api=False,creditos=0,submits=0,
                 codigo_sha256={f:pipe.sha(pipe.TP/f) for f in ['106_preparar_cortes_optuna.py','104_archivar_codigo_entrega.py','105_reproducir_csv_entrega.py']},
                 predicciones_sha256=pipe.sha(out/'predicciones_agosto.csv'),
                 limitacion='Nuevo LightGBM usa marzo–junio; Tab guardado sólo abril+mayo. Media de probabilidades, no media de ganancias/semillas. No labelsagosto ni garantía pública.')
            pipe.save(out/'manifest.json',manifest)
            (out/'MENSAJE.txt').write_text(entry['comando']+'\n',encoding='utf-8')
            (out/'ESTADO_ENVIO.txt').write_text('Preparado; un CSV, pendiente envío manual.\n',encoding='utf-8')
            (out/'INFORME.md').write_text('# '+tag+'\n\n'
                 f'Un CSV con {n:,} contactos. Score promedio10configuraciones LightGBM'
                 + (' +TabPFN202 original16,50/50.' if label.startswith('Mix') else ', sin TabPFN.')
                 +f' Localmayo: total${int(row.ganancia):,},25%${row.ganancia_25pct:,.0f}. '
                 'Mayo reutilizado; no resultado público. Cinco cortes distintos son cinco entregas, no semillas. '
                 'Referenciapública16:$96.921.000.\n\nMensaje:`'+entry['comando']+'`. Adjuntar sólo elCSV de adjuntos.\n',encoding='utf-8')
            archive.archivar(out)
            records.append(entry);pipe.save(registry,dict(estado='preparando',entregas=records,enviado_bot=False))
            print('Preparada',number,label,n,flush=True)
    assert len(records)==10
    pipe.save(registry,dict(estado='completo_verificado',entregas=records,enviado_bot=False))
    ranking=sorted(records,key=lambda r:-r['local_total'])
    lines=['# Pruebas Optuna: LightGBM solo y mezcla con TabPFN','',
       'Diez entregas, unCSV por corte. No se envían automáticamente. '
       'El Bot informa ganancia de cada corte por separado; desvío0 con unCSV no representa variabilidad de modelos. '
       'Referencia16:$96.921.000 públicos. Ganancia de agosto desconocida.','',
       '| Entrega | Modelo | Contactos | Local total | Local25% | Delta control equivalente | Delta25% |',
       '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in ranking:lines.append(f"| {r['entrega']} | {r['modelo']} | {r['contactos']} | ${r['local_total']:,} | ${r['local25pct']:,.0f} | ${r['delta_control_total']:,} | ${r['delta_control25pct']:,.0f} |")
    lines+=['','## Mensajes y adjuntos','']
    for r in ranking:lines += [f"- Entrega{r['entrega']}: `{r['comando']}`. CSV: `{r['archivo']}`."]
    lines+=['','Priorización por ganancia local en mayo reutilizado; no prueba independiente. '
       'No mezclar todos los cortes en una sola corrida del Bot, porque su media ocultaría qué corte funcionó. '
       'La ventana y composición difieren del control16. Comparación con control de misma ventana en comparacion_misma_ventana.csv.']
    lines += ['', 'Priorizar candidatos con delta positivo frente al control equivalente; preparar una lista '
        'no implica recomendar su envío si pierde localmente. No comparar media de ganancias individuales '
        'con ganancia de una única lista promedio como si fueran la misma métrica.']
    (source/'PLAN_SUBMITS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Plan y diez entregas completos:',source/'PLAN_SUBMITS.md',flush=True)


if __name__=='__main__':main()
