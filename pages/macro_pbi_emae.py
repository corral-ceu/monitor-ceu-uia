import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import random

from services.macro_data import (
    get_emae_original,
    get_emae_deseasonalizado,
)

# ============================================================
# Frases (loading)
# ============================================================
INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]

# ============================================================
# Helpers
# ============================================================
def _fmt_pct_es(x: float, dec: int = 1) -> str:
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except Exception:
        return "—"


def _compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["YoY"] = (t["Value"] / t["Value"].shift(12) - 1.0) * 100.0
    return t


def _compute_mom(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["MoM"] = (t["Value"] / t["Value"].shift(1) - 1.0) * 100.0
    return t


def render_macro_pbi_emae(go_to):

    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 📈 PBI / EMAE")
    st.caption("Actividad económica (EMAE) – serie original y desestacionalizada (INDEC / datos.gob.ar)")
    st.divider()

    phrase = random.choice(INDU_LOADING_PHRASES)
    fact_ph = st.empty()
    fact_ph.info(phrase)

    with st.spinner("Cargando EMAE..."):
        df_o = get_emae_original()
        df_s = get_emae_deseasonalizado()

    fact_ph.empty()

    if df_o is None or df_o.empty or df_s is None or df_s.empty:
        st.error("No pude cargar las series de EMAE desde datos.gob.ar.")
        return

    df_o = df_o.copy()
    df_s = df_s.copy()
    df_o["Date"] = pd.to_datetime(df_o["Date"], errors="coerce")
    df_s["Date"] = pd.to_datetime(df_s["Date"], errors="coerce")
    df_o["Value"] = pd.to_numeric(df_o["Value"], errors="coerce")
    df_s["Value"] = pd.to_numeric(df_s["Value"], errors="coerce")
    df_o = df_o.dropna().sort_values("Date").reset_index(drop=True)
    df_s = df_s.dropna().sort_values("Date").reset_index(drop=True)

    # KPIs
    o_k = _compute_yoy(df_o)
    s_k = _compute_mom(df_s)

    yoy_val = o_k["YoY"].dropna().iloc[-1] if o_k["YoY"].notna().any() else None
    yoy_date = o_k.dropna(subset=["YoY"]).iloc[-1]["Date"] if o_k["YoY"].notna().any() else None

    mom_val = s_k["MoM"].dropna().iloc[-1] if s_k["MoM"].notna().any() else None
    mom_date = s_k.dropna(subset=["MoM"]).iloc[-1]["Date"] if s_k["MoM"].notna().any() else None

    c1, c2, c3 = st.columns([2.2, 2.2, 5.6], vertical_alignment="top")

    with c1:
        st.metric(
            "Variación interanual (original)",
            _fmt_pct_es(yoy_val, 1) if yoy_val is not None else "—",
            help="(t / t-12) - 1. Calculado sobre la serie original."
        )
        if yoy_date is not None:
            st.caption(f"Último dato: {yoy_date.strftime('%m/%Y')}")

    with c2:
        st.metric(
            "Variación mensual (desest.)",
            _fmt_pct_es(mom_val, 1) if mom_val is not None else "—",
            help="(t / t-1) - 1. Calculado sobre la serie desestacionalizada."
        )
        if mom_date is not None:
            st.caption(f"Último dato: {mom_date.strftime('%m/%Y')}")

    with c3:
        max_real = max(pd.to_datetime(df_o["Date"].max()), pd.to_datetime(df_s["Date"].max()))
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "5A", "Todo"],
            horizontal=True,
            index=2,
            label_visibility="collapsed",
        )

        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
        elif rango == "5A":
            min_sel = max_real - pd.DateOffset(years=5)
        else:
            min_sel = min(pd.to_datetime(df_o["Date"].min()), pd.to_datetime(df_s["Date"].min()))

        o_plot = df_o[df_o["Date"] >= min_sel]
        s_plot = df_s[df_s["Date"] >= min_sel]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=o_plot["Date"],
                y=o_plot["Value"],
                mode="lines+markers",
                marker=dict(size=4),
                name="EMAE (original)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=s_plot["Date"],
                y=s_plot["Value"],
                mode="lines+markers",
                marker=dict(size=4),
                name="EMAE (desestacionalizado)",
            )
        )

        fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
        )
        fig.update_xaxes(title="")
        fig.update_yaxes(title="Índice")

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: INDEC (EMAE) vía API datos.gob.ar")
