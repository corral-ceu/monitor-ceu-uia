import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _mes_es(m: int) -> str:
    return {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
    }[m]


def _mmmyy_es(dt) -> str:
    dt = pd.to_datetime(dt)
    return f"{_mes_es(dt.month)}-{str(dt.year)[-2:]}"


def _find_nivel_general(opts):
    # match exacto case-insensitive
    for o in opts:
        if str(o).strip().lower() == "nivel general":
            return o
    # fallback: contiene "nivel general"
    for o in opts:
        if "nivel general" in str(o).strip().lower():
            return o
    return None


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa mensual de inflación - % Nacional")
    st.divider()

    # --- CSS: multiselect angosto + chips período (pill) ---
    st.markdown(
        """
        <style>
        /* Multiselect más angosto y más visible */
        div[data-baseweb="select"]{
            max-width: 560px;
        }
        div[data-baseweb="select"] > div{
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(0,0,0,0.10);
            border-radius: 10px;
        }

        /* Chips 6M/1A/2A/Todo estilo “pill” */
        div[role="radiogroup"]{
            gap: 8px !important;
        }
        div[role="radiogroup"] > label{
            border: 1px solid rgba(0,0,0,0.12);
            border-radius: 999px;
            padding: 6px 12px;
            background: rgba(255,255,255,0.9);
        }
        div[role="radiogroup"] > label:hover{
            border-color: rgba(0,0,0,0.22);
        }
        div[role="radiogroup"] span{
            font-size: 12px !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    # Opciones de divisiones
    opciones = sorted(ipc["Descripcion"].dropna().unique())
    ng_opt = _find_nivel_general(opciones)

    # default sugerido: nivel general si existe, sino primera
    default = [ng_opt] if ng_opt is not None else ([opciones[0]] if opciones else [])

    descs = st.multiselect(
        "Seleccioná una o más divisiones",
        options=opciones,
        default=default,
    )
    if not descs:
        st.info("Seleccioná al menos una división.")
        return

    # selector de período (chips)
    rango = st.radio(
        "Período",
        ["6M", "1A", "2A", "Todo"],
        horizontal=True,
        index=3,
        label_visibility="collapsed",
    )

    # --- Serie base: PRIMERA seleccionada ---
    base_desc = descs[0]
    base = ipc[ipc["Descripcion"] == base_desc].dropna(subset=["v_m_IPC"]).copy()
    base = base.sort_values("Periodo")
    if base.empty:
        st.warning("Sin serie para esa división.")
        return

    base_last_period = pd.to_datetime(base["Periodo"].iloc[-1])
    base_last_vm = float(base["v_m_IPC"].iloc[-1])
    base_last_yoy = float(base["v_i_a_IPC"].iloc[-1]) if pd.notna(base["v_i_a_IPC"].iloc[-1]) else None

    # --- Rango de fechas según período ---
    max_real = pd.to_datetime(base_last_period)
    if rango == "6M":
        min_sel = max_real - pd.DateOffset(months=6)
        tick_freq = "MS"    # mensual
    elif rango == "1A":
        min_sel = max_real - pd.DateOffset(years=1)
        tick_freq = "2MS"   # cada 2 meses
    elif rango == "2A":
        min_sel = max_real - pd.DateOffset(years=2)
        tick_freq = "3MS"   # cada 3 meses
    else:
        min_sel = pd.to_datetime(ipc["Periodo"].min())
        tick_freq = "6MS"   # cada 6 meses

    # aire a la derecha (1 mes)
    max_sel = max_real + pd.DateOffset(months=1)

    # ----------------------------
    # Layout KPI + Gráfico
    # ----------------------------
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    with c1:
        # KPI mensual: “3,1% dic-25” (dic-25 más chico)
        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1.0;">
              <span style="font-size:48px;">{_fmt_pct_es(base_last_vm, 1)}%</span>
              <span style="font-size:20px; font-weight:700; color:#111827; margin-left:6px;">
                {_mmmyy_es(base_last_period)}
              </span>
            </div>
            <div style="margin-top:10px; font-size:22px; font-weight:800;">
              {_fmt_pct_es(base_last_yoy, 1) if base_last_yoy is not None else "-"}% anual
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # CSV de las divisiones seleccionadas
        out = ipc[ipc["Descripcion"].isin(descs)].copy()
        out = out[out["Region"] == "Nacional"].sort_values(["Descripcion", "Periodo"])
        csv = out.to_csv(index=False, sep=";", decimal=",").encode("utf-8")

        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name="ipc_divisiones.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with c2:
        # Título: siempre usa la PRIMERA seleccionada
        title_txt = (
            f"La inflación de {base_desc} de {_mmmyy_es(base_last_period)} fue "
            f"{_fmt_pct_es(base_last_vm, 1)}%"
        )

        # Datos del período seleccionado para autoescala Y
        tmp = ipc[ipc["Descripcion"].isin(descs)].dropna(subset=["v_m_IPC"]).copy()
        tmp = tmp[(tmp["Periodo"] >= min_sel) & (tmp["Periodo"] <= max_real)]
        if tmp.empty:
            st.warning("No hay datos en el período seleccionado.")
            return

        ymin = float(tmp["v_m_IPC"].min())
        ymax = float(tmp["v_m_IPC"].max())
        pad = max(0.8, (ymax - ymin) * 0.10)
        y_range = [ymin - pad, ymax + pad]

        # ticks X en español, densidad según período
        tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq=tick_freq)
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq="MS")
        ticktext = [f"{_mes_es(d.month)}-{str(d.year)[-2:]}" for d in tickvals]

        fig = go.Figure()

        for d in descs:
            s = ipc[(ipc["Descripcion"] == d)].dropna(subset=["v_m_IPC"]).copy()
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)].sort_values("Periodo")
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s["v_m_IPC"],
                    name=d,
                    mode="lines+markers",
                    marker=dict(size=4),
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        show_legend = len(descs) > 1

        fig.update_layout(
            hovermode="x unified",
            height=520,
            margin=dict(l=10, r=20, t=60, b=70),
            title=dict(text=title_txt, x=0, xanchor="left"),
            showlegend=show_legend,
        )

        if show_legend:
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1.0,
                )
            )

        fig.update_yaxes(
            title_text="Variación mensual (%)",
            ticksuffix="%",
            range=y_range,
            fixedrange=False,
        )

        fig.update_xaxes(
            title_text="",
            range=[min_sel, max_sel],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            fixedrange=False,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: INDEC")

    # ----------------------------
    # Tabla interactiva (abajo)
    # - Primera fila: Nivel general (si existe)
    # - Luego resto alfabético
    # - Columnas: últimos 12 meses (mmm-yy) con variación mensual
    # ----------------------------
    st.markdown("#### Tabla de variaciones mensuales (últimos 12 meses)")

    tab = ipc.dropna(subset=["Periodo", "Descripcion", "v_m_IPC"]).copy()
    tab["Periodo"] = pd.to_datetime(tab["Periodo"], errors="coerce")
    tab = tab.dropna(subset=["Periodo"])

    # últimos 12 meses disponibles
    last_period = tab["Periodo"].max()
    months = pd.period_range(last_period.to_period("M") - 11, last_period.to_period("M"), freq="M")
    month_dates = [p.to_timestamp("M") for p in months]
    col_labels = [_mmmyy_es(d) for d in month_dates]

    # pivot: filas = Descripcion, cols = Periodo, values = v_m_IPC
    piv = (
        tab[tab["Periodo"].dt.to_period("M").isin(months)]
        .assign(Period=lambda x: x["Periodo"].dt.to_period("M"))
        .pivot_table(index="Descripcion", columns="Period", values="v_m_IPC", aggfunc="last")
    )

    # reindex columnas en orden cronológico y renombrar a mmm-yy
    piv = piv.reindex(columns=months)
    piv.columns = col_labels

    # ordenar filas: Nivel general primero si existe
    idx = list(piv.index)
    ng_name = _find_nivel_general(idx)
    others = sorted([x for x in idx if x != ng_name], key=lambda z: str(z))
    ordered = ([ng_name] if ng_name is not None else []) + others
    piv = piv.reindex(ordered)

    # formateo a string con coma y %
    def _fmt_cell(v):
        if pd.isna(v):
            return "-"
        return f"{_fmt_pct_es(float(v), 1)}%"

    piv_fmt = piv.applymap(_fmt_cell)

    st.dataframe(piv_fmt, use_container_width=True)
