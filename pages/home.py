import base64
import streamlit as st


def header_banner(image_path: str):
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    st.markdown(
        f"""
        <style>
          /* Pegarlo arriba: reduce paddings default de Streamlit */
          section.main > div {{
            padding-top: 0rem;
          }}
          .block-container {{
            padding-top: 0rem;
          }}

          /* Banner full width, sin recorte */
          .ceu-banner {{
            width: 100vw;
            aspect-ratio: 6 / 1;     /* ajustá si querés más bajo: 7/1 */
            margin-left: calc(-50vw + 50%);
            margin-top: -2.2rem;     /* sube más (ajustable) */

            display: block;
            line-height: 0;

            background-image: url("data:image/png;base64,{img_base64}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            background-color: #2f4f8f;
          }}
        </style>

        <div class="ceu-banner"></div>
        """,
        unsafe_allow_html=True,
    )


def render_main_home(go_to):
    header_banner("assets/header_ceu.png")

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
