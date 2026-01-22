import streamlit as st
import pandas as pd

from services.macro_data import (
    get_a3500,
    get_monetaria_serie,
    get_ipc_bcra,
)

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
    # dic-25
    if dt is None or pd.isna(dt):
        return ""
    return f"{_mes_es_abbr(dt.month)}-{str(dt.year)[-2:]}"


# ============================================================
# Últimos datos (cacheados para no hacer lenta la Home)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def _last_tc():
    df = get_a3500()  # columnas: Date, FX
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_tasa(default_id: int = 13):
    # Monetarias: Date, value
    df = get_monetaria_serie(default_id)
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_ipc_bcra():
    # BCRA IPC: Date, v_m_CPI (decimal), Period
    df = get_ipc_bcra()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "v_m_CPI"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["v_m_CPI"]), pd.to_datetime(r["Date"])


# ============================================================
# Small “KPI under button” component (HTML)
# ============================================================
def _kpi_under_button(value_line: str, label_line: str, date_line: str) -> None:
    st.markdown(
        f"""
        <div class="mini-kpi">
          <div class="mini-kpi__value">{value_line}</div>
          <div class="mini-kpi__label">{label_line}</div>
          <div class="mini-kpi__date">{date_line}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_macro_home(go_to):
    # --- Estilo “moderno, limpio, centrado”
    st.markdown(
        """
        <style>
          .mini-kpi{
            margin-top: 10px;
            text-align: center;
            padding: 6px 6px 0 6px;
          }
          .mini-kpi__value{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.2px;
            color: #0f172a; /* slate-900 */
            line-height: 1.1;
          }
          .mini-kpi__value span.kpi-prefix{
            font-size: 12px;
            font-weight: 700;
            color: #334155; /* slate-700 */
            letter-spacing: 0.2px;
            margin-right: 6px;
            vertical-align: 20%;
          }
          .mini-kpi__label{
            margin-top: 4px;
            font-size: 13px;
            font-weight: 600;
            color: #334155; /* slate-700 */
            line-height: 1.2;
          }
          .mini-kpi__date{
            margin-top: 3px;
            font-size: 12px;
            color: #64748b; /* slate-500 */
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

        # ------------------------------------------------------------
        # Últimos datos (cacheados)
        # ------------------------------------------------------------
        fx_val, fx_date = _last_tc()
        tasa_val, tasa_date = _last_tasa(13)  # Adelantos a Empresas
        ipc_val, ipc_date = _last_ipc_bcra()  # v_m_CPI decimal

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")

            if fx_val is None or fx_date is None:
                _kpi_under_button("—", "TC Mayorista", "")
            else:
                value = f"<span class='kpi-prefix'>ARS/USD</span>{_fmt_thousands_es_int(fx_val)}"
                label = "TC Mayorista"
                date = fx_date.strftime("%d/%m/%Y")
                _kpi_under_button(value, label, date)

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")

            if tasa_val is None or tasa_date is None:
                _kpi_under_button("—", "Adelantos a Empresas", "")
            else:
                value = f"{_fmt_pct_es(tasa_val, 1)} <span style='font-size:12px;font-weight:800;color:#334155;'>TNA</span>"
                label = "Adelantos a Empresas"
                date = tasa_date.strftime("%d/%m/%Y")
                _kpi_under_button(value, label, date)

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")

            if ipc_val is None:
                _kpi_under_button("—", "IPC", "")
            else:
                # ipc_val decimal -> % m/m
                value = _fmt_pct_es(ipc_val * 100, 1)
                label = "IPC"
                date = _fmt_mes_anio_es(ipc_date) if ipc_date is not None else ""
                _kpi_under_button(value, label, date)

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
