import streamlit as st


def apply_global_styles() -> None:
    """Estilos globales (unifica look)."""
    st.markdown(
        """
        <style>
          /* Base */
          .stApp { color: #0b2b4c !important; }
          h1,h2,h3,h4,p,span,div,label { color: #0b2b4c !important; }
          [data-testid="stMetricValue"] { color: #0b2b4c !important; font-weight: 800 !important; }
          [data-testid="stMetricLabel"] { color: #526484 !important; font-weight: 600 !important; }

          /* Fondo gris claro */
          [data-testid="stAppViewContainer"] { background: #f2f4f7; }

          /* Cards de Home */
          .home-wrap{
            max-width: 980px;
            margin: 0 auto;
            padding-top: 10px;
            text-align: center;
          }
          .home-title{
            font-size: 44px;
            font-weight: 800;
            color: #0b2b4c;
            margin-bottom: 10px;
          }
          .home-subtitle{
            font-size: 18px;
            color: #243447;
            margin-bottom: 28px;
          }
          .home-cards div.stButton > button{
            width: 100% !important;
            background: #dbeafe !important;
            border: 1px solid rgba(11,43,76,0.18) !important;
            border-radius: 18px !important;
            padding: 18px 18px !important;
            height: 92px !important;
            box-shadow: 0 8px 22px rgba(0,0,0,0.06) !important;
            transition: all 0.15s ease-in-out !important;
            color: #0b2b4c !important;
            font-weight: 800 !important;
            font-size: 20px !important;
            white-space: pre-line !important;
          }
          .home-cards div.stButton > button:hover{
            transform: translateY(-2px);
            box-shadow: 0 12px 28px rgba(0,0,0,0.10) !important;
            border-color: rgba(11,43,76,0.30) !important;
          }

          /* Cards internas */
          .macro-card {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #cbd5e1;
            margin-bottom: 10px;
            color: #0b2b4c;
            box-shadow: 0 6px 16px rgba(0,0,0,0.05);
          }

          @media (max-width: 900px){
            .home-title{ font-size: 36px; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
