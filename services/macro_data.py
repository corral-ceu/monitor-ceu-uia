import numpy as np
import pandas as pd
import requests
import streamlit as st
from io import BytesIO
from io import StringIO 


# ============================================================
# Helper genérico (BCRA Monetarias) — PAGINADO ROBUSTO
# ============================================================
@st.cache_data(ttl=60 * 60)
def get_monetaria_serie(id_variable: int) -> pd.DataFrame:
    """
    Descarga series del endpoint Monetarias/{id_variable}.
    Devuelve columnas: Date, value
    Paginación robusta:
      - Si metadata.count existe: usa count.
      - Si no existe: corta cuando la página viene “corta” (< Limit).
    """
    url = f"https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/{id_variable}"
    params = {"Limit": 1000, "Offset": 0}
    data = []
    last_err = None

    for _ in range(3):
        try:
            params["Offset"] = 0
            data = []

            while True:
                r = requests.get(url, params=params, timeout=20, verify=False)
                r.raise_for_status()
                payload = r.json()

                results = payload.get("results", [])
                if not results:
                    break

                detalle = results[0].get("detalle", [])
                if not detalle:
                    break

                data.extend(detalle)

                meta = payload.get("metadata", {}).get("resultset", {}) or {}
                count = meta.get("count")

                params["Offset"] += params["Limit"]

                if count is not None:
                    # corte con count
                    if params["Offset"] >= count:
                        break
                else:
                    # corte por página corta
                    if len(detalle) < params["Limit"]:
                        break

            break  # ok
        except requests.exceptions.RequestException as e:
            last_err = str(e)

    if not data:
        # No rompemos: devolvemos vacío (las páginas lo manejan),
        # pero dejamos el error visible en la app (no en consola).
        if last_err:
            st.error(f"Error BCRA Monetarias/{id_variable}: {last_err}")
        return pd.DataFrame(columns=["Date", "value"])

    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df.get("fecha"), errors="coerce")
    df["value"] = pd.to_numeric(df.get("valor"), errors="coerce")

    return (
        df[["Date", "value"]]
        .dropna()
        .drop_duplicates(subset=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )


# ============================================================
# TC mayorista (A3500)
# ============================================================
@st.cache_data(ttl=60 * 60)
def get_a3500() -> pd.DataFrame:
    """
    A3500: intentamos id=5 (como venías usando).
    Si no trae nada (por cambios del BCRA / entorno), fallback a 84.
    Devuelve columnas: Date, FX
    """
    df = get_monetaria_serie(5)

    # fallback típico que suele ser A3500 en muchos códigos
    if df.empty:
        df = get_monetaria_serie(84)

    if df.empty:
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
# IPC INDEC (para macro_precios.py)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def get_ipc_indec_full() -> pd.DataFrame:
    url = "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv"
    try:
        df = pd.read_csv(url, sep=";", decimal=",", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(url, sep=";", decimal=",", encoding="latin1")

    # ✅ CLAVE: mantener Codigo como string (preserva B/S/Núcleo/Regulados/Estacional)
    df["Codigo"] = df["Codigo"].astype(str).str.strip()

    # ✅ versión numérica para filtros tipo Codigo == 0
    df["Codigo_num"] = pd.to_numeric(df["Codigo"], errors="coerce")

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
        df[(df["Codigo_num"] == 0) & (df["Region"] == "Nacional")]
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
    df = get_monetaria_serie(27)
    if df.empty:
        return pd.DataFrame(columns=["Date", "v_m_CPI", "Period"])

    df = df.rename(columns={"value": "v_m_pct"}).copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["v_m_pct"] = pd.to_numeric(df["v_m_pct"], errors="coerce")
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
# ITCRM (Excel BCRA) - ITCRM + bilaterales
# ============================================================
@st.cache_data(ttl=12 * 60 * 60)
def get_itcrm_excel_long() -> pd.DataFrame:
    """
    Descarga ITCRMSerie.xlsx del BCRA y devuelve formato largo:
    columnas: Date, Serie, Value
    """
    url = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/ITCRMSerie.xlsx"
    sheet = "ITCRM y bilaterales"

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    df = pd.read_excel(
        BytesIO(r.content),
        sheet_name=sheet,
        header=1,
        engine="openpyxl",
    )

    df = df.rename(columns={df.columns[0]: "Date"}).copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])

    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    value_cols = [c for c in df.columns if c != "Date"]
    long_df = (
        df.melt(id_vars=["Date"], value_vars=value_cols, var_name="Serie", value_name="Value")
        .dropna(subset=["Value"])
        .sort_values(["Serie", "Date"])
        .reset_index(drop=True)
    )
    return long_df


