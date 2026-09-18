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
    [data-testid="stSidebar"] .stMarkdown h1, 
    [data-testid="stSidebar"] .stMarkdown h2, 
    [data-testid="stSidebar"] .stMarkdown h3, 
    [data-testid="stSidebar"] .stMarkdown label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] p {
        color: #1E293B !important;
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
    .stButton>button:hover {
        background-color: #F1F5F9;
        border-color: #94A3B8;
    }
    button[kind="primary"] {
        background-color: #002B36 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #001F26 !important;
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
        font-family: 'Segoe UI', system-ui, sans-serif;
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
# FUNCIONES DE PERSISTENCIA Y GIST (CORREGIDAS)
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
    # Convertir claves de tuplas a strings serializables tipo "anio|tec|mes|dia"
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
    datos_json = {}
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    cargado_remoto = False
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "datos_tecnicos_repsol.json" in files:
                    contenido = files["datos_tecnicos_repsol.json"]["content"]
                    datos_json = json.loads(contenido)
                    cargado_remoto = True
        except Exception:
            pass
            
    if not cargado_remoto:
        try:
            with open(RUTA_BDD, 'r', encoding='utf-8') as f:
                datos_json = json.load(f)
        except FileNotFoundError:
            datos_json = {}

    resultado = {}
    for k, v in datos_json.items():
        if '|' in k:
            parts = k.split('|')
            if len(parts) == 4:
                try:
                    resultado[(int(parts[0]), parts[1], str(parts[2]), str(parts[3]))] = v
                except ValueError:
                    resultado[k] = v
            elif len(parts) == 3:
                try:
                    resultado[(2026, parts[0], str(parts[1]), str(parts[2]))] = v
                except ValueError:
                    resultado[k] = v
            else:
                resultado[k] = v
        else:
            resultado[k] = v
    return resultado

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
        'Tarragona': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "Parada programada / Excepción anual", 'bolsa_ini': date(anio, 9, 28), 'bolsa_fin': date(anio, 11, 2)},
        'Puertollano': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "-", 'bolsa_ini': None, 'bolsa_fin': None},
        'Cartagena': {'horario': "L-V 07'00h-15'00h", 'h_sem': "40h", 'obs': "Parada programada / Excepción anual", 'bolsa_ini': date(anio, 10, 1), 'bolsa_fin': date(anio, 11, 5)}
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
            if isinstance(key, tuple) and len(key) == 4:
                a, t = key[0], key[1]
            elif isinstance(key, str) and '|' in key:
                parts = key.split('|')
                if len(parts) == 4:
                    a, t = int(parts[0]), parts[1]
                else:
                    continue
            else:
                continue

            if a == anio_prev and t == tecnico:
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
            if weekday < 4:
                return 8.5
            else:
                return 6.0
        else:
            if weekday < 4:
                return 9.0
            else:
                return 7.0

def obtener_horas_jornada_real(tecnico, anio, mes, dia):
    return obtener_horas_hld(tecnico, mes, dia, anio)

def calcular_he_compensadas_totales(tecnico, anio):
    lista_he = REGISTROS_HE.get(tecnico, [])
    total_reales = sum(item['horas_reales'] for item in lista_he if item['anio'] == anio)
    return round(total_reales * 1.75, 2)

def calcular_he_consumidas_horas(tecnico, anio):
    total_consumido_h = 0.0
    for key, val in REGISTROS.items():
        a, t, m, d = None, None, None, None
        if isinstance(key, tuple) and len(key) == 4:
            a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
        elif isinstance(key, str) and '|' in key:
            parts = key.split('|')
            if len(parts) == 4:
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
        a, tec, m, d = None, None, None, None
        if isinstance(key, tuple) and len(key) == 4:
            a, tec, m, d = key[0], key[1], int(key[2]), int(key[3])
        elif isinstance(key, str) and '|' in key:
            parts = key.split('|')
            if len(parts) == 4:
                a, tec, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

        marca_str = val['tipo'] if isinstance(val, dict) else val
        if a == anio and tec != tecnico_actual and m == int(mes) and d == int(dia):
            if TECNICOS[tec]['ci'] == ci_actual and marca_str != '':
                desc_marca = LEYENDA.get(marca_str, (marca_str, ''))[0]
                coincidencias.append((tec, marca_str, desc_marca))
    return coincidencias

# ==========================================
# HEADER EJECUTIVO PRINCIPAL Y AVISOS SUPERIORES
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
    val_h = REGISTROS.get((hoy_actual.year, tec_n, str(hoy_actual.month), str(hoy_actual.day)), REGISTROS.get(f"{hoy_actual.year}|{tec_n}|{hoy_actual.month}|{hoy_actual.day}", ''))
    marca_h, _ = extraer_info_registro(val_h, tec_n, hoy_actual.year, hoy_actual.month, hoy_actual.day)
    if marca_h != '':
        desc_m = LEYENDA.get(marca_h, (marca_h, ''))[0]
        ausentes_hoy_lista.append(f"📌 **{tec_n}**: **{desc_m}**")

st.markdown("""
<div style="background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%); padding: 16px 20px; border-radius: 8px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 8px; margin-bottom: 12px;">
        <span style="font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            🔔 Panel de Alertas y Estado Global del Día
        </span>
        <span style="font-size: 12px; background: rgba(255,255,255,0.2); padding: 3px 10px; border-radius: 12px; font-weight: 600;">
            📅 Hoy: {}
        </span>
    </div>
</div>
""".format(hoy_actual.strftime('%d/%m/%Y')), unsafe_allow_html=True)

col_av1, col_av2 = st.columns(2)

