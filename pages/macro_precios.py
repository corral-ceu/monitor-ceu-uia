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


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa de inflación - % Nacional")
    st.divider()

    # --- CSS: selector más grande + contraste + pills ---
    st.markdown(
        """
        <style>
        /* Multiselect: más grande + fondo oscuro + texto claro */
        div[data-baseweb="select"]{
            max-width: 720px;
        }
        div[data-baseweb="select"] > div{
            background: rgba(17,24,39,0.94);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            min-height: 52px;
        }
        div[data-baseweb="select"] *{
            color: rgba(255,255,255,0.92) !important;
            font-weight: 650;
            font-size: 14px;
        }

        /* Chips */
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

    # =========================
    # Datos base
    # =========================
    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    # Normalizaciones
    ipc["Codigo_str"] = ipc["Codigo"].astype(str).str.strip()
    ipc["Descripcion"] = ipc["Descripcion"].astype(str).str.strip()
    ipc["Clasificador"] = ipc["Clasificador"].astype(str).str.strip()
    ipc["Periodo"] = pd.to_datetime(ipc["Periodo"], errors="coerce")
    ipc = ipc.dropna(subset=["Periodo"]).sort_values("Periodo")

    # =========================
    # Selector: Divisiones + Categorías
    # - key: identificador del selector (string)
    # - label: lo que se muestra
    # - kind: "division" / "categoria"
    # - Para divisiones: key = Codigo_str
    # - Para categorías: key = "CAT::<Descripcion>"
    # =========================
    label_fix = {"B": "Bienes", "S": "Servicios"}

    divs = (
        ipc[ipc["Clasificador"].str.lower() == "divisiones"]
        [["Codigo_str", "Descripcion"]]
        .drop_duplicates()
        .rename(columns={"Codigo_str": "key", "Descripcion": "label"})
    )
    divs["kind"] = "division"

    cats = (
        ipc[ipc["Clasificador"].str.lower() == "categorias"]
        [["Descripcion"]]
        .drop_duplicates()
        .rename(columns={"Descripcion": "raw"})
    )
    cats["raw"] = cats["raw"].astype(str).str.strip()
    cats["label"] = cats["raw"].replace(label_fix)
    cats["key"] = "CAT::" + cats["raw"]
    cats["kind"] = "categoria"
    cats = cats[["key", "label", "kind"]]

    selector_df = pd.concat([divs[["key", "label", "kind"]], cats], ignore_index=True)

    # ordenar: Nivel general primero, luego alfabético
    selector_df["__ord0"] = selector_df["label"].apply(lambda x: 0 if _is_nivel_general(x) else 1)
    selector_df["__ord1"] = selector_df["label"].astype(str)
    selector_df = selector_df.sort_values(["__ord0", "__ord1"]).drop(columns=["__ord0", "__ord1"])

    selector_keys = selector_df["key"].tolist()
    key_to_label = dict(zip(selector_df["key"], selector_df["label"]))
    key_to_kind = dict(zip(selector_df["key"], selector_df["kind"]))

    # default: Nivel general
    default_key = None
    for k, lab in key_to_label.items():
        if _is_nivel_general(lab):
            default_key = k
            break
    if default_key is None and selector_keys:
        default_key = selector_keys[0]

    selected_keys = st.multiselect(
        "Seleccioná una o más divisiones",
        options=selector_keys,
        default=[default_key] if default_key else [],
        format_func=lambda k: key_to_label.get(k, k),
    )
    if not selected_keys:
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
    # Helpers de filtrado por key
    # =========================
    def _filter_by_key(df: pd.DataFrame, key: str) -> pd.DataFrame:
        kind = key_to_kind.get(key)
        if kind == "division":
            return df[df["Codigo_str"] == key]
        # categoria
        raw = key.replace("CAT::", "", 1)
        return df[(df["Clasificador"].str.lower() == "categorias") & (df["Descripcion"] == raw)]

    # Serie base: primera seleccionada
    base_key = selected_keys[0]
    base_label = key_to_label.get(base_key, base_key)

    base = _filter_by_key(ipc, base_key).copy()
    base = base.dropna(subset=[y_col]).sort_values("Periodo")
    if base.empty:
        st.warning("Sin serie para esa selección/frecuencia.")
        return

    base_last_period = pd.to_datetime(base["Periodo"].iloc[-1])
    base_last_val = float(base[y_col].iloc[-1])

    # KPI secundario (mostrar el otro, por prolijidad)
    base_last_vm = None
    base_last_yoy = None
    tmp_last = _filter_by_key(ipc, base_key).sort_values("Periodo")
    if not tmp_last.empty:
        if "v_m_IPC" in tmp_last.columns and pd.notna(tmp_last["v_m_IPC"].iloc[-1]):
            base_last_vm = float(tmp_last["v_m_IPC"].iloc[-1])
        if "v_i_a_IPC" in tmp_last.columns and pd.notna(tmp_last["v_i_a_IPC"].iloc[-1]):
            base_last_yoy = float(tmp_last["v_i_a_IPC"].iloc[-1])

    # =========================
    # Layout KPI + Gráfico
    # =========================
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    with c1:
        # KPI principal = frecuencia elegida
        big = base_last_val
        small = base_last_yoy if freq == "Mensual" else base_last_vm
        small_suffix = "anual" if freq == "Mensual" else "mensual"

        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1.0;">
              <span style="font-size:48px;">{_fmt_pct_es(big, 1)}%</span>
              <span style="font-size:20px; font-weight:700; color:#111827; margin-left:6px;">
                {_mmmyy_es(base_last_period)}
              </span>
            </div>
            <div style="margin-top:10px; font-size:18px; font-weight:800;">
              {kpi_suffix}
            </div>
            <div style="margin-top:8px; font-size:18px; font-weight:800;">
              {_fmt_pct_es(small, 1) if small is not None else "-"}% {small_suffix}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # CSV de seleccionados (Nacional)
        out_parts = []
        for k in selected_keys:
            part = _filter_by_key(ipc, k).copy()
            part["SelectorKey"] = k
            part["SelectorLabel"] = key_to_label.get(k, k)
            out_parts.append(part)
        out = pd.concat(out_parts, ignore_index=True) if out_parts else ipc.iloc[0:0].copy()

        csv = out.sort_values(["SelectorLabel", "Periodo"]).to_csv(index=False, sep=";", decimal=",").encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name="ipc_seleccion.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with c2:
        # Período ARRIBA del gráfico
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "Todo"],
            horizontal=True,
            index=3,
            label_visibility="collapsed",
        )

        max_real = pd.to_datetime(base_last_period)
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
            min_sel = pd.to_datetime(ipc["Periodo"].min())
            tick_freq = "6MS"
        max_sel = max_real + pd.DateOffset(months=1)

        # título dinámico
        title_txt = (
            f"La {title_word} de {base_label} de {_mmmyy_es(base_last_period)} fue "
            f"{_fmt_pct_es(base_last_val, 1)}%"
        )

        # Autoescala Y según período y frecuencia
        tmp_list = []
        for k in selected_keys:
            s = _filter_by_key(ipc, k).copy()
            s = s.dropna(subset=[y_col])
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)]
            if not s.empty:
                tmp_list.append(s[[y_col]])
        if not tmp_list:
            st.warning("No hay datos en el período seleccionado.")
            return
        tmp_vals = pd.concat(tmp_list, ignore_index=True)

        ymin = float(tmp_vals[y_col].min())
        ymax = float(tmp_vals[y_col].max())
        pad = max(0.8, (ymax - ymin) * 0.10)
        y_range = [ymin - pad, ymax + pad]

        # ticks X
        tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq=tick_freq)
        if len(tickvals) < 4:
            tickvals = pd.date_range(min_sel.normalize(), max_sel.normalize(), freq="MS")
        ticktext = [f"{_mes_es(d.month)}-{str(d.year)[-2:]}" for d in tickvals]

        fig = go.Figure()

        for k in selected_keys:
            lab = key_to_label.get(k, k)
            s = _filter_by_key(ipc, k).copy()
            s = s.dropna(subset=[y_col])
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)].sort_values("Periodo")
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s[y_col],
                    name=lab,
                    mode="lines+markers",
                    marker=dict(size=5),
                    hovertemplate="%{x|%b-%y}<br>%{y:.1f}%<extra></extra>",
                )
            )

        show_legend = len(selected_keys) > 1

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

    # =========================
    # TABLA: TODAS las variaciones mensuales disponibles
    # + incluye categorías (B/S/Estacional/Núcleo/Regulados)
    # + filas categorías más oscuras
    # + Nivel general primero y por default arriba
    # =========================
    st.markdown("#### Tabla de variaciones mensuales (toda la serie)")

    tab = ipc.dropna(subset=["Periodo", "v_m_IPC"]).copy()

    # rango completo de meses (de min a max) para columnas
    min_p = tab["Periodo"].min().to_period("M")
    max_p = tab["Periodo"].max().to_period("M")
    months = pd.period_range(min_p, max_p, freq="M")

    tab["Period"] = tab["Periodo"].dt.to_period("M")

    # armamos "Label" unificando divisiones + categorías
    # - divisiones: label = Descripcion (ej "Alimentos y bebidas")
    # - categorías: label = mapeo (B->Bienes, S->Servicios, etc.)
    tab["IsCategoria"] = tab["Clasificador"].str.lower().eq("categorias")
    tab["Label"] = tab["Descripcion"]
    tab.loc[tab["IsCategoria"], "Label"] = tab.loc[tab["IsCategoria"], "Label"].replace(
        {"B": "Bienes", "S": "Servicios"}
    )

    # pivot completo mensual
    piv = (
        tab[tab["Period"].isin(months)]
        .pivot_table(index="Label", columns="Period", values="v_m_IPC", aggfunc="last")
        .reindex(columns=months)
    )

    # renombrar columnas a mmm-yy
    piv.columns = [_mmmyy_es(p.to_timestamp("M")) for p in months]

    # ordenar filas: Nivel general primero, luego alfabético
    idx = list(piv.index)
    ng = None
    for r in idx:
        if _is_nivel_general(r):
            ng = r
            break
    others = sorted([x for x in idx if x != ng], key=lambda z: str(z))
    ordered = ([ng] if ng is not None else []) + others
    piv = piv.reindex(ordered)

    # formateo a string con coma y %
    def _fmt_cell(v):
        if pd.isna(v):
            return "-"
        return f"{_fmt_pct_es(float(v), 1)}%"

    piv_fmt = piv.applymap(_fmt_cell)

    # marcación de categorías más oscuras
    # detectamos qué labels son categorías presentes en el dataset:
    categorias_labels = (
        tab.loc[tab["IsCategoria"], "Label"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    categorias_set = set(categorias_labels)

    def _style_rows(df):
        styles = []
        for idx_name in df.index:
            if str(idx_name).strip() in categorias_set:
                styles.append(["font-weight:800; color:#111827; background-color:rgba(17,24,39,0.08)"] * df.shape[1])
            elif _is_nivel_general(idx_name):
                styles.append(["font-weight:800; background-color:rgba(17,24,39,0.04)"] * df.shape[1])
            else:
                styles.append([""] * df.shape[1])
        return pd.DataFrame(styles, index=df.index, columns=df.columns)

    st.dataframe(
        piv_fmt.style.apply(_style_rows, axis=None),
        use_container_width=True,
        height=520,
    )
