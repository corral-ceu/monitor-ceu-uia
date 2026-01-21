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
          /* Contenedor del widget (evita que se estire demasiado) */
          div[data-testid="stMultiSelect"] { max-width: 420px; }

          /* Caja del input */
          div[data-testid="stMultiSelect"] div[class*="control"] {
            background: #ffffff !important;
            border-color: #cbd5e1 !important;
          }

          /* Texto dentro del input */
          div[data-testid="stMultiSelect"] * {
            color: #0f172a !important;
          }

          /* Chips (seleccionados) */
          div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
            background-color: #e2e8f0 !important;
            border: 1px solid #cbd5e1 !important;
          }

          /* Texto dentro del chip */
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
            default=[13, 12],
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

        # CSV largo
