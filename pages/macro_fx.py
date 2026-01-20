import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from services.macro_data import (
    build_bands_2025,
    build_bands_2026,
    get_a3500,
    get_ipc_nacional_nivel_general,
    get_rem_last,
)
from ui.common import safe_pct


def render_macro_fx(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    st.markdown("## 💱 Tipo de cambio")
    st.caption("Tipo de cambio mayorista A3500 y bandas cambiarias – ARS/USD")
    st.divider()

    def asof_fx(df_fx: pd.DataFrame, target_date: pd.Timestamp):
        t = df_fx.dropna(subset=["Date", "FX"]).sort_values("Date")
        t = t[t["Date"] <= target_date]
        if t.empty:
            return None, None
        r = t.iloc[-1]
        return float(r["FX"]), pd.to_datetime(r["Date"])

    with st.spinner("Cargando datos..."):
        fx = get_a3500()
        rem = get_rem_last()
        ipc = get_ipc_nacional_nivel_general()

        bands_2025 = build_bands_2025("2025-04-14", "2025-12-31", 1000.0, 1400.0)
        bands_2026 = build_bands_2026(bands_2025, rem, ipc)
        bands = (
            pd.concat([bands_2025, bands_2026], ignore_index=True)
            .dropna(subset=["Date", "lower", "upper"])
            .sort_values("Date")
        )

        fx = fx.copy()
        fx["Date"] = pd.to_datetime(fx["Date"], errors="coerce")
        fx["FX"] = pd.to_numeric(fx["FX"], errors="coerce")
        fx = fx.dropna(subset=["Date", "FX"]).drop_duplicates(subset=["Date"]).sort_values("Date")

        df = bands.merge(fx, on="Date", how="left").sort_values("Date")

    if fx.empty:
        st.warning("Sin datos A3500.")
        return

    last_date = pd.to_datetime(fx["Date"].iloc[-1])
    last_fx = float(fx["FX"].iloc[-1])

    fx_m, _ = asof_fx(fx, last_date - pd.Timedelta(days=30))
    fx_y, _ = asof_fx(fx, last_date - pd.Timedelta(days=365))

    vm = None if fx_m is None else (last_fx / fx_m - 1) * 100
    va = None if fx_y is None else (last_fx / fx_y - 1) * 100

    up_row = df.loc[df["Date"] == last_date, "upper"]
    upper_last = float(up_row.iloc[0]) if (not up_row.empty and pd.notna(up_row.iloc[0])) else None
    dist_to_upper = None
    if upper_last is not None and last_fx > 0:
        dist_to_upper = (upper_last / last_fx - 1) * 100

    # Plot desde feb-2025
    start_date_plot = pd.Timestamp("2025-02-01")
    fx_plot = fx[fx["Date"] >= start_date_plot].copy()
    df_plot = df[df["Date"] >= start_date_plot].copy()
    bands_end = (
        pd.to_datetime(df_plot["Date"].max())
        if not df_plot.empty
        else pd.to_datetime(fx_plot["Date"].max())
    )

    # ---- Layout KPI + gráfico ----
    kpi_col, chart_col = st.columns([1, 3], vertical_alignment="top")

    with kpi_col:
        st.markdown(
            f"""
            <div style="font-size:54px; font-weight:800; line-height:1.0;">
              <span style="font-size:16px; font-weight:700; color:#111827;">ARS/USD</span>
              {int(round(last_fx))}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Fecha: {last_date.strftime('%d/%m/%Y')}")
    
        # % más grandes (como pediste)
        st.markdown(
            f"<div style='font-size:18px; margin-top:14px;'><b>% mensual:</b> {safe_pct(vm, 1)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:18px; margin-top:8px;'><b>% anual:</b> {safe_pct(va, 1)}</div>",
            unsafe_allow_html=True,
        )
    
        # espacio antes del botón
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    
        # Descargar CSV (debajo de todo)
        fx_csv = fx[["Date", "FX"]].copy()
        fx_csv = fx_csv.rename(columns={"Date": "date", "FX": "a3500"})
        csv_bytes = fx_csv.to_csv(index=False).encode("utf-8")
        file_name = f"a3500_{last_date.strftime('%Y-%m-%d')}.csv"
    
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=file_name,
            mime="text/csv",
            use_container_width=False,  # más angosto, como en tasa
        )


    with chart_col:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["upper"],
                name="Banda superior",
                line=dict(dash="dash"),
                hovertemplate="%{x|%d/%m/%Y}<br>Banda superior: %{y:.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["lower"],
                name="Banda inferior",
                line=dict(dash="dash"),
                fill="tonexty",
                fillcolor="rgba(0,0,0,0.08)",
                hovertemplate="%{x|%d/%m/%Y}<br>Banda inferior: %{y:.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fx_plot["Date"],
                y=fx_plot["FX"],
                name="A3500",
                mode="lines",
                connectgaps=False,
                hovertemplate="%{x|%d/%m/%Y}<br>A3500: %{y:.0f}<extra></extra>",
            )
        )

        # ---- Eje X en español (ticks manuales) ----
        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }

        min_date = start_date_plot
        max_date = bands_end + pd.DateOffset(months=1)  # aire a la derecha

        tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq="2MS")
        ticktext = [f"{mes_es[d.month]} {d.year}" for d in tickvals]

        # ---- Título dentro del gráfico (como en tasas) ----
        title_txt = ""
        if dist_to_upper is not None:
            title_txt = (
                f"   El TC se encuentra a {safe_pct(dist_to_upper, 1)} de la banda superior"
            )

        fig.update_layout(
            hovermode="x",
            height=600,
            margin=dict(l=10, r=10, t=60, b=60),
            showlegend=True,
            title=dict(text=title_txt, x=0, xanchor="left"),
        )

        fig.update_xaxes(
            title_text="",
            range=[min_date, max_date],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
        )
        fig.update_yaxes(title_text="")

        st.plotly_chart(fig, use_container_width=True)

        # Fuente
        st.markdown(
            "<div style='color:#6b7280; font-size:12px; margin-top:6px;'>"
            "Fuente: Banco Central de la República Argentina."
            "</div>",
            unsafe_allow_html=True,
        )
