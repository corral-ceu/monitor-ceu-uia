import numpy as np
import pandas as pd
import streamlit as st

from services.metrics import calc_var, fmt, obtener_nombre_mes
from services.sipa_data import cargar_sipa_excel


def render_empleo(go_to):
    if st.button("← Volver"):
        go_to("home")

    st.markdown("## 💼 Empleo Privado")
    st.caption("Fuente: SIPA – Trabajo registrado (Excel)")
    st.divider()

    with st.spinner("Cargando SIPA..."):
        df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa = cargar_sipa_excel()

    if df_total.empty:
        st.error("No se pudieron cargar los datos SIPA desde el Excel.")
        return

    ult_f = df_total["fecha"].iloc[-1]
    target_date = pd.Timestamp("2023-08-01")
    s_orig = df_total["orig"]
    s_sa = df_total["sa"]

    # Escala: miles vs puestos
    try:
        scale = 1000 if (pd.to_numeric(s_sa.dropna()).median() < 1_000_000) else 1
    except Exception:
        scale = 1000

    # Total
    m_e = calc_var(s_sa, 1)
    m_p = s_sa.diff().iloc[-1] * scale
    i_e = calc_var(s_orig, 12)
    i_p = s_orig.diff(12).iloc[-1] * scale

    try:
        val_23 = df_total.loc[df_total["fecha"] == target_date, "sa"].iloc[0]
        v23_pct = ((s_sa.iloc[-1] / val_23) - 1) * 100 if val_23 != 0 else np.nan
        v23_p = (s_sa.iloc[-1] - val_23) * scale
    except Exception:
        v23_pct = v23_p = np.nan

    st.subheader(f"Empleo Privado - {obtener_nombre_mes(ult_f)}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Mensual (SA)", f"{fmt(m_e)}%", delta=f"{fmt(m_p, 0, True)} puestos")
    c2.metric("Interanual", f"{fmt(i_e)}%", delta=f"{fmt(i_p, 0, True)} puestos")
    c3.metric("vs Agosto 2023", f"{fmt(v23_pct)}%", delta=f"{fmt(v23_p, 0, True)} puestos")

    # Sectores
    if df_sec_orig.empty or df_sec_sa.empty:
        st.warning("No se pudieron leer las hojas de sectores.")
        return

    tmp = df_sec_orig.merge(df_sec_sa, on="fecha", how="inner", suffixes=("_orig", "_sa")).sort_values("fecha")
    sectores = [c for c in df_sec_orig.columns if c != "fecha"]

    resumen = []
    ind_data = None

    for sec in sectores:
        col_o = f"{sec}_orig"
        col_s = f"{sec}_sa"
        if col_o not in tmp.columns or col_s not in tmp.columns:
            continue

        ss_orig = tmp[col_o]
        ss_sa = tmp[col_s]

        if "industria" in sec.lower():
            ind_data = {"orig": ss_orig, "sa": ss_sa, "name": sec, "tmp": tmp}

        try:
            val_23_sec = tmp.loc[tmp["fecha"] == target_date, col_s].iloc[0]
            pct_23 = ((ss_sa.iloc[-1] / val_23_sec) - 1) * 100 if val_23_sec != 0 else np.nan
            puestos_23 = (ss_sa.iloc[-1] - val_23_sec) * scale
        except Exception:
            pct_23 = puestos_23 = np.nan

        resumen.append(
            {
                "Sector": sec,
                "Mensual %": calc_var(ss_sa, 1),
                "Mensual (puestos)": ss_sa.diff().iloc[-1] * scale,
                "Interanual %": calc_var(ss_orig, 12),
                "Interanual (puestos)": ss_orig.diff(12).iloc[-1] * scale,
                "vs Ago-23 %": pct_23,
                "vs Ago-23 (puestos)": puestos_23,
            }
        )

    if resumen:
        st.write("#### Sectores Generales")
        st.dataframe(
            pd.DataFrame(resumen).style.format(
                {
                    "Mensual %": "{:,.2f}%",
                    "Mensual (puestos)": "{:,.0f}",
                    "Interanual %": "{:,.2f}%",
                    "Interanual (puestos)": "{:,.0f}",
                    "vs Ago-23 %": "{:,.2f}%",
                    "vs Ago-23 (puestos)": "{:,.0f}",
                },
                na_rep="s/d",
            ),
            width="stretch",
        )

    # Bloque Industria
    st.divider()
    if ind_data is not None:
        st.subheader(f"Empleo Industrial - {obtener_nombre_mes(ult_f)}")
        isa = ind_data["sa"]
        iorig = ind_data["orig"]
        tmp2 = ind_data["tmp"]

        mi_e = calc_var(isa, 1)
        mi_p = isa.diff().iloc[-1] * scale
        ii_e = calc_var(iorig, 12)
        ii_p = iorig.diff(12).iloc[-1] * scale

        try:
            ival_23 = tmp2.loc[tmp2["fecha"] == target_date, ind_data["name"] + "_sa"].iloc[0]
            iv23_pct = ((isa.iloc[-1] / ival_23) - 1) * 100 if ival_23 != 0 else np.nan
            iv23_p = (isa.iloc[-1] - ival_23) * scale
        except Exception:
            iv23_pct = iv23_p = np.nan

        k1, k2, k3 = st.columns(3)
        k1.metric("Mensual (SA)", f"{fmt(mi_e)}%", delta=f"{fmt(mi_p, 0, True)} puestos")
        k2.metric("Interanual", f"{fmt(ii_e)}%", delta=f"{fmt(ii_p, 0, True)} puestos")
        k3.metric("vs Agosto 2023", f"{fmt(iv23_pct)}%", delta=f"{fmt(iv23_p, 0, True)} puestos")

    # Subsectores industriales
    if df_sub_orig.empty or df_sub_sa.empty:
        st.info("No se encontraron datos de subsectores industriales (A.6.1 / A.6.2).")
        return

    st.write("#### Subsectores Industriales")
    tmpsub = df_sub_orig.merge(df_sub_sa, on="fecha", how="inner", suffixes=("_orig", "_sa")).sort_values("fecha")
    subs = [c for c in df_sub_orig.columns if c != "fecha"]

    res_sub = []
    for sb in subs:
        col_o_s = f"{sb}_orig"
        col_s_s = f"{sb}_sa"
        if col_o_s not in tmpsub.columns or col_s_s not in tmpsub.columns:
            continue

        sbs_orig = tmpsub[col_o_s]
        sbs_sa = tmpsub[col_s_s]

        try:
            v23_sb = tmpsub.loc[tmpsub["fecha"] == target_date, col_s_s].iloc[0]
            p23_sb = ((sbs_sa.iloc[-1] / v23_sb) - 1) * 100 if v23_sb != 0 else np.nan
            d23_sb = (sbs_sa.iloc[-1] - v23_sb) * scale
        except Exception:
            p23_sb = d23_sb = np.nan

        res_sub.append(
            {
                "Subsector": sb,
                "Mensual %": calc_var(sbs_sa, 1),
                "Mensual (puestos)": sbs_sa.diff().iloc[-1] * scale,
                "Interanual %": calc_var(sbs_orig, 12),
                "Interanual (puestos)": sbs_orig.diff(12).iloc[-1] * scale,
                "vs Ago-23 %": p23_sb,
                "vs Ago-23 (puestos)": d23_sb,
            }
        )

    if res_sub:
        st.dataframe(
            pd.DataFrame(res_sub).style.format(
                {
                    "Mensual %": "{:,.2f}%",
                    "Mensual (puestos)": "{:,.0f}",
                    "Interanual %": "{:,.2f}%",
                    "Interanual (puestos)": "{:,.0f}",
                    "vs Ago-23 %": "{:,.2f}%",
                    "vs Ago-23 (puestos)": "{:,.0f}",
                },
                na_rep="s/d",
            ),
            width="stretch",
        )
