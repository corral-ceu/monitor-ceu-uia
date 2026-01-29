import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import random
import textwrap
import yfinance as yf
import streamlit.components.v1 as components  # <-- NUEVO

from services.macro_data import (
    build_bands_2025,
    build_bands_2026,
    get_a3500,
    get_ipc_bcra,
    get_rem_last,
    get_itcrm_excel_long,
)

from ui.common import safe_pct


INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]


# ============================================================
# CCL (Yahoo proxy): CCL = YPFD.BA / YPF
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def get_ccl_yahoo() -> pd.DataFrame:
    def _close_series(ticker: str, out_name: str) -> pd.Series:
        px = yf.download(ticker, period="max", progress=False)

        if isinstance(px.columns, pd.MultiIndex):
            if ("Close", ticker) in px.columns:
                s = px[("Close", ticker)]
            elif ("Adj Close", ticker) in px.columns:
                s = px[("Adj Close", ticker)]
            else:
                try:
                    s = px.xs("Close", axis=1, level=0).iloc[:, 0]
                except Exception:
                    s = px.select_dtypes(include=[np.number]).iloc[:, 0]
        else:
            if "Close" in px.columns:
                s = px["Close"]
            elif "Adj Close" in px.columns:
                s = px["Adj Close"]
            else:
                s = px.select_dtypes(include=[np.number]).iloc[:, 0]

        s = pd.to_numeric(s, errors="coerce")
        s.name = out_name
        return s

    ypf_ars = _close_series("YPFD.BA", "YPF_ARS")
    ypf_usd = _close_series("YPF", "YPF_USD")

    df = pd.concat([ypf_ars, ypf_usd], axis=1, join="outer").sort_index()
    df["CCL"] = df["YPF_ARS"] / df["YPF_USD"]
    df = df.dropna(subset=["CCL"]).copy()

    out = df[["CCL"]].reset_index()
    if "Date" not in out.columns:
        out = out.rename(columns={out.columns[0]: "Date"})
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.normalize()
    out["CCL"] = pd.to_numeric(out["CCL"], errors="coerce")
    out = out.dropna(subset=["Date", "CCL"]).sort_values("Date").reset_index(drop=True)
    return out


