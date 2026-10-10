"""Archiva versiones firmadas de código por entrega, sin tocar CSV/modelos/manifiesto."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

TP=Path(__file__).resolve().parent
ROOT=TP.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archivar(entrega, adicionales=()):
    entrega=Path(entrega).resolve()
    assert entrega.is_relative_to(TP/'salidas/01_entregas_bot')
    manifest=entrega/'manifest.json'
    meta=json.loads(manifest.read_text(encoding='utf-8-sig'))
    folder=entrega/'codigo';folder.mkdir(exist_ok=True)
    signed={};sources=[];visited=set()
    def inspect(path):
        path=path.resolve()
        if path in visited or not path.is_relative_to(ROOT) or not path.exists():return
        visited.add(path)
        content=json.loads(path.read_text(encoding='utf-8-sig'))
        sources.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
        def walk(x):
            if isinstance(x,dict):
                for key,value in x.items():
                    if key.endswith('.py') and isinstance(value,str) and len(value)==64:
                        candidate=ROOT/key if (ROOT/key).exists() else TP/Path(key).name
                        signed[(str(candidate),value)]=path
                    elif key.endswith('manifest.json') and isinstance(value,str) and len(value)==64:
                        candidate=ROOT/key
                        if candidate.exists() and sha(candidate)==value:inspect(candidate)
                    elif isinstance(value,str) and (key.startswith('fuente') or key.startswith('source')):
                        candidate=ROOT/value
                        if candidate.is_dir():candidate=candidate/'manifest.json'
                        if candidate.name=='manifest.json' and candidate.exists():inspect(candidate)
                    else:walk(value)
            elif isinstance(x,list):
                for value in x:walk(value)
        walk(content)
    inspect(manifest)
    records=[]
    for (candidate,expected),source in sorted(signed.items()):
        path=Path(candidate)
        verified=path.exists() and sha(path)==expected
        record=dict(origen=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    sha256_historico=expected,fuente_firma=str(source.relative_to(ROOT)),
                    estado='version_historica_verificada' if verified else 'no_recuperada_no_coincide')
        if verified:
            target=folder/path.name
            if target.exists() and sha(target)!=expected:
                target=folder/(path.stem+'_'+expected[:12]+path.suffix)
            shutil.copy2(path,target)
            assert sha(target)==expected
            record['copia']=str(target.relative_to(entrega))
        records.append(record)
    for name in adicionales:
        path=TP/name
        assert path.is_file() and path.suffix=='.py'
        if any(r.get('copia')=='codigo/'+name for r in records):continue
        target=folder/'capturados_al_archivar'/name;target.parent.mkdir(exist_ok=True)
        if target.exists() and sha(target)!=sha(path):
            target=target.with_name(path.stem+'_'+sha(path)[:12]+path.suffix)
        shutil.copy2(path,target)
        records.append(dict(origen=str(path.relative_to(ROOT)),copia=str(target.relative_to(entrega)),
             sha256=sha(target),estado='capturado_al_archivar_sin_firma_historica'))
    shutil.copy2(manifest,folder/'manifest_capturado.json')
    shutil.copy2(TP/'105_reproducir_csv_entrega.py',folder/'reproducir_csv.py')
    effective={k:v for k,v in meta.items() if k in ['firma','train_final','train','futuro','prediccion',
       'semillas','pesos','umbral','operador','target_lightgbm','target_tabpfn','features_lightgbm','features_tabpfn']}
    (folder/'configuracion_registrada.json').write_text(json.dumps(effective,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive=dict(estado='archivado',entrega=entrega.name,fuentes=sources,archivos=records,
        manifest_original_sha256=sha(manifest),reproductor_csv_sha256=sha(folder/'reproducir_csv.py'),
        limitacion='Copias firmadas exactas cuando existe versión coincidente. Dependencias externas y datos no se duplican. '
                   'Archivos capturados sin firma histórica se identifican por separado. No copia credenciales.')
    (folder/'inventario_codigo.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text=['# Código de '+entrega.name,'',
          'Los scripts copiados directamente en esta carpeta coinciden con los hashes históricos de los manifiestos. '
          'inventario_codigo.json detalla archivos y origen de cada firma. Los adicionales sin firma histórica '
          'se guardan separadamente en capturados_al_archivar.','',
          '## Regenerar los CSV sin entrenamiento','',
          'Desde la raíz del proyecto, usar la herramienta sobre las predicciones y el manifiesto de esta entrega. '
          'Exige una salida distinta y verifica los hashes de las listas originales. No llama APIs.','',
          '```powershell',
          '.\\.venv\\Scripts\\python.exe "'+str((folder/'reproducir_csv.py').relative_to(ROOT))+'" --salida "tp_primera_entrega/salidas/reproduccion_'+str(meta.get('entrega',entrega.name.split('_')[0]))+'"',
          '```','',
          '## Código del entrenamiento original','',
          'Las copias conservan el contenido original, incluidas sus rutas relativas basadas en __file__. '
          'Para ejecutar esos scripts hay que restaurar la estructura original tp_primera_entrega en un checkout '
          'separado y conservar dataset, versiones y artefactos fuente referidos en el manifiesto. '
          'Copiar sólo el script no convierte el entrenamiento en un paquete autónomo. '
          'Auditorías originales pueden exigir manifiestos en su estado previo al envío (pre_envio). '
          'Reentrenar TabPFN puede consumir créditos; el reproductor de CSV evita ese paso.','',
          'configuracion_registrada.json contiene datos del manifiesto, no el config actual del proyecto. '
          'No se modificaron modelos, predicciones, adjuntos ni manifiesto original al archivar.']
    (folder/'README.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    return archive


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--entrega',type=Path,required=True)
    ap.add_argument('--adicional',action='append',default=[]);args=ap.parse_args()
    result=archivar(args.entrega,args.adicional)
    print(json.dumps(dict(entrega=result['entrega'],archivos=len(result['archivos'])),ensure_ascii=False))
