# ==============================================================================
# SISTEMA INTEGRAL DE GESTIÓN DE CALENDARIOS REPSOL (HASTA 2030 + CONFIG ANUAL CI + HLD) - STREAMLIT EDITION
# ==============================================================================

Python
import calendar
import json
from datetime import datetime, date
import pandas as pd
import streamlit as st
import requests

# ==========================================
# CONFIGURACIÓN Y CONSTANTES
# ==========================================
RUTA_BDD = "datos_tecnicos_repsol.json"

# ==========================================
# FUNCIONES DE PERSISTENCIA (GITHUB GIST)
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
    # Guardamos localmente como respaldo y también en el Gist
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
    url = obtener_url_gist()
    headers = obtener_cabeceras_gist()
    
    if url and headers:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                files = response.json().get("files", {})
                if "datos_tecnicos_repsol.json" in files:
                    contenido = files["datos_tecnicos_repsol.json"]["content"]
                    datos_json = json.loads(contenido)
                    resultado = {}
                    for k, v in datos_json.items():
                        parts = k.split('|')
                        if len(parts) == 3:
                            resultado[(2026, parts[0], parts[1], parts[2])] = v
                        else:
                            resultado[(int(parts[0]), parts[1], parts[2], parts[3])] = v
                    return resultado
        except Exception:
            pass
            
    # Si falla o no hay secretos configurados, lee del archivo local
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

def guardar_config_anual_drive():
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

CONFIG_ANUAL_DEFAULT = {
    anio: {
        'petronor_lj': 8.50, 'petronor_v': 5.50,
        'cartagena_ini': date(anio, 10, 1), 'cartagena_fin': date(anio, 11, 5),
        'tarragona_ini': date(anio, 9, 28), 'tarragona_fin': date(anio, 11, 2)
    } for anio in ANOS_DISPONIBLES
}

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
CONFIG_ANUAL_POR_ANIO = cargar_config_anual_drive() or CONFIG_ANUAL_DEFAULT
HORARIOS_CI_ANUAL = cargar_horarios_ci_drive() or HORARIOS_CI_DEFAULT
HLD_ANUAL_POR_ANIO = cargar_hld_anual_drive() or HLD_ANUAL_DEFAULT

REGISTROS = cargar_de_drive()
REGISTROS_HE = cargar_he_drive()

# Inicializar historial de auditoría en session_state
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

# 2. CÁLCULOS Y HORARIOS
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
        if isinstance(val, dict) and val.get('anio') == anio and val.get('tec') == tecnico and val.get('tipo') == 'HE':
            total_consumido_h += val.get('horas_gastadas', 0.0)
        else:
            parts = key.split('|') if isinstance(key, str) else None
            if parts and len(parts) == 4:
                a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                if a == anio and t == tecnico and val == 'HE':
                    total_consumido_h += obtener_horas_jornada_real(tecnico, anio, m, d)
            elif isinstance(key, tuple) and len(key) == 4:
                a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                if a == anio and t == tecnico and val == 'HE':
                    total_consumido_h += obtener_horas_jornada_real(tecnico, anio, m, d)
    return round(total_consumido_h, 2)

def verificar_coincidencias(tecnico_actual, mes, dia, tipo_marca, anio):
    if tipo_marca == '': return []
    ci_actual = TECNICOS[tecnico_actual]['ci']
    coincidencias = []
    for key, val in REGISTROS.items():
        parts = key.split('|') if isinstance(key, str) else None
        if parts and len(parts) == 4:
            a, tec, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
        elif isinstance(key, tuple) and len(key) == 4:
            a, tec, m, d = key[0], key[1], int(key[2]), int(key[3])
        else:
            continue

        marca_str = val['tipo'] if isinstance(val, dict) else val
        if a == anio and tec != tecnico_actual and m == int(mes) and d == int(dia):
            if TECNICOS[tec]['ci'] == ci_actual and marca_str != '':
                desc_marca = LEYENDA.get(marca_str, (marca_str, ''))[0]
                coincidencias.append((tec, marca_str, desc_marca))
    return coincidencias

# Interfaz Principal de Streamlit
st.markdown("<h2 style='color:#005B7F; margin:0;'>Cuadrante de Calendarios Técnicos - SAT CI REPSOL</h2>", unsafe_allow_html=True)

