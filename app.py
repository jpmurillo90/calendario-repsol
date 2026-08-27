import json
import os
import requests
import streamlit as st
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Calendario Técnico - Repsol Puertollano",
    page_icon="📅",
    layout="wide",
)

# ---------------------------------------------------------
# 1. GESTIÓN DE DATOS CON GIST / LOCAL
# ---------------------------------------------------------
ARCHIVO_LOCAL = "datos_tecnicos_repsol.json"


def cargar_datos():
    # Intentar cargar desde Gist (si está en la nube y configurado)
    try:
        if "GIST_ID" in st.secrets and "GITHUB_TOKEN" in st.secrets:
            gist_id = st.secrets["GIST_ID"]
            token = st.secrets["GITHUB_TOKEN"]
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if ARCHIVO_LOCAL in files:
                    content = files[ARCHIVO_LOCAL]["content"]
                    return json.loads(content)
    except Exception:
        pass

    # Si falla o no está en la nube, usar archivo local
    if os.path.exists(ARCHIVO_LOCAL):
        try:
            with open(ARCHIVO_LOCAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_datos(datos):
    # Guardar siempre en local primero
    try:
        with open(ARCHIVO_LOCAL, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

    # Intentar sincronizar con GitHub Gist si está configurado
    try:
        if "GIST_ID" in st.secrets and "GITHUB_TOKEN" in st.secrets:
            gist_id = st.secrets["GIST_ID"]
            token = st.secrets["GITHUB_TOKEN"]
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {
                    ARCHIVO_LOCAL: {
                        "content": json.dumps(datos, ensure_ascii=False, indent=4)
                    }
                }
            }
            requests.patch(url, headers=headers, json=payload)
    except Exception:
        pass


# ---------------------------------------------------------
# 2. SISTEMA DE AUTENTICACIÓN
# ---------------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.rol_actual = None

st.sidebar.title("🔐 Control de Acceso")

if not st.session_state.autenticado:
    st.sidebar.subheader("Iniciar Sesión")
    usuario_input = st.sidebar.text_input("Usuario")
    password_input = st.sidebar.text_input("Contraseña", type="password")

    if st.sidebar.button("Entrar"):
        # Usuarios por defecto si no están en secrets
        usuarios_validos = {
            "juanpedro": {
                "password": "123",
                "nombre": "Juan Pedro Murillo Huete",
                "rol": "Editor",
            },
            "david": {
                "password": "123",
                "nombre": "David Muñoz Burguillo",
                "rol": "Editor",
            },
            "sandra": {
                "password": "123",
                "nombre": "Sandra Bellido",
                "rol": "Editor",
            },
            "lector": {
                "password": "123",
                "nombre": "Técnico Consulta",
                "rol": "Lector",
            },
        }

        # Cargar desde secrets si existe el bloque
        if "usuarios" in st.secrets:
            usuarios_validos = st.secrets["usuarios"]

        if (
            usuario_input in usuarios_validos
            and usuarios_validos[usuario_input]["password"] == password_input
        ):
            st.session_state.autenticado = True
            st.session_state.usuario_actual = usuarios_validos[usuario_input][
                "nombre"
            ]
            st.session_state.rol_actual = usuarios_validos[usuario_input]["rol"]
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos")

    st.stop()  # Detiene la ejecución de la app hasta que inicie sesión
else:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_actual}")
    st.sidebar.info(f"Perfil: {st.session_state.rol_actual}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.session_state.rol_actual = None
        st.rerun()


# ---------------------------------------------------------
# 3. INTERFAZ PRINCIPAL DE LA APLICACIÓN
# ---------------------------------------------------------
st.title("📅 Calendario Técnico - Puertollano")

# Cargar base de datos actual
db_turnos = cargar_datos()

# Listas de técnicos y marcas
tecnicos = [
    "Juan Pedro Murillo Huete",
    "David Muñoz Burguillo",
    "Sandra Bellido",
    "Antonio Gómez",
    "María Pérez",
]

marcas = {
    "VPA - Vacaciones Pendientes Año Anterior": "VPA",
    "VAC - Vacaciones Ordinarias": "VAC",
    "HLD - Horas Libres Disponibles": "HLD",
    "FEST - Día Festivo": "FEST",
}

# --- SECCIÓN DE REGISTRO (Solo para EDITORES) ---
if st.session_state.rol_actual == "Editor":
    st.markdown("### 📝 Registrar / Modificar Turnos")
    col1, col2, col3 = st.columns(3)

    with col1:
        tecnico_sel = st.selectbox("Técnico:", tecnicos)
    with col2:
        mes_sel = st.selectbox(
            "Mes:",
            [
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
            ],
        )
    with col3:
        dia_inicio = st.number_input(
            "Día Inicio:", min_value=1, max_value=31, value=1
        )

    col4, col5 = st.columns(2)
    with col4:
        dia_fin = st.number_input("Día Fin:", min_value=1, max_value=31, value=1)
    with col5:
        marca_sel = st.selectbox("Marca:", list(marcas.keys()))

    codigo_marca = marcas[marca_sel]
    meses_dict = {
        "Enero": 1,
        "Febrero": 2,
        "Marzo": 3,
        "Abril": 4,
        "Mayo": 5,
        "Junio": 6,
        "Julio": 7,
        "Agosto": 8,
        "Septiembre": 9,
        "Octubre": 10,
        "Noviembre": 11,
        "Diciembre": 12,
    }
    mes_num = meses_dict[mes_sel]
    anio_actual = 2026

    if st.button("Guardar Rango", type="primary"):
        if dia_inicio > dia_fin:
            st.error("El día de inicio no puede ser mayor que el día de fin.")
        else:
            for d in range(dia_inicio, dia_fin + 1):
                clave = f"{anio_actual}|{tecnico_sel}|{mes_num}|{d}"
                db_turnos[clave] = codigo_marca
            guardar_datos(db_turnos)
            st.success(
                f"Registros guardados correctamente del {dia_inicio} al {dia_fin} de {mes_sel} para {tecnico_sel}."
            )
else:
    st.info(
        "👁️ Estás visualizando la aplicación en modo **Lector**. Para modificar turnos, inicia sesión con una cuenta de Editor."
    )
    tecnico_sel = st.selectbox("Seleccionar Técnico para ver:", tecnicos)
    mes_sel = st.selectbox(
        "Mes:",
        [
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
        ],
    )
    meses_dict = {
        "Enero": 1,
        "Febrero": 2,
        "Marzo": 3,
        "Abril": 4,
        "Mayo": 5,
        "Junio": 6,
        "Julio": 7,
        "Agosto": 8,
        "Septiembre": 9,
        "Octubre": 10,
        "Noviembre": 11,
        "Diciembre": 12,
    }
    mes_num = meses_dict[mes_sel]
    anio_actual = 2026

# --- VISTA DEL CALENDARIO ---
st.markdown("---")
st.subheader(f"🗓️ Vista: {mes_sel} {anio_actual} - {tecnico_sel}")

# Tabla simple de visualización mensual de ejemplo
import calendar

cal = calendar.monthcalendar(anio_actual, mes_num)

dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
filas_calendario = []

for semana in cal:
    fila = []
    for idx_dia, dia in enumerate(semana):
        if dia == 0:
            fila.append("")
        else:
            clave_busqueda = f"{anio_actual}|{tecnico_sel}|{mes_num}|{dia}"
            estado = db_turnos.get(clave_busqueda, "")
            texto_celda = f"{dia}\n**{estado}**" if estado else str(dia)
            fila.append(texto_celda)
    filas_calendario.append(fila)

import pandas as pd

df_calendario = pd.DataFrame(filas_calendario, columns=dias_semana)
st.dataframe(df_calendario, use_container_width=True, hide_index=True)
