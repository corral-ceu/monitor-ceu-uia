import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel
from services.metrics import calc_var, fmt, obtener_nombre_mes

MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic"]


# =========================
# HELPER SPARKLINE
# =========================
def sparkline_fig(df_serie: pd.DataFrame, height: int = 130):
    if df_serie is None or df_serie.empty:
        return None

    s = df_serie.dropna().sort_values("fecha").tail(24)
    if s.empty:
        return None

    # Labels X en español mmm-yy
    x_lbl = s["fecha"].map(lambda d: f"{MESES_ES[d.month-1]}-{str(d.year)[-2:]}")

    # Y formateado con coma
    y_fmt = s["valor"].map(lambda v: f"{v:.1f}".replace(".", ","))

    # Ticks X (no saturar)
    n_ticks = min(6, len(s))
    tick_idx = np.linspace(0, len(s) - 1, num=n_ticks, dtype=int)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s["fecha"],
            y=s["valor"],
            mode="lines",
            line=dict(width=2),
            customdata=np.column_stack([x_lbl, y_fmt]),
            hovertemplate="%{customdata[0]}: %{customdata[1]}<extra></extra>",
            showlegend=False,
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=55, r=10, t=5, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=",.",  # coma decimal
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=s["fecha"].iloc[tick_idx],
        ticktext=x_lbl.iloc[tick_idx],
        ticks="outside",
        showgrid=False,
        zeroline=False,
        tickfont=dict(size=10),
    )

    fig.update_yaxes(
        ticks="outside",
        showgrid=False,
        zeroline=False,
        tickfont=dict(size=10),
        tickformat=".1f",
    )

    return fig


def _scroll_to_detail_anchor():
    """
    Scroll suave a un ancla dentro del DOM del parent (Streamlit).
    Lo llamamos cuando se renderiza el panel de detalle.
    """
    components.html(
        """
        <script>
          const el = window.parent.document.getElementById("ipi_detalle_panel");
          if (el) el.scrollIntoView({behavior: "smooth", block: "start"});
        </script>
        """,
        height=0,
    )