with col_av1:
    bg_card_prl = "#FEF2F2" if avisos_rojo_naranja else "#F0FDF4"
    border_color_prl = "#EF4444" if avisos_rojo_naranja else "#22C55E"
    text_color_prl = "#991B1B" if avisos_rojo_naranja else "#166534"
    
    html_prl_card = f"""
    <div style="background-color: {bg_card_prl}; border: 1px solid {border_color_prl}; border-left: 5px solid {border_color_prl}; border-radius: 8px; padding: 16px; height: 100%;">
        <h4 style="margin: 0 0 10px 0; font-size: 14px; color: {text_color_prl}; display: flex; align-items: center; gap: 6px;">
            ⚠️ Alertas Técnicas y Reconocimientos (PRL)
        </h4>
    """
    if avisos_rojo_naranja:
        for av in avisos_rojo_naranja:
            html_prl_card += f"<div style='font-size: 12px; color: #1E293B; margin-bottom: 6px; background: white; padding: 6px 10px; border-radius: 4px; border: 1px solid #E2E8F0;'>- {av}</div>"
    else:
        html_prl_card += "<div style='font-size: 12px; color: #166534; background: white; padding: 8px 10px; border-radius: 4px; border: 1px solid #DCFCE7;'>✅ Sin alertas críticas de Reconocimiento Médico en vigor.</div>"
    html_prl_card += "</div>"
    st.markdown(html_prl_card, unsafe_allow_html=True)

