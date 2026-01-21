import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


# =========================
# Helpers
# =========================
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


# =========================
# Página
# =========================
def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa de inflación – % Nacional")
    st.divider()

    # =========================
    # CSS selector
    # =========================
    st.markdown(
        """
        <style>
        div[data-baseweb="select"]{
            max-width: 720px;
        }
        div[data-baseweb="select"] > div{
            background: rgba(17,24,39,0.94);
            border-radius: 12px;
            min-height: 52px;
        }
        div[data-baseweb="select"] *{
            color: rgba(255,255,255,0.95) !important;
            font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Datos
    # =========================
    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()

    ipc["Codigo_str"] = ipc["Codigo"].astype(str).str.strip()
    ipc["Descripcion"] = ipc["Descripcion"].astype(str).str.strip()
    ipc["Periodo"] = pd.to_datetime(ipc["Periodo"], errors="coerce")
    ipc = ipc.dropna(subset=["Periodo"])

    # =========================
    # Construcción del selector
    # =========================
    rows = (
        ipc[["Codigo_str", "Descripcion"]]
        .drop_duplicates()
        .copy()
    )

    def build_label(r):
        c = r["Codigo_str"]
        d = r["Descripcion"]

        # códigos 0–12 → usar Descripcion
        if c.isdigit() and 0 <= int(c) <= 12:
            return d

        # resto → usar Codigo, con excepciones
        if c == "B":
            return "Bienes"
        if c == "S":
            return "Servicios"
        return c

    rows["label"] = rows.apply(build_label, axis=1)

    # ordenar: Nivel general primero, luego alfabético
    rows["ord0"] = rows["label"].apply(lambda x: 0 if _is_nivel_general(x) else 1)
    rows = rows.sort_values(["ord0", "label"])

    selector_keys = rows["Codigo_str"].tolist()
    key_to_label = dict(zip(rows["Codigo_str"], rows["label"]))

    # default: Nivel general
    default_key = None
    for k, v in key_to_label.items():
        if _is_nivel_general(v):
            default_key = k
            break
    if default_key is None and selector_keys:
        default_key = selector_keys[0]

    selected = st.multiselect(
        "Seleccioná una o más divisiones",
        options=selector_keys,
        default=[default_key],
        format_func=lambda k: key_to_label.get(k, k),
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
    )

    if freq == "Mensual":
        y_col = "v_m_IPC"
        y_label = "Variación mensual (%)"
        title_word = "inflación"
        kpi_suffix = "mensual"
    else:
        y_col = "v_i_a_IPC"
        y_label = "Variación anual (%)"
        title_word = "inflación interanual"
        kpi_suffix = "anual"

    # =========================
    # Serie base (1ª selección)
    # =========================
    base_key = selected[0]
    base_label = key_to_label[base_key]

    base = ipc[ipc["Codigo_str"] == base_key].dropna(subset=[y_col]).sort_values("Periodo")
    if base.empty:
        st.warning("Sin datos para la selección.")
        return

    last_period = base["Periodo"].iloc[-1]
    last_value = float(base[y_col].iloc[-1])

    # =========================
    # Layout
    # =========================
    c1, c2 = st.columns([1, 3], vertical_alignment="top")

    with c1:
        st.markdown(
            f"""
            <div style="font-weight:800; line-height:1;">
              <span style="font-size:48px;">{_fmt_pct_es(last_value)}%</span>
              <span style="font-size:20px; margin-left:6px;">
                {_mmmyy_es(last_period)}
              </span>
            </div>
            <div style="margin-top:8px; font-size:18px; font-weight:800;">
              {kpi_suffix}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
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
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
        else:
            min_sel = ipc["Periodo"].min()

        fig = go.Figure()

        for k in selected:
            s = ipc[ipc["Codigo_str"] == k].dropna(subset=[y_col])
            s = s[(s["Periodo"] >= min_sel) & (s["Periodo"] <= max_real)]
            if s.empty:
                continue

            fig.add_trace(
                go.Scatter(
                    x=s["Periodo"],
                    y=s[y_col],
                    name=key_to_label[k],
                    mode="lines+markers",
                    marker=dict(size=5),
                )
            )

        fig.update_layout(
            height=520,
            hovermode="x unified",
            title=f"La {title_word} de {base_label} de {_mmmyy_es(last_period)} fue {_fmt_pct_es(last_value)}%",
            showlegend=len(selected) > 1,
        )

        fig.update_yaxes(title_text=y_label, ticksuffix="%")
        fig.update_xaxes(title_text="")

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: INDEC")
