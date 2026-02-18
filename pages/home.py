import base64
import streamlit as st


def _img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_main_home(go_to):
    # ------------------------------------------------------------
    # Navegación via query param (?go=...)
    # ------------------------------------------------------------
    try:
        go = st.query_params.get("go")
    except Exception:
        go = st.experimental_get_query_params().get("go", [None])[0]

    if go:
        try:
            st.query_params.clear()
        except Exception:
            st.experimental_set_query_params()
        go_to(go)
        return

    logo_b64 = _img_to_b64("assets/okok.png")

    # ------------------------------------------------------------
    # Estilos (SCOPED) + tipografía Bloomberg-ish
    # ------------------------------------------------------------
    st.markdown(
        """
        <style>
          .home-shell{
            max-width: 1200px;
            margin: 42px auto 20px auto;
            padding: 0 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
          }

          .home-shell, .home-shell *{
            font-family: Inter, "Helvetica Neue", Helvetica, Arial, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
            letter-spacing: -0.15px;
          }

          .home-title{
            font-size: 46px;
            font-weight: 900;
            letter-spacing: -0.8px;
            color: #0f172a;
            margin: 6px 0 30px 0;
            text-align: center;
          }

          .home-cards{
            width: 100%;
            max-width: 1000px;
          }

          /* Cards más altas (todas iguales) */
          .home-cards div.stButton > button{
            width: 100% !important;
            height: 156px !important;            /* 👈 más altas */
            border-radius: 22px !important;
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.14) !important;
            box-shadow: 0 12px 28px rgba(15,23,42,0.12) !important;

            font-weight: 900 !important;
            font-size: 24px !important;
            color: #0f172a !important;

            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;

            transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease !important;
          }

          .home-cards div.stButton > button:hover{
            transform: translateY(-3px);
            box-shadow: 0 18px 36px rgba(15,23,42,0.16) !important;
            border-color: rgba(15,23,42,0.22) !important;
          }

          /* Logo: centrado perfecto + sin zoom (no st.image) */
          .home-logo{
            margin-top: 26px;
            width: 100%;
            display: flex;
            justify-content: center;
          }
          .home-logo img{
            width: 96px;              /* 👈 más chico */
            height: auto;
            display: block;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------
    st.markdown("<div class='home-shell'>", unsafe_allow_html=True)
    st.markdown("<div class='home-title'>Monitor CEU–UIA</div>", unsafe_allow_html=True)

    st.markdown("<div class='home-cards'>", unsafe_allow_html=True)

    sections = [
        ("🚢 Comercio Exterior", "comex"),
        ("📈 Actividad Económica", "macro_pbi_emae"),
        ("🚀 Datos Adelantados", None),
        ("📊 Macroeconomía", "macro_home"),
        ("💼 Empleo Privado", "empleo"),
        ("🏭 Producción Industrial", "ipi"),
    ]

    r1 = st.columns(3, gap="large")
    r2 = st.columns(3, gap="large")
    cols = r1 + r2

    for col, (label, target) in zip(cols, sections):
        with col:
            if st.button(
                label,
                use_container_width=True,
                disabled=(target is None),
                key=f"home_{label.replace(' ', '_').replace('–','-').lower()}",
            ):
                go_to(target)

    st.markdown("</div>", unsafe_allow_html=True)

    # Logo centrado (sin visor/zoom)
    st.markdown(
        f"""
        <div class="home-logo">
          <img src="data:image/png;base64,{logo_b64}" alt="CEU" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