with col_av2:
    bg_card_aus = "#FFFBEB" if ausentes_hoy_lista else "#F0FDF4"
    border_color_aus = "#F59E0B" if ausentes_hoy_lista else "#22C55E"
    text_color_aus = "#92400E" if ausentes_hoy_lista else "#166534"
    
    html_aus_card = f"""
    <div style="background-color: {bg_card_aus}; border: 1px solid {border_color_aus}; border-left: 5px solid {border_color_aus}; border-radius: 8px; padding: 16px; height: 100%;">
        <h4 style="margin: 0 0 10px 0; font-size: 14px; color: {text_color_aus}; display: flex; align-items: center; gap: 6px;">
            🏖️ Ausencias / Permisos de HOY
        </h4>
    """
    if ausentes_hoy_lista:
        for aus in ausentes_hoy_lista:
            html_aus_card += f"<div style='font-size: 12px; color: #1E293B; margin-bottom: 6px; background: white; padding: 6px 10px; border-radius: 4px; border: 1px solid #E2E8F0;'>- {aus}</div>"
    else:
        html_aus_card += "<div style='font-size: 12px; color: #166534; background: white; padding: 8px 10px; border-radius: 4px; border: 1px solid #DCFCE7;'>🟢 Plantilla 100% operativa y disponible hoy.</div>"
    html_aus_card += "</div>"
    st.markdown(html_aus_card, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

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
                a, t, m, d = None, None, None, None
                if isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                elif isinstance(key, str) and '|' in key:
                    parts = key.split('|')
                    if len(parts) == 4:
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
        
        secciones_meses_html = ""
        dias_semana_abrev = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
        for mes_num, mes_nom in MESES.items():
            num_dias = calendar.monthrange(dd_anio, mes_num)[1]
            t_html = "<table class='tabla-corporativa tabla-detalle'><thead><tr><th>Técnico</th><th>Centro</th>"
            for d in range(1, num_dias + 1):
                weekday = calendar.weekday(dd_anio, mes_num, d)
                t_html += f"<th>{d}<br><span style='font-size:9px; color:#64748B;'>{dias_semana_abrev[weekday]}</span></th>"
            t_html += "</tr></thead><tbody>"
            for tec, info in TECNICOS.items():
                t_html += f"<tr><td><b>{tec}</b></td><td>{info['ci']}</td>"
                festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(info['ci'], [])
                for d in range(1, num_dias + 1):
                    val_reg = REGISTROS.get((dd_anio, tec, str(mes_num), str(d)), REGISTROS.get(f"{dd_anio}|{tec}|{mes_num}|{d}", ''))
                    marca, extra_txt = extraer_info_registro(val_reg, tec, dd_anio, mes_num, d)
                    bg_color = '#ffffff'
                    weekday = calendar.weekday(dd_anio, mes_num, d)
                    if (mes_num, d) in festivos:
                        bg_color = LEYENDA['FEST'][1]
                        if not marca: marca = 'FEST'
                    elif weekday >= 5:
                        bg_color = LEYENDA['SAB'][1] if weekday == 5 else LEYENDA['DOM'][1]
                        if not marca: marca = 'SAB' if weekday == 5 else 'DOM'
                    elif marca in LEYENDA:
                        bg_color = LEYENDA[marca][1]

                    t_html += f"<td style='background-color: {bg_color}; text-align: center; color: #0F172A;'><b>{marca}</b>{extra_txt}</td>"
                t_html += "</tr>"
            t_html += "</tbody></table>"
            secciones_meses_html += f"<div class='mes-container'><h3>📅 Mes: {mes_nom} {dd_anio}</h3><div class='table-responsive'>{t_html}</div></div>"
        
        html_template = f"<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><title>Calendario SAT CI Repsol - {dd_anio}</title><style>body{{font-family:'Segoe UI',sans-serif;background-color:#F8FAFC;color:#0F172A;margin:0;padding:20px;}}.container{{max-width:1400px;margin:auto;background:white;padding:30px;border-radius:8px;}}h1{{color:#0F172A;border-bottom:3px solid #002B36;padding-bottom:10px;font-size:22px;}}table.tabla-corporativa{{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px;text-align:left;white-space:nowrap;}}table.tabla-corporativa th{{background-color:#002B36;color:white;padding:8px;text-align:center;}}table.tabla-corporativa td{{padding:6px;border:1px solid #E2E8F0;}}</style></head><body><div class='container'><h1>Calendario SAT CI Repsol - {dd_anio}</h1><div class='fecha-generacion'>Fecha de generación: <b>{fecha_actual_str}</b></div>{html_leyenda}<h2>📈 Balance Consolidado de Saldos</h2>{tabla_res_html}<h2>🗓️ Detalle de Cuadrantes por Meses</h2>{secciones_meses_html}<div class='footer-copyright'>© {dd_anio} Juan Pedro Murillo Huete. Todos los derechos reservados. Indra Group & Repsol RPECII.</div></div></body></html>"
        st.download_button(label="📥 Descargar archivo HTML generado", data=html_template, file_name=f"Calendario_SAT_CI_Repsol_{dd_anio}.html", mime="text/html")

# ==========================================
# PESTAÑAS PRINCIPALES DEL SISTEMA (ACCESOS CI)
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
            a, t, _, _ = None, None, None, None
            if isinstance(k, tuple) and len(k) == 4:
                a, t = k[0], k[1]
            elif isinstance(k, str) and '|' in k:
                parts = k.split('|')
                if len(parts) == 4:
                    a, t = int(parts[0]), parts[1]
            if a == dd_anio and t == reg_tec:
                tipo_val = v.get('tipo') if isinstance(v, dict) else v
                if tipo_val == 'V': vac_c += 1
                elif tipo_val == 'VPA': vpa_c += 1
        
        hld_c = 0.0
        for k, v in REGISTROS.items():
            a, t, m, d = None, None, None, None
            if isinstance(k, tuple) and len(k) == 4:
                a, t, m, d = k[0], k[1], int(k[2]), int(k[3])
            elif isinstance(k, str) and '|' in k:
                parts = k.split('|')
                if len(parts) == 4:
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
            min_val = 0.5
            if max_val <= min_val: max_val = min_val + 0.5
            val_horas_disfrute = st.slider('Horas a Gastar (HE):', min_val, max_val, min_val, step=0.5)
        elif reg_tipo == 'HLD':
            hld_max_d = obtener_horas_hld(reg_tec, reg_mes_num, reg_d_ini, dd_anio)
            max_val = max(0.5, float(hld_max_d if hld_max_d > 0 else 7.0))
            min_val = 0.5
            if max_val <= min_val: max_val = min_val + 0.5
            val_horas_disfrute = st.slider('Horas a Gastar (HLD):', min_val, max_val, min_val, step=0.5)
        elif reg_tipo == 'HE+HLD':
            jornada_total = obtener_horas_jornada_real(reg_tec, dd_anio, reg_mes_num, reg_d_ini)
            st.markdown(f"<small>Jornada estimada: <b>{jornada_total}h</b>. Configura las horas de cada bolsa para completar el día:</small>", unsafe_allow_html=True)
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                val_he_mix = st.number_input('Horas HE:', min_value=0.0, max_value=float(he_disp), value=min(4.0, max(0.0, float(he_disp))), step=0.5)
            with col_m2:
                val_hld_mix = st.number_input('Horas HLD:', min_value=0.0, max_value=float(jornada_total), value=min(4.0, float(jornada_total)), step=0.5)

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
        boton_guardar = st.button('Guardar Rango de Fechas', type='primary', use_container_width=True)
        
        if boton_guardar:
            if reg_d_ini > reg_d_fin:
                st.error("❌ Error: El día de inicio debe ser menor o igual al día fin.")
            else:
                dias_a_registrar = reg_d_fin - reg_d_ini + 1
                error_saldo = False
                mensaje_error_saldo = ""

                if reg_tipo == 'V':
                    if vac_pend < dias_a_registrar:
                        error_saldo = True
                        mensaje_error_saldo = f"❌ No se puede registrar: Intentas asignar {dias_a_registrar} día(s) de Vacaciones, pero a {reg_tec} solo le quedan {vac_pend} disponibles."
                elif reg_tipo == 'VPA':
                    if vpa_pend < dias_a_registrar:
                        error_saldo = True
                        mensaje_error_saldo = f"❌ No se puede registrar: Intentas asignar {dias_a_registrar} día(s) de VPA, pero a {reg_tec} solo le quedan {vpa_pend} disponibles."
                elif reg_tipo == 'HLD':
                    total_hld_requeridas = sum(obtener_horas_hld(reg_tec, reg_mes_num, d, dd_anio) for d in range(reg_d_ini, reg_d_fin + 1))
                    if hld_pend < total_hld_requeridas:
                        error_saldo = True
                        mensaje_error_saldo = f"❌ No se puede registrar: Las horas HLD requeridas ({total_hld_requeridas}h) superan el saldo pendiente disponible ({hld_pend}h)."
                elif reg_tipo == 'HE':
                    total_he_requeridas = val_horas_disfrute * dias_a_registrar
                    if he_disp < total_he_requeridas:
                        error_saldo = True
                        mensaje_error_saldo = f"❌ No se puede registrar: Las horas HE requeridas ({total_he_requeridas}h) superan las disponibles ({he_disp}h)."

                if error_saldo:
                    st.error(mensaje_error_saldo)
                else:
                    coincidencias_totales = []
                    if reg_tipo != '':
                        for dia in range(reg_d_ini, reg_d_fin + 1):
                            c = verificar_coincidencias(reg_tec, reg_mes_num, str(dia), reg_tipo, dd_anio)
                            if c:
                                coincidencias_totales.append((dia, c))
                    
                    if coincidencias_totales:
                        st.session_state.intentando_guardar = True
                        st.session_state.coincidencias_pendientes = coincidencias_totales
                    else:
                        st.session_state.intentando_guardar = False
                        st.session_state.coincidencias_pendientes = []
                        
                        for dia in range(reg_d_ini, reg_d_fin + 1):
                            clave_reg = (dd_anio, reg_tec, str(reg_mes_num), str(dia))
                            if reg_tipo == '':
                                # Eliminar de todas las formas posibles de clave
                                REGISTROS.pop(clave_reg, None)
                                REGISTROS.pop(f"{dd_anio}|{reg_tec}|{reg_mes_num}|{dia}", None)
                            elif reg_tipo == 'HE':
                                h_jornada = obtener_horas_jornada_real(reg_tec, dd_anio, reg_mes_num, dia)
                                h_efectivas = min(val_horas_disfrute, h_jornada)
                                REGISTROS[clave_reg] = {'tipo': 'HE', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                            elif reg_tipo == 'HLD':
                                h_teorico = obtener_horas_hld(reg_tec, reg_mes_num, dia, dd_anio)
                                h_efectivas = min(val_horas_disfrute, h_teorico)
                                REGISTROS[clave_reg] = {'tipo': 'HLD', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                            elif reg_tipo == 'HE+HLD':
                                REGISTROS[clave_reg] = {
                                    'tipo': 'HE+HLD', 
                                    'he_horas': val_he_mix, 
                                    'hld_horas': val_hld_mix, 
                                    'anio': dd_anio, 
                                    'tec': reg_tec
                                }
                            else:
                                REGISTROS[clave_reg] = reg_tipo
                        
                        guardar_en_drive(REGISTROS)
                        st.session_state.historial_auditoria.append({
                            'hora': datetime.now().strftime("%H:%M:%S"),
                            'tec': reg_tec,
                            'rango': f"Del {reg_d_ini} al {reg_d_fin} de {MESES[reg_mes_num]} {dd_anio}",
                            'tipo': reg_tipo if reg_tipo else 'Limpieza (Vacío)'
                        })
                        st.success(f"✅ Registros guardados correctamente del {reg_d_ini} al {reg_d_fin} de {MESES[reg_mes_num]} para {reg_tec}.")
                        st.rerun()

        if st.session_state.intentando_guardar and st.session_state.coincidencias_pendientes:
            mensaje_alerta = "⚠️ **¡Atención! Solapamiento detectado en el mismo centro:**\n\n"
            for dia, lista_c in st.session_state.coincidencias_pendientes:
                for tec_col, marca_col, desc_marca in lista_c:
                    mensaje_alerta += f"- El día **{dia} de {MESES[reg_mes_num]}**, el otro técnico del mismo centro (**{tec_col}**) está de **{desc_marca} ({marca_col})**.\n"
            mensaje_alerta += "\n¿Deseas registrar esta ausencia a pesar del solapamiento?"
            st.warning(mensaje_alerta)
            
            confirmado_solapamiento = st.checkbox("Confirmo que deseo registrar esto a pesar de la coincidencia", value=False)
            
            if st.button("Confirmar y Guardar Definitivamente", type="primary"):
                if not confirmado_solapamiento:
                    st.error("❌ Debes marcar la casilla de confirmación para proceder.")
                else:
                    detalle_solapamientos_str = []
                    for dia, lista_c in st.session_state.coincidencias_pendientes:
                        nombres_coincidentes = ", ".join([f"{t[0]} ({t[2]})" for t in lista_c])
                        detalle_solapamientos_str.append(f"Día {dia} ({nombres_coincidentes})")

                    for dia in range(reg_d_ini, reg_d_fin + 1):
                        clave_reg = (dd_anio, reg_tec, str(reg_mes_num), str(dia))
                        if reg_tipo == '':
                            REGISTROS.pop(clave_reg, None)
                            REGISTROS.pop(f"{dd_anio}|{reg_tec}|{reg_mes_num}|{dia}", None)
                        elif reg_tipo == 'HE':
                            h_jornada = obtener_horas_jornada_real(reg_tec, dd_anio, reg_mes_num, dia)
                            h_efectivas = min(val_horas_disfrute, h_jornada)
                            REGISTROS[clave_reg] = {'tipo': 'HE', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                        elif reg_tipo == 'HLD':
                            h_teorico = obtener_horas_hld(reg_tec, reg_mes_num, dia, dd_anio)
                            h_efectivas = min(val_horas_disfrute, h_teorico)
                            REGISTROS[clave_reg] = {'tipo': 'HLD', 'horas_gastadas': h_efectivas, 'anio': dd_anio, 'tec': reg_tec}
                        elif reg_tipo == 'HE+HLD':
                            REGISTROS[clave_reg] = {
                                'tipo': 'HE+HLD', 
                                'he_horas': val_he_mix, 
                                'hld_horas': val_hld_mix, 
                                'anio': dd_anio, 
                                'tec': reg_tec
                            }
                        else:
                            REGISTROS[clave_reg] = reg_tipo
                    
                    guardar_en_drive(REGISTROS)
                    
                    texto_incidencia = f"Solapamiento en {TECNICOS[reg_tec]['ci']}: {reg_tec} ({reg_tipo}) coincide con {'; '.join(detalle_solapamientos_str)} en {MESES[reg_mes_num]} {dd_anio}"
                    if 'historial_incidencias_solapamiento' not in st.session_state:
                        st.session_state.historial_incidencias_solapamiento = []
                    
                    st.session_state.historial_incidencias_solapamiento.append({
                        'hora': datetime.now().strftime("%H:%M:%S"),
                        'centro': TECNICOS[reg_tec]['ci'],
                        'tecnico': reg_tec,
                        'descripcion': texto_incidencia,
                        'usuario': st.session_state.get('usuario_actual', 'Sistema')
                    })

                    st.session_state.historial_auditoria.append({
                        'hora': datetime.now().strftime("%H:%M:%S"),
                        'tec': reg_tec,
                        'rango': f"Del {reg_d_ini} al {reg_d_fin} de {MESES[reg_mes_num]} {dd_anio} (Con Solapamiento)",
                        'tipo': reg_tipo
                    })
                    st.session_state.intentando_guardar = False
                    st.session_state.coincidencias_pendientes = []
                    st.success(f"✅ Registros guardados y solapamiento registrado en Incidencias correctamente.")
                    st.rerun()
    else:
        st.button('Guardar Rango (Bloqueado para Lectores)', disabled=True, use_container_width=True)

    st.markdown(f"### 📅 Visualización: {MESES[reg_mes_num]} {dd_anio}")
    if dd_vista == 'Calendario Individual':
        ci_tec = TECNICOS[reg_tec]['ci']
        cal = calendar.monthcalendar(dd_anio, reg_mes_num)
        festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(ci_tec, [])
        
        html_cal = f"<h4 style='color:#0F172A;'>Calendario de {reg_tec} ({ci_tec})</h4><table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; width:100%; font-size:12px; border-color: #CBD5E1;'>"
        html_cal += "<tr style='background-color:#002B36; color:white;'><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th style='background-color:#64748B;'>Sáb</th><th style='background-color:#64748B;'>Dom</th></tr>"
        for semana in cal:
            html_cal += "<tr>"
            for idx, dia in enumerate(semana):
                if dia == 0:
                    html_cal += "<td style='background-color:#F1F5F9; height:50px;'></td>"
                else:
                    val_reg = REGISTROS.get((dd_anio, reg_tec, str(reg_mes_num), str(dia)), REGISTROS.get(f"{dd_anio}|{reg_tec}|{reg_mes_num}|{dia}", ''))
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
    else:
        num_dias = calendar.monthrange(dd_anio, reg_mes_num)[1]
        dias_semana_abrev = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
        
        html_matriz = """
        <style>
          .tabla-matriz-global { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px; white-space: nowrap; }
          .tabla-matriz-global th { background-color: #002B36; color: white; padding: 6px; text-align: center; border: 1px solid #CBD5E1; }
          .tabla-matriz-global td { padding: 6px; text-align: center; border: 1px solid #CBD5E1; font-weight: bold; color: #0F172A; }
        </style>
        <div style="overflow-x: auto;">
        <table class="tabla-matriz-global">
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Centro</th>
        """
        for d_col in range(1, num_dias + 1):
            weekday_col = calendar.weekday(dd_anio, reg_mes_num, d_col)
            html_matriz += f"<th>{d_col}<br><span style='font-size:9px; color:#94A3B8;'>{dias_semana_abrev[weekday_col]}</span></th>"
        html_matriz += "</tr></thead><tbody>"
        
        for nombre_tec, info_tec_item in TECNICOS.items():
            html_matriz += f"<tr><td style='text-align: left;'><b>{nombre_tec}</b></td><td>{info_tec_item['ci']}</td>"
            festivos_ci = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(info_tec_item['ci'], [])
            
            for d_col in range(1, num_dias + 1):
                val_reg = REGISTROS.get((dd_anio, nombre_tec, str(reg_mes_num), str(d_col)), REGISTROS.get(f"{dd_anio}|{nombre_tec}|{reg_mes_num}|{d_col}", ''))
                marca, extra_txt = extraer_info_registro(val_reg, nombre_tec, dd_anio, reg_mes_num, d_col)
                bg_color = '#ffffff'
                weekday_col = calendar.weekday(dd_anio, reg_mes_num, d_col)
                
                if (reg_mes_num, d_col) in festivos_ci:
                    bg_color = LEYENDA['FEST'][1]
                    if not marca: marca = 'FEST'
                elif weekday_col >= 5:
                    bg_color = LEYENDA['SAB'][1] if weekday_col == 5 else LEYENDA['DOM'][1]
                    if not marca: marca = 'SAB' if weekday_col == 5 else 'DOM'
                elif marca in LEYENDA:
                    bg_color = LEYENDA[marca][1]

                html_matriz += f"<td style='background-color: {bg_color};'>{marca}{extra_txt}</td>"
            html_matriz += "</tr>"
        html_matriz += "</tbody></table></div>"
        st.markdown(html_matriz, unsafe_allow_html=True)

    html_leyenda_reg = "<div style='background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; margin-top: 25px; margin-bottom: 25px; font-family: sans-serif;'><h4 style='margin: 0 0 8px 0; color: #0F172A; font-size: 14px;'>📖 Leyenda de Códigos y Estados</h4><div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
    for k, (desc, color) in LEYENDA.items():
        html_leyenda_reg += f"<div style='display: flex; align-items: center; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 4px 8px; font-size: 11px;'><span style='background-color: {color}; border: 1px solid #94A3B8; width: 14px; height: 14px; display: inline-block; margin-right: 6px; border-radius: 2px;'></span><b>{k}:</b>&nbsp;{desc}</div>"
    html_leyenda_reg += "</div></div>"
    st.markdown(html_leyenda_reg, unsafe_allow_html=True)

with tab_he:
    st.markdown("### ⚡ Gestión y Acumulación de Horas Extra")
    st.markdown("Registro de bolsa de horas extraordinarias reales. Conversión automática ponderada (x1.75).")
    he_anio = st.selectbox('Año Operativo HE:', ANOS_DISPONIBLES, key='he_anio_sel')
    he_tec = st.selectbox('Técnico Asignado:', list(TECNICOS.keys()), key='he_tec_sel')
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        txt_horas = st.number_input('Horas Reales Trabajadas:', min_value=-100.0, max_value=100.0, value=1.0, step=0.5)
    with col_h2:
        txt_motivo = st.text_input('Motivo / Justificación:', placeholder='Ej. Corrección de error o Urgencia técnica')
        
    if st.session_state.rol_actual == "Editor":
        if st.button('Registrar Horas Extra', use_container_width=True, type='primary'):
            if he_tec not in REGISTROS_HE:
                REGISTROS_HE[he_tec] = []
            
            usuario_registro = st.session_state.get('usuario_actual', 'Sistema')
            fecha_registro = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            REGISTROS_HE[he_tec].append({
                'anio': he_anio, 
                'horas_reales': txt_horas, 
                'motivo': txt_motivo or 'Sin motivo',
                'usuario': usuario_registro,
                'fecha': fecha_registro
            })
            guardar_he_drive()
            st.success(f"✅ Se han procesado {txt_horas}h extra reales a {he_tec}.")
            st.rerun()
    else:
        st.button('Registrar Horas Extra (Bloqueado)', disabled=True, use_container_width=True)

    tot_r = sum(i['horas_reales'] for i in REGISTROS_HE.get(he_tec, []) if i['anio'] == he_anio)
    tot_c = calcular_he_compensadas_totales(he_tec, he_anio)
    tot_g = calcular_he_consumidas_horas(he_tec, he_anio)
    st.info(f"📊 **Resumen HE ({he_tec} - {he_anio}):** Reales netas: {tot_r}h | Compensadas (x1.75): {tot_c:.2f}h | Gastadas: {tot_g:.2f}h | **Disponibles: {tot_c - tot_g:.2f}h**")

    st.markdown("---")
    st.markdown(f"#### 📋 Historial de Registros HE para {he_tec} ({he_anio})")
    
    lista_he_tec_anio = [
        (idx, item) for idx, item in enumerate(REGISTROS_HE.get(he_tec, [])) 
        if item['anio'] == he_anio
    ]
    
    if not lista_he_tec_anio:
        st.info("No hay registros de horas extra para este técnico en el año seleccionado.")
    else:
        datos_tabla_he = []
        for idx, item in lista_he_tec_anio:
            datos_tabla_he.append({
                'ID': idx,
                'Fecha Registro': item.get('fecha', 'N/D'),
                'Horas Reales': item['horas_reales'],
                'Horas Compensadas (x1.75)': round(item['horas_reales'] * 1.75, 2),
                'Motivo': item['motivo'],
                'Registrado por': item.get('usuario', 'Desconocido')
            })
        
        st.dataframe(pd.DataFrame(datos_tabla_he), use_container_width=True, hide_index=True)
        
        if st.session_state.rol_actual == "Editor":
            id_a_borrar = st.selectbox(
                "Seleccionar ID de registro HE para eliminar por error:", 
                [item[0] for item in lista_he_tec_anio],
                key='id_borrar_he'
            )
            if st.button("🗑️ Eliminar Registro Seleccionado", type="secondary"):
                REGISTROS_HE[he_tec].pop(id_a_borrar)
                guardar_he_drive()
                st.success("Registro eliminado correctamente.")
                st.rerun()

with tab_cobertura:
    st.markdown("### 👥 Análisis Operativo de Cobertura Diaria")
    fecha_cob = st.date_input("Seleccionar fecha de control:", value=date.today())
    
    if fecha_cob:
        anio_c, mes_c, dia_c = fecha_cob.year, fecha_cob.month, fecha_cob.day
        
        st.markdown("#### 📋 Estado de Técnicos en la Fecha Seleccionada")
        detalles_cov_tec = []
        total_trab_global = 0
        total_tecnicos = len(TECNICOS)
        
        for tec, info in TECNICOS.items():
            ci = info['ci']
            val_reg = REGISTROS.get((anio_c, tec, str(mes_c), str(dia_c)), REGISTROS.get(f"{anio_c}|{tec}|{mes_c}|{dia_c}", ''))
            marca, _ = extraer_info_registro(val_reg, tec, anio_c, mes_c, dia_c)
            weekday = calendar.weekday(anio_c, mes_c, dia_c)
            festivos = FESTIVOS_POR_ANIO.get(anio_c, {}).get(ci, [])
            es_festivo = (mes_c, dia_c) in festivos or weekday >= 5
            
            if marca == '' and not es_festivo:
                estado_hoy = "TRABAJA"
                obs = f"Trabaja {int(obtener_horas_jornada_real(tec, anio_c, mes_c, dia_c))} h"
                total_trab_global += 1
            else:
                estado_hoy = "NO TRABAJA"
                if marca == 'V':
                    obs = "Vacaciones"
                elif marca == 'VPA':
                    obs = "Vac. Pendientes Año Ant."
                elif marca == 'BL':
                    obs = "Baja Laboral"
                elif marca == 'FEST':
                    obs = "Festivo / No Laborable"
                elif marca in ['SAB', 'DOM']:
                    obs = "Fin de semana"
                else:
                    obs = LEYENDA.get(marca, (marca, ''))[0] if marca else "No laborable / Finde"
            
            detalles_cov_tec.append({
                'CI': ci,
                'TÉCNICO': tec,
                'CÓDIGO DE ESTADO': marca if marca else ('-' if not es_festivo else 'FEST'),
                'ESTADO HOY': estado_hoy,
                'OBSERVACIONES': obs
            })
            
        st.dataframe(pd.DataFrame(detalles_cov_tec), use_container_width=True, hide_index=True)
        
        disp_global_pct = round((total_trab_global / total_tecnicos) * 100) if total_tecnicos > 0 else 0
        ausentes_global = total_tecnicos - total_trab_global
        
        col_res1, col_res2 = st.columns([2, 1])
        with col_res2:
            st.markdown(f"""
            <div class="card-corporate" style="padding: 12px; font-family: sans-serif;">
                <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
                    <tr><td><b>Fecha</b></td><td style="text-align: right;"><b>{fecha_cob.strftime('%d/%m/%Y')}</b></td></tr>
                    <tr><td>Disponibles hoy</td><td style="text-align: right;"><b>{total_trab_global}/{total_tecnicos}</b></td></tr>
                    <tr><td>Ausentes hoy</td><td style="text-align: right;"><b>{ausentes_global}</b></td></tr>
                    <tr><td>Disponibilidad global</td><td style="text-align: right;"><b style="color: #047857;">{disp_global_pct}%</b></td></tr>
                    <tr><td>Estado servicio</td><td style="text-align: right;"><span style="color: #047857; font-weight: bold;">🟢 OK</span></td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

        with col_res1:
            st.markdown("#### 🏢 Resumen de Cobertura por Centro (CI)")
            
            centros_dict = {}
            for row in detalles_cov_tec:
                ci = row['CI']
                if ci not in centros_dict:
                    centros_dict[ci] = {'asignados': 0, 'trabajando': 0, 'ausentes': 0}
                centros_dict[ci]['asignados'] += 1
                if row['ESTADO HOY'] == 'TRABAJA':
                    centros_dict[ci]['trabajando'] += 1
                else:
                    centros_dict[ci]['ausentes'] += 1
                    
            resumen_centros_data = []
            for ci, data in centros_dict.items():
                asig = data['asignados']
                trab = data['trabajando']
                aus = data['ausentes']
                
                if asig == 0:
                    cob_ci = "SIN ASIGNACIÓN"
                elif trab == asig:
                    cob_ci = "🟢 OK"
                elif trab >= asig / 2:
                    cob_ci = "🟡 COBERTURA REDUCIDA - 50%"
                else:
                    cob_ci = "🔴 COBERTURA CRÍTICA"
                    
                resumen_centros_data.append({
                    'CI': ci,
                    'Técnicos asignados': asig,
                    'Trabajando hoy': trab,
                    'Ausentes': aus,
                    'Cobertura CI': cob_ci
                })
                
            st.dataframe(pd.DataFrame(resumen_centros_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### ⏳ Próxima Incorporación de Técnicos Ausentes")
        
        tecnicos_ausentes_hoy = [row['TÉCNICO'] for row in detalles_cov_tec if row['ESTADO HOY'] == 'NO TRABAJA']
        
        if not tecnicos_ausentes_hoy:
            st.success("✅ Todos los técnicos se encuentran operativos (trabajando) en la fecha seleccionada.")
        else:
            proximas_inc_data = []
            for tec in tecnicos_ausentes_hoy:
                ci_tec = TECNICOS[tec]['ci']
                f_cursor = fecha_cob + timedelta(days=1)
                dias_busqueda = 0
                fecha_incorporacion = None
                
                while dias_busqueda < 90:
                    a_cur, m_cur, d_cur = f_cursor.year, f_cursor.month, f_cursor.day
                    w_cur = f_cursor.weekday()
                    festivos_ci = FESTIVOS_POR_ANIO.get(a_cur, {}).get(ci_tec, [])
                    es_festivo_cur = (m_cur, d_cur) in festivos_ci or w_cur >= 5
                    
                    val_reg_cur = REGISTROS.get((a_cur, tec, str(m_cur), str(d_cur)), REGISTROS.get(f"{a_cur}|{tec}|{m_cur}|{d_cur}", ''))
                    marca_cur, _ = extraer_info_registro(val_reg_cur, tec, a_cur, m_cur, d_cur)
                    
                    if marca_cur == '' and not es_festivo_cur:
                        fecha_incorporacion = f_cursor
                        break
                        
                    f_cursor += timedelta(days=1)
                    dias_busqueda += 1
                    
                if fecha_incorporacion:
                    dias_faltantes = (fecha_incorporacion - fecha_cob).days
                    str_inc = f"{fecha_incorporacion.strftime('%d/%m/%Y')} (en {dias_faltantes} día{'s' if dias_faltantes > 1 else ''})"
                else:
                    str_inc = "No estimada en los próximos 90 días"
                    
                proximas_inc_data.append({
                    'Centro': ci_tec,
                    'Técnico Ausente': tec,
                    'Próxima Incorporación': str_inc
                })
                
            st.dataframe(pd.DataFrame(proximas_inc_data), use_container_width=True, hide_index=True)

with tab_balance:
    st.markdown(f"### 📈 Balance Consolidado de Saldos y Recursos ({dd_anio})")
    datos_bal = []
    for tec, info in TECNICOS.items():
        hld_tot = obtener_hld_totales_tecnico(tec, dd_anio)
        vpa_tot = obtener_vpa_totales_tecnico(tec, dd_anio)
        
        vac_c = 0
        vpa_c = 0
        hld_c = 0.0
        for k, v in REGISTROS.items():
            a, t, m, d = None, None, None, None
            if isinstance(k, tuple) and len(k) == 4:
                a, t, m, d = k[0], k[1], int(k[2]), int(k[3])
            elif isinstance(k, str) and '|' in k:
                parts = k.split('|')
                if len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])

            if a == dd_anio and t == tec:
                if isinstance(v, dict):
                    tipo_v = v.get('tipo')
                    if tipo_v == 'V': vac_c += 1
                    elif tipo_v == 'VPA': vpa_c += 1
                    elif tipo_v == 'HLD':
                        hld_c += v.get('horas_gastadas', 0.0)
                    elif tipo_v == 'HE+HLD':
                        hld_c += v.get('hld_horas', 0.0)
                else:
                    if v == 'V': vac_c += 1
                    elif v == 'VPA': vpa_c += 1
                    elif v == 'HLD':
                        hld_c += obtener_horas_hld(tec, m, d, dd_anio)

        he_comp = calcular_he_compensadas_totales(tec, dd_anio)
        he_gast = calcular_he_consumidas_horas(tec, dd_anio)
        
        datos_bal.append({
            'Centro': info['ci'], 'Técnico': tec,
            'Vac. Cons.': vac_c, 'Vac. Pend.': info['vac_totales'] - vac_c,
            'VPA Cons.': vpa_c, 'VPA Pend.': vpa_tot - vpa_c,
            'HLD Cons.': round(hld_c, 2), 'HLD Pend.': round(hld_tot - hld_c, 2),
            'HE Comp.': he_comp, 'HE Disp.': round(he_comp - he_gast, 2)
        })
    st.dataframe(pd.DataFrame(datos_bal), use_container_width=True, hide_index=True)

with tab_prl:
    st.markdown("### 🏢 Control de Accesos CI (Reconocimientos Médicos)")
    st.markdown("Control de caducidad de reconocimientos médicos del equipo técnico.")

    hoy_prl = date.today()
    tabla_prl_visual = []

    for tec, info in TECNICOS.items():
        datos_tec_prl = REGISTROS_PRL.get(tec, {'nip': 'N/D', 'dni': 'N/D', 'fecha': '2030-01-01', 'obs': ''})
        f_str = datos_tec_prl.get('fecha', '2030-01-01')
        
        try:
            f_cad = datetime.strptime(f_str, '%Y-%m-%d').date()
            dias_restantes = (f_cad - hoy_prl).days
        except Exception:
            dias_restantes = 9999
            f_cad = hoy_prl

        if dias_restantes < 30:
            semaforo = "🔴 ROJO (< 1 mes)"
            accion = "🚨 Pedir cita reconocimiento"
        elif dias_restantes < 60:
            semaforo = "🟠 NARANJA (< 2 meses)"
            accion = "⚠️ Revisar y planificar cita"
        else:
            semaforo = "🟢 VERDE"
            accion = "✅ Al corriente"

        tabla_prl_visual.append({
            'Centro': info['ci'],
            'Técnico': tec,
            'NIP': datos_tec_prl.get('nip', ''),
            'DNI': datos_tec_prl.get('dni', ''),
            'Próxima Revisión': f_cad.strftime('%d/%m/%Y'),
            'Días Restantes': dias_restantes,
            'Estado': semaforo,
            'Acción Recomendada': accion,
            'Observaciones': datos_tec_prl.get('obs', '')
        })

    st.dataframe(pd.DataFrame(tabla_prl_visual), use_container_width=True, hide_index=True)

    if st.session_state.rol_actual == "Editor":
        st.markdown("---")
        st.markdown("#### ✏️ Actualizar Reconocimiento Médico (PRL)")
        tec_sel_prl = st.selectbox("Seleccionar Técnico a Actualizar:", list(TECNICOS.keys()), key='tec_prl_upd')
        current_data = REGISTROS_PRL.get(tec_sel_prl, {})
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            nuevo_nip = st.text_input("NIP:", value=current_data.get('nip', ''))
            nuevo_dni = st.text_input("DNI:", value=current_data.get('dni', ''))
        with col_p2:
            try:
                def_date = datetime.strptime(current_data.get('fecha', '2027-01-01'), '%Y-%m-%d').date()
            except Exception:
                def_date = date.today()
            nueva_fecha = st.date_input("Fecha Reconocimiento:", value=def_date)
        with col_p3:
            nueva_obs = st.text_input("Observaciones:", value=current_data.get('obs', ''))

        if st.button("💾 Guardar Cambios PRL", type="primary"):
            REGISTROS_PRL[tec_sel_prl] = {
                'nip': nuevo_nip,
                'dni': nuevo_dni,
                'fecha': nueva_fecha.strftime('%Y-%m-%d'),
                'obs': nueva_obs
            }
            guardar_prl_drive()
            st.success(f"✅ Reconocimiento médico actualizado correctamente para {tec_sel_prl}.")
            st.rerun()

with tab_incidencias:
    st.markdown("### ⚠️ Registro Histórico de Incidencias y Solapamientos")
    if 'historial_incidencias_solapamiento' in st.session_state and st.session_state.historial_incidencias_solapamiento:
        st.dataframe(pd.DataFrame(st.session_state.historial_incidencias_solapamiento), use_container_width=True, hide_index=True)
    else:
        st.info("No se han registrado incidencias de solapamiento en la sesión actual.")

with tab_auditoria:
    st.markdown("### 📋 Auditoría de Acciones de la Sesión")
    if st.session_state.historial_auditoria:
        st.dataframe(pd.DataFrame(st.session_state.historial_auditoria), use_container_width=True, hide_index=True)
    else:
        st.info("No hay acciones registradas en el portafolio de auditoría todavía.")

with tab_config:
    st.markdown("### ⚙️ Configuración General y Festivos")
    st.markdown("Gestión de festivos por centro de trabajo y año operativo.")
    conf_anio_sel = st.selectbox("Año operativo a configurar:", ANOS_DISPONIBLES, key='conf_anio')
    conf_ci_sel = st.selectbox("Centro de Trabajo (CI):", list(FESTIVOS_DEFAULT.keys()), key='conf_ci')
    
    festivos_actuales = FESTIVOS_POR_ANIO.get(conf_anio_sel, FESTIVOS_POR_ANIO_DEFAULT[conf_anio_sel]).get(conf_ci_sel, [])
    st.write(f"Festivos actuales configurados para **{conf_ci_sel}** en **{conf_anio_sel}**: {festivos_actuales}")

with tab_horarios:
    st.markdown("### ⏰ Configuración de Horarios por Centro (CI)")
    horarios_anio_sel = st.selectbox("Año Horarios:", ANOS_DISPONIBLES, key='horarios_anio_s')
    horarios_actuales = HORARIOS_CI_ANUAL.get(horarios_anio_sel, HORARIOS_CI_DEFAULT[horarios_anio_sel])
    
    tabla_horarios_vis = []
    for ci_n, val_h in horarios_actuales.items():
        tabla_horarios_vis.append({
            'Centro': ci_n,
            'Horario': val_h['horario'].replace('<br>', ' | '),
            'Horas Semanales': val_h['h_sem'],
            'Observaciones': val_h['obs']
        })
    st.dataframe(pd.DataFrame(tabla_horarios_vis), use_container_width=True, hide_index=True)

with tab_hld:
    st.markdown("### ⏳ Configuración Anual de Horas de Libre Disposición (HLD)")
    hld_anio_sel = st.selectbox("Año HLD:", ANOS_DISPONIBLES, key='hld_anio_s')
    hld_actuales = HLD_ANUAL_POR_ANIO.get(hld_anio_sel, HLD_ANUAL_DEFAULT[hld_anio_sel])
    
    tabla_hld_vis = [{'Centro': ci_n, 'Horas HLD Anuales': h_val} for ci_n, h_val in hld_actuales.items()]
    st.dataframe(pd.DataFrame(tabla_hld_vis), use_container_width=True, hide_index=True)

st.markdown("""
<div class="footer-copyright">
    © 2026 Juan Pedro Murillo Huete. Todos los derechos reservados. <br>
    Sistema de Accesos CI - Indra Group & Repsol RPECII.
</div>
""", unsafe_allow_html=True)
