import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import textwrap
import streamlit.components.v1 as components

from services.metrics import calc_var, fmt, obtener_nombre_mes
from services.comex_data import fetch_ica

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fmt_mes_es(d):
    ts = pd.Timestamp(d)
    return f"{MESES_ES[ts.month - 1]}-{str(ts.year)[-2:]}"


def fmt_es(x, dec=1):
    if pd.isna(x):
        return "s/d"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_comex(go_to):
    # =========================
    # Botón volver
    # =========================
    if st.button("← Volver"):
        go_to("home")

    # =========================
    # CSS (header + panel grande + composición PRO en grilla 4 col)
    # =========================
    st.markdown(
        """
        <style>
        /* ===================== HEADER COMEX ===================== */
        .com-wrap{
          background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
          border: 1px solid #dfeaf6;
          border-radius: 22px;
          padding: 14px;
          box-shadow: 0 10px 24px rgba(15, 55, 100, 0.16),
                      inset 0 0 0 1px rgba(255,255,255,0.55);
          margin-top: 8px;
        }
        .com-title-row{
          display:flex; align-items:center; justify-content:space-between;
          gap:12px; margin-bottom: 10px; padding-left: 4px;
        }
        .com-title-left{ display:flex; align-items:center; gap:12px; }
        .com-icon-badge{
          width: 64px; height: 52px; border-radius: 14px;
          background: linear-gradient(180deg, #e7eef6 0%, #dfe7f1 100%);
          border: 1px solid rgba(15,23,42,0.10);
          display:flex; align-items:center; justify-content:center;
          box-shadow: 0 8px 14px rgba(15,55,100,0.12);
          font-size: 30px; flex: 0 0 auto;
        }
        .com-title{
          font-size: 23px; font-weight: 900; letter-spacing: -0.01em;
          color: #14324f; margin: 0; line-height: 1.0;
        }
        .com-subtitle{
          font-size: 14px; font-weight: 800;
          color: rgba(20,50,79,0.78); margin-top: 2px;
        }
        .com-card{
          background: rgba(255,255,255,0.94);
          border: 1px solid rgba(15, 23, 42, 0.10);
          border-radius: 18px;
          padding: 14px 14px 12px 14px;
          box-shadow: 0 10px 18px rgba(15, 55, 100, 0.10);
        }
        .com-kpi-grid{
          display:grid;
          grid-template-columns: 1fr 1fr 1fr;
          gap: 26px;
          align-items: start;
          margin-top: 4px;
        }
        .com-meta{
          font-size: 16px;
          color: #2b4660;
          font-weight: 800;
          margin-bottom: 6px;
        }
        .com-value{
          font-size: 44px;
          font-weight: 950;
          letter-spacing: -0.02em;
          color: #14324f;
          line-height: 0.95;
        }
        .com-badge{
          display:inline-flex;
          align-items:center;
          justify-content:center;
          padding: 6px 12px;
          border-radius: 999px;
          border: 1px solid rgba(15,23,42,0.10);
          font-size: 14px;
          font-weight: 800;
          margin-top: 8px;
          width: fit-content;
        }
        .com-badge.red{ background: rgba(220,38,38,0.07); }
        .com-badge.green{ background: rgba(22,163,74,0.08); }
        @media (max-width: 900px){
          .com-kpi-grid{ grid-template-columns: 1fr; gap: 14px; }
        }

        /* Título estilo macro_fx */
        .fx-panel-title{
          font-size: 12px;
          font-weight: 900;
          color: rgba(20,50,79,0.78);
          margin: 0 0 6px 2px;
          letter-spacing: 0.01em;
        }

        /* ================= PANEL GRANDE COMEX (igual a macro_fx) ================= */
        .com-panel-wrap{
          background: rgba(230, 243, 255, 0.55);
          border: 1px solid rgba(15, 55, 100, 0.10);
          border-radius: 22px;
          padding: 16px 16px 26px 16px;
          box-shadow: 0 10px 18px rgba(15,55,100,0.06);
          margin-top: 10px;
        }

        .com-panel-wrap div[data-testid="stSelectbox"],
        .com-panel-wrap div[data-testid="stMultiSelect"],
        .com-panel-wrap div[data-testid="stSlider"],
        .com-panel-wrap div[data-testid="stPlotlyChart"],
        .com-panel-wrap div[data-testid="stDownloadButton"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          margin: 0 !important;
        }

        /* ================= COMPOSICIÓN PRO (GRILLA 4 COL) ================= */
        .com-comp-panel{
          background: rgba(230, 243, 255, 0.35);
          border: 1px solid rgba(15, 55, 100, 0.10);
          border-radius: 22px;
          padding: 16px 16px 18px 16px;
          box-shadow: 0 10px 18px rgba(15,55,100,0.05);
          margin-top: 14px;
        }

        .com-comp-title{
          font-weight: 950;
          font-size: 16px;
          color: #14324f;
          margin: 0 0 6px 2px;
        }
        .com-comp-subtitle{
          font-size: 12px;
          font-weight: 800;
          color: rgba(20,50,79,0.70);
          margin: 0 0 14px 2px;
        }

        .com-comp-head{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
          margin-bottom: 10px;
          padding: 0 2px;
        }
        .com-comp-hlab{
          font-size: 12px;
          font-weight: 950;
          color: rgba(20,50,79,0.82);
          letter-spacing: 0.01em;
        }

        .com-comp-body{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
        align-items: start;
        }

        .com-comp-col{
        display: grid;
        grid-template-columns: 1fr 1fr; /* 2 cards por fila */
        gap: 16px;
        }

        @media (max-width: 1100px){
        .com-comp-body{ grid-template-columns: 1fr; }
        .com-comp-col{ grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 700px){
        .com-comp-col{ grid-template-columns: 1fr; }
        }

        /* Card */
        .ipi-card{
          background: rgba(255,255,255,0.96);
          border: 1px solid rgba(15, 23, 42, 0.10);
          border-radius: 16px;
          padding: 14px 14px 12px 14px;
          box-shadow: 0 10px 18px rgba(15,55,100,0.08);
          min-height: 112px;
        }
        .ipi-title{
          font-weight: 950;
          font-size: 15px;
          color:#0f2a43;
          margin-bottom: 12px;
          line-height: 1.15;
        }
        .ipi-row{
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:12px;
        }
        .ipi-metric{
          display:flex;
          gap:10px;
          align-items:center;
        }
        .ipi-label{
          font-size: 14px;
          font-weight: 900;
          color:#526484;
          letter-spacing: 0.01em;
        }
        .ipi-badge{
          width:56px;
          height:56px;
          border-radius:999px;
          display:flex;
          align-items:center;
          justify-content:center;
          font-weight: 950;
          font-size: 15px;
          border: 1px solid transparent;
          white-space:nowrap;
        }
        .ipi-up{
          background: rgba(22,163,74,.12);
          color: rgb(22,163,74);
          border-color: rgba(22,163,74,.25);
        }
        .ipi-down{
          background: rgba(220,38,38,.12);
          color: rgb(220,38,38);
          border-color: rgba(220,38,38,.25);
        }
        .ipi-neutral{
          background: rgba(100,116,139,.12);
          color: rgb(100,116,139);
          border-color: rgba(100,116,139,.22);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Data
    # =========================
    with st.spinner("Cargando ICA (INDEC)..."):
        df = fetch_ica()

    if df is None or df.empty or "fecha" not in df.columns:
        st.error("No se pudieron cargar los datos de ICA.")
        return

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).sort_values("fecha")

    ult_f = df["fecha"].iloc[-1]
    mes_txt = obtener_nombre_mes(ult_f)

    def _cls(x):
        return "green" if (x is not None and not pd.isna(x) and x >= 0) else "red"

    def _arrow(x):
        return "▲" if (x is not None and not pd.isna(x) and x >= 0) else "▼"

    expo = df.get("expo_total")
    impo = df.get("impo_total")
    saldo = df.get("saldo")

    expo_i = calc_var(expo, 12) if expo is not None else np.nan
    impo_i = calc_var(impo, 12) if impo is not None else np.nan
    saldo_di = (saldo.diff(12).iloc[-1]) if saldo is not None else np.nan

    expo_last = expo.iloc[-1] if expo is not None else np.nan
    impo_last = impo.iloc[-1] if impo is not None else np.nan
    saldo_last = saldo.iloc[-1] if saldo is not None else np.nan

    # =========================
    # Header KPI
    # =========================
    st.markdown(
        f"""
        <div class="com-wrap">
          <div class="com-title-row">
            <div class="com-title-left">
              <div class="com-icon-badge">🚢</div>
              <div>
                <div class="com-title">Comercio Exterior — ICA (INDEC) · {mes_txt}</div>
                <div class="com-subtitle">Millones de USD · Exportaciones, Importaciones y Saldo</div>
              </div>
            </div>
          </div>

          <div class="com-card">
            <div class="com-kpi-grid">

        <div>
        <div class="com-meta">Exportaciones</div>
                <div class="com-value">{fmt_es(expo_last,0)}</div>
                <div class="com-badge {_cls(expo_i)}">{_arrow(expo_i)}{fmt_es(expo_i,1)}% interanual</div>
        </div>

        <div>
                <div class="com-meta">Importaciones</div>
                <div class="com-value">{fmt_es(impo_last,0)}</div>
                <div class="com-badge {_cls(impo_i)}">{_arrow(impo_i)}{fmt_es(impo_i,1)}% interanual</div>
        </div>

        <div>
                <div class="com-meta">Saldo comercial</div>
                <div class="com-value">{fmt_es(saldo_last,0)}</div>
                <div class="com-badge {_cls(saldo_di)}">{_arrow(saldo_di)}USD {fmt_es(saldo_di,0)}</div>
        </div>

        </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # PANEL GRANDE (marker + JS)
    # =========================
    st.markdown("<span id='com_panel_marker'></span>", unsafe_allow_html=True)
    components.html(
        """
        <script>
        (function() {
          function applyComPanelClass() {
            const marker = window.parent.document.getElementById('com_panel_marker');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('com-panel-wrap');
          }
          applyComPanelClass();
          let tries = 0;
          const t = setInterval(() => {
            applyComPanelClass();
            tries += 1;
            if (tries >= 10) clearInterval(t);
          }, 150);
          const obs = new MutationObserver(() => applyComPanelClass());
          obs.observe(window.parent.document.body, { childList: true, subtree: true });
          setTimeout(() => obs.disconnect(), 2500);
        })();
        </script>
        """,
        height=0,
    )

    # =========================
    # Selector rango
    # =========================
    max_real = pd.to_datetime(df["fecha"].max())
    min_real = pd.to_datetime(df["fecha"].min())

    months = pd.date_range(
        min_real.to_period("M").to_timestamp(),
        max_real.to_period("M").to_timestamp(),
        freq="MS",
    )
    months_d = [m.date() for m in months]

    end_idx = len(months_d) - 1
    start_idx = max(0, end_idx - 12)
    default_value = (months_d[start_idx], months_d[end_idx])

    st.markdown("<div class='fx-panel-title'>Rango de fechas</div>", unsafe_allow_html=True)
    start_d, end_d = st.select_slider(
        "",
        options=months_d,
        value=default_value,
        format_func=fmt_mes_es,
        label_visibility="collapsed",
        key="comex_range",
    )

    start_ts = pd.Timestamp(start_d).to_period("M").to_timestamp()
    end_ts = pd.Timestamp(end_d).to_period("M").to_timestamp()
    dff = df[(df["fecha"] >= start_ts) & (df["fecha"] <= end_ts)].copy()

    # =========================
    # Gráfico principal
    # =========================
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dff["fecha"], y=dff["expo_total"], name="Exportaciones", mode="lines"))
    fig.add_trace(go.Scatter(x=dff["fecha"], y=dff["impo_total"], name="Importaciones", mode="lines"))
    fig.add_trace(go.Bar(x=dff["fecha"], y=dff["saldo"], name="Saldo", opacity=0.35, yaxis="y2"))

    fig.update_layout(
        template="plotly_white",
        height=520,
        hovermode="x",
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        yaxis=dict(title="Millones USD"),
        yaxis2=dict(title="Saldo (Millones USD)", overlaying="y", side="right", showgrid=False),
        dragmode=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
    )

    export_cols = ["fecha", "expo_total", "impo_total", "saldo"]
    export_cols = [c for c in export_cols if c in dff.columns]
    export_df = dff[export_cols].copy().rename(columns={"fecha": "date"})
    st.download_button(
        "⬇️ Descargar CSV",
        export_df.to_csv(index=False).encode("utf-8"),
        file_name="comex_ica.csv",
        mime="text/csv",
        use_container_width=False,
        key="dl_comex_csv",
    )

    st.markdown(
        "<div style='color:rgba(20,50,79,0.70); font-size:12px; margin-top:10px;'>"
        "Fuente: INDEC — Intercambio Comercial Argentino (ICA)."
        "</div>",
        unsafe_allow_html=True,
    )

    # =========================
    # COMPOSICIÓN (FIX FINAL)
    # =========================

    df_comp = df.copy()

    def _dot_class(x: float) -> str:
            if x is None or pd.isna(x) or abs(float(x)) < 1e-12:
                return "ipi-neutral"
            return "ipi-up" if float(x) > 0 else "ipi-down"

    def _fmt_pct_es_local(x: float, dec: int = 1) -> str:
            if x is None or pd.isna(x):
                return "s/d"
            return f"{float(x):.{dec}f}%".replace(".", ",")

    def _calc_ytd_pct(df_, col):
            if col not in df_.columns:
                return np.nan
            last = df_["fecha"].iloc[-1]
            y = last.year
            m = last.month
            cur = df_[(df_["fecha"].dt.year == y) & (df_["fecha"].dt.month <= m)][col].sum()
            prev = df_[(df_["fecha"].dt.year == y-1) & (df_["fecha"].dt.month <= m)][col].sum()
            if prev == 0:
                return np.nan
            return (cur/prev - 1) * 100

    def _card(title, yoy, ytd):
            return f"""
        <div class="ipi-card">
                <div class="ipi-title">{title}</div>
                <div class="ipi-row">
                    <div class="ipi-metric">
                        <div class="ipi-badge {_dot_class(yoy)}">{_fmt_pct_es_local(yoy)}</div>
                        <div class="ipi-label">Interanual</div>
        </div>
        <div class="ipi-metric">
                        <div class="ipi-badge {_dot_class(ytd)}">{_fmt_pct_es_local(ytd)}</div>
                        <div class="ipi-label">Acumulada</div>
            </div>
            </div>
            </div>
            """

    exp_rows = [
            ("Productos primarios (PP)", "expo_pp"),
            ("MOA", "expo_moa"),
            ("MOI", "expo_moi"),
            ("Combustibles y energía (CyE)", "expo_cye"),
        ]

    imp_rows = [
            ("Bienes de capital (BK)", "impo_bk"),
            ("Bienes intermedios (BI)", "impo_bi"),
            ("Combustibles y lubricantes (CL)", "impo_cl"),
            ("Piezas y accesorios p/ BK", "impo_pabc"),
            ("Bienes de consumo (BC)", "impo_bc"),
            ("Vehículos automotores pasajeros (VAP)", "impo_vap"),
            ("Resto", "impo_resto"),
        ]

    # =========================================================
    # COMPOSICIÓN (DISEÑO: ETIQUETAS DEBAJO DEL CÍRCULO)
    # =========================================================
    
    # Definición de datos para asegurar el scope
    exp_rows = [
        ("Productos primarios (PP)", "expo_pp"),
        ("MOA", "expo_moa"),
        ("MOI", "expo_moi"),
        ("Combustibles y energía (CyE)", "expo_cye"),
    ]

    imp_rows = [
        ("Bienes de capital (BK)", "impo_bk"),
        ("Bienes intermedios (BI)", "impo_bi"),
        ("Combustibles y lubricantes (CL)", "impo_cl"),
        ("Piezas y accesorios p/ BK", "impo_pabc"),
        ("Bienes de consumo (BC)", "impo_bc"),
        ("Vehículos automotores pasajeros (VAP)", "impo_vap"),
        ("Resto", "impo_resto"),
    ]

    def _local_fmt_pct(x):
        if x is None or pd.isna(x):
            return "s/d"
        return f"{float(x):.1f}%".replace(".", ",")

    def _get_circle_style(val):
        if val is None or pd.isna(val):
            return "background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;"
        if val >= 0:
            return "background: rgba(22, 163, 74, 0.1); color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.2);"
        return "background: rgba(220, 38, 38, 0.1); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.2);"

    def _card_pro_vertical_label(title, yoy, ytd):
        return f"""
        <div style="
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            min-height: 140px;
        ">
            <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 16px; min-height: 34px; line-height: 1.2;">
                {title}
            </div>
            <div style="display: flex; gap: 24px; justify-content: flex-start; align-items: flex-start;">
                
        <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                    <div style="{_get_circle_style(yoy)} width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 13px;">
                        {_local_fmt_pct(yoy)}
        </div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; text-align: center;">Interanual</div>
        </div>

        <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
        <div style="{_get_circle_style(ytd)} width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 13px;">
                        {_local_fmt_pct(ytd)}
        </div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; text-align: center;">Acumulada</div>
        </div>
        </div>
        </div>
        """

    # Renderizado en Streamlit
    st.markdown("---")
    st.subheader("📦 Desglose por Rubros y Usos")

    df_comp = df.copy() 
    col_exp, col_imp = st.columns([1, 1.8])

    with col_exp:
        st.markdown("<p style='font-weight:700; color:#475569; margin-bottom:12px;'>EXPORTACIONES</p>", unsafe_allow_html=True)
        e1, e2 = st.columns(2)
        for i, (label, key) in enumerate(exp_rows):
            if key in df_comp.columns:
                yoy = calc_var(df_comp[key], 12)
                ytd = _calc_ytd_pct(df_comp, key) # Asegúrate que esta función exista en tu services.metrics
                target = e1 if i % 2 == 0 else e2
                target.markdown(_card_pro_vertical_label(label, yoy, ytd), unsafe_allow_html=True)

    with col_imp:
        st.markdown("<p style='font-weight:700; color:#475569; margin-bottom:12px;'>IMPORTACIONES</p>", unsafe_allow_html=True)
        i1, i2, i3 = st.columns(3)
        for i, (label, key) in enumerate(imp_rows):
            if key in df_comp.columns:
                yoy = calc_var(df_comp[key], 12)
                ytd = _calc_ytd_pct(df_comp, key)
                if i % 3 == 0: target = i1
                elif i % 3 == 1: target = i2
                else: target = i3
                target.markdown(_card_pro_vertical_label(label, yoy, ytd), unsafe_allow_html=True)