# Controles Superiores Globales
col_v1, col_v2, col_v3 = st.columns([1.5, 1, 1])
with col_v1:
    dd_vista = st.selectbox('Modo Vista:', ['Calendario Individual', 'Matriz Cuadrante Global (Equipo)'])
with col_v2:
    dd_anio = st.selectbox('Año:', ANOS_DISPONIBLES)
with col_v3:
    # Botón exportar HTML detallado
    if st.button('📥 Descargar HTML Detallado'):
        fecha_actual_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        html_leyenda = "<div style='background-color: #F8F9FA; border: 1px solid #DCDCDC; border-radius: 6px; padding: 12px; margin-top: 20px; margin-bottom: 25px; font-family: sans-serif;'><h4 style='margin: 0 0 8px 0; color: #002A3A; font-size: 14px;'>📖 Leyenda de Códigos y Estados</h4><div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
        for k, (desc, color) in LEYENDA.items():
            html_leyenda += f"<div style='display: flex; align-items: center; background: white; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; font-size: 11px;'><span style='background-color: {color}; border: 1px solid #999; width: 14px; height: 14px; display: inline-block; margin-right: 6px; border-radius: 2px;'></span><b>{k}:</b>&nbsp;{desc}</div>"
        html_leyenda += "</div></div>"
        
        datos_resumen = []
        for tec, info in TECNICOS.items():
            hld_tot_t = obtener_hld_totales_tecnico(tec, dd_anio)
            vpa_tot_t = obtener_vpa_totales_tecnico(tec, dd_anio)
            vac_c = 0
            vpa_c = 0
            hld_c = 0.0
            for key, val in REGISTROS.items():
                parts = key.split('|') if isinstance(key, str) else None
                if parts and len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                elif isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    continue
                if a == dd_anio and t == tec:
                    marca_str = val['tipo'] if isinstance(val, dict) else val
                    if marca_str == 'V': vac_c += 1
                    elif marca_str == 'VPA': vpa_c += 1
                    elif marca_str == 'HLD':
                        hld_c += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, dd_anio)) if isinstance(val, dict) else obtener_horas_hld(tec, m, d, dd_anio)
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
                t_html += f"<th>{d}<br><span style='font-size:9px; color:#ccc;'>{dias_semana_abrev[weekday]}</span></th>"
            t_html += "</tr></thead><tbody>"
            for tec, info in TECNICOS.items():
                t_html += f"<tr><td><b>{tec}</b></td><td>{info['ci']}</td>"
                festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(info['ci'], [])
                for d in range(1, num_dias + 1):
                    val_reg = REGISTROS.get((dd_anio, tec, str(mes_num), str(d)), REGISTROS.get(f"{dd_anio}|{tec}|{mes_num}|{d}", ''))
                    marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
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
                    t_html += f"<td style='background-color: {bg_color}; text-align: center;'><b>{marca}</b></td>"
                t_html += "</tr>"
            t_html += "</tbody></table>"
            secciones_meses_html += f"<div class='mes-container'><h3>📅 Mes: {mes_nom} {dd_anio}</h3><div class='table-responsive'>{t_html}</div></div>"
        
        html_template = f"<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'><title>Calendario SAT CI Repsol - {dd_anio}</title><style>body{{font-family:'Segoe UI',sans-serif;background-color:#F4F6F8;color:#333;margin:0;padding:20px;}}.container{{max-width:1400px;margin:auto;background:white;padding:30px;border-radius:8px;}}h1{{color:#002A3A;border-bottom:3px solid #005B7F;padding-bottom:10px;font-size:22px;}}table.tabla-corporativa{{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px;text-align:left;white-space:nowrap;}}table.tabla-corporativa th{{background-color:#002A3A;color:white;padding:8px;text-align:center;}}table.tabla-corporativa td{{padding:6px;border:1px solid #ddd;}}</style></head><body><div class='container'><h1>Calendario SAT CI Repsol - {dd_anio}</h1><div class='fecha-generacion'>Fecha de generación: <b>{fecha_actual_str}</b></div>{html_leyenda}<h2>📈 Balance Consolidado de Saldos</h2>{tabla_res_html}<h2>🗓️ Detalle de Cuadrantes por Meses</h2>{secciones_meses_html}</div></body></html>"
        st.download_button(label="📥 Descargar archivo HTML generado", data=html_template, file_name=f"Calendario_SAT_CI_Repsol_{dd_anio}.html", mime="text/html")

