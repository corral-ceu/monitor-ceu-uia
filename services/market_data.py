# services/market_data.py
from __future__ import annotations

import pandas as pd
import streamlit as st

# yfinance opcional
try:
    import yfinance as yf
except Exception:
    yf = None





import time

def _history_one(ticker: str, start: str) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance no está disponible (pip install yfinance).")

    t = yf.Ticker(ticker)

    last_err = None
    for _ in range(2):  # 2 intentos
        try:
            df = t.history(start=start, auto_adjust=False)  # daily
            if df is None or df.empty:
                raise RuntimeError(f"Yahoo devolvió vacío para {ticker}")
            df = df.copy()

            idx = pd.to_datetime(df.index, errors="coerce")
            # quitar tz solo si existe
            try:
                if getattr(idx, "tz", None) is not None:
                    idx = idx.tz_convert(None)
            except Exception:
                try:
                    idx = idx.tz_localize(None)
                except Exception:
                    pass

            df.index = idx
            return df

        except Exception as e:
            last_err = e
            time.sleep(0.3)  # micro pausa

    # IMPORTANTE: tirar error para NO cachear vacío
    raise RuntimeError(f"history() falló para {ticker}: {last_err}")



def _pick_price_single(df: pd.DataFrame, prefer_adj: bool = False) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype="float64")
    if prefer_adj and "Adj Close" in df.columns:
        return df["Adj Close"].astype("float64")
    if "Close" in df.columns:
        return df["Close"].astype("float64")
    # fallback
    for c in ["Adj Close", "Open", "High", "Low"]:
        if c in df.columns:
            return df[c].astype("float64")
    raise KeyError(f"No encuentro columnas de precio. cols={list(df.columns)}")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_ypf_ars_history(start: str = "2000-01-01", prefer_adj: bool = False) -> pd.Series:
    df = _history_one("YPFD.BA", start=start)
    s = _pick_price_single(df, prefer_adj=prefer_adj)
    s.name = "YPF_ARS"
    return s.dropna()


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_ypf_usd_history(start: str = "1993-01-01", prefer_adj: bool = False) -> pd.Series:
    df = _history_one("YPF", start=start)
    s = _pick_price_single(df, prefer_adj=prefer_adj)
    s.name = "YPF_USD"
    return s.dropna()


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_ccl_ypf_history(start: str = "2000-01-01", prefer_adj: bool = False) -> pd.Series:
    """
    CCL proxy diario: YPFD.BA (ARS) / YPF (USD)
    """
    s_ars = get_ypf_ars_history(start=start, prefer_adj=prefer_adj)
    s_usd = get_ypf_usd_history(start="1993-01-01", prefer_adj=prefer_adj)

    df = pd.concat([s_ars, s_usd], axis=1, join="inner").dropna()
    df["CCL_YPF"] = df["YPF_ARS"] / df["YPF_USD"]

    out = df["CCL_YPF"].replace([float("inf"), -float("inf")], pd.NA).dropna()
    out.name = "CCL_YPF"
    return out


def get_ccl_ypf_df(start: str = "2000-01-01", prefer_adj: bool = False) -> pd.DataFrame:
    """
    Devuelve DataFrame con columnas Date, value (estándar para tus plots).
    """
    s = get_ccl_ypf_history(start=start, prefer_adj=prefer_adj)
    return s.rename("value").reset_index().rename(columns={"index": "Date"})


import time

@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_ccl_ypf_df_fast(period: str = "2y", prefer_adj: bool = False) -> pd.DataFrame:
    """
    CCL proxy diario liviano (igual estilo que macro_home):
    usa yf.download con period corto para evitar history(start=1993).
    Devuelve DataFrame: Date, value
    """
    if yf is None:
        return pd.DataFrame(columns=["Date", "value"])

    def _get_close(dl, ticker: str) -> pd.Series:
        # dl es DataFrame con MultiIndex cols cuando pedís varios tickers
        # Queremos Close de cada ticker
        if dl is None or dl.empty:
            return pd.Series(dtype="float64")

        if isinstance(dl.columns, pd.MultiIndex):
            # formato: (campo, ticker) o (ticker, campo) depende
            if ("Close", ticker) in dl.columns:
                s = dl[("Close", ticker)]
            elif (ticker, "Close") in dl.columns:
                s = dl[(ticker, "Close")]
            else:
                # fallback: buscar "Close" en el segundo nivel
                candidates = [c for c in dl.columns if "Close" in c]
                s = dl[candidates[0]] if candidates else pd.Series(dtype="float64")
        else:
            # si viniera plano (raro en multi-ticker), probar Close
            s = dl["Close"] if "Close" in dl.columns else pd.Series(dtype="float64")

        s = s.copy()
        s.index = pd.to_datetime(s.index, errors="coerce")
        try:
            s.index = s.index.tz_localize(None)
        except Exception:
            pass
        s.index = s.index.normalize()
        return pd.to_numeric(s, errors="coerce").dropna()

    last_err = None
    for _ in range(2):  # reintento rápido
        try:
            dl = yf.download(
                ["YPFD.BA", "YPF"],
                period=period,
                progress=False,
                auto_adjust=False,
                group_by="column",
                threads=False,     # clave: no más subthreads
            )
            s_ars = _get_close(dl, "YPFD.BA")
            s_usd = _get_close(dl, "YPF")

            df = pd.concat([s_ars.rename("YPF_ARS"), s_usd.rename("YPF_USD")], axis=1).dropna()
            if df.empty:
                raise RuntimeError("download devolvió vacío para YPFD.BA/YPF")

            df["value"] = (df["YPF_ARS"] / df["YPF_USD"]).replace([float("inf"), -float("inf")], pd.NA)
            out = df[["value"]].dropna().reset_index().rename(columns={"index": "Date"})
            return out

        except Exception as e:
            last_err = e
            time.sleep(0.25)

    # No caches vacío “silencioso”: devolvemos vacío pero con columnas
    return pd.DataFrame(columns=["Date", "value"])




