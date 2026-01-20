import numpy as np
import pandas as pd
import streamlit as st

from services.ipi_data import cargar_ipi_excel, procesar_serie_excel
from services.metrics import calc_var, fmt, obtener_nombre_mes


def render_ipi(go_to):
    if st.button("← Volver"):
        go_to("home")

    st.markdown("## 🏭 Producción Industrial")
    st.caption("Fuente: INDEC – IPI Manufacturero (Excel)")
    st.divider()

    if "ipi_sel_div" not in st.session_state:
        st.session_state.ipi_sel_div = None

    df_c2, df_c5 = cargar_ipi_excel()
    if df_c2 is None or df_c5 is None:
        st.error("Error al descargar el archivo del INDEC.")
        return

    names_c2 = [str(x).strip() for x in df_c2.iloc[3].fillna("").tolist()]
    codes_c2 = [str(x).strip() for x in df_c2.iloc[2].fillna("").tolist()]
    names_c5 = [str(x).strip() for x in df_c5.iloc[3].fillna("").tolist()]

    ng_sa = procesar_serie_excel(df_c5, 3)
    ng_orig = procesar_serie_excel(df_c2, 3)

    if ng_sa.empty or ng_orig.empty:
        st.warning("No se pudieron extraer series del Excel.")
        return

    m_ng = calc_var(ng_sa["valor"], 1)
    i_ng = calc_var(ng_orig["valor"], 12)

    st.subheader(f"IPI Manufacturero - {obtener_nombre_mes(ng_sa['fecha'].iloc[-1])}")
    m_cols = st.columns(2)
    m_cols[0].metric("Variación Mensual (SA)", f"{fmt(m_ng, 1)}%")
    m_cols[1].metric("Variación Interanual", f"{fmt(i_ng, 1)}%")

    st.write("#### Divisiones Industriales")
    divs_idxs = [
        i
        for i, n in enumerate(names_c5)
        if i >= 3 and i % 2 != 0 and n not in ("", "Período", "IPI Manufacturero")
    ]

    for i in range(0, len(divs_idxs), 3):
        cols = st.columns(3)
        for j, idx in enumerate(divs_idxs[i : i + 3]):
            name = names_c5[idx]
            s_sa = procesar_serie_excel(df_c5, idx)

            try:
                idx_c2 = names_c2.index(name)
                s_orig = procesar_serie_excel(df_c2, idx_c2)
                v_i = calc_var(s_orig["valor"], 12)
                raw_code = codes_c2[idx_c2]
            except Exception:
                v_i = np.nan
                raw_code = None

            v_m = calc_var(s_sa["valor"], 1)

            with cols[j]:
                st.markdown(
                    f'<div class="macro-card"><b>{name}</b><br>'
                    f'Mensual (SA): {fmt(v_m, 1)}%<br>'
                    f'Interanual: {fmt(v_i, 1)}%</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Ver detalle", key=f"ipi_btn_{idx}"):
                    if raw_code:
                        st.session_state.ipi_sel_div = (name, raw_code)
                    else:
                        st.warning("Código no encontrado para esa división.")

    if st.session_state.ipi_sel_div:
        div_name, div_code = st.session_state.ipi_sel_div
        st.divider()
        st.subheader(f"Detalle de Subclases: {div_name}")

        prefixes = [p.strip() for p in str(div_code).split("-") if p.strip()]
        if "36" in prefixes:
            prefixes.append("33")

        sub_list = []
        for i, code in enumerate(codes_c2):
            code_s = str(code).strip()
            if any(code_s.startswith(p) for p in prefixes) and code_s not in prefixes and code_s not in [
                "20-22",
                "36-37",
                "17-18",
                "13-14",
                "24-25",
            ]:
                s = procesar_serie_excel(df_c2, i)
                if not s.empty:
                    sub_list.append({"Subclase": names_c2[i], "Variación Interanual (%)": calc_var(s["valor"], 12)})

        if sub_list:
            df_sub = pd.DataFrame(sub_list).dropna()
            st.dataframe(df_sub.style.format({"Variación Interanual (%)": "{:,.2f}%"}), width="stretch")
        else:
            st.info("No hay desglose adicional disponible.")
