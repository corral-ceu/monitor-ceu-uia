# pages/ipi.py
import random
import textwrap
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel


# ============================================================
# Frases (loading) — mismas del page EMAE
# ============================================================
INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Link header (pedido)
INFORME_CEU_URL = "https://uia.org.ar/centro-de-estudios/documentos/actualidad-industrial/?q=Industrial"

# Rebase (pedido)
BASE_DT = pd.Timestamp("2023-04-01")  # abr-23 (MS)


# ============================================================
# Helpers (formato EMAE)
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


def _month_label_es(dt: pd.Timestamp) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = pd.to_datetime(dt)
    return f"{MESES_ES[dt.month-1]}-{dt.year}"


def _compute_yoy_df(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["YoY"] = (t["Value"] / t["Value"].shift(12) - 1.0) * 100.0
    return t


def _compute_mom_df(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Date", "Value"]).sort_values("Date").copy()
    t["MoM"] = (t["Value"] / t["Value"].shift(1) - 1.0) * 100.0
    return t


def _clean_series(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Value"])
    t = df.copy()
    t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
    t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
    return t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)


def _rebase_100(df: pd.DataFrame, base_dt: pd.Timestamp) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    t = df.copy()
    t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
    t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
    t = t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)
    base_val = t.loc[t["Date"] == base_dt, "Value"]
    if base_val.empty:
        return t
    b = float(base_val.iloc[0])
    if b == 0 or np.isnan(b):
        return t
    t["Value"] = (t["Value"] / b) * 100.0
    return t


# ============================================================
# Helpers para detectar divisiones en Excel
# ============================================================
def _is_header_div(code_str: str) -> bool:
    s = str(code_str).strip()
    if not s or s.lower() == "nan":
        return False
    if s.isdigit() and len(s) == 2:
        return True
    if "-" in s:
        return True
    return False


def _build_div_blocks(codes: List[str]) -> Tuple[List[int], Dict[str, int]]:
    header_idxs = []
    code_to_idx = {}
    for i, c in enumerate(codes):
        if i < 3:
            continue
        if _is_header_div(c):
            header_idxs.append(i)
            code_to_idx[str(c).strip()] = i
    return header_idxs, code_to_idx

def _subcol_range_for_header(header_idx: int, header_idxs: list[int], total_cols: int) -> range:
    if header_idx not in header_idxs:
        return range(0, 0)
    pos = header_idxs.index(header_idx)
    next_h = header_idxs[pos + 1] if pos + 1 < len(header_idxs) else total_cols
    return range(header_idx + 1, next_h)


def _dot_class(x: float) -> str:
    if x is None or pd.isna(x) or abs(float(x)) < 1e-12:
        return "ipi-neutral"
    return "ipi-up" if float(x) > 0 else "ipi-down"


# ============================================================
# Abreviaciones de nombres largos para las cards
# ============================================================
CARD_NAME_ABBREV = {
    "Refinación del petróleo, coque y combustible nuclear": "Refinación del petróleo y combustible",
    "Vehículos automotores, carrocerías, remolques y autopartes": "Vehículos automotores y autopartes",
    "Otros equipos, aparatos e instrumentos": "Otros equipos y aparatos",
    "Muebles y colchones, y otras industrias manufactureras": "Muebles y otras industrias manuf.",
    "Madera, papel, edición e impresión": "Madera, papel e impresión",
    "Sustancias y productos químicos": "Sustancias y prod. químicos",
    "Productos minerales no metálicos": "Prod. minerales no metálicos",
    "Prendas de vestir, cuero y calzado": "Prendas de vestir y calzado",
}

def _abbrev_name(name: str) -> str:
    return CARD_NAME_ABBREV.get(name, name)


# ---- helpers para las cards nuevas ----
def _chip_class(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "chip-neu"
    return "chip-pos" if x > 0 else "chip-neg"

def _val_class(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "val-neu"
    return "val-pos" if x > 0 else "val-neg"

def _arrow_dir(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "→"
    return "↑" if x > 0 else "↓"

def _arrow_color_class(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "arrow-neu"
    return "arrow-up" if x > 0 else "arrow-dn"

def _bar_class(v_m: float, v_i: float) -> str:
    m_pos = v_m is not None and not (isinstance(v_m, float) and np.isnan(v_m)) and v_m >= 0
    i_pos = v_i is not None and not (isinstance(v_i, float) and np.isnan(v_i)) and v_i >= 0
    m_neg = v_m is not None and not (isinstance(v_m, float) and np.isnan(v_m)) and v_m < 0
    i_neg = v_i is not None and not (isinstance(v_i, float) and np.isnan(v_i)) and v_i < 0
    if m_pos and i_pos:
        return "bar-pos"
    if m_neg and i_neg:
        return "bar-neg"
    return "bar-mix"


# ============================================================
# CSS
# ============================================================
def _inject_css_fx():
    st.markdown(
        textwrap.dedent(
            """
        <style>
          /* ===== HEADER ===== */
          .fx-wrap{
            background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
            border: 1px solid #dfeaf6;
            border-radius: 22px;
            padding: 12px;
            box-shadow:
              0 10px 24px rgba(15, 55, 100, 0.16),
              inset 0 0 0 1px rgba(255,255,255,0.55);
          }

          .fx-title-row{
            display:flex;
            align-items:center;
            gap: 12px;
            margin-bottom: 8px;
            padding-left: 4px;
          }

          .fx-icon-badge{
            width: 64px;
            height: 52px;
            border-radius: 14px;
            background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
            border: 1px solid rgba(15,23,42,0.10);
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow: 0 8px 14px rgba(15,55,100,0.12);
            font-size: 32px;
            flex: 0 0 auto;
          }

          .fx-title{
            font-size: 23px;
            font-weight: 900;
            letter-spacing: -0.01em;
            color: #14324f;
            margin: 0;
            line-height: 1.0;
          }

          .fx-card{
            background: rgba(255,255,255,0.94);
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 18px;
            padding: 14px 14px 12px 14px;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
          }

          .fx-row{
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            column-gap: 14px;
          }

          .fx-value{
            font-size: 46px;
            font-weight: 950;
            letter-spacing: -0.02em;
            color: #14324f;
            line-height: 0.95;
          }

          .fx-meta{
            font-size: 13px;
            color: #2b4660;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .fx-meta .sep{ opacity: 0.40; padding: 0 6px; }

          .fx-pills{
            display:flex;
            gap: 10px;
            justify-content: flex-end;
            align-items: center;
            white-space: nowrap;
          }

          .fx-pill{
            display:inline-flex;
            align-items:center;
            gap: 8px;
            padding: 7px 10px;
            border-radius: 12px;
            border: 1px solid rgba(15,23,42,0.10);
            font-size: 13px;
            font-weight: 700;
            box-shadow: 0 6px 10px rgba(15,55,100,0.08);
          }

          .fx-pill .lab{ color:#2b4660; font-weight: 900; }

          .fx-pill.red{
            background: linear-gradient(180deg, rgba(220,38,38,0.08) 0%, rgba(220,38,38,0.05) 100%);
          }
          .fx-pill.green{
            background: linear-gradient(180deg, rgba(22,163,74,0.10) 0%, rgba(22,163,74,0.06) 100%);
          }

          .fx-up{ color:#168a3a; font-weight: 900; }
          .fx-down{ color:#cc2e2e; font-weight: 900; }

          .fx-arrow{
            width: 14px;
            text-align:center;
            font-weight: 900;
          }

          .fx-panel-title{
            font-size: 12px;
            font-weight: 900;
            color: rgba(20,50,79,0.78);
            margin: 0 0 6px 2px;
            letter-spacing: 0.01em;
          }

          .fx-panel-gap{ height: 16px; }

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

          .fx-panel-wrap div[role="combobox"]{
            border-radius: 16px !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.08) !important;
          }

          .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"]{
            background: #0b2a55 !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10) !important;
          }
          .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] *{
            color: #8fc2ff !important;
            fill: #8fc2ff !important;
            font-weight: 800 !important;
          }

          .fx-panel-wrap span[data-baseweb="tag"]{
            background: #0b2a55 !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
          }
          .fx-panel-wrap span[data-baseweb="tag"] *{
            color: #ffffff !important;
            fill: #ffffff !important;
            font-weight: 800 !important;
          }

          .fx-report a{
            display:inline-block;
            padding:6px 10px;
            border-radius:999px;
            border:1px solid #e5e7eb;
            background:#ffffff;
            color:#0f172a;
            font-size:12px;
            font-weight:700;
            text-decoration:none;
            box-shadow:0 2px 4px rgba(0,0,0,0.06);
            white-space: nowrap;
          }

          @media (max-width: 900px){
            .fx-row{ grid-template-columns: 1fr; row-gap: 10px; }
            .fx-meta{ white-space: normal; }
            .fx-pills{ justify-content: flex-start; }
          }

          /* =========================
             IPI – Cards nuevas
             ========================= */

          .ipi-card {
            background: #ffffff;
            border: 1px solid #dde6f0;
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(15,55,100,.07);
          }

          /* barra superior — azul institucional único */
          .ipi-card-bar {
            height: 5px;
            width: 100%;
            background: #0ea5e9;
          }

          /* clase legacy mantenida pero sin efecto visual */
          .bar-pos, .bar-neg, .bar-mix { background: #0ea5e9; }

          .ipi-card-body {
            padding: 16px 16px 14px 16px;
          }

          .ipi-title {
            font-family:"Source Sans", sans-serif;
            font-weight: 700;
            font-size: 22px;
            color: #1e3a5f;
            line-height: 1.35;
            margin-bottom: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          /* chips MoM / YoY */
          .ipi-metrics {
            display: flex;
            gap: 10px;
          }

          .ipi-chip {
            flex: 1;
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
          }
          .chip-pos { background: #f0fdf4; border: 1px solid #bbf7d0; }
          .chip-neg { background: #fff1f2; border: 1px solid #fecdd3; }
          .chip-neu { background: #f8fafc; border: 1px solid #e2e8f0; }

          .ipi-chip-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }

          .ipi-chip-label {
            font-family:"Source Sans", sans-serif;
            font-size: 16px;
            font-weight: 700;
            color: #7a90a8;
          }

          .ipi-chip-arrow {
            font-size: 15px;
            font-weight: 900;
            line-height: 1;
          }
          .arrow-up  { color: #16a34a; }
          .arrow-dn  { color: #e11d48; }
          .arrow-neu { color: #64748b; }

          .ipi-chip-val {
            font-family:"Source Sans", sans-serif;
            font-size: 20px;
            font-weight: 700;
            line-height: 1;
          }
          .val-pos { color: #16a34a !important; }
          .val-neg { color: #e11d48 !important; }
          .val-neu { color: #64748b !important; }

          /* ── Modal KPIs: mismo chip format que las cards ── */
          .ipi-modal-chips {
            display: flex;
            gap: 12px;
            margin-bottom: 14px;
          }
          .ipi-modal-chip {
            flex: 1;
            border-radius: 10px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 7px;
          }
          .ipi-modal-chip-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          .ipi-modal-chip-label {
            font-family:"Source Sans", sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .5px;
            color: #7a90a8;
          }
          .ipi-modal-chip-val {
            font-family:"Source Sans", sans-serif;
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
          }

          /* ── Botón "Abrir detalle" integrado como pie de card ── */
          .ipi-card + div button[kind="secondary"] {
            background: #ffffff !important;
            border: 1px solid #dde6f0 !important;
            border-top: 1px solid #e8eff7 !important;
            border-radius: 0 0 14px 14px !important;
            color: #2563eb !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            letter-spacing: .2px !important;
            padding: 9px 0 !important;
            box-shadow: none !important;
            margin-top: -8px !important;
            transition: background .15s, color .15s !important;
          }
          .ipi-card + div button[kind="secondary"]:hover {
            background: #eff4ff !important;
            color: #1d4ed8 !important;
          }

          /* legacy — ya no se usan en cards pero sí en modal antiguo si quedara */
          .ipi-mini-wrap{ display:flex; gap:12px; margin-bottom:6px; }
          .ipi-mini{
            flex:1;
            border:1px solid #e6edf5;
            border-radius:12px;
            padding:10px 12px;
            background:#ffffff;
            text-align:center;
          }
          .ipi-mini-lbl{ font-size:16px; font-weight:800; color:#526484; margin-bottom:6px; }
          .ipi-mini-row{ display:flex; justify-content:center; }
          .ipi-dot{
            width:52px; height:52px; border-radius:999px;
            display:flex; align-items:center; justify-content:center;
            font-weight:900; font-size:18px;
            border:1px solid transparent;
          }
          .ipi-up{ background:rgba(22,163,74,.12); color:rgb(22,163,74); border-color:rgba(22,163,74,.25); }
          .ipi-down{ background:rgba(220,38,38,.12); color:rgb(220,38,38); border-color:rgba(220,38,38,.25); }
          .ipi-neutral{ background:rgba(100,116,139,.12); color:rgb(100,116,139); border-color:rgba(100,116,139,.22); }

        </style>
        """
        ),
        unsafe_allow_html=True,
    )


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

          let tries = 0;
          const t = setInterval(() => {{
            applyPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
          }}, 150);

          const obs = new MutationObserver(() => applyPanelClass());
          obs.observe(window.parent.document.body, {{ childList: true, subtree: true }});
          setTimeout(() => obs.disconnect(), 3000);
        }})();
        </script>
        """,
        height=0,
    )


# ============================================================
# Main
# ============================================================
def render_ipi(go_to):
    _inject_css_fx()

    if st.button("← Volver"):
        go_to("home")

    fact = st.empty()
    fact.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    with st.spinner("Cargando indicadores..."):
        df_c2, df_c5 = cargar_ipi_excel()

    fact.empty()

    if df_c2 is None or df_c5 is None:
        st.error("No pude cargar el Excel del IPI Manufacturero (INDEC).")
        return

    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]
    codes_c5 = [str(x).strip() for x in df_c5.iloc[2].fillna("").tolist()]

    header_idxs_c2, code_to_header_idx_c2 = _build_div_blocks(codes_c2)

    ng_se_raw = procesar_serie_excel(df_c5, 3)
    ng_orig_raw = procesar_serie_excel(df_c2, 3)

    df_ng_se = _rebase_100(_clean_series(ng_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
    df_ng_o  = _rebase_100(_clean_series(ng_orig_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)

    if df_ng_se.empty or df_ng_o.empty:
        st.error("No pude extraer la serie de IPI (nivel general) desde el Excel.")
        return

    yoy_full = _compute_yoy_df(df_ng_o)
    mom_full = _compute_mom_df(df_ng_se)

    yoy_val = yoy_full["YoY"].dropna().iloc[-1] if yoy_full["YoY"].notna().any() else None
    yoy_date = yoy_full.dropna(subset=["YoY"]).iloc[-1]["Date"] if yoy_full["YoY"].notna().any() else None

    mom_val = mom_full["MoM"].dropna().iloc[-1] if mom_full["MoM"].notna().any() else None
    mom_date = mom_full.dropna(subset=["MoM"]).iloc[-1]["Date"] if mom_full["MoM"].notna().any() else None

    divs_idxs = [
        i for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    SERIES: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]] = {
        "IPI - Nivel general": (df_ng_o, df_ng_se),
    }

    for idx in divs_idxs:
        div_name = names_c5[idx]
        div_code = str(codes_c5[idx]).strip()

        s_se_raw = procesar_serie_excel(df_c5, idx)
        s_se = _rebase_100(_clean_series(s_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)

        header_idx = code_to_header_idx_c2.get(div_code, None)
        if header_idx is not None:
            s_o_raw = procesar_serie_excel(df_c2, int(header_idx))
            s_o = _rebase_100(_clean_series(s_o_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
        else:
            s_o = pd.DataFrame(columns=["Date", "Value"])

        SERIES[div_name] = (s_o, s_se)

    # =========================================================
    # BLOQUE 1 — IPI
    # =========================================================
    with st.container():
        _apply_panel_wrap("ipi_panel_marker")

        a_yoy, cls_yoy = _arrow_cls(yoy_val)
        a_mom, cls_mom = _arrow_cls(mom_val)

        header_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row" style="justify-content:space-between;">',
            '    <div style="display:flex; align-items:center; gap:12px;">',
            '      <div class="fx-icon-badge">🏭</div>',
            '      <div class="fx-title">Índice de Producción Industrial (IPI)</div>',
            "    </div>",
            f'    <div class="fx-report"><a href="{INFORME_CEU_URL}" target="_blank">📄 Ver último Informe Industrial</a></div>',
            "  </div>",
            '  <div class="fx-card">',
            '    <div class="fx-row">',
            f'      <div class="fx-value">{_fmt_pct_es(yoy_val, 1)}%</div>' if yoy_val is not None else '      <div class="fx-value">—</div>',
            '      <div class="fx-meta">',
            f'        IPI (original)<span class="sep">|</span>YoY<span class="sep">|</span>{_month_label_es(yoy_date)}',
            "      </div>",
            '      <div class="fx-pills">',
            '        <div class="fx-pill red">',
            f'          <span class="fx-arrow {cls_yoy}">{a_yoy}</span>',
            f'          <span class="{cls_yoy}">{_fmt_pct_es(yoy_val, 1) if yoy_val is not None else "—"}%</span>',
            '          <span class="lab">anual</span>',
            "        </div>",
            '        <div class="fx-pill green">',
            f'          <span class="fx-arrow {cls_mom}">{a_mom}</span>',
            f'          <span class="{cls_mom}">{_fmt_pct_es(mom_val, 1) if mom_val is not None else "—"}%</span>',
            '          <span class="lab">mensual</span>',
            "        </div>",
            "      </div>",
            "    </div>",
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header_lines), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        if "ipi_medida" not in st.session_state:
            st.session_state["ipi_medida"] = "Nivel desestacionalizado"
        if "ipi_vars" not in st.session_state:
            st.session_state["ipi_vars"] = ["IPI - Nivel general"]

        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                [
                    "Nivel desestacionalizado",
                    "Nivel original",
                    "Variación acumulada sin estacionalidad",
                ],
                key="ipi_medida",
                label_visibility="collapsed",
            )

        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.multiselect(
                "",
                options=list(SERIES.keys()),
                key="ipi_vars",
                label_visibility="collapsed",
            )

        vars_sel = st.session_state.get("ipi_vars", [])
        if not vars_sel:
            st.warning("Seleccioná una variable.")
            return

        medida = st.session_state.get("ipi_medida", "Nivel desestacionalizado")

        date_mins = []
        date_maxs = []

        for vname in vars_sel:
            df_o, df_s = SERIES.get(vname, (pd.DataFrame(), pd.DataFrame()))
            if medida == "Nivel original":
                base = df_o
            else:
                base = df_s

            if base is not None and not base.empty and "Date" in base.columns:
                date_mins.append(pd.to_datetime(base["Date"].min()))
                date_maxs.append(pd.to_datetime(base["Date"].max()))

        if not date_mins or not date_maxs:
            date_mins = [pd.to_datetime(df_ng_se["Date"].min())]
            date_maxs = [pd.to_datetime(df_ng_se["Date"].max())]

        min_real = min(date_mins)
        max_real = max(date_maxs)

        months = pd.date_range(
            min_real.to_period("M").to_timestamp(),
            max_real.to_period("M").to_timestamp(),
            freq="MS",
        )
        months_d = [m.date() for m in months]

        try:
            default_start = (pd.Timestamp(max_real) - pd.DateOffset(years=4)).date()
        except Exception:
            default_start = months_d[0]

        start_default = max(default_start, months_d[0])
        end_default = months_d[-1]

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.select_slider(
            "",
            options=months_d,
            value=(start_default, end_default),
            format_func=lambda d: f"{MESES_ES[pd.Timestamp(d).month-1]}-{pd.Timestamp(d).year}",
            label_visibility="collapsed",
            key="ipi_range",
        )

        start_ts = pd.Timestamp(start_d).to_period("M").to_timestamp()
        end_ts = pd.Timestamp(end_d).to_period("M").to_timestamp()

        fig = go.Figure()

        if medida in ("Nivel desestacionalizado", "Nivel original"):
            for vname in vars_sel:
                df_o, df_s = SERIES.get(
                    vname,
                    (pd.DataFrame(columns=["Date", "Value"]), pd.DataFrame(columns=["Date", "Value"])),
                )
                base = df_s if medida == "Nivel desestacionalizado" else df_o
                base = base[(base["Date"] >= start_ts) & (base["Date"] <= end_ts)].copy()

                if not base.empty:
                    suf = "(s.e.)" if medida == "Nivel desestacionalizado" else "(original)"
                    fig.add_trace(
                        go.Scatter(
                            x=base["Date"],
                            y=base["Value"],
                            mode="lines+markers",
                            name=f"{vname} {suf}",
                        )
                    )
            fig.update_yaxes(title="Índice (base 100=abr-23)")

        else:
            for vname in vars_sel:
                _, df_s = SERIES.get(vname, (pd.DataFrame(columns=["Date", "Value"]), pd.DataFrame(columns=["Date", "Value"])))
                t = df_s[(df_s["Date"] >= start_ts) & (df_s["Date"] <= end_ts)].copy()
                t = t.dropna(subset=["Date", "Value"]).sort_values("Date")
                if t.empty:
                    continue
                base_val = float(t["Value"].iloc[0])
                if base_val == 0 or np.isnan(base_val):
                    continue
                t["Acc"] = (t["Value"] / base_val - 1.0) * 100.0

                fig.add_trace(
                    go.Scatter(
                        x=t["Date"],
                        y=t["Acc"],
                        mode="lines+markers",
                        name=f"{vname} (acum s.e.)",
                        hovertemplate="%{y:.1f}%<extra></extra>",
                    )
                )
            fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#666666")
            fig.update_yaxes(ticksuffix="%", title="Variación acumulada (%)")

        fig.update_layout(
            height=520,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode=False,
        )

        x_max = pd.Timestamp(end_ts) + pd.Timedelta(days=10)
        fig.update_xaxes(range=[pd.Timestamp(start_ts), x_max])

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            key="chart_ipi_panel1",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC — IPI Manufacturero (Excel .xls)"
            "</div>",
            unsafe_allow_html=True,
        )

    # =========================================================
    # BLOQUE 2 — IPI por ramas
    # =========================================================
    st.divider()

    with st.container():
        _apply_panel_wrap("ipi_sect_panel_marker")

        header2_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">🏭</div>',
            '    <div class="fx-title">Índice de Producción Industrial por Ramas</div>',
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header2_lines), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        rows_o = []
        rows_s = []

        for vname, (df_o, df_s) in SERIES.items():
            if df_o is not None and not df_o.empty:
                tmp = df_o.copy()
                tmp["Sector"] = vname
                rows_o.append(tmp)
            if df_s is not None and not df_s.empty:
                tmp = df_s.copy()
                tmp["Sector"] = vname
                rows_s.append(tmp)

        df_o_long = pd.concat(rows_o, ignore_index=True) if rows_o else pd.DataFrame(columns=["Date", "Value", "Sector"])
        df_s_long = pd.concat(rows_s, ignore_index=True) if rows_s else pd.DataFrame(columns=["Date", "Value", "Sector"])

        if df_o_long.empty and df_s_long.empty:
            st.error("No hay datos suficientes para construir la apertura por ramas.")
            return

        max_dt_o = pd.to_datetime(df_o_long["Date"].max()) if not df_o_long.empty else None
        max_dt_s = pd.to_datetime(df_s_long["Date"].max()) if not df_s_long.empty else None
        max_dt = max([d for d in [max_dt_o, max_dt_s] if d is not None])

        last_month_num = int(max_dt.month)
        last_month_label = MESES_ES[last_month_num - 1]

        years_all = sorted(pd.to_datetime(df_o_long["Date"]).dt.year.unique().tolist(), reverse=True) if not df_o_long.empty else []

        def _month_opt_label(dt: pd.Timestamp) -> str:
            return _month_label_es(pd.to_datetime(dt))

        acc_label = f"Variación acumulada anual (ene-{last_month_label})"

        MODE_LABELS = {
            "acum": acc_label,
            "acum_cerrado": "Variación acumulada año cerrado",
            "anual": "Variación anual",
            "se": "Variación serie sin estacionalidad",
        }
        MODE_KEYS = list(MODE_LABELS.keys())

        if "ipi_sec_mode_key" not in st.session_state:
            st.session_state["ipi_sec_mode_key"] = "acum"
        if "ipi_sec_rama_sel" not in st.session_state:
            st.session_state["ipi_sec_rama_sel"] = "Total"

        # Lista de ramas para el selector (Total + todas las divisiones)
        ramas_opciones = ["Total"] + [names_c5[i] for i in divs_idxs]

        r1c1, r1c2 = st.columns(2, gap="large")

        with r1c1:
            st.markdown("<div class='fx-panel-title'>Tipo de comparación</div>", unsafe_allow_html=True)
            rama_sel = st.session_state.get("ipi_sec_rama_sel", "Total")
            # Si rama != Total, bloquear opción s.e.
            available_modes = MODE_KEYS if rama_sel == "Total" else [k for k in MODE_KEYS if k != "se"]
            # Si el modo guardado ya no está disponible, resetear
            if st.session_state.get("ipi_sec_mode_key") not in available_modes:
                st.session_state["ipi_sec_mode_key"] = available_modes[0]
            mode_key = st.selectbox(
                "",
                available_modes,
                format_func=lambda k: MODE_LABELS.get(k, k),
                key="ipi_sec_mode_key",
                label_visibility="collapsed",
            )

        with r1c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná una rama</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                ramas_opciones,
                key="ipi_sec_rama_sel",
                label_visibility="collapsed",
            )
            rama_sel = st.session_state.get("ipi_sec_rama_sel", "Total")

        # ── Armar df_o_long y df_s_long filtrados según rama_sel ──
        if rama_sel == "Total":
            df_o_plot = df_o_long.copy()
            df_s_plot = df_s_long.copy()
        else:
            # Buscar el header_idx de la rama seleccionada en Cuadro 2
            rama_code = None
            for i in divs_idxs:
                if names_c5[i] == rama_sel:
                    rama_code = str(codes_c5[i]).strip()
                    break

            rama_header_idx = code_to_header_idx_c2.get(rama_code, None) if rama_code else None

            # Construir df_o_plot con: la rama total + sus subramas (Cuadro 2)
            rows_rama = []
            if rama_header_idx is not None:
                # La rama total
                s_rama_o_raw = procesar_serie_excel(df_c2, int(rama_header_idx))
                s_rama_o = _rebase_100(_clean_series(s_rama_o_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                if s_rama_o is not None and not s_rama_o.empty:
                    s_rama_o["Sector"] = rama_sel
                    rows_rama.append(s_rama_o)

                # Sus subramas
                subcols = list(_subcol_range_for_header(rama_header_idx, header_idxs_c2, len(codes_c2)))
                for k in subcols:
                    nm = str(names_c2[k]).strip()
                    if nm in ("", "Período", "IPI Manufacturero"):
                        continue
                    s_sub_raw = procesar_serie_excel(df_c2, k)
                    s_sub = _rebase_100(_clean_series(s_sub_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                    if s_sub is None or s_sub.empty:
                        continue
                    s_sub["Sector"] = nm
                    rows_rama.append(s_sub)

            df_o_plot = pd.concat(rows_rama, ignore_index=True) if rows_rama else pd.DataFrame(columns=["Date", "Value", "Sector"])
            df_s_plot = pd.DataFrame(columns=["Date", "Value", "Sector"])  # subramas no tienen s.e.

        colA, colB = st.columns(2, gap="large")

        if mode_key == "acum":
            if not years_all:
                st.warning("No hay años disponibles en la serie original.")
                return

            if "ipi_sec_year_a" not in st.session_state:
                st.session_state["ipi_sec_year_a"] = years_all[0]
            if "ipi_sec_year_b" not in st.session_state:
                st.session_state["ipi_sec_year_b"] = years_all[1] if len(years_all) > 1 else years_all[0]

            with colA:
                st.markdown("<div class='fx-panel-title'>Período Final</div>", unsafe_allow_html=True)
                st.selectbox("", years_all, key="ipi_sec_year_a", label_visibility="collapsed")

            with colB:
                st.markdown("<div class='fx-panel-title'>Período Inicial</div>", unsafe_allow_html=True)
                st.selectbox("", years_all, key="ipi_sec_year_b", label_visibility="collapsed")

            year_a = int(st.session_state.get("ipi_sec_year_a"))
            year_b = int(st.session_state.get("ipi_sec_year_b"))

            def _accum_avg_by_sector_orig(year: int) -> pd.Series:
                t = df_o_plot[df_o_plot["Date"].dt.year == year].copy()
                t = t[t["Date"].dt.month <= last_month_num]
                return t.groupby("Sector")["Value"].mean()

            A = _accum_avg_by_sector_orig(year_a)
            B = _accum_avg_by_sector_orig(year_b)

            rama_label = f" — {rama_sel}" if rama_sel != "Total" else ""
            subtitle = f"Comparación acumulada ene–{last_month_label} (promedio) · A={year_a} / B={year_b}{rama_label}"

        elif mode_key == "acum_cerrado":
            years_closed = []
            if not df_o_plot.empty:
                month_counts = (
                    df_o_plot.assign(Y=df_o_plot["Date"].dt.year, M=df_o_plot["Date"].dt.month)
                    .groupby(["Sector", "Y"])["M"]
                    .nunique()
                    .reset_index()
                )
                if not month_counts.empty:
                    # Año cerrado = 12 meses completos para todas las series visibles
                    min_months_by_year = month_counts.groupby("Y")["M"].min()
                    years_closed = sorted([int(y) for y, m in min_months_by_year.items() if int(m) == 12], reverse=True)

            if not years_closed:
                st.warning("No hay años cerrados disponibles para comparar (12 meses completos).")
                return

            if "ipi_sec_year_closed_a" not in st.session_state:
                st.session_state["ipi_sec_year_closed_a"] = years_closed[0]
            if "ipi_sec_year_closed_b" not in st.session_state:
                st.session_state["ipi_sec_year_closed_b"] = years_closed[1] if len(years_closed) > 1 else years_closed[0]

            with colA:
                st.markdown("<div class='fx-panel-title'>Período Final</div>", unsafe_allow_html=True)
                st.selectbox("", years_closed, key="ipi_sec_year_closed_a", label_visibility="collapsed")

            with colB:
                st.markdown("<div class='fx-panel-title'>Período Inicial</div>", unsafe_allow_html=True)
                st.selectbox("", years_closed, key="ipi_sec_year_closed_b", label_visibility="collapsed")

            year_a = int(st.session_state.get("ipi_sec_year_closed_a"))
            year_b = int(st.session_state.get("ipi_sec_year_closed_b"))

            def _full_year_avg_by_sector_orig(year: int) -> pd.Series:
                t = df_o_plot[df_o_plot["Date"].dt.year == year].copy()
                return t.groupby("Sector")["Value"].mean()

            A = _full_year_avg_by_sector_orig(year_a)
            B = _full_year_avg_by_sector_orig(year_b)

            rama_label = f" — {rama_sel}" if rama_sel != "Total" else ""
            subtitle = f"Comparación acumulada año cerrado (promedio anual) · A={year_a} / B={year_b}{rama_label}"

        elif mode_key == "anual":
            month_num = last_month_num

            possible_dates = []
            if not df_o_plot.empty:
                for y in years_all:
                    dt = pd.Timestamp(year=y, month=month_num, day=1)
                    if (df_o_plot["Date"] == dt).any():
                        possible_dates.append(dt)
            possible_dates = sorted(possible_dates, reverse=True)

            if not possible_dates:
                st.warning("No hay meses comparables en la serie original para la variación anual.")
                return

            if "ipi_sec_month_a" not in st.session_state:
                st.session_state["ipi_sec_month_a"] = possible_dates[0]
            if "ipi_sec_month_b" not in st.session_state:
                st.session_state["ipi_sec_month_b"] = possible_dates[1] if len(possible_dates) > 1 else possible_dates[0]

            with colA:
                st.markdown("<div class='fx-panel-title'>Período Final</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_month_a",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            with colB:
                st.markdown("<div class='fx-panel-title'>Período Inicial</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_month_b",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_a = pd.to_datetime(st.session_state.get("ipi_sec_month_a"))
            dt_b = pd.to_datetime(st.session_state.get("ipi_sec_month_b"))

            def _month_level_by_sector_orig(dt: pd.Timestamp) -> pd.Series:
                t = df_o_plot[df_o_plot["Date"] == dt].copy()
                return t.groupby("Sector")["Value"].mean()

            A = _month_level_by_sector_orig(dt_a)
            B = _month_level_by_sector_orig(dt_b)

            rama_label = f" — {rama_sel}" if rama_sel != "Total" else ""
            subtitle = f"Comparación anual ({MESES_ES[month_num-1]}) · A={_month_opt_label(dt_a)} / B={_month_opt_label(dt_b)}{rama_label}"

        else:
            if df_s_plot.empty:
                st.warning("No hay datos sin estacionalidad disponibles para esta comparación.")
                return

            possible_dates = sorted(df_s_plot["Date"].dropna().unique().tolist(), reverse=True)
            possible_dates = [pd.to_datetime(d) for d in possible_dates]

            if "ipi_sec_se_month_a" not in st.session_state:
                st.session_state["ipi_sec_se_month_a"] = possible_dates[0] if possible_dates else None

            with colA:
                st.markdown("<div class='fx-panel-title'>Período Final</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates,
                    key="ipi_sec_se_month_a",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_a = pd.to_datetime(st.session_state.get("ipi_sec_se_month_a"))

            possible_dates_b = [d for d in possible_dates if pd.to_datetime(d).month != dt_a.month]
            if not possible_dates_b:
                st.warning("No hay meses alternativos para Período Inicial (sin repetir el mes de A).")
                return

            if ("ipi_sec_se_month_b" not in st.session_state) or (pd.to_datetime(st.session_state["ipi_sec_se_month_b"]).month == dt_a.month):
                st.session_state["ipi_sec_se_month_b"] = possible_dates_b[0]

            with colB:
                st.markdown("<div class='fx-panel-title'>Período Inicial</div>", unsafe_allow_html=True)
                st.selectbox(
                    "",
                    possible_dates_b,
                    key="ipi_sec_se_month_b",
                    format_func=_month_opt_label,
                    label_visibility="collapsed",
                )

            dt_b = pd.to_datetime(st.session_state.get("ipi_sec_se_month_b"))

            def _month_level_by_sector_se(dt: pd.Timestamp) -> pd.Series:
                t = df_s_plot[df_s_plot["Date"] == dt].copy()
                return t.groupby("Sector")["Value"].mean()

            A = _month_level_by_sector_se(dt_a)
            B = _month_level_by_sector_se(dt_b)

            subtitle = f"Comparación serie s.e. · A={_month_opt_label(dt_a)} / B={_month_opt_label(dt_b)}"

        common = pd.DataFrame({"A": A, "B": B}).dropna()
        common = common[(common["A"] > 0) & (common["B"] > 0)]

        if common.empty:
            st.warning("No hay datos suficientes para comparar esos períodos.")
            return

        common["pct"] = (common["A"] / common["B"] - 1.0) * 100.0
        common = common.reset_index().rename(columns={"index": "Sector"})
        common = common.sort_values("pct", ascending=False).reset_index(drop=True)

        x = common["pct"].values
        x_min = float(np.nanmin(x)) if len(x) else 0.0
        x_max = float(np.nanmax(x)) if len(x) else 0.0

        pad = 0.15 * max(abs(x_min), abs(x_max), 1e-6)
        x_left = min(0.0, x_min) - pad
        x_right = max(0.0, x_max) + pad

        y_plain = common["Sector"].tolist()
        y = []
        for s in y_plain:
            if s == "IPI - Nivel general" or (rama_sel != "Total" and s == rama_sel):
                y.append(f"<b>{s}</b>")
            else:
                y.append(s)

        colors = np.where(x >= 0, "rgba(34,197,94,0.55)", "rgba(239,68,68,0.55)")

        fig2 = go.Figure()
        fig2.add_trace(
            go.Bar(
                x=x,
                y=y,
                orientation="h",
                marker=dict(color=colors),
                customdata=y_plain,
                text=[f"{v:.1f}%".replace(".", ",") for v in x],
                textposition="outside",
                texttemplate="%{text}",
                cliponaxis=False,
                hovertemplate="%{customdata}<br>%{x:.1f}%<extra></extra>",
                name="",
            )
        )

        fig2.update_layout(
            height=max(520, 26 * len(common) + 120),
            margin=dict(l=10, r=10, t=10, b=40),
            hovermode="closest",
            showlegend=False,
            dragmode=False,
        )
        fig2.update_xaxes(
            ticksuffix="%",
            range=[x_left, x_right],
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="rgba(120,120,120,0.65)",
            showgrid=True,
            gridcolor="rgba(120,120,120,0.25)",
        )
        fig2.update_yaxes(autorange="reversed")

        st.markdown(f"<div class='fx-panel-title'>{subtitle}</div>", unsafe_allow_html=True)

        st.plotly_chart(
            fig2,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            key="chart_ipi_sect_comp",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC — IPI Manufacturero (Excel .xls)"
            "</div>",
            unsafe_allow_html=True,
        )

        # =========================================================
        # Cards por rama — NUEVO FORMATO
        # =========================================================
        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # Header "Detalle por rama" con mismo formato fx-wrap
        st.markdown(
            textwrap.dedent("""
                <div class="fx-wrap" style="margin-bottom:12px;">
                  <div class="fx-title-row">
                    <div class="fx-icon-badge">🏭</div>
                    <div>
                      <div class="fx-title">Detalle por rama</div>
                      <div style="font-size:12px; color:#526484; margin-top:2px;">
                        Hacé click en una rama para ver variaciones, subsectores y la serie (s.e.)
                      </div>
                    </div>
                  </div>
                </div>
            """),
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)

        if "ipi_modal_open" not in st.session_state:
            st.session_state["ipi_modal_open"] = False
            st.session_state["ipi_modal_div_name"] = None
            st.session_state["ipi_modal_div_code"] = None
            st.session_state["ipi_modal_div_idx_c5"] = None

        def _open_modal(div_name: str, div_code: str, div_idx_c5: int):
            st.session_state["ipi_modal_open"] = True
            st.session_state["ipi_modal_div_name"] = div_name
            st.session_state["ipi_modal_div_code"] = div_code
            st.session_state["ipi_modal_div_idx_c5"] = div_idx_c5

        # ── Cards (3 columnas) ──────────────────────────────────
        for start in range(0, len(divs_idxs), 3):
            cols = st.columns(3, vertical_alignment="top")

            for j, idx in enumerate(divs_idxs[start:start + 3]):
                name     = names_c5[idx]
                div_code = str(codes_c5[idx]).strip()

                # MoM (s.e.)
                s_se_raw = procesar_serie_excel(df_c5, idx)
                s_se = _rebase_100(_clean_series(s_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                v_m = None
                if s_se is not None and not s_se.empty:
                    s_tmp = _compute_mom_df(s_se)
                    v_m = s_tmp["MoM"].dropna().iloc[-1] if s_tmp["MoM"].notna().any() else None

                # YoY (original)
                v_i = None
                header_idx = code_to_header_idx_c2.get(div_code, None)
                if header_idx is not None:
                    s_o_raw = procesar_serie_excel(df_c2, int(header_idx))
                    s_o = _rebase_100(_clean_series(s_o_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                    if s_o is not None and not s_o.empty:
                        s_y = _compute_yoy_df(s_o)
                        v_i = s_y["YoY"].dropna().iloc[-1] if s_y["YoY"].notna().any() else None

                mom_str = f"{_fmt_pct_es(v_m, 1)}%" if v_m is not None else "—"
                yoy_str = f"{_fmt_pct_es(v_i, 1)}%" if v_i is not None else "—"

                card_html = textwrap.dedent(f"""
                    <div class="ipi-card">
                      <div class="ipi-card-bar {_bar_class(v_m, v_i)}"></div>
                      <div class="ipi-card-body">
                        <div class="ipi-title">{_abbrev_name(name)}</div>
                        <div class="ipi-metrics">
                          <div class="ipi-chip {_chip_class(v_m)}">
                            <div class="ipi-chip-top">
                              <span class="ipi-chip-label">Mensual</span>
                              <span class="ipi-chip-arrow {_arrow_color_class(v_m)}">{_arrow_dir(v_m)}</span>
                            </div>
                            <div class="ipi-chip-val {_val_class(v_m)}">{mom_str}</div>
                          </div>
                          <div class="ipi-chip {_chip_class(v_i)}">
                            <div class="ipi-chip-top">
                              <span class="ipi-chip-label">Interanual</span>
                              <span class="ipi-chip-arrow {_arrow_color_class(v_i)}">{_arrow_dir(v_i)}</span>
                            </div>
                            <div class="ipi-chip-val {_val_class(v_i)}">{yoy_str}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div style="height:6px;"></div>
                """)

                with cols[j]:
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button("🔍 Abrir detalle", key=f"ipi_open_{idx}", use_container_width=True):
                        if div_code and div_code.lower() != "nan":
                            _open_modal(name, div_code, idx)
                            st.rerun()
                        else:
                            st.warning("No se encontró el código de la rama.")

        # ── Modal (sin cambios) ─────────────────────────────────
        if st.session_state.get("ipi_modal_open"):
            div_name     = st.session_state.get("ipi_modal_div_name")
            div_code     = st.session_state.get("ipi_modal_div_code")
            div_idx_c5   = st.session_state.get("ipi_modal_div_idx_c5")

            @st.dialog(f"{div_name}")
            def _modal():
                s_div_se_raw = procesar_serie_excel(df_c5, int(div_idx_c5))
                s_div_se = _rebase_100(_clean_series(s_div_se_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)

                v_m_div = None
                if s_div_se is not None and not s_div_se.empty:
                    mdf = _compute_mom_df(s_div_se)
                    v_m_div = mdf["MoM"].dropna().iloc[-1] if mdf["MoM"].notna().any() else None

                header_idx = code_to_header_idx_c2.get(str(div_code).strip(), None)
                if header_idx is None:
                    candidates = [i2 for i2 in header_idxs_c2 if names_c2[i2].strip() == str(div_name).strip()]
                    if candidates:
                        header_idx = candidates[0]

                v_i_div = None
                s_div_o = pd.DataFrame(columns=["Date", "Value"])
                if header_idx is not None:
                    s_div_o_raw = procesar_serie_excel(df_c2, int(header_idx))
                    s_div_o = _rebase_100(_clean_series(s_div_o_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                    if s_div_o is not None and not s_div_o.empty:
                        ydf = _compute_yoy_df(s_div_o)
                        v_i_div = ydf["YoY"].dropna().iloc[-1] if ydf["YoY"].notna().any() else None

                mom_modal_str = f"{_fmt_pct_es(v_m_div, 1)}%" if v_m_div is not None else "—"
                yoy_modal_str = f"{_fmt_pct_es(v_i_div, 1)}%" if v_i_div is not None else "—"

                st.markdown(
                    textwrap.dedent(f"""
                    <div class="ipi-modal-chips">
                      <div class="ipi-modal-chip {_chip_class(v_m_div)}">
                        <div class="ipi-modal-chip-top">
                          <span class="ipi-modal-chip-label">MoM</span>
                          <span class="ipi-chip-arrow {_arrow_color_class(v_m_div)}">{_arrow_dir(v_m_div)}</span>
                        </div>
                        <div class="ipi-modal-chip-val {_val_class(v_m_div)}">{mom_modal_str}</div>
                      </div>
                      <div class="ipi-modal-chip {_chip_class(v_i_div)}">
                        <div class="ipi-modal-chip-top">
                          <span class="ipi-modal-chip-label">YoY</span>
                          <span class="ipi-chip-arrow {_arrow_color_class(v_i_div)}">{_arrow_dir(v_i_div)}</span>
                        </div>
                        <div class="ipi-modal-chip-val {_val_class(v_i_div)}">{yoy_modal_str}</div>
                      </div>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

                st.caption("Nota: **(s.e)** = sin estacionalidad. Base: **100=abr-23**.")

                tab1, tab2 = st.tabs(["🔎 Subsectores", "📈 Gráfico"])

                with tab1:
                    st.caption("Variación interanual (%). Fuente: INDEC — IPI Manufacturero (Excel)")
                    if header_idx is None:
                        st.warning("No se pudo ubicar la rama en el Cuadro 2.")
                    else:
                        subcols = list(_subcol_range_for_header(header_idx, header_idxs_c2, len(codes_c2)))
                        rows = []
                        for k in subcols:
                            nm = str(names_c2[k]).strip()
                            if nm in ("", "Período", "IPI Manufacturero"):
                                continue
                            s_sub_raw = procesar_serie_excel(df_c2, k)
                            s_sub = _rebase_100(_clean_series(s_sub_raw.rename(columns={"fecha": "Date", "valor": "Value"})), BASE_DT)
                            if s_sub is None or s_sub.empty:
                                continue
                            yoy = _compute_yoy_df(s_sub)["YoY"].dropna()
                            if yoy.empty:
                                continue
                            rows.append({"Subsector": nm, "Interanual (%)": float(yoy.iloc[-1])})

                        if not rows:
                            st.info("No hay desglose adicional disponible.")
                        else:
                            df_sub = pd.DataFrame(rows)
                            df_sub["Interanual (%)"] = pd.to_numeric(df_sub["Interanual (%)"], errors="coerce")
                            df_sub = df_sub.sort_values("Interanual (%)", ascending=False).reset_index(drop=True)
                            df_sub["Interanual"] = df_sub["Interanual (%)"].apply(lambda x: f"{_fmt_pct_es(x,1)}%")

                            st.dataframe(
                                df_sub[["Subsector", "Interanual"]],
                                use_container_width=True,
                                height=520,
                                hide_index=True,
                                column_config={
                                    "Subsector": st.column_config.TextColumn("Subsector"),
                                    "Interanual": st.column_config.TextColumn("Interanual", help="Variación interanual (%)"),
                                },
                            )

                with tab2:
                    st.caption("Serie (s.e). Fuente: INDEC — IPI Manufacturero (Excel)")
                    if s_div_se is None or s_div_se.empty:
                        st.warning("No se pudo extraer la serie (s.e).")
                    else:
                        show_total = st.checkbox("Mostrar también el Total IPI (s.e)", value=True)

                        min_date = s_div_se["Date"].min().date()
                        max_date = s_div_se["Date"].max().date()

                        try:
                            default_start = (pd.Timestamp(max_date) - pd.DateOffset(years=5)).date()
                            if default_start < min_date:
                                default_start = min_date
                        except Exception:
                            default_start = min_date

                        d1, d2 = st.slider(
                            "Rango de fechas",
                            min_value=min_date,
                            max_value=max_date,
                            value=(default_start, max_date),
                        )

                        s_div_plot = s_div_se[(s_div_se["Date"].dt.date >= d1) & (s_div_se["Date"].dt.date <= d2)]

                        figm = go.Figure()

                        if show_total:
                            tot = df_ng_se[(df_ng_se["Date"].dt.date >= d1) & (df_ng_se["Date"].dt.date <= d2)]
                            if not tot.empty:
                                figm.add_trace(go.Scatter(
                                    x=tot["Date"], y=tot["Value"],
                                    mode="lines", name="Total (s.e)", line=dict(width=2)
                                ))

                        figm.add_trace(go.Scatter(
                            x=s_div_plot["Date"], y=s_div_plot["Value"],
                            mode="lines", name=f"{div_name} (s.e)", line=dict(width=3)
                        ))

                        figm.update_layout(
                            template="plotly_white",
                            height=420,
                            margin=dict(l=10, r=10, t=10, b=10),
                            hovermode="x unified",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                        )
                        st.plotly_chart(figm, use_container_width=True)

                if st.button("Cerrar", use_container_width=True):
                    st.session_state["ipi_modal_open"] = False
                    st.rerun()

            _modal()
