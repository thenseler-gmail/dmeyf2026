"""Espera el scoring final verificado y prepara/verifica diez entregas topN."""
import argparse
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
import psutil

TP=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--salida',type=Path,required=True);args=ap.parse_args()
out=args.salida.resolve();state=out/'preparacion_submits_estado.json'
def save(status,**extra):
    state.write_text(json.dumps(dict(estado=status,api=False,creditos=0,enviado_bot=False,**extra),indent=2)+'\n',encoding='utf-8')
save('esperando_scoring_final')
try:
    while not (out/'final_estado.json').exists():
        continuation=json.loads((out/'continuacion_estado.json').read_text(encoding='utf-8'))
        if continuation['estado'].startswith('error') or continuation['estado']=='optuna_termino_sin_resultado':
            raise RuntimeError('La continuación local falló: '+str(continuation))
        alive=False
        for proc in psutil.process_iter(['name','cmdline']):
            try:
                argv=proc.info['cmdline'] or []
                if proc.info['name'].lower().startswith('python') and any(Path(a).name=='95_continuar_catedra.py' for a in argv):alive=True
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        if not alive:raise RuntimeError('No hay proceso de continuación activo; no generar candidatos incompletos')
        time.sleep(10)
    save('preparando_entregas')
    subprocess.run([sys.executable,str(TP/'106_preparar_cortes_optuna.py'),'--salida',str(out)],check=True,cwd=TP.parent)
    batch=json.loads((out/'entregas_cortes.json').read_text(encoding='utf-8'))
    for entry in batch['entregas']:
        delivery=TP.parent/entry['carpeta']
        destination=out/'verificacion_reproduccion'/str(entry['entrega'])
        subprocess.run([sys.executable,str(delivery/'codigo/reproducir_csv.py'),'--salida',str(destination)],check=True,cwd=TP.parent)
    save('diez_entregas_completas_verificadas',entregas=batch['entregas'])
    config=TP/'config_validacion_lightgbm.json'
    meta=json.loads(config.read_text(encoding='utf-8'))
    meta['pruebas_optuna_submits'].update(estado='diez_entregas_completas_verificadas',
           entregas=batch['entregas'],informe=str((out/'PLAN_SUBMITS.md').relative_to(TP.parent)))
    config.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Diez candidatos listos, un corte por entrega, CSV reproducidos exactamente. No envío al Bot.',flush=True)
except Exception as e:
    save('error_preparacion',error=str(e));raise
