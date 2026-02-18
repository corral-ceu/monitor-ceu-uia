import re
import hashlib
from io import BytesIO
from datetime import date

import pandas as pd
import requests
import streamlit as st


# ============================================================
# Fuente (en vez de hardcodear el .xlsx del mes)
# ============================================================
SIPA_LANDING_PAGE = (
    "https://www.argentina.gob.ar/trabajo/estadisticas/"
    "situacion-y-evolucion-del-trabajo-registrado"
)

# matchea URLs como:
# https://www.argentina.gob.ar/sites/default/files/trabajoregistrado_2511_estadisticas.xlsx
_SIPA_XLSX_RE = re.compile(
    r"https?://www\.argentina\.gob\.ar/sites/default/files/"
    r"trabajoregistrado_(\d{4})_estadisticas\.xlsx",
    re.IGNORECASE,
)


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)  # resolver como máx 1 vez/día
def _resolve_latest_sipa_xlsx_url() -> str:
    """
    Busca en la página oficial el link del XLSX vigente y devuelve el más nuevo.
    Fallback: si no encuentra nada, prueba por patrón hacia atrás.
    """
    # 1) Intento principal: scrape de la landing
    try:
        r = requests.get(SIPA_LANDING_PAGE, timeout=30)
        r.raise_for_status()
        html = r.text

        matches = list(_SIPA_XLSX_RE.finditer(html))
        if matches:
            # elegir el de mayor YYMM
            best = max(matches, key=lambda m: int(m.group(1)))
            return best.group(0)
    except Exception:
        pass

    # 2) Fallback robusto: probar por patrón (últimos 24 meses)
    #    (útil si cambian el HTML o el botón no aparece por algún motivo)
    def iter_yymm(back_months: int = 24):
        y = date.today().year
        m = date.today().month
        for _ in range(back_months):
            yield f"{y % 100:02d}{m:02d}"
            m -= 1
            if m == 0:
                m = 12
                y -= 1

    for yymm in iter_yymm(24):
        url = (
            "https://www.argentina.gob.ar/sites/default/files/"
            f"trabajoregistrado_{yymm}_estadisticas.xlsx"
        )
        try:
            # HEAD a veces falla en algunos servidores; si falla, caemos a GET mínimo
            h = requests.head(url, allow_redirects=True, timeout=15)
            if h.status_code == 200:
                return h.url  # por si redirige
        except Exception:
            pass

        try:
            g = requests.get(url, stream=True, timeout=20)
            if g.status_code == 200:
                return g.url
        except Exception:
            pass

    raise RuntimeError("No se pudo resolver el último link del XLSX de SIPA.")
def _parse_mes(x):
    if pd.isna(x):
        return pd.NaT

    if isinstance(x, pd.Timestamp):
        return pd.Timestamp(x.year, x.month, 1)

    if isinstance(x, (int, float)) and not pd.isna(x):
        try:
            dt = pd.to_datetime(x, unit="D", origin="1899-12-30", errors="coerce")
            if pd.isna(dt):
                return pd.NaT
            return pd.Timestamp(dt.year, dt.month, 1)
        except Exception:
            pass

    s = str(x).strip().lower()
    if not s:
        return pd.NaT

    s = s.replace("*", "").replace("/", "-").replace(".", "-")
    s = re.sub(r"\s+", "", s)

    m = re.match(r"^(?P<yyyy>\d{4})m(?P<mm>\d{1,2})$", s)
    if m:
        return pd.Timestamp(int(m.group("yyyy")), int(m.group("mm")), 1)

    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if not pd.isna(dt):
        return pd.Timestamp(dt.year, dt.month, 1)

    meses = {
        "ene": 1, "enero": 1,
        "feb": 2, "febrero": 2,
        "mar": 3, "marzo": 3,
        "abr": 4, "abril": 4,
        "may": 5, "mayo": 5,
        "jun": 6, "junio": 6,
        "jul": 7, "julio": 7,
        "ago": 8, "agosto": 8,
        "sep": 9, "set": 9, "sept": 9, "septiembre": 9,
        "oct": 10, "octubre": 10,
        "nov": 11, "noviembre": 11,
        "dic": 12, "diciembre": 12,
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
        if mon in meses:
            return pd.Timestamp(year, meses[mon], 1)

    return pd.NaT


# ============================================================
# Extractores
# ============================================================
def _extraer_serie_colB(df_raw, col_fecha=0, col_val=1):
    tmp = df_raw.copy()
    tmp = tmp.rename(columns={tmp.columns[col_fecha]: "fecha_raw", tmp.columns[col_val]: "valor_raw"})
    tmp["fecha"] = tmp["fecha_raw"].apply(_parse_mes)
    tmp["valor"] = pd.to_numeric(tmp["valor_raw"], errors="coerce")
    out = tmp.dropna(subset=["fecha", "valor"])[["fecha", "valor"]].sort_values("fecha")
    return out


def _extraer_sectores(df_raw):
    # La fila de títulos está en índice 1 y empieza en columna 1 (B) según tu lógica original
    header = df_raw.iloc[1, 1:].copy().dropna()
    sectores = [str(x).strip() for x in header.tolist() if str(x).strip() != ""]
    if not sectores:
        return pd.DataFrame(columns=["fecha"])

    data = df_raw.iloc[2:, : (1 + len(sectores))].copy()
    data.columns = ["fecha_raw"] + sectores
    data["fecha"] = data["fecha_raw"].apply(_parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])

    for c in sectores:
        data[c] = pd.to_numeric(data[c], errors="coerce")

    return data.dropna(how="all", subset=sectores).sort_values("fecha")


