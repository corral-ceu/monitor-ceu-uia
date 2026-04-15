import textwrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from services.metrics import calc_var, fmt, obtener_nombre_mes
from services.sipa_data import cargar_sipa_excel


# ============================================================
# Helpers de formato
# ============================================================
def _fmt_pct_es(x, dec: int = 1) -> str:
    try:
        return f"{float(x):.{dec}f}".replace(".", ",")
    except Exception:
        return "—"


def _fmt_abs_es(x, dec: int = 0) -> str:
    """Número absoluto con separador de miles, sin signo."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    try:
        return f"{abs(float(x)):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def _fmt_delta_es(x, dec: int = 0) -> str:
    """Número con signo + separador de miles."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    try:
        s = f"{abs(float(x)):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"+{s}" if float(x) >= 0 else f"-{s}"
    except Exception:
        return "—"


def _num_cls(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "t-neu"
    return "t-pos" if float(x) >= 0 else "t-neg"


def _arrow_cls(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ("", "")
    return ("▲", "fx-up") if v >= 0 else ("▼", "fx-down")
def _calc_yoy_by_date(fechas: pd.Series, serie: pd.Series) -> float:
    df = pd.DataFrame({
        "fecha": pd.to_datetime(fechas),
        "valor": pd.to_numeric(serie, errors="coerce")
    }).dropna().sort_values("fecha")

    if df.empty:
        return np.nan

    fecha_actual = df["fecha"].iloc[-1]
    fecha_prev   = fecha_actual - pd.DateOffset(years=1)

    prev = df.loc[df["fecha"] == fecha_prev, "valor"]
    if prev.empty or prev.iloc[0] == 0:
        return np.nan

    val_actual = df["valor"].iloc[-1]
    return ((val_actual / prev.iloc[0]) - 1) * 100


def _calc_yoy_diff_by_date(fechas: pd.Series, serie: pd.Series, scale: int = 1) -> float:
    df = pd.DataFrame({
        "fecha": pd.to_datetime(fechas),
        "valor": pd.to_numeric(serie, errors="coerce")
    }).dropna().sort_values("fecha")

    if df.empty:
        return np.nan

    fecha_actual = df["fecha"].iloc[-1]
    fecha_prev   = fecha_actual - pd.DateOffset(years=1)

    prev = df.loc[df["fecha"] == fecha_prev, "valor"]
    if prev.empty:
        return np.nan

    val_actual = df["valor"].iloc[-1]
    return (val_actual - prev.iloc[0]) * scale

# ============================================================
# CSS
# ============================================================
def _inject_css():
    st.markdown(
        textwrap.dedent("""
        <style>
          /* ===== HEADER WRAPPER ===== */
          .fx-wrap {
            background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
            border: 1px solid #dfeaf6;
            border-radius: 22px;
            padding: 12px;
            box-shadow: 0 10px 24px rgba(15,55,100,0.16),
                        inset 0 0 0 1px rgba(255,255,255,0.55);
          }
          .fx-title-row {
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 8px; padding-left: 4px;
          }
          .fx-icon-badge {
            width: 64px; height: 52px; border-radius: 14px;
            background: linear-gradient(180deg,#e7eef6 0%,#dfe7f1 100%);
            border: 1px solid rgba(15,23,42,0.10);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 14px rgba(15,55,100,0.12);
            font-size: 32px; flex: 0 0 auto;
          }
          .fx-title {
            font-size: 23px; font-weight: 900;
            letter-spacing: -0.01em; color: #14324f; line-height: 1.0;
          }
          .fx-subtitle {
            font-size: 13px; font-weight: 700;
            color: rgba(20,50,79,0.65); margin-top: 3px;
          }
          .fx-report a {
            display: inline-block; padding: 6px 10px;
            border-radius: 999px; border: 1px solid #e5e7eb;
            background: #fff; color: #0f172a;
            font-size: 12px; font-weight: 700; text-decoration: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.06); white-space: nowrap;
          }
          /* ===== KPI CARD ===== */
          .fx-card {
            background: rgba(255,255,255,0.94);
            border: 1px solid rgba(15,23,42,0.10);
            border-radius: 18px; padding: 18px 18px 14px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.10);
          }
          .fx-kpi-grid {
            display: grid; grid-template-columns: 1fr 1fr 1fr;
            gap: 20px; align-items: start;
          }
          .fx-kpi-label { font-size: 13px; font-weight: 800; color: #526484; margin-bottom: 4px; }
          .fx-value {
            font-size: 46px; font-weight: 950;
            letter-spacing: -0.02em; color: #14324f; line-height: 0.95;
          }
          .fx-badge {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 5px 11px; border-radius: 999px;
            border: 1px solid rgba(15,23,42,0.10);
            font-size: 13px; font-weight: 800; margin-top: 7px;
          }
          .fx-badge.green { background: rgba(22,163,74,0.08); color: #168a3a; }
          .fx-badge.red   { background: rgba(220,38,38,0.07); color: #cc2e2e; }
          .fx-badge.neu   { background: rgba(100,116,139,0.08); color: #526484; }
          .fx-up   { color: #168a3a; font-weight: 900; }
          .fx-down { color: #cc2e2e; font-weight: 900; }
          .fx-divider { height: 1px; background: rgba(15,55,100,0.08); margin: 14px 0 0; }
          .fx-note { font-size: 11px; color: rgba(20,50,79,0.55); margin-top: 10px; }
          /* ===== PANEL WRAP ===== */
          .fx-panel-wrap {
            background: rgba(230,243,255,0.55);
            border: 1px solid rgba(15,55,100,0.10);
            border-radius: 22px; padding: 16px 16px 26px;
            box-shadow: 0 10px 18px rgba(15,55,100,0.06);
            margin-top: 10px;
          }
          .fx-panel-gap { height: 16px; }

          /* ===== TABLA SECTORES (estilo imagen CEU-UIA) ===== */
          .emp-table-wrap {
            background: #fff;
            border: 1px solid #dde6f0;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(15,55,100,0.08);
          }
          .emp-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
          }
          /* fila de grupo de columnas */
          .emp-table thead tr.row-group th {
            background: #1a3a5c;
            color: #fff;
            font-weight: 800;
            font-size: 12px;
            padding: 7px 10px;
            text-align: center;
            border-right: 1px solid rgba(255,255,255,0.15);
            line-height: 1.35;
          }
          .emp-table thead tr.row-group th:first-child { text-align: left; }
          .emp-table thead tr.row-group th span { color: #fff; font-weight: 500; font-size: 10.5px; opacity: .8; }
          .th-sub { color: #fff !important; font-weight: 500; font-size: 10.5px; opacity: .8; display: block; }
          /* fila sub (Asalariados / %) */
          .emp-table thead tr.row-sub th {
            background: #2563a8;
            color: #cde4ff;
            font-weight: 700;
            font-size: 11px;
            padding: 6px 10px;
            text-align: right;
            border-right: 1px solid rgba(255,255,255,0.12);
          }
          .emp-table thead tr.row-sub th:first-child { text-align: left; }
          /* filas de datos */
          .emp-table tbody tr {
            border-bottom: 1px solid #eaf0f8;
            transition: background .12s;
          }
          .emp-table tbody tr:hover { background: #f4f8fd; }
          .emp-table tbody tr:last-child { border-bottom: none; }
          /* fila TOTAL */
          .emp-table tbody tr.row-total td {
            background: #1a3a5c;
            color: #fff;
            font-weight: 800;
            border-bottom: none;
          }
          .emp-table tbody tr.row-total td.t-pos { color: #6ee7b7 !important; }
          .emp-table tbody tr.row-total td.t-neg { color: #fca5a5 !important; }
          .emp-table td {
            padding: 6px 10px;
            vertical-align: middle;
          }
          .emp-table td:first-child {
            font-weight: 600; color: #1e3a5f;
            text-align: left; min-width: 160px;
          }
          .emp-table td:not(:first-child) { text-align: right; }
          /* separador entre grupos */
          .emp-table td.col-sep, .emp-table th.col-sep {
            border-left: 2px solid #dde6f0;
          }
          .emp-table tbody tr.row-total td.col-sep {
            border-left: 2px solid rgba(255,255,255,0.20);
          }
          /* colores de valores */
          .t-pos { color: #16a34a; font-weight: 700; }
          .t-neg { color: #e11d48; font-weight: 700; }
          .t-neu { color: #64748b; }

          @media (max-width: 900px) {
            .fx-kpi-grid { grid-template-columns: 1fr; gap: 14px; }
            .emp-table { font-size: 11px; }
            .emp-table td, .emp-table th { padding: 6px 6px; }
          }
        </style>
        """),
        unsafe_allow_html=True,
    )


def _apply_panel_wrap(marker_id: str):
    st.markdown(f"<span id='{marker_id}'></span>", unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          function applyPanelClass() {{
            const marker = window.parent.document.getElementById('{marker_id}');
            if (!marker) return;
            const block = marker.closest('div[data-testid="stVerticalBlock"]');
            if (block) block.classList.add('fx-panel-wrap');
          }}
          applyPanelClass();
          let tries = 0;
          const t = setInterval(() => {{ applyPanelClass(); tries++; if (tries >= 10) clearInterval(t); }}, 150);
          const obs = new MutationObserver(() => applyPanelClass());
          obs.observe(window.parent.document.body, {{ childList: true, subtree: true }});
          setTimeout(() => obs.disconnect(), 3000);
        }})();
        </script>
        """,
        height=0,
    )


# ============================================================
# Bloque KPI principal (Total o Industria)
# ============================================================
def _render_kpi_block(title, subtitle, icon, mes_txt, m_e, m_p, i_e, i_p, v23_pct, v23_p, report_url=None):
    def _bc(x):
        if x is None or (isinstance(x, float) and np.isnan(x)): return "neu"
        return "green" if float(x) >= 0 else "red"
    def _ar(x):
        if x is None or (isinstance(x, float) and np.isnan(x)): return "→"
        return "▲" if float(x) >= 0 else "▼"
    def _ps(x):
        return f"{_fmt_pct_es(x, 1)}%" if x is not None and not (isinstance(x, float) and np.isnan(x)) else "—"

    rep = (f'<div class="fx-report"><a href="{report_url}" target="_blank">📄 Ver último Informe</a></div>'
           if report_url else "")

    html = (
        f'<div class="fx-wrap">'
        f'<div class="fx-title-row" style="justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'<div class="fx-icon-badge">{icon}</div>'
        f'<div>'
        f'<div class="fx-title">{title}</div>'
        f'<div class="fx-subtitle">{subtitle} · {mes_txt}</div>'
        f'</div></div>'
        f'{rep}'
        f'</div>'
        f'<div class="fx-card">'
        f'<div class="fx-kpi-grid">'
        f'<div>'
        f'<div class="fx-kpi-label">Mensual (s.e.)</div>'
        f'<div class="fx-value">{_ps(m_e)}</div>'
        f'<div class="fx-badge {_bc(m_e)}">{_ar(m_e)} {_fmt_delta_es(m_p, 0)} puestos</div>'
        f'</div>'
        f'<div>'
        f'<div class="fx-kpi-label">Interanual</div>'
        f'<div class="fx-value">{_ps(i_e)}</div>'
        f'<div class="fx-badge {_bc(i_e)}">{_ar(i_e)} {_fmt_delta_es(i_p, 0)} puestos</div>'
        f'</div>'
        f'<div>'
        f'<div class="fx-kpi-label">vs Agosto 2023</div>'
        f'<div class="fx-value">{_ps(v23_pct)}</div>'
        f'<div class="fx-badge {_bc(v23_pct)}">{_ar(v23_pct)} {_fmt_delta_es(v23_p, 0)} puestos</div>'
        f'</div>'
        f'</div>'
        f'<div class="fx-divider"></div>'
        f'<div class="fx-note">Nota: (s.e.) = sin estacionalidad. Fuente: SIPA.</div>'
        f'</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# Tabla estilizada  (reemplaza las cards)
# rows: list of dicts con claves:
#   name, abs_val, m_p, m_e, i_p, i_e, v23_p, v23_e, is_total (opt)
# mes_label: str  p.ej. "nov-25"
# ============================================================
def _render_sector_table(rows: list, mes_label: str = ""):
    def _td(val_str, cls="", sep=False):
        sep_cls = " col-sep" if sep else ""
        return f'<td class="{cls}{sep_cls}">{val_str}</td>'

    hdr = (
        '<div class="emp-table-wrap">'
        '<table class="emp-table">'
        '<thead>'
        '<tr class="row-group">'
        f'<th rowspan="2">Sector</th>'
        f'<th rowspan="2" class="col-sep" style="text-align:center;">Empleo<br>registrado<br>{mes_label}</th>'
        '<th colspan="2" class="col-sep">Variación mensual<br><span class="th-sub">(sin estacionalidad)</span></th>'
        '<th colspan="2" class="col-sep">Variación interanual</th>'
        '<th colspan="2" class="col-sep">VS Agosto 2023<br><span class="th-sub">(Máximo anterior)</span></th>'
        '</tr>'
        '<tr class="row-sub">'
        '<th class="col-sep">Asalariados</th><th>%</th>'
        '<th class="col-sep">Asalariados</th><th>%</th>'
        '<th class="col-sep">Asalariados</th><th>%</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
    )

    body = ""
    for r in rows:
        is_total = r.get("is_total", False)
        tr_cls   = ' class="row-total"' if is_total else ""

        nan_safe = lambda v: v is not None and not (isinstance(v, float) and np.isnan(v))

        abs_s  = _fmt_abs_es(r.get("abs_val"))
        mp_s   = _fmt_delta_es(r.get("m_p"))
        me_s   = (_fmt_pct_es(r.get("m_e")) + "%") if nan_safe(r.get("m_e")) else "—"
        ip_s   = _fmt_delta_es(r.get("i_p"))
        ie_s   = (_fmt_pct_es(r.get("i_e")) + "%") if nan_safe(r.get("i_e")) else "—"
        v23p_s = _fmt_delta_es(r.get("v23_p"))
        v23e_s = (_fmt_pct_es(r.get("v23_e")) + "%") if nan_safe(r.get("v23_e")) else "—"

        mc   = _num_cls(r.get("m_e"))
        ic   = _num_cls(r.get("i_e"))
        v23c = _num_cls(r.get("v23_e"))

        body += (
            f'<tr{tr_cls}>'
            f'<td style="text-align:left;font-weight:{"800" if is_total else "600"}">{r["name"]}</td>'
            + _td(abs_s, sep=True)
            + _td(mp_s,   mc,   sep=True)
            + _td(me_s,   mc)
            + _td(ip_s,   ic,   sep=True)
            + _td(ie_s,   ic)
            + _td(v23p_s, v23c, sep=True)
            + _td(v23e_s, v23c)
            + '</tr>'
        )

    st.markdown(hdr + body + '</tbody></table></div>', unsafe_allow_html=True)


# ============================================================
# Gráfico de línea — serie s.e.
# ============================================================
MESES_ES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun",
                  "jul", "ago", "sep", "oct", "nov", "dic"]


def _render_empleo_chart(serie: pd.Series, fechas: pd.Series, titulo: str, chart_key: str, scale: int = 1):
    df_plot = (
        pd.DataFrame({"fecha": pd.to_datetime(fechas), "valor": serie * scale})
        .dropna()
        .sort_values("fecha")
        .reset_index(drop=True)
    )
    if df_plot.empty:
        st.info("No hay datos para graficar.")
        return

    # ── selector de rango ────────────────────────────────────
    fecha_min = df_plot["fecha"].min().date()
    fecha_max = df_plot["fecha"].max().date()
    meses_disp = pd.date_range(
        pd.Timestamp(fecha_min).to_period("M").to_timestamp(),
        pd.Timestamp(fecha_max).to_period("M").to_timestamp(),
        freq="MS",
    )
    meses_d = [m.date() for m in meses_disp]

    try:
        default_start = (pd.Timestamp(fecha_max) - pd.DateOffset(years=6)).date()
        default_start = max(default_start, meses_d[0])
    except Exception:
        default_start = meses_d[0]

    rng_start, rng_end = st.select_slider(
        "",
        options=meses_d,
        value=(default_start, meses_d[-1]),
        format_func=lambda d: f"{MESES_ES_CORTO[pd.Timestamp(d).month-1]}-{str(pd.Timestamp(d).year)[2:]}",
        label_visibility="collapsed",
        key=f"{chart_key}_slider",
    )

    # filtrar al rango seleccionado
    rng_start_ts = pd.Timestamp(rng_start)
    rng_end_ts   = pd.Timestamp(rng_end)
    df_vis = df_plot[(df_plot["fecha"] >= rng_start_ts) & (df_plot["fecha"] <= rng_end_ts)].copy()

    if df_vis.empty:
        st.warning("No hay datos en el rango seleccionado.")
        return

    # ── ticks manuales en español: cada enero + cada julio ──
    tick_dates, tick_labels = [], []
    for dt in pd.date_range(rng_start_ts, rng_end_ts, freq="MS"):
        if dt.month in (1, 7):
            tick_dates.append(dt)
            tick_labels.append(f"{MESES_ES_CORTO[dt.month-1]}-{str(dt.year)[2:]}")

    # ── hover label en español ───────────────────────────────
    df_vis["hover_label"] = df_vis["fecha"].apply(
        lambda d: f"{MESES_ES_CORTO[d.month-1]}-{str(d.year)[2:]}"
    )

    # ── eje Y: rango ajustado con margen del 5% ──────────────
    y_min = df_vis["valor"].min()
    y_max = df_vis["valor"].max()
    y_pad = (y_max - y_min) * 0.08
    y_range = [y_min - y_pad, y_max + y_pad]

    # separador de miles con punto
    def _fmt_tick(v):
        return f"{v:,.0f}".replace(",", ".")

    y_ticks_raw = pd.Series(
        range(int(round(y_min - y_pad, -3)), int(round(y_max + y_pad, -3)) + 1, 50_000)
    )
    y_ticks = y_ticks_raw.tolist()
    y_labels = [_fmt_tick(v) for v in y_ticks]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_vis["fecha"],
            y=df_vis["valor"],
            mode="lines",
            line=dict(color="#2563a8", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(37,99,168,0.07)",
            customdata=df_vis["hover_label"],
            hovertemplate="%{customdata}<br><b>%{y:,.0f}</b> asalariados<extra></extra>".replace(",", "."),
        )
    )

    # línea de referencia ago-23
    ref_date = pd.Timestamp("2023-08-01")
    ref_row = df_plot[df_plot["fecha"] == ref_date]
    if not ref_row.empty and rng_start_ts <= ref_date <= rng_end_ts:
        ref_val = float(ref_row["valor"].iloc[0])
        fig.add_hline(
            y=ref_val,
            line_dash="dot",
            line_color="rgba(220,38,38,0.55)",
            line_width=1.5,
            annotation_text="ago-23",
            annotation_font_size=10,
            annotation_font_color="rgba(220,38,38,0.8)",
            annotation_position="bottom right",
        )

    x_max_pad = rng_end_ts + pd.DateOffset(months=1)

    fig.update_layout(
        height=300,
        margin=dict(l=10, r=20, t=10, b=10),
        hovermode="x unified",
        showlegend=False,
        dragmode=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            tickvals=y_ticks,
            ticktext=y_labels,
            range=y_range,
            gridcolor="rgba(15,55,100,0.08)",
            zeroline=False,
            tickfont=dict(size=11, color="#526484"),
        ),
        xaxis=dict(
            tickvals=tick_dates,
            ticktext=tick_labels,
            tickfont=dict(size=10, color="#526484"),
            tickangle=-90,
            gridcolor="rgba(15,55,100,0.05)",
            range=[rng_start_ts, x_max_pad],
        ),
    )

    st.markdown(
        f"<div style='font-size:12px;font-weight:800;color:#526484;margin:14px 0 4px 2px;'>"
        f"{titulo}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
        key=chart_key,
    )


# ============================================================
# Main
# ============================================================
def render_empleo(go_to):
    _inject_css()

    if st.button("← Volver"):
        go_to("home")

    with st.spinner("Cargando SIPA..."):
        df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa = cargar_sipa_excel()

    if df_total.empty:
        st.error("No se pudieron cargar los datos SIPA desde el Excel.")
        return

    target_date = pd.Timestamp("2023-08-01")
    ult_f       = df_total["fecha"].iloc[-1]
    mes_txt     = obtener_nombre_mes(ult_f)
    MESES_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic"
}

    mes_label = f"{MESES_ES[ult_f.month]}-{str(ult_f.year)[-2:]}"

    s_orig = df_total["orig"]
    s_sa   = df_total["sa"]

    try:
        scale = 1000 if pd.to_numeric(s_sa.dropna()).median() < 1_000_000 else 1
    except Exception:
        scale = 1000

    # ── KPIs totales ──
    m_e  = calc_var(s_sa, 1)
    m_p  = s_sa.diff().iloc[-1] * scale
    i_e  = _calc_yoy_by_date(df_total["fecha"], s_orig)
    i_p  = _calc_yoy_diff_by_date(df_total["fecha"], s_orig, scale=scale)

    try:
        val_23  = df_total.loc[df_total["fecha"] == target_date, "sa"].iloc[0]
        v23_pct = ((s_sa.iloc[-1] / val_23) - 1) * 100 if val_23 != 0 else np.nan
        v23_p   = (s_sa.iloc[-1] - val_23) * scale
    except Exception:
        v23_pct = v23_p = np.nan

    INFORME_URL = "https://uia.org.ar/centro-de-estudios/documentos/actualidad-industrial/?q=Laborales"

    # =========================================================
    # BLOQUE 1 — Total empleo privado registrado
    # =========================================================
    with st.container():
        _apply_panel_wrap("emp_total_marker")
        _render_kpi_block(
            title="Empleo Privado Registrado", subtitle="Total", icon="💼",
            mes_txt=mes_txt, m_e=m_e, m_p=m_p, i_e=i_e, i_p=i_p,
            v23_pct=v23_pct, v23_p=v23_p, report_url=INFORME_URL,
        )

    # =========================================================
    # BLOQUE 2 — Sectores generales
    # =========================================================
    st.divider()

    if df_sec_orig.empty or df_sec_sa.empty:
        st.warning("No se pudieron leer las hojas de sectores.")
        return

    sectores = [c for c in df_sec_orig.columns if c != "fecha"]
    tmp_sec  = (df_sec_orig
                .merge(df_sec_sa, on="fecha", how="inner", suffixes=("_orig", "_sa"))
                .sort_values("fecha"))

    sector_rows = []
    ind_data    = None

    for sec in sectores:
        # excluir filas de total que vienen en los datos
        if "total" in sec.lower():
            continue

        col_o = f"{sec}_orig"
        col_s = f"{sec}_sa"
        if col_o not in tmp_sec.columns or col_s not in tmp_sec.columns:
            continue

        ss_orig = tmp_sec[col_o]
        ss_sa   = tmp_sec[col_s]

        if "industria" in sec.lower():
            ind_data = {"orig": ss_orig, "sa": ss_sa, "name": sec, "tmp": tmp_sec}

        abs_val = ss_orig.iloc[-1] * scale if not ss_orig.empty else np.nan

        try:
            v23_sec  = tmp_sec.loc[tmp_sec["fecha"] == target_date, col_s].iloc[0]
            pct_23   = ((ss_sa.iloc[-1] / v23_sec) - 1) * 100 if v23_sec != 0 else np.nan
            delta_23 = (ss_sa.iloc[-1] - v23_sec) * scale
        except Exception:
            pct_23 = delta_23 = np.nan

        sector_rows.append({
            "name":    sec,
            "abs_val": abs_val,
            "m_p":     ss_sa.diff().iloc[-1] * scale,
            "m_e":     calc_var(ss_sa, 1),
            "i_p":     _calc_yoy_diff_by_date(tmp_sec["fecha"], ss_orig, scale=scale),
            "i_e":     _calc_yoy_by_date(tmp_sec["fecha"], ss_orig),
            "v23_p":   delta_23,
            "v23_e":   pct_23,
        })

    total_row = {
        "name":    "Total Empleo Privado",
        "abs_val": s_orig.iloc[-1] * scale,
        "m_p": m_p,    "m_e": m_e,
        "i_p": i_p,    "i_e": i_e,
        "v23_p": v23_p, "v23_e": v23_pct,
        "is_total": True,
    }

    with st.container():
        _apply_panel_wrap("emp_sec_marker")

        st.markdown(
            '<div class="fx-wrap" style="margin-bottom:12px;">'
            '<div class="fx-title-row">'
            '<div class="fx-icon-badge">📊</div>'
            '<div>'
            '<div class="fx-title">Sectores Generales</div>'
            '<div class="fx-subtitle">Empleo asalariado privado registrado por sector</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        if sector_rows:
            _render_sector_table(sector_rows + [total_row], mes_label=mes_label)

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70);font-size:12px;margin-top:8px;'>"
            "Fuente: SIPA — Ministerio de Trabajo, Empleo y Seguridad Social"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Gráfico serie s.e. total empleo privado ──
    _render_empleo_chart(
        serie=s_sa,
        fechas=df_total["fecha"],
        titulo="Empleo privado registrado total (s.e.) — Asalariados",
        chart_key="chart_emp_total_sa",
        scale=scale,
    )

    # =========================================================
    # BLOQUE 3 — Empleo Industrial
    # =========================================================
    st.divider()

    mi_e = mi_p = ii_e = ii_p = iv23_pct = iv23_p = np.nan

    if ind_data is not None:
        isa   = ind_data["sa"]
        iorig = ind_data["orig"]
        tmp2  = ind_data["tmp"]

        mi_e = calc_var(isa, 1)
        mi_p = isa.diff().iloc[-1] * scale
        ii_e = _calc_yoy_by_date(tmp2["fecha"], iorig)
        ii_p = _calc_yoy_diff_by_date(tmp2["fecha"], iorig, scale=scale)

        try:
            ival_23  = tmp2.loc[tmp2["fecha"] == target_date, ind_data["name"] + "_sa"].iloc[0]
            iv23_pct = ((isa.iloc[-1] / ival_23) - 1) * 100 if ival_23 != 0 else np.nan
            iv23_p   = (isa.iloc[-1] - ival_23) * scale
        except Exception:
            iv23_pct = iv23_p = np.nan

        with st.container():
            _apply_panel_wrap("emp_ind_marker")
            _render_kpi_block(
                title="Empleo Industrial", subtitle="Industria manufacturera", icon="🏭",
                mes_txt=mes_txt, m_e=mi_e, m_p=mi_p, i_e=ii_e, i_p=ii_p,
                v23_pct=iv23_pct, v23_p=iv23_p, report_url=None,
            )

    # =========================================================
    # BLOQUE 4 — Subsectores Industriales
    # =========================================================
    st.divider()

    if df_sub_orig.empty or df_sub_sa.empty:
        st.info("No se encontraron datos de subsectores industriales.")
        return

    subs    = [c for c in df_sub_orig.columns if c != "fecha"]
    tmp_sub = (df_sub_orig
               .merge(df_sub_sa, on="fecha", how="inner", suffixes=("_orig", "_sa"))
               .sort_values("fecha"))

    sub_rows = []
    for sb in subs:
        # excluir filas de total que vienen en los datos
        if "total" in sb.lower():
            continue

        col_o_s = f"{sb}_orig"
        col_s_s = f"{sb}_sa"
        if col_o_s not in tmp_sub.columns or col_s_s not in tmp_sub.columns:
            continue

        sbs_orig = tmp_sub[col_o_s]
        sbs_sa   = tmp_sub[col_s_s]
        abs_val  = sbs_orig.iloc[-1] * scale if not sbs_orig.empty else np.nan

        try:
            v23_sb  = tmp_sub.loc[tmp_sub["fecha"] == target_date, col_s_s].iloc[0]
            p23_sb  = ((sbs_sa.iloc[-1] / v23_sb) - 1) * 100 if v23_sb != 0 else np.nan
            d23_sb  = (sbs_sa.iloc[-1] - v23_sb) * scale
        except Exception:
            p23_sb = d23_sb = np.nan

        sub_rows.append({
            "name":    sb,
            "abs_val": abs_val,
            "m_p":     sbs_sa.diff().iloc[-1] * scale,
            "m_e":     calc_var(sbs_sa, 1),
            "i_p":     _calc_yoy_diff_by_date(tmp_sub["fecha"], sbs_orig, scale=scale),
            "i_e":     _calc_yoy_by_date(tmp_sub["fecha"], sbs_orig),
            "v23_p":   d23_sb,
            "v23_e":   p23_sb,
        })

    # fila total industria al pie
    ind_total_rows = sub_rows.copy()
    if ind_data is not None:
        ind_total_rows.append({
            "name":    "Total Industria",
            "abs_val": ind_data["orig"].iloc[-1] * scale,
            "m_p": mi_p, "m_e": mi_e,
            "i_p": ii_p, "i_e": ii_e,
            "v23_p": iv23_p, "v23_e": iv23_pct,
            "is_total": True,
        })

    with st.container():
        _apply_panel_wrap("emp_sub_marker")

        st.markdown(
            '<div class="fx-wrap" style="margin-bottom:12px;">'
            '<div class="fx-title-row">'
            '<div class="fx-icon-badge">🏭</div>'
            '<div>'
            '<div class="fx-title">Subsectores Industriales</div>'
            '<div class="fx-subtitle">Empleo asalariado privado registrado en la industria</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div class='fx-panel-gap'></div>", unsafe_allow_html=True)

        if ind_total_rows:
            _render_sector_table(ind_total_rows, mes_label=mes_label)

        st.markdown(
            "<div style='color:rgba(20,50,79,0.70);font-size:12px;margin-top:8px;'>"
            "Fuente: SIPA — Ministerio de Trabajo, Empleo y Seguridad Social"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Gráfico serie s.e. empleo industrial ──
    if ind_data is not None:
        _render_empleo_chart(
            serie=ind_data["sa"],
            fechas=ind_data["tmp"]["fecha"],
            titulo="Empleo industrial (s.e.) — Asalariados",
            chart_key="chart_emp_ind_sa",
            scale=scale,
        )