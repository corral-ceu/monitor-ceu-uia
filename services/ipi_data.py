from io import BytesIO

import pandas as pd
import requests
import streamlit as st


@st.cache_data(ttl=3600)
def cargar_ipi_excel():
    """Descarga y lee el Excel del IPI Manufacturero (INDEC) .xls"""
    url = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2025.xls"
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

        xls = BytesIO(r.content)

        # .xls -> xlrd
        df_c2 = pd.read_excel(xls, sheet_name="Cuadro 2", header=None, engine="xlrd")
        df_c5 = pd.read_excel(xls, sheet_name="Cuadro 5", header=None, engine="xlrd")

        return df_c2, df_c5
    except Exception:
        return None, None


def procesar_serie_excel(df: pd.DataFrame, col_idx: int) -> pd.DataFrame:
    """Extrae serie mensual desde el formato del Excel de INDEC."""
    try:
        data = df.iloc[6:].copy()
        data[1] = data[1].ffill().astype(str).str.extract(r"(\d{4})")[0]
        data = data.dropna(subset=[1, 2, col_idx])

        meses_map = {
            "enero": 1,
            "febrero": 2,
            "marzo": 3,
            "abril": 4,
            "mayo": 5,
            "junio": 6,
            "julio": 7,
            "agosto": 8,
            "septiembre": 9,
            "octubre": 10,
            "noviembre": 11,
            "diciembre": 12,
        }
        data["m"] = data[2].astype(str).str.lower().str.strip().map(meses_map)

        data["fecha"] = pd.to_datetime(
            data[1] + "-" + data["m"].astype(int).astype(str) + "-01",
            errors="coerce",
        )

        return (
            data[["fecha", col_idx]]
            .rename(columns={col_idx: "valor"})
            .dropna()
            .sort_values("fecha")
        )
    except Exception:
        return pd.DataFrame(columns=["fecha", "valor"])