# Pestañas principales de Streamlit
tab_registrar, tab_he, tab_cobertura, tab_balance, tab_incidencias, tab_auditoria, tab_config, tab_horarios, tab_hld = st.tabs([
    '🛠️ Registrar', '⚡ Horas Extra', '👥 Cobertura', '📈 Balance', '⚠️ Incidencias', '📋 Auditoría', '⚙️ Configuración', '⏰ Horarios / CI', '⏳ Config. HLD'
])

# --- 1. SECCIÓN REGISTRAR ---
with tab_registrar:
    st.markdown("### 📝 Registro de Calendarios y Ausencias")
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
        reg_tipo_tupla = st.selectbox('Marca:', opciones_marca, key='reg_tipo')
        reg_tipo = reg_tipo_tupla[1]
    with c6:
        info_tec = TECNICOS[reg_tec]
        hld_tot_anio = obtener_hld_totales_tecnico(reg_tec, dd_anio)
        vpa_tot_anio = obtener_vpa_totales_tecnico(reg_tec, dd_anio)
        
        vac_c = sum(1 for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == reg_tec and (v['tipo'] if isinstance(v, dict) else v) == 'V')
        vpa_c = sum(1 for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == reg_tec and (v['tipo'] if isinstance(v, dict) else v) == 'VPA')
        hld_c = sum(v.get('horas_gastadas', 0.0) if isinstance(v, dict) else obtener_horas_hld(reg_tec, int(k[2] if isinstance(k, tuple) else k.split('|')[2]), int(k[3] if isinstance(k, tuple) else k.split('|')[3]), dd_anio) for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == reg_tec and (v['tipo'] if isinstance(v, dict) else v) == 'HLD')
        
        he_comp = calcular_he_compensadas_totales(reg_tec, dd_anio)
        he_gast = calcular_he_consumidas_horas(reg_tec, dd_anio)
        he_disp = round(he_comp - he_gast, 2)
        
        val_horas_disfrute = 0.0
        if reg_tipo == 'HE':
            val_horas_disfrute = st.slider('Horas a Gastar (HE):', 0.5, max(0.5, float(he_disp)), 0.5, step=0.5)
        elif reg_tipo == 'HLD':
            hld_max_d = obtener_horas_hld(reg_tec, reg_mes_num, reg_d_ini, dd_anio)
            val_horas_disfrute = st.slider('Horas a Gastar (HLD):', 0.5, max(0.5, float(hld_max_d if hld_max_d > 0 else 7.0)), 0.5, step=0.5)

    vac_pend = info_tec['vac_totales'] - vac_c
    vpa_pend = vpa_tot_anio - vpa_c
    hld_pend = hld_tot_anio - hld_c
    st.markdown(f"""
    <div style='background-color:#F2F4F7; border-left:4px solid #005B7F; padding:8px 12px; margin-bottom:10px; font-family:sans-serif; font-size:12px; display:flex; justify-content:space-between; flex-wrap:wrap;'>
        <div><b>👤 Técnico:</b> {reg_tec} ({dd_anio})</div>
        <div>🏖️ <b>Vac:</b> {vac_c}/{info_tec['vac_totales']} (<b>{vac_pend}</b>)</div>
        <div>⏱️ <b>VPA:</b> {vpa_c}/{vpa_tot_anio} (<b>{vpa_pend}</b>)</div>
        <div>⏳ <b>HLD:</b> {hld_c:.1f}h/{hld_tot_anio}h (<b>{hld_pend:.1f}h</b>)</div>
        <div>⚡ <b>HE Disp:</b> <b>{he_disp:.2f}h</b></div>
    </div>
    """, unsafe_allow_html=True)

    if st.button('Guardar Rango', type='primary'):
        if reg_d_ini > reg_d_fin:
            st.error("❌ Error: El día de inicio debe ser menor o igual al día fin.")
        else:
            coincidencias_totales = []
            for dia in range(reg_d_ini, reg_d_fin + 1):
                c = verificar_coincidencias(reg_tec, reg_mes_num, str(dia), reg_tipo, dd_anio)
                if c: coincidencias_totales.append((dia, c))
                
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
            if coincidencias_totales:
                st.warning("⚠️ ¡Existen coincidencias/solapamientos de ausencias en el mismo centro!")

    st.markdown(f"### 📅 Vista: {MESES[reg_mes_num]} {dd_anio}")
    if dd_vista == 'Calendario Individual':
        ci_tec = TECNICOS[reg_tec]['ci']
        cal = calendar.monthcalendar(dd_anio, reg_mes_num)
        festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(ci_tec, [])
        
        html_cal = f"<h4 style='color:#002A3A;'>Calendario de {reg_tec} ({ci_tec})</h4><table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; width:100%; font-size:12px;'>"
        html_cal += "<tr style='background-color:#002A3A; color:white;'><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th style='background-color:#7f7f7f;'>Sáb</th><th style='background-color:#7f7f7f;'>Dom</th></tr>"
        for semana in cal:
            html_cal += "<tr>"
            for idx, dia in enumerate(semana):
                if dia == 0:
                    html_cal += "<td style='background-color:#f2f2f2; height:50px;'></td>"
                else:
                    val_reg = REGISTROS.get((dd_anio, reg_tec, str(reg_mes_num), str(dia)), REGISTROS.get(f"{dd_anio}|{reg_tec}|{reg_mes_num}|{dia}", ''))
                    marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
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
                    html_cal += f"<td style='background-color:{bg_color}; height:50px;'><b>{dia}</b><br><span style='font-size:10px;'>{marca}</span></td>"
            html_cal += "</tr>"
        html_cal += "</table>"
        st.markdown(html_cal, unsafe_allow_html=True)
    else:
        num_dias = calendar.monthrange(dd_anio, reg_mes_num)[1]
        matriz_datos = []
        for tec, info in TECNICOS.items():
            fila = {'Técnico': tec, 'CI': info['ci']}
            festivos = FESTIVOS_POR_ANIO.get(dd_anio, {}).get(info['ci'], [])
            for d in range(1, num_dias + 1):
                val_reg = REGISTROS.get((dd_anio, tec, str(reg_mes_num), str(d)), REGISTROS.get(f"{dd_anio}|{tec}|{reg_mes_num}|{d}", ''))
                marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
                weekday = calendar.weekday(dd_anio, reg_mes_num, d)
                if (reg_mes_num, d) in festivos:
                    if not marca: marca = 'FEST'
                elif weekday >= 5 and not marca:
                    marca = 'SAB' if weekday == 5 else 'DOM'
                fila[f'{d}'] = marca if marca else ''
            matriz_datos.append(fila)
        st.dataframe(pd.DataFrame(matriz_datos), use_container_width=True)

