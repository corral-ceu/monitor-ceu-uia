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

    # ----------------------------
    # Selector de serie
    # ----------------------------
    SERIES = {
        13: {
            "label": "Adelantos en cuenta corriente",
            "caption": "Tasa de interés por adelantos en cuenta corriente - % TNA",
            "unit_short": "TNA",
            "y_title": "% TNA",
            "csv_col": "tna",
        },
        12: {
            "label": "Depósitos a 30 días (plazo)",
            "caption": "Tasa de interés de depósitos a 30 días de plazo en entidades financieras - % TNA",
            "unit_short": "TNA",
            "y_title": "% TNA",
            "csv_col": "tna",
        },
        14: {
            "label": "Préstamos personales",
            "caption": "Tasa de interés de préstamos personales - % TNA",
            "unit_short": "TNA",
            "y_title": "% TNA",
            "csv_col": "tna",
        },
        29: {
            "label": "Inflación esperada (REM) 12m",
            "caption": "REM: Mediana de la variación interanual próximos 12 meses (IPC) - %",
            "unit_short": "%",
            "y_title": "% i.a. (próx. 12m)",
            "csv_col": "inflacion_esp_12m",
        },
    }

    # Orden como te interesa ver en el selector
    options = [13, 12, 14, 29]
    labels = {k: SERIES[k]["label"] for k in options}

    sel_id = st.selectbox(
        "Serie",
        options=options,
        format_func=lambda k: labels.get(k, str(k)),
        index=0,
        label_visibility="collapsed",
    )

    meta = SERIES[sel_id]
    st.caption(meta["caption"])
    st.divider()

    # ----------------------------
    # Traigo serie seleccionada
    # ----------------------------
    df = get_monetaria_serie(sel_id)
    if df.empty:
        st.warning("Sin datos para la serie seleccionada.")
        return

    df = df.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)

    # Último dato
    last_val = float(df["value"].iloc[-1])
    last_date_ts = pd.to_datetime(df["Date"].iloc[-1])

    c1, c2 = st.columns([1, 3])

    # KPI + descarga
    with c1:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
                {_fmt_pct_es(last_val, 1)}% <span style="font-size:18px; font-weight:700;">{meta["unit_short"]}</span>
            </div>
            <div style="margin-top:8px; color:#6b7280; font-size:14px;">
                Último dato: {last_date_ts.strftime("%d/%m/%Y")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        csv_bytes = (
            df.rename(columns={"Date": "date", "value": meta["csv_col"]})
            .to_csv(index=False)
            .encode("utf-8")
        )
        file_name = f"serie_{sel_id}_{last_date_ts.strftime('%Y-%m-%d')}.csv"
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=False,
        )

    with c2:
        # Selector de período
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "Todo"],
            horizontal=True,
            index=2,  # 2A por defecto
            label_visibility="collapsed",
        )

        max_real = pd.to_datetime(df["Date"].max())
        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
        else:
            min_sel = pd.to_datetime(df["Date"].min())

        # Aire a la derecha: 1 mes calendario
        max_sel = max_real + pd.DateOffset(months=1)

        df_plot = df[df["Date"] >= min_sel].copy()

        # ----------------------------
        # Benchmark inflación esperada (id=29)
        # ----------------------------
        inflacion_esp_12m = None
        if sel_id != 29:
            infl = get_monetaria_serie(29)
            if not infl.empty:
                infl = infl.dropna(subset=["Date", "value"]).sort_values("Date")
                inflacion_esp_12m = float(infl["value"].iloc[-1])

        # fallback como tenías antes
        if inflacion_esp_12m is None:
            inflacion_esp_12m = 20.0

        if sel_id == 29:
            title_txt = (
                "   Inflación esperada (REM) para los próximos 12 meses "
                f"(mediana i.a.): {_fmt_pct_es(last_val, 1)}%"
            )
        else:
            pos = "por encima" if last_val > inflacion_esp_12m else "debajo"
            title_txt = (
                f"   La tasa se ubica {pos} de la inflación esperada para los próximos 12 meses: "
                f"{_fmt_pct_es(inflacion_esp_12m, 0)}%"
            )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["value"],
                name="Serie",
                mode="lines",
            )
        )

        # Eje X en español (ticks manuales)
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }

        min_date = pd.to_datetime(df_plot["Date"].min())
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

        fig.update_yaxes(title_text=meta["y_title"], ticksuffix="%")
        fig.update_xaxes(
            title_text="",
            range=[min_date, max_date],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            rangeslider=dict(visible=False),
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<div style='color:#6b7280; font-size:12px; margin-top:6px;'>"
            "Fuente: Banco Central de la República Argentina."
            "</div>",
            unsafe_allow_html=True,
        )
