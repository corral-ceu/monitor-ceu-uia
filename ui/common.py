import pandas as pd
import streamlit as st


def topbar_logo() -> None:
    """Logo institucional arriba a la derecha."""
    _, col_logo = st.columns([10, 2], vertical_alignment="top")
    with col_logo:
        try:
            # Nota: asegurate de subir assets/logo_ceu.png al repo
            st.image("assets/logo_ceu.png", use_container_width=True)
        except Exception:
            st.markdown("### CEU - UIA")


def safe_pct(x, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.{dec}f}%".replace(".", ",")


def get_section(default: str = "home") -> str:
    """Lee la seccion desde session_state y query params."""
    if "section" not in st.session_state:
        st.session_state.section = default

    params = st.query_params
    if "section" in params:
        sec = params["section"]
        if isinstance(sec, (list, tuple)):
            sec = sec[0]
        if isinstance(sec, str) and sec.strip():
            st.session_state.section = sec.strip()

    return st.session_state.section


def go_to(section: str):
    st.session_state["section"] = section
    st.query_params["section"] = section  # mantiene URL consistente
    st.rerun()