# --- 2. SECCIÓN HORAS EXTRA ---
with tab_he:
    st.markdown("### ⚡ Gestión y Acumulación de Horas Extra")
    st.markdown("Añade las horas reales trabajadas. Se multiplicarán automáticamente por 1.75 (equivalente a 1h 45min).")
    he_anio = st.selectbox('Año HE:', ANOS_DISPONIBLES, key='he_anio_sel')
    he_tec = st.selectbox('Técnico HE:', list(TECNICOS.keys()), key='he_tec_sel')
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        txt_horas = st.number_input('Horas Reales:', min_value=0.5, value=1.0, step=0.5)
    with col_h2:
        txt_motivo = st.text_input('Motivo / Aviso:', placeholder='Ej. Urgencia en planta')
        
    if st.button('Registrar Horas Extra'):
        if he_tec not in REGISTROS_HE:
            REGISTROS_HE[he_tec] = []
        REGISTROS_HE[he_tec].append({'anio': he_anio, 'horas_reales': txt_horas, 'motivo': txt_motivo or 'Sin motivo'})
        guardar_he_drive()
        st.success(f"✅ Se han registrado {txt_horas}h extra reales a {he_tec} (Equivalen a {txt_horas * 1.75:.2f}h compensadas).")

    tot_r = sum(i['horas_reales'] for i in REGISTROS_HE.get(he_tec, []) if i['anio'] == he_anio)
    tot_c = calcular_he_compensadas_totales(he_tec, he_anio)
    tot_g = calcular_he_consumidas_horas(he_tec, he_anio)
    st.info(f"📊 **Resumen HE ({he_tec} - {he_anio}):** Reales: {tot_r}h | Compensadas (x1.75): {tot_c:.2f}h | Gastadas: {tot_g:.2f}h | **Disponibles: {tot_c - tot_g:.2f}h**")