def render_macro_fx(go_to):

    # =========================
    # Botón volver (afuera del panel)
    # =========================
    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # CSS (incluye el panel grande)
    # =========================
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

          .fx-pill .lab{ color:#2b4660; font-weight: 700; }

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

          /* ===============================
             PANEL GRANDE REAL (aplicado por JS al contenedor de Streamlit)
             =============================== */
          .fx-panel-wrap{
            background: rgba(230, 243, 255, 0.55);
            border: 1px solid rgba(15, 55, 100, 0.10);
            border-radius: 22px;
            padding: 16px 16px 26px 16px; /* (3) + aire abajo */
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }

          /* Evitar “cortes” visuales dentro del panel */
          .fx-panel-wrap div[data-testid="stSelectbox"],
          .fx-panel-wrap div[data-testid="stMultiSelect"],
          .fx-panel-wrap div[data-testid="stSlider"],
          .fx-panel-wrap div[data-testid="stPlotlyChart"],
          .fx-panel-wrap div[data-testid="stDownloadButton"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
          }

          /* Estilo combobox base (default) */
          .fx-panel-wrap div[role="combobox"]{
            border-radius: 16px !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 10px 18px rgba(15, 55, 100, 0.08) !important;
          }

          /* (2) SELECTBOX "Medida" estilo chip (oscuro + texto azul) */
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

          /* Tags multiselect visibles (variable ya venía así) */
          .fx-panel-wrap span[data-baseweb="tag"]{
            background: #0b2a55 !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
          }
          .fx-panel-wrap span[data-baseweb="tag"] *{
            color: #ffffff !important;
            fill: #ffffff !important;
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

    # =========================
    # Load data
    # =========================
    fact = st.empty()
    fact.info("💡 " + random.choice(INDU_LOADING_PHRASES))

    with st.spinner("Cargando datos..."):
        fx = get_a3500().copy()
        fx["Date"] = pd.to_datetime(fx["Date"], errors="coerce").dt.normalize()
        fx["FX"] = pd.to_numeric(fx["FX"], errors="coerce")
        fx = (
            fx.dropna(subset=["Date", "FX"])
            .drop_duplicates(subset=["Date"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        rem = get_rem_last()
        ipc = get_ipc_bcra()

        bands_2025 = build_bands_2025("2025-04-14", "2025-12-31", 1000.0, 1400.0)
        bands_2026 = build_bands_2026(bands_2025, rem, ipc)

        bands = (
            pd.concat([bands_2025, bands_2026], ignore_index=True)
            .dropna(subset=["Date", "lower", "upper"])
            .sort_values("Date")
            .reset_index(drop=True)
        )
        bands["Date"] = pd.to_datetime(bands["Date"], errors="coerce").dt.normalize()
        bands = bands.dropna(subset=["Date", "lower", "upper"])

        ccl = get_ccl_yahoo()

    fact.empty()

    if fx.empty:
        st.warning("Sin datos del tipo de cambio.")
        return

    # =========================
    # Helpers
    # =========================
    def _asof(df_: pd.DataFrame, target: pd.Timestamp, col: str):
        t = df_.dropna(subset=["Date", col]).sort_values("Date")
        t = t[t["Date"] <= target]
        if t.empty:
            return None
        return float(t[col].iloc[-1])

    def _arrow_cls(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return ("", "")
        return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")

    # =========================
    # Header dinámico según selección actual
    # =========================
    DEFAULT_VARS = ["TC Mayorista"]
    vars_state = st.session_state.get("fx_vars", DEFAULT_VARS)
    if not vars_state:
        vars_state = ["TC Mayorista"]

    header_var = "CCL" if (len(vars_state) == 1 and vars_state[0] == "CCL") else "TC Mayorista"

    if header_var == "CCL" and not ccl.empty:
        hdr_df = ccl.rename(columns={"CCL": "VAL"}).copy()
        label_unidad = "ARS/USD"
    else:
        hdr_df = fx.rename(columns={"FX": "VAL"}).copy()
        header_var = "TC Mayorista"
        label_unidad = "ARS/USD"

    last_date = pd.to_datetime(hdr_df["Date"].iloc[-1])
    last_val = float(hdr_df["VAL"].iloc[-1])

    val_m = _asof(hdr_df, last_date - pd.Timedelta(days=30), "VAL")
    val_y = _asof(hdr_df, last_date - pd.Timedelta(days=365), "VAL")

    vm = None if val_m is None else (last_val / val_m - 1) * 100
    va = None if val_y is None else (last_val / val_y - 1) * 100

    a_vm, cls_vm = _arrow_cls(vm)
    a_va, cls_va = _arrow_cls(va)

    vm_txt = safe_pct(vm, 1)
    va_txt = safe_pct(va, 1)

    # =========================================================
    # PANEL GRANDE REAL: marker + JS que “marca” el contenedor
    # =========================================================
    st.markdown("<span id='fx_panel_marker'></span>", unsafe_allow_html=True)

    components.html(
        """
        <script>
        (function() {
          function applyFxPanelClass() {
            const marker = window.parent.document.getElementById('fx_panel_marker');
            if (!marker) return;

            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
          }

          applyFxPanelClass();

          let tries = 0;
          const t = setInterval(() => {
            applyFxPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
          }, 150);

          const obs = new MutationObserver(() => applyFxPanelClass());
          obs.observe(window.parent.document.body, { childList: true, subtree: true });
          setTimeout(() => obs.disconnect(), 3000);
        })();
        </script>
        """,
        height=0,
    )

    # =========================
    # HEADER
    # =========================
    header_lines = [
        '<div class="fx-wrap">',
        '  <div class="fx-title-row">',
        '    <div class="fx-icon-badge">💵</div>',
        '    <div class="fx-title">Tipo de cambio</div>',
        "  </div>",
        '  <div class="fx-card">',
        '    <div class="fx-row">',
        f'      <div class="fx-value">{int(round(last_val))}</div>',
        '      <div class="fx-meta">',
        f'        {header_var}<span class="sep">|</span>{label_unidad}<span class="sep">|</span>{last_date.strftime("%d/%m/%Y")}',
        "      </div>",
        '      <div class="fx-pills">',
        '        <div class="fx-pill red">',
        f'          <span class="fx-arrow {cls_vm}">{a_vm}</span>',
        f'          <span class="{cls_vm}">{vm_txt}</span>',
        '          <span class="lab">mensual</span>',
        "        </div>",
        '        <div class="fx-pill green">',
        f'          <span class="fx-arrow {cls_va}">{a_va}</span>',
        f'          <span class="{cls_va}">{va_txt}</span>',
        '          <span class="lab">interanual</span>',
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "</div>",
    ]
    st.markdown("\n".join(header_lines), unsafe_allow_html=True)

    st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

    # =========================
    # CONTROLES
    # =========================
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
        medida = st.selectbox(
            "",
            ["Nivel", "Variación acumulada"],
            label_visibility="collapsed",
            key="fx_medida",
        )

    with c2:
        st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
        variables = st.multiselect(
            "",
            options=["TC Mayorista", "CCL"],
            default=DEFAULT_VARS,
            label_visibility="collapsed",
            key="fx_vars",
        )

    if not variables:
        variables = ["TC Mayorista"]

    # =========================
    # MASTER DF
    # =========================
    fx_min = pd.to_datetime(fx["Date"].min())
    last_fx_date = pd.to_datetime(fx["Date"].max())
    last_ccl_date = pd.to_datetime(ccl["Date"].max()) if not ccl.empty else pd.NaT
    bands_max = pd.to_datetime(bands["Date"].max()) if not bands.empty else pd.NaT

    full_end = max(d for d in [last_fx_date, last_ccl_date, bands_max] if pd.notna(d))
    cal = pd.DataFrame({"Date": pd.date_range(fx_min, full_end, freq="D")})

    df = (
        cal.merge(fx, on="Date", how="left")
           .merge(bands, on="Date", how="left")
           .merge(ccl, on="Date", how="left")
           .sort_values("Date")
           .reset_index(drop=True)
    )

    df["FX"] = df["FX"].ffill()
    df.loc[df["Date"] > last_fx_date, "FX"] = np.nan
    df["CCL"] = df["CCL"].ffill()
    if pd.notna(last_ccl_date):
        df.loc[df["Date"] > last_ccl_date, "CCL"] = np.nan

    # =========================
    # Slider
    # =========================
    cols_map = {"TC Mayorista": "FX", "CCL": "CCL"}
    sel_cols = [cols_map[v] for v in variables]

    mask_any = df[sel_cols].notna().any(axis=1)
    s_min = df.loc[mask_any, "Date"].min()
    s_max = df.loc[mask_any, "Date"].max()

    if medida == "Nivel" and pd.notna(bands_max):
        s_max = max(s_max, bands_max)

    min_d = s_min.date()
    max_d = s_max.date()
    default_start = max(min_d, (s_max - pd.Timedelta(days=365)).date())

    st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
    start_d, end_d = st.slider(
        "",
        min_value=min_d,
        max_value=max_d,
        value=(default_start, max_d),
        label_visibility="collapsed",
        key="fx_rangebar",
    )

    df_plot = df[(df["Date"] >= pd.Timestamp(start_d)) & (df["Date"] <= pd.Timestamp(end_d))].copy()
    if medida == "Nivel" and pd.notna(bands_max):
        df_plot = df_plot[df_plot["Date"] <= bands_max]

    # =========================
    # PLOT
    # =========================
    fig = go.Figure()

    # (1) Bandas más claras
    band_line = "rgba(35, 120, 200, 0.55)"
    band_fill = "rgba(35, 120, 200, 0.08)"

    if medida == "Nivel" and not bands.empty:
        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["upper"],
                name="Banda superior",
                line=dict(dash="dash", color=band_line),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["lower"],
                name="Banda inferior",
                line=dict(dash="dash", color=band_line),
                fill="tonexty",
                fillcolor=band_fill,
            )
        )

    for v in variables:
        col = cols_map[v]
        y = df_plot[col]

        if medida == "Variación acumulada":
            base = y.dropna().iloc[0]
            y = (y / base - 1) * 100
            fig.add_trace(go.Scatter(x=df_plot["Date"], y=y, name=v, mode="lines", hovertemplate="%{x|%d/%m/%Y}<br>Variación acumulada: %{y:.2f}%<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=df_plot["Date"], y=y, name=v, mode="lines"))

    fig.update_layout(height=520, hovermode="x", margin=dict(l=10, r=10, t=10, b=40), legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1.0), dragmode=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False})

    # =========================
    # CSV + Fuente
    # =========================
    st.download_button(
        "⬇️ Descargar CSV",
        df_plot.to_csv(index=False).encode("utf-8"),
        file_name="tc.csv",
        mime="text/csv",
    )

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
        "Fuente: CEU-UIA en base a BCRA y Yahoo Finance."
        "</div>",
        unsafe_allow_html=True,
    )

    # =========================================================
    # TIPO DE CAMBIO REAL (ITCRM + bilaterales) — FORMATO NUEVO
    # =========================================================
    st.divider()

    with st.spinner("Cargando ITCRM..."):
        tcr_long = get_itcrm_excel_long()

    if tcr_long is None or tcr_long.empty:
        st.warning("Sin datos de ITCRM.")
    else:
        # Normalización mínima
        tcr_long = tcr_long.copy()
        tcr_long["Date"] = pd.to_datetime(tcr_long["Date"], errors="coerce").dt.normalize()
        tcr_long["Value"] = pd.to_numeric(tcr_long["Value"], errors="coerce")
        tcr_long["Serie"] = tcr_long["Serie"].astype(str)
        tcr_long = tcr_long.dropna(subset=["Date", "Serie", "Value"]).sort_values("Date")

        preferred = ["ITCRM ", "ITCRB Brasil", "ITCRB Estados Unidos", "ITCRB China"]
        series_all = tcr_long["Serie"].dropna().unique().tolist()

        options = [s for s in preferred if s in series_all]
        options += [s for s in sorted(series_all) if s not in options]

        if not options:
            st.warning("No se encontraron series de ITCRM en el Excel.")
        else:
            st.markdown("<div class='tcr-panel-start'></div>", unsafe_allow_html=True)

            # --- CSS del panel TCR (solo (3): + aire abajo)
            st.markdown(
                """
                <style>
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start){
                    background: rgba(230, 243, 255, 0.55);
                    border: 1px solid rgba(15, 55, 100, 0.10);
                    border-radius: 22px;
                    padding: 14px 14px 26px 14px; /* (3) + aire abajo */
                    box-shadow: 0 10px 18px rgba(15,55,100,0.06);
                    margin-top: 10px;
                }

                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stSelectbox"],
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stMultiSelect"],
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stSlider"],
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stPlotlyChart"],
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stDownloadButton"]{
                    background: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                    margin: 0 !important;
                }

                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[role="combobox"]{
                    border-radius: 16px !important;
                    border: 1px solid rgba(15,23,42,0.10) !important;
                    background: rgba(255,255,255,0.94) !important;
                    box-shadow: 0 10px 18px rgba(15, 55, 100, 0.08) !important;
                }

                /* (2) Selectbox medida también “chip” en TCR */
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stSelectbox"] div[role="combobox"]{
                    background: #0b2a55 !important;
                    border: 1px solid rgba(255,255,255,0.14) !important;
                }
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stSelectbox"] div[role="combobox"] *{
                    color: #8fc2ff !important;
                    fill: #8fc2ff !important;
                    font-weight: 800 !important;
                }

                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stMultiSelect"] span[data-baseweb="tag"]{
                    background: #0b2a55 !important;
                    color: #ffffff !important;
                    border-radius: 10px !important;
                    border: 1px solid rgba(255,255,255,0.12) !important;
                }
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start)
                div[data-testid="stMultiSelect"] span[data-baseweb="tag"] *{
                    color: #ffffff !important;
                    fill: #ffffff !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            default_main = "ITCRM " if "ITCRM " in options else (options[0] if options else "")
            default_tcr_vars = st.session_state.get("tcr_vars", [default_main])

            if "tcr_medida" not in st.session_state:
                st.session_state["tcr_medida"] = "Nivel"

            def _asof_tcr(df_: pd.DataFrame, target: pd.Timestamp):
                tt = df_.dropna(subset=["Date", "Value"]).sort_values("Date")
                tt = tt[tt["Date"] <= target]
                if tt.empty:
                    return None
                return float(tt["Value"].iloc[-1])

            tcr_vars_now = st.session_state.get("tcr_vars", [default_main])
            if not tcr_vars_now:
                tcr_vars_now = [default_main]
            main_series = tcr_vars_now[0]

            tcr_main = tcr_long[tcr_long["Serie"] == main_series].sort_values("Date")
            last_tcr_date = pd.to_datetime(tcr_main["Date"].iloc[-1]) if not tcr_main.empty else pd.NaT
            last_tcr_val = float(tcr_main["Value"].iloc[-1]) if not tcr_main.empty else np.nan

            vm_tcr = None
            va_tcr = None
            if pd.notna(last_tcr_date) and pd.notna(last_tcr_val):
                m = _asof_tcr(tcr_main, last_tcr_date - pd.Timedelta(days=30))
                y = _asof_tcr(tcr_main, last_tcr_date - pd.Timedelta(days=365))
                vm_tcr = None if m is None else (last_tcr_val / m - 1) * 100
                va_tcr = None if y is None else (last_tcr_val / y - 1) * 100

            a_vm2, cls_vm2 = _arrow_cls(vm_tcr)
            a_va2, cls_va2 = _arrow_cls(va_tcr)
            vm2_txt = safe_pct(vm_tcr, 1)
            va2_txt = safe_pct(va_tcr, 1)

            header2_lines = [
                '<div class="fx-wrap">',
                '  <div class="fx-title-row">',
                '    <div class="fx-icon-badge">🌍</div>',
                '    <div class="fx-title">Tipo de cambio real</div>',
                "  </div>",
                '  <div class="fx-card">',
                '    <div class="fx-row">',
                f'      <div class="fx-value">{(f"{last_tcr_val:.1f}".replace(".", ",")) if pd.notna(last_tcr_val) else "—"}</div>',
                '      <div class="fx-meta">',
                f'        {main_series}<span class="sep">|</span>Índice (100=17-dic-15)<span class="sep">|</span>{last_tcr_date.strftime("%d/%m/%Y") if pd.notna(last_tcr_date) else ""}',
                "      </div>",
                '      <div class="fx-pills">',
                '        <div class="fx-pill red">',
                f'          <span class="fx-arrow {cls_vm2}">{a_vm2}</span>',
                f'          <span class="{cls_vm2}">{vm2_txt}</span>',
                '          <span class="lab">mensual</span>',
                "        </div>",
                '        <div class="fx-pill green">',
                f'          <span class="fx-arrow {cls_va2}">{a_va2}</span>',
                f'          <span class="{cls_va2}">{va2_txt}</span>',
                '          <span class="lab">interanual</span>',
                "        </div>",
                "      </div>",
                "    </div>",
                "  </div>",
                "</div>",
            ]
            st.markdown("\n".join(header2_lines), unsafe_allow_html=True)

            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2, gap="large")

            with c1:
                st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
                tcr_medida = st.selectbox(
                    "",
                    ["Nivel", "Variación acumulada"],
                    index=0 if st.session_state.get("tcr_medida", "Nivel") == "Nivel" else 1,
                    label_visibility="collapsed",
                    key="tcr_medida",
                )

            with c2:
                st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
                tcr_vars = st.multiselect(
                    "",
                    options=options,
                    default=default_tcr_vars,
                    label_visibility="collapsed",
                    key="tcr_vars",
                )

            if not tcr_vars:
                tcr_vars = [default_main]
                st.session_state["tcr_vars"] = tcr_vars

            tcr_min = pd.to_datetime(tcr_long["Date"].min())
            tcr_max = pd.to_datetime(tcr_long["Date"].max())

            cal2 = pd.DataFrame({"Date": pd.date_range(tcr_min, tcr_max, freq="D")})

            wide = (
                tcr_long.pivot_table(index="Date", columns="Serie", values="Value", aggfunc="last")
                .sort_index()
                .reset_index()
            )

            df2 = cal2.merge(wide, on="Date", how="left").sort_values("Date").reset_index(drop=True)

            for s in options:
                if s in df2.columns:
                    last_s_date = tcr_long.loc[tcr_long["Serie"] == s, "Date"].max()
                    df2[s] = pd.to_numeric(df2[s], errors="coerce").ffill()
                    df2.loc[df2["Date"] > pd.to_datetime(last_s_date), s] = np.nan

            sel_cols2 = [s for s in tcr_vars if s in df2.columns]
            mask_any2 = df2[sel_cols2].notna().any(axis=1) if sel_cols2 else (df2["Date"].notna())

            s_min2 = df2.loc[mask_any2, "Date"].min()
            s_max2 = df2.loc[mask_any2, "Date"].max()

            if pd.isna(s_min2) or pd.isna(s_max2):
                s_min2, s_max2 = tcr_min, tcr_max

            min_date2 = pd.to_datetime(s_min2).date()
            max_date2 = pd.to_datetime(s_max2).date()

            default_start2 = (pd.to_datetime(s_max2) - pd.Timedelta(days=365)).date()
            if default_start2 < min_date2:
                default_start2 = min_date2

            st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
            start2, end2 = st.slider(
                label="",
                min_value=min_date2,
                max_value=max_date2,
                value=(default_start2, max_date2),
                format="YYYY-MM-DD",
                label_visibility="collapsed",
                key="tcr_rangebar",
            )

            df2_plot = df2[(df2["Date"] >= pd.Timestamp(start2)) & (df2["Date"] <= pd.Timestamp(end2))].copy()

            fig2 = go.Figure()

            if tcr_medida == "Variación acumulada":
                hover2 = "%{x|%d/%m/%Y}<br>Variación acumulada: %{y:.2f}%<extra></extra>"
                y_title2 = "%"
            else:
                hover2 = "%{x|%d/%m/%Y}<br>Valor: %{y:.2f}<extra></extra>"
                y_title2 = ""

            for s in tcr_vars:
                if s not in df2_plot.columns:
                    continue
                y = df2_plot[s].copy()

                if tcr_medida == "Variación acumulada":
                    base_series = y.dropna()
                    base = float(base_series.iloc[0]) if not base_series.empty else np.nan
                    y_plot = (y / base - 1) * 100
                    name = f"{s} (var. acum.)"
                else:
                    y_plot = y
                    name = s

                fig2.add_trace(
                    go.Scatter(
                        x=df2_plot["Date"],
                        y=y_plot,
                        name=name,
                        mode="lines",
                        connectgaps=True,
                        hovertemplate=hover2,
                    )
                )

            fig2.update_layout(height=520, hovermode="x", margin=dict(l=10, r=10, t=10, b=40), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0), dragmode=False)

            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False})



            export2 = df2_plot[["Date"] + [s for s in tcr_vars if s in df2_plot.columns]].copy()
            export2 = export2.rename(columns={"Date": "date"})

            st.download_button(
                label="⬇️ Descargar CSV",
                data=export2.to_csv(index=False).encode("utf-8"),
                file_name=f"tcr_{pd.Timestamp(end2).strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
                use_container_width=False,
                key="dl_tcr_csv",
            )

            st.markdown(
                "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:10px;'>"
                "Fuente: BCRA — ITCRMSerie.xlsx."
                "</div>",
                unsafe_allow_html=True,
            )