def render_ipi(go_to):
    # -------------------------
    # Volver
    # -------------------------
    if st.button("← Volver"):
        go_to("home")

    st.markdown("## 🏭 Producción Industrial")
    st.caption("Fuente: INDEC – IPI Manufacturero (Excel)")
    st.divider()

    # -------------------------
    # Session state (robusto)
    # -------------------------
    if "ipi_sel_div" not in st.session_state:
        st.session_state["ipi_sel_div"] = None
    if "ipi_scroll_nonce" not in st.session_state:
        st.session_state["ipi_scroll_nonce"] = 0


    # -------------------------
    # Carga Excel INDEC
    # -------------------------
    df_c2, df_c5 = cargar_ipi_excel()
    if df_c2 is None or df_c5 is None:
        st.error("Error al descargar el archivo del INDEC.")
        return

    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]

    # Nivel general
    ng_sa = procesar_serie_excel(df_c5, 3)
    ng_orig = procesar_serie_excel(df_c2, 3)

    if ng_sa.empty or ng_orig.empty:
        st.warning("No se pudieron extraer series del Excel.")
        return

    m_ng = calc_var(ng_sa["valor"], 1)
    i_ng = calc_var(ng_orig["valor"], 12)

    st.subheader(f"IPI Manufacturero - {obtener_nombre_mes(ng_sa['fecha'].iloc[-1])}")
    m_cols = st.columns(2)
    m_cols[0].metric("Variación Mensual (SA)", f"{fmt(m_ng, 1)}%")
    m_cols[1].metric("Variación Interanual", f"{fmt(i_ng, 1)}%")

    # =========================
    # DIVISIONES INDUSTRIALES
    # =========================
    st.write("#### Divisiones Industriales")

    divs_idxs = [
        i for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    for start in range(0, len(divs_idxs), 3):
        cols = st.columns(3, vertical_alignment="top")

        for j, idx in enumerate(divs_idxs[start:start + 3]):
            name = names_c5[idx]

            s_sa = procesar_serie_excel(df_c5, idx)
            v_m = calc_var(s_sa["valor"], 1) if not s_sa.empty else np.nan

            # Buscar interanual original en c2 por el mismo nombre
            try:
                idx_c2 = names_c2.index(name)
                s_orig = procesar_serie_excel(df_c2, idx_c2)
                v_i = calc_var(s_orig["valor"], 12) if not s_orig.empty else np.nan
                raw_code = codes_c2[idx_c2]
            except Exception:
                v_i = np.nan
                raw_code = None

            arrow = (
                "⬆️" if (pd.notna(v_m) and v_m > 0) else
                ("⬇️" if (pd.notna(v_m) and v_m < 0) else "•")
            )

            fig_sp = sparkline_fig(s_sa)

            with cols[j]:
                st.markdown(
                    f"""
                    <div class="macro-card">
                      <div style="font-weight:800; font-size:16px; margin-bottom:6px;">{name}</div>
                      <div style="display:flex; gap:14px; align-items:baseline; margin-bottom:4px;">
                        <div style="font-size:26px; font-weight:900;">{arrow} {fmt(v_m, 1)}%</div>
                        <div style="font-size:13px; font-weight:700; color:#526484;">Var. Mensual (s.e)</div>
                      </div>
                      <div style="font-size:13px; font-weight:700; color:#526484; margin-bottom:8px;">
                        Interanual:
                        <span style="color:#0b2b4c; font-weight:900;">{fmt(v_i, 1)}%</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if fig_sp is not None:
                    st.plotly_chart(
                        fig_sp,
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )

                # Botón (setea state + rerun para que aparezca el panel)
                if st.button("Ver detalle", key=f"ipi_btn_{idx}", use_container_width=True):
                    if raw_code is None or str(raw_code).strip() == "" or str(raw_code).strip().lower() == "nan":
                        st.warning("No se encontró el código de la división para abrir el detalle.")
                    else:
                        st.session_state["ipi_sel_div"] = (name, str(raw_code).strip())
                        st.session_state["ipi_scroll_nonce"] += 1
                        st.rerun()

    # =========================
    # DETALLE SUBCLASES (PANEL DESTACADO + SCROLL)
    # =========================
    sel = st.session_state.get("ipi_sel_div", None)
    if not sel:
        return  # no hay selección: no mostramos panel

    div_name, div_code = sel

    # Ancla + scroll suave a este panel
    nonce = st.session_state.get("ipi_scroll_nonce", 0)
    anchor_id = f"ipi_detalle_panel_{nonce}"

    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)
    components.html(
    f"""
    <script>
      const el = window.parent.document.getElementById("{anchor_id}");
      if (el) el.scrollIntoView({{behavior: "smooth", block: "start"}});
    </script>
    """,
    height=0,
)

    with st.container(border=True):
        c1, c2 = st.columns([8, 2], vertical_alignment="center")
        with c1:
            st.markdown(f"### 🔎 Detalle por subclases — **{div_name}**")
            st.caption("Variación interanual (serie original). Fuente: INDEC – IPI Manufacturero (Excel)")
        with c2:
            if st.button("✖ Cerrar", key="ipi_close_detail", use_container_width=True):
                st.session_state["ipi_sel_div"] = None
                st.rerun()

        st.divider()

        prefixes = [p.strip() for p in str(div_code).split("-") if p.strip()]
        if "36" in prefixes:
            prefixes.append("33")

        sub_list = []
        for k, code in enumerate(codes_c2):
            code_s = str(code).strip()
            if any(code_s.startswith(p) for p in prefixes) and code_s not in prefixes:
                s = procesar_serie_excel(df_c2, k)
                if not s.empty:
                    sub_list.append({
                        "Subclase": names_c2[k],
                        "Variación Interanual (%)": calc_var(s["valor"], 12),
                    })

        if sub_list:
            df_sub = (
                pd.DataFrame(sub_list)
                .dropna()
                .sort_values("Variación Interanual (%)", ascending=False)
                .reset_index(drop=True)
            )

            st.dataframe(
                df_sub.style.format({"Variación Interanual (%)": "{:,.2f}%"}),
                use_container_width=True,
            )
        else:
            st.info("No hay desglose adicional disponible.")