# ============================================================
# DATOS.GOB.AR — EMAE (INDEC)
# ============================================================

DATOS_GOB_AR_SERIES_URL = "https://apis.datos.gob.ar/series/api/series"

def _parse_datos_gob_series_csv(csv_text: str, series_id: str) -> pd.DataFrame:
    """
    Parsea CSV de datos.gob.ar.
    Soporta:
      - formato largo: indice_tiempo, serie_id, valor
      - formato ancho: indice_tiempo + columna con el id de la serie
      - formato simple: indice_tiempo, valor   <-- ESTE ERA EL QUE FALTABA
    Devuelve DataFrame con columnas Date, Value.
    """
    try:
        df = pd.read_csv(StringIO(csv_text))
        if df.empty:
            return pd.DataFrame(columns=["Date", "Value"])

        df.columns = [c.strip() for c in df.columns]

        # 1) Formato largo
        if {"indice_tiempo", "serie_id", "valor"}.issubset(df.columns):
            out = df[df["serie_id"] == series_id][["indice_tiempo", "valor"]].copy()
            out = out.rename(columns={"indice_tiempo": "Date", "valor": "Value"})

        # 2) Formato ancho
        elif "indice_tiempo" in df.columns and series_id in df.columns:
            out = df[["indice_tiempo", series_id]].copy()
            out = out.rename(columns={"indice_tiempo": "Date", series_id: "Value"})

        # 3) ✅ Formato simple (una sola serie)
        elif {"indice_tiempo", "valor"}.issubset(df.columns):
            out = df[["indice_tiempo", "valor"]].copy()
            out = out.rename(columns={"indice_tiempo": "Date", "valor": "Value"})

        # 4) Fallback clásico
        elif {"fecha", "valor"}.issubset(df.columns):
            out = df.rename(columns={"fecha": "Date", "valor": "Value"})[["Date", "Value"]]

        else:
            return pd.DataFrame(columns=["Date", "Value"])

        out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
        out["Value"] = pd.to_numeric(out["Value"], errors="coerce")

        return (
            out.dropna(subset=["Date", "Value"])
               .drop_duplicates(subset=["Date"])
               .sort_values("Date")
               .reset_index(drop=True)
        )

    except Exception:
        return pd.DataFrame(columns=["Date", "Value"])



@st.cache_data(ttl=12 * 60 * 60)
def get_datos_gob_series(series_id: str) -> pd.DataFrame:
    """
    Descarga una serie puntual desde datos.gob.ar.
    Usamos CSV (probado por vos en Jupyter) porque suele ser lo más estable.
    """
    params = {"ids": series_id, "format": "csv", "limit": 1000}

    try:
        r = requests.get(
            DATOS_GOB_AR_SERIES_URL,
            params=params,
            timeout=30,
            headers={
                "User-Agent": "monitor-ceu-uia/1.0 (streamlit)",
                "Accept": "text/csv,*/*",
            },
        )
        # Si falla, queremos ver algo útil en la app (no silencio total)
        if r.status_code != 200:
            st.warning(f"datos.gob.ar ({series_id}) status={r.status_code}: {r.text[:200]}")
            return pd.DataFrame(columns=["Date", "Value"])

        return _parse_datos_gob_series_csv(r.text, series_id)

    except Exception as e:
        st.warning(f"datos.gob.ar ({series_id}) error: {e}")
        return pd.DataFrame(columns=["Date", "Value"])


# IDs (confirmados por vos)
EMAE_ORIGINAL_ID = "143.3_NO_PR_2004_A_21"
EMAE_DESEASON_ID = "143.3_NO_PR_2004_A_31"


@st.cache_data(ttl=12 * 60 * 60)
def get_emae_original() -> pd.DataFrame:
    return get_datos_gob_series(EMAE_ORIGINAL_ID)


@st.cache_data(ttl=12 * 60 * 60)
def get_emae_deseasonalizado() -> pd.DataFrame:
    return get_datos_gob_series(EMAE_DESEASON_ID)

