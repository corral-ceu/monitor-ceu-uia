import base64
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# Helper: imagen a base64
# ============================================================
def _img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ============================================================
# HOME
# ============================================================
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

    # ------------------------------------------------------------
    # Streamlit: limpiar chrome y scroll
    # ------------------------------------------------------------
    st.markdown(
        """
        <style>
          html, body { height: 100%; overflow: hidden; }
          .stApp { height: 100vh; overflow: hidden; background: transparent !important; }

          section.main > div.block-container {
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
          }

          header[data-testid="stHeader"],
          [data-testid="stToolbar"],
          [data-testid="stDecoration"],
          #MainMenu,
          footer {
            display: none !important;
          }

          iframe[title="streamlit_component"]{
            width: 100% !important;
            height: 100vh !important;
            border: 0 !important;
            display: block !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # LOGO (ACÁ se define, UNA sola vez)
    # ------------------------------------------------------------
    logo_b64 = _img_to_b64("assets/okok2.png")

    # ------------------------------------------------------------
    # HTML DEL IFRAME
    # ------------------------------------------------------------
    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: #f3f5f9;
  }}

  .ceu-home-bg {{

  
  max-width: 1400px;     /* 👈 controla el ancho total */
  width: 100%;
  margin: 24px auto;     /* 👈 centra y crea aire lateral */
  border-radius: 28px;   /* 👈 queda tipo panel */
  padding: 30px 18px 22px 18px;
  box-sizing: border-box;


  background:
    radial-gradient(1200px 520px at 50% 18%, rgba(255,255,255,0.11), rgba(255,255,255,0.00) 60%),
    radial-gradient(900px 520px at 30% 76%, rgba(255,255,255,0.07), rgba(255,255,255,0.00) 60%),
    radial-gradient(1200px 700px at 70% 86%, rgba(0,0,0,0.18), rgba(0,0,0,0.00) 65%),
    linear-gradient(180deg, #1f2f5c 0%, #273a6f 45%, #1d2d5a 100%);

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 18px;
  }}

  .ceu-wrap {{
    max-width: 1120px;
    width: 100%;
    text-align: center;
  }}

  .ceu-title {{
    font-size: 52px;
    font-weight: 900;
    letter-spacing: -0.7px;
    color: rgba(255,255,255,0.96);
    margin: 0;
  }}

  .ceu-sub {{
    font-size: 18px;
    color: rgba(255,255,255,0.78);
    margin-top: 8px;
  }}

  .ceu-panel {{
    max-width: 1120px;
    width: 100%;
    padding: 24px;
    border-radius: 22px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 18px 60px rgba(0,0,0,0.30);
    backdrop-filter: blur(10px);
  }}

  .ceu-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
  }}

  .ceu-card {{
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(239,243,252,0.94));
    border: 1px solid rgba(16,24,40,0.10);
    box-shadow: 0 10px 28px rgba(0,0,0,0.14);
    padding: 18px;
    min-height: 100px;
  }}

  .ceu-top {{
    display: flex;
    gap: 14px;
  }}

  .ceu-ic {{
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: rgba(255,255,255,0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    flex-shrink: 0;
  }}

  .ceu-tt {{
    font-size: 20px;
    font-weight: 900;
    color: #1b2b55;
  }}

  .ceu-desc {{
    font-size: 14px;
    color: rgba(27,43,85,0.72);
    margin-top: 6px;
    line-height: 1.25;
  }}

  .ceu-cta {{
    margin-top: 16px;
    font-size: 14px;
    font-weight: 900;
    color: rgba(47,109,246,0.98);
    text-decoration: none;
    display: inline-flex;
  }}

  .ceu-cta.disabled {{
    color: rgba(27,43,85,0.35);
    pointer-events: none;
  }}

  .ceu-logo {{
    margin-top: 80px;
    display: flex;
    justify-content: center;
    opacity: 0.95;
  }}

  .ceu-logo img {{
    width: 150px;
    height: auto;
  }}

  @media (max-width: 1000px) {{
    .ceu-grid {{ grid-template-columns: repeat(2, 1fr); }}
  }}

  @media (max-width: 640px) {{
    .ceu-grid {{ grid-template-columns: 1fr; }}
    .ceu-title {{ font-size: 40px; }}
  }}
</style>
</head>

<body>
<div class="ceu-home-bg">

  <div class="ceu-wrap">
    <h1 class="ceu-title">Monitor CEU–UIA</h1>
    <div class="ceu-sub"></div>
  </div>

  <div class="ceu-panel">
    <div class="ceu-grid">

      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">🚢</div><div><div class="ceu-tt">Comercio Exterior</div><div class="ceu-desc">Exportaciones, importaciones, balanza, destinos y rubros.</div></div></div><a class="ceu-cta disabled">Abrir sección →</a></div>
      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">📈</div><div><div class="ceu-tt">Actividad Económica</div><div class="ceu-desc">Evolución del PBI, demanda, producción y sectores.</div></div></div><a class="ceu-cta disabled">Abrir sección →</a></div>
      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">🚀</div><div><div class="ceu-tt">Datos Adelantados</div><div class="ceu-desc">Elección Centro UIA, índices adelantados y expectativas.</div></div></div><a class="ceu-cta disabled">Abrir sección →</a></div>
      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">📊</div><div><div class="ceu-tt">Macroeconomía</div><div class="ceu-desc">Tipo de cambio, inflación, actividad, monetarias y más.</div></div></div><a class="ceu-cta" href="?go=macro_home">Abrir sección →</a></div>
      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">💼</div><div><div class="ceu-tt">Empleo Privado</div><div class="ceu-desc">Evolución, salarios, sectores y dinámica laboral.</div></div></div><a class="ceu-cta" href="?go=empleo">Abrir sección →</a></div>
      <div class="ceu-card"><div class="ceu-top"><div class="ceu-ic">🏭</div><div><div class="ceu-tt">Producción Industrial</div><div class="ceu-desc">IPI/EMI, sectores, niveles y variaciones.</div></div></div><a class="ceu-cta" href="?go=ipi">Abrir sección →</a></div>

    </div>
  </div>

  <div class="ceu-logo">
    <img src="data:image/png;base64,{logo_b64}" alt="CEU"/>
  </div>

</div>
</body>
</html>
"""

    components.html(html, height=1400, scrolling=False)
