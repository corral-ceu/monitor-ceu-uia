import base64
import streamlit as st


def _header_banner(image_path: str, height_px: int = 140):
    """
    Banner full-width (full-bleed) con imagen de fondo.
    Requiere: image_path (ej: assets/header_ceu.png)
    """
    try:
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        st.markdown(
            f"""
            <style>
              /* Full-bleed: ocupa 100vw aunque el contenido esté en container */
              .ceu-banner {{
                width: 100vw;
                height: {height_px}px;
                margin-left: calc(-50vw + 50%);
                background-image: url("data:image/png;base64,{img_base64}");
                background-size: cover;
                background-position: center;
                border-radius: 0px;
              }}

              /* Espacio debajo del banner (ajustable) */
              .ceu-banner-spacer {{
                height: 18px;
              }}
            </style>

            <div class="ceu-banner"></div>
            <div class="ceu-banner-spacer"></div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        # Si no encuentra el archivo o falla, no rompe la home
        st.warning("No se pudo cargar el banner (assets/header_ceu.png).")


def render_main_home(go_to):
    # ✅ 1) Banner arriba (todo el ancho)
    _header_banner("assets/header_ceu.png", height_px=140)

    # ✅ 2) Tu título/subtítulo como estaban
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

  
