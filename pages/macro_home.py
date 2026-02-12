import streamlit as st
import pandas as pd
import random
import numpy as np
import io
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# yfinance opcional
try:
    import yfinance as yf
except Exception:
    yf = None

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
# Cache wrappers (para no repetir descargas/procesos)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _a3500_cached() -> pd.DataFrame:
    df = get_a3500()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    if "FX" in df.columns:
        df["FX"] = pd.to_numeric(df["FX"], errors="coerce")
    df = df.dropna(subset=["Date", "FX"]).sort_values("Date")
    return df


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _monetaria_cached(serie_id: int) -> pd.DataFrame:
    df = get_monetaria_serie(serie_id)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")
    return df


# ============================================================
# Últimos datos
# ============================================================
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_tc():
    df = _a3500_cached()
    if df is None or df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["FX"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_tasa(default_id: int = 13):
    df = _monetaria_cached(int(default_id))
    if df is None or df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_ipc_bcra():
    df = get_ipc_bcra()
    if df is None or df.empty:
        return None, None
    df = df.copy()
    df = df.dropna(subset=["Date", "v_m_CPI"]).sort_values("Date")
    if df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["v_m_CPI"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_reservas():
    df = _monetaria_cached(1)
    if df is None or df.empty:
        return None, None
    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_riesgo_pais():
    """
    Riesgo País (puntos básicos).
    Import lazy desde pages/finanzas, pero cacheado por TTL.
    """
    try:
        from pages.finanzas import _load_riesgo_pais
    except Exception:
        return None, None

    try:
        df = _load_riesgo_pais()
    except Exception:
        return None, None

    if df is None or df.empty:
        return None, None

    df = df.copy()

    if "Date" not in df.columns:
        for c in ["date", "fecha", "Fecha"]:
            if c in df.columns:
                df = df.rename(columns={c: "Date"})
                break

    if "value" not in df.columns:
        for c in ["Value", "valor", "riesgo_pais", "Riesgo País", "Riesgo Pais"]:
            if c in df.columns:
                df = df.rename(columns={c: "value"})
                break

    if "Date" not in df.columns or "value" not in df.columns:
        return None, None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["Date", "value"]).sort_values("Date")

    if df.empty:
        return None, None

    r = df.iloc[-1]
    return float(r["value"]), pd.to_datetime(r["Date"])


# ============================================================
# Brecha (estable: última fecha común + fallback asof)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_brecha_from_macro_fx():
    """
    Brecha = CCL / Oficial - 1.
    Estable: usa última fecha común exacta; si no hay, merge_asof con tolerancia.
    Rápido: usa tail() para no mergear todo.
    """
    # ✅ CCL desde services (evita import circular con pages.macro_fx)
    try:
        from services.market_data import get_ccl_ypf_df_fast
    except Exception:
        return None, None

    ofi = _a3500_cached()
    if ofi is None or ofi.empty or "Date" not in ofi.columns or "FX" not in ofi.columns:
        return None, None

    try:
        ccl = get_ccl_ypf_df_fast(period="2y", prefer_adj=False)
    except Exception:
        return None, None

    if ccl is None or ccl.empty or "Date" not in ccl.columns:
        return None, None

    # --- normalizaciones mínimas
    ofi = ofi.copy()
    ofi["Date"] = pd.to_datetime(ofi["Date"], errors="coerce").dt.normalize()
    ofi["FX"] = pd.to_numeric(ofi["FX"], errors="coerce")
    ofi = ofi.dropna(subset=["Date", "FX"]).sort_values("Date")

    ccl = ccl.copy()
    ccl["Date"] = pd.to_datetime(ccl["Date"], errors="coerce").dt.normalize()

    # normalizar nombre por si viene como value
    if "CCL" not in ccl.columns:
        if "value" in ccl.columns:
            ccl = ccl.rename(columns={"value": "CCL"})
        else:
            for col in ["ccl", "Value", "precio", "Precio"]:
                if col in ccl.columns:
                    ccl = ccl.rename(columns={col: "CCL"})
                    break

    if "CCL" not in ccl.columns:
        return None, None

    ccl["CCL"] = pd.to_numeric(ccl["CCL"], errors="coerce")
    ccl = ccl.dropna(subset=["Date", "CCL"]).sort_values("Date")

    if ccl.empty or ofi.empty:
        return None, None

    # 1) última fecha común exacta (rápido: acotar universo)
    common = (
        ofi[["Date", "FX"]].tail(1500)
        .merge(ccl[["Date", "CCL"]].tail(1500), on="Date", how="inner")
        .dropna()
        .sort_values("Date")
    )
    if not common.empty:
        last = common.iloc[-1]
        brecha = (float(last["CCL"]) / float(last["FX"]) - 1) * 100
        return float(brecha), pd.to_datetime(last["Date"])

    # 2) fallback: asof (oficial <= fecha CCL), tolerancia 7 días
    left = ccl[["Date", "CCL"]].tail(600).sort_values("Date")
    right = ofi[["Date", "FX"]].tail(1200).sort_values("Date")

    left = ofi[["Date", "FX"]].tail(1200).sort_values("Date")     # FECHAS OFICIAL
    right = ccl[["Date", "CCL"]].tail(1200).sort_values("Date")   # CCL ANTERIOR

    m = pd.merge_asof(
        left,
        right,
        on="Date",
        direction="backward",
        tolerance=pd.Timedelta(days=14),
    ).dropna()


    if m.empty:
        return None, None

    last = m.iloc[-1]
    brecha = (float(last["CCL"]) / float(last["FX"]) - 1) * 100
    return float(brecha), pd.to_datetime(last["Date"])


# ============================================================
# Merval USD (estable: última fecha común + limpieza de índice)
# ============================================================
@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def _last_merval_usd():
    """
    MERVAL en USD = ^MERV / (YPFD.BA / YPF)
    Estable: alinea por última fecha común normalizando índice a fecha.
    """
    if yf is None:
        return None, None

    def _close_series(dl):
        if dl is None:
            return None
        if isinstance(dl, pd.Series):
            return dl
        if isinstance(dl, pd.DataFrame):
            if "Close" in dl.columns:
                s = dl["Close"]
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                return s
            if isinstance(dl.columns, pd.MultiIndex):
                cols = list(dl.columns)
                c1 = [c for c in cols if len(c) >= 2 and c[0] == "Close"]
                if c1:
                    s = dl[c1[0]]
                    if isinstance(s, pd.DataFrame):
                        s = s.iloc[:, 0]
                    return s
                c2 = [c for c in cols if len(c) >= 2 and c[1] == "Close"]
                if c2:
                    s = dl[c2[0]]
                    if isinstance(s, pd.DataFrame):
                        s = s.iloc[:, 0]
                    return s
        return None

    try:
        merv_dl = yf.download("^MERV", period="1y", progress=False, auto_adjust=False, group_by="column", threads=False)
        ypf_ars_dl = yf.download("YPFD.BA", period="1y", progress=False, auto_adjust=False, group_by="column", threads=False)
        ypf_usd_dl = yf.download("YPF", period="1y", progress=False, auto_adjust=False, group_by="column", threads=False)

        merv = _close_series(merv_dl)
        ypf_ars = _close_series(ypf_ars_dl)
        ypf_usd = _close_series(ypf_usd_dl)
    except Exception:
        return None, None

    if merv is None or ypf_ars is None or ypf_usd is None:
        return None, None
    if merv.empty or ypf_ars.empty or ypf_usd.empty:
        return None, None

    def _norm_index(s: pd.Series) -> pd.Series:
        s2 = s.copy()
        s2.index = pd.to_datetime(s2.index, errors="coerce")
        try:
            s2.index = s2.index.tz_localize(None)
        except Exception:
            pass
        s2.index = s2.index.normalize()
        return s2

    merv = _norm_index(merv).rename("^MERV")
    ypf_ars = _norm_index(ypf_ars).rename("YPFD.BA")
    ypf_usd = _norm_index(ypf_usd).rename("YPF")

    df = pd.concat([merv, ypf_ars, ypf_usd], axis=1).dropna()
    if df.empty:
        return None, None

    last_date = df.index.max()
    last = df.loc[last_date]

    ccl_ypf = float(last["YPFD.BA"]) / float(last["YPF"])
    if not np.isfinite(ccl_ypf) or ccl_ypf <= 0:
        return None, None

    merval_usd = float(last["^MERV"]) / ccl_ypf
    return float(merval_usd), pd.to_datetime(last_date)


# ============================================================
# IPIM (INDEC) — último dato Manufacturas v/m
# ============================================================
IPIM_URL = "https://www.indec.gob.ar/ftp/cuadros/economia/indice_ipim.csv"
IPIM_HEADER_CODE = "d_productos_manufacturados"

@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def _last_ipim_ng_vm():
    """
    Devuelve (ultimo_vm_en_% , periodo_as_timestamp) para IPIM Manufacturas.
    (El nombre histórico de la función se mantiene para no romper imports.)
    """
    try:
        r = requests.get(IPIM_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        raw = r.content
    except Exception:
        return None, None

    df = None
    for sep in [";", ",", "\t"]:
        try:
            tmp = pd.read_csv(io.BytesIO(raw), sep=sep, engine="python")
            if tmp is None or tmp.empty:
                continue
            cols = [c.strip().lower() for c in tmp.columns]
            if "periodo" in cols and "nivel_general_aperturas" in cols and "indice_ipim" in cols:
                df = tmp
                break
        except Exception:
            continue

    if df is None or df.empty:
        return None, None

    out = df[["periodo", "nivel_general_aperturas", "indice_ipim"]].copy()
    out = out.rename(
        columns={
            "periodo": "Periodo_raw",
            "nivel_general_aperturas": "Apertura_raw",
            "indice_ipim": "Indice_raw",
        }
    )

    out["Apertura"] = (
        out["Apertura_raw"].astype(str).str.strip().str.lower()
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(" ", "_", regex=False)
        .str.replace("__", "_", regex=False)
    )

    s_per = out["Periodo_raw"].astype(str).str.strip()
    per = pd.to_datetime(s_per, format="%Y-%m-%d", errors="coerce")
    out["Periodo"] = per.dt.to_period("M").dt.to_timestamp(how="start")

    s = out["Indice_raw"].astype(str).str.strip()
    s = s.str.replace("\u00a0", " ", regex=False).str.replace(" ", "", regex=False)
    has_comma = s.str.contains(",", na=False)
    s.loc[has_comma] = s.loc[has_comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    out["Indice"] = pd.to_numeric(s, errors="coerce")

    out = (
        out.dropna(subset=["Periodo", "Apertura", "Indice"])
        .sort_values(["Apertura", "Periodo"])
        .reset_index(drop=True)
    )
    if out.empty:
        return None, None

    out["v_m"] = out.groupby("Apertura")["Indice"].pct_change(1) * 100

    hdr = out[out["Apertura"] == IPIM_HEADER_CODE].dropna(subset=["v_m"]).sort_values("Periodo")
    if hdr.empty:
        return None, None

    last_period = pd.to_datetime(hdr["Periodo"].iloc[-1])
    last_vm = float(hdr["v_m"].iloc[-1])
    return last_vm, last_period


# ============================================================
# NEWS TICKER (RSS + scoring)
# ============================================================
NEWS_FEEDS = [
    "https://www.ambito.com/rss/pages/economia.xml",
]

NEWS_WEIGHTS = {
    "bcra": 4,
    "indec": 10,
    "inflación": 4,
    "inflacion": 4,
    "ipc": 4,
    "ipim": 3,
    "emae": 4,
    "pbi": 4,
    "fmi": 4,
    "deuda": 5,
    "empleo": 5,
    "salarios": 5,
    "china": 10,
    "licitación": 3,
    "licitacion": 3,
    "bono": 5,
    "bonos": 5,
    "riesgo país": 10,
    "riesgo pais": 10,
    "reservas": 3,
    "dólar": 3,
    "dolar": 3,
    "monetaria": 3,
    "cambiaria": 2,
    "fiscal": 2,
    "merval": 10,
    "recaudación": 2,
    "recaudacion": 2,
    "actividad": 5,
    "industria": 20,
    "importaciones": 10,
    "exportaciones": 10,
    "caputo": 10,
    "milei": 10,
    "quirno": 10,
    "uia": 50,
    "ministerio": 1,
    "economía": 1,
    "economia": 1,
    "gobierno": 1,
    "supermercado": -4,
    "descuentos": -3,
    "verano": -3,
    "hamaca": -4,
    "ofertas": -3,
    "oferta": -5,
    "limpieza": -3,
    "plazo fijo": -2,
    "banco": -1,
    "crucero": -5,
    "turismo": -3,
    "vacaciones": -4,
    "fin de semana": -3,
    "gastronomía": -3,
    "gastronomia": -3,
    "restaurante": -3,
}

def _news_score_title(title: str) -> int:
    t = str(title).lower()
    score = 0
    for k, w in NEWS_WEIGHTS.items():
        if k in t:
            score += w
    if "argentina" in t:
        score += 1
    return int(score)


def _parse_rss(xml_bytes: bytes, feed_url: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        channel = root.find(".//channel")
    if channel is None:
        return []

    out: list[dict] = []
    for it in channel.findall("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        if not title or not link:
            continue

        dt = None
        if pub:
            try:
                dt = parsedate_to_datetime(pub)
            except Exception:
                dt = None

        out.append(
            {
                "title": title,
                "link": link,
                "published": dt,
                "source": urlparse(feed_url).netloc.replace("www.", ""),
                "feed": feed_url,
            }
        )
    return out


@st.cache_data(ttl=15 * 60, show_spinner=False)
def _load_news_scored(feeds: list[str] | None = None, max_items_total: int = 50) -> pd.DataFrame:
    feeds = feeds or NEWS_FEEDS
    items: list[dict] = []
    for url in feeds:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            items.extend(_parse_rss(r.content, url))
        except Exception:
            continue

    df = pd.DataFrame(items)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["link"], keep="first").copy()
    if "published" in df.columns:
        df["published"] = pd.to_datetime(df["published"], errors="coerce")

    df["score"] = df["title"].apply(_news_score_title).astype(int)
    df = df.sort_values(["score", "published"], ascending=[False, False], na_position="last")
    return df.head(max_items_total).reset_index(drop=True)


def _build_news_ticker_html(df_news: pd.DataFrame, top_n: int = 12) -> str:
    if df_news is None or df_news.empty:
        return ""

    df_top = df_news[df_news["score"] > 0].head(top_n)
    if df_top.empty:
        df_top = df_news.head(min(top_n, 8))

    parts: list[str] = []
    for _, r in df_top.iterrows():
        title = str(r.get("title", "")).strip()
        link = str(r.get("link", "")).strip()
        src = str(r.get("source", "")).strip()
        if not title or not link:
            continue

        parts.append(
            "<span class='tk-item'>"
            f"<a class='tk-link' href='{link}' target='_blank' rel='noopener noreferrer'>"
            f"📌 {title} <span class='tk-src'>— {src}</span>"
            "</a>"
            "</span>"
        )

    return "<span class='tk-sep'>•</span>".join(parts)


# ============================================================
# KPI card helpers
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
          /* ===== Fondo celeste global ===== */
          section.main { background: #eaf3fb !important; }
          div[data-testid="stAppViewContainer"]{ background: #eaf3fb !important; }
          div[data-testid="stHeader"]{ background: #eaf3fb !important; }
          div[data-testid="stSidebar"]{ background: #eaf3fb !important; }

          .macrohome-shell{
            max-width: 1000px;
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

          .mh-pills-marker{}
          .mh-kpis-marker{}

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

          .ticker-wrap{
            width: 82%;
            margin: 10px auto 12px auto;
            background:#0b0b0b;
            border-radius:12px;
            overflow:hidden;
            border: 1px solid rgba(255,255,255,.10);
          }

          .ticker-viewport{ padding: 9px 0; }

          .ticker-track{
            display:inline-block;
            white-space:nowrap;
            animation:tickerScroll 75s linear infinite;
            will-change: transform;
          }
          @keyframes tickerScroll{
            from{ transform:translateX(0%); }
            to{ transform:translateX(-50%); }
          }

          /* ===== Bloomberg-ish ===== */
          .tk-item{
            display:inline-block;
            padding: 0 8px;
            font-family: Inter, "Segoe UI", -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            font-size: 13.5px;
            font-weight: 500;
            letter-spacing: 0.15px;
            color: rgba(255,255,255,0.92) !important;
          }
          .tk-sep{
            margin: 0 6px;
            color: rgba(255,255,255,.28) !important;
          }
          .tk-link{
            color: rgba(255,255,255,0.92) !important;
            text-decoration:none !important;
          }
          .tk-link:hover{
            text-decoration: none !important;
            color: rgba(170,215,255,0.98) !important;
          }
          .tk-src{
            opacity: 0.60;
            font-weight: 400;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="macrohome-shell">', unsafe_allow_html=True)


    # Placeholder de frase
    fact_ph = st.empty()
    fact_ph.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    # Placeholder ticker
    ticker_ph = st.empty()

    # Título y botones
    st.markdown("<div class='macrohome-title'>Macroeconomía</div>", unsafe_allow_html=True)

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
        if st.button("📈  Finanzas", use_container_width=True, key="mh_btn_fin"):
            go_to("finanzas")

    st.markdown("<div class='mh-kpis-marker'></div>", unsafe_allow_html=True)

    # KPIs (con espacio entre filas)
    r1c1, r1c2, r1c3, r1c4 = st.columns(4, gap="large")
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    r2c1, r2c2, r2c3, r2c4 = st.columns(4, gap="large")

    ph_fx = r1c1.empty()
    ph_tasa = r1c2.empty()
    ph_ipc = r1c3.empty()
    ph_riesgo = r1c4.empty()

    ph_brecha = r2c1.empty()
    ph_res = r2c2.empty()
    ph_ipim = r2c3.empty()
    ph_merv = r2c4.empty()

    with ph_fx.container(): _kpi_card("—", "TC Mayorista", "—")
    with ph_tasa.container(): _kpi_card("—", "Adelantos a Empresas", "—")
    with ph_ipc.container(): _kpi_card("—", "IPC", "—")
    with ph_riesgo.container(): _kpi_card("—", "Riesgo País", "—")
    with ph_brecha.container(): _kpi_card("—", "Brecha Cambiaria", "—")
    with ph_res.container(): _kpi_card("—", "Reservas Internacionales", "—")
    with ph_ipim.container(): _kpi_card("—", "IPIM Manufacturas", "—")
    with ph_merv.container(): _kpi_card("—", "MERVAL (USD)", "—")

    # --- SIEMPRE definir results antes de todo
    results: dict = {}

    tasks = {
        "fx": _last_tc,
        "tasa": _last_tasa,
        "ipc": _last_ipc_bcra,
        "riesgo": _last_riesgo_pais,
        "reservas": _last_reservas,
        "ipim": _last_ipim_ng_vm,
        "merval": _last_merval_usd,
        "news": _load_news_scored,
    }

    # Carga en paralelo
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fn): k for k, fn in tasks.items()}
        for fut in as_completed(futs):
            k = futs[fut]
            try:
                results[k] = fut.result()
            except Exception:
                results[k] = None

    # ✅ brecha afuera del pool (pero results ya existe)
    try:
        results["brecha"] = _last_brecha_from_macro_fx()
    except Exception:
        results["brecha"] = (None, None)


    # Carga en paralelo
    with ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(fn): k for k, fn in tasks.items()}
        for fut in as_completed(futs):
            k = futs[fut]
            try:
                results[k] = fut.result()
            except Exception:
                results[k] = None

    # apagar loading y frase
    fact_ph.empty()

    # Ticker
    df_news = results.get("news")
    news_line = _build_news_ticker_html(df_news, top_n=12) if isinstance(df_news, pd.DataFrame) else ""
    if news_line:
        ticker_ph.markdown(
            f"""
            <div class="ticker-wrap">
              <div class="ticker-viewport">
                <div class="ticker-track">
                  {news_line}<span class='tk-sep'>•</span>{news_line}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        ticker_ph.markdown(
            """
            <div class="ticker-wrap">
              <div class="ticker-viewport" style="padding:10px 14px; color:#cbd5e1; font-weight:700; font-family: Inter, 'Segoe UI', Arial, sans-serif;">
                📌 Sin titulares disponibles (reintenta en unos minutos)
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Resultados
    fx = results.get("fx")
    fx_val, fx_date = fx if isinstance(fx, tuple) and len(fx) == 2 else (None, None)

    tasa = results.get("tasa")
    tasa_val, tasa_date = tasa if isinstance(tasa, tuple) and len(tasa) == 2 else (None, None)

    ipc = results.get("ipc")
    ipc_val, ipc_date = ipc if isinstance(ipc, tuple) and len(ipc) == 2 else (None, None)

    riesgo = results.get("riesgo")
    riesgo_val, riesgo_date = riesgo if isinstance(riesgo, tuple) and len(riesgo) == 2 else (None, None)

    brecha = results.get("brecha")
    brecha_val, brecha_date = brecha if isinstance(brecha, tuple) and len(brecha) == 2 else (None, None)

    resv = results.get("reservas")
    res_val, res_date = resv if isinstance(resv, tuple) and len(resv) == 2 else (None, None)

    ipim = results.get("ipim")
    ipim_vm, ipim_date = ipim if isinstance(ipim, tuple) and len(ipim) == 2 else (None, None)

    merv = results.get("merval")
    mervusd_val, mervusd_date = merv if isinstance(merv, tuple) and len(merv) == 2 else (None, None)

    # Render cards
    with ph_fx.container():
        if fx_val is not None and fx_date is not None:
            _kpi_card(
                f"<span class='kpi-prefix'>ARS/USD</span>{_fmt_thousands_es_int(fx_val)}",
                "TC Mayorista",
                fx_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "TC Mayorista", "—")

    with ph_tasa.container():
        if tasa_val is not None and tasa_date is not None:
            _kpi_card(
                f"{_fmt_pct_es(tasa_val)}<span class='kpi-suffix'>TNA</span>",
                "Adelantos a Empresas",
                tasa_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "Adelantos a Empresas", "—")

    with ph_ipc.container():
        if ipc_val is not None and ipc_date is not None:
            _kpi_card(_fmt_pct_es(ipc_val * 100), "IPC", _fmt_mes_anio_es(ipc_date))
        else:
            _kpi_card("—", "IPC", "—")

    with ph_riesgo.container():
        if riesgo_val is not None and riesgo_date is not None:
            _kpi_card(_fmt_thousands_es_int(riesgo_val), "Riesgo País", riesgo_date.strftime("%d/%m/%Y"))
        else:
            _kpi_card("—", "Riesgo País", "—")

    with ph_brecha.container():
        if brecha_val is not None and brecha_date is not None:
            _kpi_card(_fmt_pct_es(brecha_val, 1), "Brecha Cambiaria", brecha_date.strftime("%d/%m/%Y"))
        else:
            _kpi_card("—", "Brecha Cambiaria", "—")

    with ph_res.container():
        if res_val is not None and res_date is not None:
            _kpi_card(
                f"<span class='kpi-prefix'>USD</span>{_fmt_thousands_es_int(res_val)}<span class='kpi-suffix'>mill</span>",
                "Reservas Internacionales",
                res_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "Reservas Internacionales", "—")

    # ✅ CAMBIO: label siempre "IPIM Manufacturas"
    with ph_ipim.container():
        if ipim_vm is not None and ipim_date is not None:
            _kpi_card(_fmt_pct_es(ipim_vm, 1), "IPIM Manufacturas", _fmt_mes_anio_es(ipim_date))
        else:
            _kpi_card("—", "IPIM Manufacturas", "—")

    with ph_merv.container():
        if mervusd_val is not None and mervusd_date is not None:
            _kpi_card(
                f"<span class='kpi-prefix'>USD</span>{_fmt_thousands_es_int(mervusd_val)}",
                "MERVAL (USD)",
                mervusd_date.strftime("%d/%m/%Y"),
            )
        else:
            _kpi_card("—", "MERVAL (USD)", "—")

    st.markdown("</div>", unsafe_allow_html=True)
