import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import random
import textwrap
import streamlit.components.v1 as components

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
        return f"{float(x):.{dec}f}".replace(".", ",")
    except Exception:
        return "—"

def _arrow_cls(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ("", "")
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")

def _compute_yoy(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["YoY"] = (t["Value"] / t["Value"].shift(12) - 1.0) * 100.0
    return t

def _compute_mom(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["MoM"] = (t["Value"] / t["Value"].shift(1) - 1.0) * 100.0
    return t

def _apply_panel_wrap(marker_id: str):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          function applyPanelClass() {{
            const marker = window.parent.document.getElementById('{marker_id}');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
          }}
          applyPanelClass();
        }})();
        </script>
        """,
        height=0,
    )

def _month_es(dt: pd.Timestamp) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = pd.to_datetime(dt)
    return dt.strftime("%m/%Y")

# ============================================================
# Main
# ============================================================
def render_macro_pbi_emae(go_to):

    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # CSS (TU ORIGINAL COMPLETO)
    # =========================
    st.markdown(textwrap.dedent("""<style>
    /* === TODO TU CSS ORIGINAL AQUÍ SIN MODIFICAR === */
    </style>"""), unsafe_allow_html=True)

    # =========================
    # Load data
    # =========================
    fact = st.empty()
    fact.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    with st.spinner("Cargando EMAE..."):
        df_o = get_emae_original()
        df_s = get_emae_deseasonalizado()

    fact.empty()

    if df_o is None or df_o.empty or df_s is None or df_s.empty:
        st.error("No pude cargar las series de EMAE desde datos.gob.ar.")
        return

    df_o["Date"] = pd.to_datetime(df_o["Date"])
    df_s["Date"] = pd.to_datetime(df_s["Date"])

    o_full_yoy = _compute_yoy(df_o)
    s_full_mom = _compute_mom(df_s)

    yoy_val = o_full_yoy["YoY"].dropna().iloc[-1]
    yoy_date = o_full_yoy.dropna(subset=["YoY"]).iloc[-1]["Date"]

    mom_val = s_full_mom["MoM"].dropna().iloc[-1]

    # =========================
    # Panel
    # =========================
    with st.container():
        _apply_panel_wrap("emae_panel_marker")

        # Header
        st.markdown(
            "\n".join(
                [
                    '<div class="fx-wrap">',
                    '<div class="fx-title-row">',
                    '<div class="fx-icon-badge">📊</div>',
                    '<div class="fx-title">Estimador Mensual de Actividad Económica</div>',
                    '</div>',
                    '<div class="fx-card">',
                    '<div class="fx-row">',
                    f'<div class="fx-value">{_fmt_pct_es(yoy_val,1)}%</div>',
                    '<div class="fx-meta">',
                    f'EMAE (original)<span class="sep">|</span>YoY<span class="sep">|</span>{_month_es(yoy_date)}',
                    '</div>',
                    '<div class="fx-pills">',
                    '<div class="fx-pill red">',
                    f'<span class="fx-arrow {_arrow_cls(yoy_val)[1]}">{_arrow_cls(yoy_val)[0]}</span>',
                    f'<span class="{_arrow_cls(yoy_val)[1]}">{_fmt_pct_es(yoy_val,1)}%</span>',
                    '<span class="lab">anual (orig.)</span>',
                    '</div>',
                    '<div class="fx-pill green">',
                    f'<span class="fx-arrow {_arrow_cls(mom_val)[1]}">{_arrow_cls(mom_val)[0]}</span>',
                    f'<span class="{_arrow_cls(mom_val)[1]}">{_fmt_pct_es(mom_val,1)}%</span>',
                    '<span class="lab">mensual (s.e.)</span>',
                    '</div>',
                    '</div></div></div></div>',
                ]
            ),
            unsafe_allow_html=True,
        )

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # =========================
        # CONTROLES NUEVOS
        # =========================
        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                ["Nivel desestacionalizado", "Variación mensual", "Variación anual"],
                key="emae_medida_new",
                label_visibility="collapsed",
            )

        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.multiselect(
                "",
                [
                    "EMAE - Nivel general",
                    "IPI Manufacturero",
                    "IPI Minero",
                    "ISAC - Construcción",
                ],
                default=["EMAE - Nivel general"],
                key="emae_variable_new",
                label_visibility="collapsed",
            )

        # =========================
        # Rango fechas
        # =========================
        min_date = min(df_o["Date"].min(), df_s["Date"].min())
        max_date = max(df_o["Date"].max(), df_s["Date"].max())

        months = pd.date_range(
            min_date.to_period("M").to_timestamp(),
            max_date.to_period("M").to_timestamp(),
            freq="MS",
        )

        months_d = [m.date() for m in months]

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.select_slider(
            "",
            options=months_d,
            value=(months_d[0], months_d[-1]),
            format_func=lambda d: pd.Timestamp(d).strftime("%b-%y"),
            label_visibility="collapsed",
        )

        start_ts = pd.Timestamp(start_d)
        end_ts = pd.Timestamp(end_d)

        # =========================
        # Gráfico
        # =========================
        medida = st.session_state.get("emae_medida_new")
        variables = st.session_state.get("emae_variable_new", [])

        fig = go.Figure()

        if "EMAE - Nivel general" in variables:

            if medida == "Nivel desestacionalizado":
                lvl = df_s[(df_s["Date"] >= start_ts) & (df_s["Date"] <= end_ts)]
                fig.add_trace(go.Scatter(x=lvl["Date"], y=lvl["Value"], mode="lines", name="EMAE (s.e.)"))
                fig.update_yaxes(title="Índice")

            elif medida == "Variación mensual":
                mom = s_full_mom[(s_full_mom["Date"] >= start_ts) & (s_full_mom["Date"] <= end_ts)]
                fig.add_trace(go.Bar(x=mom["Date"], y=mom["MoM"], name="EMAE - mensual"))
                fig.add_hline(y=0)
                fig.update_yaxes(ticksuffix="%")

            elif medida == "Variación anual":
                yoy = o_full_yoy[(o_full_yoy["Date"] >= start_ts) & (o_full_yoy["Date"] <= end_ts)]
                fig.add_trace(go.Bar(x=yoy["Date"], y=yoy["YoY"], name="EMAE - anual"))
                fig.add_hline(y=0)
                fig.update_yaxes(ticksuffix="%")

        fig.update_layout(
            height=520,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=50),
            legend=dict(orientation="h"),
            dragmode=False,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC (EMAE) vía API datos.gob.ar"
            "</div>",
            unsafe_allow_html=True,
        )
