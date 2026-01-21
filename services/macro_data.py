import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# TC mayorista (BCRA) - id=5
# ============================================================
@st.cache_data(ttl=60 * 60)
def get_a3500() -> pd.DataFrame:
    """
    Wrapper del id=5 usando el helper genérico paginado.
    Devuelve columnas: Date, FX
    """
    df = get_monetaria_serie(5)  # <- usa tu función paginada robusta
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "FX"])

    out = df.rename(columns={"value": "FX"}).copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out["FX"] = pd.to_numeric(out["FX"], errors="coerce")

    return (
        out[["Date", "FX"]]
        .dropna()
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )

# ============================================================
# REM
# ============================================================
@st.cache_data(ttl=60 * 60)
def get_rem_last() -> pd.DataFrame:
    url = (
        "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/"
        "historico-relevamiento-expectativas-mercado.xlsx"
    )
    df = pd.read_excel(url, sheet_name="Base de Datos Completa", skiprows=1)

    rem = df.loc[
        (df["Variable"] == "Precios minoristas (IPC nivel general; INDEC)")
        & (df["Referencia"] == "var. % mensual")
    ].copy()

    latest = rem["Fecha de pronóstico"].max()

    return (
        rem.loc[rem["Fecha de pronóstico"] == latest]
        .sort_values("Período")
        .tail(24)
        .rename(columns={"Período": "Date", "Mediana": "v_m_REM"})
        .assign(Date=lambda x: pd.to_datetime(x["Date"], errors="coerce"))
        .reset_index(drop=True)
    )


