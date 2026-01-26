import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

#### NUEVO: imports para frase aleatoria
import random
####

from services.macro_data import (
    build_bands_2025,
    build_bands_2026,
    get_a3500,
    get_ipc_bcra,
    get_rem_last,
    get_itcrm_excel_long,  # <-- AGREGAR
)

from ui.common import safe_pct


#### NUEVO: pool de frases (solo se muestra UNA, elegida al azar)
INDU_LOADING_PHRASES = [
    "La industria aporta más del 18% del valor agregado de la economía argentina.",
    "La industria es el segundo mayor empleador privado del país.",
    "Por cada empleo industrial directo se generan casi dos empleos indirectos.",
    "Los salarios industriales son 23% más altos que el promedio privado.",
    "Dos tercios de las exportaciones argentinas provienen de la industria.",
]
####


def render_macro_fx(go_to):
    if st.button("← Volver"):
        go_to("macro_home")

    # =========================
    # Estilos (solo formato)
    # =========================
    st.markdown(
        """
        <style>
          .fx-header{
            padding: 18px 18px 14px 18px;
            border-radius: 18px;
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(17,24,39,0.06);
            box-shadow: 0 10px 30px rgba(17,24,39,0.08);
            backdrop-filter: blur(6px);
          }
          .fx-title{
            font-size: 44px;
            font-weight: 850;
            letter-spacing: -0.02em;
            color: #111827;
            display:flex;
            align-items:center;
            gap: 12px;
            margin: 0;
          }
          .fx-icon{
            width: 44px;
            height: 44px;
            border-radius: 16px;
            display:flex;
            align-items:center;
            justify-content:center;
            background: rgba(59,130,246,0.12);
            color: #1d4ed8;
            font-weight: 900;
            font-size: 22px;
          }
          .fx-inline{
            display:flex;
            align-items: baseline;
            gap: 14px;
            flex-wrap: wrap;
            margin-top: 6px;
          }
          .fx-pair{
            font-size: 16px;
            font-weight: 800;
            color: #111827;
            opacity: 0.92;
          }
          .fx-value{
            font-size: 52px;
            font-weight: 900;
            letter-spacing: -0.03em;
            color:#111827;
            line-height: 1.0;
          }
          .fx-sub{
            margin-top: 8px;
            font-size: 14px;
            color: #6b7280;
          }
          .fx-chips{
            display:flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
          }
          .fx-chip{
            display:inline-flex;
            align-items:center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 12px;
            background: rgba(255,255,255,0.70);
            border: 1px solid rgba(17,24,39,0.08);
            font-size: 14px;
            color:#111827;
          }
          .fx-chip b{ font-weight: 850; }
          .fx-chip .up{ color:#047857; font-weight: 900; }
          .fx-chip .down{ color:#b91c1c; font-weight: 900; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Helpers
    # =========================
    def asof_fx(df_fx: pd.DataFrame, target_date: pd.Timestamp):
        t = df_fx.dropna(subset=["Date", "FX"]).sort_values("Date")
        t = t[t["Date"] <= target_date]
        if t.empty:
            return None, None
        r = t.iloc[-1]
        return float(r["FX"]), pd.to_datetime(r["Date"])

    # =========================
    # Carga datos
    # =========================

    #### NUEVO: frase mientras carga (se borra al terminar)
    fact_ph = st.empty()
    fact_ph.info("💡 " + random.choice(INDU_LOADING_PHRASES))
    ####

    with st.spinner("Cargando datos..."):
        fx = get_a3500()          # id=5
        rem = get_rem_last()
        ipc = get_ipc_bcra()      # id=27, % mensual en decimal

        bands_2025 = build_bands_2025("2025-04-14", "2025-12-31", 1000.0, 1400.0)
        bands_2026 = build_bands_2026(bands_2025, rem, ipc)

        bands = (
            pd.concat([bands_2025, bands_2026], ignore_index=True)
            .dropna(subset=["Date", "lower", "upper"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        fx = fx.copy()
        fx["Date"] = pd.to_datetime(fx["Date"], errors="coerce")
        fx["FX"] = pd.to_numeric(fx["FX"], errors="coerce")
        fx = (
            fx.dropna(subset=["Date", "FX"])
            .drop_duplicates(subset=["Date"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

    #### NUEVO: limpiar mensaje cuando terminó la carga
    fact_ph.empty()
    ####

    if fx.empty:
        st.warning("Sin datos del tipo de cambio.")
        return

    # =========================
    # KPIs
    # =========================
    last_date = pd.to_datetime(fx["Date"].iloc[-1])
    last_fx = float(fx["FX"].iloc[-1])

    fx_m, _ = asof_fx(fx, last_date - pd.Timedelta(days=30))
    fx_y, _ = asof_fx(fx, last_date - pd.Timedelta(days=365))

    vm = None if fx_m is None else (last_fx / fx_m - 1) * 100
    va = None if fx_y is None else (last_fx / fx_y - 1) * 100

    # =========================
    # DF diario histórico (para TODO real)
    # =========================
    fx_min = pd.to_datetime(fx["Date"].min())
    bands_max = pd.to_datetime(bands["Date"].max()) if not bands.empty else last_date
    full_end = max(last_date, bands_max)

    cal = pd.DataFrame({"Date": pd.date_range(fx_min, full_end, freq="D")})

    df = (
        cal.merge(fx, on="Date", how="left")
           .merge(bands, on="Date", how="left")
           .sort_values("Date")
           .reset_index(drop=True)
    )

    # TC sin huecos SOLO hasta el último dato observado (después queda vacío)
    last_fx_date = fx["Date"].max()

    df["FX"] = df["FX"].ffill()
    df.loc[df["Date"] > last_fx_date, "FX"] = np.nan

    # Distancia a banda superior (solo si hay banda en last_date)
    up_row = df.loc[df["Date"] == last_date, "upper"]
    upper_last = float(up_row.iloc[0]) if (not up_row.empty and pd.notna(up_row.iloc[0])) else None

    dist_to_upper = None
    if upper_last is not None and last_fx > 0:
        dist_to_upper = (upper_last / last_fx - 1) * 100

    title_txt = ""
    if dist_to_upper is not None:
        title_txt = f"   El TC se encuentra a {safe_pct(dist_to_upper, 1)} de la banda superior"

    # =========================
    # NUEVO LAYOUT (solo formato)
    # - Header moderno
    # - Selector de rango a la derecha
    # - Gráfico full width (MISMO CONTENIDO, MISMOS EJES)
    # =========================

    # --- fila 1: header + selector rango
    left, right = st.columns([3, 1], vertical_alignment="top")

    with left:
        # chips: signo para flecha
        vm_txt = safe_pct(vm, 1)
        va_txt = safe_pct(va, 1)

        # Determinar flecha por signo (solo estética)
        def _chip_arrow(txt: str):
            if txt is None:
                return "", ""
            t = str(txt).strip()
            if t.startswith("-"):
                return "▼", "down"
            return "▲", "up"

        a1, c1 = _chip_arrow(vm_txt)
        a2, c2 = _chip_arrow(va_txt)

        st.markdown(
            f"""
            <div class="fx-header">
              <div class="fx-title">
                <div class="fx-icon">$↗</div>
                <div>Tipo de cambio</div>
              </div>

              <div class="fx-inline">
                <div class="fx-pair">ARS/USD</div>
                <div class="fx-value">{int(round(last_fx))}</div>
              </div>

              <div class="fx-sub">
                Tipo de cambio oficial mayorista de referencia · Al {last_date.strftime('%d/%m/%Y')}
              </div>

              <div class="fx-chips">
                <div class="fx-chip">
                  <span class="{c1}">{a1}</span>
                  <span><b>{vm_txt}</b> mensual</span>
                </div>
                <div class="fx-chip">
                  <span class="{c2}">{a2}</span>
                  <span><b>{va_txt}</b> interanual</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        # Selector rango (default 1A) - MISMO radio, mismas opciones, misma key
        rango_map = {"6M": 180, "1A": 365, "2A": 365 * 2, "5A": 365 * 5, "TODO": None}

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        rango = st.radio(
            label="",
            options=list(rango_map.keys()),
            index=1,  # 1A por defecto
            horizontal=True,
            label_visibility="collapsed",
            key="fx_rango",
        )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # --- fila 2: gráfico + botón descargar (sin tocar contenido del gráfico)
    # CSV con TC + bandas (igual que antes)
    export = df[["Date", "FX", "lower", "upper"]].copy()
    export = export.rename(
        columns={
            "Date": "date",
            "FX": "tc_mayorista",
            "lower": "banda_inferior",
            "upper": "banda_superior",
        }
    )
    csv_bytes = export.to_csv(index=False).encode("utf-8")
    file_name = f"tc_bandas_{last_date.strftime('%Y-%m-%d')}.csv"

    # --- armado df_plot (MISMA LÓGICA)
    days = rango_map[rango]
    if days is None:
        min_date = fx_min
    else:
        min_date = max(fx_min, last_date - pd.Timedelta(days=days))

    df_plot = df[df["Date"] >= min_date].copy()

    # aire a la derecha (MISMO)
    max_date = pd.to_datetime(df["Date"].max()) + pd.DateOffset(months=1)

    # =========================
    # Gráfico (NO SE TOCA el contenido ni ejes)
    # =========================
    fig = go.Figure()

    # Bandas
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

    # TC
    fig.add_trace(
        go.Scatter(
            x=df_plot["Date"],
            y=df_plot["FX"],
            name="TC mayorista",
            mode="lines",
            connectgaps=True,
            hovertemplate="%{x|%d/%m/%Y}<br>TC mayorista: %{y:.2f}<extra></extra>",
        )
    )

    # ticks en español (MISMO)
    mes_es = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
    }

    # En TODO: etiquetas cada 6 meses; resto cada 2 meses (MISMO)
    tick_freq = "6MS" if rango == "TODO" else "2MS"
    tickvals = pd.date_range(min_date.normalize(), max_date.normalize(), freq=tick_freq)
    ticktext = [f"{mes_es[d.month]} {d.year}" for d in tickvals]

    # Layout (MISMO que tenías; solo afuera movimos el header)
    fig.update_layout(
        hovermode="x",
        height=600,
        margin=dict(l=10, r=10, t=90, b=60),
        showlegend=True,
        title=dict(text=title_txt, x=0, xanchor="left"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=12),
        ),
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

    # Botón descargar (abajo, izquierda) - solo formato alrededor, contenido igual
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
        use_container_width=False,
    )

    st.markdown(
        "<div style='color:#6b7280; font-size:12px; margin-top:6px;'>"
        "Fuente: Banco Central de la República Argentina."
        "</div>",
        unsafe_allow_html=True,
    )

    # =========================================================
    # TIPO DE CAMBIO REAL (ITCRM + bilaterales)
    # =========================================================
    st.divider()
    st.markdown("### 🌍 Tipo de cambio real multilateral y bilaterales")
    st.caption("ITCRM y tipos de cambio reales bilaterales (100=17-dic-15)")

    with st.spinner("Cargando ITCRM..."):
        tcr_long = get_itcrm_excel_long()

    if tcr_long.empty:
        st.warning("Sin datos de ITCRM.")
        return

    # -------------------------
    # Series disponibles
    # -------------------------
    series_all = sorted(tcr_long["Serie"].dropna().unique().tolist())

    default_sel = ["ITCRM"] if "ITCRM" in series_all else ([series_all[0]] if series_all else [])

    # -------------------------
    # Selector de series (1 fila – 4 columnas)
    # -------------------------
    st.markdown("**Seleccionar series**")

    # Usamos los nombres EXACTOS del Excel (incluido el espacio en ITCRM )
    series_focus = ["ITCRM ", "ITCRB Brasil", "ITCRB Estados Unidos", "ITCRB China"]

    cols = st.columns(4)
    sel_series = []

    for col, s in zip(cols, series_focus):
        with col:
            if st.checkbox(
                s,
                value=(s == "ITCRM "),  # default ITCRM (con espacio)
                key=f"itcrm_cb_{s}"
            ):
                sel_series.append(s)

    if not sel_series:
        st.info("Seleccioná al menos una serie para ver el gráfico.")
        return

    # -------------------------
    # Data filtrada
    # -------------------------
    tcr = tcr_long[tcr_long["Serie"].isin(sel_series)].copy().sort_values("Date")

    # Serie principal = primera seleccionada
    main_series = sel_series[0]
    tcr_main = (
        tcr_long[tcr_long["Serie"] == main_series]
        .sort_values("Date")
        .reset_index(drop=True)
    )

    last_tcr_date = pd.to_datetime(tcr_main["Date"].iloc[-1])
    last_tcr_val = float(tcr_main["Value"].iloc[-1])

    # As-of helpers (consistente con TC nominal)
    def asof_value(df_: pd.DataFrame, target_date: pd.Timestamp):
        tt = df_.dropna(subset=["Date", "Value"]).sort_values("Date")
        tt = tt[tt["Date"] <= target_date]
        if tt.empty:
            return None, None
        rr = tt.iloc[-1]
        return float(rr["Value"]), pd.to_datetime(rr["Date"])

    tcr_m, _ = asof_value(tcr_main, last_tcr_date - pd.Timedelta(days=30))
    tcr_y, _ = asof_value(tcr_main, last_tcr_date - pd.Timedelta(days=365))

    vm_tcr = None if tcr_m is None else (last_tcr_val / tcr_m - 1) * 100
    va_tcr = None if tcr_y is None else (last_tcr_val / tcr_y - 1) * 100

    # -------------------------
    # Layout KPI + gráfico
    # -------------------------
    kpi2_col, chart2_col = st.columns([1, 3], vertical_alignment="top")

    with kpi2_col:
        st.markdown(
            f"""
            <div style="font-size:46px; font-weight:800; line-height:1.0;">
              <span style="font-size:16px; font-weight:700; color:#111827;">{main_series}</span>
              {last_tcr_val:.1f}
            </div>
            """.replace(".", ","),
            unsafe_allow_html=True,
        )
        st.caption(f"Fecha: {last_tcr_date.strftime('%d/%m/%Y')}")

        st.markdown(
            f"<div style='font-size:18px; margin-top:14px;'><b>% mensual:</b> {safe_pct(vm_tcr, 1)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:18px; margin-top:8px;'><b>% anual:</b> {safe_pct(va_tcr, 1)}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # CSV export
        export_tcr = (
            tcr.pivot_table(index="Date", columns="Serie", values="Value", aggfunc="last")
            .sort_index()
            .reset_index()
            .rename(columns={"Date": "date"})
        )
        csv_bytes_tcr = export_tcr.to_csv(index=False).encode("utf-8")
        file_name_tcr = f"itcrm_{last_tcr_date.strftime('%Y-%m-%d')}.csv"

        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes_tcr,
            file_name=file_name_tcr,
            mime="text/csv",
            key="dl_itcrm_csv",
        )

    with chart2_col:
        # Selector rango (TODO por default)
        rango_map2 = {"6M": 180, "1A": 365, "2A": 365 * 2, "5A": 365 * 5, "TODO": None}

        rango2 = st.radio(
            label="",
            options=list(rango_map2.keys()),
            index=list(rango_map2.keys()).index("TODO"),
            horizontal=True,
            label_visibility="collapsed",
            key="itcrm_rango",
        )

        days2 = rango_map2[rango2]
        tcr_min = pd.to_datetime(tcr["Date"].min())
        tcr_last = pd.to_datetime(tcr["Date"].max())

        min_date2 = tcr_min if days2 is None else max(tcr_min, tcr_last - pd.Timedelta(days=days2))
        tcr_plot = tcr[tcr["Date"] >= min_date2].copy()

        max_date2 = tcr_last + pd.DateOffset(months=1)

        fig2 = go.Figure()

        for s in sel_series:
            ss = tcr_plot[tcr_plot["Serie"] == s]
            fig2.add_trace(
                go.Scatter(
                    x=ss["Date"],
                    y=ss["Value"],
                    name=s,
                    mode="lines",
                    connectgaps=True,
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:.2f}<extra></extra>",
                )
            )

        mes_es = {
            1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
            7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
        }

        tick_freq2 = "6MS" if rango2 == "TODO" else "2MS"
        tickvals2 = pd.date_range(min_date2.normalize(), max_date2.normalize(), freq=tick_freq2)
        ticktext2 = [f"{mes_es[d.month]} {d.year}" for d in tickvals2]

        fig2.update_layout(
            hovermode="x",
            height=520,
            margin=dict(l=10, r=10, t=30, b=60),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                font=dict(size=12),
            ),
        )

        fig2.update_xaxes(
            title_text="",
            range=[min_date2, max_date2],
            tickmode="array",
            tickvals=tickvals2,
            ticktext=ticktext2,
        )
        fig2.update_yaxes(title_text="")

        st.plotly_chart(fig2, use_container_width=True)

        st.markdown(
            "<div style='color:#6b7280; font-size:12px; margin-top:6px;'>"
            "Fuente: BCRA — ITCRMSerie.xlsx."
            "</div>",
            unsafe_allow_html=True,
        )
