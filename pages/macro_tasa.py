import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_monetaria_serie


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


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

    tasa = tasa.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)

    # Último dato
    last_val = float(tasa["value"].iloc[-1])
    last_date = pd.to_datetime(tasa["Date"].iloc[-1]).date()

    c1, c2 = st.columns([1, 3])

    # KPI
    with c1:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
                {_fmt_pct_es(last_val, 1)}% <span style="font-size:18px; font-weight:700;">TNA</span>
            </div>
            <div style="margin-top:8px; color:#6b7280; font-size:14px;">
                Último dato: {last_date.strftime("%d/%m/%Y")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        # ---- Selector de período (sin mini-gráfico) ----
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "5A", "Todo"],
            horizontal=True,
            index=2,  # 2A por defecto
            label_visibility="collapsed",
        )

        max_real = pd.to_datetime(tasa["Date"].max())
        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
        elif rango == "5A":
            min_sel = max_real - pd.DateOffset(years=5)
        else:
            min_sel = pd.to_datetime(tasa["Date"].min())

        # Aire a la derecha: 1 mes calendario
        max_sel = max_real + pd.DateOffset(months=1)

        tasa_plot = tasa[tasa["Date"] >= min_sel].copy()

        # ---- Título dinámico ----
        inflacion_esp_12m = 20.0
        pos = "por encima" if last_val > inflacion_esp_12m else "debajo"
        title_txt = (
            f"La tasa se ubica {pos} de la inflación esperada para los próximos 12 meses: "
            f"{_fmt_pct_es(inflacion_esp_12m, 0)}%"
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=tasa_plot["Date"],
                y=tasa_plot["value"],
                name="Tasa",
                mode="lines",
            )
        )

        # Eje X en español (ticks manuales)
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }

        min_date = pd.to_datetime(tasa_plot["Date"].min())
        max_date = max_sel

        tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="6MS")
        ticktext = [f"{mes_es[d.month]} {d.year}" for d in tickvals]

        fig.update_layout(
            hovermode="x unified",
            height=450,
            margin=dict(l=10, r=10, t=70, b=60),
            showlegend=False,
            title=dict(text=title_txt, x=0, xanchor="left"),
        )

        fig.update_yaxes(title_text="% TNA", ticksuffix="%")
        fig.update_xaxes(
            title_text="",
            range=[min_date, max_date],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            rangeslider=dict(visible=False),  # <- sin mini gráfico
        )

        st.plotly_chart(fig, use_container_width=True)