# --- 3. SECCIÓN COBERTURA ---
with tab_cobertura:
    st.markdown("### 👥 Análisis de Cobertura Diaria")
    fecha_cob = st.date_input("Selecciona fecha de cobertura:", value=date(dd_anio, 8, 25))
    if fecha_cob:
        anio_c, mes_c, dia_c = fecha_cob.year, fecha_cob.month, fecha_cob.day
        detalles_cov = []
        total_trab = 0
        for tec, info in TECNICOS.items():
            ci = info['ci']
            val_reg = REGISTROS.get((anio_c, tec, str(mes_c), str(dia_c)), REGISTROS.get(f"{anio_c}|{tec}|{mes_c}|{dia_c}", ''))
            marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
            weekday = calendar.weekday(anio_c, mes_c, dia_c)
            festivos = FESTIVOS_POR_ANIO.get(anio_c, {}).get(ci, [])
            es_festivo = (mes_c, dia_c) in festivos or weekday >= 5
            
            if marca == '' and not es_festivo:
                estado = "TRABAJA"
                total_trab += 1
            else:
                estado = f"NO TRABAJA ({marca if marca else 'FEST/FINDE'})"
            detalles_cov.append({'CI': ci, 'Técnico': tec, 'Estado': estado})
        st.dataframe(pd.DataFrame(detalles_cov), use_container_width=True)
        st.metric(label="Disponibilidad Global de la Plantilla", value=f"{round((total_trab / len(TECNICOS)) * 100)}%")

# --- 4. SECCIÓN BALANCE ---
with tab_balance:
    st.markdown(f"### 📈 Balance Consolidado de Saldos - {dd_anio}")
    datos_bal = []
    for tec, info in TECNICOS.items():
        hld_tot = obtener_hld_totales_tecnico(tec, dd_anio)
        vpa_tot = obtener_vpa_totales_tecnico(tec, dd_anio)
        vac_c = sum(1 for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == tec and (v['tipo'] if isinstance(v, dict) else v) == 'V')
        vpa_c = sum(1 for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == tec and (v['tipo'] if isinstance(v, dict) else v) == 'VPA')
        hld_c = sum(v.get('horas_gastadas', 0.0) if isinstance(v, dict) else obtener_horas_hld(tec, int(k[2] if isinstance(k, tuple) else k.split('|')[2]), int(k[3] if isinstance(k, tuple) else k.split('|')[3]), dd_anio) for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == tec and (v['tipo'] if isinstance(v, dict) else v) == 'HLD')
        he_comp = calcular_he_compensadas_totales(tec, dd_anio)
        he_gast = calcular_he_consumidas_horas(tec, dd_anio)
        
        datos_bal.append({
            'Centro': info['ci'], 'Técnico': tec,
            'Vac. Cons.': vac_c, 'Vac. Pend.': info['vac_totales'] - vac_c,
            'VPA Cons.': vpa_c, 'VPA Pend.': vpa_tot - vpa_c,
            'HLD Cons.': round(hld_c, 2), 'HLD Pend.': round(hld_tot - hld_c, 2),
            'HE Comp.': he_comp, 'HE Disp.': round(he_comp - he_gast, 2)
        })
    st.dataframe(pd.DataFrame(datos_bal), use_container_width=True)

