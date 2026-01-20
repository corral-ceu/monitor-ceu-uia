import streamlit as st


def render_main_home(go_to):
    st.markdown(
        """
        <div class="home-wrap">
          <div class="home-title">Monitor CEU–UIA</div>
          <div class="home-subtitle">Seleccioná una sección</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_pad, mid, right_pad = st.columns([1, 6, 1])
    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("📊\nMacroeconomía", use_container_width=True):
                go_to("macro_home")
        with c2:
            if st.button("💼\nEmpleo Privado", use_container_width=True):
                go_to("empleo")
        with c3:
            if st.button("🏭\nProducción Industrial", use_container_width=True):
                go_to("ipi")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:90px'></div>", unsafe_allow_html=True)

        logo_col = st.columns([2, 1, 2])
        with logo_col[1]:
            try:
                st.image("assets/logo_ceu.png")
            except Exception:
                st.markdown("### CEU - UIA")