def _extraer_subsectores_industria(df_raw):
    """
    IMPORTANTE: df_raw llega RECORTADO desde read_excel con:
      usecols=[0,3,4,5,6,7,8,9]
    Por lo tanto df_raw tiene 8 columnas:
      - col 0 = Fecha (A)
      - col 1..7 = D..J (subsectores)

    Fila de títulos: índice 1
    Datos: desde índice 2
    """
    if df_raw is None or df_raw.empty or df_raw.shape[1] < 2:
        return pd.DataFrame(columns=["fecha"])

    # En el DF recortado, subsectores = cols 1..7 (si existen)
    col_indices = list(range(1, min(8, df_raw.shape[1])))

    # Nombres desde fila de títulos (índice 1)
    nombres = []
    for c in col_indices:
        val = df_raw.iloc[1, c]
        nombres.append(str(val).strip())

    # Seleccionar Fecha (0) + subsectores
    cols_to_use = [0] + col_indices
    data = df_raw.iloc[2:, cols_to_use].copy()
    data.columns = ["fecha_raw"] + nombres

    data["fecha"] = data["fecha_raw"].apply(_parse_mes)
    data = data.dropna(subset=["fecha"]).drop(columns=["fecha_raw"])

    for c in nombres:
        data[c] = pd.to_numeric(data[c], errors="coerce")

    return data.dropna(how="all", subset=nombres).sort_values("fecha")


# ============================================================
# Descarga y parseo cacheados (hash)
# ============================================================
@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)  # baja el XLSX como máx cada 12h
def _download_sipa_bytes() -> bytes:
    url = _resolve_latest_sipa_xlsx_url()

    # opcional: mostrar qué link se está usando (útil para debug)
    # st.caption(f"Descargando SIPA desde: {url}")

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


@st.cache_data(show_spinner=False)  # se invalida solo si cambia el hash
def _parse_sipa(content_hash: str, content: bytes):
    xls = pd.ExcelFile(BytesIO(content), engine="openpyxl")

    # General (2 columnas)
    t21 = pd.read_excel(xls, sheet_name="T.2.1", header=None, usecols=[0, 1])
    t22 = pd.read_excel(xls, sheet_name="T.2.2", header=None, usecols=[0, 1])

    # Sectores: 17 columnas reales (0..16)
    a21 = pd.read_excel(xls, sheet_name="A.2.1", header=None, usecols=list(range(17)))
    a22 = pd.read_excel(xls, sheet_name="A.2.2", header=None, usecols=list(range(17)))

    # Subsectores industriales: A + D:J
    a61 = pd.read_excel(xls, sheet_name="A.6.1", header=None, usecols=[0, 3, 4, 5, 6, 7, 8, 9])
    a62 = pd.read_excel(xls, sheet_name="A.6.2", header=None, usecols=[0, 3, 4, 5, 6, 7, 8, 9])

    # Procesar series generales
    s_orig = _extraer_serie_colB(t21).rename(columns={"valor": "orig"})
    s_sa = _extraer_serie_colB(t22).rename(columns={"valor": "sa"})
    df_total = s_orig.merge(s_sa, on="fecha", how="inner").sort_values("fecha")

    # Procesar sectores
    df_sec_orig = _extraer_sectores(a21)
    df_sec_sa = _extraer_sectores(a22)

    # Procesar subsectores
    df_sub_orig = _extraer_subsectores_industria(a61)
    df_sub_sa = _extraer_subsectores_industria(a62)

    # Filtro de fechas
    for df in [df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa]:
        if not df.empty:
            df.drop(
                df[(df["fecha"] < "2000-01-01") | (df["fecha"] > "2035-12-01")].index,
                inplace=True,
            )

    return df_total, df_sec_orig, df_sec_sa, df_sub_orig, df_sub_sa


def cargar_sipa_excel():
    try:
        content = _download_sipa_bytes()
        h = hashlib.sha1(content).hexdigest()
        return _parse_sipa(h, content)
    except Exception:
        # producción: devolver vacíos (tu página ya muestra el error genérico)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
