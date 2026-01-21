import pandas as pd
import streamlit as st

from services.macro_data import get_a3500, get_monetaria_serie, get_ipc_nacional_nivel_general


def _fmt_num_es(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _fmt_mes_es(ts: pd.Timestamp) -> str:
    mes_es = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
    }
    return f"{mes_es[ts.month]}-{str(ts.year)[-2:]}"


def _kpi_card_html(value_txt: str, label_txt: str, date_txt: str) -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-value">{value_txt}</div>
        <div class="kpi-label">{label_txt}</div>
        <div class="kpi-date">{date_txt}</div>
    </div>
    """


def render_macro_home(go_to):
    # ---------- estilos (cards KPI) ----------
    st.markdown(
        """
        <style>
          .kpi-card{
            margin-top:10px;
            padding:14px 14px 12px 14px;
            background:#ffffff;
            border:1px solid rgba(15, 23, 42, 0.10);
            border-radius:14px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
          }
          .kpi-value{
            font-size:26px;
            font-weight:800;
            line-height:1.1;
            color:#0f172a;
            letter-spacing:-0.3px;
          }
          .kpi-label{
            margin-top:6px;
            font-size:13px;
            font-weight:600;
            color:#0f172a;
            opacity:0.85;
          }
          .kpi-date{
            margin-top:2px;
            font-size:12px;
            color:#64748b;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="home-wrap">
            <div class="home-title">Macroeconomía</div>
            <div class="home-subtitle">Seleccioná una variable</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- obtener últimos datos (fallbacks seguros) ----------
    # Tipo de cambio (A3500)
    fx_value_txt, fx_date_txt = "—", "—"
    try:
        fx = get_a3500()
        if fx is not None and not fx.empty:
            last_fx = float(fx["FX"].iloc[-1])
            last_fx_dt = pd.to_datetime(fx["Date"].iloc[-1])
            fx_value_txt = f"ARS/USD {_fmt_num_es(last_fx, 0)}"
            fx_date_txt = last_fx_dt.strftime("%d/%m/%Y")
    except Exception:
        pass

    # Tasa (Adelantos a empresas = id 13)
    tasa_value_txt, tasa_date_txt = "—", "—"
    try:
        t = get_monetaria_serie(13)
        if t is not None and not t.empty:
            last_t = float(t["value"].iloc[-1])
            last_t_dt = pd.to_datetime(t["Date"].iloc[-1])
            tasa_value_txt = f"{_fmt_pct_es(last_t, 1)}%"
            tasa_date_txt = last_t_dt.strftime("%d/%m/%Y")
    except Exception:
        pass

    # Precios (IPC Nacional nivel general, variación mensual)
    ipc_value_txt, ipc_date_txt = "—", "—"
    try:
        ipc = get_ipc_nacional_nivel_general()
        if ipc is not None and not ipc.empty:
            last_ipc = float(ipc["v_m_CPI"].iloc[-1]) * 100.0  # decimal -> %
            last_ipc_dt = pd.to_datetime(ipc["Date"].iloc[-1])
            ipc_value_txt = f"{_fmt_pct_es(last_ipc, 1)}%"
            ipc_date_txt = _fmt_mes_es(last_ipc_dt)
    except Exception:
        pass

    left_pad, mid, right_pad = st.columns([1, 6, 1])

    with mid:
        st.markdown('<div class="home-cards">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("💱\nTipo de cambio", use_container_width=True):
                go_to("macro_fx")
            st.markdown(
                _kpi_card_html(
                    fx_value_txt,
                    "TC Mayorista",
                    fx_date_txt,
                ),
                unsafe_allow_html=True,
            )

        with c2:
            if st.button("📈\nTasa de interés", use_container_width=True):
                go_to("macro_tasa")
            st.markdown(
                _kpi_card_html(
                    tasa_value_txt,
                    "Adelantos a empresas",
                    tasa_date_txt,
                ),
                unsafe_allow_html=True,
            )

        with c3:
            if st.button("🛒\nPrecios", use_container_width=True):
                go_to("macro_precios")
            st.markdown(
                _kpi_card_html(
                    ipc_value_txt,
                    "IPC Nivel general",
                    ipc_date_txt,
                ),
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
