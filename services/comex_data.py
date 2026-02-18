import io
import pandas as pd
import requests
import streamlit as st

# ✅ Este es el CSV FINAL (el que subiste)
URL_ICA = "https://infra.datos.gob.ar/catalog/sspm/dataset/74/distribution/74.3/download/intercambio-comercial-argentino-mensual.csv"

HEADERS = {
    "User-Agent": "monitor-ceu-uia/1.0 (+streamlit; requests)",
    "Accept": "text/csv,application/octet-stream,*/*;q=0.8",
}

# Mapeo EXACTO (según tu CSV final)
RENAME = {
    # Totales
    "ica_expo_totales": "expo_total",
    "ica_importaciones_totales": "impo_total",
    "ica_saldo_comercial": "saldo",

    # Exportaciones (FOB) por rubro
    "ica_exportacion_productos_primarios": "expo_pp",
    "ica_exportacion_manufacturas_origen_agropecuario": "expo_moa",
    "ica_exportacion_manufacturas_origen_industrial": "expo_moi",
    "ica_exportacion_combustible_energia": "expo_cye",

    # Importaciones (CIF) por uso
    "ica_importaciones_bienes_capital": "impo_bk",
    "ica_importaciones_bienes_intermedios": "impo_bi",
    "ica_importaciones_combustibles_lubricantes": "impo_cl",
    "ica_importaciones_piezas_accesorios_bienes_capital": "impo_pabc",
    "ica_importaciones_bienes_consumo": "impo_bc",
    "ica_importaciones_vehiculos_automotores_pasajeros": "impo_vap",
    "ica_importaciones_resto": "impo_resto",

    # (Opcionales, vienen en tu CSV)
    "ica_bienes_capital_partes_piezas": "impo_bk_pabc",
    "ica_bienes_intermedios_combustibles_lubricantes": "impo_bi_cl",
    "ica_importaciones_bs_consumo_vehiculos_automotor_pasajeros": "impo_bc_vap",
}

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_ica() -> pd.DataFrame:
    r = requests.get(URL_ICA, headers=HEADERS, timeout=60)
    r.raise_for_status()

    # bytes -> pandas (más robusto)
    df = pd.read_csv(io.BytesIO(r.content))

    # fecha
    df = df.rename(columns={"indice_tiempo": "fecha"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # rename a nombres internos CEU
    df = df.rename(columns=RENAME)

    # numéricos
    for c in df.columns:
        if c != "fecha":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["fecha"]).sort_values("fecha")
    return df


