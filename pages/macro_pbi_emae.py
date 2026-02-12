import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import random
import textwrap
import streamlit.components.v1 as components
from services.macro_data import get_emae_sectores_long
from services.macro_data import (
    get_emae_original,
    get_emae_deseasonalizado,
    get_isac_original,
    get_isac_deseasonalizado,
    get_ipi_manuf_original,
    get_ipi_manuf_deseasonalizado,
    get_ipi_minero_original,
    get_ipi_minero_deseasonalizado,
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


def _month_es(dt: pd.Timestamp) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = pd.to_datetime(dt)
    return dt.strftime("%m/%Y")


# ============================================================
# Main
# ============================================================
def render_macro_pbi_emae(go_to):

    # =========================
    # Volver (afuera del panel)
    # =========================
    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # CSS (COPIA del formato TASA)
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

          /* ===============================
             PANEL GRANDE REAL (aplicado por JS al contenedor de Streamlit)
             =============================== */
          .fx-panel-wrap{
            background: rgba(230, 243, 255, 0.55);
            border: 1px solid rgba(15, 55, 100, 0.10);
            border-radius: 22px;
            padding: 16px 16px 26px 16px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }

          /* Evitar “cortes” visuales dentro del panel */
          .fx-panel-wrap div[data-testid="stSelectbox"],
          .fx-panel-wrap div[data-testid="stMultiSelect"],
          .fx-panel-wrap div[data-testid="stSlider"],
          .fx-panel-wrap div[data-testid="stPlotlyChart"]{
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

          /* Selectbox medida estilo chip (oscuro + texto azul) */
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

          /* Tags multiselect (texto BLANCO garantizado) */
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

    with st.spinner("Cargando indicadores..."):
        df_emae_o = get_emae_original()
        df_emae_s = get_emae_deseasonalizado()

        df_isac_o = get_isac_original()
        df_isac_s = get_isac_deseasonalizado()

        df_ipim_o = get_ipi_manuf_original()
        df_ipim_s = get_ipi_manuf_deseasonalizado()

        df_ipimin_o = get_ipi_minero_original()
        df_ipimin_s = get_ipi_minero_deseasonalizado()

    fact.empty()

    # Limpieza helper rápida
    def _clean(df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["Date", "Value"])
        t = df.copy()
        t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
        t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
        return t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)

    df_emae_o = _clean(df_emae_o)
    df_emae_s = _clean(df_emae_s)
    df_isac_o = _clean(df_isac_o)
    df_isac_s = _clean(df_isac_s)
    df_ipim_o = _clean(df_ipim_o)
    df_ipim_s = _clean(df_ipim_s)
    df_ipimin_o = _clean(df_ipimin_o)
    df_ipimin_s = _clean(df_ipimin_s)

    BASE_DT = pd.Timestamp("2023-11-01")  # nov-23 (MS)

    def _rebase_100(df: pd.DataFrame, base_dt: pd.Timestamp) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        t = df.copy()
        t["Date"] = pd.to_datetime(t["Date"], errors="coerce")
        t["Value"] = pd.to_numeric(t["Value"], errors="coerce")
        t = t.dropna(subset=["Date", "Value"]).sort_values("Date").reset_index(drop=True)

        base_val = t.loc[t["Date"] == base_dt, "Value"]
        if base_val.empty:
            # si justo no existe el mes (raro), no rebasea
            return t
        b = float(base_val.iloc[0])
        if b == 0 or np.isnan(b):
            return t

        t["Value"] = (t["Value"] / b) * 100.0
        return t

    # Rebase SOLO las desestacionalizadas (nivel)
    df_emae_s = _rebase_100(df_emae_s, BASE_DT)
    df_isac_s = _rebase_100(df_isac_s, BASE_DT)
    df_ipim_s = _rebase_100(df_ipim_s, BASE_DT)
    df_ipimin_s = _rebase_100(df_ipimin_s, BASE_DT)

    

    # Guard mínimo: al menos EMAE (como antes)
    if df_emae_o.empty or df_emae_s.empty:
        st.error("No pude cargar las series de EMAE desde datos.gob.ar.")
        return

    # Diccionario de variables (label -> (original, sa))
    SERIES = {
        "EMAE - Nivel general": (df_emae_o, df_emae_s),
        "IPI Manufacturero": (df_ipim_o, df_ipim_s),
        "IPI Minero": (df_ipimin_o, df_ipimin_s),
        "ISAC - Construcción": (df_isac_o, df_isac_s),
    }

    # Variaciones completas por serie (precomputo)
    YOY = {k: _compute_yoy(v[0]) if not v[0].empty else pd.DataFrame(columns=["Date", "Value", "YoY"]) for k, v in SERIES.items()}
    MOM = {k: _compute_mom(v[1]) if not v[1].empty else pd.DataFrame(columns=["Date", "Value", "MoM"]) for k, v in SERIES.items()}

    # KPIs del header: se mantienen EMAE como antes (YoY original + MoM s.e.)
    o_full_yoy = YOY["EMAE - Nivel general"]
    s_full_mom = MOM["EMAE - Nivel general"]

    yoy_val = o_full_yoy["YoY"].dropna().iloc[-1] if o_full_yoy["YoY"].notna().any() else None
    yoy_date = o_full_yoy.dropna(subset=["YoY"]).iloc[-1]["Date"] if o_full_yoy["YoY"].notna().any() else None

    mom_val = s_full_mom["MoM"].dropna().iloc[-1] if s_full_mom["MoM"].notna().any() else None
    mom_date = s_full_mom.dropna(subset=["MoM"]).iloc[-1]["Date"] if s_full_mom["MoM"].notna().any() else None

    # =========================
    # Defaults (state) - antes de widgets
    # =========================
    if "act_medida" not in st.session_state:
        st.session_state["act_medida"] = "Nivel desestacionalizado"

    if "act_vars" not in st.session_state:
        st.session_state["act_vars"] = ["EMAE - Nivel general", "IPI Manufacturero"]


    # =========================================================
    # Panel grande: TODO adentro de un container (como TASA)
    # =========================================================
    with st.container():

        # --- marker + JS PRIMERO en el container ---
        st.markdown("<span id='act_panel_marker'></span>", unsafe_allow_html=True)
        components.html(
            """
            <script>
            (function() {
              function applyPanelClass() {
                const marker = window.parent.document.getElementById('act_panel_marker');
                if (!marker) return;
                const block = marker.closest('div[data-testid="stVerticalBlock"]');
                if (block) block.classList.add('fx-panel-wrap');
              }

              applyPanelClass();

              let tries = 0;
              const t = setInterval(() => {
                applyPanelClass();
                tries += 1;
                if (tries >= 10) clearInterval(t);
              }, 150);

              const obs = new MutationObserver(() => applyPanelClass());
              obs.observe(window.parent.document.body, { childList: true, subtree: true });
              setTimeout(() => obs.disconnect(), 3000);
            })();
            </script>
            """,
            height=0,
        )

        # =========================
        # Header (igual que antes, solo cambia título)
        # =========================
        a_yoy, cls_yoy = _arrow_cls(yoy_val)
        a_mom, cls_mom = _arrow_cls(mom_val)

        header_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">📊</div>',
            '    <div class="fx-title">Estimador Mensual de Actividad Económica</div>',
            "  </div>",
            '  <div class="fx-card">',
            '    <div class="fx-row">',
            f'      <div class="fx-value">{_fmt_pct_es(yoy_val, 1)}%</div>' if yoy_val is not None else '      <div class="fx-value">—</div>',
            '      <div class="fx-meta">',
            f'        EMAE (original)<span class="sep">|</span>YoY<span class="sep">|</span>{_month_es(yoy_date)}',
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

        # =========================
        # Controles (debajo del header, como TASA)
        # =========================
        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("<div class='fx-panel-title'>Seleccioná la medida</div>", unsafe_allow_html=True)
            st.selectbox(
                "",
                ["Nivel desestacionalizado", "Variación mensual", "Variación anual"],
                key="act_medida",
                label_visibility="collapsed",
            )

        with c2:
            st.markdown("<div class='fx-panel-title'>Seleccioná la variable</div>", unsafe_allow_html=True)
            st.multiselect(
                "",
                options=[
                    "EMAE - Nivel general",
                    "IPI Manufacturero",
                    "IPI Minero",
                    "ISAC - Construcción",
                ],
                key="act_vars",
                label_visibility="collapsed",
            )

        # Guard: sin selección
        vars_sel = st.session_state.get("act_vars", [])
        if not vars_sel:
            st.warning("Seleccioná una variable.")
            return

        # =========================
        # Rango de fechas (MENSUAL)
        # (se arma según la medida elegida y las series seleccionadas)
        # =========================
        medida = st.session_state.get("act_medida", "Nivel desestacionalizado")

        date_mins = []
        date_maxs = []

        for vname in vars_sel:
            df_o, df_s = SERIES.get(vname, (pd.DataFrame(), pd.DataFrame()))

            if medida == "Variación anual":
                base = df_o
            else:
                base = df_s

            if base is not None and not base.empty and "Date" in base.columns:
                date_mins.append(pd.to_datetime(base["Date"].min()))
                date_maxs.append(pd.to_datetime(base["Date"].max()))

        # fallback seguro (por si alguna serie no está)
        if not date_mins or not date_maxs:
            date_mins = [pd.to_datetime(df_emae_s["Date"].min())]
            date_maxs = [pd.to_datetime(df_emae_s["Date"].max())]

        min_real = min(date_mins)
        max_real = max(date_maxs)

        months = pd.date_range(
            min_real.to_period("M").to_timestamp(),
            max_real.to_period("M").to_timestamp(),
            freq="MS",
        )
        months_d = [m.date() for m in months]

        DEFAULT_START = pd.Timestamp("2017-01-01").date()  # dic-21

        # si dic-21 está antes del mínimo disponible, cae al mínimo
        start_default = max(DEFAULT_START, months_d[0])
        end_default = months_d[-1]

        st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
        start_d, end_d = st.select_slider(
            "",
            options=months_d,
            value=(start_default, end_default),
            format_func=lambda d: pd.Timestamp(d).strftime("%b-%y"),
            label_visibility="collapsed",
            key="act_range",
        )


        start_ts = pd.Timestamp(start_d).to_period("M").to_timestamp()
        end_ts = pd.Timestamp(end_d).to_period("M").to_timestamp()

        # =========================
        # Plot
        # =========================
        fig = go.Figure()

        for vname in vars_sel:
            df_o, df_s = SERIES.get(vname, (pd.DataFrame(columns=["Date", "Value"]), pd.DataFrame(columns=["Date", "Value"])))

            if medida == "Nivel desestacionalizado":
                lvl = df_s[(df_s["Date"] >= start_ts) & (df_s["Date"] <= end_ts)].copy()
                if not lvl.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=lvl["Date"],
                            y=lvl["Value"],
                            mode="lines+markers",
                            name=f"{vname} (s.e.)",
                        )
                    )
                    fig.update_yaxes(title="Índice")

            elif medida == "Variación mensual":
                mom = MOM.get(vname, pd.DataFrame(columns=["Date", "MoM"]))
                mom = mom[(mom["Date"] >= start_ts) & (mom["Date"] <= end_ts)].copy()
                if not mom.empty:
                    fig.add_trace(
                        go.Bar(
                            x=mom["Date"],
                            y=mom["MoM"],
                            name=f"{vname} - mensual",
                        )
                    )
                    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#666666")
                    fig.update_yaxes(ticksuffix="%")

            elif medida == "Variación anual":
                yoy = YOY.get(vname, pd.DataFrame(columns=["Date", "YoY"]))
                yoy = yoy[(yoy["Date"] >= start_ts) & (yoy["Date"] <= end_ts)].copy()
                if not yoy.empty:
                    fig.add_trace(
                        go.Bar(
                            x=yoy["Date"],
                            y=yoy["YoY"],
                            name=f"{vname} - anual",
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
            key="chart_act",
        )

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
            "Fuente: INDEC vía datos.gob.ar (EMAE/ISAC/IPI manuf.) + INDEC (IPI minero, Excel)"
            "</div>",
            unsafe_allow_html=True,
        )

    # =========================================================
    # EMAE — Apertura por sectores (comparación A / B)
    # =========================================================

    from services.macro_data import get_emae_sectores_long

    st.divider()

    with st.container():
        # --- marker + JS para aplicar el mismo panel-wrap ---
        st.markdown("<span id='emae_sect_panel_marker'></span>", unsafe_allow_html=True)
        components.html(
            """
            <script>
            (function() {
            function applyPanelClass() {
                const marker = window.parent.document.getElementById('emae_sect_panel_marker');
                if (!marker) return;
                const block = marker.closest('div[data-testid="stVerticalBlock"]');
                if (block) block.classList.add('fx-panel-wrap');
            }
            applyPanelClass();
            let tries = 0;
            const t = setInterval(() => {
                applyPanelClass();
                tries += 1;
                if (tries >= 10) clearInterval(t);
            }, 150);
            const obs = new MutationObserver(() => applyPanelClass());
            obs.observe(window.parent.document.body, { childList: true, subtree: true });
            setTimeout(() => obs.disconnect(), 3000);
            })();
            </script>
            """,
            height=0,
        )

        # =========================
        # Header (solo título)
        # =========================
        header2_lines = [
            '<div class="fx-wrap">',
            '  <div class="fx-title-row">',
            '    <div class="fx-icon-badge">📊</div>',
            '    <div class="fx-title">Estimador Mensual de Actividad Económica por Sectores</div>',
            "  </div>",
            "</div>",
        ]
        st.markdown("\n".join(header2_lines), unsafe_allow_html=True)

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)


        # --- load data ---
        with st.spinner("Cargando EMAE por sectores..."):
            df_sec = get_emae_sectores_long()

        if df_sec is None or df_sec.empty:
            st.error("No pude cargar EMAE por sectores.")
        else:
            # Limpieza
            df_sec = df_sec.copy()
            df_sec["Date"] = pd.to_datetime(df_sec["Date"], errors="coerce")
            df_sec["Value"] = pd.to_numeric(df_sec["Value"], errors="coerce")
            df_sec = (
                df_sec.dropna(subset=["Date", "Sector", "Value"])
                    .sort_values(["Sector", "Date"])
                    .reset_index(drop=True)
            )

            # Último mes disponible (para mensual y para el acumulado ene–último mes)
            max_dt = pd.to_datetime(df_sec["Date"].max())
            last_month_num = int(max_dt.month)
            last_month_label = max_dt.strftime("%b").lower()

            years_all = sorted(df_sec["Date"].dt.year.unique().tolist(), reverse=True)

            def _pretty_sector(s: str) -> str:
                s = (s or "").strip()
                if not s:
                    return s
                fixes = {
                    "admin_publica_planes_seguridad_social_afiliacion_obligatoria": "Administración pública / planes / seguridad social",
                    "ensenianza": "Enseñanza",
                    "impuestos_netos_subsidios": "Impuestos netos de subsidios",
                    "comercio_mayorista_minorista_reparaciones": "Comercio mayorista/minorista y reparaciones",
                    "electricidad_gas_agua": "Electricidad, gas y agua",
                    "explotacion_minas_canteras": "Explotación de minas y canteras",
                    "otras_actividades_servicios_comunitarias_sociales_personales": "Otros servicios comunitarios, sociales y personales",
                    "servicios_sociales_salud": "Servicios sociales y salud",
                    "transporte_comunicaciones": "Transporte y comunicaciones",
                    "actividades_inmobiliarias_empresariales_alquiler": "Act. inmobiliarias, empresariales y alquiler",
                    "hoteles_restaurantes": "Hoteles y restaurantes",
                    "industria_manufacturera": "Industria manufacturera",
                    "agricultura_ganaderia_caza_silvicultura": "Agricultura, ganadería, caza y silvicultura",
                }
                if s in fixes:
                    return fixes[s]
                return s.replace("_", " ").capitalize()

            def _month_opt_label(dt: pd.Timestamp) -> str:
                return pd.to_datetime(dt).strftime("%b-%Y").lower()


            # =========================
            # Fila 1: selector modo (solo columna izquierda)
            # =========================

            # label dinámico del acumulado según último dato disponible
            acc_label = f"Acumulado (ene-{last_month_label})"

            MODE_LABELS = {
                "mensual": "Mensual",
                "acum": acc_label,
            }
            MODE_KEYS = list(MODE_LABELS.keys())  # ["mensual", "acum"]

            # default
            if "emae_sec_mode_key" not in st.session_state:
                st.session_state["emae_sec_mode_key"] = "acum"

            r1c1, r1c2 = st.columns(2, gap="large")

            with r1c1:
                st.markdown("<div class='fx-panel-title'>Tipo de comparación</div>", unsafe_allow_html=True)

                try:
                    _idx = MODE_KEYS.index(st.session_state["emae_sec_mode_key"])
                except Exception:
                    _idx = 1  # acum por defecto

                mode_key = st.selectbox(
                    "",
                    MODE_KEYS,
                    format_func=lambda k: MODE_LABELS.get(k, k),
                    key="emae_sec_mode_key",
                    label_visibility="collapsed",
                )

            with r1c2:
                st.markdown("&nbsp;", unsafe_allow_html=True)  # columna vacía

            mode = "Mensual" if mode_key == "mensual" else "Acumulado"


            # =========================
            # Fila 2: Período A / B
            # =========================
            colA, colB = st.columns(2, gap="large")

            if st.session_state.get("emae_sec_mode_key") == "acum":
                if "emae_sec_year_a" not in st.session_state:
                    st.session_state["emae_sec_year_a"] = years_all[0] if years_all else None
                if "emae_sec_year_b" not in st.session_state:
                    st.session_state["emae_sec_year_b"] = years_all[1] if len(years_all) > 1 else (years_all[0] if years_all else None)

                with colA:
                    st.markdown("<div class='fx-panel-title'>Período A</div>", unsafe_allow_html=True)
                    st.selectbox("", years_all, key="emae_sec_year_a", label_visibility="collapsed")

                with colB:
                    st.markdown("<div class='fx-panel-title'>Período B</div>", unsafe_allow_html=True)
                    st.selectbox("", years_all, key="emae_sec_year_b", label_visibility="collapsed")

                year_a = int(st.session_state.get("emae_sec_year_a"))
                year_b = int(st.session_state.get("emae_sec_year_b"))

                def _accum_avg_by_sector(year: int) -> pd.Series:
                    t = df_sec[df_sec["Date"].dt.year == year].copy()
                    t = t[t["Date"].dt.month <= last_month_num]
                    return t.groupby("Sector")["Value"].mean()

                A = _accum_avg_by_sector(year_a)
                B = _accum_avg_by_sector(year_b)

                subtitle = f"Comparación acumulada ene–{last_month_label} (promedio) · A={year_a} / B={year_b}"

            else:
                month_num = last_month_num

                possible_dates = []
                for y in years_all:
                    dt = pd.Timestamp(year=y, month=month_num, day=1)
                    if (df_sec["Date"] == dt).any():
                        possible_dates.append(dt)
                possible_dates = sorted(possible_dates, reverse=True)

                if "emae_sec_month_a" not in st.session_state:
                    st.session_state["emae_sec_month_a"] = possible_dates[0] if possible_dates else None
                if "emae_sec_month_b" not in st.session_state:
                    st.session_state["emae_sec_month_b"] = possible_dates[1] if len(possible_dates) > 1 else (possible_dates[0] if possible_dates else None)

                with colA:
                    st.markdown("<div class='fx-panel-title'>Período A</div>", unsafe_allow_html=True)
                    st.selectbox(
                        "",
                        possible_dates,
                        key="emae_sec_month_a",
                        format_func=_month_opt_label,
                        label_visibility="collapsed",
                    )

                with colB:
                    st.markdown("<div class='fx-panel-title'>Período B</div>", unsafe_allow_html=True)
                    st.selectbox(
                        "",
                        possible_dates,
                        key="emae_sec_month_b",
                        format_func=_month_opt_label,
                        label_visibility="collapsed",
                    )

                dt_a = pd.to_datetime(st.session_state.get("emae_sec_month_a"))
                dt_b = pd.to_datetime(st.session_state.get("emae_sec_month_b"))

                def _month_level_by_sector(dt: pd.Timestamp) -> pd.Series:
                    t = df_sec[df_sec["Date"] == dt].copy()
                    return t.groupby("Sector")["Value"].mean()

                A = _month_level_by_sector(dt_a)
                B = _month_level_by_sector(dt_b)

                subtitle = f"Comparación mensual ({max_dt.strftime('%b').lower()}) · A={_month_opt_label(dt_a)} / B={_month_opt_label(dt_b)}"

            # =========================
            # Armar %Δ = (A/B - 1) * 100
            # =========================
            common = pd.DataFrame({"A": A, "B": B}).dropna()
            common = common[(common["A"] > 0) & (common["B"] > 0)]

            if common.empty:
                st.warning("No hay datos suficientes para comparar esos períodos.")
            else:
                common["pct"] = (common["A"] / common["B"] - 1.0) * 100.0
                common = common.reset_index().rename(columns={"index": "Sector"})
                common["Sector_label"] = common["Sector"].apply(_pretty_sector)

                # Orden desc por variación (top = mejor)
                common = common.sort_values("pct", ascending=False).reset_index(drop=True)

                # =========================
                # Plot: barras horizontales divergentes
                # =========================
                x = common["pct"].values
                x_min = float(np.nanmin(x)) if len(x) else 0.0
                x_max = float(np.nanmax(x)) if len(x) else 0.0

                pad = 0.15 * max(abs(x_min), abs(x_max), 1e-6)

                x_left  = min(0.0, x_min) - pad
                x_right = max(0.0, x_max) + pad

                y_plain = common["Sector_label"].tolist()

                # Bold solo "Industria manufacturera"
                y = [
                    "<b>Industria manufacturera</b>" if s == "Industria manufacturera" else s
                    for s in y_plain
                ]

                # colores pastel: verde si +, rojo si -
                colors = np.where(x >= 0, "rgba(34,197,94,0.55)", "rgba(239,68,68,0.55)")

                fig2 = go.Figure()
                fig2.add_trace(
                    go.Bar(
                        x=x,
                        y=y,
                        orientation="h",
                        marker=dict(color=colors),
                        customdata=y_plain,
                        text=[f"{v:.1f}%" for v in x],
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

                fig2.update_yaxes(autorange="reversed")  # top=mayor

                st.markdown(f"<div class='fx-panel-title'>{subtitle}</div>", unsafe_allow_html=True)

                st.plotly_chart(
                    fig2,
                    use_container_width=True,
                    config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
                    key="chart_emae_sect_comp",
                )

                st.markdown(
                    "<div style='color:rgba(20,50,79,0.70); font-size:12px;'>"
                    "Fuente: SSPM / INDEC — EMAE apertura por sectores (índice base 2004)"
                    "</div>",
                    unsafe_allow_html=True,
                )
