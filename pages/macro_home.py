import streamlit as st


def render_macro_home(go_to):
    # Botón volver
    if st.button("← Volver"):
        go_to("home")

    st.markdown(
        """
        <div class="home-wrap">
          <div class="home-title">Macroeconomía</div>
          <div class="home-subtitle">Seleccioná una variable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_pad, mid, right_pad = st.columns([1, 6, 1])
    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")
        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")
        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
