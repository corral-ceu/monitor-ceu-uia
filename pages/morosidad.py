import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ============================================================
# Config
# ============================================================
MORA_PATH  = "assets/mora_por_actividad.xlsx"
COL_SECTOR = "Sector_1_dígito"
COL_ID     = "id"
COL_NOMBRE = "Nombre"
COL_SALDO  = "saldo_total (miles de $)"
COL_IRREG  = "saldo_irregular (miles de $)"
COL_MORA   = "tasa_mora"


# ============================================================
# Loader
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Excluir fila id=0
    if COL_ID in df.columns:
        df = df[pd.to_numeric(df[COL_ID], errors="coerce").fillna(-1) != 0].copy()

    # Excluir Nombre NaN
    if COL_NOMBRE in df.columns:
        df = df[df[COL_NOMBRE].notna()].copy()
        df = df[df[COL_NOMBRE].astype(str).str.strip().str.lower() != "nan"].copy()

    # Normalizar tasa_mora
    if COL_MORA in df.columns:
        def _parse(x):
            try:
                v = float(str(x).replace("%", "").replace(",", ".").strip())
                return v if v > 1 else v * 100
            except:
                return float("nan")
        df[COL_MORA] = df[COL_MORA].apply(_parse)

    for c in [COL_SALDO, COL_IRREG]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if COL_SECTOR in df.columns:
        df[COL_SECTOR] = df[COL_SECTOR].astype(str).str.strip()
        df = df[~df[COL_SECTOR].str.lower().isin(["nan", "none", ""])].copy()

    return df


# ============================================================
# Gráficos
# ============================================================
def _fig_barras_h(title, labels, values, suffix="%"):
    pares = []
    for l, v in zip(labels, values):
        try:
            vf = float(v)
            if not np.isnan(vf):
                pares.append((l, vf))
        except:
            pass
    pares = sorted(pares, key=lambda x: x[1])
    names = [p[0] for p in pares]
    vals  = [p[1] for p in pares]
    n     = len(vals)
    if n == 0:
        return go.Figure()

    maxv = max(abs(v) for v in vals) or 1.0
    azul_osc = (27, 45, 107)
    azul_cla = (173, 198, 230)
    colores  = []
    for i in range(n):
        t = i / max(n - 1, 1)
        r = int(azul_cla[0] + t * (azul_osc[0] - azul_cla[0]))
        g = int(azul_cla[1] + t * (azul_osc[1] - azul_cla[1]))
        b = int(azul_cla[2] + t * (azul_osc[2] - azul_cla[2]))
        colores.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker_color=colores,
        text=[f"{v:.1f}{suffix}".replace(".", ",") for v in vals],
        textposition="outside", textfont=dict(size=11),
        cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:.1f}}{suffix}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13), x=0.01),
        margin=dict(t=40, b=20, l=220, r=70),
        xaxis=dict(range=[0, maxv * 1.18], showgrid=False,
                   showticklabels=False, showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(340, n * 38 + 80),
        showlegend=False, bargap=0.28, dragmode=False,
    )
    return fig


