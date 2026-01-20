import re
import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

SIPA_XLSX_URL = "https://www.argentina.gob.ar/sites/default/files/trabajoregistrado_2510_estadisticas.xlsx"

def _parse_mes(x):
    if pd.isna(x): return pd.NaT
    if isinstance(x, pd.Timestamp): return pd.Timestamp(x.year, x.month, 1)
    if isinstance(x, (int, float)) and not pd.isna(x):
        try:
            dt = pd.to_datetime(x, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(dt): return pd.NaT
            return pd.Timestamp(dt.year, dt.month, 1)
        except Exception: pass

    s = str(x).strip().lower()
    if not s: return pd.NaT
    s = s.replace("*", "").replace("/", "-").replace(".", "-")
    s = re.sub(r"\s+", "", s)

    m = re.match(r"^(?P<yyyy>\d{4})m(?P<mm>\d{1,2})$", s)
    if m:
        return pd.Timestamp(int(m.group("yyyy")), int(m.group("mm")), 1)

    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if not pd.isna(dt): return pd.Timestamp(dt.year, dt.month, 1)

    meses = {
        "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
        "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
        "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "set": 9, "sept": 9, "septiembre": 9,
        "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12,
    }
    m = re.match(r"^(?P<mon>[a-záéíóúñ]{3,9})-?(?P<yy>\d{2,4})$", s)
    if m:
        mon = m.group("mon")
        yy = int(m.group("yy"))
        if mon in meses:
            year = yy if yy > 1900 else (2000 + yy if yy < 70 else 1900 + yy)
            return pd.Timestamp(year, meses[mon], 1)
    m = re.match(r"^(?P<yyyy>\d{4})-?(?P<mon>[a-záéíóúñ]{3,9})$", s)
    if m:
        year = int(m.group("yyyy"))
        mon = m.group("mon")
        if mon in meses: return pd.Timestamp(year, meses[mon], 1)
    return pd.NaT

def _extraer_serie_colB(df_raw, col_fecha=0, col_val=1):
    tmp = df_raw.copy()
    tmp = tmp.rename(columns={tmp.columns[col_fecha]: "fecha_raw", tmp.columns[col_val]: "valor_raw"})
    tmp["fecha"] = tmp["fecha_raw"].apply(_parse_mes)
    tmp["valor"] = pd.to_numeric(tmp["valor_raw"], errors="coerce")
    out = tmp.dropna(subset=["fecha", "valor"])[["fecha", "valor"]].sort_values("fecha")
    return out

def _extraer_sectores(df_raw):
    header = df_raw.iloc[1, 1:].copy().dropna()
    sectores = [str(x).strip() for x in header.tolist() if str(x).strip() != ""]
    if not sectores: return pd.DataFrame(columns=["fecha"])
    
    data = df_raw.iloc[2:, : (1 + len(sectores))].copy()
    data.columns = ["fecha_raw"] + sectores
    data["fecha"] = data["fecha_raw"].apply(_parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])
    
    for c in sectores:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    return data.dropna(how="all", subset=sectores).sort_values("fecha")

def _extraer_subsectores_industria(df_raw):
    """
    Extrae columnas D a J (indices 3 a 9) de las hojas A.6.x
    Fila de titulos: 2 (indice 1)
    Columna fecha: A (indice 0)
    """
    # Índices de columnas de interés: 3,4,5,6,7,8,9
    col_indices = [3, 4, 5, 6, 7, 8, 9]
    
    # Obtener nombres de los subsectores desde la fila 2 (indice 1)
    nombres = []
    for c in col_indices:
        val = df_raw.iloc[1, c]
        nombres.append(str(val).strip())
    
    # Seleccionar solo Fecha (0) y las columnas de datos
    cols_to_use = [0] + col_indices
    data = df_raw.iloc[2:, cols_to_use].copy()
    
    # Renombrar
    nuevos_nombres = ["fecha_raw"] + nombres
    data.columns = nuevos_nombres
    
    # Parsear fecha
    data["fecha"] = data["fecha_raw"].apply(_parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])
    
    # Convertir a numérico
    for c in nombres:
        data[c] = pd.to_numeric(data[c], errors="coerce")
        
    return data.sort_values("fecha")

@st.cache_data(ttl=3600)
def cargar_sipa_excel():
    try:
        r = requests.get(SIPA_XLSX_URL, timeout=60)
        r.raise_for_status()
        content = r.content
        xls = pd.ExcelFile(BytesIO(content), engine="openpyxl")
        
        # Hojas generales
        t21 = pd.read_excel(xls, sheet_name="T.2.1", header=None, usecols=[0, 1])
        t22 = pd.read_excel(xls, sheet_name="T.2.2", header=None, usecols=[0, 1])
        a21 = pd.read_excel(xls, sheet_name="A.2.1", header=None)
        a22 = pd.read_excel(xls, sheet_name="A.2.2", header=None)
        
        # NUEVO: Hojas de subsectores industriales
        a61 = pd.read_excel(xls, sheet_name="A.6.1", header=None)
        a62 = pd.read_excel(xls, sheet_name="A.6.2", header=None)
        
        # Procesar General
        s_orig = _extraer_serie_colB(t21).rename(columns={"valor": "orig"})
        s_sa = _extraer_serie_colB(t22).rename(columns={"valor": "sa"})
        df_total = s_orig.merge(s_sa, on="fecha", how="inner").sort_values("fecha")
        
        df_sec_orig = _extraer_sectores(a21)
        df_sec_sa = _extraer_sectores(a22)
        
        # Procesar Subsectores (Nuevo)
        df_sub_orig = _extraer_subsectores_industria(a61)
        df_sub_sa = _extraer_subsectores_industria(a62)
        
        # Filtrar fechas
        for df in [df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa]:
            if not df.empty:
                df.drop(df[(df["fecha"] < "2000-01-01") | (df["fecha"] > "2035-12-01")].index, inplace=True)
                
        return df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. CARGA DE DATOS (IPI - EXCEL INDEC) ---
