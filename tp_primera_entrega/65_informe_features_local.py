"""Informe y figura de las cuatro pruebas locales, tras verificacion exitosa."""
import hashlib
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LABELS = dict(control_entrega8='Control 202',sin_prestamos='Sin préstamos 200',
              rangos_mensuales='Rangos mensuales 205',historia_1_mes='Historia un mes 189',
              historia_1_mes_sin_relativos='Un mes sin relativos 177')


def money(value):
    return '$'+f'{value:,.0f}'.replace(',','.')


def main():
    out=Path(sys.argv[1]).resolve();m=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert m['estado']=='completo_verificado'
    assert json.loads((out/'verificacion_independiente.json').read_text())['estado']=='verificado'
    summary=pd.read_csv(out/'comparacion_media5.csv').set_index('variante')
    individual=pd.read_csv(out/'resultados_semillas.csv')
    seeds=m['firma']['seeds'];variants=list(LABELS)
    pivot=individual.pivot(index='seed',columns='variante',values='ganancia').loc[seeds,variants]
    colors=['#4d6474','#b44b48','#2971a2','#318363','#ab8132']
    fig,axes=plt.subplots(1,2,figsize=(13,5.4),layout='constrained')
    for i,v in enumerate(variants):
        axes[0].scatter(np.full(5,i)+np.linspace(-.12,.12,5),pivot[v]/4e6,color=colors[i],s=34,alpha=.65)
        axes[0].scatter(i,summary.loc[v,'ganancia']/4e6,color=colors[i],s=100,marker='D',edgecolor='white',zorder=3)
    axes[0].axhline(258368000/4e6,color=colors[0],linestyle='--',linewidth=1)
    axes[0].set(xticks=range(5),xticklabels=[LABELS[v] for v in variants],ylabel='25% de ganancia local ($ millones)',
                title='Puntos: semillas; rombo: media de cinco listas')
    axes[0].tick_params(axis='x',labelrotation=28)
    for i,v in enumerate(variants[1:],1):
        axes[1].plot(range(5),(pivot[v]-pivot.control_entrega8)/1e6,marker='o',color=colors[i],label=LABELS[v])
    axes[1].axhline(0,color=colors[0],linestyle='--',linewidth=1)
    axes[1].set(xticks=range(5),xticklabels=[str(s) for s in seeds],ylabel='Diferencia de ganancia total ($ millones)',
                xlabel='Semilla fija',title='Cambio frente al control de la misma semilla')
    axes[1].tick_params(axis='x',labelrotation=28)
    axes[1].secondary_yaxis('right',functions=(lambda a:a/4,lambda a:a*4)).set_ylabel('25% de la diferencia ($ millones)')
    axes[1].legend(fontsize=8,loc='lower right')
    for ax in axes:
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Abril → mayo · LightGBM combinado + TabPFN BAJA+2 · 50/50 · corte >2,5%')
    fig.savefig(out/'comparacion_features.png',dpi=160);plt.close(fig)
    report=['# Mini informe: cuatro pruebas locales de features','',
        '**Resultado: conservar las variaciones relativas de un mes y quitar los 13 resúmenes de hasta tres meses es la mejor variante de esta tanda.** LightGBM pasa de 202 a 189 variables; TabPFN mantiene sus 202 variables y predicciones guardadas. La mejora aparece en las cinco semillas y en las cuatro partes de mayo. No se generó otra entrega al Bot.','',
        '| Prueba | Variables LightGBM | Ganancia total media | 25% | Diferencia total | 25% de diferencia | Semillas mejores | Partes de mayo mejores |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for v,r in summary.iterrows():
        report.append(f'| {LABELS[v]} | {int(r.features)} | {money(r.ganancia)} | {money(r.ganancia_25pct)} | {money(r.delta_total)} | {money(r.delta_25pct)} | {int(r.semillas_mejoran)}/5 | {int(r.partes_mejoran)}/4 |')
    report+=['','Métrica principal: media de ganancias de **cinco listas individuales**. La ganancia de una única lista construida con el promedio de probabilidades se guarda separadamente en [lista_promedio5.csv](lista_promedio5.csv); no se usa para elegir ganadores de esta tanda.','',
        '![Comparación de features](comparacion_features.png)','',
        '## Qué cambió y qué significa','',
        '- **Préstamos personales, 202→200:** se retiraron solo `cprestamos_personales` y `mprestamos_personales`. Perdió en 5/5 semillas. Aunque había una indicación de drift en un script docente, esta ablación no justifica eliminarlas del modelo actual.','',
        '- **Rangos mensuales, 202→205:** se añadieron `rango_mensual_mpayroll`, `rango_mensual_mcuentas_saldo` y `rango_mensual_mrentabilidad`, conservando sus originales. Mejoró 4/5 semillas; la semilla 541440 perdió. Los rangos usan cada población mensual completa y sus valores no nulos, sin etiquetas: rango medio para empates dividido por cantidad no nula; nulos preservados, ceros y negativos válidos. No se combinó este cambio con la reducción histórica.','',
        '- **Historia de un mes, 202→189:** se quitaron `historial_meses_previos_3` y las columnas `media_previa_3_*`, `delta_media_previa_3_*`, `observaciones_previas_3_*` de las cuatro fuentes base. Quedan 152 originales y 37 históricas: 12 lags, 12 deltas, 12 relativos y disponibilidad del mes anterior. Mejoró 5/5 semillas y 4/4 partes.','',
        '- **Un mes sin relativos, 202→177:** además de las 13 anteriores, se quitaron las 12 `variacion_relativa_1_*`. Mejoró frente al control, pero rindió menos que 189. Dentro de esta tanda, conviene conservar los relativos.','',
        '## De dónde viene la mejora de 189','',
        '| Dato medio de cinco listas | Control 202 | Historia un mes 189 | Cambio |',
        '| --- | ---: | ---: | ---: |']
    base=summary.loc['control_entrega8'];best=summary.loc['historia_1_mes']
    for c,label in [('contactos','Contactos'),('tp','BAJA+2 contactados'),('fp','Falsos positivos'),('fn','BAJA+2 no contactados')]:
        report.append(f'| {label} | {base[c]:.1f} | {best[c]:.1f} | {best[c]-base[c]:+.1f} |')
    report+=['',
        'Se contactan en promedio **7,6 BAJA+2 adicionales** y **3,6 falsos positivos adicionales**. La mejora neta es '+money(best.delta_total)+' total, cuyo 25% es '+money(best.delta_25pct)+'. La métrica paga $1.072.500 por BAJA+2 contactado y resta $27.500 por los demás, incluyendo BAJA+1.','',
        '## Protocolo y límites','',
        'Entrenamiento abril de 2021: 163.284 clientes; evaluación mayo: 163.768, con 870 BAJA+2. Marzo aporta solo historia; sus etiquetas no se extraen. Junio y agosto no se leen. Target LightGBM BAJA+1/BAJA+2; target TabPFN guardado BAJA+2; mezcla 50/50 y corte estricto >0,025. Esta mezcla sigue siendo un score de targets distintos, no una probabilidad calibrada de BAJA+2.','',
        'Mismos parámetros LightGBM trial6/273 árboles: num_leaves66, learning_rate0,0653221892, min_data_in_leaf452, feature_fraction0,162827866, bagging_fraction0,8281386633, max_bin31, bagging_freq1, determinismo y CPU4. Sin búsqueda de hiperparámetros, early stopping, selección de corte ni ajuste de pesos. Semillas541440/408476/741961/248865/717444. Cada variante parte del control original; no se acumulan cambios.','',
        'Mayo y estas semillas ya fueron usados para decisiones anteriores. Las partes son grupos de clientes del mismo mes, no nuevos meses independientes. Cambiar la cantidad de features cambia también qué columnas se muestrean; el resultado no prueba causalmente que los resúmenes generen overfitting. La cobertura de historia de abril/mayo es menor que la disponible para agosto; la transferencia de esta mejora sigue sin comprobarse.','',
        '## Cómo seguir','',
        'Primero revisar el resultado de CatBoost de la entrega 15, que ya está preparada. Para la siguiente prueba del Bot, el candidato respaldado por esta tanda es **LightGBM189 + TabPFN202 al 50/50**, entrenando LightGBM final con abril+mayo y reutilizando TabPFN de entrega8. Falta ese entrenamiento final y la creación/verificación de una nueva carpeta numerada: este informe no es una entrega preparada.','',
        'Una prueba local posterior posible es agregar los tres rangos a la versión189 (192 variables). No se ejecutó esa combinación ni se supone que las mejoras se sumen. CatBoost Optuna, vínculos recurrentes y candidato de targets invertidos reservado para última hora siguen pendientes.','',
        '## Trazabilidad','',
        'Veinte nuevos fits LightGBM, cero API/créditos/submits. Se conservaron modelos, predicciones, matrices/targets identificados por hashes y parámetros en [manifest.json](manifest.json). [verificacion_independiente.json](verificacion_independiente.json) confirma reproducción desde datos originales de 20 modelos nuevos y cinco controles, rangos calculados también por frecuencias, 25 ganancias individuales, 100 resultados por partes, 25 cambios de contactos y cinco listas de promedio de probabilidades.','',
        'Resultados detallados: [resultados_semillas.csv](resultados_semillas.csv), [comparacion_media5.csv](comparacion_media5.csv), [resultados_partes_mayo.csv](resultados_partes_mayo.csv), [cambios_contactos.csv](cambios_contactos.csv). Fuente local: modelos de validación/predicciones de entrega7, misma configuración que el control de entrega8. Fuentes anteriores y entrega15 preservadas.']
    (out/'MINI_INFORME.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    (out/'INFORME.md').write_text('Ver [MINI_INFORME.md](MINI_INFORME.md) para resultados y límites.\n',encoding='utf-8')
    m['informe_sha256']=hashlib.sha256((out/'MINI_INFORME.md').read_bytes()).hexdigest()
    m['grafico_sha256']=hashlib.sha256((out/'comparacion_features.png').read_bytes()).hexdigest()
    m['codigo_informe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    m['decision']='Mejor local historia_1_mes189; entrenamiento final/CSV pendientes. No enviar automaticamente al Bot.'
    (out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Mini informe y grafico:',out,flush=True)


if __name__=='__main__':
    main()
