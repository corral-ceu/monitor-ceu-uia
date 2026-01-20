import numpy as np
import pandas as pd


def fmt(n, dec: int = 2, es_puestos: bool = False) -> str:
    if pd.isna(n) or n is None:
        return "s/d"
    formatted = f"{n:,.0f}" if es_puestos else f"{n:,.{dec}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def obtener_nombre_mes(fecha) -> str:
    if pd.isna(fecha):
        return "s/d"
    meses = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    return f"{meses[fecha.month - 1]} {fecha.year}"


def calc_var(serie: pd.Series, lag: int) -> float:
    if len(serie) <= lag:
        return np.nan
    den = serie.iloc[-lag - 1]
    if den == 0 or pd.isna(den):
        return np.nan
    return (serie.iloc[-1] / den - 1) * 100
