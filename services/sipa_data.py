from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SIPA_DIR = ROOT / "assets" / "sipa"


def _leer_csv_sipa(nombre_archivo: str) -> pd.DataFrame:
    path = SIPA_DIR / nombre_archivo

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    df = pd.read_csv(path)

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df = df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)

    return df


@st.cache_data(show_spinner=False)
def cargar_sipa_excel():
    """
    Mantengo el mismo nombre para no tocar empleo.py.

    Antes:
      - resolvía URL
      - descargaba Excel
      - parseaba hojas
      - cacheaba

    Ahora:
      - solo lee CSV locales generados por scripts/actualizar_sipa_assets.py
    """
    try:
        df_total = _leer_csv_sipa("sipa_total.csv")
        df_sec_orig = _leer_csv_sipa("sipa_sec_orig.csv")
        df_sec_sa = _leer_csv_sipa("sipa_sec_sa.csv")
        df_sub_orig = _leer_csv_sipa("sipa_sub_orig.csv")
        df_sub_sa = _leer_csv_sipa("sipa_sub_sa.csv")

        return df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa

    except Exception as e:
        st.error(f"No se pudieron cargar los datos SIPA locales: {e}")

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )