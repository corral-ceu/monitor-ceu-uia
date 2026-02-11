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


def _month_es(dt: pd.Timestamp) -> str:
    # "11/2025"
    if dt is None or pd.isna(dt):
        return "—"
    dt = pd.to_datetime(dt)
    return dt.strftime("%m/%Y")


# ============================================================
# Main
# ============================================================
def render_macro_pbi_emae(go_to):

    # =========================
    # Volver
    # =========================
    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # CSS
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

    with st.spinner("Cargando EMAE..."):
        df_o = get_emae_original()
        df_s = get_emae_deseasonalizado()

    fact.empty()

    if df_o is None or df_o.empty or df_s is None or df_s.empty:
        st.error("No pude cargar las series de EMAE desde datos.gob.ar.")
        return

    # Limpieza
    df_o = df_o.copy()
    df_s = df_s.copy()
    df_o["Date"] = pd.to_datetime(df_o["Date"], errors="coerce")
    df_s["Date"] = pd.to_datetime(df_s["Date"], errors="coerce")
    df_o["Value"] = pd.to_numeric(df_o["Value"], errors="coerce")
    df_s["Value"] = pd.to_numeric(df_s["Value"], errors="coerce")
    df_o = df_o.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)
    df_s = df_s.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)

    # Variaciones sobre series completas
    o_full_yoy = _compute_yoy(df_o)
    s_full_mom = _compute_mom(df_s)

    # KPIs “fijos” para pills:
    # - YoY: siempre del original
    # - MoM: siempre del desestacionalizado
    yoy_val = o_full_yoy["YoY"].dropna().iloc[-1] if o_full_yoy["YoY"].notna().any() else None
    yoy_date = o_full_yoy.dropna(subset=["YoY"]).iloc[-1]["Date"] if o_full_yoy["YoY"].notna().any() else None

    mom_val = s_full_mom["MoM"].dropna().iloc[-1] if s_full_mom["MoM"].notna().any() else None
    mom_date = s_full_mom.dropna(subset=["MoM"]).iloc[-1]["Date"] if s_full_mom["MoM"].notna().any() else None

    # =========================
    # Defaults (pedido)
    # =========================
    if "emae_variable" not in st.session_state:
        st.session_state["emae_variable"] = "Serie desestacionalizada"
    if "emae_medida" not in st.session_state:
        st.session_state["emae_medida"] = "Nivel"

    # Normalizar estado por si cambian opciones
    if st.session_state["emae_variable"] not in ["Serie original", "Serie desestacionalizada"]:
        st.session_state["emae_variable"] = "Serie desestacionalizada"
    if st.session_state["emae_medida"] not in ["Nivel", "Variación mensual", "Variación anual"]:
        st.session_state["emae_medida"] = "Nivel"

    # Restricciones:
    # - Original: solo Nivel o Variación anual
    # - Desest.: solo Nivel o Variación mensual
    var_now = st.session_state["emae_variable"]
    medida_now = st.session_state["emae_medida"]

    if var_now == "Serie original" and medida_now == "Variación mensual":
        st.session_state["emae_medida"] = "Nivel"
    if var_now == "Serie desestacionalizada" and medida_now == "Variación anual":
        st.session_state["emae_medida"] = "Nivel"

    # =========================
    # Panel único
    # =========================
    with st.container():
        _apply_panel_wrap("emae_panel_marker")

        # Header fijo: "EMAE"
        # Valor grande: mostramos YoY del original (como pediste: "-0,3% EMAE (original)|YoY|11/2025")
        st.markdown(
            "\n".join(
                [
                    '<div class="fx-wrap">',
                    '  <div class="fx-title-row">',
                    '    <div class="fx-icon-badge">📊</div>',
                    '    <div class="fx-title">EMAE</div>',
                    "  </div>",
                    '  <div class="fx-card">',
                    '    <div class="fx-row">',
                    f'      <div class="fx-value">{_fmt_pct_es(yoy_val, 1)}%</div>' if yoy_val is not None else '      <div class="fx-value">—</div>',
                    '      <div class="fx-meta">',
                    f'        EMAE (original)<span class="sep">|</span>YoY<span class="sep">|</span>{_month_es(yoy_date)}',
                    "      </div>",
                    '      <div class="fx-pills">',
                    # pill 1: YoY original
                    '        <div class="fx-pill red">',
                    f'          <span class="fx-arrow {_arrow_cls(yoy_val)[1]}">{_arrow_cls(yoy_val)[0]}</span>',
                    f'          <span class="{_arrow_cls(yoy_val)[1]}">{_fmt_pct_es(yoy_val, 1) if yoy_val is not None else "—"}%</span>',
                    '          <span class="lab">anual (orig.)</span>',
                    "        </div>",
                    # pill 2: MoM desest
                    '        <div class="fx-pill green">',
                    f'          <span class="fx-arrow {_arrow_cls(mom_val)[1]}">{_arrow_cls(mom_val)[0]}</span>',
                    f'          <span class="{_arrow_cls(mom_val)[1]}">{_fmt_pct_es(mom_val, 1) if mom_val is not None else "—"}%</span>',
                    '          <span class="lab">mensual (s.e.)</span>',
                    "        </div>",
                    "      </div>",
                    "    </div>",
                    "  </div>",
                    "</div>",
                ]
            ),
            unsafe_allow_html=True,
        )

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        # =========================
        # Controles (swap)
        # =========================
        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                ["Serie original", "Serie desestacionalizada"],
                key="emae_variable",
                label_visibility="collapsed",
            )

        # Re-calcular opciones de medida según variable elegida
        var_now = st.session_state.get("emae_variable", "Serie desestacionalizada")
        if var_now == "Serie original":
            medida_opts = ["Nivel", "Variación anual"]
        else:
            medida_opts = ["Nivel", "Variación mensual"]

        # Ajustar medida si quedó inválida
        if st.session_state.get("emae_medida") not in medida_opts:
            st.session_state["emae_medida"] = "Nivel"

        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                medida_opts,
                key="emae_medida",
                label_visibility="collapsed",
            )

        # =========================
        # Rango de fechas (default: mínimo disponible ~2004)
        # =========================
        max_real = max(pd.to_datetime(df_o["Date"].max()), pd.to_datetime(df_s["Date"].max()))
        min_real = min(pd.to_datetime(df_o["Date"].min()), pd.to_datetime(df_s["Date"].min()))
        min_d = min_real.date()
        max_d = max_real.date()

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.slider(
            "",
            min_value=min_d,
            max_value=max_d,
            value=(min_d, max_d),
            label_visibility="collapsed",
            key="emae_range",
        )

        start_ts = pd.Timestamp(start_d)
        end_ts = pd.Timestamp(end_d)

        # =========================
        # Series elegidas + medida
        # =========================
        medida = st.session_state.get("emae_medida", "Nivel")
        fig = go.Figure()

        if var_now == "Serie original":
            lvl = df_o[(df_o["Date"] >= start_ts) & (df_o["Date"] <= end_ts)].copy()
            yoy = o_full_yoy[(o_full_yoy["Date"] >= start_ts) & (o_full_yoy["Date"] <= end_ts)].copy()

            if medida == "Nivel":
                # líneas
                fig.add_trace(
                    go.Scatter(
                        x=lvl["Date"],
                        y=lvl["Value"],
                        mode="lines",
                        name="EMAE (original)",
                    )
                )
                fig.update_yaxes(title="Índice")
            else:
                # barras
                fig.add_trace(
                    go.Bar(
                        x=yoy["Date"],
                        y=yoy["YoY"],
                        name="EMAE (original) - anual",
                    )
                )
                fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#666666")
                fig.update_yaxes(ticksuffix="%")

        else:
            lvl = df_s[(df_s["Date"] >= start_ts) & (df_s["Date"] <= end_ts)].copy()
            mom = s_full_mom[(s_full_mom["Date"] >= start_ts) & (s_full_mom["Date"] <= end_ts)].copy()

            if medida == "Nivel":
                # líneas
                fig.add_trace(
                    go.Scatter(
                        x=lvl["Date"],
                        y=lvl["Value"],
                        mode="lines",
                        name="EMAE (desestacionalizada)",
                    )
                )
                fig.update_yaxes(title="Índice")
            else:
                # barras
                fig.add_trace(
                    go.Bar(
                        x=mom["Date"],
                        y=mom["MoM"],
                        name="EMAE (desest.) - mensual",
                    )
                )
                fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#666666")
                fig.update_yaxes(ticksuffix="%")

        fig.update_layout(
            height=520,
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode=False,
        )

        # Aire a la derecha
        x_max = pd.Timestamp(end_ts) + pd.Timedelta(days=10)
        fig.update_xaxes(range=[pd.Timestamp(start_ts), x_max])

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            key="chart_emae",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC (EMAE) vía API datos.gob.ar"
            "</div>",
            unsafe_allow_html=True,
        )

