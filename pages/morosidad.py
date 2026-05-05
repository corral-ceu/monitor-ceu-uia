import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

# ============================================================
# Config
# ============================================================
MORA_PATH       = "assets/mora_por_actividad2.xlsx"
COL_FECHA       = "fecha"
COL_SECTOR      = "Sector_1_dígito"
COL_ID          = "id"
COL_NOMBRE      = "Nombre"
COL_SALDO       = "saldo_total (miles de $)"
COL_IRREG       = "saldo_irregular (miles de $)"
COL_MORA        = "tasa_mora"
ID_IND_MIN      = 101
ID_IND_MAX      = 332
LABEL_IND       = "Industria manufacturera"
LABEL_IND_TOTAL = f"▶ Total {LABEL_IND}"

# columna interna usada en Tab 3 para el eje Y (siempre float limpio)
COL_Y_SERIE = "valor_serie"


# ============================================================
# Loader
# ============================================================
@st.cache_data(show_spinner=False)
def load_mora():
    df = pd.read_excel(MORA_PATH, sheet_name="Monitor", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df[COL_ID] = pd.to_numeric(df[COL_ID], errors="coerce")
    df = df[df[COL_ID].fillna(-1) != 0].copy()
    if COL_NOMBRE in df.columns:
        df = df[df[COL_NOMBRE].notna()].copy()
        df = df[df[COL_NOMBRE].astype(str).str.strip().str.lower() != "nan"].copy()

    def _parse(x):
        try:
            v = float(str(x).replace("%", "").replace(",", ".").strip())
            return v if v > 1 else v * 100
        except Exception:
            return float("nan")

    df[COL_MORA] = df[COL_MORA].apply(_parse)
    for c in [COL_SALDO, COL_IRREG]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[COL_SECTOR] = df[COL_SECTOR].astype(str).str.strip()
    df = df[~df[COL_SECTOR].str.lower().isin(["nan", "none", ""])].copy()
    df[COL_FECHA] = (
        pd.to_numeric(df[COL_FECHA], errors="coerce")
        .astype("Int64")
        .astype(str)
        .str[:6]              # 👈 CLAVE: recorta a AAAAMM
        .astype(int)
    )

    # Último mes → Tab 1 y Tab 2
    ultimo_mes = df[COL_FECHA].max()
    df_last = df[df[COL_FECHA] == ultimo_mes].copy()
    df_ext  = df_last[(df_last[COL_ID] < ID_IND_MIN) | (df_last[COL_ID] > ID_IND_MAX)].copy()
    df_ind  = df_last[(df_last[COL_ID] >= ID_IND_MIN) & (df_last[COL_ID] <= ID_IND_MAX)].copy()

    # Histórico completo → Tab 3
    df_hist = df.copy()

    return df_ext, df_ind, df_hist


# ============================================================
# Helpers generales
# ============================================================
def _agrupar(df_in, col_grupo):
    g = df_in.groupby(col_grupo, as_index=False).agg(
        **{COL_SALDO: (COL_SALDO, "sum"), COL_IRREG: (COL_IRREG, "sum")}
    )
    g[COL_MORA] = g.apply(
        lambda r: (r[COL_IRREG] / r[COL_SALDO] * 100) if r[COL_SALDO] > 0 else float("nan"),
        axis=1,
    )
    return g


def _total_row(df_in, label):
    s = df_in[COL_SALDO].sum()
    i = df_in[COL_IRREG].sum()
    return {
        COL_SECTOR: label,
        COL_SALDO:  s,
        COL_IRREG:  i,
        COL_MORA:   (i / s * 100) if s > 0 else float("nan"),
    }


def fmt_pct(x, dec=1):
    try:
        return f"{float(x):.{dec}f}".replace(".", ",") + "%"
    except Exception:
        return "—"


def fmt_millones(x):
    try:
        v = int(round(float(x)))
        return f"{v:,}".replace(",", ".") + " M"
    except Exception:
        return "—"


def _fecha_label(f):
    """202401 → ene-24"""
    meses = ["ene","feb","mar","abr","may","jun",
             "jul","ago","sep","oct","nov","dic"]
    try:
        f = int(f)
        anio = str(f // 100)[2:]
        mes  = meses[(f % 100) - 1]
        return f"{mes}-{anio}"
    except Exception:
        return str(f)


# ============================================================
# CSS
# ============================================================
CSS = """
<style>
  .mora-hero {
    border-left: 5px solid #1B2D6B;
    border-radius: 0 12px 12px 0;
    padding: 16px 20px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 24px;
    background: rgba(27,45,107,0.06);
  }
  .mora-hero-left { display: flex; flex-direction: column; gap: 2px; }
  .mora-hero-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.10em; color: #6b7a99;
  }
  .mora-hero-value {
    font-size: 44px; font-weight: 900; color: #1B2D6B;
    letter-spacing: -0.03em; line-height: 1;
  }
  .mora-hero-sub { font-size: 11px; color: #9aa3b2; margin-top: 2px; }
  .mora-hero-divider {
    width: 1px; height: 44px;
    background: rgba(27,45,107,0.15); flex-shrink: 0;
  }
  .mora-hero-stat { display: flex; flex-direction: column; gap: 2px; }
  .mora-hero-stat-label {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.10em; color: #9aa3b2;
  }
  .mora-hero-stat-value { font-size: 22px; font-weight: 800; color: #c0392b; }

  .fx-panel-wrap {
    background: rgba(230,243,255,0.55);
    border: 1px solid rgba(15,55,100,0.10);
    border-radius: 22px;
    padding: 14px 16px 22px 16px;
    box-shadow: 0 10px 18px rgba(15,55,100,0.06);
    margin-top: 0px;
  }
  .sel-label {
    font-size: 11px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.10em; color: rgba(20,50,79,0.60);
    margin-bottom: 4px; margin-left: 2px;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] {
    background: #0b2a55 !important;
    border: 1px solid rgba(99,163,255,0.20) !important;
    border-radius: 10px !important;
  }
  .fx-panel-wrap div[data-testid="stSelectbox"] div[role="combobox"] * {
    color: #8fc2ff !important; fill: #8fc2ff !important; font-weight: 700 !important;
  }
  .sel-divider { height: 1px; background: rgba(15,55,100,0.10); margin: 10px 0 12px 0; }
  .mora-caption { font-size: 11px; color: rgba(20,50,79,0.40); margin-top: 8px; }
  .fx-panel-wrap div[data-testid="stTabs"] { margin-top: 0 !important; }
  .fx-panel-wrap button[data-baseweb="tab"] {
    font-size: 13px !important; font-weight: 600 !important; padding: 6px 14px !important;
  }
</style>
"""


# ============================================================
# Panel celestito
# ============================================================
def _inject_panel(marker_id):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""<script>
        (function() {{
          function apply() {{
            const m = window.parent.document.getElementById('{marker_id}');
            if (!m) return;
            const b = m.closest('div[data-testid="stVerticalBlock"]');
            if (b) b.classList.add('fx-panel-wrap');
          }}
          apply();
          let i = 0;
          const t = setInterval(() => {{ apply(); if (++i >= 10) clearInterval(t); }}, 150);
          const obs = new MutationObserver(apply);
          obs.observe(window.parent.document.body, {{childList: true, subtree: true}});
          setTimeout(() => obs.disconnect(), 3000);
        }})();
        </script>""",
        height=0,
    )


# ============================================================
# Gráfico barras horizontales (Tab 1 y Tab 2 — sin cambios)
# ============================================================
def _fig_barras(nombres, valores, sufijo, titulo, bold_label=None):
    pares = [
        (n, float(v)) for n, v in zip(nombres, valores)
        if v is not None and not np.isnan(float(v))
    ]
    pares = sorted(pares, key=lambda x: x[1])
    names = [p[0] for p in pares]
    vals  = [p[1] for p in pares]
    n     = len(vals)
    if n == 0:
        return go.Figure()

    maxv     = max(abs(v) for v in vals) or 1.0
    azul_osc = (27, 45, 107)
    azul_cla = (173, 198, 230)
    rojo     = "rgb(192,57,43)"
    colores  = []
    y_labels = []

    for i, nm in enumerate(names):
        t = i / max(n - 1, 1)
        r = int(azul_cla[0] + t * (azul_osc[0] - azul_cla[0]))
        g = int(azul_cla[1] + t * (azul_osc[1] - azul_cla[1]))
        b = int(azul_cla[2] + t * (azul_osc[2] - azul_cla[2]))
        if bold_label and nm == bold_label:
            colores.append(rojo)
            y_labels.append(f"<b>{nm}</b>")
        else:
            colores.append(f"rgb({r},{g},{b})")
            y_labels.append(nm)

    fig = go.Figure(go.Bar(
        x=vals, y=y_labels, orientation="h",
        marker_color=colores,
        text=[fmt_millones(v) if sufijo == "M" else f"{v:.1f}%".replace(".", ",") for v in vals],
        textposition="outside",
        textfont=dict(size=13, color="#14324f"),
        cliponaxis=False,
        customdata=names,
        hovertemplate=f"<b>%{{customdata}}</b><br>%{{x:.1f}}{sufijo}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13, color="#14324f"), x=0.01),
        margin=dict(t=40, b=20, l=300, r=90),
        xaxis=dict(
            range=[0, maxv * 1.20], showgrid=False,
            showticklabels=False, showline=False, zeroline=False,
        ),
        yaxis=dict(tickfont=dict(size=13, color="#334155"), automargin=True),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(360, n * 44 + 80),
        showlegend=False,
        bargap=0.28,
        dragmode=False,
    )
    return fig


# ============================================================
# Helpers Tab 3
# ============================================================
def _build_series(df_hist, fechas_ord, usar_mm, grupos):
    """
    grupos: lista de (nombre_serie, df_subset)
    Devuelve DataFrame con columnas:
      fecha_ord | fecha_label | nombre_serie | COL_Y_SERIE
    COL_Y_SERIE es siempre float listo para graficar:
      - tasa de mora en % si not usar_mm
      - saldo irregular en millones si usar_mm
    """
    rows = []
    for nombre, df_sub in grupos:
        for f in fechas_ord:
            df_f = df_sub[df_sub[COL_FECHA] == f]
            s    = df_f[COL_SALDO].sum()
            irr  = df_f[COL_IRREG].sum()
            if usar_mm:
                val = irr / 1_000
            else:
                val = (irr / s * 100) if s > 0 else np.nan
            rows.append({
                "fecha_ord":    f,
                "fecha_label":  _fecha_label(f),
                "nombre_serie": nombre,
                COL_Y_SERIE:    val,
            })
    return pd.DataFrame(rows)


def _fig_lineas(df_series, sufijo, titulo):
    if df_series.empty:
        return go.Figure()

    colores_linea = [
        "#1B2D6B", "#c0392b", "#2980b9", "#27ae60", "#8e44ad",
        "#e67e22", "#16a085", "#d35400", "#2c3e50", "#7f8c8d",
    ]

    fig    = go.Figure()
    series = df_series["nombre_serie"].unique()

    for idx, serie in enumerate(series):
        df_s   = df_series[df_series["nombre_serie"] == serie].sort_values("fecha_ord")
        color  = colores_linea[idx % len(colores_linea)]
        es_tot = serie.startswith("Total ")

        hover_fmt = "%{y:.1f}%" if sufijo == "%" else "%{y:,.0f} M"

        fig.add_trace(go.Scatter(
            x=df_s["fecha_label"],
            y=df_s[COL_Y_SERIE],
            mode="lines+markers",
            name=serie,
            line=dict(color=color, width=3 if es_tot else 1.8,
                      dash="solid" if es_tot else "dot"),
            marker=dict(size=6 if es_tot else 4, color=color),
            hovertemplate=f"<b>{serie}</b><br>{hover_fmt}<extra></extra>",
        ))

    tick_suf = "%" if sufijo == "%" else ""

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=13, color="#14324f"), x=0.01),
        margin=dict(t=40, b=40, l=60, r=20),
        xaxis=dict(
            tickfont=dict(size=11, color="#334155"),
            showgrid=False, showline=True,
            linecolor="rgba(15,55,100,0.15)",
        ),
        yaxis=dict(
            tickfont=dict(size=11, color="#334155"),
            ticksuffix=tick_suf,
            showgrid=True,
            gridcolor="rgba(15,55,100,0.08)",
            zeroline=False,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=460,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#334155"),
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="rgba(15,55,100,0.10)",
            borderwidth=1,
        ),
        hovermode="x unified",
        dragmode=False,
    )
    return fig


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def render_morosidad(go_to):

    st.markdown(CSS, unsafe_allow_html=True)

    try:
        df_ext, df_ind, df_hist = load_mora()
    except Exception as e:
        st.error(f"⚠️ No se pudo cargar `{MORA_PATH}`\n\n`{e}`")
        return

    # ── Agregados globales (último mes) ──────────────────────
    df_todo     = pd.concat([df_ext, df_ind], ignore_index=True)
    total_saldo = df_todo[COL_SALDO].sum()
    total_irreg = df_todo[COL_IRREG].sum()
    mora_global = (total_irreg / total_saldo * 100) if total_saldo > 0 else float("nan")

    df_g_ext     = _agrupar(df_ext, COL_SECTOR)
    ind_total    = _total_row(df_ind, LABEL_IND)
    df_g_ind_sub = _agrupar(df_ind, COL_SECTOR)
    mora_ind     = ind_total[COL_MORA]
    df_g1        = pd.concat([df_g_ext, pd.DataFrame([ind_total])], ignore_index=True)

    # ── HERO ─────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="mora-hero">
          <div class="mora-hero-left">
            <div class="mora-hero-label">Morosidad del sistema financiero · BCRA</div>
            <div class="mora-hero-value">{fmt_pct(mora_global)}</div>
            <div class="mora-hero-sub">tasa de irregularidad global · saldo irregular / saldo total</div>
          </div>
          <div class="mora-hero-divider"></div>
          <div class="mora-hero-stat">
            <div class="mora-hero-stat-label">Industria manufacturera</div>
            <div class="mora-hero-stat-value">{fmt_pct(mora_ind)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── PANEL ────────────────────────────────────────────────
    with st.container():
        _inject_panel("mora_panel")

        tab_sectores, tab_lupa, tab_hist = st.tabs([
            "📊 Morosidad por sectores",
            "🔍 Lupa en Industria",
            "📈 Evolución histórica",
        ])

        # ══════════════════════════════════════════════════════
        # TAB 1 — sin cambios
        # ══════════════════════════════════════════════════════
        with tab_sectores:
            opciones_t1 = ["Total sectores"] + sorted(df_g1[COL_SECTOR].tolist())
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='sel-label'>Seleccioná el sector</div>", unsafe_allow_html=True)
                sector_t1 = st.selectbox("", opciones_t1, index=0,
                                         key="t1_sector", label_visibility="collapsed")
            with c2:
                st.markdown("<div class='sel-label'>Seleccioná la medida</div>", unsafe_allow_html=True)
                medida_t1 = st.selectbox("", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
                                         key="t1_medida", label_visibility="collapsed")
            st.markdown("<div class='sel-divider'></div>", unsafe_allow_html=True)

            usar_mm = medida_t1 == "Saldo irregular (en millones de pesos)"
            suf     = "M" if usar_mm else "%"

            if sector_t1 == "Total sectores":
                nombres = df_g1[COL_SECTOR].tolist()
                valores = (df_g1[COL_IRREG] / 1_000).tolist() if usar_mm else df_g1[COL_MORA].tolist()
                bold    = LABEL_IND
                titulo  = f"{'Saldo irregular (M$)' if usar_mm else 'Tasa de irregularidad (%)'} — todos los sectores"
            elif sector_t1 == LABEL_IND:
                tot_val = (ind_total[COL_IRREG] / 1_000) if usar_mm else ind_total[COL_MORA]
                nombres = [f"Total {LABEL_IND}"] + df_g_ind_sub[COL_SECTOR].tolist()
                valores = ([tot_val] + (df_g_ind_sub[COL_IRREG] / 1_000).tolist() if usar_mm
                           else [tot_val] + df_g_ind_sub[COL_MORA].tolist())
                bold    = f"Total {LABEL_IND}"
                titulo  = f"{'Saldo irregular (M$)' if usar_mm else 'Tasa de irregularidad (%)'} — {sector_t1}"
            else:
                df_sub   = df_ext[df_ext[COL_SECTOR] == sector_t1].copy()
                df_sub_g = _agrupar(df_sub, COL_NOMBRE)
                tot      = _total_row(df_sub, f"Total {sector_t1}")
                tot_val  = (tot[COL_IRREG] / 1_000) if usar_mm else tot[COL_MORA]
                nombres  = [f"Total {sector_t1}"] + df_sub_g[COL_NOMBRE].tolist()
                valores  = ([tot_val] + (df_sub_g[COL_IRREG] / 1_000).tolist() if usar_mm
                            else [tot_val] + df_sub_g[COL_MORA].tolist())
                bold     = f"Total {sector_t1}"
                titulo   = f"{'Saldo irregular (M$)' if usar_mm else 'Tasa de irregularidad (%)'} — {sector_t1}"

            with st.container(border=True):
                st.plotly_chart(_fig_barras(nombres, valores, suf, titulo, bold_label=bold),
                                use_container_width=True, config={"displayModeBar": False}, key="t1_chart")
            st.markdown("<div class='mora-caption'>Fuente: BCRA — Central de deudores del sistema financiero</div>",
                        unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════
        # TAB 2 — sin cambios
        # ══════════════════════════════════════════════════════
        with tab_lupa:
            subsectores_ind = sorted(df_g_ind_sub[COL_SECTOR].tolist())
            opciones_t2     = [LABEL_IND_TOTAL] + subsectores_ind
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='sel-label'>Seleccioná el sector industrial</div>", unsafe_allow_html=True)
                subsector_t2 = st.selectbox("", opciones_t2, index=0,
                                            key="t2_subsector", label_visibility="collapsed")
            with c2:
                st.markdown("<div class='sel-label'>Seleccioná la medida</div>", unsafe_allow_html=True)
                medida_t2 = st.selectbox("", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
                                         key="t2_medida", label_visibility="collapsed")
            st.markdown("<div class='sel-divider'></div>", unsafe_allow_html=True)

            usar_mm2 = medida_t2 == "Saldo irregular (en millones de pesos)"
            suf2     = "M" if usar_mm2 else "%"

            if subsector_t2 == LABEL_IND_TOTAL:
                tot_val2 = (ind_total[COL_IRREG] / 1_000) if usar_mm2 else ind_total[COL_MORA]
                nombres2 = [f"Total {LABEL_IND}"] + df_g_ind_sub[COL_SECTOR].tolist()
                valores2 = ([tot_val2] + (df_g_ind_sub[COL_IRREG] / 1_000).tolist() if usar_mm2
                            else [tot_val2] + df_g_ind_sub[COL_MORA].tolist())
                bold2    = f"Total {LABEL_IND}"
                titulo2  = f"{'Saldo irregular (M$)' if usar_mm2 else 'Tasa de irregularidad (%)'} — {LABEL_IND}"
            else:
                df_sub2  = df_ind[df_ind[COL_SECTOR] == subsector_t2].copy()
                df_sub2g = _agrupar(df_sub2, COL_NOMBRE)
                tot2     = _total_row(df_sub2, f"Total {subsector_t2}")
                tot2_val = (tot2[COL_IRREG] / 1_000) if usar_mm2 else tot2[COL_MORA]
                nombres2 = [f"Total {subsector_t2}"] + df_sub2g[COL_NOMBRE].tolist()
                valores2 = ([tot2_val] + (df_sub2g[COL_IRREG] / 1_000).tolist() if usar_mm2
                            else [tot2_val] + df_sub2g[COL_MORA].tolist())
                bold2    = f"Total {subsector_t2}"
                titulo2  = f"{'Saldo irregular (M$)' if usar_mm2 else 'Tasa de irregularidad (%)'} — {subsector_t2}"

            with st.container(border=True):
                st.plotly_chart(_fig_barras(nombres2, valores2, suf2, titulo2, bold_label=bold2),
                                use_container_width=True, config={"displayModeBar": False}, key="t2_chart")
            st.markdown("<div class='mora-caption'>Fuente: BCRA — Central de deudores del sistema financiero</div>",
                        unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════
        # TAB 3 — EVOLUCIÓN HISTÓRICA
        # ══════════════════════════════════════════════════════
        with tab_hist:

            fechas_ord  = sorted(df_hist[COL_FECHA].dropna().unique())
            df_hist_ext = df_hist[(df_hist[COL_ID] < ID_IND_MIN) | (df_hist[COL_ID] > ID_IND_MAX)].copy()
            df_hist_ind = df_hist[(df_hist[COL_ID] >= ID_IND_MIN) & (df_hist[COL_ID] <= ID_IND_MAX)].copy()

            sectores_hist = sorted(df_hist_ext[COL_SECTOR].dropna().unique().tolist())
            opciones_t3   = ["Total sistema"] + sectores_hist + [LABEL_IND]

            # Fila 1 de selectores
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("<div class='sel-label'>Seleccioná el sector</div>", unsafe_allow_html=True)
                sector_t3 = st.selectbox("", opciones_t3, index=0,
                                         key="t3_sector", label_visibility="collapsed")
            with c2:
                st.markdown("<div class='sel-label'>Seleccioná la medida</div>", unsafe_allow_html=True)
                medida_t3 = st.selectbox("", ["Tasa de irregularidad", "Saldo irregular (en millones de pesos)"],
                                         key="t3_medida", label_visibility="collapsed")

            usar_mm3 = medida_t3 == "Saldo irregular (en millones de pesos)"
            suf3     = "M" if usar_mm3 else "%"

            # Selector condicional de subsector
            subsector_t3 = None
            subind_t3    = None

            if sector_t3 != "Total sistema":
                st.markdown("<div class='sel-divider'></div>", unsafe_allow_html=True)
                c3, _ = st.columns([1, 1], gap="large")

                if sector_t3 == LABEL_IND:
                    subsectores_ind_hist = sorted(df_hist_ind[COL_SECTOR].dropna().unique().tolist())
                    with c3:
                        st.markdown("<div class='sel-label'>Seleccioná el subsector industrial</div>",
                                    unsafe_allow_html=True)
                        subind_t3 = st.selectbox(
                            "", [f"▶ Total {LABEL_IND}"] + subsectores_ind_hist,
                            index=0, key="t3_subind", label_visibility="collapsed",
                        )
                else:
                    df_sector_hist      = df_hist_ext[df_hist_ext[COL_SECTOR] == sector_t3]
                    subsectores_nombres = sorted(df_sector_hist[COL_NOMBRE].dropna().unique().tolist())
                    with c3:
                        st.markdown("<div class='sel-label'>Seleccioná el subsector</div>",
                                    unsafe_allow_html=True)
                        subsector_t3 = st.selectbox(
                            "", [f"▶ Total {sector_t3}"] + subsectores_nombres,
                            index=0, key="t3_subsector", label_visibility="collapsed",
                        )

            st.markdown("<div class='sel-divider'></div>", unsafe_allow_html=True)

            # Construir grupos
            grupos3 = []

            if sector_t3 == "Total sistema":
                grupos3 = [("Total sistema", df_hist)]

            elif sector_t3 == LABEL_IND:
                if subind_t3 is None or subind_t3 == f"▶ Total {LABEL_IND}":
                    grupos3 = [(f"Total {LABEL_IND}", df_hist_ind)]
                else:
                    grupos3 = [
                        (f"Total {LABEL_IND}", df_hist_ind),
                        (subind_t3, df_hist_ind[df_hist_ind[COL_SECTOR] == subind_t3]),
                    ]

            else:
                df_sector_hist = df_hist_ext[df_hist_ext[COL_SECTOR] == sector_t3]
                if subsector_t3 is None or subsector_t3 == f"▶ Total {sector_t3}":
                    grupos3 = [(f"Total {sector_t3}", df_sector_hist)]
                else:
                    grupos3 = [
                        (f"Total {sector_t3}", df_sector_hist),
                        (subsector_t3, df_sector_hist[df_sector_hist[COL_NOMBRE] == subsector_t3]),
                    ]

            df_series3 = _build_series(df_hist, fechas_ord, usar_mm3, grupos3)
            titulo3    = (
                f"{'Saldo irregular (M$)' if usar_mm3 else 'Tasa de irregularidad (%)'}"
                f" — {sector_t3}"
            )

            with st.container(border=True):
                st.plotly_chart(
                    _fig_lineas(df_series3, suf3, titulo3),
                    use_container_width=True,
                    config={"displayModeBar": False},
                    key="t3_chart",
                )

            st.markdown(
                "<div class='mora-caption'>Fuente: BCRA — Central de deudores del sistema financiero</div>",
                unsafe_allow_html=True,
            )


# ============================================================
# Standalone
# ============================================================
if __name__ == "__main__":
    st.set_page_config(
        page_title="Morosidad – CEU UIA",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_morosidad(go_to=None)
