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


def _is_nivel_general(label: str) -> bool:
    return str(label).strip().lower() == "nivel general"


def _clean_code(x) -> str:
    # limpia floats tipo "0.0" -> "0"
    s = str(x).strip()
    if s.endswith(".0") and s.replace(".0", "").isdigit():
        return s[:-2]
    return s


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa de inflación – % Nacional")
    st.divider()

    # --- CSS: selector más grande y legible ---
    st.markdown(
        """
        <style>
        div[data-baseweb="select"]{ max-width: 720px; }
        div[data-baseweb="select"] > div{
            background: rgba(17,24,39,0.94);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            min-height: 52px;
        }
        div[data-baseweb="select"] *{
            color: rgba(255,255,255,0.95) !important;
            font-weight: 650;
            font-size: 14px;
        }
        div[role="radiogroup"]{ gap: 8px !important; }
        div[role="radiogroup"] > label{
            border: 1px solid rgba(0,0,0,0.12);
            border-radius: 999px;
            padding: 6px 12px;
            background: rgba(255,255,255,0.9);
        }
        div[role="radiogroup"] span{
            font-size: 12px !important;
            font-weight: 700 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Datos (Nacional fijo)
    # =========================
    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    ipc["Codigo_str"] = ipc["Codigo"].apply(_clean_code).astype(str).str.strip()
    ipc["Descripcion"] = ipc["Descripcion"].astype(str).str.strip()
    ipc["Periodo"] = pd.to_datetime(ipc["Periodo"], errors="coerce")
    ipc = ipc.dropna(subset=["Periodo"]).sort_values("Periodo")

    # =========================
    # Selector DF (NUEVO) con tu regla:
    # - si Descripcion vacía -> usar Codigo
    # - B/S con mapping
    # =========================
    label_fix = {"B": "Bienes", "S": "Servicios"}

    sel = (
        ipc[["Codigo_str", "Descripcion"]]
        .drop_duplicates()
        .copy()
    )

    def _is_empty_desc(d: str) -> bool:
        ds = str(d).strip().lower()
        return (ds == "") or (ds == "nan") or (ds == "none")

    def build_label(code: str, desc: str) -> str:
        code = str(code).strip()

        # fuerza 0 como Nivel general (por las dudas)
        if code.isdigit() and int(code) == 0:
            return "Nivel general"

        # si hay descripción válida, usarla
        if not _is_empty_desc(desc):
            return str(desc).strip()

        # si descripción vacía, usar el código (con fix B/S)
        if code in label_fix:
            return label_fix[code]
        return code

    sel["Label"] = sel.apply(lambda r: build_label(r["Codigo_str"], r["Descripcion"]), axis=1)

    # ordenar: Nivel general primero
    sel["ord0"] = sel["Label"].apply(lambda x: 0 if _is_nivel_general(x) else 1)
    sel = sel.sort_values(["ord0", "Label"]).drop(columns=["ord0"])

    options = sel["Codigo_str"].tolist()
    code_to_label = dict(zip(sel["Codigo_str"], sel["Label"]))

    # default: Nivel general
    default_code = None
    for c, lab in code_to_label.items():
        if _is_nivel_general(lab):
            default_code = c
            break
    if default_code is None and options:
        default_code = options[0]

    selected = st.multiselect(
        "Seleccioná una o más divisiones",
        options=options,
        default=[default_code] if default_code else [],
        format_func=lambda c: code_to_label.get(c, c),
    )
    if not selected:
        st.info("Seleccioná al menos una división.")
        return

    # =========================
    # Frecuencia
    # =========================
    freq = st.radio(
        "Seleccioná la frecuencia",
        ["Mensual", "Anual"],
        horizontal=True,
        index=0,
    )

    if freq == "Mensual":
        y_col = "v_m_IPC"
        y_axis_label = "Variación mensual (%)"
        title_word = "inflación"
        kpi_suffix = "mensual"
    else:
        y_col = "v_i_a_IPC"
        y_axis_label = "Variación anual (%)"
        title_word = "inflación interanual"
        kpi_suffix = "anual"

    # =========================
    # Serie base (primera seleccionada)
    # =========================
    base_code = selected[0]
    base_label = code_to_label.get(base_code, base_code)

    base = ipc[ipc["Codigo_str"] == base_code].dropna(subset=[y_col]).sort_values("Periodo")
    if base.empty:
        st.warning("Sin datos para esa selección/frecuencia.")
        return

    last_period = pd.to_datetime(base["Periodo"].iloc[-1])
    last_value = float(base[y_col].iloc[-1])

    # =========================
    # Layout KPI + Gráfico
    # =========================
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    with c1:
        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1;">
              <span style="font-size:48px;">{_fmt_pct_es(last_value, 1)}%</span>
              <span style="font-size:20px; font-weight:700; margin-left:6px;">
                {_mmmyy_es(last_period)}
              </span>
            </div>
            <div style="margin-top:8px; font-size:18px; font-weight:800;">
              {kpi_suffix}
            </div>
            """,
            unsafe_allow_html=True,
        )

        out = ipc[ipc["Codigo_str"].isin(selected)].sort_values(["Codigo_str", "Periodo"])
        csv = out.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name="ipc_seleccion.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with c2:
        # Período arriba del gráfico
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "Todo"],
            horizontal=True,
            index=3,
            label_visibility="collapsed",
        )

        max_real = last_period
        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
            tick_freq = "MS"
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
            tick_freq = "2MS"
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
            tick_freq = "3MS"
        else:
            min_sel = ipc["Periodo"].min()
            tick_freq = "6MS"
        max_sel = max_real + pd.DateOffset(months=1)

        # Autoescala Y (por rango + selecciones)
        tmp = ipc[ipc["Codigo_str"].isin(selected)].dropna(subset=[y_col]).copy()
        tmp = tmp[(tmp["Periodo"] >= min_sel) & (tmp["Periodo"] <= max_real)]
        if tmp.empty:
            st.warning("No hay datos en el período seleccionado.")
            return

        ymin = float(tmp[y_col].min())
        ymax = float(tmp[y_col].max())
        pad = max(0.8, (ymax - ymin) * 0.10)
        y_range = [ymin - pad, ymax + pad]

        tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq=tick_freq)
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq="MS")
        ticktext = [f"{_mes_es(d.month)}-{str(d.year)[-2:]}" for d in tickvals]

        title_txt = (
            f"La {title_word} de {base_label} de {_mmmyy_es(last_period)} fue "
            f"{_fmt_pct_es(last_value, 1)}%"
        )

        fig = go.Figure()
        for c in selected:
            s = ipc[ipc["Codigo_str"] == c].dropna(subset=[y_col]).copy()
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)].sort_values("Periodo")
            if s.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s[y_col],
                    name=code_to_label.get(c, c),
                    mode="lines+markers",
                    marker=dict(size=5),
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        fig.update_layout(
            hovermode="x unified",
            height=520,
            margin=dict(l=10, r=20, t=60, b=70),
            title=dict(text=title_txt, x=0, xanchor="left"),
            showlegend=len(selected) > 1,
        )
        if len(selected) > 1:
            fig.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0)
            )

        fig.update_yaxes(
            title_text=y_axis_label,
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

    
    # ============================================================
    # CUADRO – Variaciones mensuales por año (IPC Nacional)
    # ============================================================
    st.markdown("### 📋 Variaciones mensuales por año")
    st.caption("Variación mensual del IPC (%). Cobertura nacional – INDEC")
    
    # ----------------------------
    # Dataset base (mensual)
    # ----------------------------
    tab = ipc.dropna(subset=["Periodo", "v_m_IPC"]).copy()
    tab["Year"] = tab["Periodo"].dt.year
    tab["Month"] = tab["Periodo"].dt.month
    
    # ----------------------------
    # Selector de año (completo)
    # ----------------------------
    years = sorted(tab["Year"].dropna().unique(), reverse=True)
    if not years:
        st.info("No hay datos suficientes para armar la tabla.")
    else:
        selected_year = st.selectbox(
            "Seleccioná el año",
            years,
            index=0,
            key="ipc_year_table",
        )
    
        tab = tab[tab["Year"] == selected_year].copy()
    
        # ----------------------------
        # Label unificado (misma lógica del selector)
        # ----------------------------
        label_fix = {"B": "Bienes", "S": "Servicios"}
    
        def _is_empty_desc(d):
            d = str(d).strip().lower()
            return d in ["", "nan", "none"]
    
        def build_label(code, desc):
            code = str(code).strip()
    
            if code.isdigit() and int(code) == 0:
                return "Nivel general"
    
            if not _is_empty_desc(desc):
                return desc
    
            if code in label_fix:
                return label_fix[code]
    
            return code
    
        tab["Label"] = tab.apply(
            lambda r: build_label(r["Codigo_str"], r["Descripcion"]),
            axis=1
        )
    
        # ----------------------------
        # Pivot mensual (ene–dic)
        # ----------------------------
        piv = (
            tab.pivot_table(
                index="Label",
                columns="Month",
                values="v_m_IPC",
                aggfunc="last",
            )
            .reindex(columns=range(1, 13))
        )
    
        month_map = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        piv.columns = [month_map[m] for m in piv.columns]
    
        # ----------------------------
        # Orden de filas
        # ----------------------------
        categorias = {"Bienes", "Servicios", "Núcleo", "Regulados", "Estacional"}
    
        def sort_key(x):
            if x.lower() == "nivel general":
                return (0, x)
            if x in categorias:
                return (1, x)
            return (2, x)
    
        piv = piv.loc[sorted(piv.index, key=sort_key)]
    
        # ----------------------------
        # Formato %
        # ----------------------------
        def fmt(v):
            if pd.isna(v):
                return "-"
            return f"{v:.1f}%".replace(".", ",")
    
        piv_fmt = piv.applymap(fmt)
    
        # ----------------------------
        # Estilo visual
        # ----------------------------
        def style_rows(df):
            styles = []
            for idx in df.index:
                if idx.lower() == "nivel general":
                    styles.append(
                        ["font-weight:800; background-color:rgba(17,24,39,0.06)"] * df.shape[1]
                    )
                elif idx in categorias:
                    styles.append(
                        ["font-weight:800; background-color:rgba(17,24,39,0.10)"] * df.shape[1]
                    )
                else:
                    styles.append([""] * df.shape[1])
            return pd.DataFrame(styles, index=df.index, columns=df.columns)
    
        st.dataframe(
            piv_fmt.style.apply(style_rows, axis=None),
            use_container_width=True,
            height=520,
        )
