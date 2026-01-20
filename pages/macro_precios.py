import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_ipc_indec_full


def render_macro_precios(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 🛒 Precios")
    st.caption("Tasa mensual de inflación - % Nacional")
    st.divider()

    ipc = get_ipc_indec_full()
    ipc = ipc[ipc["Region"] == "Nacional"].copy()
    if ipc.empty:
        st.warning("Sin datos IPC.")
        return

    opciones = sorted(ipc["Descripcion"].unique())
    default = opciones.index("Nivel general") if "Nivel general" in opciones else 0
    desc = st.selectbox("Seleccioná una división", opciones, index=default)

    serie = ipc[ipc["Descripcion"] == desc].dropna(subset=["v_m_IPC"])
    if serie.empty:
        st.warning("Sin serie para esa división.")
        return

    c1, c2 = st.columns([1, 3])
    with c1:
        last_val = float(serie["v_m_IPC"].iloc[-1])
        st.markdown(
            f"<div style='font-size:46px; font-weight:800'>{last_val:.1f}%</div>",
            unsafe_allow_html=True,
        )

    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=serie["Periodo"], y=serie["v_m_IPC"], name="Variación mensual"))
        fig.update_layout(hovermode="x unified", height=450)
        fig.update_yaxes(title_text="Variación mensual (%)", ticksuffix="%")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)
