"""Correccion logistica de dos probabilidades: ajuste mayo, evaluacion junio."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold,cross_val_predict
from sklearn.metrics import brier_score_loss,log_loss,roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
SAL=ROOT/'tp_primera_entrega/salidas'


def transformar(df):
    p=np.clip(df[['p_lightgbm','p_tabpfn']].to_numpy(),1e-7,1-1e-7)
    return np.log(p/(1-p))


def evaluar(df,p):
    y=df.clase_ternaria.eq('BAJA+2').to_numpy()
    seleccion=np.asarray(p)>0.025
    tp=int((y & seleccion).sum()); n=int(seleccion.sum())
    g=tp*1072500-(n-tp)*27500
    return dict(contactos=n,tp=tp,fp=n-tp,fn=int(y.sum())-tp,ganancia=g,ganancia_25pct=g/4,
        brier=float(brier_score_loss(y,p)),log_loss=float(log_loss(y,p)),auc=float(roc_auc_score(y,p)))


def bins(df,p):
    t=pd.DataFrame({'pred':p,'y':df.clase_ternaria.eq('BAJA+2').astype(int)})
    t['bin']=pd.qcut(t.pred,15,duplicates='drop')
    return t.groupby('bin',observed=True).agg(pred=('pred','mean'),real=('y','mean'),n=('y','size'),positivos=('y','sum')).reset_index(drop=True)


def main():
    out=SAL/datetime.now(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('calibracion_%Y%m%d_%H%M%S')
    out.mkdir()
    maypath=SAL/'revision_umbral_20261005_131001/2_lgbm_catedra_hist_20261004_225654_bajas_trial6_mayo.csv'
    tabpath=SAL/'tabpfn_historicas_20261004_165442_887149/predicciones.csv'
    junpath=SAL/'ensemble_junio_20261005_131355/predicciones_junio.csv'
    mayo=pd.read_csv(maypath).rename(columns={'p_promedio':'p_lightgbm'})
    tab=pd.read_csv(tabpath)[['numero_de_cliente','foto_mes','clase_ternaria','p_historicas']].rename(columns={'p_historicas':'p_tabpfn'})
    mayo=mayo.merge(tab,on=['numero_de_cliente','foto_mes'],validate='one_to_one',suffixes=('','_tab'))
    assert len(mayo)==len(tab)==163768 and mayo.clase_ternaria.eq(mayo.clase_ternaria_tab).all()
    mayo['mezcla_probabilidades']=(mayo.p_lightgbm+mayo.p_tabpfn)/2
    junio=pd.read_csv(junpath)
    assert len(junio)==164114 and junio.foto_mes.eq(202106).all()
    modelo=make_pipeline(StandardScaler(),LogisticRegression(C=1,solver='lbfgs',max_iter=1000,random_state=214363))
    protocolo=dict(estado='iniciado',entrenamiento_calibrador=202105,evaluacion=202106,
        metodo='Regresion logistica sobre logit de probabilidades LightGBM y TabPFN; StandardScaler; C=1; sin balanceo ni busqueda',
        umbral=0.025,operador='>',fuentes=[str(maypath),str(tabpath),str(junpath)],
        notas='Correccion supervisada de dos eventos diferentes; no descompone explicitamente BAJA+1. Mayo reutilizado para seleccionar LightGBM, OOF solo del calibrador. Junio expuesto y exploratorio. Mayo LightGBM tres semillas y junio veinte; entrenamientos base diferentes entre meses.')
    def save():
        (out/'manifest.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    save()
    y=mayo.clase_ternaria.eq('BAJA+2').astype(int)
    x=transformar(mayo)
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=214363)
    mayo['p_corregida_oof']=cross_val_predict(modelo,x,y,cv=cv,method='predict_proba',n_jobs=1)[:,1]
    modelo.fit(x,y)
    junio['p_corregida']=modelo.predict_proba(transformar(junio))[:,1]
    joblib.dump(modelo,out/'calibrador.joblib')
    resultados=[]
    for mes,df,cor in [('mayo_oof',mayo,'p_corregida_oof'),('junio',junio,'p_corregida')]:
        for etiqueta,col in [('TabPFN','p_tabpfn'),('LightGBM combinado','p_lightgbm'),('Promedio 50/50','mezcla_probabilidades'),('Correccion aprendida',cor)]:
            resultados.append(dict(mes=mes,modelo=etiqueta,**evaluar(df,df[col])))
    pd.DataFrame(resultados).to_csv(out/'comparacion.csv',index=False)
    mayo.to_csv(out/'predicciones_mayo.csv',index=False)
    junio.to_csv(out/'predicciones_junio.csv',index=False)
    colores=['#3575c4','#e29427']
    fig,axs=plt.subplots(1,2,figsize=(13,5.4),layout='constrained')
    for ax,mes,df,cor in [(axs[0],'Mayo: correccion fuera de muestra',mayo,'p_corregida_oof'),(axs[1],'Junio: comprobacion posterior',junio,'p_corregida')]:
        for label,col,color in [('Promedio 50/50','mezcla_probabilidades',colores[0]),('Correccion aprendida',cor,colores[1])]:
            b=bins(df,df[col]); b.to_csv(out/(mes[:5].strip()+'_'+col+'_bins.csv'),index=False)
            ax.plot(b.pred*100,b.real*100,'o-',label=label,color=color)
        lim=max(ax.get_xlim()[1],ax.get_ylim()[1],3)
        ax.plot([0,lim],[0,lim],'--',color='#777777',label='Prediccion = frecuencia real')
        ax.axvline(2.5,color='#777777',alpha=.5)
        ax.set(xlabel='Probabilidad estimada media (%)',ylabel='BAJA+2 realmente observados (%)',title=mes,xlim=(0,lim),ylim=(0,lim))
        ax.grid(alpha=.2); ax.legend(fontsize=9)
    fig.suptitle('¿El puntaje coincide con la frecuencia real de BAJA+2?',fontsize=15)
    fig.savefig(out/'calibracion.png',dpi=160); plt.close(fig)
    # Frecuencia real segun ambas señales, sin atribuir BAJA+1 a un cliente.
    bordes=[0,.005,.01,.025,.05,.10,1.000001]
    etiquetas=['<0,5%','0,5–1%','1–2,5%','2,5–5%','5–10%','≥10%']
    t=mayo.copy(); t['l']=pd.cut(t.p_lightgbm,bordes,labels=etiquetas,right=False)
    t['t']=pd.cut(t.p_tabpfn,bordes,labels=etiquetas,right=False)
    g=t.groupby(['t','l'],observed=False).clase_ternaria.agg(n='size',baja2=lambda s:int(s.eq('BAJA+2').sum()))
    rates=(g.baja2/g.n*100).unstack('l').reindex(index=etiquetas,columns=etiquetas)
    counts=g.n.unstack('l').reindex(index=etiquetas,columns=etiquetas)
    g.to_csv(out/'frecuencias_dos_senales.csv')
    fig,ax=plt.subplots(figsize=(10,7),layout='constrained')
    im=ax.imshow(rates.to_numpy(),origin='lower',cmap='YlOrRd',aspect='auto')
    for i in range(6):
        for j in range(6):
            n=counts.iloc[i,j]; v=rates.iloc[i,j]
            if n:
                ax.text(j,i,f'{v:.1f}%\nn={int(n):,}',ha='center',va='center',fontsize=10,color='black',bbox=dict(facecolor='white',alpha=.65,edgecolor='none'))
    ax.set_xticks(range(6),etiquetas); ax.set_yticks(range(6),etiquetas)
    ax.set(xlabel='Probabilidad LightGBM: BAJA+1 o BAJA+2',ylabel='Probabilidad TabPFN: BAJA+2',title='Mayo: porcentaje real de BAJA+2 en cada grupo\nGrupos pequeños: estimaciones menos estables')
    fig.colorbar(im,ax=ax,label='BAJA+2 observados (%)')
    fig.savefig(out/'dos_senales.png',dpi=160); plt.close(fig)
    protocolo.update(estado='completo',resultados=resultados,coeficientes_estandarizados=modelo[-1].coef_.tolist(),intercepto=modelo[-1].intercept_.tolist())
    save()
    print(pd.DataFrame(resultados).to_string(index=False))
    print('Salida:',out)


if __name__=='__main__':
    main()