# ============================================================
# IPC INDEC (se mantiene para macro_precios.py)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def get_ipc_indec_full() -> pd.DataFrame:
    url = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv"
    try:
        df = pd.read_csv(url, sep=";", decimal=",", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(url, sep=";", decimal=",", encoding="latin1")

    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")
    df["Periodo"] = pd.to_datetime(df["Periodo"].astype(str), format="%Y%m", errors="coerce")

    for c in ["Descripcion", "Clasificador", "Region"]:
        df[c] = df[c].astype(str).str.strip()

    for c in ["Indice_IPC", "v_m_IPC", "v_i_a_IPC"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna(subset=["Periodo"]).sort_values("Periodo").reset_index(drop=True)


@st.cache_data(ttl=12 * 60 * 60)
def get_ipc_nacional_nivel_general() -> pd.DataFrame:
    df = get_ipc_indec_full()

    tmp = (
        df[(df["Codigo"] == 0) & (df["Region"] == "Nacional")]
        .dropna(subset=["v_m_IPC"])
        .rename(columns={"Periodo": "Date"})
        .sort_values("Date")
    )
    tmp["Period"] = tmp["Date"].dt.to_period("M")
    tmp["v_m_CPI"] = tmp["v_m_IPC"] / 100.0  # % -> decimal

    return (
        tmp[["Date", "v_m_CPI", "Period"]]
        .drop_duplicates("Period")
        .sort_values("Period")
        .reset_index(drop=True)
    )


# ============================================================
# IPC BCRA (id=27) para bandas
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def get_ipc_bcra() -> pd.DataFrame:
    """
    IPC (% mensual) desde BCRA Monetarias idVariable=27.
    Devuelve v_m_CPI en DECIMAL (ej 2.8% -> 0.028).
    """
    url = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/27"
    params = {"Limit": 1000, "Offset": 0}
    data = []

    for _ in range(3):
        try:
            while True:
                r = requests.get(url, params=params, timeout=10, verify=False)
                r.raise_for_status()
                payload = r.json()

                results = payload.get("results", [])
                if not results:
                    break

                detalle = results[0].get("detalle", [])
                if not detalle:
                    break

                data.extend(detalle)

                meta = payload["metadata"]["resultset"]
                params["Offset"] += params["Limit"]
                if params["Offset"] >= meta["count"]:
                    break
            break
        except requests.exceptions.RequestException:
            pass

    if not data:
        return pd.DataFrame(columns=["Date", "v_m_CPI", "Period"])

    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["v_m_pct"] = pd.to_numeric(df["valor"], errors="coerce")  # viene como % (ej 2.8)
    df = df.dropna(subset=["Date", "v_m_pct"]).sort_values("Date")

    df["Period"] = df["Date"].dt.to_period("M")
    df["v_m_CPI"] = df["v_m_pct"] / 100.0

    return (
        df[["Date", "v_m_CPI", "Period"]]
        .drop_duplicates("Period")
        .sort_values("Period")
        .reset_index(drop=True)
    )


# ============================================================
# Bandas
# ============================================================
def build_bands_2025(start, end, lower0, upper0) -> pd.DataFrame:
    g_up = (1 + 0.01) ** (1 / 30)
    g_dn = (1 - 0.01) ** (1 / 30)

    dates = pd.date_range(start, end, freq="D")
    t = np.arange(len(dates))

    return pd.DataFrame({"Date": dates, "lower": lower0 * (g_dn**t), "upper": upper0 * (g_up**t)})


def build_bands_2026(bands_2025: pd.DataFrame, rem: pd.DataFrame, ipc: pd.DataFrame) -> pd.DataFrame:
    """
    ipc debe tener Period y v_m_CPI en DECIMAL.
    rem trae v_m_REM en %.
    """
    rem_m = rem.assign(Period=rem["Date"].dt.to_period("M"))[["Period", "v_m_REM"]]
    m = ipc.merge(rem_m, on="Period", how="outer").sort_values("Period")
    m["v_m_dec"] = np.where(m["v_m_CPI"].notna(), m["v_m_CPI"], m["v_m_REM"] / 100)

    end_month = m.loc[m["v_m_REM"].notna(), "Period"].max() + 2
    b = pd.DataFrame({"Period": pd.period_range("2026-01", end_month, freq="M")})
    b["ref"] = b["Period"] - 2
    b = b.merge(m[["Period", "v_m_dec"]].rename(columns={"Period": "ref"}), on="ref", how="left")

    lower0 = bands_2025.loc[bands_2025["Date"] == "2025-12-31", "lower"].iloc[0]
    upper0 = bands_2025.loc[bands_2025["Date"] == "2025-12-31", "upper"].iloc[0]

    cal = pd.DataFrame({"Date": pd.date_range("2026-01-01", b["Period"].max().to_timestamp("M"), freq="D")})
    cal["Period"] = cal["Date"].dt.to_period("M")
    cal = cal.merge(b[["Period", "v_m_dec"]], on="Period", how="left")

    r_d = (1 + cal["v_m_dec"]) ** (1 / 30) - 1
    cal["lower"] = lower0 * (1 - r_d).cumprod()
    cal["upper"] = upper0 * (1 + r_d).cumprod()

    return cal[["Date", "lower", "upper"]]


# ============================================================
# Helper genérico
# ============================================================
# ============================================================
# Helper genérico (BCRA Monetarias) — PAGINADO
# ============================================================
@st.cache_data(ttl=60 * 60)
def get_monetaria_serie(id_variable: int) -> pd.DataFrame:
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_variable}"
    params = {"Limit": 1000, "Offset": 0}
    data = []

    for _ in range(3):
        try:
            while True:
                r = requests.get(url, params=params, timeout=10, verify=False)
                r.raise_for_status()
                payload = r.json()

                results = payload.get("results", [])
                if not results:
                    break

                detalle = results[0].get("detalle", [])
                if not detalle:
                    break

                data.extend(detalle)

                meta = payload.get("metadata", {}).get("resultset", {})
                count = meta.get("count")

                params["Offset"] += params["Limit"]
                if count is None or params["Offset"] >= count:
                    break
            break
        except requests.exceptions.RequestException:
            pass

    if not data:
        return pd.DataFrame(columns=["Date", "value"])

    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["value"] = pd.to_numeric(df["valor"], errors="coerce")

    return (
        df[["Date", "value"]]
        .dropna()
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )



# ============================================================
# ITCRM (Excel BCRA) - ITCRM + bilaterales
# ============================================================

from io import BytesIO

@st.cache_data(ttl=12 * 60 * 60)
def get_itcrm_excel_long() -> pd.DataFrame:
    """
    Descarga ITCRMSerie.xlsx del BCRA y devuelve formato largo:
    columnas: Date, Serie, Value

    Hoja: "ITCRM y bilaterales"
    Col A: fechas
    Fila 2: nombres de series
    """
    url = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/ITCRMSerie.xlsx"
    sheet = "ITCRM y bilaterales"

    r = requests.get(url, timeout=60)  # NO usa verify=False (es bcra.gob.ar)
    r.raise_for_status()

    df = pd.read_excel(
        BytesIO(r.content),
        sheet_name=sheet,
        header=1,          # fila 2 como encabezados
        engine="openpyxl"
    )

    # Primera columna = fecha
    df = df.rename(columns={df.columns[0]: "Date"}).copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])

    # A numérico (vienen con coma o como string a veces)
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Largo
    value_cols = [c for c in df.columns if c != "Date"]
    long_df = (
        df.melt(id_vars=["Date"], value_vars=value_cols, var_name="Serie", value_name="Value")
          .dropna(subset=["Value"])
          .sort_values(["Serie", "Date"])
          .reset_index(drop=True)
    )

    return long_df

