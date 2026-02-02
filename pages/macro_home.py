import streamlit as st
import pandas as pd
import random
import numpy as np

# yfinance opcional (ticker)
try:
    import yfinance as yf
except Exception:
    yf = None

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
        1: "ene", 2: "feb", 3: "mar", 4: "abr",
        5: "may", 6: "jun", 7: "jul", 8: "ago",
        9: "sep", 10: "oct", 11: "nov", 12: "dic",
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


@st.cache_data(ttl=12 * 60 * 60)
def _last_brecha_from_macro_fx():
    """
    Trae CCL desde pages/macro_fx.py (como pediste) y calcula brecha.
    Si el import falla, devuelve (None, None) sin romper el home.
    """
    try:
        from pages.macro_fx import get_ccl_yahoo  # debe existir en macro_fx
    except Exception:
        return None, None

    df_ofi = get_a3500()         # Date, FX
    df_ccl = get_ccl_yahoo()     # Date, CCL

    if df_ofi is None or df_ccl is None or df_ofi.empty or df_ccl.empty:
        return None, None

    ofi = df_ofi.copy()
    ccl = df_ccl.copy()

    ofi["Date"] = pd.to_datetime(ofi["Date"], errors="coerce").dt.normalize()
    ccl["Date"] = pd.to_datetime(ccl["Date"], errors="coerce").dt.normalize()

    if "FX" not in ofi.columns or "CCL" not in ccl.columns:
        return None, None

    ofi["FX"] = pd.to_numeric(ofi["FX"], errors="coerce")
    ccl["CCL"] = pd.to_numeric(ccl["CCL"], errors="coerce")

    ofi = ofi.dropna(subset=["Date", "FX"]).sort_values("Date")
    ccl = ccl.dropna(subset=["Date", "CCL"]).sort_values("Date")

    if ofi.empty or ccl.empty:
        return None, None

    min_date = max(ofi["Date"].min(), ccl["Date"].min())
    max_date = min(ofi["Date"].max(), ccl["Date"].max())
    if pd.isna(min_date) or pd.isna(max_date) or min_date > max_date:
        return None, None

    cal = pd.DataFrame({"Date": pd.date_range(min_date, max_date, freq="D")})
    df = (
        cal.merge(ofi[["Date", "FX"]], on="Date", how="left")
           .merge(ccl[["Date", "CCL"]], on="Date", how="left")
           .sort_values("Date")
           .reset_index(drop=True)
    )

    df["FX"] = pd.to_numeric(df["FX"], errors="coerce").ffill()
    df["CCL"] = pd.to_numeric(df["CCL"], errors="coerce").ffill()
    df["Brecha"] = (df["CCL"] / df["FX"] - 1) * 100

    df_ok = df.dropna(subset=["Brecha"]).sort_values("Date")
    if df_ok.empty:
        return None, None

    last = df_ok.iloc[-1]
    return float(last["Brecha"]), pd.to_datetime(last["Date"])


@st.cache_data(ttl=12 * 60 * 60)
def _last_reservas():
    """
    Reservas internacionales brutas (BCRA) – id serie=1 (millones de USD)
    """
    df = get_monetaria_serie(1)
    if df is None or df.empty:
        return None, None

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    if df.empty:
        return None, None

    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


# ============================================================
# Ticker tape – yfinance
# ============================================================
@st.cache_data(ttl=120, show_spinner=False)
def _get_daily_changes(symbols: list[str]) -> dict[str, float | None]:
    if yf is None:
        return {s: None for s in symbols}

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
# KPI card
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


def _kpi_card_blank() -> None:
    _kpi_card("&nbsp;", "&nbsp;", "&nbsp;")