@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_ticker_history(
    ticker: str,
    start: str = "2000-01-01",
    prefer_adj: bool = False,
) -> pd.Series:
    """
    Serie diaria (Close o Adj Close) para cualquier ticker de Yahoo.
    NO toca tus funciones existentes.
    """
    df = _history_one(ticker, start=start)
    s = _pick_price_single(df, prefer_adj=prefer_adj)
    s.name = ticker
    return s.dropna()


def series_to_df(s: pd.Series) -> pd.DataFrame:
    """Convierte Series index datetime a DataFrame estándar Date/value."""
    return s.rename("value").reset_index().rename(columns={"index": "Date"})


def get_ticker_df(
    ticker: str,
    start: str = "2000-01-01",
    prefer_adj: bool = False,
) -> pd.DataFrame:
    """Wrapper estándar para plots."""
    return series_to_df(get_ticker_history(ticker, start=start, prefer_adj=prefer_adj))


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_ratio_history(
    num_ticker: str,
    den_ticker: str,
    start: str = "2000-01-01",
    prefer_adj: bool = False,
    name: str | None = None,
) -> pd.Series:
    """
    Ratio diario: num/den (ej: ARS/BRL, CCL proxy, etc.)
    NO reemplaza tu CCL; solo lo complementa.
    """
    s1 = get_ticker_history(num_ticker, start=start, prefer_adj=prefer_adj)
    s2 = get_ticker_history(den_ticker, start=start, prefer_adj=prefer_adj)

    df = pd.concat([s1, s2], axis=1, join="inner").dropna()
    out = (df.iloc[:, 0] / df.iloc[:, 1]).replace([float("inf"), -float("inf")], pd.NA).dropna()
    out.name = name or f"{num_ticker}/{den_ticker}"
    return out





# ============================================================
# EMBI / Riesgo País (BCRA) — XLSX Serie_Historica_Spread_del_EMBI.xlsx
# Devuelve formato largo: Date, Serie, Value
# ============================================================

EMBI_XLSX_URL = "https://bcrdgdcprod.blob.core.windows.net/documents/entorno-internacional/documents/Serie_Historica_Spread_del_EMBI.xlsx"

@st.cache_data(ttl=12 * 60 * 60, show_spinner=False)
def get_embi_spread_long() -> pd.DataFrame:
    """
    Descarga el Excel del BCRA con spreads EMBI y lo devuelve en formato largo:
      Date (datetime), Serie (str), Value (float)
    """
    try:
        df = pd.read_excel(EMBI_XLSX_URL, engine="openpyxl")
    except Exception as e:
        st.warning(f"EMBI XLSX error: {e}")
        return pd.DataFrame(columns=["Date", "Serie", "Value"])

    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Serie", "Value"])

    # Normalizar nombres por si vienen con espacios raros
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Primera columna suele ser "Fecha" (como en tu captura)
    date_col = None
    for cand in ["Fecha", "fecha", "Date", "date"]:
        if cand in df.columns:
            date_col = cand
            break
    if date_col is None:
        # fallback: primera columna
        date_col = df.columns[0]

    df = df.rename(columns={date_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")

    # Todo lo demás numérico
    value_cols = [c for c in df.columns if c != "Date"]
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    long_df = (
        df.melt(id_vars=["Date"], value_vars=value_cols, var_name="Serie", value_name="Value")
          .dropna(subset=["Value"])
          .sort_values(["Serie", "Date"])
          .reset_index(drop=True)
    )

    # Limpieza suave de nombres
    long_df["Serie"] = long_df["Serie"].astype(str).str.strip()

    return long_df