# --- 5. SECCIÓN INCIDENCIAS ---
with tab_incidencias:
    st.markdown(f"### ⚠️ Control de Excesos y Alertas ({dd_anio})")
    alertas = []
    for tec, info in TECNICOS.items():
        hld_tot = obtener_hld_totales_tecnico(tec, dd_anio)
        vpa_tot = obtener_vpa_totales_tecnico(tec, dd_anio)
        vac_c = sum(1 for k, v in REGISTROS.items() if (k[0] if isinstance(k, tuple) else int(k.split('|')[0])) == dd_anio and (k[1] if isinstance(k, tuple) else k.split('|')[1]) == tec and (v['tipo'] if isinstance(v, dict) else v) == 'V')
        if vac_c > info['vac_totales']:
            alertas.append(f"Exceso de Vacaciones: **{tec}** ha consumido {vac_c} de {info['vac_totales']}.")
    if alertas:
        for al in alertas: st.error(al)
    else:
        st.success("✅ Ningún técnico supera sus topes de saldo actuales.")

# --- 6. SECCIÓN AUDITORÍA ---
with tab_auditoria:
    st.markdown("### 📋 Historial de Cambios de la Sesión")
    if not st.session_state.historial_auditoria:
        st.info("No se han registrado modificaciones en esta sesión todavía.")
    else:
        st.dataframe(pd.DataFrame(st.session_state.historial_auditoria), use_container_width=True)

# --- 7. SECCIÓN CONFIGURACIÓN ---
with tab_config:
    st.markdown("### ⚙️ Configuración y Copias de Seguridad")
    
    st.markdown("#### 💾 Descargar Copia de Seguridad de Datos")
    st.markdown("Haz clic en el siguiente botón para descargar el archivo con todos los registros actuales de vacaciones y ausencias a tu dispositivo:")
    
    try:
        with open(RUTA_BDD, 'r', encoding='utf-8') as f:
            json_data_str = f.read()
    except FileNotFoundError:
        json_data_str = "{}"
        
    st.download_button(
        label="📥 Descargar archivo de datos (.json)",
        data=json_data_str,
        file_name="datos_tecnicos_repsol.json",
        mime="application/json"
    )
    
    st.markdown("---")
    st.markdown("### 📅 Configuración de Festivos por Centro")
    cfg_centro = st.selectbox('Centro CI:', list(set(i['ci'] for i in TECNICOS.values())), key='cfg_c')
    cfg_mes = st.selectbox('Mes Festivo:', list(MESES.keys()), format_func=lambda x: MESES[x], key='cfg_m')
    cfg_dia = st.selectbox('Día Festivo:', list(range(1, calendar.monthrange(dd_anio, cfg_mes)[1] + 1)), key='cfg_d')
    
    if st.button('Añadir Festivo'):
        if dd_anio not in FESTIVOS_POR_ANIO: FESTIVOS_POR_ANIO[dd_anio] = {}
        if cfg_centro not in FESTIVOS_POR_ANIO[dd_anio]: FESTIVOS_POR_ANIO[dd_anio][cfg_centro] = []
        if (cfg_mes, cfg_dia) not in FESTIVOS_POR_ANIO[dd_anio][cfg_centro]:
            FESTIVOS_POR_ANIO[dd_anio][cfg_centro].append((cfg_mes, cfg_dia))
            guardar_festivos_drive()
            st.success(f"✅ Festivo {cfg_dia}/{cfg_mes}/{dd_anio} añadido para {cfg_centro}.")

# --- 8. SECCIÓN HORARIOS / CI ---
with tab_horarios:
    st.markdown("### ⏰ Horarios Reales de Cliente por CI")
    horarios_anio = HORARIOS_CI_ANUAL.get(dd_anio, HORARIOS_CI_DEFAULT[dd_anio])
    h_data = [{'Centro': ci, 'Horario': d['horario'], 'H/Semana': d['h_sem'], 'Obs': d['obs']} for ci, d in horarios_anio.items()]
    st.dataframe(pd.DataFrame(h_data), use_container_width=True)

# --- 9. SECCIÓN CONFIG. HLD ---
with tab_hld:
    st.markdown("### ⏳ Configuración de HLD Totales por Centro y Año")
    hld_anio = HLD_ANUAL_POR_ANIO.get(dd_anio, HLD_ANUAL_DEFAULT[dd_anio])
    hld_data = [{'Centro': ci, 'Total HLD (h)': val} for ci, val in hld_anio.items()]
    st.dataframe(pd.DataFrame(hld_data), use_container_width=True)
