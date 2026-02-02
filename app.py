# ============================================================
# Monitor CEU–UIA (UNIFICADO)
# Estructura modular para trabajar en equipo (GitHub)
# Secciones:
# - Home
# - Macroeconomía (FX / Tasa / Precios)
# - Empleo Privado (SIPA)
# - Producción Industrial (IPI INDEC)
# ============================================================

import warnings

import streamlit as st

from ui.theme import apply_global_styles
from ui.common import get_section, go_to, topbar_logo

from pages.home import render_main_home
from pages.macro_home import render_macro_home
from pages.macro_fx import render_macro_fx
from pages.macro_tasa import render_macro_tasa
from pages.macro_precios import render_macro_precios
from pages.macro_pbi_emae import render_macro_pbi_emae
from pages.empleo import render_empleo
from pages.ipi import render_ipi


# ----------------------------
# Warnings (limpia consola)
# ----------------------------
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


# ----------------------------
# Configuración Streamlit
# ----------------------------
st.set_page_config(
    page_title="Monitor CEU–UIA",
    page_icon="assets/ok.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_global_styles()


# ----------------------------
# Router
# ----------------------------
sec = get_section(default="home")

# Logo en todas las secciones salvo Home
if sec != "home":
    topbar_logo()

if sec == "home":
    render_main_home(go_to)

elif sec == "macro_home":
    if st.button("← Volver a secciones"):
        go_to("home")
    render_macro_home(go_to)

elif sec == "macro_fx":
    if st.button("← Volver a secciones"):
        go_to("home")
    render_macro_fx(go_to)

elif sec == "macro_tasa":
    if st.button("← Volver a secciones"):
        go_to("home")
    render_macro_tasa(go_to)

elif sec == "macro_precios":
    if st.button("← Volver a secciones"):
        go_to("home")
    render_macro_precios(go_to)

elif sec == "macro_pbi_emae":
    if st.button("← Volver a secciones"):
        go_to("home")
    render_macro_pbi_emae(go_to)

elif sec == "empleo":
    render_empleo(go_to)

elif sec == "ipi":
    render_ipi(go_to)

else:
    st.warning("Sección desconocida. Volviendo al inicio.")
    go_to("home")
