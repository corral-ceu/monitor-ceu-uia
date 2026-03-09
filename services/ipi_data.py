from io import BytesIO

import pandas as pd
import requests
import streamlit as st


@st.cache_data(ttl=3600)
def cargar_ipi_excel():
    """Descarga y lee el Excel del IPI Manufacturero (INDEC) .xls"""
    url = "https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipi_manufacturero_2026.xls"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.ms-excel,application/octet-stream,*/*",
        "Referer": "https://www.indec.gob.ar/",
    }

    try:
        r = requests.get(url, timeout=60, headers=headers)
        # Si INDEC responde 403/404/etc
        r.raise_for_status()

        # Si por algún motivo te devuelven HTML (bloqueo/proxy), no es un Excel
        head = r.content[:200].lstrip().lower()
        if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
            st.error(
                "IPI: INDEC devolvió HTML en lugar de un .xls. "
                f"Status={r.status_code} Content-Type={r.headers.get('Content-Type')}"
            )
            return None, None

        xls = BytesIO(r.content)

        # .xls -> xlrd (asegurate de tener xlrd>=2.0 en requirements)
        df_c2 = pd.read_excel(xls, sheet_name="Cuadro 2", header=None, engine="xlrd")
        xls.seek(0)
        df_c5 = pd.read_excel(xls, sheet_name="Cuadro 5", header=None, engine="xlrd")

        return df_c2, df_c5

    except Exception as e:
        st.error(f"IPI: error descargando/leyendo Excel ({type(e).__name__}): {e}")
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
