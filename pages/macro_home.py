import streamlit as st
import pandas as pd
import random

from services.macro_data import (
    get_a3500,
    get_monetaria_serie,
    get_ipc_bcra,
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
# Format helpers (ES)
# ============================================================
def _fmt_thousands_es_int(x: float) -> str:
    """1_430 -> '1.430' (sin decimales, miles con punto)"""
    try:
        n = int(round(float(x)))
        return f"{n:,}".replace(",", ".")
    except Exception:
        return "—"

def _fmt_pct_es(x: float, dec: int = 1) -> str:
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except Exception:
        return "—"

def _mes_es_abbr(m: int) -> str:
    return {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
    }.get(m, "")

def _fmt_mes_anio_es(dt: pd.Timestamp) -> str:
    if dt is None or pd.isna(dt):
        return ""
    return f"{_mes_es_abbr(dt.month)}-{str(dt.year)[-2:]}"


# ============================================================
# Últimos datos (cacheados)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def _last_tc():
    df = get_a3500()  # Date, FX
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_tasa(default_id: int = 13):
    df = get_monetaria_serie(default_id)  # Date, value
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_ipc_bcra():
    df = get_ipc_bcra()  # Date, v_m_CPI (decimal)
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "v_m_CPI"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["v_m_CPI"]), pd.to_datetime(r["Date"])


# ============================================================
# Mini-card KPI (HTML)
# ============================================================
def _kpi_card(value_html: str, label: str, date: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-card__value">{value_html}</div>
          <div class="kpi-card__label">{label}</div>
          <div class="kpi-card__date">{date}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_macro_home(go_to):

    st.markdown(
        """
        <style>
          /* Texto de los botones de la home en negrita (Streamlit real DOM) */
          div.home-cards div[data-testid="stButton"] > button {
            font-weight: 700 !important;
            letter-spacing: 0.2px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


    
    # --- Estilos: “mini card” fresca, sobria, moderna
    st.markdown(
        """
        <style>
          .kpi-card{
            margin: 10px auto 0 auto;
            width: 92%;
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.10); /* slate-900 @10% */
            border-radius: 14px;
            padding: 10px 10px 9px 10px;
            text-align: center;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
          }
          .kpi-card__value{
            font-size: 26px;
            font-weight: 900;
            letter-spacing: -0.4px;
            color: #0f172a;
            line-height: 1.05;
          }
          .kpi-prefix{
            display: inline-block;
            font-size: 12px;
            font-weight: 800;
            color: #475569; /* slate-600 */
            letter-spacing: 0.6px;
            margin-right: 8px;
            vertical-align: 30%;
            text-transform: uppercase;
          }
          .kpi-suffix{
            font-size: 12px;
            font-weight: 900;
            color: #334155;
            margin-left: 6px;
            letter-spacing: 0.6px;
            text-transform: uppercase;
          }
          .kpi-card__label{
            margin-top: 6px;
            font-size: 13px;
            font-weight: 700;
            color: #334155;
            line-height: 1.2;
          }
          .kpi-card__date{
            margin-top: 4px;
            font-size: 12px;
            color: #64748b;
            line-height: 1.2;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="home-wrap">
            <div class="home-title">Macroeconomía</div>
            <div class="home-subtitle">Seleccioná una variable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_pad, mid, right_pad = st.columns([1, 6, 1])

    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        # ============================================================
        # Loading phrases (solo mientras obtiene últimos datos)
        # ============================================================
        fact_ph = st.empty()
        fact_ph.info("💡 " + random.choice(INDU_LOADING_PHRASES))

        with st.spinner("Actualizando últimos datos..."):
            fx_val, fx_date = _last_tc()
            tasa_val, tasa_date = _last_tasa(13)     # Adelantos a Empresas
            ipc_val, ipc_date = _last_ipc_bcra()     # IPC BCRA (decimal)

        fact_ph.empty()

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")

            if fx_val is None or fx_date is None:
                _kpi_card("—", "TC Mayorista", "")
            else:
                value = f"<span class='kpi-prefix'>ARS/USD</span>{_fmt_thousands_es_int(fx_val)}"
                _kpi_card(value, "TC Mayorista", fx_date.strftime("%d/%m/%Y"))

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")

            if tasa_val is None or tasa_date is None:
                _kpi_card("—", "Adelantos a Empresas", "")
            else:
                value = f"{_fmt_pct_es(tasa_val, 1)}<span class='kpi-suffix'>TNA</span>"
                _kpi_card(value, "Adelantos a Empresas", tasa_date.strftime("%d/%m/%Y"))

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")

            if ipc_val is None:
                _kpi_card("—", "IPC", "")
            else:
                value = _fmt_pct_es(ipc_val * 100, 1)
                _kpi_card(value, "IPC", _fmt_mes_anio_es(ipc_date))

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
