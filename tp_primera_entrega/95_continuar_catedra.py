"""Completa etapas locales cuando termina Optuna; sin inferencias API ni submits."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True)
ap.add_argument('--pid-optuna',type=int,required=True);args=ap.parse_args()
out=args.salida.resolve();tp=Path(__file__).resolve().parent
state=out/'continuacion_estado.json'
def save(estado,**kw):
    state.write_text(json.dumps(dict(estado=estado,api=False,creditos=0,submits=0,**kw),indent=2)+'\n',encoding='utf-8')
save('esperando_optuna')
while not (out/'optuna_estado.json').exists():
    import psutil
    if not psutil.pid_exists(args.pid_optuna):
        save('optuna_termino_sin_resultado');raise RuntimeError('Optuna no completó su estado; revisar proceso/log')
    time.sleep(10)
steps=[('94_verificar_catedra.py',[]),('96_control_temporal_catedra.py',[]),
       ('93_reentrenar_control16_orden2.py',[]),('89_catedra_pipeline.py',['--etapa','final']),
       ('98_preparar_tabpfn226_final.py',[])]
complete=[]
try:
    for script,extra in steps:
        save('ejecutando',script=script,completadas=complete)
        print('Etapa:',script,flush=True)
        subprocess.run([sys.executable,str(tp/script),'--salida',str(out),*extra],check=True,cwd=tp.parent)
        complete.append(script)
    if (out/'predicciones_tab226_mayo.csv').exists():
        subprocess.run([sys.executable,str(tp/'97_evaluar_tabpfn226.py'),'--salida',str(out)],check=True,cwd=tp.parent)
        complete.append('97_evaluar_tabpfn226.py')
    import importlib
    sys.path.insert(0,str(tp))
    pipe=importlib.import_module('89_catedra_pipeline');pipe.informe(out)
    with (out/'MINI_INFORME.md').open('a',encoding='utf-8') as f:
        f.write('\n## Cobertura temporal\n\nMarzo y abril no tienen historia de orden2 en el dataset. '
                'La búsqueda marzo+abril a mayo no puede aprender esos24 predictores. '
                'El diagnóstico por clientes de mayo y el fit final que incluye mayo/junio sí tienen '
                'valores observables. No atribuir el resultado del backtest abril a mayo al aporte aprendido '
                'de los lag2/delta2.\n')
        if (out/'INFORME_TABPFN226.md').exists():
            f.write('\n'+(out/'INFORME_TABPFN226.md').read_text(encoding='utf-8')+'\n')
        reference=out/'junio_diagnostico_referencia.json'
        if reference.exists():
            june=Path(json.loads(reference.read_text(encoding='utf-8'))['directorio'])
            f.write('\n'+(june/'MINI_INFORME.md').read_text(encoding='utf-8')+'\n')
        elif (out/'diagnostico_orden2/resumen.csv').exists():
            import pandas as pd
            f.write('\n## Diagnóstico por clientes mayo\n\n```text\n'+pd.read_csv(out/'diagnostico_orden2/resumen.csv').to_string(index=False)+'\n```\n')
            f.write('No es un test temporal ni usa TabPFN guardado incompatible con esa partición.\n')
        f.write('Controles16 actualizados y ensemble LightGBM final terminados. TabPFN final todavía guardado202 '
                'con ventana abril+mayo. No generar un submit automáticamente ni interpretar como ensemble '
                'con ambos modelos reentrenados.\n')
        f.write('\nPayloads finales TabPFN226 preparados para revisar ventana, cotización y autorización '
                'antes de cualquier inferencia.\n')
    save('etapas_locales_completas_tabpfn_pendiente',completadas=complete)
    print('Etapas locales completas. TabPFN pendiente de autorización/ejecución específica.',flush=True)
except Exception as e:
    save('error_etapa_local',completadas=complete,error=str(e));raise
