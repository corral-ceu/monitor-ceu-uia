import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

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

SECTOR_INDUSTRIA = "Alimentos y bebidas"  # se sobreescribe dinámicamente


# ============================================================
# Loader
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    # Excluir fila id=0 (Otros)
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
# Helper formato
# ============================================================
def fmt_pct(x, dec=1):
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except:
        return "—"


# ============================================================
# Panel celestito (igual que macro_pbi_emae)
# ============================================================
CSS_PANEL = """
<style>
  .fx-panel-wrap {
    background: rgba(230,243,255,0.55);
    border: 1px solid rgba(15,55,100,0.10);
    border-radius: 22px;
    padding: 16px 16px 26px 16px;
    box-shadow: 0 10px 18px rgba(15,55,100,0.06);
    margin-top: 10px;
  }
  .fx-panel-title {
    font-size: 12px; font-weight: 900;
    color: rgba(20,50,79,0.78); margin: 0 0 6px 2px; letter-spacing: 0.01em;
  }
  .fx-panel-gap { height: 16px; }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] {
    background: #0b2a55 !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] * {
    color: #8fc2ff !important; fill: #8fc2ff !important; font-weight: 800 !important;
  }
</style>
"""

def _inject_panel(marker_id: str):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          function apply() {{
            const m = window.parent.document.getElementById('{marker_id}');
            if (!m) return;
            const b = m.closest('div[data-testid="stVerticalBlock"]');
            if (b) b.classList.add('fx-panel-wrap');
          }}
          apply();
          let i=0; const t=setInterval(()=>{{ apply(); if(++i>=10) clearInterval(t); }},150);
          const obs=new MutationObserver(apply);
          obs.observe(window.parent.document.body,{{childList:true,subtree:true}});
          setTimeout(()=>obs.disconnect(),3000);
        }})();
        </script>
        """,
        height=0,
    )


# ============================================================
# Gráfico de barras horizontales
# ============================================================
def _fig_barras_sector(df_g1, variable):
    """Barras horizontales ordenadas de mayor a menor."""

    if variable == "Tasa de mora (%)":
        col_val = COL_MORA
        suf     = "%"
        titulo  = "Tasa de mora por sector (%)"
    elif variable == "Saldo total":
        col_val = "_saldo_bn"
        df_g1   = df_g1.copy()
        df_g1["_saldo_bn"] = df_g1[COL_SALDO] / 1_000_000
        suf     = "B"
        titulo  = "Saldo total por sector (billones de $)"
    else:
        col_val = "_irreg_bn"
        df_g1   = df_g1.copy()
        df_g1["_irreg_bn"] = df_g1[COL_IRREG] / 1_000_000
        suf     = "B"
        titulo  = "Saldo irregular por sector (billones de $)"

    df_plot = df_g1.dropna(subset=[col_val]).sort_values(col_val, ascending=True)
    names   = df_plot[COL_SECTOR].tolist()
    vals    = df_plot[col_val].tolist()
    n       = len(vals)
    if n == 0:
        return go.Figure()

    maxv     = max(abs(v) for v in vals) or 1.0
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
        text=[f"{v:.1f}{suf}".replace(".", ",") for v in vals],
        textposition="outside", textfont=dict(size=11),
        cliponaxis=False,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:.1f}}{suf}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13), x=0.01),
        margin=dict(t=40, b=20, l=260, r=80),
        xaxis=dict(range=[0, maxv * 1.20], showgrid=False,
                   showticklabels=False, showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(360, n * 42 + 80),
        showlegend=False, bargap=0.28, dragmode=False,
    )
    return fig


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def render_morosidad(go_to):

    st.markdown(CSS_PANEL, unsafe_allow_html=True)

    if st.button("← Volver"):
        go_to("home")

    # Cargar y agregar
    try:
        df = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # Agrupación por sector 1 dígito — suma saldo e irregular, ratio para mora
    df_g1 = (
        df.groupby(COL_SECTOR, as_index=False)
        .agg(**{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")})
    )
    df_g1[COL_MORA] = df_g1.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )

    # Mora global (todos los sectores)
    total_saldo = df_g1[COL_SALDO].sum()
    total_irreg = df_g1[COL_IRREG].sum()
    mora_global = (total_irreg / total_saldo * 100) if total_saldo > 0 else float("nan")

    # Mora de industria manufacturera (buscar por substring)
    _ind_mask = df_g1[COL_SECTOR].str.lower().str.contains("industria|manufactur|alimentos", na=False)
    _ind_row  = df_g1[_ind_mask]
    mora_ind  = _ind_row.iloc[0][COL_MORA] if not _ind_row.empty else float("nan")
    ind_label = _ind_row.iloc[0][COL_SECTOR] if not _ind_row.empty else "Industria"

    # ── TAB ───────────────────────────────────
    tab_sectores, tab_lupa = st.tabs(["📊 Morosidad por sectores", "🔍 Lupa en actividad"])

    # ══════════════════════════════════════════
    # TAB 1 — MOROSIDAD POR SECTORES
    # ══════════════════════════════════════════
    with tab_sectores:
        with st.container():
            _inject_panel("mora_sectores_marker")

            # --- Header con datos agregados ---
            st.markdown(
                f"""
                <div style="
                  background: linear-gradient(180deg,#f7fbff 0%,#eef6ff 100%);
                  border:1px solid #dfeaf6; border-radius:18px; padding:14px 18px;
                  box-shadow:0 8px 20px rgba(15,55,100,0.12);
                  display:flex; align-items:center; gap:24px; margin-bottom:4px;
                ">
                  <div style="font-size:32px;">⚠️</div>
                  <div>
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.08em;color:#6b7a99;margin-bottom:4px;">
                      Morosidad del sistema financiero · BCRA
                    </div>
                    <div style="display:flex;gap:28px;align-items:baseline;">
                      <div>
                        <span style="font-size:32px;font-weight:950;color:#14324f;letter-spacing:-0.02em;">
                          {fmt_pct(mora_global)}
                        </span>
                        <span style="font-size:12px;color:#6b7a99;margin-left:6px;">mora global</span>
                      </div>
                      <div style="width:1px;height:32px;background:#dfeaf6;"></div>
                      <div>
                        <span style="font-size:22px;font-weight:800;color:#c0392b;letter-spacing:-0.01em;">
                          {fmt_pct(mora_ind)}
                        </span>
                        <span style="font-size:12px;color:#6b7a99;margin-left:6px;">{ind_label[:30]}</span>
                      </div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            # --- Selector variable ---
            st.markdown("<div class='fx-panel-title'>Variable</div>", unsafe_allow_html=True)
            var_t = st.selectbox(
                "", ["Tasa de mora (%)", "Saldo total", "Saldo irregular"],
                key="mora_var_total", label_visibility="collapsed",
            )

            st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

            with st.container(border=True):
                st.plotly_chart(
                    _fig_barras_sector(df_g1, var_t),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="mora_chart_sectores",
                )

            st.caption("Fuente: BCRA — Central de deudores del sistema financiero")

    # ══════════════════════════════════════════
    # TAB 2 — LUPA (placeholder por ahora)
    # ══════════════════════════════════════════
    with tab_lupa:
        st.info("🚧 Próximamente — zoom por actividad (2 dígitos)")


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(page_title="Morosidad – CEU UIA", layout="wide",
                       initial_sidebar_state="collapsed")
    render_morosidad(go_to=None)
