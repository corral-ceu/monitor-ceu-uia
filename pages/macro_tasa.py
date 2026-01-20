import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_monetaria_serie


def render_macro_tasa(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 📈 Tasa de interés")
    st.caption("Tasa de adelantos a cuentas corrientes de empresas - % TNA")
    st.divider()

    tasa = get_monetaria_serie(145)
    if tasa.empty:
        st.warning("Sin datos de tasa.")
        return

    c1, c2 = st.columns([1, 3])

    with c1:
        last_val = float(tasa["value"].iloc[-1])
        st.markdown(
            f"<div style='font-size:46px; font-weight:800'>{last_val:.1f}%</div>",
            unsafe_allow_html=True,
        )

    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=tasa["Date"], y=tasa["value"], name="Tasa"))
        fig.update_layout(hovermode="x unified", height=450)
        fig.update_yaxes(title_text="% TNA", ticksuffix="%")
        fig.update_xaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True)
