"""Validación descriptiva y estabilidad de k=5 para el TP de Miranda.

Ejecutar desde cualquier directorio con el entorno del proyecto:
  python validacion_clusters_k5_th.py
No modifica z501_cluster_rf.py. CSV UTF-8 BOM, separador coma, sin redondeo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import sklearn
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

import z501_cluster_rf as base
from z501_cluster_rf_th import cargar_diccionario

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "output/miranda_k5"
ID, MONTH, TARGET = base.ID_COL, base.MES_COL, base.TARGET_COL
SEED = 214363
CATS = ["Visa_status", "Master_status", "internet"]
BINARY = ["active_quarter", "cliente_vip", "ccaja_seguridad", "tcallcenter", "thomebanking", "tmobile_app", "Visa_delinquency", "Master_delinquency"]
STATUS = {0: "abierta", 6: "en proceso de cierre", 7: "cierre avanzado", 9: "cerrada"}
KEY = ["cliente_edad", "cliente_antiguedad", "cproductos", "active_quarter", "ctrx_quarter",
       "cpayroll_trx", "mpayroll", "mpayroll2", "mcuentas_saldo", "ctarjeta_visa", "ctarjeta_master",
       "mtarjeta_visa_consumo", "mtarjeta_master_consumo", "ctarjeta_visa_transacciones", "ctarjeta_master_transacciones",
       "ctarjeta_visa_debitos_automaticos", "mttarjeta_visa_debitos_automaticos",
       "ctarjeta_master_debitos_automaticos", "mttarjeta_master_debitos_automaticos",
       "chomebanking_transacciones", "cmobile_app_trx", "thomebanking", "tmobile_app",
       "mextraccion_autoservicio", "cextraccion_autoservicio", "mpagomiscuentas",
       "cprestamos_personales", "mprestamos_personales", "mrentabilidad", "mrentabilidad_annual",
       "mcomisiones_mantenimiento", "Visa_mlimitecompra", "Master_mlimitecompra",
       "Visa_delinquency", "Master_delinquency"]


def save(df, name):
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def representation(df, seed):
    feats = base.columnas_features(df)
    X = df[feats].to_numpy(dtype=np.float32)
    rf = base.entrenar_rf(X, df[base.GRUPO_COL].to_numpy(), 300, 50, seed)
    P = base.normalizar(base.contar_hojas_por_id(rf, X, df[ID].to_numpy(), feats))
    ids = df.loc[df[base.GRUPO_COL] == 1, ID].unique()
    return P.loc[ids], feats


def numeric_profiles(df, group_cols, features, dictionary, scope):
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        group = dict(zip(group_cols, keys))
        for var in features:
            if var in CATS:
                continue
            s = g[var].dropna()
            q = s.quantile([.25, .5, .75, .9])
            rows.append({"ambito": scope, **group, "variable": var, "descripcion": dictionary[var],
                         "n_clientes": g[ID].nunique(), "n_filas": len(g), "n_validos": len(s),
                         "n_faltantes": int(g[var].isna().sum()), "faltantes_pct": g[var].isna().mean()*100,
                         "media": s.mean(), "mediana": q.loc[.5], "p25": q.loc[.25], "p75": q.loc[.75],
                         "p90": q.loc[.9], "p95": s.quantile(.95), "p99": s.quantile(.99), "maximo": s.max(),
                         "minimo": s.min(), "pct_positivo_validos": (s > 0).mean()*100,
                         "pct_uno_validos": (s == 1).mean()*100 if var in BINARY else np.nan,
                         "n_uno": int((s == 1).sum()) if var in BINARY else np.nan})
    return pd.DataFrame(rows)


def categories(df, groups, scope):
    rows = []
    for keys, g in df.groupby(groups, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for var in CATS + ["Visa_delinquency", "Master_delinquency"]:
            values = g[var].map(lambda x: "FALTANTE" if pd.isna(x) else format(float(x), ".15g"))
            counts = values.value_counts()
            expected = ["0", "6", "7", "9", "FALTANTE"] if var.endswith("status") else ["0", "1", "FALTANTE"] if var.endswith("delinquency") else list(counts.index)
            # Mantener categorías observadas no previstas, y ceros explícitos para estados definidos.
            counts = counts.reindex(list(dict.fromkeys(expected + list(counts.index))), fill_value=0)
            for value, n in counts.items():
                meaning = "sin observación" if value == "FALTANTE" else (
                    STATUS.get(float(value), "código no definido") if var.endswith("status") else
                    ("mora" if float(value) == 1 else "sin mora" if float(value) == 0 else "código no definido")
                    if var.endswith("delinquency") else "codificación no explicada por el diccionario")
                rows.append({"ambito": scope, **dict(zip(groups, keys)), "variable": var, "valor": value,
                             "significado": meaning, "n": n, "denominador": len(g), "porcentaje": 100*n/len(g)})
    return pd.DataFrame(rows)


def paired(df, time_col, a, b, variables):
    left = df[df[time_col] == a].set_index(ID)
    right = df[df[time_col] == b].set_index(ID)
    common = left.index.intersection(right.index)
    rows = []
    for c in range(1, 6):
        ids = common[left.loc[common, "cluster"].eq(c)]
        for v in variables:
            s = pd.DataFrame({"a": left.loc[ids, v], "b": right.loc[ids, v]}).dropna()
            diff = s.b - s.a
            rows.append({"eje": time_col, "momento_a": a, "momento_b": b, "cluster": c, "variable": v,
                         "n_clientes_ambas_fotos": len(ids), "n_pares_validos": len(s),
                         "media_a": s.a.mean(), "media_b": s.b.mean(), "mediana_a": s.a.median(), "mediana_b": s.b.median(),
                         "media_cambio_individual": diff.mean(), "mediana_cambio_individual": diff.median(),
                         "pct_disminuye": (diff < 0).mean()*100, "pct_aumenta": (diff > 0).mean()*100,
                         "pct_negativo_a": (s.a < 0).mean()*100, "pct_negativo_b": (s.b < 0).mean()*100})
    return rows


def flags(df):
    def val(v):
        return df[v].astype("Float64")
    visa = val("ctarjeta_visa_transacciones") > 0
    debit = val("ctarjeta_visa_debitos_automaticos") > 0
    payroll = (val("cpayroll_trx") > 0) | (val("mpayroll") > 0) | (val("mpayroll2") > 0)
    low = (val("active_quarter") == 0) & (val("ctrx_quarter") <= 1)
    close = pd.Series(False, index=df.index, dtype="boolean")
    for v in ["Visa_status", "Master_status"]:
        flag = val(v).isin([6, 7, 9]).astype("boolean").mask(df[v].isna())
        close = close | flag
    mora = (val("Visa_delinquency") == 1) | (val("Master_delinquency") == 1)
    limits = (val("Visa_mlimitecompra") > 0) | (val("Master_mlimitecompra") > 0)
    no_card_use = (val("ctarjeta_visa_transacciones") == 0) & (val("ctarjeta_master_transacciones") == 0)
    return {
        "uso_visa": visa, "debitos_visa": debit, "haberes": payroll,
        "sin_haberes": ~payroll, "baja_actividad": low, "cierre_alguna_tarjeta": close,
        "mora_alguna_tarjeta": mora, "prestamos_positivos": val("cprestamos_personales") > 0,
        "deuda_positiva": val("mprestamos_personales") > 0, "rentabilidad_negativa": val("mrentabilidad") < 0,
        "C1_visa_debitos_sin_haberes": visa & debit & ~payroll,
        "C2_relacion_amplia": payroll & (val("mcuentas_saldo") > 0) &
            (visa | (val("ctarjeta_master_transacciones") > 0)) & (val("mpagomiscuentas") > 0) & (val("ctrx_quarter") > 1),
        "C3_productos_limites_poco_uso": (val("cproductos") >= 3) & limits & no_card_use & (val("ctrx_quarter") <= 1),
        "C4_baja_actividad_y_cierre": low & close,
        "C5_prestamos_deuda_y_perdida": (val("cprestamos_personales") > 0) & (val("mprestamos_personales") > 0) & (val("mrentabilidad") < 0),
    }


def flag_summary(df, groups, scope):
    f = pd.DataFrame(flags(df), index=df.index)
    rows = []
    for keys, g in df.groupby(groups):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for name in f:
            s = f.loc[g.index, name]
            rows.append({"ambito": scope, **dict(zip(groups, keys)), "rasgo": name,
                         "n_total": len(s), "n_evaluables": s.notna().sum(), "n_cumplen": s.sum(),
                         "n_desconocidos": s.isna().sum(), "pct_total": 100*s.sum()/len(s),
                         "pct_evaluables": 100*s.mean()})
    return pd.DataFrame(rows)


def concentration(s):
    s = s.dropna().sort_values(ascending=False)
    result = {"n": len(s), "total": s.sum(), "media": s.mean(), "mediana": s.median(),
              "p90": s.quantile(.9), "p95": s.quantile(.95), "p99": s.quantile(.99), "maximo": s.max()}
    for pct in [1, 5]:
        n = math.ceil(len(s)*pct/100)
        result.update({f"n_top{pct}": n, f"top{pct}_pct_total": s.iloc[:n].sum()/s.sum()*100 if s.sum() else np.nan,
                       f"media_sin_top{pct}": s.iloc[n:].mean(), f"mediana_sin_top{pct}": s.iloc[n:].median(),
                       f"n_sin_top{pct}": len(s)-n})
    return result


def compare_labels(ref, other, stage, seed):
    other = other.reindex(ref.index)
    assert other.notna().all()
    tab = pd.crosstab(ref.to_numpy(), other.to_numpy()).reindex(index=range(1,6), columns=range(1,6), fill_value=0)
    r, c = linear_sum_assignment(-tab.to_numpy())
    mapping = {int(tab.columns[j]): int(tab.index[i]) for i, j in zip(r,c)}
    aligned = other.map(mapping)
    summary = {"etapa": stage, "semilla": seed, "ARI": adjusted_rand_score(ref, other),
               "coincidencia_emparejada_pct": (aligned == ref).mean()*100}
    groups = []
    for k in range(1,6):
        a, b = ref.eq(k), aligned.eq(k)
        inter = int((a & b).sum())
        groups.append({"etapa": stage, "semilla": seed, "cluster_base": k, "n_base": int(a.sum()),
                       "n_otro": int(b.sum()), "interseccion": inter, "recuperacion_pct": inter/a.sum()*100,
                       "precision_pct": inter/b.sum()*100, "jaccard": inter/(a|b).sum(),
                       "cluster_original_otro": next(old for old,new in mapping.items() if new == k)})
    confusion = tab.rename_axis("cluster_base").reset_index()
    confusion.insert(0,"semilla", seed)
    confusion.insert(0,"etapa", stage)
    return summary, groups, confusion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reuse", action="store_true", help="Reutilizar muestra y representación si coinciden hashes y versiones")
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    data = ROOT / "data/competencia_01.csv"
    dictionary_path = ROOT / "dmeyf2026-9c6f_DiccionarioDatos_2026.ods"
    dic = cargar_diccionario(dictionary_path)
    meta = {"dataset": str(data), "sha256_dataset": sha(data), "sha256_original": sha(Path(base.__file__)),
            "diccionario": str(dictionary_path), "sha256_diccionario": sha(dictionary_path),
            "python": platform.python_version(), "sklearn": sklearn.__version__, "pandas": pd.__version__,
            "numpy": np.__version__, "duckdb": duckdb.__version__, "seed": SEED, "k":5,
            "n_trees":300, "min_samples_leaf":50, "KMeans_n_init":20}
    cache = OUT / "cache"
    cache.mkdir(exist_ok=True)
    if args.reuse and (cache / "meta.json").exists() and json.loads((cache/"meta.json").read_text()) == meta:
        df = pd.read_pickle(cache / "muestra.pkl")
        P = pd.read_pickle(cache / "representacion.pkl")
        feats = base.columnas_features(df)
    else:
        base.log("reproduciendo RF y representación original")
        df = base.cargar_muestra(data, SEED)
        P, feats = representation(df, SEED)
        df.to_pickle(cache / "muestra.pkl")
        P.to_pickle(cache / "representacion.pkl")
        (cache/"meta.json").write_text(json.dumps(meta), encoding="utf-8")
    assert set(feats) <= dic.keys()
    assert set(KEY) <= set(feats)
    labels = base.clusterizar(P, 5, SEED)
    sizes = labels.value_counts().sort_index()
    assert sizes.tolist() == [1281,1089,915,559,223], sizes
    save(labels.rename_axis(ID).reset_index(), "asignaciones_clientes")
    save(pd.DataFrame({"cluster":sizes.index,"n_clientes":sizes.values,"porcentaje_bajas":sizes.values/len(labels)*100}), "tamanos_clusters")
    save(P.reset_index(), "representacion_bosque")
    save([{"variable":v,"descripcion_diccionario":dic[v],"tratamiento":"categorica" if v in CATS else "binaria" if v in BINARY else "numerica"} for v in feats], "diccionario_variables")

    base.log("auditando dataset completo y cronología")
    con = duckdb.connect()
    con.read_csv(str(data), sample_size=-1).create_view("raw")
    audit = con.sql(f"SELECT count(*) filas, count(distinct {ID}) clientes, count(distinct ({ID},{MONTH})) claves_unicas FROM raw").df()
    audit["duplicados_cliente_mes"] = audit.filas - audit.claves_unicas
    save(audit,"auditoria_claves")
    assert audit.duplicados_cliente_mes.iloc[0] == 0
    save(con.sql(f"SELECT {MONTH}, {TARGET}, count(*) n FROM raw GROUP BY ALL ORDER BY 1,2").df(),"clases_dataset_por_mes")
    save(con.sql(f"SELECT {MONTH}, internet, count(*) n FROM raw GROUP BY ALL ORDER BY 1,2").df(),"internet_dataset_por_mes")
    h = df[df.grupo == 1].merge(labels, left_on=ID, right_index=True).copy()
    counts = h[h[TARGET].eq("BAJA+2")].groupby(ID).size()
    save(counts.rename("n_meses_baja2").rename_axis(ID).reset_index(), "unicidad_mes_baja2")
    assert len(counts) == len(labels) and counts.eq(1).all(), "BAJA+2 no único: requiere regla explícita"
    event = h[h[TARGET].eq("BAJA+2")][[ID, MONTH]].rename(columns={MONTH:"mes_baja2"})
    h = h.merge(event, on=ID)
    absolute = lambda s: (s//100)*12+s%100
    h["mes_relativo"] = absolute(h[MONTH])-absolute(h.mes_baja2)
    snap = h[h.mes_relativo.eq(0)].copy()
    assert len(snap) == len(labels) and snap[ID].is_unique
    save(h, "historia_segmentada")
    save(snap, "observaciones_mes_baja2")
    save(h.groupby(["cluster",MONTH,TARGET],dropna=False).size().rename("n").reset_index(),"historia_clases_mes")
    save(h.groupby(["cluster","mes_relativo",TARGET],dropna=False).size().rename("n").reset_index(),"historia_clases_relativas")
    per_client = h.sort_values(MONTH).groupby([ID,"cluster"]).agg(n_meses=(MONTH,"size"),primer_mes=(MONTH,"min"),ultimo_mes=(MONTH,"max"),
         meses=(MONTH,lambda s:";".join(map(str,s))),estados=(TARGET,lambda s:";".join(s.fillna("FALTANTE")))).reset_index()
    save(per_client,"historia_por_cliente")
    coverage = h.groupby(MONTH).agg(n_clientes=(ID,"nunique"),filas=(ID,"size")).reset_index()
    allmonths = con.sql(f"SELECT DISTINCT {MONTH} FROM raw ORDER BY 1").df()
    coverage = allmonths.merge(coverage,on=MONTH,how="left").fillna(0)
    save(coverage,"cobertura_historia_bajas")
    meta["exclusion_ultimo_mes_justificada"] = bool(coverage.iloc[-1].n_clientes == 0)

    base.log("calculando perfiles por mes calendario y respecto de BAJA+2")
    for table, groups, name in [(snap,["cluster"],"baja2"),(h,["cluster",MONTH],"mensual"),(h,["cluster","mes_relativo"],"relativo")]:
        save(numeric_profiles(table,groups,feats,dic,name),f"perfiles_{name}")
        save(categories(table,groups,name),f"categorias_{name}")
        save(flag_summary(table,groups,name),f"rasgos_{name}")
    pairs=[]
    for a,b in [(-2,-1),(-1,0),(0,1),(-2,0)]:
        pairs += paired(h,"mes_relativo",a,b,KEY)
    pairs += paired(h,MONTH,202106,202107,KEY)
    save(pairs,"cambios_pareados")
    # Recurrencia: al menos dos meses con uso Y débitos Visa en ventana [-2,0].
    f = flags(h)
    window = h[h.mes_relativo.between(-2,0)].copy()
    window["visa_y_debitos"] = (f["uso_visa"] & f["debitos_visa"]).loc[window.index]
    rec = window.groupby([ID,"cluster"]).agg(n_meses=(MONTH,"size"),n_evaluables=("visa_y_debitos","count"),
          n_meses_visa_debitos=("visa_y_debitos","sum")).reset_index()
    rec = rec.merge(snap[[ID]].assign(sin_haberes=flags(snap)["sin_haberes"].to_numpy()),on=ID)
    rec["recurrente_sin_haberes_baja2"] = (rec.n_meses_visa_debitos>=2)&rec.sin_haberes.astype("boolean")
    save(rec,"recurrencia_visa_cliente")

    # Cierres: primera observación, censura a izquierda y transiciones reales.
    onset=[]; transitions=[]
    for (client,c),g in h.sort_values(MONTH).groupby([ID,"cluster"]):
        for v in ["Visa_status","Master_status"]:
            valid = g[g[v].notna()]
            closed = valid[valid[v].isin([6,7,9])]
            onset.append({ID:client,"cluster":c,"variable":v,"n_observaciones_validas":len(valid),
                          "alguna_vez_cierre":bool(len(closed)),
                          "primer_cierre_relativo":closed.mes_relativo.iloc[0] if len(closed) else np.nan,
                          "primer_cierre_mes":closed[MONTH].iloc[0] if len(closed) else np.nan,
                          "ya_cierre_primera_observacion_valida":bool(len(closed) and closed.index[0]==valid.index[0])})
            for i in range(1,len(g)):
                a,b = g.iloc[i-1],g.iloc[i]
                if b.mes_relativo-a.mes_relativo != 1:
                    continue
                transitions.append({ID:client,"cluster":c,"variable":v,"mes_a":a[MONTH],"mes_b":b[MONTH],
                                    "relativo_a":a.mes_relativo,"relativo_b":b.mes_relativo,"estado_a":a[v],"estado_b":b[v],
                                    "mora_b":b[v.replace("status","delinquency")]})
    save(onset,"primer_cierre_por_cliente")
    trans = pd.DataFrame(transitions)
    save(trans,"transiciones_tarjetas")
    save(trans.groupby(["cluster","variable","relativo_a","relativo_b","estado_a","estado_b"],dropna=False).size().rename("n").reset_index(),"transiciones_tarjetas_resumen")

    concentration_rows=[]
    for scope,frame,tcol in [("baja2",snap,None),("mensual",h,MONTH),("relativo",h,"mes_relativo")]:
        for keys,g in frame.groupby(["cluster"]+([tcol] if tcol else [])):
            keys = keys if isinstance(keys,tuple) else (keys,)
            for v in ["cprestamos_personales","mprestamos_personales","mrentabilidad","mrentabilidad_annual"]:
                s = g[v]
                # Rentabilidad: concentración de pérdidas brutas, no neteo con ganancias.
                if v.startswith("mrentabilidad"):
                    s = (-s).clip(lower=0)
                concentration_rows.append({"ambito":scope,"cluster":keys[0],"momento":keys[1] if tcol else 0,
                                           "variable":v,"medida":"perdida_bruta" if v.startswith("mrentabilidad") else "valor_original",
                                           **concentration(s)})
    save(concentration_rows,"concentracion_y_sensibilidad")
    save(snap.groupby(["cluster","cprestamos_personales"],dropna=False).size().rename("n").reset_index(),"distribucion_numero_prestamos_baja2")
    # Descomposición exacta: cambio pareado + componente de composición.
    decomposition=[]; loss_rows=[]
    for c in range(1,6):
        g = h[h.cluster.eq(c)]
        a = g[g[MONTH].eq(202106)].set_index(ID).mrentabilidad.dropna()
        b = g[g[MONTH].eq(202107)].set_index(ID).mrentabilidad.dropna()
        ids = a.index.intersection(b.index)
        within = b.loc[ids].mean()-a.loc[ids].mean()
        composition = (b.mean()-b.loc[ids].mean())-(a.mean()-a.loc[ids].mean())
        decomposition.append({"cluster":c,"n_junio":len(a),"n_julio":len(b),"n_pares":len(ids),
                              "media_junio_todos":a.mean(),"media_julio_todos":b.mean(),
                              "cambio_media_todos":b.mean()-a.mean(),"cambio_mismos_clientes":within,
                              "componente_composicion":composition})
        assert np.isclose(b.mean()-a.mean(),within+composition)
        for month,s in [(202106,a.loc[ids]),(202107,b.loc[ids])]:
            loss_rows.append({"cluster":c,"mes":month,"n_pares":len(ids),"pct_negativos":(s<0).mean()*100,
                              "n_negativos":int((s<0).sum()),"rentabilidad_media":s.mean(),"rentabilidad_mediana":s.median(),
                              **{f"perdidas_{k}":v for k,v in concentration((-s).clip(lower=0)).items()}})
    save(decomposition,"rentabilidad_descomposicion_junio_julio")
    save(loss_rows,"perdidas_pareadas_junio_julio")

    base.log("estabilidad KMeans con representación fija y procedimiento completo")
    stability=[]; group_stability=[]; confusions=[]
    runs = {SEED:labels}
    for seed in [17,42,101,503,1009,2026,4099,8191,12347,65537]:
        other = base.clusterizar(P,5,seed)
        runs[seed] = other
        summary,groups,confusion = compare_labels(labels,other,"kmeans_matriz_fija",seed)
        stability.append(summary); group_stability.extend(groups); confusions.append(confusion)
    save([{"semilla_a":a,"semilla_b":b,"ARI":adjusted_rand_score(la,lb)}
          for a,la in runs.items() for b,lb in runs.items() if a < b],"estabilidad_ARI_todos_pares")
    assignments = pd.DataFrame({f"seed_{s}":v for s,v in runs.items()})
    save(assignments.rename_axis(ID).reset_index(),"asignaciones_semillas_kmeans")
    for seed in [17,42,2026]:
        # RF fijo en la misma muestra: aísla la variación del bosque.
        base.log(f"RF semilla {seed}: muestra fija")
        p_other,_ = representation(df,seed)
        other = base.clusterizar(p_other,5,SEED)
        summary,groups,confusion = compare_labels(labels,other,"bosque_muestra_fija",seed)
        stability.append(summary); group_stability.extend(groups); confusions.append(confusion)
        # Procedimiento completo: cambian muestra de fieles, RF y KMeans.
        base.log(f"procedimiento completo semilla {seed}")
        d_other = base.cargar_muestra(data,seed)
        p_other,_ = representation(d_other,seed)
        other = base.clusterizar(p_other,5,seed)
        summary,groups,confusion = compare_labels(labels,other,"procedimiento_completo",seed)
        stability.append(summary); group_stability.extend(groups); confusions.append(confusion)
    save(stability,"estabilidad_global")
    save(group_stability,"estabilidad_por_cluster")
    save(pd.concat(confusions,ignore_index=True),"estabilidad_confusiones")
    meta["tam_clusters"] = sizes.to_dict()
    meta["meses_historia_bajas"] = sorted(h[MONTH].unique().tolist())
    meta["n_observaciones_baja1"] = int(h[TARGET].eq("BAJA+1").sum())
    meta["n_clientes_baja2"] = len(labels)
    (OUT/"metadatos.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    base.log(f"tablas completas en {OUT}")


if __name__ == "__main__":
    main()
