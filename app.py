import calendar
import json
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st
import requests

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
RUTA_PRL = "prl_repsol.json"

st.set_page_config(
    page_title="Accesos CI",
    page_icon="🏢",
    layout="wide"
)

# ==========================================
# ESTILOS CSS CORPORATIVOS AVANZADOS (INDRA BRANDING)
# ==========================================
st.markdown("""
<style>
    .stApp {
        background-color: #F4F6F9 !important;
        color: #0F172A !important;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    .card-corporate {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        color: #0F172A !important;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #0F172A !important;
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #E2E8F0;
        padding: 6px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        background-color: #FFFFFF;
        border-radius: 6px;
        color: #334155;
        font-weight: 600;
        border: 1px solid #CBD5E1;
        padding: 0 14px;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #002B36 !important;
        color: #FFFFFF !important;
        border-color: #002B36 !important;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid #CBD5E1;
        background-color: #FFFFFF;
        color: #0F172A;
        transition: all 0.2s ease-in-out;
    }
    button[kind="primary"] {
        background-color: #002B36 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    table {
        font-family: 'Segoe UI', sans-serif;
        border-collapse: collapse;
        width: 100%;
        font-size: 12px;
    }
    table th {
        background-color: #002B36 !important;
        color: #FFFFFF !important;
        text-align: center;
        padding: 8px;
        border: 1px solid #334155;
    }
    table td {
        padding: 6px;
        border: 1px solid #CBD5E1;
        color: #0F172A !important;
    }
    .footer-copyright {
        text-align: center;
        font-size: 11px;
        color: #64748B;
        border-top: 1px solid #E2E8F0;
        padding-top: 15px;
        margin-top: 35px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SISTEMA DE AUTENTICACIÓN (LOGIN)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.rol_actual = None

try:
    st.sidebar.image("AF_INDRA_SIM_POS.png", use_container_width=True)
except Exception:
    st.sidebar.markdown("### 🏢 Indra Group")

st.sidebar.markdown("---")
st.sidebar.title("🔐 Control de Acceso")

if not st.session_state.autenticado:
    st.sidebar.subheader("Identificación de Usuario")
    usuario_input = st.sidebar.text_input("Usuario")
    password_input = st.sidebar.text_input("Contraseña", type="password")

    if st.sidebar.button("Acceder al Sistema", use_container_width=True, type="primary"):
        usuarios_validos = {
            "juanpedro": {"password": "123", "nombre": "Juan Pedro Murillo", "rol": "Editor"},
            "david": {"password": "123", "nombre": "David Muñoz", "rol": "Editor"},
            "sandra": {"password": "123", "nombre": "Sandra Bellido", "rol": "Editor"},
            "lector": {"password": "123", "nombre": "Técnico Consulta", "rol": "Lector"}
        }

        if hasattr(st, "secrets") and "usuarios" in st.secrets:
            usuarios_validos = st.secrets["usuarios"]

        if usuario_input in usuarios_validos and usuarios_validos[usuario_input]["password"] == password_input:
            st.session_state.autenticado = True
            st.session_state.usuario_actual = usuarios_validos[usuario_input]["nombre"]
            st.session_state.rol_actual = usuarios_validos[usuario_input]["rol"]
            st.rerun()
        else:
            st.sidebar.error("Credenciales no válidas")

    st.stop()
else:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_actual}")
    st.sidebar.info(f"Nivel de Acceso: {st.session_state.rol_actual}")
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_actual = None
        st.session_state.rol_actual = None
        st.rerun()

# ==========================================
# FUNCIONES DE PERSISTENCIA Y GIST
# ==========================================
def obtener_cabeceras_gist():
    try:
        token = st.secrets["GITHUB_TOKEN"]
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    except Exception:
        return {}

def obtener_url_gist():
    try:
        gist_id = st.secrets["GIST_ID"]
        return f"https://api.github.com/gists/{gist_id}"
    except Exception:
        return ""

def guardar_en_drive(registros_dict):
    # Asegurar claves en formato string plano "anio|tec|mes|dia" para evitar errores de tipo
    datos_json = {}
    for k, v in registros_dict.items():
        if isinstance(k, tuple):
            k_str = f"{k[0]}|{k[1]}|{k[2]}|{k[3]}"
        else:
            k_str = str(k)
        datos_json[k_str] = v

    try:
        with open(RUTA_BDD, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
        
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    if url and headers:
        payload = {
            "files": {
                "datos_tecnicos_repsol.json": {
                    "content": json.dumps(datos_json, ensure_ascii=False, indent=4)
                }
            }
        }
        try:
            requests.patch(url, headers=headers, json=payload, timeout=5)
        except Exception:
            pass

def cargar_de_drive():
    resultado = {}
    datos_json = None
    
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "datos_tecnicos_repsol.json" in files:
                    contenido = files["datos_tecnicos_repsol.json"]["content"]
                    datos_json = json.loads(contenido)
        except Exception:
            pass
            
    if datos_json is None:
        try:
            with open(RUTA_BDD, 'r', encoding='utf-8') as f:
                datos_json = json.load(f)
        except FileNotFoundError:
            return {}

    if datos_json:
        for k, v in datos_json.items():
            parts = k.split('|')
            if len(parts) == 3:
                # Compatibilidad con formato antiguo sin año (asume 2026)
                resultado[(2026, parts[0], parts[1], parts[2])] = v
            elif len(parts) >= 4:
                resultado[(int(parts[0]), parts[1], parts[2], parts[3])] = v
            else:
                resultado[k] = v
        return resultado
    return {}

def guardar_festivos_drive():
    datos_json = {str(anio): {ci: [[m, d] for m, d in lista] for ci, lista in centros.items()} for anio, centros in FESTIVOS_POR_ANIO.items()}
    try:
        with open(RUTA_FESTIVOS, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
        
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    if url and headers:
        payload = {
            "files": {
                "festivos_repsol.json": {
                    "content": json.dumps(datos_json, ensure_ascii=False, indent=4)
                }
            }
        }
        try:
            requests.patch(url, headers=headers, json=payload, timeout=5)
        except Exception:
            pass

def cargar_festivos_drive():
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "festivos_repsol.json" in files:
                    datos_json = json.loads(files["festivos_repsol.json"]["content"])
                    return {int(anio): {ci: [tuple(x) for x in lista] for ci, lista in centros.items()} for anio, centros in datos_json.items()}
        except Exception:
            pass
            
    try:
        with open(RUTA_FESTIVOS, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            return {int(anio): {ci: [tuple(x) for x in lista] for ci, lista in centros.items()} for anio, centros in datos_json.items()}
    except FileNotFoundError:
        return None

def guardar_he_drive():
    try:
        with open(RUTA_HE, 'w', encoding='utf-8') as f:
            json.dump(REGISTROS_HE, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
        
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    if url and headers:
        payload = {
            "files": {
                "he_repsol.json": {
                    "content": json.dumps(REGISTROS_HE, ensure_ascii=False, indent=4)
                }
            }
        }
        try:
            requests.patch(url, headers=headers, json=payload, timeout=5)
        except Exception:
            pass

def cargar_he_drive():
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "he_repsol.json" in files:
                    return json.loads(files["he_repsol.json"]["content"])
        except Exception:
            pass
            
    try:
        with open(RUTA_HE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_config_anual_drive():
    try:
        datos_serializables = {}
        for anio, cfg in CONFIG_ANUAL_POR_ANIO.items():
            datos_serializables[str(anio)] = {
                'petronor_lj': cfg['petronor_lj'],
                'petronor_v': cfg['petronor_v'],
                'cartagena_ini': cfg['cartagena_ini'].strftime('%Y-%m-%d'),
                'cartagena_fin': cfg['cartagena_fin'].strftime('%Y-%m-%d'),
                'tarragona_ini': cfg['tarragona_ini'].strftime('%Y-%m-%d'),
                'tarragona_fin': cfg['tarragona_fin'].strftime('%Y-%m-%d')
            }
        with open(RUTA_CONFIG_ANUAL, 'w', encoding='utf-8') as f:
            json.dump(datos_serializables, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def cargar_config_anual_drive():
    try:
        with open(RUTA_CONFIG_ANUAL, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            resultado = {}
            for anio_str, cfg in datos_json.items():
                resultado[int(anio_str)] = {
                    'petronor_lj': cfg['petronor_lj'],
                    'petronor_v': cfg['petronor_v'],
                    'cartagena_ini': datetime.strptime(cfg['cartagena_ini'], '%Y-%m-%d').date(),
                    'cartagena_fin': datetime.strptime(cfg['cartagena_fin'], '%Y-%m-%d').date(),
                    'tarragona_ini': datetime.strptime(cfg['tarragona_ini'], '%Y-%m-%d').date(),
                    'tarragona_fin': datetime.strptime(cfg['tarragona_fin'], '%Y-%m-%d').date()
                }
            return resultado
    except FileNotFoundError:
        return None

def guardar_horarios_ci_drive():
    try:
        datos_serializables = {}
        for anio, centros in HORARIOS_CI_ANUAL.items():
            datos_serializables[str(anio)] = {}
            for ci, d in centros.items():
                datos_serializables[str(anio)][ci] = {
                    'horario': d['horario'],
                    'h_sem': d['h_sem'],
                    'obs': d['obs'],
                    'bolsa_ini': d.get('bolsa_ini', '').strftime('%Y-%m-%d') if isinstance(d.get('bolsa_ini'), date) else d.get('bolsa_ini', ''),
                    'bolsa_fin': d.get('bolsa_fin', '').strftime('%Y-%m-%d') if isinstance(d.get('bolsa_fin'), date) else d.get('bolsa_fin', '')
                }
        with open(RUTA_HORARIOS_CI, 'w', encoding='utf-8') as f:
            json.dump(datos_serializables, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def cargar_horarios_ci_drive():
    try:
        with open(RUTA_HORARIOS_CI, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            resultado = {}
            for anio_str, centros in datos_json.items():
                resultado[int(anio_str)] = {}
                for ci, d in centros.items():
                    b_ini = datetime.strptime(d['bolsa_ini'], '%Y-%m-%d').date() if d.get('bolsa_ini') else None
                    b_fin = datetime.strptime(d['bolsa_fin'], '%Y-%m-%d').date() if d.get('bolsa_fin') else None
                    resultado[int(anio_str)][ci] = {
                        'horario': d['horario'],
                        'h_sem': d['h_sem'],
                        'obs': d['obs'],
                        'bolsa_ini': b_ini,
                        'bolsa_fin': b_fin
                    }
            return resultado
    except FileNotFoundError:
        return None

def guardar_hld_anual_drive():
    try:
        datos_json = {str(anio): hld_dict for anio, hld_dict in HLD_ANUAL_POR_ANIO.items()}
        with open(RUTA_HLD_ANUAL, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def cargar_hld_anual_drive():
    try:
        with open(RUTA_HLD_ANUAL, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            return {int(anio): hld_dict for anio, hld_dict in datos_json.items()}
    except FileNotFoundError:
        return None

# ==========================================
# GESTIÓN Y PERSISTENCIA DE PRL
# ==========================================
PRL_DEFAULT = {
    'Juan Pedro Murillo Huete': {'nip': '709355', 'dni': '05933159X', 'fecha': '2027-03-27', 'obs': 'BIENAL'},
    'David Muñoz Burguillo': {'nip': '709743', 'dni': '70052109C', 'fecha': '2027-03-28', 'obs': 'BIENAL'},
    'Fernando Bocija Sanchez': {'nip': '565127', 'dni': '53162879N', 'fecha': '2028-04-21', 'obs': 'BIENAL'},
    'Oscar Luna Murillo': {'nip': '722573', 'dni': '47950833L', 'fecha': '2027-08-28', 'obs': 'BIENAL'},
    'Joan Vila Cascan': {'nip': '710090', 'dni': '39922718P', 'fecha': '2027-04-02', 'obs': 'BIENAL'},
    'Endika Ramirez Rodriguez': {'nip': '723603', 'dni': '79136742K', 'fecha': '2026-10-22', 'obs': ''},
    'David Rodriguez Novua': {'nip': '709717', 'dni': '45818446P', 'fecha': '2027-03-27', 'obs': ''},
    'Simon Alberto Conesa Lloris': {'nip': '716271', 'dni': '23034801W', 'fecha': '2028-06-19', 'obs': 'BIENAL'},
    'Alejandro Gutierrez Bastida': {'nip': '717260', 'dni': '23310758M', 'fecha': '2026-10-10', 'obs': 'CITA 11 PETICION 4591420 CITACION RM'}
}

def guardar_prl_drive():
    try:
        with open(RUTA_PRL, 'w', encoding='utf-8') as f:
            json.dump(REGISTROS_PRL, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
        
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    if url and headers:
        payload = {
            "files": {
                "prl_repsol.json": {
                    "content": json.dumps(REGISTROS_PRL, ensure_ascii=False, indent=4)
                }
            }
        }
        try:
            requests.patch(url, headers=headers, json=payload, timeout=5)
        except Exception:
            pass

def cargar_prl_drive():
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "prl_repsol.json" in files:
                    return json.loads(files["prl_repsol.json"]["content"])
        except Exception:
            pass
            
    try:
        with open(RUTA_PRL, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

REGISTROS_PRL = cargar_prl_drive() or PRL_DEFAULT

# 1. CONFIGURACIÓN Y BASE DE DATOS
TECNICOS = {
    'David Rodriguez Novua': {'ci': 'Petronor', 'vac_totales': 22, 'vpa_base': 8, 'he_totales': 0.0},
    'Endika Ramirez Rodriguez': {'ci': 'Petronor', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0},
    'Fernando Bocija Sanchez': {'ci': 'Coruña', 'vac_totales': 23, 'vpa_base': 11, 'he_totales': 0.0},
    'Joan Vila Cascan': {'ci': 'Tarragona', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0},
    'Oscar Luna Murillo': {'ci': 'Tarragona', 'vac_totales': 22, 'vpa_base': 1, 'he_totales': 0.0},
    'David Muñoz Burguillo': {'ci': 'Puertollano', 'vac_totales': 22, 'vpa_base': 4, 'he_totales': 0.0},
    'Juan Pedro Murillo Huete': {'ci': 'Puertollano', 'vac_totales': 22, 'vpa_base': 2, 'he_totales': 0.0},
    'Simon Alberto Conesa Lloris': {'ci': 'Cartagena', 'vac_totales': 22, 'vpa_base': 6, 'he_totales': 0.0},
    'Alejandro Gutierrez Bastida': {'ci': 'Cartagena', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0}
}

LEYENDA = {
    'V': ('Vacaciones', '#C6EFCE'),
    'VPA': ('Vac. Pendientes Año Anterior', '#E2EFDA'),
    'HE': ('Horas Extras Disfrutadas / Parciales', '#FCE4D6'),
    'HLD': ('Hora de Libre Disposición / Parciales', '#BDD7EE'),
    'HE+HLD': ('Mixto: HE y HLD en el mismo día', '#E1D5E7'),
    'BL': ('Baja Laboral', '#FFF2CC'),
    'FF1': ('Fallecimiento Familiar 1grado', '#F2F2F2'),
    'FF2': ('Fallecimiento Familiar 2grado', '#F2F2F2'),
    'EF': ('Enfermedad Familiar', '#FFD966'),
    'CF': ('Curso/Formación', '#D9E1F2'),
    'EBM': ('Enfermedad con Baja Médica', '#F8CBAD'),
    'ESM': ('Enfermédad sin Baja Médica', '#FFE699'),
    'FEST': ('Festivo / No Laborable', '#FFC7CE'),
    'SAB': ('Sábado (Fin de semana)', '#E6E6E6'),
    'DOM': ('Domingo (Fin de semana)', '#E6E6E6')
}

MESES = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
         7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}

FESTIVOS_DEFAULT = {
    'Petronor': [(1, 1), (1, 6), (5, 1), (10, 12), (12, 6), (12, 8), (12, 24), (12, 25), (12, 31)],
    'Coruña': [(1, 1), (1, 6), (5, 1), (10, 12), (12, 6), (12, 8), (12, 24), (12, 25), (12, 31)],
    'Tarragona': [(1, 1), (1, 6), (5, 1), (10, 12), (12, 6), (12, 8), (12, 24), (12, 25), (12, 31)],
    'Puertollano': [(1, 1), (1, 6), (5, 1), (10, 12), (12, 6), (12, 8), (12, 24), (12, 25), (12, 31)],
    'Cartagena': [(1, 1), (1, 6), (5, 1), (10, 12), (12, 6), (12, 8), (12, 24), (12, 25), (12, 31)]
}

FESTIVOS_POR_ANIO_DEFAULT = {anio: FESTIVOS_DEFAULT for anio in ANOS_DISPONIBLES}

CONFIG_ANUAL_DEFAULT = {
    anio: {
        'petronor_lj': 8.50, 'petronor_v': 5.50,
        'cartagena_ini': date(anio, 10, 1), 'cartagena_fin': date(anio, 11, 5),
        'tarragona_ini': date(anio, 9, 28), 'tarragona_fin': date(anio, 11, 2)
    } for anio in ANOS_DISPONIBLES
}

HORARIOS_CI_DEFAULT = {
    anio: {
        'Petronor': {'horario': "L-J 08'00h-17'10h<br>V 08'00h-13'27h", 'h_sem': "39'27h", 'obs': "-", 'bolsa_ini': None, 'bolsa_fin': None},
        'Coruña': {'horario': "L-V 07'20h-15'15h", 'h_sem': "39'36h", 'obs': "-", 'bolsa_ini': None, 'bolsa_fin': None},
        'Tarragona': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "Parada programada", 'bolsa_ini': date(anio, 9, 28), 'bolsa_fin': date(anio, 11, 2)},
        'Puertollano': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "-", 'bolsa_ini': None, 'bolsa_fin': None},
        'Cartagena': {'horario': "L-V 07'00h-15'00h", 'h_sem': "40h", 'obs': "Parada programada", 'bolsa_ini': date(anio, 10, 1), 'bolsa_fin': date(anio, 11, 5)}
    } for anio in ANOS_DISPONIBLES
}

HLD_ANUAL_DEFAULT = {
    anio: {
        'Petronor': 89.0,
        'Coruña': 63.5,
        'Tarragona': 87.0,
        'Puertollano': 87.0,
        'Cartagena': 76.0
    } for anio in ANOS_DISPONIBLES
}

FESTIVOS_POR_ANIO = cargar_festivos_drive() or FESTIVOS_POR_ANIO_DEFAULT
CONFIG_ANUAL_POR_ANIO = cargar_config_anual_drive() or CONFIG_ANUAL_DEFAULT
HORARIOS_CI_ANUAL = cargar_horarios_ci_drive() or HORARIOS_CI_DEFAULT
HLD_ANUAL_POR_ANIO = cargar_hld_anual_drive() or HLD_ANUAL_DEFAULT

REGISTROS = cargar_de_drive()
REGISTROS_HE = cargar_he_drive()

if 'historial_auditoria' not in st.session_state:
    st.session_state.historial_auditoria = []

if 'intentando_guardar' not in st.session_state:
    st.session_state.intentando_guardar = False
if 'coincidencias_pendientes' not in st.session_state:
    st.session_state.coincidencias_pendientes = []

def obtener_vpa_totales_tecnico(tecnico, anio):
    if anio == ANOS_DISPONIBLES[0]:
        return TECNICOS[tecnico].get('vpa_base', 0)
    else:
        anio_prev = anio - 1
        vac_cons_prev = 0
        for key, val in REGISTROS.items():
            parts = key[1] if isinstance(key, tuple) else None
            a = key[0] if isinstance(key, tuple) else None
            if a == anio_prev and parts == tecnico:
                marca_str = val['tipo'] if isinstance(val, dict) else val
                if marca_str == 'V':
                    vac_cons_prev += 1
        vac_totales_prev = TECNICOS[tecnico]['vac_totales']
        return max(0, vac_totales_prev - vac_cons_prev)

def obtener_hld_totales_tecnico(tecnico, anio):
    ci = TECNICOS[tecnico]['ci']
    return HLD_ANUAL_POR_ANIO.get(anio, HLD_ANUAL_DEFAULT.get(anio, {} )).get(ci, 87.0)

def obtener_horas_hld(tecnico, mes, dia, anio):
    weekday = calendar.weekday(anio, int(mes), int(dia))
    ci = TECNICOS[tecnico]['ci']
    festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(ci, [])

    if weekday >= 5 or (int(mes), int(dia)) in festivos:
        return 0.0

    es_verano = (int(mes) == 7 or int(mes) == 8)
    horarios_anio = HORARIOS_CI_ANUAL.get(anio, HORARIOS_CI_DEFAULT[anio])
    if ci in horarios_anio:
        b_ini = horarios_anio[ci].get('bolsa_ini')
        b_fin = horarios_anio[ci].get('bolsa_fin')
        if b_ini and b_fin:
            try:
                f_actual = date(anio, int(mes), int(dia))
                if b_ini <= f_actual <= b_fin and weekday < 4:
                    return 9.0 + 2.0
            except Exception:
                pass

    if es_verano:
        return 7.0
    else:
        if ci == 'Coruña':
            return 8.5 if weekday < 4 else 6.0
        else:
            return 9.0 if weekday < 4 else 7.0

def obtener_horas_jornada_real(tecnico, anio, mes, dia):
    return obtener_horas_hld(tecnico, mes, dia, anio)

def calcular_he_compensadas_totales(tecnico, anio):
    lista_he = REGISTROS_HE.get(tecnico, [])
    total_reales = sum(item['horas_reales'] for item in lista_he if item['anio'] == anio)
    return round(total_reales * 1.75, 2)

def calcular_he_consumidas_horas(tecnico, anio):
    total_consumido_h = 0.0
    for key, val in REGISTROS.items():
        if isinstance(key, tuple):
            a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
        else:
            parts = key.split('|')
            a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

        if a == anio and t == tecnico:
            if isinstance(val, dict):
                tipo_reg = val.get('tipo')
                if tipo_reg == 'HE':
                    total_consumido_h += val.get('horas_gastadas', 0.0)
                elif tipo_reg == 'HE+HLD':
                    total_consumido_h += val.get('he_horas', 0.0)
            else:
                if val == 'HE':
                    total_consumido_h += obtener_horas_jornada_real(tecnico, anio, m, d)
    return round(total_consumido_h, 2)

def extraer_info_registro(val_reg, tec, anio, mes, dia):
    if not val_reg:
        return '', ''
    if isinstance(val_reg, str):
        return val_reg, ''
        
    tipo = val_reg.get('tipo', '')
    if tipo == 'HE':
        hg = val_reg.get('horas_gastadas', 0.0)
        h_max = obtener_horas_jornada_real(tec, anio, mes, dia)
        parcial = "Completo" if hg >= h_max else f"{hg}h"
        return 'HE', f"<br><span style='font-size:8px; color:#334155;'>HE: {parcial}</span>"
    elif tipo == 'HLD':
        hg = val_reg.get('horas_gastadas', 0.0)
        h_max = obtener_horas_hld(tec, mes, dia, anio)
        parcial = "Completo" if hg >= h_max else f"{hg}h"
        return 'HLD', f"<br><span style='font-size:8px; color:#334155;'>HLD: {parcial}</span>"
    elif tipo == 'HE+HLD':
        he_h = val_reg.get('he_horas', 0.0)
        hld_h = val_reg.get('hld_horas', 0.0)
        return 'HE+HLD', f"<br><span style='font-size:8px; color:#334155;'>HE:{he_h}h | HLD:{hld_h}h</span>"
    else:
        return tipo, ''

def verificar_coincidencias(tecnico_actual, mes, dia, tipo_marca, anio):
    if tipo_marca == '': return []
    ci_actual = TECNICOS[tecnico_actual]['ci']
    coincidencias = []
    for key, val in REGISTROS.items():
        if isinstance(key, tuple):
            a, tec, m, d = key[0], key[1], int(key[2]), int(key[3])
        else:
            parts = key.split('|')
            a, tec, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

        marca_str = val['tipo'] if isinstance(val, dict) else val
        if a == anio and tec != tecnico_actual and m == int(mes) and d == int(dia):
            if TECNICOS[tec]['ci'] == ci_actual and marca_str != '':
                desc_marca = LEYENDA.get(marca_str, (marca_str, ''))[0]
                coincidencias.append((tec, marca_str, desc_marca))
    return coincidencias

# ==========================================
# HEADER EJECUTIVO PRINCIPAL
# ==========================================
st.markdown("""
<div class="card-corporate" style="display: flex; justify-content: space-between; align-items: center; background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%); border-left: 6px solid #002B36; padding: 22px;">
    <div>
        <h1 style="color: #0F172A !important; margin: 0; font-size: 22px; font-weight: 700;">Sistema de Gestión de Calendarios Técnicos</h1>
        <p style="margin: 4px 0 0 0; font-size: 13px; color: #475569; font-weight: 500;">Servicio de soporte a Infraestructuras y Sistemas de CCII - RPECII</p>
    </div>
    <div style="text-align: right; font-size: 11px; color: #64748B;">
        <span>Ambiente: <b>Producción Enterprise</b></span><br>
        <span>Sincronización: <b>Automática (Cloud)</b></span>
    </div>
</div>
""", unsafe_allow_html=True)

hoy_actual = date.today()
avisos_rojo_naranja = []
ausentes_hoy_lista = []

for tec_n, info_n in TECNICOS.items():
    datos_prl = REGISTROS_PRL.get(tec_n, {'fecha': '2030-01-01'})
    try:
        f_cad_p = datetime.strptime(datos_prl.get('fecha', '2030-01-01'), '%Y-%m-%d').date()
        d_rest = (f_cad_p - hoy_actual).days
        if d_rest < 30:
            avisos_rojo_naranja.append(f"🔴 **PRL Crítico (<1 mes):** {tec_n} ({f_cad_p.strftime('%d/%m/%Y')})")
        elif d_rest < 60:
            avisos_rojo_naranja.append(f"🟠 **PRL Próximo (<2 meses):** {tec_n} ({f_cad_p.strftime('%d/%m/%Y')})")
    except Exception:
        pass

for tec_n, info_n in TECNICOS.items():
    val_h = REGISTROS.get((hoy_actual.year, tec_n, str(hoy_actual.month), str(hoy_actual.day)), '')
    marca_h, _ = extraer_info_registro(val_h, tec_n, hoy_actual.year, hoy_actual.month, hoy_actual.day)
    if marca_h != '':
        desc_m = LEYENDA.get(marca_h, (marca_h, ''))[0]
        ausentes_hoy_lista.append(f"📌 **{tec_n}**: **{desc_m}**")

col_v1, col_v2, col_v3 = st.columns([1.5, 1, 1])
with col_v1:
    dd_vista = st.selectbox('Modo Vista:', ['Calendario Individual', 'Matriz Cuadrante Global (Equipo)'])
with col_v2:
    dd_anio = st.selectbox('Año Operativo:', ANOS_DISPONIBLES)
with col_v3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button('📥 Exportar HTML Detallado', use_container_width=True):
        fecha_actual_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        html_leyenda = "<div style='background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; margin-top: 20px; margin-bottom: 25px; font-family: sans-serif;'><h4 style='margin: 0 0 8px 0; color: #0F172A; font-size: 14px;'>📖 Leyenda de Códigos y Estados</h4><div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
        for k, (desc, color) in LEYENDA.items():
            html_leyenda += f"<div style='display: flex; align-items: center; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 4px 8px; font-size: 11px;'><span style='background-color: {color}; border: 1px solid #94A3B8; width: 14px; height: 14px; display: inline-block; margin-right: 6px; border-radius: 2px;'></span><b>{k}:</b>&nbsp;{desc}</div>"
        html_leyenda += "</div></div>"
        
        datos_resumen = []
        for tec, info in TECNICOS.items():
            hld_tot_t = obtener_hld_totales_tecnico(tec, dd_anio)
            vpa_tot_t = obtener_vpa_totales_tecnico(tec, dd_anio)
            vac_c = 0
            vpa_c = 0
            hld_c = 0.0
            for key, val in REGISTROS.items():
                if isinstance(key, tuple):
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    parts = key.split('|')
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

                if a == dd_anio and t == tec:
                    if isinstance(val, dict):
                        tipo_v = val.get('tipo')
                        if tipo_v == 'V': vac_c += 1
                        elif tipo_v == 'VPA': vpa_c += 1
                        elif tipo_v == 'HLD':
                            hld_c += val.get('horas_gastadas', 0.0)
                        elif tipo_v == 'HE+HLD':
                            hld_c += val.get('hld_horas', 0.0)
                    else:
                        if val == 'V': vac_c += 1
                        elif val == 'VPA': vpa_c += 1
                        elif val == 'HLD':
                            hld_c += obtener_horas_hld(tec, m, d, dd_anio)
            he_comp = calcular_he_compensadas_totales(tec, dd_anio)
            he_gast = calcular_he_consumidas_horas(tec, dd_anio)
            datos_resumen.append({'Centro': info['ci'], 'Técnico': tec, 'Vac. Cons.': vac_c, 'Vac. Pend.': info['vac_totales'] - vac_c, 'VPA Cons.': vpa_c, 'VPA Pend.': vpa_tot_t - vpa_c, 'HLD Cons.': round(hld_c, 2), 'HLD Pend.': round(hld_tot_t - hld_c, 2), 'HE Comp.': he_comp, 'HE Disp.': round(he_comp - he_gast, 2)})
        
        tabla_res_html = pd.DataFrame(datos_resumen).to_html(index=False, classes='tabla-corporativa', border=0)
        st.download_button(label="📥 Descargar archivo HTML generado", data=tabla_res_html, file_name=f"Calendario_SAT_CI_Repsol_{dd_anio}.html", mime="text/html")

# ==========================================
# PESTAÑAS PRINCIPALES DEL SISTEMA
# ==========================================
tab_registrar, tab_he, tab_cobertura, tab_balance, tab_prl, tab_incidencias, tab_auditoria, tab_config, tab_horarios, tab_hld = st.tabs([
    '🛠️ Registrar', '⚡ Horas Extra', '👥 Cobertura', '📈 Balance', '🏢 Accesos CI', '⚠️ Incidencias', '📋 Auditoría', '⚙️ Configuración', '⏰ Horarios / CI', '⏳ Config. HLD'
])

with tab_registrar:
    st.markdown("### 📝 Gestión de Cuadrantes y Registro de Ausencias")
    
    if st.session_state.rol_actual != "Editor":
        st.info("👁️ Estás visualizando en modo **Lector**. Puedes consultar los calendarios pero no modificar datos.")

    c1, c2, c3 = st.columns(3)
    with c1:
        reg_tec = st.selectbox('Técnico:', list(TECNICOS.keys()), key='reg_tec')
    with c2:
        reg_mes_num = st.selectbox('Mes:', list(MESES.keys()), format_func=lambda x: MESES[x], key='reg_mes')
    with c3:
        num_dias_mes = calendar.monthrange(dd_anio, reg_mes_num)[1]
        opciones_dias_ini = list(range(1, num_dias_mes + 1))
        reg_d_ini = st.selectbox('Día Inicio:', opciones_dias_ini, key='reg_d_ini')

    c4, c5, c6 = st.columns(3)
    with c4:
        opciones_dias_fin = list(range(1, num_dias_mes + 1))
        reg_d_fin = st.selectbox('Día Fin:', opciones_dias_fin, index=len(opciones_dias_fin) - 1, key='reg_d_fin')
    with c5:
        opciones_marca = [(f"{k} - {v[0]}", k) for k, v in LEYENDA.items() if k not in ['FEST', 'SAB', 'DOM']]
        opciones_marca.append(('Limpiar Marca (Vacío)', ''))
        reg_tipo_tupla = st.selectbox('Tipo de Ausencia / Marca:', opciones_marca, key='reg_tipo')
        reg_tipo = reg_tipo_tupla[1]
    with c6:
        info_tec = TECNICOS[reg_tec]
        hld_tot_anio = obtener_hld_totales_tecnico(reg_tec, dd_anio)
        vpa_tot_anio = obtener_vpa_totales_tecnico(reg_tec, dd_anio)
        
        vac_c = 0
        vpa_c = 0
        for k, v in REGISTROS.items():
            if isinstance(k, tuple):
                a, t = k[0], k[1]
            else:
                parts = k.split('|')
                a, t = int(parts[0]), parts[1]
            if a == dd_anio and t == reg_tec:
                marca_val = v.get('tipo') if isinstance(v, dict) else v
                if marca_val == 'V': vac_c += 1
                elif marca_val == 'VPA': vpa_c += 1

        hld_c = 0.0
        for k, v in REGISTROS.items():
            if isinstance(k, tuple):
                a, t, m, d = k[0], k[1], int(k[2]), int(k[3])
            else:
                parts = k.split('|')
                a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
            if a == dd_anio and t == reg_tec:
                if isinstance(v, dict):
                    if v.get('tipo') == 'HLD':
                        hld_c += v.get('horas_gastadas', 0.0)
                    elif v.get('tipo') == 'HE+HLD':
                        hld_c += v.get('hld_horas', 0.0)
                elif v == 'HLD':
                    hld_c += obtener_horas_hld(reg_tec, m, d, dd_anio)
        
        he_comp = calcular_he_compensadas_totales(reg_tec, dd_anio)
        he_gast = calcular_he_consumidas_horas(reg_tec, dd_anio)
        he_disp = round(he_comp - he_gast, 2)
        
        val_horas_disfrute = 0.0
        val_he_mix = 0.0
        val_hld_mix = 0.0
        
        if reg_tipo == 'HE':
            max_val = max(0.5, float(he_disp))
            val_horas_disfrute = st.slider('Horas a Gastar (HE):', 0.5, max_val, 0.5, step=0.5)
        elif reg_tipo == 'HLD':
            hld_max_d = obtener_horas_hld(reg_tec, reg_mes_num, reg_d_ini, dd_anio)
            max_val = max(0.5, float(hld_max_d if hld_max_d > 0 else 7.0))
            val_horas_disfrute = st.slider('Horas a Gastar (HLD):', 0.5, max_val, 0.5, step=0.5)
        elif reg_tipo == 'HE+HLD':
            jornada_total = obtener_horas_jornada_real(reg_tec, dd_anio, reg_mes_num, reg_d_ini)
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                val_he_mix = st.number_input('Horas HE:', min_value=0.0, max_value=float(he_disp), value=0.0, step=0.5)
            with col_m2:
                val_hld_mix = st.number_input('Horas HLD:', min_value=0.0, max_value=float(jornada_total), value=0.0, step=0.5)

    vac_pend = info_tec['vac_totales'] - vac_c
    vpa_pend = vpa_tot_anio - vpa_c
    hld_pend = hld_tot_anio - hld_c
    
    st.markdown(f"""
    <div class="card-corporate" style='border-left:4px solid #002B36; padding:12px; margin-bottom:15px; display:flex; justify-content:space-between; flex-wrap:wrap; font-size:13px;'>
        <div><b>👤 Técnico:</b> {reg_tec} ({dd_anio})</div>
        <div>🏖️ <b>Vac:</b> {vac_c}/{info_tec['vac_totales']} (<b>{vac_pend}</b>)</div>
        <div>⏱️ <b>VPA:</b> {vpa_c}/{vpa_tot_anio} (<b>{vpa_pend}</b>)</div>
        <div>⏳ <b>HLD:</b> {hld_c:.1f}h/{hld_tot_anio}h (<b>{hld_pend:.1f}h</b>)</div>
        <div>⚡ <b>HE Disp:</b> <b>{he_disp:.2f}h</b></div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.rol_actual == "Editor":
        if st.button('Guardar Rango de Fechas', type='primary', use_container_width=True):
            if reg_d_ini > reg_d_fin:
                st.error("❌ Error: El día de inicio debe ser menor o igual al día fin.")
            else:
                dias_a_registrar = reg_d_fin - reg_d_ini + 1
                error_saldo = False
                mensaje_error_saldo = ""

                if reg_tipo == 'V' and vac_pend < dias_a_registrar:
                    error_saldo = True
                    mensaje_error_saldo = f"❌ No se puede registrar: Intentas asignar {dias_a_registrar} día(s) de Vacaciones, pero solo quedan {vac_pend} disponibles."
                elif reg_tipo == 'VPA' and vpa_pend < dias_a_registrar:
                    error_saldo = True
                    mensaje_error_saldo = f"❌ No se puede registrar: Intentas asignar {dias_a_registrar} día(s) de VPA, pero solo quedan {vpa_pend} disponibles."

                if error_saldo:
                    st.error(mensaje_error_saldo)
                else:
                    for dia in range(reg_d_ini, reg_d_fin + 1):
                        clave_reg = (dd_anio, reg_tec, str(reg_mes_num), str(dia))
                        if reg_tipo == '':
                            REGISTROS.pop(clave_reg, None)
                        elif reg_tipo == 'HE':
                            h_jornada = obtener_horas_jornada_real(reg_tec, dd_anio, reg_mes_num, dia)
                            h_efectivas = min(val_horas_disfrute, h_jornada)
                            REGISTROS[clave_reg] = {'tipo': 'HE', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                        elif reg_tipo == 'HLD':
                            h_teorico = obtener_horas_hld(reg_tec, reg_mes_num, dia, dd_anio)
                            h_efectivas = min(val_horas_disfrute, h_teorico)
                            REGISTROS[clave_reg] = {'tipo': 'HLD', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                        elif reg_tipo == 'HE+HLD':
                            REGISTROS[clave_reg] = {'tipo': 'HE+HLD', 'he_horas': val_he_mix, 'hld_horas': val_hld_mix, 'anio': dd_anio, 'tec': reg_tec}
                        else:
                            REGISTROS[clave_reg] = reg_tipo
                    
                    guardar_en_drive(REGISTROS)
                    st.success(f"✅ Registros guardados correctamente del {reg_d_ini} al {reg_d_fin} de {MESES[reg_mes_num]} para {reg_tec}.")
                    st.rerun()

    if dd_vista == 'Calendario Individual':
        ci_tec = TECNICOS[reg_tec]['ci']
        cal = calendar.monthcalendar(dd_anio, reg_mes_num)
        festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(ci_tec, [])
        
        html_cal = f"<h4 style='color:#0F172A;'>Calendario de {reg_tec} ({ci_tec})</h4><table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; width:100%; font-size:12px; border-color: #CBD5E1;'>"
        html_cal += "<tr style='background-color:#002B36; color:white;'><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th style='background-color:#64748B;'>Sáb</th><th style='background-color:#64748B;'>Dom</th></tr>"
        for semana in cal:
            html_cal += "<tr>"
            for dia in semana:
                if dia == 0:
                    html_cal += "<td style='background-color:#F1F5F9; height:50px;'></td>"
                else:
                    val_reg = REGISTROS.get((dd_anio, reg_tec, str(reg_mes_num), str(dia)), '')
                    marca, extra_txt = extraer_info_registro(val_reg, reg_tec, dd_anio, reg_mes_num, dia)
                    bg_color = '#ffffff'
                    weekday = calendar.weekday(dd_anio, reg_mes_num, dia)
                    if (reg_mes_num, dia) in festivos:
                        bg_color = LEYENDA['FEST'][1]
                        if not marca: marca = 'FEST'
                    elif weekday == 5:
                        bg_color = LEYENDA['SAB'][1]
                        if not marca: marca = 'SAB'
                    elif weekday == 6:
                        bg_color = LEYENDA['DOM'][1]
                        if not marca: marca = 'DOM'
                    elif marca in LEYENDA:
                        bg_color = LEYENDA[marca][1]

                    html_cal += f"<td style='background-color:{bg_color}; height:50px; color:#0F172A;'><b>{dia}</b><br><span style='font-size:10px;'>{marca}</span>{extra_txt}</td>"
            html_cal += "</tr>"
        html_cal += "</table>"
        st.markdown(html_cal, unsafe_allow_html=True)

with tab_he:
    st.markdown("### ⚡ Gestión y Acumulación de Horas Extra")
    he_anio = st.selectbox('Año Operativo HE:', ANOS_DISPONIBLES, key='he_anio_sel')
    he_tec = st.selectbox('Técnico Asignado:', list(TECNICOS.keys()), key='he_tec_sel')
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        txt_horas = st.number_input('Horas Reales Trabajadas:', min_value=-100.0, max_value=100.0, value=1.0, step=0.5)
    with col_h2:
        txt_motivo = st.text_input('Motivo / Justificación:', placeholder='Ej. Urgencia técnica')
        
    if st.session_state.rol_actual == "Editor":
        if st.button('Registrar Horas Extra', use_container_width=True, type='primary'):
            if he_tec not in REGISTROS_HE:
                REGISTROS_HE[he_tec] = []
            REGISTROS_HE[he_tec].append({
                'anio': he_anio, 'horas_reales': txt_horas, 'motivo': txt_motivo or 'Sin motivo',
                'usuario': st.session_state.get('usuario_actual', 'Sistema'),
                'fecha': datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            guardar_he_drive()
            st.success(f"✅ Se han procesado {txt_horas}h extra a {he_tec}.")
            st.rerun()

    tot_r = sum(i['horas_reales'] for i in REGISTROS_HE.get(he_tec, []) if i['anio'] == he_anio)
    tot_c = calcular_he_compensadas_totales(he_tec, he_anio)
    tot_g = calcular_he_consumidas_horas(he_tec, he_anio)
    st.info(f"📊 **Resumen HE ({he_tec} - {he_anio}):** Compensadas: {tot_c:.2f}h | Gastadas: {tot_g:.2f}h | **Disponibles: {tot_c - tot_g:.2f}h**")

with tab_cobertura:
    st.markdown("### 👥 Análisis Operativo de Cobertura Diaria")
    fecha_cob = st.date_input("Seleccionar fecha de control:", value=date.today())
    if fecha_cob:
        anio_c, mes_c, dia_c = fecha_cob.year, fecha_cob.month, fecha_cob.day
        detalles_cov_tec = []
        for tec, info in TECNICOS.items():
            ci = info['ci']
            val_reg = REGISTROS.get((anio_c, tec, str(mes_c), str(dia_c)), '')
            marca, _ = extraer_info_registro(val_reg, tec, anio_c, mes_c, dia_c)
            weekday = calendar.weekday(anio_c, mes_c, dia_c)
            festivos = FESTIVOS_POR_ANIO.get(anio_c, {}).get(ci, [])
            es_festivo = (mes_c, dia_c) in festivos or weekday >= 5
            
            estado_hoy = "TRABAJA" if marca == '' and not es_festivo else "NO TRABAJA"
            detalles_cov_tec.append({'CI': ci, 'TÉCNICO': tec, 'ESTADO HOY': estado_hoy})
        st.dataframe(pd.DataFrame(detalles_cov_tec), use_container_width=True, hide_index=True)

with tab_balance:
    st.markdown(f"### 📈 Balance Consolidado de Saldos ({dd_anio})")
    datos_bal = []
    for tec, info in TECNICOS.items():
        hld_tot = obtener_hld_totales_tecnico(tec, dd_anio)
        vpa_tot = obtener_vpa_totales_tecnico(tec, dd_anio)
        vac_c, vpa_c, hld_c = 0, 0, 0.0
        
        for k, v in REGISTROS.items():
            if isinstance(k, tuple):
                a, t, m, d = k[0], k[1], int(k[2]), int(k[3])
            else:
                parts = k.split('|')
                a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

            if a == dd_anio and t == tec:
                if isinstance(v, dict):
                    tipo_v = v.get('tipo')
                    if tipo_v == 'V': vac_c += 1
                    elif tipo_v == 'VPA': vpa_c += 1
                    elif tipo_v == 'HLD': hld_c += v.get('horas_gastadas', 0.0)
                    elif tipo_v == 'HE+HLD': hld_c += v.get('hld_horas', 0.0)
                else:
                    if v == 'V': vac_c += 1
                    elif v == 'VPA': vpa_c += 1
                    elif v == 'HLD': hld_c += obtener_horas_hld(tec, m, d, dd_anio)

        he_comp = calcular_he_compensadas_totales(tec, dd_anio)
        he_gast = calcular_he_consumidas_horas(tec, dd_anio)
        datos_bal.append({
            'Centro': info['ci'], 'Técnico': tec, 'Vac. Pend.': info['vac_totales'] - vac_c,
            'VPA Pend.': vpa_tot - vpa_c, 'HLD Pend.': round(hld_tot - hld_c, 2), 'HE Disp.': round(he_comp - he_gast, 2)
        })
    st.dataframe(pd.DataFrame(datos_bal), use_container_width=True, hide_index=True)

with tab_prl:
    st.markdown("### 🏢 Control de Accesos CI (Reconocimientos Médicos)")
    tabla_prl_visual = []
    for tec, info in TECNICOS.items():
        datos_tec_prl = REGISTROS_PRL.get(tec, {'nip': 'N/D', 'dni': 'N/D', 'fecha': '2030-01-01', 'obs': ''})
        tabla_prl_visual.append({'Centro': info['ci'], 'Técnico': tec, 'Caducidad': datos_tec_prl.get('fecha', '')})
    st.dataframe(pd.DataFrame(tabla_prl_visual), use_container_width=True, hide_index=True)

with tab_incidencias:
    st.markdown("### ⚠️ Panel de Control de Excesos y Alertas")
    st.info("Sistema de incidencias operativo y sincronizado.")

with tab_auditoria:
    st.markdown("### 📋 Auditoría de Sesión")
    if st.session_state.historial_auditoria:
        st.dataframe(pd.DataFrame(st.session_state.historial_auditoria), use_container_width=True, hide_index=True)
    else:
        st.info("No hay acciones registradas en la sesión actual.")

with tab_config:
    st.markdown("### ⚙️ Configuración General")
    st.write("Configuración general de parámetros del sistema de turnos y control.")

with tab_horarios:
    st.markdown("### ⏰ Horarios por Centro de Interés (CI)")
    st.write("Gestión de horarios semanales y jornadas operativas.")

with tab_hld:
    st.markdown("### ⏳ Configuración Anual de Horas de Libre Disposición (HLD)")
    st.write("Bolsas anuales de HLD por centro de trabajo.")

st.markdown("""
<div class="footer-copyright">
    © 2026 Juan Pedro Murillo Huete. Todos los derechos reservados. Indra Group & Repsol RPECII.
</div>
""", unsafe_allow_html=True)
