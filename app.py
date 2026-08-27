import calendar
import json
from datetime import datetime, date
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

# ==========================================
# FUNCIONES DE PERSISTENCIA
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
    datos_json = {f"{a}|{t}|{m}|{d}": v for (a, t, m, d), v in registros_dict.items()}
    with open(RUTA_BDD, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)
        
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
            requests.patch(url, headers=headers, json=payload)
        except Exception:
            pass

def cargar_de_drive():
    try:
        with open(RUTA_BDD, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            resultado = {}
            for k, v in datos_json.items():
                parts = k.split('|')
                if len(parts) == 3:
                    resultado[(2026, parts[0], parts[1], parts[2])] = v
                else:
                    resultado[(int(parts[0]), parts[1], parts[2], parts[3])] = v
            return resultado
    except FileNotFoundError:
        return {}

def guardar_festivos_drive():
    datos_json = {str(anio): {ci: [[m, d] for m, d in lista] for ci, lista in centros.items()} for anio, centros in FESTIVOS_POR_ANIO.items()}
    with open(RUTA_FESTIVOS, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)

def cargar_festivos_drive():
    try:
        with open(RUTA_FESTIVOS, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            return {int(anio): {ci: [tuple(x) for x in lista] for ci, lista in centros.items()} for anio, centros in datos_json.items()}
    except FileNotFoundError:
        return None

def guardar_he_drive():
    with open(RUTA_HE, 'w', encoding='utf-8') as f:
        json.dump(REGISTROS_HE, f, ensure_ascii=False, indent=4)

def cargar_he_drive():
    try:
        with open(RUTA_HE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_horarios_ci_drive():
    datos_json = {str(anio): centros for anio, centros in HORARIOS_CI_ANUAL.items()}
    with open(RUTA_HORARIOS_CI, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)

def cargar_horarios_ci_drive():
    try:
        with open(RUTA_HORARIOS_CI, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            return {int(anio): centros for anio, centros in datos_json.items()}
    except FileNotFoundError:
        return None

def guardar_hld_anual_drive():
    datos_json = {str(anio): hld_dict for anio, hld_dict in HLD_ANUAL_POR_ANIO.items()}
    with open(RUTA_HLD_ANUAL, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)

def cargar_hld_anual_drive():
    try:
        with open(RUTA_HLD_ANUAL, 'r', encoding='utf-8') as f:
            datos_json = json.load(f)
            return {int(anio): hld_dict for anio, hld_dict in datos_json.items()}
    except FileNotFoundError:
        return None

# 1. CONFIGURACIÓN Y BASE DE DATOS
TECNICOS = {
    'David Rodriguez': {'ci': 'Petronor', 'vac_totales': 22, 'vpa_base': 8, 'he_totales': 0.0},
    'Endika Ramirez': {'ci': 'Petronor', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0},
    'Fernando Bocija': {'ci': 'Coruña', 'vac_totales': 23, 'vpa_base': 11, 'he_totales': 0.0},
    'Joan Vila': {'ci': 'Tarragona', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0},
    'Óscar Luna': {'ci': 'Tarragona', 'vac_totales': 22, 'vpa_base': 1, 'he_totales': 0.0},
    'David Muñoz': {'ci': 'Puertollano', 'vac_totales': 22, 'vpa_base': 4, 'he_totales': 0.0},
    'Juan Pedro Murillo': {'ci': 'Puertollano', 'vac_totales': 22, 'vpa_base': 2, 'he_totales': 0.0},
    'Simón Conesa': {'ci': 'Cartagena', 'vac_totales': 22, 'vpa_base': 6, 'he_totales': 0.0},
    'Alejandro Gutiérrez': {'ci': 'Cartagena', 'vac_totales': 22, 'vpa_base': 0, 'he_totales': 0.0}
}

LEYENDA = {
    'V': ('Vacaciones', '#C6EFCE'),
    'VPA': ('Vac. Pendientes Año Anterior', '#E2EFDA'),
    'HE': ('Horas Extras Disfrutadas / Parciales', '#FCE4D6'),
    'HLD': ('Hora de Libre Disposición / Parciales', '#BDD7EE'),
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

HORARIOS_CI_DEFAULT = {
    anio: {
        'Petronor': {'horario': "L-J 08'00h-17'10h<br>V 08'00h-13'27h", 'h_sem': "39'27h", 'obs': "-"},
        'Coruña': {'horario': "L-V 07'20h-15'15h", 'h_sem': "39'36h", 'obs': "-"},
        'Tarragona': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "Parada programada / Excepción anual"},
        'Puertollano': {'horario': "L-V 07'15h-15'15h", 'h_sem': "40h", 'obs': "-"},
        'Cartagena': {'horario': "L-V 07'00h-15'00h", 'h_sem': "40h", 'obs': "Parada programada / Excepción anual"}
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
HORARIOS_CI_ANUAL = cargar_horarios_ci_drive() or HORARIOS_CI_DEFAULT
HLD_ANUAL_POR_ANIO = cargar_hld_anual_drive() or HLD_ANUAL_DEFAULT

REGISTROS = cargar_de_drive()
REGISTROS_HE = cargar_he_drive()

if 'historial_auditoria' not in st.session_state:
    st.session_state.historial_auditoria = []

def obtener_vpa_totales_tecnico(tecnico, anio):
    if anio == ANOS_DISPONIBLES[0]:
        return TECNICOS[tecnico].get('vpa_base', 0)
    else:
        anio_prev = anio - 1
        vac_cons_prev = 0
        for key, val in REGISTROS.items():
            parts = key.split('|') if isinstance(key, str) else None
            if parts and len(parts) == 4:
                a, t = int(parts[0]), parts[1]
            elif isinstance(key, tuple) and len(key) == 4:
                a, t = key[0], key[1]
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
    if es_verano:
        return 7.0
    else:
        if ci == 'Coruña':
            return 8.5 if weekday < 4 else 6.0
        else:
            return 9.0 if weekday < 4 else 7.0

def calcular_he_compensadas_totales(tecnico, anio):
    lista_he = REGISTROS_HE.get(tecnico, [])
    total_reales = sum(item['horas_reales'] for item in lista_he if item['anio'] == anio)
    return round(total_reales * 1.75, 2)

def calcular_he_consumidas_horas(tecnico, anio):
    total_consumido_h = 0.0
    for key, val in REGISTROS.items():
        if isinstance(val, dict) and val.get('anio') == anio and val.get('tec') == tecnico and val.get('tipo') == 'HE':
            total_consumido_h += val.get('horas_gastadas', 0.0)
        else:
            parts = key.split('|') if isinstance(key, str) else None
            if parts and len(parts) == 4:
                a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                if a == anio and t == tecnico and val == 'HE':
                    total_consumido_h += obtener_horas_hld(tecnico, m, d, anio)
            elif isinstance(key, tuple) and len(key) == 4:
                a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                if a == anio and t == tecnico and val == 'HE':
                    total_consumido_h += obtener_horas_hld(tecnico, m, d, anio)
    return round(total_consumido_h, 2)

st.markdown("<h2 style='color:#005B7F; margin:0;'>Cuadrante de Calendarios Técnicos - SAT CI REPSOL</h2>", unsafe_allow_html=True)

col_v1, col_v2, col_v3 = st.columns([1.5, 1, 1])
with col_v1:
    dd_vista = st.selectbox('Modo Vista:', ['Calendario Individual', 'Matriz Cuadrante Global (Equipo)'])
with col_v2:
    dd_anio = st.selectbox('Año:', ANOS_DISPONIBLES)
with col_v3:
    if st.button('📥 Descargar HTML Detallado'):
        pass  # Mantener lógica de descarga previa si se desea

tab_registrar, tab_he, tab_cobertura, tab_balance, tab_incidencias, tab_auditoria, tab_config, tab_horarios, tab_hld = st.tabs([
    '🛠️ Registrar', '⚡ Horas Extra', '👥 Cobertura', '📈 Balance', '⚠️ Incidencias', '📋 Auditoría', '⚙️ Configuración', '⏰ Horarios / CI', '⏳ Config. HLD'
])

with tab_registrar:
    st.markdown("### 📝 Registro de Calendarios y Ausencias")
    # Lógica de registro existente...

with tab_he:
    st.markdown("### ⚡ Gestión y Acumulación de Horas Extra")
    # Lógica de horas extra existente...

with tab_cobertura:
    st.markdown("### 👥 Análisis de Cobertura Diaria")

with tab_balance:
    st.markdown(f"### 📈 Balance Consolidado de Saldos - {dd_anio}")

with tab_incidencias:
    st.markdown(f"### ⚠️ Control de Excesos y Alertas ({dd_anio})")

with tab_auditoria:
    st.markdown("### 📋 Historial de Cambios de la Sesión")

with tab_config:
    st.markdown("### ⚙️ Configuración y Copias de Seguridad")

with tab_horarios:
    st.markdown(f"### ⏰ Horarios Reales de Cliente por CI ({dd_anio})[cite: 2]")
    st.markdown("Detalle de los turnos oficiales y cómputo de horas semanales por centro de trabajo configurables por año[cite: 2]:")
    horarios_anio = HORARIOS_CI_ANUAL.get(dd_anio, HORARIOS_CI_DEFAULT[dd_anio])
    h_data = [{'Centro': ci, 'Horario': d['horario'], 'H/Semana': d['h_sem'], 'Observaciones': d['obs']} for ci, d in horarios_anio.items()]
    st.dataframe(pd.DataFrame(h_data), use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### ⚙️ Modificar Horario de CI por Año[cite: 2]")
    col_h_1, col_h_2 = st.columns(2)
    with col_h_1:
        ci_h_anio = st.selectbox('Año CI:', ANOS_DISPONIBLES, key='ci_h_anio')
    with col_h_2:
        ci_h_centro = st.selectbox('Centro CI:', list(HORARIOS_CI_DEFAULT[ANOS_DISPONIBLES[0]].keys()), key='ci_h_centro')
        
    col_h_3, col_h_4 = st.columns(2)
    with col_h_3:
        txt_horario_texto = st.text_input('Horario:', value=HORARIOS_CI_ANUAL.get(ci_h_anio, HORARIOS_CI_DEFAULT[ci_h_anio])[ci_h_centro]['horario'])
    with col_h_4:
        txt_horario_sem = st.text_input('H/Semana:', value=HORARIOS_CI_ANUAL.get(ci_h_anio, HORARIOS_CI_DEFAULT[ci_h_anio])[ci_h_centro]['h_sem'])
        
    txt_horario_obs = st.text_input('Observaciones:', value=HORARIOS_CI_ANUAL.get(ci_h_anio, HORARIOS_CI_DEFAULT[ci_h_anio])[ci_h_centro]['obs'])
    
    if st.button('Guardar Horario CI'):
        if ci_h_anio not in HORARIOS_CI_ANUAL:
            HORARIOS_CI_ANUAL[ci_h_anio] = HORARIOS_CI_DEFAULT[ci_h_anio].copy()
        HORARIOS_CI_ANUAL[ci_h_anio][ci_h_centro] = {
            'horario': txt_horario_texto,
            'h_sem': txt_horario_sem,
            'obs': txt_horario_obs
        }
        guardar_horarios_ci_drive()
        st.success(f"✅ Horario actualizado correctamente para {ci_h_centro} en el año {ci_h_anio}.")

with tab_hld:
    st.markdown(f"### ⏳ Configuración de HLD Totales por Centro y Año ({dd_anio})[cite: 2]")
    st.markdown("Asignación de horas de libre disposición totales que recibe cada Complejo Industrial para este año[cite: 2]:")
    hld_anio = HLD_ANUAL_POR_ANIO.get(dd_anio, HLD_ANUAL_DEFAULT[dd_anio])
    hld_data = [{'Centro (CI)': ci, 'Total HLD (h)': f"{val}h"} for ci, val in hld_anio.items()]
    st.dataframe(pd.DataFrame(hld_data), use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### ⚙️ Configurar Total de HLD por Centro y Año[cite: 2]")
    col_d_1, col_d_2 = st.columns(2)
    with col_d_1:
        hld_cfg_anio = st.selectbox('Año HLD:', ANOS_DISPONIBLES, key='hld_cfg_anio')
    with col_d_2:
        hld_cfg_centro = st.selectbox('Centro HLD:', list(HLD_ANUAL_DEFAULT[ANOS_DISPONIBLES[0]].keys()), key='hld_cfg_centro')
        
    val_actual_hld = HLD_ANUAL_POR_ANIO.get(hld_cfg_anio, HLD_ANUAL_DEFAULT[hld_cfg_anio]).get(hld_cfg_centro, 87.0)
    txt_hld_valor_asig = st.number_input('Total HLD:', value=float(val_actual_hld), step=0.5, key='txt_hld_valor_asig')
    
    if st.button('Guardar HLD Anual'):
        if hld_cfg_anio not in HLD_ANUAL_POR_ANIO:
            HLD_ANUAL_POR_ANIO[hld_cfg_anio] = HLD_ANUAL_DEFAULT[hld_cfg_anio].copy()
        HLD_ANUAL_POR_ANIO[hld_cfg_anio][hld_cfg_centro] = txt_hld_valor_asig
        guardar_hld_anual_drive()
        st.success(f"✅ Total HLD actualizado a {txt_hld_valor_asig}h para {hld_cfg_centro} en el año {hld_cfg_anio}.")
