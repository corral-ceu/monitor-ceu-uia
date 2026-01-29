import streamlit as st
import pandas as pd
import random
import yfinance as yf

from services.macro_data import (
    get_a3500,
    get_monetaria_serie,
    get_ipc_bcra,
    get_emae_original,
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


def _fmt_pct_es_signed(x: float | None, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "—"
    sign = "+" if x >= 0 else "−"
    s = f"{abs(float(x)):.{dec}f}".replace(".", ",")
    return f"{sign}{s}%"


def _mes_es_abbr(m: int) -> str:
    return {
        1: "ene",
        2: "feb",
        3: "mar",
        4: "abr",
        5: "may",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "sep",
        10: "oct",
        11: "nov",
        12: "dic",
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
    df = get_a3500()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_tasa(default_id: int = 13):
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
    df = get_ipc_bcra()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "v_m_CPI"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["v_m_CPI"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_emae_yoy():
    df = get_emae_original()
    if df is None or df.empty:
        return None, None
    df = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    df["YoY"] = (df["Value"] / df["Value"].shift(12) - 1) * 100
    df = df.dropna(subset=["YoY"])
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["YoY"]), pd.to_datetime(r["Date"])


# ============================================================
# Ticker tape – yfinance
# ============================================================
@st.cache_data(ttl=120, show_spinner=False)
def _get_daily_changes(symbols: list[str]) -> dict[str, float | None]:
    """
    Variación diaria (%) vs cierre previo.
    """
    try:
        df = yf.download(
            tickers=" ".join(symbols),
            period="7d",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True,
            progress=False,
        )

        changes: dict[str, float | None] = {}
        for s in symbols:
            try:
                close = df[(s, "Close")].dropna()
                if len(close) < 2:
                    changes[s] = None
                else:
                    prev = float(close.iloc[-2])
                    last = float(close.iloc[-1])
                    changes[s] = (last / prev - 1) * 100
            except Exception:
                changes[s] = None

        return changes
    except Exception:
        return {s: None for s in symbols}


def _build_ticker_html(changes: dict[str, float | None], order: list[str]) -> str:
    parts = []
    for s in order:
        v = changes.get(s)
        cls = "tk-flat"
        if v is not None:
            cls = "tk-pos" if v >= 0 else "tk-neg"
        parts.append(
            f"<span class='tk-item'><span class='tk-sym'>{s}</span> "
            f"<span class='{cls}'>{_fmt_pct_es_signed(v)}</span></span>"
        )
    return "<span class='tk-sep'>•</span>".join(parts)


# ============================================================
# Mini-card KPI
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


# ============================================================
# RENDER
# ============================================================
def render_macro_home(go_to):

    st.markdown(
        """
        <style>
          /* ======================================================
             IMPORTANTE:
             - NO tocamos .block-container (rompe topbar/logo).
             - Bajamos levemente el header/topbar (logo) con una regla
               sobre el header de Streamlit.
             - Subimos SOLO el contenido del cuerpo con un wrapper.
             ====================================================== */

          /* 🔽 Logo/topbar un poco más abajo */
          header[data-testid="stHeader"]{
            top: 10px !important; /* ajustá: 8/10/12 */
          }

          /* 🔼 Subir SOLO el contenido (desde volver a secciones hacia abajo) */
          .macrohome-shift{
            margin-top: -46px; /* ajustá: -36 / -42 / -46 / -52 */
          }

          /* Si tu theme global centra home-wrap con mucho margin, lo achicamos acá */
          .home-wrap{
            margin-top: 8px !important;
            margin-bottom: 10px !important;
          }
          .home-title{ margin-top: 0px !important; }

          div.home-cards div[data-testid="stButton"] > button {
            font-weight: 700 !important;
          }

          .kpi-card{
            margin: 10px auto 0 auto;
            width: 92%;
            background: #ffffff;
            border-radius: 14px;
            padding: 10px;
            text-align: center;
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .kpi-card__value{ font-size:26px; font-weight:500; }
          .kpi-prefix{ font-size:12px; margin-right:6px; color:#475569; }
          .kpi-suffix{ font-size:12px; margin-left:6px; color:#334155; }
          .kpi-card__label{ font-size:13px; margin-top:6px; }
          .kpi-card__date{ font-size:12px; color:#64748b; }

          /* ===== TICKER ===== */
          .ticker-wrap{
            width:92%;
            margin:14px auto 6px auto;
            background:#0b0b0b;
            border-radius:12px;
            overflow:hidden;
            border: 1px solid rgba(255,255,255,.10);
          }

          .ticker-viewport{ padding:10px 0; }

          .ticker-track{
            display:inline-block;
            white-space:nowrap;
            animation:tickerScroll 26s linear infinite;
            will-change: transform;
          }

          @keyframes tickerScroll{
            from{ transform:translateX(0%); }
            to{ transform:translateX(-50%); }
          }

          .tk-item{
            padding:0 14px;
            font-size:16px;
            font-weight:800;
            color:#ffffff !important;
          }

          .tk-sym{
            color:#ffffff !important;
            font-weight:900;
            letter-spacing:.2px;
          }

          .tk-sep{
            color:rgba(255,255,255,.35) !important;
          }

          .tk-pos{ color:#00e676 !important; }
          .tk-neg{ color:#ff1744 !important; }
          .tk-flat{ color:#cbd5e1 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Wrapper que sube el body (sin tocar el topbar/logo)
    st.markdown('<div class="macrohome-shift">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="home-wrap">
          <div class="home-title">Macroeconomía</div>
          <div class="home-subtitle">Seleccioná una variable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1, 6, 1])

    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        fact_ph = st.empty()
        fact_ph.info("💡 " + random.choice(INDU_LOADING_PHRASES))

        with st.spinner("Actualizando últimos datos..."):
            fx_val, fx_date = _last_tc()
            tasa_val, tasa_date = _last_tasa()
            ipc_val, ipc_date = _last_ipc_bcra()
            emae_yoy, emae_date = _last_emae_yoy()

        fact_ph.empty()

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")
            if fx_val is not None:
                _kpi_card(
                    f"<span class='kpi-prefix'>ARS/USD</span>{_fmt_thousands_es_int(fx_val)}",
                    "TC Mayorista",
                    fx_date.strftime("%d/%m/%Y"),
                )

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")
            if tasa_val is not None:
                _kpi_card(
                    f"{_fmt_pct_es(tasa_val)}<span class='kpi-suffix'>TNA</span>",
                    "Adelantos a Empresas",
                    tasa_date.strftime("%d/%m/%Y"),
                )

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")
            if ipc_val is not None:
                _kpi_card(_fmt_pct_es(ipc_val * 100), "IPC", _fmt_mes_anio_es(ipc_date))

        with c4:
            if st.button("📈\nPBI / EMAE", use_container_width=True):
                go_to("macro_pbi_emae")
            if emae_yoy is not None:
                _kpi_card(_fmt_pct_es(emae_yoy), "EMAE (i.a.)", _fmt_mes_anio_es(emae_date))

        st.markdown("</div>", unsafe_allow_html=True)

        # ===== TICKER (ABAJO) =====
        symbols = ["KO", "GOOGL", "TSLA", "AAPL", "AMZN", "NVDA", "META", "GGAL", "PAM", "VIST", "YPF"]
        changes = _get_daily_changes(symbols)
        line = _build_ticker_html(changes, symbols)

        st.markdown(
            f"""
            <div class="ticker-wrap">
              <div class="ticker-viewport">
                <div class="ticker-track">
                  {line}<span class='tk-sep'>•</span>{line}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

    # Cerrar wrapper
    st.markdown("</div>", unsafe_allow_html=True)

