import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import textwrap
import io
import requests
import streamlit.components.v1 as components

from ui.common import safe_pct

# ✅ services
from services.market_data import get_ccl_ypf_df

# yfinance opcional (solo para ^MERV)
try:
    import yfinance as yf
except Exception:
    yf = None


# ============================================================
# Helpers (mismos que FX)
# ============================================================
def _arrow_cls(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ("", "")
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")


# ============================================================
# EMBI (BCRA XLSX) — loader robusto
# ============================================================
EMBI_XLSX_URL = (
    "https://bcrdgdcprod.blob.core.windows.net/documents/entorno-internacional/documents/"
    "Serie_Historica_Spread_del_EMBI.xlsx"
)

EMBI_LAST_COL = "Venezuela"      # hasta esta columna inclusive
EMBI_DEFAULT_SERIE = "Argentina" # default


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _load_embi_wide_from_bcra() -> pd.DataFrame:
    """
    Devuelve DF wide: Date + columnas países/regiones (B..T, hasta Venezuela)
    """
    try:
        r = requests.get(EMBI_XLSX_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        raw = r.content
    except Exception:
        return pd.DataFrame()

    try:
        df = pd.read_excel(io.BytesIO(raw), header=1)  # header=1 => fila 2
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # detectar columna fecha
    date_col = None
    for c in df.columns:
        if str(c).strip().lower() in ["fecha", "date"]:
            date_col = c
            break
    if date_col is None:
        date_col = df.columns[0]

    df = df.rename(columns={date_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["Date"]).sort_values("Date")

    # cortar hasta Venezuela (inclusive)
    cols = list(df.columns)
    if EMBI_LAST_COL in cols:
        last_idx = cols.index(EMBI_LAST_COL)
        keep = ["Date"] + cols[1:last_idx + 1]
        df = df[keep].copy()
    else:
        keep = ["Date"] + [c for c in cols[1:] if not str(c).lower().startswith("unnamed")]
        df = df[keep].copy()

    # pasar valores a numérico (acepta coma/punto)
    for c in df.columns:
        if c == "Date":
            continue
        s = df[c].astype(str).str.strip()
        s = s.replace({"N/A": np.nan, "NA": np.nan, "": np.nan, "nan": np.nan})

        has_comma = s.str.contains(",", na=False)
        s.loc[has_comma] = s.loc[has_comma].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(s, errors="coerce")

    return df.reset_index(drop=True)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _load_embi_long_from_bcra() -> pd.DataFrame:
    """
    Devuelve long: Date, Serie, Value (EN PUNTOS => x100)
    """
    wide = _load_embi_wide_from_bcra()
    if wide is None or wide.empty:
        return pd.DataFrame(columns=["Date", "Serie", "Value"])

    value_cols = [c for c in wide.columns if c != "Date"]
    long = wide.melt(id_vars=["Date"], value_vars=value_cols, var_name="Serie", value_name="Value")
    long["Serie"] = long["Serie"].astype(str).str.strip()
    long["Value"] = pd.to_numeric(long["Value"], errors="coerce")
    long = long.dropna(subset=["Date", "Serie", "Value"]).sort_values("Date")

    # ✅ pasar a puntos
    long["Value"] = long["Value"] * 100.0
    return long.reset_index(drop=True)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _load_riesgo_pais() -> pd.DataFrame:
    """
    DataFrame: Date, value (puntos EMBI Argentina)
    """
    long = _load_embi_long_from_bcra()
    if long is None or long.empty:
        return pd.DataFrame(columns=["Date", "value"])

    if EMBI_DEFAULT_SERIE in long["Serie"].unique():
        s = long[long["Serie"] == EMBI_DEFAULT_SERIE][["Date", "Value"]].copy()
    else:
        first = long["Serie"].dropna().unique().tolist()
        if not first:
            return pd.DataFrame(columns=["Date", "value"])
        s = long[long["Serie"] == first[0]][["Date", "Value"]].copy()

    s = s.rename(columns={"Value": "value"})
    s["Date"] = pd.to_datetime(s["Date"], errors="coerce").dt.normalize()
    s["value"] = pd.to_numeric(s["value"], errors="coerce")
    s = s.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)
    return s


# ============================================================
# MERVAL ARS (^MERV) desde Yahoo
# ============================================================
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _load_merval_ars(start: str = "1990-01-01") -> pd.DataFrame:
    if yf is None:
        return pd.DataFrame(columns=["Date", "merval_ars"])

    try:
        dl = yf.download(
            "^MERV",
            start=start,
            progress=False,
            auto_adjust=False,
            interval="1d",
            group_by="column",
            threads=True,
        )
    except Exception:
        dl = None

    if dl is None or getattr(dl, "empty", True):
        try:
            dl = yf.download(
                "^MERV",
                period="max",
                progress=False,
                auto_adjust=False,
                interval="1d",
                group_by="column",
                threads=True,
            )
        except Exception:
            dl = None

    if dl is None or getattr(dl, "empty", True):
        return pd.DataFrame(columns=["Date", "merval_ars"])

    s = None
    if isinstance(dl, pd.DataFrame):
        if isinstance(dl.columns, pd.MultiIndex):
            if ("Close", "^MERV") in dl.columns:
                s = dl[("Close", "^MERV")]
            else:
                if "Close" in dl.columns.get_level_values(0):
                    tmp = dl.xs("Close", axis=1, level=0)
                    if tmp.shape[1] == 1:
                        s = tmp.iloc[:, 0]
                    elif "^MERV" in tmp.columns:
                        s = tmp["^MERV"]
        else:
            if "Close" in dl.columns:
                s = dl["Close"]

    if s is None:
        return pd.DataFrame(columns=["Date", "merval_ars"])

    s = pd.to_numeric(s, errors="coerce")
    idx = pd.to_datetime(s.index, errors="coerce")
    try:
        idx = idx.tz_localize(None)
    except Exception:
        pass

    out = pd.DataFrame({"Date": idx, "merval_ars": s.values})
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.normalize()
    out["merval_ars"] = pd.to_numeric(out["merval_ars"], errors="coerce")
    out = (
        out.dropna(subset=["Date", "merval_ars"])
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )
    return out


# ============================================================
# MERVAL USD (MERVAL ARS / CCL)
# ============================================================
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def _load_merval_usd() -> pd.DataFrame:
    merv = _load_merval_ars(start="1990-01-01")
    if merv is None or merv.empty:
        return pd.DataFrame(columns=["Date", "value", "merval_ars", "ccl"])

    ccl = get_ccl_ypf_df(start="2000-01-01", prefer_adj=False)  # Date, value
    if ccl is None or ccl.empty:
        return pd.DataFrame(columns=["Date", "value", "merval_ars", "ccl"])

    ccl = ccl.copy()
    ccl["Date"] = pd.to_datetime(ccl["Date"], errors="coerce").dt.normalize()
    ccl["value"] = pd.to_numeric(ccl["value"], errors="coerce")
    ccl = ccl.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)
    ccl = ccl.rename(columns={"value": "ccl"})

    left = merv.sort_values("Date").reset_index(drop=True)
    right = ccl.sort_values("Date").reset_index(drop=True)

    merged = pd.merge_asof(
        left,
        right,
        on="Date",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    merged["merval_ars"] = pd.to_numeric(merged["merval_ars"], errors="coerce")
    merged["ccl"] = pd.to_numeric(merged["ccl"], errors="coerce")
    merged = merged.dropna(subset=["Date", "merval_ars", "ccl"]).sort_values("Date").reset_index(drop=True)

    merged["value"] = (merged["merval_ars"] / merged["ccl"]).replace([np.inf, -np.inf], np.nan)

    out = merged[["Date", "value", "merval_ars", "ccl"]].dropna(subset=["Date", "value"]).reset_index(drop=True)
    return out


# ============================================================
# RENDER
# ============================================================
def render_finanzas(go_to=None):

    st.markdown(
        textwrap.dedent(
            """
        <style>
          .fx-wrap{
            background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
            border: 1px solid #dfeaf6;
            border-radius: 22px;
            padding: 12px;
            box-shadow:
              0 10px 24px rgba(15, 55, 100, 0.16),
              inset 0 0 0 1px rgba(255,255,255,0.55);
          }
          .fx-title-row{ display:flex; align-items:center; gap:12px; margin-bottom:8px; padding-left:4px; }
          .fx-icon-badge{
            width:64px; height:52px; border-radius:14px;
            background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
            border: 1px solid rgba(15,23,42,0.10);
            display:flex; align-items:center; justify-content:center;
            box-shadow: 0 8px 14px rgba(15,55,100,0.12);
            font-size: 32px; flex:0 0 auto;
          }
          .fx-title{ font-size:23px; font-weight:900; letter-spacing:-0.01em; color:#14324f; margin:0; line-height:1.0; }
          .fx-card{
            background: rgba(255,255,255,0.94);
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 18px;
            padding: 14px 14px 12px 14px;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
          }
          .fx-row{ display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:14px; }
          .fx-value{ font-size:46px; font-weight:950; letter-spacing:-0.02em; color:#14324f; line-height:0.95; }
          .fx-meta{
            font-size:13px; color:#2b4660; font-weight:700;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
          }
          .fx-meta .sep{ opacity:0.40; padding:0 6px; }
          .fx-pills{ display:flex; gap:10px; justify-content:flex-end; align-items:center; white-space:nowrap; }
          .fx-pill{
            display:inline-flex; align-items:center; gap:8px;
            padding:7px 10px; border-radius:12px;
            border:1px solid rgba(15,23,42,0.10);
            font-size:13px; font-weight:700;
            box-shadow:0 6px 10px rgba(15,55,100,0.08);
          }
          .fx-pill.red{ background: linear-gradient(180deg, rgba(220,38,38,0.08) 0%, rgba(220,38,38,0.05) 100%); }
          .fx-pill.green{ background: linear-gradient(180deg, rgba(22,163,74,0.10) 0%, rgba(22,163,74,0.06) 100%); }
          .fx-up{ color:#168a3a; font-weight:900; }
          .fx-down{ color:#cc2e2e; font-weight:900; }
          .fx-arrow{ width:14px; text-align:center; font-weight:900; }
          .fx-panel-title{
            font-size:12px; font-weight:900; color: rgba(20,50,79,0.78);
            margin:0 0 6px 2px; letter-spacing:0.01em;
          }
          .fx-panel-gap{ height:16px; }
          .fx-panel-wrap{
            background: rgba(230, 243, 255, 0.55);
            border: 1px solid rgba(15, 55, 100, 0.10);
            border-radius: 22px;
            padding: 16px 16px 26px 16px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }
          .fx-panel-wrap div[data-testid="stSelectbox"],
          .fx-panel-wrap div[data-testid="stMultiSelect"],
          .fx-panel-wrap div[data-testid="stSlider"],
          .fx-panel-wrap div[data-testid="stPlotlyChart"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
          }

          /* =========================================================
             BaseWeb Select: FORZAR fondo azul + texto blanco
             ========================================================= */
          .fx-panel-wrap div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
          .fx-panel-wrap div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div{
            background: #0b2a55 !important;
            border-radius: 16px !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            box-shadow: 0 10px 18px rgba(15,55,100,0.10) !important;
          }

          .fx-panel-wrap div[data-testid="stSelectbox"] div[data-baseweb="select"] *,
          .fx-panel-wrap div[data-testid="stMultiSelect"] div[data-baseweb="select"] *{
            color: #ffffff !important;
            fill: #ffffff !important;
            font-weight: 800 !important;
          }

          .fx-panel-wrap div[data-testid="stSelectbox"] svg,
          .fx-panel-wrap div[data-testid="stMultiSelect"] svg{
            fill: #ffffff !important;
          }

          /* dropdown listbox oscuro + texto blanco */
          .fx-panel-wrap div[role="listbox"]{ background:#0b2a55 !important; }
          .fx-panel-wrap div[role="listbox"] *{ color:#ffffff !important; }

          /* chips multiselect */
          .fx-panel-wrap span[data-baseweb="tag"]{
            background: rgba(255,255,255,0.12) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
          }
          .fx-panel-wrap span[data-baseweb="tag"] *{
            color:#ffffff !important; fill:#ffffff !important;
          }

          @media (max-width: 900px){
            .fx-row{ grid-template-columns: 1fr; row-gap: 10px; }
            .fx-meta{ white-space: normal; }
            .fx-pills{ justify-content: flex-start; }
          }
        </style>
        """
        ),
        unsafe_allow_html=True,
    )


    
    
    # ============================================================
    # VISOR DE PRECIOS (Yahoo) — estilo Bloomberg (1 fila, sin emojis)
    # - Loop perfecto (vuelve a ARS/USD)
    # - Sin flechas: variación diaria colorea (verde fuerte / rojo)
    # - ^TNX: solo nivel (ej 4,278%), sin variación
    # ============================================================

    import html as _html

    def _fmt_es_num(x: float, dec: int = 2) -> str:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        s = f"{x:,.{dec}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_pct_es(x: float, dec: int = 1) -> str:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        return _fmt_es_num(x, dec) + "%"

    def _get_last_prev_close(df: pd.DataFrame) -> tuple[float | None, float | None]:
        if df is None or df.empty:
            return (None, None)

        col = "Adj Close" if "Adj Close" in df.columns else ("Close" if "Close" in df.columns else None)
        if col is None:
            return (None, None)

        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            return (None, None)
        last = float(s.iloc[-1])
        prev = float(s.iloc[-2]) if len(s) >= 2 else None
        return (last, prev)

    def _download_many(tickers: list[str]) -> dict[str, pd.DataFrame]:
        if yf is None:
            return {}
        try:
            dl = yf.download(
                tickers=" ".join(tickers),
                period="10d",
                interval="1d",
                auto_adjust=False,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception:
            return {}

        out: dict[str, pd.DataFrame] = {}
        if dl is None or getattr(dl, "empty", True):
            return out

        # 1 ticker
        if isinstance(dl, pd.DataFrame) and not isinstance(dl.columns, pd.MultiIndex):
            out[tickers[0]] = dl.copy()
            return out

        # multi tickers
        if isinstance(dl.columns, pd.MultiIndex):
            levels0 = list(map(str, dl.columns.get_level_values(0).unique()))
            if any(t in levels0 for t in tickers):
                # (ticker, field)
                for t in tickers:
                    if t in dl.columns.get_level_values(0):
                        out[t] = dl[t].copy()
            else:
                # (field, ticker)
                for t in tickers:
                    if t in dl.columns.get_level_values(1):
                        out[t] = dl.xs(t, axis=1, level=1).copy()
        return out

    def _build_items_html_from_yahoo() -> str:
        """
        Devuelve HTML con spans por item:
        - label: bold
        - value: normal
        - chg: coloreado (verde/rojo) sin flechas
        - ^TNX: solo value en %
        """
        cfg = [
            ("ARS/USD", "ARS=X", "fx_ars"),
            ("BRL/USD", "BRL=X", "fx_brl"),
            ("DXY", "DX-Y.NYB", "index"),
            ("S&P 500", "^GSPC", "eq"),
            ("Merval", "^MERV", "eq"),
            ("EWZ", "EWZ", "eq"),
            ("FXI", "FXI", "eq"),
            ("BTC", "BTC-USD", "crypto"),
            ("WTI", "CL=F", "cmd"),
            ("Oro", "GC=F", "cmd"),
            ("Soja", "ZS=F", "cmd"),
            ("Trigo", "ZW=F", "cmd"),
        ]

        tickers = [t for _, t, _ in cfg]
        data = _download_many(tickers)

        parts: list[str] = []
        for label, tkr, kind in cfg:
            df = data.get(tkr)
            last, prev = _get_last_prev_close(df)

            safe_label = _html.escape(label)

            if last is None:
                parts.append(
                    f'<span class="bb-item"><span class="bb-lab">{safe_label}</span>'
                    f'<span class="bb-val">—</span></span>'
                )
                continue

            # Formato valor

            if kind == "fx_ars":
                val_txt = _fmt_es_num(last, 0)
            elif kind == "fx_brl":
                val_txt = _fmt_es_num(last, 2)
            elif kind == "crypto":
                val_txt = _fmt_es_num(last, 0)
            else:
                val_txt = _fmt_es_num(last, 2)

            # Variación diaria %
            chg_pct = None
            if prev is not None and prev != 0:
                chg_pct = (last / prev - 1) * 100

            if chg_pct is None or (isinstance(chg_pct, float) and np.isnan(chg_pct)):
                parts.append(
                    f'<span class="bb-item"><span class="bb-lab">{safe_label}</span>'
                    f'<span class="bb-val">{val_txt}</span>'
                    f'<span class="bb-chg bb-flat">—</span></span>'
                )
                continue

            chg_txt = _fmt_pct_es(chg_pct, 1)
            chg_cls = "bb-pos" if chg_pct >= 0 else "bb-neg"

            parts.append(
                f'<span class="bb-item">'
                f'  <span class="bb-lab">{safe_label}</span>'
                f'  <span class="bb-val">{val_txt}</span>'
                f'  <span class="bb-chg {chg_cls}">({chg_txt})</span>'
                f'</span>'
            )

        # Separador tipo terminal
        return '<span class="bb-sep">•</span>'.join(parts)

    def _render_ticker_tape_bloomberg(items_html: str, speed_sec: int = 34, height: int = 44):
        # duplicado para loop perfecto: -50% porque hay 2 copias idénticas
        html = f"""
        <div class="bb-wrap" role="region" aria-label="Visor de precios">
          <div class="bb-track">
            <div class="bb-inner">
              <div class="bb-line">{items_html}</div>
              <div class="bb-line" aria-hidden="true">{items_html}</div>
            </div>
          </div>
        </div>

        <style>
          .bb-wrap {{
            width: 100%;
            overflow: hidden;
            border-radius: 14px;
            padding: 7px 0;
            background: linear-gradient(180deg, rgba(8,14,24,0.98) 0%, rgba(5,10,18,0.98) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow: 0 14px 26px rgba(0,0,0,0.22);
            margin: 2px 0 10px 0;
          }}

          .bb-track {{
            position: relative;
            white-space: nowrap;
          }}

          .bb-inner {{
            display: inline-flex;
            align-items: center;
            gap: 40px;
            will-change: transform;
            animation: bb-scroll {speed_sec}s linear infinite;
            padding-left: 100%;
          }}

          @keyframes bb-scroll {{
            0%   {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
          }}

          .bb-wrap:hover .bb-inner {{
            animation-play-state: paused;
          }}

          .bb-line {{
            font-family: "Inter Tight", "Inter", "IBM Plex Sans", "Roboto Condensed",
                        "Segoe UI", Arial, sans-serif;
          }}

          .bb-item {{
            display: inline-flex;
            align-items: baseline;
            gap: 8px;
            padding: 0 2px;
          }}

          .bb-lab {{
            font-weight: 900;
            font-size: 14px; 
            color: #ffffff;
            letter-spacing: 0.02em;
          }}

          .bb-val {{
            color: #ffffff;
            font-weight: 700;
          }}

          .bb-chg {{
  font-weight: 900;
  font-size: 14px;                 /* MÁS GRANDE */
  letter-spacing: 0.02em;
          }}

          .bb-pos {{
  color: #00ff87;                  /* verde Bloomberg */
  text-shadow: 0 0 6px rgba(0,255,135,0.35);
          }}

          .bb-neg {{
  color: #ff2e2e;                  /* rojo Bloomberg */
  text-shadow: 0 0 6px rgba(255,46,46,0.35)
          }}

          .bb-flat {{
  color: rgba(235,245,255,0.55);
  font-size: 13px;
          }}

          .bb-sep {{
  color: rgba(255,255,255,0.18);
  padding: 0 10px;
          }}
        </style>
        """
        components.html(html, height=height)

    # ---- Construye desde Yahoo + render (loop perfecto) ----
    with st.spinner("Cargando visor de precios..."):
        items_html = _build_items_html_from_yahoo()
    _render_ticker_tape_bloomberg(items_html, speed_sec=34, height=46)

    # Espaciado fino
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


    # ============================================================
    # RIESGO PAÍS (EMBI) — ARRIBA
    # ============================================================

    with st.spinner("Cargando Riesgo País (EMBI)..."):
        embi_long = _load_embi_long_from_bcra()

    if embi_long is None or embi_long.empty:
        st.warning("Sin datos de Riesgo País (EMBI).")
        return

    with st.container():
        # ✅ marker único
        st.markdown("<div id='embi_panel_marker'></div>", unsafe_allow_html=True)

        # ✅ aplica panel-wrap al bloque MÁS EXTERNO => envuelve TODO
        components.html(
            """
            <script>
            (function() {
              function applyPanelClass() {
                const doc = window.parent.document;
                const m = doc.getElementById('embi_panel_marker');
                if (!m) return;

                const blocks = [];
                let el = m;
                while (el) {
                  if (el.matches && el.matches('div[data-testid="stVerticalBlock"]')) blocks.push(el);
                  el = el.parentElement;
                }
                if (!blocks.length) return;

                const target = blocks[blocks.length - 1];
                target.classList.add('fx-panel-wrap');
              }

              applyPanelClass();
              let i = 0;
              const t = setInterval(() => {
                applyPanelClass();
                if (++i > 20) clearInterval(t);
              }, 150);
            })();
            </script>
            """,
            height=0,
        )

        embi_long = embi_long.copy()
        embi_long["Date"] = pd.to_datetime(embi_long["Date"], errors="coerce").dt.normalize()
        embi_long["Value"] = pd.to_numeric(embi_long["Value"], errors="coerce")
        embi_long["Serie"] = embi_long["Serie"].astype(str).str.strip()
        embi_long = embi_long.dropna(subset=["Date", "Serie", "Value"]).sort_values("Date")

        series_all = sorted(embi_long["Serie"].unique().tolist())
        if not series_all:
            st.warning("Sin series EMBI disponibles.")
            return

        default_main = EMBI_DEFAULT_SERIE if EMBI_DEFAULT_SERIE in series_all else series_all[0]
        defaults = [default_main]

        if "embi_medida" not in st.session_state:
            st.session_state["embi_medida"] = "Nivel"
        if "embi_vars" not in st.session_state or not st.session_state.get("embi_vars"):
            st.session_state["embi_vars"] = defaults

        header_ph = st.empty()
        header_gap_ph = st.empty()

        # --- header usa lo último del estado actual ---
        main_series = st.session_state["embi_vars"][0] if st.session_state.get("embi_vars") else defaults[0]
        main = embi_long[embi_long["Serie"] == main_series].sort_values("Date")

        last_date = pd.to_datetime(main["Date"].iloc[-1]) if not main.empty else pd.NaT
        last_val  = float(main["Value"].iloc[-1]) if not main.empty else np.nan

        def _asof_val(df_: pd.DataFrame, target: pd.Timestamp):
            tt = df_.dropna(subset=["Date", "Value"]).sort_values("Date")
            tt = tt[tt["Date"] <= target]
            if tt.empty:
                return None
            return float(tt["Value"].iloc[-1])

        vm = va = None
        if pd.notna(last_date) and pd.notna(last_val):
            m = _asof_val(main, last_date - pd.Timedelta(days=30))
            y = _asof_val(main, last_date - pd.Timedelta(days=365))
            vm = None if m is None else (last_val / m - 1) * 100
            va = None if y is None else (last_val / y - 1) * 100

        a_vm, cls_vm = _arrow_cls(vm)
        a_va, cls_va = _arrow_cls(va)

        header_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">📉</div>',
            '    <div class="fx-title">Riesgo País (EMBI)</div>',
            "  </div>",
            '  <div class="fx-card">',
            '    <div class="fx-row">',
            f'      <div class="fx-value">{(f"{last_val:.0f}".replace(".", ",")) if pd.notna(last_val) else "—"}</div>',
            '      <div class="fx-meta">',
            f'        {main_series}<span class="sep">|</span>Spread EMBI (puntos)<span class="sep">|</span>{last_date.strftime("%d/%m/%Y") if pd.notna(last_date) else ""}',
            "      </div>",
            '      <div class="fx-pills">',
            '        <div class="fx-pill red">',
            f'          <span class="fx-arrow {cls_vm}">{a_vm}</span>',
            f'          <span class="{cls_vm}">{safe_pct(vm, 1)}</span>',
            '          <span class="lab">mensual</span>',
            "        </div>",
            '        <div class="fx-pill green">',
            f'          <span class="fx-arrow {cls_va}">{a_va}</span>',
            f'          <span class="{cls_va}">{safe_pct(va, 1)}</span>',
            '          <span class="lab">interanual</span>',
            "        </div>",
            "      </div>",
            "    </div>",
            "  </div>",
            "</div>",
        ]
        header_ph.markdown("\n".join(header_lines), unsafe_allow_html=True)
        header_gap_ph.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # --- selectores ---
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            embi_medida = st.selectbox(
                "",
                ["Nivel", "Variación acumulada"],
                key="embi_medida",
                label_visibility="collapsed",
            )
        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            embi_vars = st.multiselect(
                "",
                options=series_all,
                key="embi_vars",
                label_visibility="collapsed",
            )

        if not embi_vars:
            embi_vars = defaults
            st.session_state["embi_vars"] = embi_vars

        # --- calendario diario + wide ---
        tmin = pd.to_datetime(embi_long["Date"].min())
        tmax = pd.to_datetime(embi_long["Date"].max())
        cal = pd.DataFrame({"Date": pd.date_range(tmin, tmax, freq="D")})

        wide = (
            embi_long.pivot_table(index="Date", columns="Serie", values="Value", aggfunc="last")
            .sort_index()
            .reset_index()
        )
        df = cal.merge(wide, on="Date", how="left").sort_values("Date").reset_index(drop=True)

        for s in embi_vars:
            if s not in df.columns:
                continue
            last_s = embi_long.loc[embi_long["Serie"] == s, "Date"].max()
            df[s] = pd.to_numeric(df[s], errors="coerce").ffill()
            df.loc[df["Date"] > pd.to_datetime(last_s), s] = np.nan

        sel_cols = [s for s in embi_vars if s in df.columns]
        mask_any = df[sel_cols].notna().any(axis=1) if sel_cols else df["Date"].notna()
        s_min = df.loc[mask_any, "Date"].min()
        s_max = df.loc[mask_any, "Date"].max()
        min_d = pd.to_datetime(s_min).date()
        max_d = pd.to_datetime(s_max).date()

        default_start = max(min_d, pd.Timestamp("2023-01-01").date())

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.slider(
            "",
            min_value=min_d,
            max_value=max_d,
            value=(default_start, max_d),
            label_visibility="collapsed",
            key="embi_range",
        )

        df_plot = df[(df["Date"] >= pd.Timestamp(start_d)) & (df["Date"] <= pd.Timestamp(end_d))].copy()

        # --- plot (✅ múltiple series + leyenda horizontal arriba derecha) ---
        fig = go.Figure()

        hover_nivel = "%{fullData.name}<br>%{y:.0f}<extra></extra>"
        hover_acum = "%{fullData.name}<br>%{y:.2f}%<extra></extra>"
        hover = hover_acum if embi_medida == "Variación acumulada" else hover_nivel

        for s in embi_vars:
            if s not in df_plot.columns:
                continue
            y = pd.to_numeric(df_plot[s], errors="coerce")

            if embi_medida == "Variación acumulada":
                base_series = y.dropna()
                base = float(base_series.iloc[0]) if not base_series.empty else np.nan
                y_plot = (y / base - 1) * 100
                name = f"{s} (var. acum.)"
            else:
                y_plot = y
                name = s

            fig.add_trace(
                go.Scatter(
                    x=df_plot["Date"],
                    y=y_plot,
                    name=name,
                    mode="lines",
                    connectgaps=True,
                    hovertemplate=hover,
                )
            )

        fig.update_layout(
            height=520,
            hovermode="x",
            margin=dict(l=10, r=10, t=10, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
            dragmode=False,
        )

        x_max = pd.to_datetime(df_plot["Date"].max())
        x_min = pd.to_datetime(df_plot["Date"].min())
        fig.update_xaxes(range=[x_min, x_max + pd.Timedelta(days=10)])

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        )

        export_cols = ["Date"] + [s for s in embi_vars if s in df_plot.columns]
        export = df_plot[export_cols].copy().rename(columns={"Date": "date"})
        st.download_button(
            "⬇️ Descargar CSV",
            export.to_csv(index=False).encode("utf-8"),
            file_name=f"embi_{pd.Timestamp(end_d).strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            key="dl_embi_csv",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:10px;'>"
            "Fuente: BCRA — Serie_Historica_Spread_del_EMBI.xlsx."
            "</div>",
            unsafe_allow_html=True,
        )

    # ============================================================
    # MERVAL EN DÓLARES (MERVAL ARS / CCL) — ABAJO
    # ============================================================
    st.divider()

    with st.spinner("Cargando MERVAL en dólares..."):
        merval_usd = _load_merval_usd()

    if merval_usd is None or merval_usd.empty:
        st.warning("Sin datos para MERVAL en dólares (Yahoo Finance + CCL services).")
        return

    with st.container():
        # ⚠️ marker distinto (evita colisiones con el de EMBI)
        st.markdown("<div id='merv_panel_marker'></div>", unsafe_allow_html=True)

        components.html(
            """
            <script>
            (function() {
              function applyPanelClass() {
                const doc = window.parent.document;
                const m = doc.getElementById('merv_panel_marker');
                if (!m) return;

                const blocks = [];
                let el = m;
                while (el) {
                  if (el.matches && el.matches('div[data-testid="stVerticalBlock"]')) blocks.push(el);
                  el = el.parentElement;
                }
                if (!blocks.length) return;

                const target = blocks[blocks.length - 1];
                target.classList.add('fx-panel-wrap');
              }

              applyPanelClass();
              let i = 0;
              const t = setInterval(() => {
                applyPanelClass();
                if (++i > 20) clearInterval(t);
              }, 150);
            })();
            </script>
            """,
            height=0,
        )

        last_date = pd.to_datetime(merval_usd["Date"].iloc[-1])
        last_val = float(merval_usd["value"].iloc[-1])

        def _asof(df_, target):
            t = df_[df_["Date"] <= target]
            if t.empty:
                return None
            return float(t["value"].iloc[-1])

        v_m = _asof(merval_usd, last_date - pd.Timedelta(days=30))
        v_y = _asof(merval_usd, last_date - pd.Timedelta(days=365))

        vm = None if v_m is None else (last_val / v_m - 1) * 100
        va = None if v_y is None else (last_val / v_y - 1) * 100

        a_vm, cls_vm = _arrow_cls(vm)
        a_va, cls_va = _arrow_cls(va)

        header = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">📈</div>',
            '    <div class="fx-title">MERVAL</div>',
            "  </div>",
            '  <div class="fx-card">',
            '    <div class="fx-row">',
            f'      <div class="fx-value">{int(round(last_val)):,}'.replace(",", ".") + "</div>",
            '      <div class="fx-meta">',
            f"        MERVAL en dólares (CCL)<span class=\"sep\">|</span>{last_date:%d/%m/%Y}",
            "      </div>",
            '      <div class="fx-pills">',
            f'        <div class="fx-pill red"><span class="fx-arrow {cls_vm}">{a_vm}</span><span class="{cls_vm}">{safe_pct(vm,1)}</span><span class="lab">mensual</span></div>',
            f'        <div class="fx-pill green"><span class="fx-arrow {cls_va}">{a_va}</span><span class="{cls_va}">{safe_pct(va,1)}</span><span class="lab">interanual</span></div>',
            "      </div>",
            "    </div>",
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        if "mervusd_medida" not in st.session_state:
            st.session_state["mervusd_medida"] = "Nivel"

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            m_medida = st.selectbox(
                "",
                ["Nivel", "Variación acumulada"],
                key="mervusd_medida",
                label_visibility="collapsed",
            )
        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.selectbox("", ["—"], disabled=True, label_visibility="collapsed")

        min_d = merval_usd["Date"].min().date()
        max_d = merval_usd["Date"].max().date()
        start_def = max(min_d, pd.Timestamp("2023-01-01").date())

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.slider(
            "",
            min_d,
            max_d,
            (start_def, max_d),
            label_visibility="collapsed",
            key="mervusd_range",
        )

        df_plot = merval_usd[(merval_usd["Date"] >= pd.Timestamp(start_d)) & (merval_usd["Date"] <= pd.Timestamp(end_d))].copy()

        fig = go.Figure()
        y0 = pd.to_numeric(df_plot["value"], errors="coerce")

        if m_medida == "Variación acumulada":
            base_series = y0.dropna()
            base = float(base_series.iloc[0]) if not base_series.empty else np.nan
            y = (y0 / base - 1) * 100
            fig.add_trace(go.Scatter(x=df_plot["Date"], y=y, mode="lines"))
            fig.add_hline(y=0, line_width=1, line_color="rgba(80,80,80,0.7)")
            fig.update_yaxes(ticksuffix="%")
        else:
            fig.add_trace(go.Scatter(x=df_plot["Date"], y=y0, mode="lines"))

        fig.update_layout(height=520, hovermode="x", margin=dict(l=10, r=10, t=10, b=40), dragmode=False)

        x_max = pd.to_datetime(df_plot["Date"].max())
        x_min = pd.to_datetime(df_plot["Date"].min())
        fig.update_xaxes(range=[x_min, x_max + pd.Timedelta(days=10)])

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        export = df_plot.rename(columns={"value": "merval_usd"}).copy()
        export["merval_ars"] = df_plot.get("merval_ars")
        export["ccl"] = df_plot.get("ccl")

        st.download_button(
            "⬇️ Descargar CSV",
            export.to_csv(index=False).encode("utf-8"),
            file_name=f"merval_usd_{end_d}.csv",
            mime="text/csv",
            key="dl_mervusd_csv",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: CEU-UIA en base a Yahoo Finance (^MERV) y CCL proxy YPFD.BA/YPF (services)."
            "</div>",
            unsafe_allow_html=True,
        )



        # ============================================================
        # INTERNACIONAL (Yahoo) — ABAJO DE MERVAL USD
        # - Usa tickers del visor de precios EXCEPTO ARS/USD y Merval
        # - Medida: Nivel / Variación acumulada
        # - Variable: selectbox (sin selección múltiple)
        # - Header fijo: 🌍 Internacional
        # - Meta (abajo del valor) se actualiza según variable elegida
        # ============================================================
        st.divider()

        # --- catálogo: mismo “nombre” que el visor ---
        INTL_CFG = [
            ("BRL/USD", "BRL=X", "fx"),
            ("DXY", "DX-Y.NYB", "index"),
            ("S&P 500", "^GSPC", "eq"),
            ("EWZ", "EWZ", "eq"),
            ("FXI", "FXI", "eq"),
            ("BTC", "BTC-USD", "crypto"),
            ("WTI", "CL=F", "cmd"),
            ("Oro", "GC=F", "cmd"),
            ("Soja", "ZS=F", "cmd"),
            ("Trigo", "ZW=F", "cmd"),
        ]

        INTL_LABELS = [x[0] for x in INTL_CFG]
        INTL_MAP = {lab: {"ticker": tkr, "kind": kind} for lab, tkr, kind in INTL_CFG}

        def _intl_unit(kind: str) -> str:
            return {
                "fx": "Tipo de cambio (USD)",
                "index": "Índice",
                "eq": "Índice / ETF",
                "crypto": "Cripto (USD)",
                "cmd": "Commodity (USD)",
            }.get(kind, "Yahoo Finance")

        def _fmt_intl_value(x: float, kind: str) -> str:
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return "—"
            if kind == "fx":
                return _fmt_es_num(x, 2)
            if kind == "crypto":
                return _fmt_es_num(x, 0)
            return _fmt_es_num(x, 2)

        @st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
        def _load_yahoo_series(ticker: str, start: str = "2000-01-01") -> pd.DataFrame:
            if yf is None:
                return pd.DataFrame(columns=["Date", "value"])

            try:
                dl = yf.download(
                    ticker,
                    start=start,
                    progress=False,
                    auto_adjust=False,
                    interval="1d",
                    group_by="column",
                    threads=True,
                )
            except Exception:
                dl = None

            if dl is None or getattr(dl, "empty", True):
                try:
                    dl = yf.download(
                        ticker,
                        period="max",
                        progress=False,
                        auto_adjust=False,
                        interval="1d",
                        group_by="column",
                        threads=True,
                    )
                except Exception:
                    dl = None

            if dl is None or getattr(dl, "empty", True):
                return pd.DataFrame(columns=["Date", "value"])

            # --- EXTRAER SERIE (Close / Adj Close) ROBUSTO ---
            s = None

            # Caso columnas simples
            if isinstance(dl, pd.DataFrame) and not isinstance(dl.columns, pd.MultiIndex):
                col = "Adj Close" if "Adj Close" in dl.columns else ("Close" if "Close" in dl.columns else None)
                if col is None:
                    return pd.DataFrame(columns=["Date", "value"])
                s = dl[col]

            # Caso columnas MultiIndex
            else:
                # (field, ticker)
                for field in ["Adj Close", "Close"]:
                    if field in dl.columns.get_level_values(0):
                        tmp = dl.xs(field, axis=1, level=0)
                        if isinstance(tmp, pd.DataFrame):
                            if tmp.shape[1] == 1:
                                s = tmp.iloc[:, 0]
                            elif ticker in tmp.columns:
                                s = tmp[ticker]
                        else:
                            s = tmp
                        if s is not None:
                            break

                # (ticker, field)
                if s is None:
                    for field in ["Adj Close", "Close"]:
                        if (
                            ticker in dl.columns.get_level_values(0)
                            and field in dl.columns.get_level_values(1)
                        ):
                            s = dl[(ticker, field)]
                            break

            if s is None:
                return pd.DataFrame(columns=["Date", "value"])

            # Asegurar 1D
            if isinstance(s, pd.DataFrame):
                if s.shape[1] == 1:
                    s = s.iloc[:, 0]
                else:
                    return pd.DataFrame(columns=["Date", "value"])

            s = pd.to_numeric(s, errors="coerce")

            idx = pd.to_datetime(s.index, errors="coerce")
            try:
                idx = idx.tz_localize(None)
            except Exception:
                pass

            out = pd.DataFrame({"Date": idx, "value": s.values})
            out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.normalize()
            out["value"] = pd.to_numeric(out["value"], errors="coerce")
            out = (
                out.dropna(subset=["Date", "value"])
                .drop_duplicates(subset=["Date"])
                .sort_values("Date")
                .reset_index(drop=True)
            )
            return out

        def _asof_val_1col(df_: pd.DataFrame, target: pd.Timestamp):
            t = df_.dropna(subset=["Date", "value"]).sort_values("Date")
            t = t[t["Date"] <= target]
            if t.empty:
                return None
            return float(t["value"].iloc[-1])

        with st.container():
            # marker único
            st.markdown("<div id='intl_panel_marker'></div>", unsafe_allow_html=True)

            # aplicar panel-wrap
            components.html(
                """
                <script>
                (function() {
                function applyPanelClass() {
                    const doc = window.parent.document;
                    const m = doc.getElementById('intl_panel_marker');
                    if (!m) return;

                    const blocks = [];
                    let el = m;
                    while (el) {
                    if (el.matches && el.matches('div[data-testid="stVerticalBlock"]')) blocks.push(el);
                    el = el.parentElement;
                    }
                    if (!blocks.length) return;

                    const target = blocks[blocks.length - 1];
                    target.classList.add('fx-panel-wrap');
                }

                applyPanelClass();
                let i = 0;
                const t = setInterval(() => {
                    applyPanelClass();
                    if (++i > 20) clearInterval(t);
                }, 150);
                })();
                </script>
                """,
                height=0,
            )

            # ---- defaults (estado) ----
            if "intl_medida" not in st.session_state:
                st.session_state["intl_medida"] = "Nivel"
            if "intl_var" not in st.session_state or st.session_state["intl_var"] not in INTL_LABELS:
                st.session_state["intl_var"] = INTL_LABELS[0]

            # ✅ Placeholders ARRIBA (para que el header quede visualmente arriba)
            header_ph = st.empty()
            gap_ph = st.empty()

            # ---- selectores (pero el header ya “vive” arriba) ----
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
                intl_medida = st.selectbox(
                    "",
                    ["Nivel", "Variación acumulada"],
                    key="intl_medida",
                    label_visibility="collapsed",
                )
            with c2:
                st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
                intl_var = st.selectbox(
                    "",
                    INTL_LABELS,
                    key="intl_var",
                    label_visibility="collapsed",
                )

            # ---- cargar serie según variable elegida ----
            tkr = INTL_MAP[intl_var]["ticker"]
            kind = INTL_MAP[intl_var]["kind"]

            with st.spinner("Cargando Internacional (Yahoo Finance)..."):
                s_intl = _load_yahoo_series(tkr, start="1990-01-01")

            if s_intl is None or s_intl.empty:
                st.warning("Sin datos para la serie seleccionada (Yahoo Finance).")
                st.stop()

            last_date = pd.to_datetime(s_intl["Date"].iloc[-1])
            last_val = float(s_intl["value"].iloc[-1])

            v_m = _asof_val_1col(s_intl, last_date - pd.Timedelta(days=30))
            v_y = _asof_val_1col(s_intl, last_date - pd.Timedelta(days=365))

            vm = None if v_m is None else (last_val / v_m - 1) * 100
            va = None if v_y is None else (last_val / v_y - 1) * 100

            a_vm, cls_vm = _arrow_cls(vm)
            a_va, cls_va = _arrow_cls(va)

            # ✅ Ahora sí, rellenamos el header (pero queda arriba)
            header = [
                '<div class="fx-wrap">',
                '  <div class="fx-title-row">',
                '    <div class="fx-icon-badge">🌍</div>',
                '    <div class="fx-title">Internacional</div>',
                "  </div>",
                '  <div class="fx-card">',
                '    <div class="fx-row">',
                f'      <div class="fx-value">{_fmt_intl_value(last_val, kind)}</div>',
                '      <div class="fx-meta">',
                f'        {intl_var}<span class="sep">|</span>{_intl_unit(kind)}<span class="sep">|</span>{last_date.strftime("%d/%m/%Y")}',
                "      </div>",
                '      <div class="fx-pills">',
                '        <div class="fx-pill red">',
                f'          <span class="fx-arrow {cls_vm}">{a_vm}</span>',
                f'          <span class="{cls_vm}">{safe_pct(vm, 1)}</span>',
                '          <span class="lab">mensual</span>',
                "        </div>",
                '        <div class="fx-pill green">',
                f'          <span class="fx-arrow {cls_va}">{a_va}</span>',
                f'          <span class="{cls_va}">{safe_pct(va, 1)}</span>',
                '          <span class="lab">interanual</span>',
                "        </div>",
                "      </div>",
                "    </div>",
                "  </div>",
                "</div>",
            ]
            header_ph.markdown("\n".join(header), unsafe_allow_html=True)
            gap_ph.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            # ---- Rango ----
            min_d = s_intl["Date"].min().date()
            max_d = s_intl["Date"].max().date()
            start_def = max(min_d, pd.Timestamp("2023-01-01").date())

            st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
            start_d, end_d = st.slider(
                "",
                min_value=min_d,
                max_value=max_d,
                value=(start_def, max_d),
                label_visibility="collapsed",
                key="intl_range",
            )

            df_plot = s_intl[(s_intl["Date"] >= pd.Timestamp(start_d)) & (s_intl["Date"] <= pd.Timestamp(end_d))].copy()

            # ---- Plot ----
            fig = go.Figure()
            y0 = pd.to_numeric(df_plot["value"], errors="coerce")

            if intl_medida == "Variación acumulada":
                base_series = y0.dropna()
                base = float(base_series.iloc[0]) if not base_series.empty else np.nan
                y = (y0 / base - 1) * 100
                fig.add_trace(
                    go.Scatter(
                        x=df_plot["Date"],
                        y=y,
                        mode="lines",
                        name=f"{intl_var} (var. acum.)",
                        hovertemplate="%{y:.2f}%<extra></extra>",
                    )
                )
                fig.add_hline(y=0, line_width=1, line_color="rgba(80,80,80,0.7)")
                fig.update_yaxes(ticksuffix="%")
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df_plot["Date"],
                        y=y0,
                        mode="lines",
                        name=intl_var,
                        hovertemplate="%{y:.2f}<extra></extra>",
                    )
                )

            fig.update_layout(
                height=520,
                hovermode="x",
                margin=dict(l=10, r=10, t=10, b=40),
                dragmode=False,
                showlegend=False,
            )

            x_max = pd.to_datetime(df_plot["Date"].max())
            x_min = pd.to_datetime(df_plot["Date"].min())
            fig.update_xaxes(range=[x_min, x_max + pd.Timedelta(days=10)])

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # ---- Export ----
            export = df_plot.copy()
            st.download_button(
                "⬇️ Descargar CSV",
                export.to_csv(index=False).encode("utf-8"),
                file_name=f"internacional_{tkr}_{pd.Timestamp(end_d).strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                key="dl_intl_csv",
            )

            st.markdown(
                "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
                "Fuente: CEU-UIA en base a Yahoo Finance."
                "</div>",
                unsafe_allow_html=True,
            )
