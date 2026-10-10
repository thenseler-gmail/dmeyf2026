"""Informe y grafico del reentrenamiento33, desde resultados verificados."""
import argparse
import json
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def pesos(x):
    return '$'+f'{x:,.0f}'.replace(',','.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta',type=Path)
    out=parser.parse_args().carpeta
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert json.loads((out/'verificacion.json').read_text())['estado']=='verificado'
    t=pd.read_csv(out/'comparacion.csv')
    seeds=pd.read_csv(out/'resultados_semillas.csv')
    perfil=pd.read_csv(out/'feature_desarrollo.csv')
    cov=perfil.groupby('foto_mes')[m['feature_nueva']].agg(filas='size',observables='count',interrupciones='sum')
    cov.to_csv(out/'cobertura_feature.csv')
    cols=m['firma']['features']
    labels={'historicas':'Historicas','haberes':'Historicas + haberes'}
    targets={'baja2':'BAJA+2','bajas':'Combinado'}
    stages={'cv_cliente':'CV por cliente','temporal_2meses':'Marzo -> mayo','retrospectivo_1mes':'Abril -> mayo'}
    lines=['# LightGBM reentrenado: historicas e interrupcion de haberes','',
        'Se reentreno con las nuevas particiones y tres semillas, manteniendo parametros y umbral. BAJA+2 es el target principal; el combinado es control. Sin TabPFN ni llamadas API.','',
        '203 variables en la configuracion solicitada:152 originales,50 historicas y abandono_pasa_a_cero_mpayroll. La ultima columna vale1 si el cliente tenia haberes positivos el mes calendario anterior y ahora cero; es NaN si falta alguna fuente.','',
        '## Resultados del promedio de tres semillas','',
        '| Particion | Mes | Target | Variables | Contactos | TP | FP | Ganancia total | 25% del total |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in t.sort_values(['target','etapa','mes','variante']).itertuples():
        lines.append(f'| {stages[r.etapa]} | {r.mes} | {targets[r.target]} | {labels[r.variante]} | {r.contactos:,} | {r.tp:,} | {r.fp:,} | {pesos(r.ganancia)} | {pesos(r.ganancia_25pct)} |'.replace(',','.' ))
    lines += ['', '## Aporte de haberes, misma particion y mismas semillas','']
    for target in ['baja2','bajas']:
        for etapa,mes in [('cv_cliente',202104),('cv_cliente',202105),('temporal_2meses',202105),('retrospectivo_1mes',202105)]:
            part=t[t.target.eq(target)&t.etapa.eq(etapa)&t.mes.eq(mes)].set_index('variante')
            delta=part.loc['haberes','ganancia']-part.loc['historicas','ganancia']
            pc=delta/part.loc['historicas','ganancia']*100
            lines.append(f'- {targets[target]}, {stages[etapa]} {mes}: diferencia {pesos(delta)} total,25% {pesos(delta/4)} ({pc:+.2f}%).')
    lines += ['', 'La diferencia entre203 y202 columnas tambien cambia el muestreo de variables por arbol: no identifica un efecto causal puro de la nueva senal.', '',
        '## Protocolo y limites','',
        'Cuatro grupos fijos por cliente. CVabril entrena marzo+abril de los otros grupos; CVmayo entrena marzo+abril+mayo. Ninguna fila del cliente evaluado entra en fit, ni meses posteriores al evaluado. CV retrospectivo: puede usar etiquetas de otros clientes del mismo mes, por lo que no mide drift futuro ni simula disponibilidad prospectiva de etiquetas.','',
        'Control temporal marzo->mayo con dos meses de distancia; marzo carece de febrero, historicas e interrupcion de haberes observables. Por tanto, este control no puede aprender la senal de haberes. Abril->mayo conserva historia de train, pero es retrospectivo de un mes. Parametros previamente seleccionados en mayo reutilizado; no hay test independiente nuevo. Junio no decide la seleccion.','',
        'BAJA+2 trial29/192rondas, combinado trial6/273rondas. Semillas189293,107584,408287; se promedian probabilidades antes de aplicar p>0.025. Se guardan resultados individuales, folds y cache. No se optimizaron parametros ni corte. BAJA+1 siempre cuenta como error de ganancia; la salida combinada no es P(BAJA+2).','',
        'Ganancia OOF mensual suma las partes disjuntas, sin extrapolarlas. El25% local es referencia proporcional; no certifica $100millones en el publico de agosto. Folds/modelos comparten train y no son observaciones independientes para un intervalo de confianza.','',
        '## Variacion entre semillas individuales','',
        '| Target | Variables | Particion | Mes | Ganancia minima total /25% | Ganancia maxima total /25% |',
        '| --- | --- | --- | --- | --- | --- |']
    for (target,variante,etapa,mes),g in seeds.groupby(['target','variante','etapa','mes']):
        lo=g.ganancia.min(); hi=g.ganancia.max()
        lines.append(f'| {targets[target]} | {labels[variante]} | {stages[etapa]} | {mes} | {pesos(lo)} /{pesos(lo/4)} | {pesos(hi)} /{pesos(hi/4)} |')
    if 'carpeta_candidato' in m:
        c=Path(m['carpeta_candidato']); cm=json.loads((c/'manifest.json').read_text())
        lines += ['', '## Candidato preparado','',
            f'`{c.name}`: LightGBM BAJA+2,203 variables, promedio de20 semillas, entrenamiento mayo+junio,327.882 filas. Agosto:{cm["filas_agosto"]:,} clientes, {cm["contactos"]:,} contactos con p>2.5%. Ganancia agosto desconocida. Candidato solicitado, sin seleccion automatica ni envio al Bot.', '',
            f'CSV `{cm["archivo_submit"]}`. Mensaje manual: `submit {cm["submit"]}`. Modelos y probabilidades guardados; verificacion independiente reprodujo una semilla desde el modelo y variables de agosto.']
        (c/'RESULTADO_VALIDACION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines += ['', '## Verificacion','',
        'Script34 reconstruyo16 comparaciones de promedios,48 de semillas,32 folds, la feature desde mpayroll crudo y el candidato. Verifico claves/probabilidades, grupos disjuntos, meses de fit, ganancias y su25%, hashes,20 modelos finales, promedio/umbral y reproduccion de una semilla. Sin API ni creditos.','',
        '![Comparacion de ganancias](comparacion_ganancias.png)']
    (out/'INFORME.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(13,5.9),sharey=True)
    specs=[('baja2','historicas'),('baja2','haberes'),('bajas','historicas'),('bajas','haberes')]
    colors=['#598e9e','#1d6479','#afbed0','#768ca7']
    names=['BAJA+2\nHistoricas','BAJA+2\n+ haberes','Combinado\nHistoricas','Combinado\n+ haberes']
    for a,mes in zip(axes,[202104,202105]):
        for i,(target,variante) in enumerate(specs):
            r=t[t.etapa.eq('cv_cliente')&t.mes.eq(mes)&t.target.eq(target)&t.variante.eq(variante)].iloc[0]
            v=r.ganancia_25pct/1e6
            a.bar(i,v,width=.68,color=colors[i])
            a.text(i,v+2,f'{v:.2f}'.replace('.',',')+'\nTotal '+f'{r.ganancia/1e6:.2f}'.replace('.',','),ha='center',fontsize=9)
        a.set_title({202104:'Abril',202105:'Mayo'}[mes],weight='bold')
        a.set_xticks(range(4),names,fontsize=10)
        a.set_ylim(0,165)
        a.grid(axis='y',alpha=.18); a.set_axisbelow(True)
        a.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('25% de la ganancia OOF ($ millones)')
    fig.suptitle('LightGBM: historicas e interrupcion de haberes',fontsize=16,weight='bold')
    fig.text(.5,.035,'Promedio de tres semillas; cuatro grupos de clientes; p >2,5%.\nEtiquetas: 25% y total, en millones. CV retrospectivo; no garantiza publico de agosto.',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.12,1,.93])
    fig.savefig(out/'comparacion_ganancias.png',dpi=160)
    plt.close(fig)
    print('Informe y grafico guardados:',out)


if __name__=='__main__':
    main()
