import calendar
import json
from datetime import datetime, date
import pandas as pd
import streamlit as st
import requests

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Cuadrante SAT CI Repsol", layout="wide")

# ==========================================
# SISTEMA DE AUTENTICACIÓN (USUARIO / CONTRASEÑA)
# ==========================================
def verificar_autenticacion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h2 style='color:#005B7F; text-align:center;'>Acceso - Cuadrante SAT CI Repsol</h2>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Iniciar Sesión")

            if submit_login:
                # Puedes cambiar o enlazar esto con st.secrets para mayor seguridad
                try:
                    user_valido = st.secrets["auth"]["usuario"]
                    pass_valido = st.secrets["auth"]["password"]
                except Exception:
                    # Credenciales por defecto si no están en secrets.toml
                    user_valido = "admin"
                    pass_valido = "repsol2026"

                if usuario == user_valido and password == pass_valido:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

# Si no está autenticado, detener la ejecución aquí para pedir credenciales
if not verificar_autenticacion():
    st.stop()

# ==========================================
# CONFIGURACIÓN Y CONSTANTES
# ==========================================
ANOS_DISPONIBLES = [2026, 2027, 2028, 2029, 2030]
RUTA_BDD = "datos_tecnicos_repsol.json"
RUTA_FESTIVOS = "festivos_repsol.json"
RUTA_HE = "he_repsol.json"
RUTA_CONFIG_ANUAL = "config_anual_repsol.json"
RUTA_HORARIOS_CI = "horarios_ci_repsol.json"
RUTA_HLD_ANUAL = "hld_anual_repsol.json"

# (El resto de funciones de persistencia y la aplicación continúan aquí...)
