import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import get_monetaria_serie


def _fmt_pct_es(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def _rem29_to_daily(df_m: pd.DataFrame) -> pd.DataFrame:
    """REM 29 mensual -> diario (valor mensual repetido cada día del mes)."""
    if df_m is None or df_m.empty:
        return pd.DataFrame(columns=["Date", "value"])

    df_m = (
        df_m.dropna(subset=["Date", "value"])
        .sort_values("Date")
        .reset_index(drop=True)
    )
    df_m["Period"] = df_m["Date"].dt.to_period("M")
    df_m = df_m.drop_duplicates("Period", keep="last")

    start = df_m["Period"].min().to_timestamp(how="start")
    end = df_m["Period"].max().to_timestamp(how="end")

    cal = pd.DataFrame({"Date": pd.date_range(start, end, freq="D")})
    cal["Period"] = cal["Date"].dt.to_period("M")

    out = cal.merge(df_m[["Period", "value"]], on="Period", how="left").drop(columns=["Period"])
    return out


def _title_line(nombre: str, tasa_val: float, infl_val: float) -> str:
    pos = "por encima" if tasa_val > infl_val else "por debajo"

    if nombre == "Adelantos":
        desc = "adelantos en cuenta corriente"
    elif nombre == "Préstamos Personales":
        desc = "préstamos personales"
    else:
        desc = "plazo fijo"

    return (
        f"<b>{nombre}:</b> La tasa de {desc} ({_fmt_pct_es(tasa_val, 1)}%) "
        f"se encuentra {pos} de la inflación esperada ({_fmt_pct_es(infl_val, 1)}%)"
    )


def render_macro_tasa(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 📈 Tasa de interés")
    st.caption("Seleccioná una o más tasas (% TNA) y comparalas con la inflación esperada (REM, 12m).")
    st.divider()

    # --- CSS para que el multiselect se lea bien (chips + fondo claro) ---
    st.markdown(
        """
        <style>
          /* ancho max del selector */
          div[data-testid="stMultiSelect"] { max-width: 420px; }

          /* caja del input */
          div[data-testid="stMultiSelect"] div[class*="control"] {
            background: #ffffff !important;
            border-color: #cbd5e1 !important;
          }

          /* texto general del multiselect */
          div[data-testid="stMultiSelect"] * {
            color: #0f172a !important;
          }

          /* chips seleccionados */
          div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
            background-color: #e2e8f0 !important;
            border: 1px solid #cbd5e1 !important;
          }

          /* texto dentro del chip */
          div[data-testid="stMultiSelect"] span[data-baseweb="tag"] span {
            color: #0f172a !important;
            font-weight: 600 !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    SERIES_TASAS = {
        13: {"nombre": "Adelantos"},
        12: {"nombre": "Depósitos"},
        14: {"nombre": "Préstamos Personales"},
    }

    # ---------- Selector angosto, alineado a la izquierda ----------
    sel_wrap, _ = st.columns([2, 8])
    with sel_wrap:
        sel_ids = st.multiselect(
            "Tasas",
            options=[13, 12, 14],
            default=[13, 14],
            format_func=lambda k: SERIES_TASAS[k]["nombre"],
            label_visibility="collapsed",
        )

    if not sel_ids:
        st.warning("Seleccioná al menos una tasa.")
        return

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ---------- REM 29 como benchmark (mensual -> diario) ----------
    rem29_m = get_monetaria_serie(29)
    rem29_d = _rem29_to_daily(rem29_m)
    inflacion_esp_12m = float(rem29_d["value"].iloc[-1]) if not rem29_d.empty else 20.0

    # ---------- Series seleccionadas ----------
    series_data = {}
    for sid in sel_ids:
        df = get_monetaria_serie(sid)
        if df.empty:
            continue
        df = df.dropna(subset=["Date", "value"]).sort_values("Date").reset_index(drop=True)
        series_data[sid] = df

    if not series_data:
        st.warning("Sin datos para las tasas seleccionadas.")
        return

    # KPI: primera seleccionada disponible
    base_id = sel_ids[0] if sel_ids[0] in series_data else list(series_data.keys())[0]
    base_df = series_data[base_id]
    last_val = float(base_df["value"].iloc[-1])
    last_date_ts = pd.to_datetime(base_df["Date"].iloc[-1])

    c1, c2 = st.columns([1, 3])

    # ---------- KPI + CSV ----------
    with c1:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
                {_fmt_pct_es(last_val, 1)}% <span style="font-size:18px; font-weight:700;">TNA</span>
            </div>
            <div style="margin-top:8px; color:#6b7280; font-size:14px;">
                Último dato ({SERIES_TASAS[base_id]["nombre"]}): {last_date_ts.strftime("%d/%m/%Y")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # CSV largo: date, serie, value
        long_parts = []
        for sid, df in series_data.items():
            tmp = df.rename(columns={"Date": "date", "value": "value"}).copy()
            tmp["serie"] = SERIES_TASAS[sid]["nombre"]
            long_parts.append(tmp[["date", "serie", "value"]])
        out = pd.concat(long_parts, ignore_index=True).sort_values(["serie", "date"])

        csv_bytes = out.to_csv(index=False).encode("utf-8")
        file_name = f"tasas_tna_{last_date_ts.strftime('%Y-%m-%d')}.csv"

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=False,
        )

    # ---------- Controles + Gráfico ----------
    with c2:
        rango = st.radio(
            "Período",
            ["6M", "1A", "2A", "5A", "Todo"],
            horizontal=True,
            index=2,
            label_visibility="collapsed",
        )

        show_infl_line = st.checkbox("Mostrar inflación esperada (REM) en el gráfico", value=False)

        max_real = max(pd.to_datetime(df["Date"].max()) for df in series_data.values())

        if rango == "6M":
            min_sel = max_real - pd.DateOffset(months=6)
        elif rango == "1A":
            min_sel = max_real - pd.DateOffset(years=1)
        elif rango == "2A":
            min_sel = max_real - pd.DateOffset(years=2)
        elif rango == "5A":
            min_sel = max_real - pd.DateOffset(years=5)
        else:
            # por ahora, lo que haya en datos (después arreglamos lo de 2022 con paginación)
            min_sel = min(pd.to_datetime(df["Date"].min()) for df in series_data.values())

        max_sel = max_real + pd.DateOffset(months=1)

        # Texto explicativo arriba del gráfico (sin pisarse con leyenda)
        title_lines = []
        for sid in sel_ids:
            df = series_data.get(sid)
            if df is None or df.empty:
                continue
            tasa_last = float(df["value"].iloc[-1])
            title_lines.append(_title_line(SERIES_TASAS[sid]["nombre"], tasa_last, inflacion_esp_12m))

        st.markdown(
            "<div style='margin-top:8px; margin-bottom:6px; font-size:14px; line-height:1.35; color:#0f172a;'>"
            + "<br>".join(title_lines)
            + "</div>",
            unsafe_allow_html=True,
        )

        fig = go.Figure()

        for sid in sel_ids:
            df = series_data.get(sid)
            if df is None or df.empty:
                continue
            df_plot = df[df["Date"] >= min_sel].copy()
            fig.add_trace(
                go.Scatter(
                    x=df_plot["Date"],
                    y=df_plot["value"],
                    name=SERIES_TASAS[sid]["nombre"],
                    mode="lines",
                )
            )

        if show_infl_line and (not rem29_d.empty):
            infl_plot = rem29_d[(rem29_d["Date"] >= min_sel) & (rem29_d["Date"] <= max_sel)].copy()
            fig.add_trace(
                go.Scatter(
                    x=infl_plot["Date"],
                    y=infl_plot["value"],
                    name="Inflación esperada (REM 12m)",
                    mode="lines",
                    line=dict(dash="dot"),
                )
            )

        # Eje X en español (ticks manuales)
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }
        tickvals = pd.date_range(pd.to_datetime(min_sel).normalize(), pd.to_datetime(max_sel).normalize(), freq="6MS")
        ticktext = [f"{mes_es[d.month]} {d.year}" for d in tickvals]

        fig.update_layout(
            hovermode="x unified",
            height=450,
            margin=dict(l=10, r=10, t=10, b=60),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )

        fig.update_yaxes(title_text="% (TNA)", ticksuffix="%")
        fig.update_xaxes(
            title_text="",
            range=[min_sel, max_sel],
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
