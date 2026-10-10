"""Reproduce OOF, clientes excluidos, errores y ganancias de la auditoria."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from baseline import preparar
from features_trayectorias import FEATURES,FUENTES,KEYS,agregar_trayectorias


def main():
    root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);m=json.loads((out/'manifest.json').read_text())
    assert m['estado']=='completo' and m['entrenamientos_nuevos']==40 and m['creditos']==0
    for n,h in m['archivos_sha256'].items():assert hashlib.sha256((out/n).read_bytes()).hexdigest()==h
    config=json.loads((root/'tp_primera_entrega/config.json').read_text())
    datos,cols=importlib.import_module('33_reentrenar_lightgbm_haberes').cargar_desarrollo(config)
    new=agregar_trayectorias(datos[KEYS+FUENTES])
    datos=datos.merge(new,on=KEYS,validate='one_to_one',sort=False)
    groups=pd.read_csv(out/'asignacion_folds.csv')
    pd.testing.assert_frame_equal(datos[KEYS+['clase_ternaria']],groups[KEYS+['clase_ternaria']])
    assert groups.groupby('numero_de_cliente').fold_cliente.nunique().max()==1
    folds=groups.fold_cliente.to_numpy();may=datos.loc[datos.foto_mes.eq(202105)].reset_index(drop=True)
    source=pd.read_csv(m['fuente_errores']);assert hashlib.sha256(Path(m['fuente_errores']).read_bytes()).hexdigest()==m['fuente_sha256']
    pd.testing.assert_frame_equal(may[KEYS+['clase_ternaria']],source[KEYS+['clase_ternaria']])
    selected=source.probabilidad>.025;y=may.clase_ternaria.eq('BAJA+2')
    error=np.select([selected&y,selected&~y,~selected&y],['TP','FP','FN'],default='TN')
    expected=pd.DataFrame({'grupo_error':error,'clase_ternaria':may.clase_ternaria}).groupby(['grupo_error','clase_ternaria']).size().reset_index(name='clientes')
    pd.testing.assert_frame_equal(expected,pd.read_csv(out/'conteo_errores.csv'))
    allx=preparar(datos,cols+FEATURES)[0]
    comparison=pd.read_csv(out/'comparacion.csv');singles=pd.read_csv(out/'resultados_semillas.csv')
    audit=json.loads((out/'auditoria_fits.json').read_text());assert len(audit)==40
    def check(p,row):
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        sel=np.asarray(p)>.025;truth=y.to_numpy()
        tp=int((sel&truth).sum());fp=int((sel&~truth).sum());gain=tp*1072500-fp*27500
        assert (row.contactos,row.tp,row.fp,row.ganancia,row.ganancia_25pct)==(tp+fp,tp,fp,gain,gain/4)
    reproduced=0
    for variant,columns in [('control',cols),('trayectorias',cols+FEATURES)]:
        oof=pd.read_csv(out/f'oof_{variant}_mayo.csv')
        pd.testing.assert_frame_equal(oof[KEYS+['clase_ternaria']],may[KEYS+['clase_ternaria']])
        for seed in m['semillas']:
            prob=np.full(len(datos),np.nan)
            for fold in range(4):
                it=np.flatnonzero(datos.foto_mes.isin([202104,202105]).to_numpy()&(folds!=fold))
                iv=np.flatnonzero(datos.foto_mes.eq(202105).to_numpy()&(folds==fold))
                assert set(datos.numero_de_cliente.iloc[it]).isdisjoint(set(datos.numero_de_cliente.iloc[iv]))
                a=next(a for a in audit if (a['variante'],a['seed'],a['fold'])==(variant,seed,fold))
                assert (a['filas_train'],a['filas_eval'])==(len(it),len(iv))
                model=lgb.Booster(model_file=str(out/'modelos'/f'{variant}_{seed}_{fold}.txt'))
                assert model.feature_name()==columns and model.num_trees()==273
                prob[iv]=model.predict(allx.iloc[iv][columns],validate_features=True);reproduced+=1
            np.testing.assert_allclose(prob[datos.foto_mes.eq(202105)],oof[f'p_seed{seed}'],rtol=0,atol=1e-15)
            r=singles.loc[singles.variante.eq(variant)&singles.seed.eq(seed)].iloc[0];check(oof[f'p_seed{seed}'],r)
        np.testing.assert_allclose(oof.probabilidad,oof[[f'p_seed{s}' for s in m['semillas']]].mean(axis=1),rtol=0,atol=1e-15)
        check(oof.probabilidad,comparison.loc[comparison.variante.eq(variant)].iloc[0])
    # Alterar un mes futuro no debe cambiar los features de meses anteriores.
    changed=datos[KEYS+FUENTES].copy();changed.loc[changed.foto_mes.eq(202105),FUENTES]=999
    altered=agregar_trayectorias(changed)
    pd.testing.assert_frame_equal(new.loc[new.foto_mes.le(202104)].reset_index(drop=True),altered.loc[altered.foto_mes.le(202104)].reset_index(drop=True))
    v=dict(estado='verificado',modelos_oof_reproducidos=reproduced,ganancias_individuales=10,ensembles=2,grupos_sin_solapamiento=True,sin_influencia_futura=True,api=False,creditos=0)
    (out/'verificacion.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(v)


if __name__=='__main__':main()