def _fig_scatter(df_in, x_col, y_col, label_col, title):
    fig = go.Figure(go.Scatter(
        x=df_in[x_col], y=df_in[y_col],
        mode="markers+text",
        text=df_in[label_col],
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(color="rgba(27,45,107,0.65)", size=10,
                    line=dict(color="white", width=1)),
        hovertemplate="<b>%{text}</b><br>Saldo: $%{x:,.0f}k<br>Mora: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13), x=0.01),
        height=380,
        margin=dict(t=40, b=50, l=60, r=20),
        xaxis=dict(title="Saldo total (miles de $)", gridcolor="#F0F2F6", tickfont=dict(size=9)),
        yaxis=dict(title="Tasa de mora (%)", gridcolor="#F0F2F6",
                   tickfont=dict(size=9), ticksuffix="%"),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, dragmode=False,
    )
    return fig


# ============================================================
# RENDER
# ============================================================
def render_morosidad(go_to):

    if st.button("← Volver"):
        go_to("home")

    try:
        df = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # Agrupar por sector 1 dígito
    df_g1 = (
        df.groupby(COL_SECTOR, as_index=False)
        .agg(**{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")})
    )
    df_g1[COL_MORA] = df_g1.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )

    # ── TABS ──────────────────────────────────
    tab_total, tab_lupa = st.tabs(["📊 Total por sector", "🔍 Lupa en actividad"])

    # ══════════════════════════════════════════
    # TAB 1 — TOTAL
    # ══════════════════════════════════════════
    with tab_total:

        c1, c2 = st.columns(2, gap="large")
        with c1:
            var_t = st.selectbox(
                "Variable",
                ["Tasa de mora (%)", "Saldo total", "Saldo irregular"],
                key="mora_var_total",
            )

        if var_t == "Tasa de mora (%)":
            labs, vals, suf = df_g1[COL_SECTOR].tolist(), df_g1[COL_MORA].tolist(), "%"
        elif var_t == "Saldo total":
            labs = df_g1[COL_SECTOR].tolist()
            vals = (df_g1[COL_SALDO] / 1_000_000).tolist()
            suf  = "B"
        else:
            labs = df_g1[COL_SECTOR].tolist()
            vals = (df_g1[COL_IRREG] / 1_000_000).tolist()
            suf  = "B"

        with st.container(border=True):
            st.plotly_chart(
                _fig_barras_h(f"{var_t} por sector", labs, vals, suffix=suf),
                use_container_width=True,
                config={"displayModeBar": False},
                key="mora_chart_total_barras",
            )

        with st.container(border=True):
            st.plotly_chart(
                _fig_scatter(
                    df_g1.dropna(subset=[COL_MORA, COL_SALDO]),
                    COL_SALDO, COL_MORA, COL_SECTOR,
                    "Tamaño vs mora — sectores",
                ),
                use_container_width=True,
                config={"displayModeBar": False},
                key="mora_chart_total_scatter",
            )

        st.caption("Fuente: BCRA — Central de deudores del sistema financiero")

    # ══════════════════════════════════════════
    # TAB 2 — LUPA EN ACTIVIDAD
    # ══════════════════════════════════════════
    with tab_lupa:

        c1, c2 = st.columns(2, gap="large")
        with c1:
            sectores_disp = sorted(df[COL_SECTOR].dropna().unique().tolist())
            sector_sel = st.selectbox("Sector", sectores_disp, key="mora_sector_lupa")
        with c2:
            var_l = st.selectbox(
                "Variable",
                ["Tasa de mora (%)", "Saldo total", "Saldo irregular"],
                key="mora_var_lupa",
            )

        df_zoom = df[df[COL_SECTOR] == sector_sel].copy() if sector_sel else pd.DataFrame()

        if not df_zoom.empty:
            df_zoom[COL_MORA] = df_zoom.apply(
                lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100)
                          if r[COL_SALDO] > 0 else float("nan"),
                axis=1,
            )

            if var_l == "Tasa de mora (%)":
                labs_l, vals_l, suf_l = df_zoom[COL_NOMBRE].tolist(), df_zoom[COL_MORA].tolist(), "%"
            elif var_l == "Saldo total":
                labs_l = df_zoom[COL_NOMBRE].tolist()
                vals_l = (df_zoom[COL_SALDO] / 1_000_000).tolist()
                suf_l  = "B"
            else:
                labs_l = df_zoom[COL_NOMBRE].tolist()
                vals_l = (df_zoom[COL_IRREG] / 1_000_000).tolist()
                suf_l  = "B"

            with st.container(border=True):
                st.plotly_chart(
                    _fig_barras_h(f"{var_l} — {sector_sel}", labs_l, vals_l, suffix=suf_l),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="mora_chart_lupa_barras",
                )

            with st.container(border=True):
                st.plotly_chart(
                    _fig_scatter(
                        df_zoom.dropna(subset=[COL_MORA, COL_SALDO]),
                        COL_SALDO, COL_MORA, COL_NOMBRE,
                        f"Tamaño vs mora — {sector_sel}",
                    ),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="mora_chart_lupa_scatter",
                )
        else:
            st.info("No hay datos para el sector seleccionado.")

        st.caption("Fuente: BCRA — Central de deudores del sistema financiero")


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Morosidad – CEU UIA", layout="wide",
                       initial_sidebar_state="collapsed")
    render_morosidad(go_to=None)
