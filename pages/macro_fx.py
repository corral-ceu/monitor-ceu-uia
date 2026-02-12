# pages/macro_fx.py

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import random
import textwrap
import streamlit.components.v1 as components

from services.macro_data import (
    build_bands_2025,
    build_bands_2026,
    get_a3500,
    get_ipc_bcra,
    get_rem_last,
    get_itcrm_excel_long,
)

# ✅ CCL desde services (NO yfinance acá)
from services.market_data import get_ccl_ypf_df_fast

from ui.common import safe_pct


INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]


def render_macro_fx(go_to):

    # =========================
    # Botón volver
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

          /* PANEL GRANDE */
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
          .fx-panel-wrap div[data-testid="stPlotlyChart"],
          .fx-panel-wrap div[data-testid="stDownloadButton"]{
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

    # -------------------------
    # CCL proxy (FAST) desde services — igual que Home
    # -------------------------
    ccl_df = get_ccl_ypf_df_fast(period="2y", prefer_adj=False)

    ccl = ccl_df.rename(columns={"value": "CCL"}).copy()
    ccl["Date"] = pd.to_datetime(ccl["Date"], errors="coerce").dt.normalize()
    ccl["CCL"] = pd.to_numeric(ccl["CCL"], errors="coerce")
    ccl = ccl.dropna(subset=["Date", "CCL"]).drop_duplicates("Date").sort_values("Date").reset_index(drop=True)

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

    # =========================================================
    # Brecha diaria (para reusar en Brecha + TCRM (CCL))
    # brecha% = (CCL / Oficial - 1)*100
    # CCL asignado asof al calendario del oficial
    # =========================================================
    brecha_daily = pd.DataFrame(columns=["Date", "Oficial", "CCL", "Brecha"])
    if (fx is not None and not fx.empty) and (ccl is not None and not ccl.empty):
        ofi = fx[["Date", "FX"]].rename(columns={"FX": "Oficial"}).copy()
        ofi["Date"] = pd.to_datetime(ofi["Date"], errors="coerce").dt.normalize()
        ofi["Oficial"] = pd.to_numeric(ofi["Oficial"], errors="coerce")
        ofi = ofi.dropna(subset=["Date", "Oficial"]).drop_duplicates("Date").sort_values("Date").reset_index(drop=True)

        ccl_s = ccl[["Date", "CCL"]].copy()
        ccl_s["Date"] = pd.to_datetime(ccl_s["Date"], errors="coerce").dt.normalize()
        ccl_s["CCL"] = pd.to_numeric(ccl_s["CCL"], errors="coerce")
        ccl_s = ccl_s.dropna(subset=["Date", "CCL"]).drop_duplicates("Date").sort_values("Date").reset_index(drop=True)

        tmpb = pd.merge_asof(ofi, ccl_s, on="Date", direction="backward")
        tmpb["Brecha"] = (tmpb["CCL"] / tmpb["Oficial"] - 1) * 100
        brecha_daily = tmpb.dropna(subset=["Brecha"]).reset_index(drop=True)

    # =========================
    # Header dinámico según selección actual
    # =========================
    DEFAULT_VARS = ["TC Mayorista"]
    vars_state = st.session_state.get("fx_vars", DEFAULT_VARS)
    if not vars_state:
        vars_state = ["TC Mayorista"]

    header_var = "CCL" if (len(vars_state) == 1 and vars_state[0] == "CCL") else "TC Mayorista"

    if header_var == "CCL" and (ccl is not None and not ccl.empty):
        hdr_df = ccl.rename(columns={"CCL": "VAL"})[["Date", "VAL"]].copy()
        label_unidad = "ARS/USD"
    else:
        hdr_df = fx.rename(columns={"FX": "VAL"})[["Date", "VAL"]].copy()
        header_var = "TC Mayorista"
        label_unidad = "ARS/USD"

    # --- Guardas anti-baches (BCRA/Yahoo) para el header ---
    if hdr_df is None or hdr_df.empty or ("Date" not in hdr_df.columns) or ("VAL" not in hdr_df.columns):
        st.warning("Tipo de cambio: sin datos para el header (API sin respuesta o DF vacío). Reintentá más tarde.")
        return

    hdr_df = hdr_df.dropna(subset=["Date", "VAL"]).sort_values("Date").reset_index(drop=True)
    if hdr_df.empty:
        st.warning("Tipo de cambio: sin datos válidos (Date/VAL).")
        return

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
    # PANEL GRANDE REAL: marker + JS
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
    # HEADER (Tipo de cambio)
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
    last_ccl_date = pd.to_datetime(ccl["Date"].max()) if (ccl is not None and not ccl.empty) else pd.NaT
    bands_max = pd.to_datetime(bands["Date"].max()) if not bands.empty else pd.NaT

    full_end = max(d for d in [last_fx_date, last_ccl_date, bands_max] if pd.notna(d))
    cal = pd.DataFrame({"Date": pd.date_range(fx_min, full_end, freq="D")})

    ccl_panel = ccl[["Date", "CCL"]].copy() if (ccl is not None and not ccl.empty and "CCL" in ccl.columns) else pd.DataFrame(columns=["Date", "CCL"])

    df = (
        cal.merge(fx, on="Date", how="left")
        .merge(bands, on="Date", how="left")
        .merge(ccl_panel, on="Date", how="left")
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
    default_start = max(min_d, pd.to_datetime("2025-01-01").date())

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
    # PLOT (Tipo de cambio)
    # =========================
    fig = go.Figure()

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
            y2 = (y / base - 1) * 100
            fig.add_trace(
                go.Scatter(
                    x=df_plot["Date"],
                    y=y2,
                    name=v,
                    mode="lines",
                    hovertemplate="%{x|%d/%m/%Y}<br>Variación acumulada: %{y:.2f}%<extra></extra>",
                )
            )
        else:
            fig.add_trace(go.Scatter(x=df_plot["Date"], y=y, name=v, mode="lines"))

    fig.update_layout(
        height=520,
        hovermode="x",
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1.0),
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False})

    st.download_button(
        "⬇️ Descargar CSV",
        df_plot.to_csv(index=False).encode("utf-8"),
        file_name="tc.csv",
        mime="text/csv",
    )

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
        "Fuente: CEU-UIA en base a BCRA y Yahoo Finance (proxy CCL: YPFD.BA/YPF)."
        "</div>",
        unsafe_allow_html=True,
    )


    # =========================================================
    # TIPO DE CAMBIO REAL (ITCRM + bilaterales)
    # + variable sintética: "ITCRM (CCL)" = ITCRM * (1 + brecha%)
    # brecha% asof sobre fechas del TCRM (último inmediato)
    # =========================================================
    st.divider()


    tcr_long = get_itcrm_excel_long()

    if tcr_long is None or tcr_long.empty:
        st.warning("Sin datos de ITCRM.")
    else:
        tcr_long = tcr_long.copy()
        tcr_long["Date"] = pd.to_datetime(tcr_long["Date"], errors="coerce").dt.normalize()
        tcr_long["Value"] = pd.to_numeric(tcr_long["Value"], errors="coerce")
        tcr_long["Serie"] = tcr_long["Serie"].astype(str)
        tcr_long = tcr_long.dropna(subset=["Date", "Serie", "Value"]).sort_values("Date")

        preferred = ["ITCRM ", "ITCRB Brasil", "ITCRB Estados Unidos", "ITCRB China"]
        series_all = tcr_long["Serie"].dropna().unique().tolist()

        options = [s for s in preferred if s in series_all]
        options += [s for s in sorted(series_all) if s not in options]

        # ✅ Agregar "ITCRM (CCL)" como variable (solo si existe ITCRM base)
        if "ITCRM " in options and "ITCRM (CCL)" not in options:
            options.insert(options.index("ITCRM ") + 1, "ITCRM (CCL)")

        if not options:
            st.warning("No se encontraron series de ITCRM en el Excel.")
        else:
            st.markdown("<div class='tcr-panel-start'></div>", unsafe_allow_html=True)

            # --- CSS panel TCR
            st.markdown(
                """
                <style>
                section.main div[data-testid="stVerticalBlock"]:has(.tcr-panel-start){
                    background: rgba(230, 243, 255, 0.55);
                    border: 1px solid rgba(15, 55, 100, 0.10);
                    border-radius: 22px;
                    padding: 14px 14px 26px 14px;
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

                /* Selectbox medida “chip” en TCR */
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

            # ✅ Medida: SOLO Nivel / Variación acumulada (NO TCRM (CCL))
            if st.session_state.get("tcr_medida") not in ["Nivel", "Variación acumulada"]:
                st.session_state["tcr_medida"] = "Nivel"

            def _asof_tcr(df_: pd.DataFrame, target: pd.Timestamp):
                tt = df_.dropna(subset=["Date", "Value"]).sort_values("Date")
                tt = tt[tt["Date"] <= target]
                if tt.empty:
                    return None
                return float(tt["Value"].iloc[-1])

            # para el header: si seleccionan ITCRM (CCL), el header sigue mostrando ITCRM base (más estable)
            tcr_vars_now = st.session_state.get("tcr_vars", [default_main])
            if not tcr_vars_now:
                tcr_vars_now = [default_main]
            main_series = tcr_vars_now[0]
            if main_series == "ITCRM (CCL)":
                main_series = "ITCRM " if "ITCRM " in options else default_main

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

            # ffill respetando último dato por serie
            for s in series_all:
                if s in df2.columns:
                    last_s_date = tcr_long.loc[tcr_long["Serie"] == s, "Date"].max()
                    df2[s] = pd.to_numeric(df2[s], errors="coerce").ffill()
                    df2.loc[df2["Date"] > pd.to_datetime(last_s_date), s] = np.nan

            # ---- brecha asof sobre fechas TCRM (último inmediato)
            if brecha_daily is not None and not brecha_daily.empty:
                b = brecha_daily[["Date", "Brecha"]].dropna().sort_values("Date").reset_index(drop=True)
                df2 = pd.merge_asof(df2.sort_values("Date"), b, on="Date", direction="backward")
            else:
                df2["Brecha"] = np.nan

            df2["TCRM_factor_ccl"] = 1.0 + (pd.to_numeric(df2["Brecha"], errors="coerce") / 100.0)

            # ✅ variable sintética ITCRM (CCL)
            if "ITCRM " in df2.columns:
                df2["ITCRM (CCL)"] = (
                    pd.to_numeric(df2["ITCRM "], errors="coerce")
                    * pd.to_numeric(df2["TCRM_factor_ccl"], errors="coerce")
                )
            else:
                df2["ITCRM (CCL)"] = np.nan

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
            else:
                hover2 = "%{x|%d/%m/%Y}<br>Valor: %{y:.2f}<extra></extra>"

            for s in tcr_vars:
                if s not in df2_plot.columns:
                    continue

                y = pd.to_numeric(df2_plot[s], errors="coerce").copy()

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

            fig2.update_layout(
                height=520,
                hovermode="x",
                margin=dict(l=10, r=10, t=10, b=40),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
                dragmode=False,
            )

            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False})

            export_cols = ["Date"] + [s for s in tcr_vars if s in df2_plot.columns]
            export2 = df2_plot[export_cols].copy().rename(columns={"Date": "date"})

            # Siempre útil si exportan ITCRM (CCL)
            if "ITCRM (CCL)" in export2.columns:
                export2["brecha_pct_asof"] = df2_plot["Brecha"]

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
                "Fuente: BCRA — ITCRMSerie.xlsx. CCL proxy: YPFD.BA/YPF (Yahoo Finance). Brecha as-of."
                "</div>",
                unsafe_allow_html=True,
            )




    # =========================================================
    # BRECHA CAMBIARIA (CCL vs Oficial) — 3er bloque
    # usa brecha_daily (as-of sobre oficial)
    # =========================================================
    st.divider()

    def _fmt_pct_es(x: float, dec: int = 1) -> str:
        try:
            if x is None or pd.isna(x):
                return "—"
            return f"{float(x):.{dec}f}".replace(".", ",")
        except Exception:
            return "—"

    def _asof_val(df_: pd.DataFrame, target: pd.Timestamp):
        tt = df_.dropna(subset=["Date", "Value"]).sort_values("Date")
        tt = tt[tt["Date"] <= target]
        if tt.empty:
            return None
        return float(tt["Value"].iloc[-1])

    if brecha_daily is None or brecha_daily.empty:
        st.warning("Sin datos para calcular brecha (CCL u Oficial).")
        return

    st.markdown("<div class='brecha-panel-start'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        section.main div[data-testid="stVerticalBlock"]:has(.brecha-panel-start){
            background: rgba(245, 247, 250, 0.85);
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 22px;
            padding: 14px 14px 26px 14px;
            box-shadow: 0 10px 18px rgba(15,23,42,0.06);
            margin-top: 10px;
        }

        section.main div[data-testid="stVerticalBlock"]:has(.brecha-panel-start)
        div[data-testid="stSlider"],
        section.main div[data-testid="stVerticalBlock"]:has(.brecha-panel-start)
        div[data-testid="stPlotlyChart"],
        section.main div[data-testid="stVerticalBlock"]:has(.brecha-panel-start)
        div[data-testid="stDownloadButton"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    df_ok = brecha_daily.copy().sort_values("Date").reset_index(drop=True)

    last_row = df_ok.iloc[-1]
    last_date = pd.to_datetime(last_row["Date"])
    last_brecha = float(last_row["Brecha"])

    brecha_series = df_ok[["Date", "Brecha"]].rename(columns={"Brecha": "Value"}).copy()
    b_m = _asof_val(brecha_series, last_date - pd.Timedelta(days=30))
    b_y = _asof_val(brecha_series, last_date - pd.Timedelta(days=365))

    vm = None if b_m is None else (last_brecha - b_m)  # pp
    va = None if b_y is None else (last_brecha - b_y)  # pp

    a_vm, cls_vm = _arrow_cls(vm)
    a_va, cls_va = _arrow_cls(va)

    header_lines = [
        '<div class="fx-wrap">',
        '  <div class="fx-title-row">',
        '    <div class="fx-icon-badge">📉</div>',
        '    <div class="fx-title">Brecha cambiaria</div>',
        "  </div>",
        '  <div class="fx-card">',
        '    <div class="fx-row">',
        f'      <div class="fx-value">{_fmt_pct_es(last_brecha, 1)}%</div>',
        '      <div class="fx-meta">',
        f'        CCL vs Oficial<span class="sep">|</span>{last_date.strftime("%d/%m/%Y")}',
        "      </div>",
        '      <div class="fx-pills">',
        '        <div class="fx-pill red">',
        f'          <span class="fx-arrow {cls_vm}">{a_vm}</span>',
        f'          <span class="{cls_vm}">{_fmt_pct_es(vm, 1)} pp</span>',
        '          <span class="lab">mensual</span>',
        "        </div>",
        '        <div class="fx-pill green">',
        f'          <span class="fx-arrow {cls_va}">{a_va}</span>',
        f'          <span class="{cls_va}">{_fmt_pct_es(va, 1)} pp</span>',
        '          <span class="lab">interanual</span>',
        "        </div>",
        "      </div>",
        "    </div>",
        "  </div>",
        "</div>",
    ]
    st.markdown("\n".join(header_lines), unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    min_d = df_ok["Date"].min().date()
    max_d = df_ok["Date"].max().date()
    default_start = (pd.to_datetime(df_ok["Date"].max()) - pd.Timedelta(days=365)).date()
    if default_start < min_d:
        default_start = min_d

    st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
    start_b, end_b = st.slider(
        label="",
        min_value=min_d,
        max_value=max_d,
        value=(default_start, max_d),
        format="YYYY-MM-DD",
        label_visibility="collapsed",
        key="brecha_rangebar",
    )

    df_plot = df_ok[(df_ok["Date"] >= pd.Timestamp(start_b)) & (df_ok["Date"] <= pd.Timestamp(end_b))].copy()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_plot["Date"],
            y=df_plot["Brecha"],
            name="Brecha (%)",
            mode="lines",
            connectgaps=True,
            hovertemplate="%{x|%d/%m/%Y}<br>Brecha: %{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        height=520,
        hovermode="x",
        margin=dict(l=10, r=10, t=10, b=40),
        showlegend=False,
        dragmode=False,
        yaxis_title="%",
    )

    last_date_x = df_plot["Date"].max()
    fig.update_xaxes(range=[df_plot["Date"].min(), last_date_x + pd.Timedelta(days=10)])

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False})

    # Export
    export = df_plot[["Date", "Oficial", "CCL", "Brecha"]].copy()

    # Si el DF de CCL trae también YPF_ARS/YPF_USD, los agregamos; si no, seguimos sin eso.
    if ccl is not None and not ccl.empty:
        extra_cols = [c for c in ["YPF_ARS", "YPF_USD"] if c in ccl.columns]
        if extra_cols:
            ccl_cols = ccl[["Date"] + extra_cols].dropna().sort_values("Date").reset_index(drop=True)
            export = pd.merge_asof(export.sort_values("Date"), ccl_cols, on="Date", direction="backward")

    export = export.rename(
        columns={
            "Date": "date",
            "Brecha": "brecha_pct",
            "Oficial": "oficial",
            "CCL": "ccl",
            "YPF_ARS": "ypf_ars",
            "YPF_USD": "ypf_usd",
        }
    )

    st.download_button(
        label="⬇️ Descargar CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name=f"brecha_{pd.Timestamp(end_b).strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        use_container_width=False,
        key="dl_brecha_csv",
    )

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:10px;'>"
        "Fuente: Yahoo Finance (proxy CCL: YPFD.BA y YPF) y tipo de cambio mayorista A3500 (BCRA)."
        "</div>",
        unsafe_allow_html=True,
    )
