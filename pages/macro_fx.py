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

    last_date = fx["Date"].iloc[-1]
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

    start_date_plot = pd.Timestamp("2025-02-01")
    fx_plot = fx[fx["Date"] >= start_date_plot].copy()
    df_plot = df[df["Date"] >= start_date_plot].copy()
    bands_end = pd.to_datetime(df_plot["Date"].max()) if not df_plot.empty else pd.to_datetime(fx_plot["Date"].max())

    if dist_to_upper is not None:
        st.markdown(
            f"<div style='text-align:center; font-weight:700; margin: 6px 0 14px 0;'>"
            f"El TC se encuentra a {safe_pct(dist_to_upper, 1)} de la banda superior"
            f"</div>",
            unsafe_allow_html=True,
        )

    kpi_col, chart_col = st.columns([1, 3], vertical_alignment="top")

    with kpi_col:
        st.markdown(
            f"<div style='font-size:54px; font-weight:800; line-height:1.0'>{int(round(last_fx))}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Fecha: {pd.to_datetime(last_date).date().isoformat()}")
        st.markdown(f"**% mensual:** {safe_pct(vm, 1)}")
        st.markdown(f"**% anual:** {safe_pct(va, 1)}")

    with chart_col:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_plot["Date"],
                y=df_plot["upper"],
                name="Banda superior",
                line=dict(dash="dash"),
                hovertemplate="%{x|%Y-%m-%d}<br>Banda superior: %{y:.0f}<extra></extra>",
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
                hovertemplate="%{x|%Y-%m-%d}<br>Banda inferior: %{y:.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fx_plot["Date"],
                y=fx_plot["FX"],
                name="A3500",
                mode="lines",
                connectgaps=False,
                hovertemplate="%{x|%Y-%m-%d}<br>A3500: %{y:.0f}<extra></extra>",
            )
        )

        fig.update_layout(hovermode="x", height=600, margin=dict(t=10), showlegend=True)
        fig.update_xaxes(title_text="", range=[start_date_plot, bands_end])
        fig.update_yaxes(title_text="")

        st.plotly_chart(fig, use_container_width=True)