# ============================================================
# RENDER
# ============================================================
def render_macro_home(go_to):
    st.markdown(
        """
        <style>
          /* Contenedor central (NO toca header/logo) */
          .macrohome-shell{
            max-width: 1000px;   /* angosto, pero sin exagerar */
            margin: 0 auto;
            padding: 0 6px;
          }

          .macrohome-title{
            text-align:center;
            font-size: 44px;
            font-weight: 800;
            color: #0f172a;
            margin-top: 8px;
            margin-bottom: 10px;
          }

          /* Marcadores para aplicar estilos SOLO donde corresponde */
          .mh-pills-marker{}
          .mh-kpis-marker{}

          /* === Botones de secciones (celestito + hover) ===
             Importante: apuntamos SOLO al bloque que contiene el marker,
             así NO tocamos "Volver a secciones".
          */
          section.main div[data-testid="stVerticalBlock"]:has(.mh-pills-marker)
          div[data-testid="stButton"] > button{
            height: 44px !important;
            border-radius: 10px !important;
            background: #eaf3fb !important;
            border: 1px solid #9ec5e5 !important;
            font-weight: 700 !important;
            color: #0f172a !important;
            box-shadow: 0 6px 14px rgba(15,23,42,0.08) !important;
          }

          section.main div[data-testid="stVerticalBlock"]:has(.mh-pills-marker)
          div[data-testid="stButton"] > button:hover{
            background: #dceefe !important;
            border-color: #7fb3dd !important;
            box-shadow: 0 8px 18px rgba(15,23,42,0.12) !important;
          }

          /* KPI cards */
          .kpi-card{
            background:#ffffff;
            border-radius: 14px;
            padding: 16px 14px 14px 14px;
            text-align:center;
            box-shadow: 0 10px 24px rgba(15,23,42,0.08);
            border: 1px solid rgba(15,23,42,.06);
            min-height: 96px;
            display:flex;
            flex-direction: column;
            justify-content:center;
          }
          .kpi-card__value{
            font-size: 30px;
            font-weight: 700;
            line-height: 1.05;
            color:#0f172a;
          }
          .kpi-prefix{
            font-size: 12px;
            margin-right: 6px;
            color:#475569;
            font-weight: 700;
          }
          .kpi-suffix{
            font-size: 12px;
            margin-left: 6px;
            color:#334155;
            font-weight: 800;
          }
          .kpi-card__label{
            font-size: 13px;
            margin-top: 8px;
            color:#0f172a;
            font-weight: 650;
          }
          .kpi-card__date{
            font-size: 12px;
            color:#64748b;
            margin-top: 2px;
          }

          /* Ticker */
          .ticker-wrap{
            width: 82%;
            margin: 10px auto 12px auto;
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
          .tk-sym{ color:#ffffff !important; font-weight:900; letter-spacing:.2px; }
          .tk-sep{ color:rgba(255,255,255,.35) !important; }
          .tk-pos{ color:#00e676 !important; }
          .tk-neg{ color:#ff1744 !important; }
          .tk-flat{ color:#cbd5e1 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="macrohome-shell">', unsafe_allow_html=True)

    # =======================================================
    # Loading + últimos datos
    # =======================================================
    fact_ph = st.empty()
    fact_ph.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    with st.spinner("Actualizando últimos datos..."):
        fx_val, fx_date = _last_tc()
        tasa_val, tasa_date = _last_tasa()
        ipc_val, ipc_date = _last_ipc_bcra()
        emae_yoy, emae_date = _last_emae_yoy()
        brecha_val, brecha_date = _last_brecha_from_macro_fx()
        res_val, res_date = _last_reservas()

    fact_ph.empty()

    # =======================================================
    # TICKER ARRIBA
    # =======================================================
    symbols = ["TSLA", "AAPL", "AMZN", "NVDA", "META", "GGAL", "PAM", "VIST", "YPF", "KO", "GOOGL"]
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

    # =======================================================
    # TÍTULO (SIN subtítulo)
    # =======================================================
    st.markdown("<div class='macrohome-title'>Macroeconomía</div>", unsafe_allow_html=True)

    # =======================================================
    # BOTONES SECCIONES (marker para CSS scope)
    # =======================================================
    st.markdown("<div class='mh-pills-marker'></div>", unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns(4, gap="large")
    with b1:
        if st.button("💱  Tipo de cambio", use_container_width=True, key="mh_btn_fx"):
            go_to("macro_fx")
    with b2:
        if st.button("🏦  Monetario", use_container_width=True, key="mh_btn_mon"):
            go_to("macro_tasa")
    with b3:
        if st.button("🛒  Precios", use_container_width=True, key="mh_btn_precios"):
            go_to("macro_precios")
    with b4:
        if st.button("📈  PBI / EMAE", use_container_width=True, key="mh_btn_pbi"):
            go_to("macro_pbi_emae")

    # =======================================================
    # KPIs (2 filas, aire entre filas)
    # =======================================================
    st.markdown("<div class='mh-kpis-marker'></div>", unsafe_allow_html=True)

    r1c1, r1c2, r1c3, r1c4 = st.columns(4, gap="large")

    with r1c1:
        if fx_val is not None and fx_date is not None:
            _kpi_card(
                f"<span class='kpi-prefix'>ARS/USD</span>{_fmt_thousands_es_int(fx_val)}",
                "TC Mayorista",
                fx_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "TC Mayorista", "—")

    with r1c2:
        if tasa_val is not None and tasa_date is not None:
            _kpi_card(
                f"{_fmt_pct_es(tasa_val)}<span class='kpi-suffix'>TNA</span>",
                "Adelantos a Empresas",
                tasa_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "Adelantos a Empresas", "—")

    with r1c3:
        if ipc_val is not None and ipc_date is not None:
            _kpi_card(_fmt_pct_es(ipc_val * 100), "IPC", _fmt_mes_anio_es(ipc_date))
        else:
            _kpi_card("—", "IPC", "—")

    with r1c4:
        if emae_yoy is not None and emae_date is not None:
            _kpi_card(_fmt_pct_es(emae_yoy), "EMAE (i.a.)", _fmt_mes_anio_es(emae_date))
        else:
            _kpi_card("—", "EMAE (i.a.)", "—")

    # aire real
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    r2c1, r2c2, r2c3, r2c4 = st.columns(4, gap="large")

    with r2c1:
        if brecha_val is not None and brecha_date is not None:
            _kpi_card(
                _fmt_pct_es(brecha_val, 1),
                "Brecha Cambiaria",
                brecha_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "Brecha Cambiaria", "—")

    with r2c2:
        if res_val is not None and res_date is not None:
            _kpi_card(
                f"<span class='kpi-prefix'>USD</span>{_fmt_thousands_es_int(res_val)}<span class='kpi-suffix'>mill</span>",
                "Reservas Internacionales",
                res_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "Reservas Internacionales", "—")

    with r2c3:
        _kpi_card_blank()

    with r2c4:
        _kpi_card_blank()

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
