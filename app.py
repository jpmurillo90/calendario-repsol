"""Gestión de Técnicos CI — versión reorganizada.
Ejecutar: streamlit run app.py
Dependencias: streamlit>=1.40,<2, pandas, requests.
Mantener los JSON y AF_INDRA_SIM_POS.png junto a app.py.
Configurar [usuarios] en .streamlit/secrets.toml (sin usuarios por defecto).
Admite password para compatibilidad o password_hash PBKDF2 (ver verificar_password).
GITHUB_TOKEN y GIST_ID son opcionales. Con Gist configurado, es la fuente principal.
El registro exige datos remotos legibles; no se sobrescribe Gist tras un error de lectura.
Las escrituras comprueban cambios concurrentes, pero Gist no ofrece transacciones:
evitar ediciones simultáneas. Para múltiples editores concurrentes, migrar a una BD.
Los cálculos horarios originales se conservan: validar reglas con el responsable.
"""
import calendar
import json
import os
import hashlib
import hmac
import time
import tempfile
import copy
import io
import zipfile
from pathlib import Path
from html import escape
from datetime import datetime, date, timedelta
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Gestión de Técnicos CI", page_icon="📅", layout="wide")
ANOS_DISPONIBLES = [2026, 2027, 2028, 2029, 2030]

RUTA_BDD = "datos_tecnicos_repsol.json"

RUTA_FESTIVOS = "festivos_repsol.json"

RUTA_HE = "he_repsol.json"

RUTA_CONFIG_ANUAL = "config_anual_repsol.json"

RUTA_HORARIOS_CI = "horarios_ci_repsol.json"

RUTA_HLD_ANUAL = "hld_anual_repsol.json"

RUTA_PRL = "prl_repsol.json"

PRL_DEFAULT = {
    'Juan Pedro Murillo Huete': {'nip': '709355', 'dni': '05933159X', 'fecha': '2027-03-27', 'obs': 'BIENAL'},
    'David Muñoz Burguillo': {'nip': '709743', 'dni': '70052109C', 'fecha': '2027-03-28', 'obs': 'BIENAL'},
    'Fernando Bocija Sanchez': {'nip': '565127', 'dni': '53162879N', 'fecha': '2028-04-21', 'obs': 'BIENAL'},
    'Oscar Luna Murillo': {'nip': '722573', 'dni': '47950833L', 'fecha': '2027-08-28', 'obs': 'BIENAL'},
    'Joan Vila Cascan': {'nip': '710090', 'dni': '39922718P', 'fecha': '2027-04-02', 'obs': 'BIENAL'},
    'Endika Ramirez Rodriguez': {'nip': '723603', 'dni': '79136742K', 'fecha': '2026-10-22', 'obs': ''},
    'David Rodriguez Novua': {'nip': '709717', 'dni': '45818446P', 'fecha': '2027-03-27', 'obs': ''},
    'Simon Alberto Conesa Lloris': {'nip': '716271', 'dni': '23034801W', 'fecha': '2028-06-19', 'obs': 'BIENAL'},
    'Alejandro Gutierrez Bastida': {'nip': '717260', 'dni': '23310758M', 'fecha': '2026-10-10', 'obs': 'CITA 11 PETICION 4591420 CITACION RM - SE PREGUNTA POR TEAMS'}
}

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

# -------------------- Presentación y autenticación --------------------
st.markdown('''<style>
.stApp {background:#f5f7fa;color:#172b3a;}
.block-container {padding-top:2rem;max-width:1600px;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e2e8f0;}
h1,h2,h3 {letter-spacing:-.025em;color:#12313d;}
[data-testid="stMetric"] {background:white;padding:18px;border:1px solid #e5ebf0;border-radius:12px;}
button[kind="primary"] {background:#07566a;border-color:#07566a;color:white;}
.ci-card {background:white;border:1px solid #e5ebf0;border-radius:14px;padding:20px;margin:8px 0 18px;min-height:150px;}
.ci-card h3 {margin:0 0 12px;font-size:19px;}
.subtle {color:#607584;font-size:14px;}
.grid-wrap {overflow:auto;border:1px solid #dee6ec;border-radius:12px;background:white;}
.grid {border-collapse:separate;border-spacing:0;width:100%;font-size:13px;white-space:nowrap;}
.grid th {background:#123b49;color:white;padding:12px 9px;position:sticky;top:0;}
.grid td {border-bottom:1px solid #edf1f4;padding:12px 9px;text-align:center;min-width:42px;}
.grid .name {position:sticky;left:0;text-align:left;background:white;min-width:200px;z-index:1;}
.grid th.name {background:#123b49;z-index:2;}
.today {box-shadow:inset 0 0 0 2px #087c94;}
.tag {display:inline-block;padding:4px 9px;border-radius:6px;margin:4px;font-size:12px;color:#172b3a;}
</style>''', unsafe_allow_html=True)

BASE = Path(__file__).resolve().parent

def secreto(nombre, defecto=None):
    try:
        return st.secrets.get(nombre, defecto)
    except (FileNotFoundError, KeyError):
        return defecto

def verificar_password(password, usuario):
    """Hash: pbkdf2_sha256$600000$sal_hex$hash_hex; o password legado en secrets."""
    encoded = usuario.get('password_hash', '')
    if encoded:
        try:
            algoritmo, rondas, sal, esperado = encoded.split('$')
            if algoritmo != 'pbkdf2_sha256' or not 100000 <= int(rondas) <= 2000000:
                return False
            calculado = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(sal), int(rondas)).hex()
            return hmac.compare_digest(calculado, esperado)
        except (ValueError, TypeError):
            return False
    return bool(usuario.get('password')) and hmac.compare_digest(password.encode(), str(usuario['password']).encode())

usuarios = secreto('usuarios', {})
if not st.session_state.get('autenticado'):
    st.title('Gestión de Técnicos CI')
    st.caption('Planificación del equipo · Infraestructuras y Sistemas')
    if not usuarios:
        st.warning('Configura los usuarios en .streamlit/secrets.toml. Se han eliminado las contraseñas de respaldo del código.')
        st.code('[usuarios.coordinador]\nnombre = "Coordinador"\nrol = "Editor"\npassword = "SUSTITUIR_POR_UNA_CLAVE_LARGA_Y_UNICA"', language='toml')
        st.stop()
    _, centro_login, _ = st.columns([1, 2, 1])
    with centro_login:
        with st.form('login'):
            user = st.text_input('Usuario')
            password = st.text_input('Contraseña', type='password')
            entrar = st.form_submit_button('Entrar', type='primary', use_container_width=True)
        if entrar:
            if time.time() < st.session_state.get('bloqueado_hasta', 0):
                st.error('Espera un minuto antes de volver a intentarlo.')
            elif user in usuarios and verificar_password(password, usuarios[user]):
                st.session_state.update(autenticado=True, usuario_actual=usuarios[user].get('nombre', user),
                                        rol_actual=usuarios[user].get('rol', 'Lector'), usuario_id=user, intentos=0)
                st.rerun()
            else:
                st.session_state.intentos = st.session_state.get('intentos', 0) + 1
                if st.session_state.intentos >= 5:
                    st.session_state.bloqueado_hasta = time.time() + 60
                    st.session_state.intentos = 0
                st.error('Credenciales no válidas.')
    st.stop()

EDITOR = st.session_state.rol_actual == 'Editor'
# El límite de intentos es por sesión; el despliegue debe restringirse a la organización.

# -------------------- Persistencia compatible y verificable --------------------
ARCHIVOS = [RUTA_BDD, RUTA_FESTIVOS, RUTA_HE, RUTA_CONFIG_ANUAL,
            RUTA_HORARIOS_CI, RUTA_HLD_ANUAL, RUTA_PRL, 'auditoria_repsol.json']
TOKEN, GIST = secreto('GITHUB_TOKEN', ''), secreto('GIST_ID', '')
REMOTE = bool(TOKEN and GIST)
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json'}
URL = f'https://api.github.com/gists/{GIST}'
SNAPSHOTS = {}

def descargar_remoto():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    files = response.json()['files']
    if any(files.get(n, {}).get('truncated') for n in ARCHIVOS):
        raise ValueError('Un archivo remoto supera el límite de contenido de Gist.')
    return files

if bool(TOKEN) != bool(GIST):
    st.error('Configuración incompleta: GITHUB_TOKEN y GIST_ID deben configurarse juntos.')
    st.stop()
REMOTE_FILES = {}
if REMOTE:
    try:
        REMOTE_FILES = descargar_remoto()
    except (requests.RequestException, ValueError, KeyError):
        st.error('No se han podido leer los datos remotos. Por seguridad, la aplicación no permitirá editar hasta recuperar la conexión.')
        st.stop()

def cargar_json(nombre, defecto):
    try:
        if REMOTE and nombre in REMOTE_FILES:
            raw = REMOTE_FILES[nombre]['content']
        else:
            path = BASE / nombre
            raw = path.read_text(encoding='utf-8') if path.exists() else None
        SNAPSHOTS[nombre] = REMOTE_FILES.get(nombre, {}).get('content') if REMOTE else raw
        return json.loads(raw) if raw is not None else copy.deepcopy(defecto)
    except (ValueError, OSError, KeyError):
        st.error(f'No se puede leer {nombre}. Restaura una copia válida antes de continuar.')
        st.stop()

def escribir_local(nombre, contenido):
    temporal = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=BASE, encoding='utf-8', delete=False) as f:
            temporal = f.name
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, BASE / nombre)
    finally:
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)

def json_text(datos):
    return json.dumps(datos, ensure_ascii=False, indent=2, default=lambda x: x.isoformat() if isinstance(x, date) else str(x))

def guardar_cambios(cambios, accion):
    if not EDITOR:
        st.error('La edición está reservada al rol Editor.')
        return False
    evento = {'fecha': datetime.now().isoformat(timespec='seconds'),
              'usuario': st.session_state.usuario_actual, 'accion': accion}
    cambios = dict(cambios)
    cambios['auditoria_repsol.json'] = AUDITORIA + [evento]
    textos = {n: json_text(d) for n, d in cambios.items()}
    try:
        actuales = descargar_remoto() if REMOTE else {}
        for n in cambios:
            actual = actuales.get(n, {}).get('content') if REMOTE else ((BASE/n).read_text(encoding='utf-8') if (BASE/n).exists() else None)
            if actual != SNAPSHOTS.get(n):
                st.error('Los datos han cambiado desde que abriste la pantalla. Recarga y revisa antes de guardar.')
                return False
        if REMOTE:
            response = requests.patch(URL, headers=HEADERS, json={'files': {n: {'content': t} for n, t in textos.items()}}, timeout=15)
            response.raise_for_status()
        for n, contenido in textos.items():
            try:
                escribir_local(n, contenido)
            except OSError:
                if not REMOTE:
                    raise
                st.session_state.aviso_local = 'Guardado remoto correcto, pero no se pudo actualizar la copia local.'
        st.session_state.guardado = 'Sincronizado con el almacenamiento remoto.' if REMOTE else 'Guardado localmente. No hay sincronización remota configurada.'
        return True
    except (requests.RequestException, OSError, ValueError, KeyError):
        st.error('No se pudo confirmar el guardado. Recarga para comprobar el estado antes de reintentar. En modo local, una escritura múltiple puede quedar parcialmente aplicada.')
        return False

def normalizar_registros(datos):
    result = {}
    for k, val in datos.items():
        parts = k.split('|') if isinstance(k, str) else list(k)
        if len(parts) == 3:
            parts = [2026] + parts
        a, t, m, d = parts
        result[(int(a), t, str(int(m)), str(int(d)))] = val
    return result

REGISTROS = normalizar_registros(cargar_json(RUTA_BDD, {}))
REGISTROS_HE = cargar_json(RUTA_HE, {})
REGISTROS_PRL = cargar_json(RUTA_PRL, PRL_DEFAULT)
AUDITORIA = cargar_json('auditoria_repsol.json', [])
FESTIVOS_POR_ANIO = {int(a): {c: [tuple(x) for x in v] for c,v in cs.items()} for a,cs in cargar_json(RUTA_FESTIVOS, FESTIVOS_POR_ANIO_DEFAULT).items()}
CONFIG_ANUAL_POR_ANIO = {int(a): v for a,v in cargar_json(RUTA_CONFIG_ANUAL, CONFIG_ANUAL_DEFAULT).items()}
HORARIOS_CI_ANUAL = {int(a): cs for a,cs in cargar_json(RUTA_HORARIOS_CI, HORARIOS_CI_DEFAULT).items()}
for cs in HORARIOS_CI_ANUAL.values():
    for v in cs.values():
        for field in ['bolsa_ini', 'bolsa_fin']:
            if isinstance(v.get(field), str) and v[field]:
                v[field] = date.fromisoformat(v[field])
HLD_ANUAL_POR_ANIO = {int(a): cs for a,cs in cargar_json(RUTA_HLD_ANUAL, HLD_ANUAL_DEFAULT).items()}

def serializar_registros(datos):
    return {'|'.join(map(str, k)): v for k,v in datos.items()}

def valor_registro(tecnico, fecha, registros=None):
    return (REGISTROS if registros is None else registros).get((fecha.year, tecnico, str(fecha.month), str(fecha.day)), '')

def tipo_registro(valor):
    return valor.get('tipo', '') if isinstance(valor, dict) else valor

def consumo(tecnico, fecha, valor):
    tipo = tipo_registro(valor)
    v = valor if isinstance(valor, dict) else {}
    jornada = obtener_horas_jornada_real(tecnico, fecha.year, fecha.month, fecha.day)
    return {'V': int(tipo == 'V'), 'VPA': int(tipo == 'VPA'),
            'HE': float(v.get('he_horas', 0)) if tipo == 'HE+HLD' else float(v.get('horas_gastadas', jornada)) if tipo == 'HE' else 0,
            'HLD': float(v.get('hld_horas', 0)) if tipo == 'HE+HLD' else float(v.get('horas_gastadas', jornada)) if tipo == 'HLD' else 0}

def saldos(tecnico, anio, registros=None):
    total = {'V': 0, 'VPA': 0, 'HE': 0., 'HLD': 0.}
    for (a,t,m,d), val in (REGISTROS if registros is None else registros).items():
        if a == anio and t == tecnico:
            gasto = consumo(t, date(a,int(m),int(d)), val)
            for k in total:
                total[k] += gasto[k]
    asignado = {'V': TECNICOS[tecnico]['vac_totales'], 'VPA': obtener_vpa_totales_tecnico(tecnico, anio),
                'HE': calcular_he_compensadas_totales(tecnico, anio), 'HLD': obtener_hld_totales_tecnico(tecnico, anio)}
    return total, {k: round(asignado[k]-total[k], 2) for k in total}

def calcular_he_consumidas_horas(tecnico, anio):
    return saldos(tecnico, anio)[0]['HE']

def estado_prl(tecnico):
    valor = REGISTROS_PRL.get(tecnico, {}).get('fecha')
    try:
        fecha = date.fromisoformat(valor)
    except (ValueError, TypeError):
        return 'Sin información', None, None
    dias = (fecha-date.today()).days
    estado = 'Caducado' if dias < 0 else 'Próximo (<30 días)' if dias < 30 else 'Próximo (<60 días)' if dias < 60 else 'Vigente'
    return estado, fecha, dias

def disponibilidad(tecnico, fecha):
    jornada = obtener_horas_jornada_real(tecnico, fecha.year, fecha.month, fecha.day)
    if jornada <= 0:
        return 'No laborable', 0.
    val = valor_registro(tecnico, fecha)
    tipo = tipo_registro(val)
    if not tipo:
        return 'Disponible', jornada
    if tipo in ('HE', 'HLD', 'HE+HLD'):
        gasto = consumo(tecnico, fecha, val)
        resto = max(0., jornada-gasto['HE']-gasto['HLD'])
        return ('Parcial' if resto else 'Ausente'), resto
    return ('Formación' if tipo == 'CF' else 'Ausente'), 0.

CENTROS = sorted({v['ci'] for v in TECNICOS.values()})
logo = BASE/'AF_INDRA_SIM_POS.png'
if logo.exists():
    st.sidebar.image(str(logo), use_container_width=True)
st.sidebar.title('Técnicos CI')
pagina = st.sidebar.radio('Navegación', ['Inicio', 'Cuadrante', 'Técnicos', 'Horas extra', 'Informes', 'Configuración'])
dd_anio = st.sidebar.selectbox('Año', ANOS_DISPONIBLES, index=ANOS_DISPONIBLES.index(date.today().year) if date.today().year in ANOS_DISPONIBLES else 0)
centro = st.sidebar.selectbox('Centro', ['Todos'] + CENTROS)
visibles = [t for t,v in TECNICOS.items() if centro == 'Todos' or v['ci'] == centro]
st.sidebar.divider()
st.sidebar.caption(f'{st.session_state.usuario_actual} · {st.session_state.rol_actual}')
st.sidebar.caption('Datos remotos conectados' if REMOTE else 'Almacenamiento local')
if st.sidebar.button('Cerrar sesión', use_container_width=True):
    st.session_state.clear()
    st.rerun()
if 'guardado' in st.session_state:
    st.success(st.session_state.pop('guardado'))
if 'aviso_local' in st.session_state:
    st.warning(st.session_state.pop('aviso_local'))
st.title(pagina)
st.caption(f'Gestión de Técnicos CI · {centro} · {dd_anio}')

def tabla(datos):
    if datos:
        st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True)
    else:
        st.info('No hay registros para esta selección.')

def aviso_prl_visual(tecnico):
    estado, fecha, dias = estado_prl(tecnico)
    if dias is None:
        return 3, 'neutral', 'SIN INFORMACIÓN', 'Completar la fecha del reconocimiento.'
    if dias < 0:
        return 0, 'danger', f'CADUCADO HACE {abs(dias)} DÍAS', 'Revisar la situación y gestionar la renovación.'
    if dias < 30:
        return 1, 'danger', 'CADUCA HOY' if dias == 0 else f'CADUCA EN {dias} DÍAS', 'Gestionar la cita del reconocimiento.'
    if dias < 60:
        return 2, 'warning', f'CADUCA EN {dias} DÍAS', 'Planificar la renovación.'
    return 4, 'success', 'VIGENTE', 'Sin actuaciones próximas.'

def render_inicio():
    st.markdown('''<style>
    .home-box {--accent:#64748b;--surface:#f1f5f9;--ink:#334155;
      background:var(--surface);color:var(--ink);border:1px solid #dbe3ea;
      border-top:5px solid var(--accent);border-radius:12px;padding:18px;margin:8px 0 16px;}
    .home-box.success,.home-badge.success {--accent:#15803d;--surface:#f0fdf4;--ink:#166534;}
    .home-box.warning,.home-badge.warning {--accent:#b45309;--surface:#fffbeb;--ink:#92400e;}
    .home-box.danger,.home-badge.danger {--accent:#b91c1c;--surface:#fef2f2;--ink:#991b1b;}
    .home-box.info,.home-badge.info {--accent:#0369a1;--surface:#eff6ff;--ink:#075985;}
    .home-box.neutral,.home-badge.neutral {--accent:#64748b;--surface:#f1f5f9;--ink:#334155;}
    .home-value {font-size:34px;font-weight:800;line-height:1.2;margin:8px 0;}
    .home-label {font-weight:700;font-size:14px;}
    .home-note {font-size:13px;margin-top:8px;}
    .home-badge {display:inline-block;border-radius:6px;padding:5px 9px;
      background:var(--surface);color:var(--ink);border:1px solid var(--accent);
      font-size:12px;font-weight:700;margin:4px 4px 4px 0;}
    .home-person {padding:12px 0;border-top:1px solid #dbe3ea;margin-top:12px;}
    .home-person strong {display:block;color:#172b3a;margin-bottom:4px;}
    .home-box h3 {margin:0 0 8px;font-size:19px;color:var(--ink);}
    </style>''', unsafe_allow_html=True)
    fecha = st.date_input('Fecha de planificación', value=date.today())
    if fecha.year not in ANOS_DISPONIBLES:
        st.warning('Selecciona una fecha de los años configurados.'); return
    estados = {t: disponibilidad(t, fecha) for t in visibles}
    centros = sorted({TECNICOS[t]['ci'] for t in visibles})
    sin_cobertura = [c for c in centros if any(obtener_horas_jornada_real(t,fecha.year,fecha.month,fecha.day)>0 for t in visibles if TECNICOS[t]['ci']==c) and not any(estados[t][1]>0 for t in visibles if TECNICOS[t]['ci']==c)]
    avisos = [t for t in visibles if estado_prl(t)[0] != 'Vigente']
    caducados = sum(estado_prl(t)[0]=='Caducado' for t in visibles)
    proximos = sum(estado_prl(t)[2] is not None and 0 <= estado_prl(t)[2] < 60 for t in visibles)
    faltan = sum(estado_prl(t)[2] is None for t in visibles)
    ausentes = [t for t,(e,h) in estados.items() if e in ('Ausente','Formación','Parcial')]
    indicadores = [
        ('Disponibles / parciales',sum(h>0 for _,h in estados.values()),'success' if any(h>0 for _,h in estados.values()) else 'neutral','Personas con horas previstas disponibles'),
        ('Ausencias / parciales',len(ausentes),'warning' if ausentes else 'success','Incluye permisos parciales y formación'),
        ('Centros sin cobertura',len(sin_cobertura),'danger' if sin_cobertura else 'success','Requieren revisión de la planificación' if sin_cobertura else 'Sin centros laborables totalmente descubiertos'),
        ('PRL por revisar',len(avisos),'danger' if caducados else 'warning' if proximos else 'neutral' if faltan else 'success',f'{caducados} caducados · {proximos} próximos · {faltan} sin datos')]
    for col,(label,value,color,nota) in zip(st.columns(4),indicadores):
        col.markdown(f'<div class="home-box {color}"><div class="home-label">{label}</div><div class="home-value">{value}</div><div class="home-note">{nota}</div></div>',unsafe_allow_html=True)
    st.caption('Disponibilidad prevista, no fichajes. PRL se evalúa a fecha de hoy. Cobertura alerta cuando un centro laborable queda sin personal disponible; no hay mínimos de dotación configurados.')
    if sin_cobertura:
        st.error('SIN COBERTURA PREVISTA: '+', '.join(sin_cobertura)+'. Revisa la asignación de personal.')
    st.subheader('Situación por centro')
    for i in range(0,len(centros),3):
        for col,c in zip(st.columns(3),centros[i:i+3]):
            miembros = [t for t in visibles if TECNICOS[t]['ci']==c]
            no_laborable = all(estados[t][0]=='No laborable' for t in miembros)
            hay_ausencias = any(t in ausentes for t in miembros)
            color,etiqueta = ('neutral','NO LABORABLE') if no_laborable else ('danger','SIN COBERTURA') if c in sin_cobertura else ('warning','COBERTURA CON AUSENCIAS') if hay_ausencias else ('success','EQUIPO DISPONIBLE')
            detalle = ''
            for t in miembros:
                estado,horas = estados[t]
                tipo = tipo_registro(valor_registro(t,fecha))
                motivo = LEYENDA.get(tipo,(tipo,''))[0] if tipo else estado
                tono = 'neutral' if estado=='No laborable' else 'warning' if estado in ('Ausente','Parcial') else 'info' if estado=='Formación' else 'success'
                if estado=='No laborable': motivo = 'No laborable' + (f' · {motivo}' if tipo else '')
                detalle += f'<div class="home-person"><strong>{escape(t)}</strong><span class="home-badge {tono}">{escape(motivo)}</span><div class="home-note">{horas:g} h disponibles previstas' + (' · Ausencia parcial' if estado=='Parcial' else '') + '</div></div>'
            col.markdown(f'<div class="home-box {color}"><h3>{escape(c)}</h3><span class="home-badge {color}">{etiqueta}</span>{detalle}</div>',unsafe_allow_html=True)
    st.subheader('Reconocimientos PRL · acciones pendientes')
    st.caption(f'Estado a fecha de hoy ({date.today():%d/%m/%Y}), independiente de la fecha de planificación seleccionada.')
    ordenados = sorted(avisos,key=lambda t:(aviso_prl_visual(t)[0],estado_prl(t)[2] if estado_prl(t)[2] is not None else 99999,t))
    if not ordenados:
        st.success('Todos los reconocimientos del equipo seleccionado están vigentes y no vencen en los próximos 60 días.')
    for i in range(0,len(ordenados),2):
        for col,t in zip(st.columns(2),ordenados[i:i+2]):
            _,color,titular,accion = aviso_prl_visual(t)
            cad = estado_prl(t)[1]
            fecha_txt = cad.strftime('%d/%m/%Y') if cad else 'Sin fecha registrada'
            col.markdown(f'<div class="home-box {color}"><span class="home-badge {color}">{escape(titular)}</span><h3>{escape(t)}</h3><div>{escape(TECNICOS[t]["ci"])} · {fecha_txt}</div><div class="home-note">{escape(accion)}</div></div>',unsafe_allow_html=True)
    if ordenados:
        st.caption('Actualiza fechas y observaciones desde Técnicos → Editar datos de acceso.')

def cuadrante_html(tecnicos, mes, anio):
    dias = range(1,calendar.monthrange(anio,mes)[1]+1)
    texto = '<div class="grid-wrap"><table class="grid"><thead><tr><th class="name">Técnico / centro</th>'
    for d in dias:
        texto += f'<th>{d}<br>{["L","M","X","J","V","S","D"][date(anio,mes,d).weekday()]}</th>'
    texto += '</tr></thead><tbody>'
    for t in tecnicos:
        texto += f'<tr><td class="name">{escape(t)}<br><span class="subtle">{escape(TECNICOS[t]["ci"])}</span></td>'
        for d in dias:
            fecha = date(anio,mes,d)
            val = valor_registro(t,fecha)
            tipo = tipo_registro(val)
            if not tipo:
                tipo = 'FEST' if (mes,d) in FESTIVOS_POR_ANIO.get(anio,{}).get(TECNICOS[t]['ci'],[]) else 'SAB' if fecha.weekday()==5 else 'DOM' if fecha.weekday()==6 else ''
            color = LEYENDA.get(tipo,('', '#fff'))[1]
            desc = LEYENDA.get(tipo,('Sin marca',''))[0]
            gasto = consumo(t,fecha,val)
            detalle = f' · HE {gasto["HE"]:g} h / HLD {gasto["HLD"]:g} h' if tipo in ('HE','HLD','HE+HLD') else ''
            clase = 'today' if fecha==date.today() else ''
            texto += f'<td class="{clase}" style="background:{color}" title="{escape(desc+detalle,quote=True)}">{escape(tipo or "·")}</td>'
        texto += '</tr>'
    return texto+'</tbody></table></div>'

def registrar_ausencia():
    st.subheader('Registrar ausencia o permiso')
    t = st.selectbox('Técnico',visibles,key='aus_tec')
    cols = st.columns(2)
    minimo,maximo = date(dd_anio,1,1),date(dd_anio,12,31)
    defecto = date.today() if date.today().year==dd_anio else minimo
    ini = cols[0].date_input('Desde',defecto,min_value=minimo,max_value=maximo,key=f'ini_{dd_anio}')
    fin = cols[1].date_input('Hasta',ini,min_value=minimo,max_value=maximo,key=f'fin_{dd_anio}_{ini}')
    tipo = st.selectbox('Tipo', [k for k in LEYENDA if k not in ('FEST','SAB','DOM')]+['BORRAR'],format_func=lambda k: LEYENDA[k][0] if k in LEYENDA else 'Eliminar marcas del rango')
    solo_laborables = st.checkbox('Solo días laborables según el calendario del centro',value=True)
    he,hld = 0.,0.
    if tipo in ('HE','HE+HLD'):
        he = st.number_input('Horas HE por día',min_value=0.,max_value=24.,value=1.,step=.5)
    if tipo in ('HLD','HE+HLD'):
        hld = st.number_input('Horas HLD por día',min_value=0.,max_value=24.,value=1.,step=.5)
    if fin < ini:
        st.error('La fecha final no puede ser anterior a la inicial.'); return
    fechas = [ini+timedelta(days=i) for i in range((fin-ini).days+1)]
    if solo_laborables:
        fechas = [f for f in fechas if obtener_horas_jornada_real(t,f.year,f.month,f.day)>0]
    if not fechas:
        st.info('No hay días aplicables en el rango.'); return
    propuesta = copy.deepcopy(REGISTROS)
    existentes, conflictos = [], []
    for f in fechas:
        key = (f.year,t,str(f.month),str(f.day))
        if propuesta.get(key): existentes.append(f)
        jornada = obtener_horas_jornada_real(t,f.year,f.month,f.day)
        if tipo in ('HE','HLD','HE+HLD') and (he+hld<=0 or he+hld>jornada):
            st.error(f'{f:%d/%m/%Y}: las horas deben ser positivas y no superar la jornada ({jornada:g} h).'); return
        if tipo=='BORRAR': propuesta.pop(key,None)
        elif tipo=='HE+HLD': propuesta[key]={'tipo':tipo,'he_horas':he,'hld_horas':hld,'anio':f.year,'tec':t}
        elif tipo in ('HE','HLD'): propuesta[key]={'tipo':tipo,'horas_gastadas':he if tipo=='HE' else hld,'anio':f.year,'tec':t}
        else: propuesta[key]=tipo
        if tipo!='BORRAR':
            for otro in visibles_del_centro(t):
                if otro!=t and valor_registro(otro,f): conflictos.append({'Fecha':str(f),'Técnico':otro,'Marca':tipo_registro(valor_registro(otro,f))})
    _,antes = saldos(t,dd_anio)
    _,despues = saldos(t,dd_anio,propuesta)
    st.caption(f'{len(fechas)} días afectados. Se sustituyen {len(existentes)} registros existentes; no se duplican consumos.')
    tabla([{'Bolsa':k,'Unidad':'días' if k in ('V','VPA') else 'horas','Disponible':antes[k],'Consumo neto':round(antes[k]-despues[k],2),'Saldo resultante':despues[k]} for k in antes])
    excede = any(despues[k]<0 and despues[k]<antes[k] for k in antes)
    if excede: st.error('El cambio supera el saldo disponible.')
    if conflictos:
        st.warning('Hay otras marcas en el mismo centro. Revisa si afectan a la cobertura.'); tabla(conflictos)
    firma = hashlib.sha256(repr((t,ini,fin,tipo,he,hld,solo_laborables)).encode()).hexdigest()[:16]
    confirmado = st.checkbox('He revisado el consumo, las sustituciones y los solapamientos.',key=f'confirmar_{firma}')
    if st.button('Confirmar registro',type='primary',disabled=not confirmado or excede):
        accion = f'{t}: {tipo}, {ini} a {fin}, {len(fechas)} días; solapamientos: {len(conflictos)}'
        if guardar_cambios({RUTA_BDD:serializar_registros(propuesta)},accion): st.rerun()

def visibles_del_centro(t):
    return [n for n,v in TECNICOS.items() if v['ci']==TECNICOS[t]['ci']]

def informe_mensual_html(equipo, mes, anio):
    """Informe autónomo y filtrado. No exporta DNI, NIP ni observaciones PRL."""
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    hoy = date.today()
    centros = sorted({TECNICOS[t]['ci'] for t in equipo})
    filas_aus, filas_cob, filas_prl, filas_saldos = [], [], [], []
    dias_vac = 0
    horas_parciales = 0.
    for t in equipo:
        for d in range(1, fin.day+1):
            f = date(anio, mes, d)
            val = valor_registro(t, f)
            tipo = tipo_registro(val)
            if not tipo:
                continue
            gasto = consumo(t, f, val)
            dias_vac += gasto['V'] + gasto['VPA']
            horas_parciales += gasto['HE'] + gasto['HLD']
            detalle = f"HE: {gasto['HE']:g} h · HLD: {gasto['HLD']:g} h" if tipo in ('HE', 'HLD', 'HE+HLD') else 'Marca de día'
            filas_aus.append({'Fecha':f.strftime('%d/%m/%Y'),'Técnico':t,'Centro':TECNICOS[t]['ci'],
                             'Planificación':LEYENDA.get(tipo,(tipo,''))[0],'Detalle':detalle})
        estado, cad, dias = estado_prl(t)
        # Incluye vencimientos próximos a hoy y los que afectan al mes elegido.
        if cad is None or cad <= max(fin, hoy+timedelta(days=60)):
            if cad is None:
                etiqueta, accion = 'Sin información', 'Completar fecha de reconocimiento'
            elif cad < hoy:
                etiqueta, accion = f'Caducado hace {abs(dias)} días', 'Revisar renovación'
            elif cad == hoy:
                etiqueta, accion = 'Caduca hoy', 'Gestionar renovación'
            else:
                etiqueta = f'Caduca en {dias} días'
                accion = 'Gestionar cita' if dias < 30 else 'Planificar renovación'
            relacion = 'Sin fecha' if cad is None else 'Vence antes del mes' if cad < inicio else 'Vence en el mes' if cad <= fin else 'Vence después del mes'
            filas_prl.append({'Técnico':t,'Centro':TECNICOS[t]['ci'],'Caducidad':cad.strftime('%d/%m/%Y') if cad else 'Sin datos',
                              'Estado a fecha de emisión':etiqueta,'Relación con el mes':relacion,'Acción':accion,
                              '_orden':(0 if cad and cad < hoy else 1 if cad else 2, cad or date.max)})
        _, pendientes = saldos(t, anio)
        filas_saldos.append({'Técnico':t,'Vacaciones (días)':pendientes['V'],'VPA (días)':pendientes['VPA'],
                             'HLD (h)':pendientes['HLD'],'HE (h)':pendientes['HE']})
    # Nunca deducir cobertura de un centro solo a partir de una selección parcial.
    centros_completos = [c for c in centros if all(t in equipo for t,v in TECNICOS.items() if v['ci']==c)]
    centros_parciales = [c for c in centros if c not in centros_completos]
    for c in centros_completos:
        miembros = [t for t in equipo if TECNICOS[t]['ci']==c]
        for d in range(1, fin.day+1):
            f = date(anio, mes, d)
            laborable = any(obtener_horas_jornada_real(t,anio,mes,d)>0 for t in miembros)
            disponibles = [t for t in miembros if disponibilidad(t,f)[1]>0]
            if laborable and not disponibles:
                filas_cob.append({'Fecha':f.strftime('%d/%m/%Y'),'Centro':c,'Situación':'Sin personal disponible previsto',
                                  'Técnicos':', '.join(miembros)})
    filas_prl.sort(key=lambda x:x['_orden'])
    for fila in filas_prl: fila.pop('_orden')
    def tabla_html(filas, vacio):
        if not filas:
            return f'<p class="empty">{escape(vacio)}</p>'
        return '<div class="scroll">'+pd.DataFrame(filas).to_html(index=False,escape=True,border=0)+'</div>'
    css = '''body{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f9;color:#18313e;margin:0;padding:28px}
    main{max-width:1500px;margin:auto;background:white;padding:30px;border-radius:14px}
    h1{margin:8px 0;font-size:28px}h2{font-size:20px;margin-top:32px;border-bottom:2px solid #e2e8f0;padding-bottom:10px}
    .muted{color:#536977;font-size:13px}.metrics{display:flex;gap:14px;flex-wrap:wrap;margin:24px 0}
    .metric{flex:1;min-width:150px;border-radius:10px;padding:16px;background:#edf6f8;border-top:4px solid #07566a}
    .metric strong{display:block;font-size:28px;margin-top:6px}.warn{background:#fff7e6;border-color:#b45309}.danger{background:#fef2f2;border-color:#b91c1c}
    table{border-collapse:collapse;width:100%;font-size:12px}th{background:#123b49;color:white;text-align:left;padding:10px}
    td{border-bottom:1px solid #e2e8f0;padding:9px}tbody tr:nth-child(even){background:#f8fafc}
    .scroll,.grid-wrap{overflow-x:auto}.grid{white-space:nowrap;font-size:10px}.grid td,.grid th{padding:7px 5px;text-align:center}
    .grid .name{text-align:left;min-width:165px}.subtle{font-size:10px;color:#536977}
    .legend span{display:inline-block;padding:5px 9px;margin:4px;border-radius:5px;font-size:11px}
    .empty{background:#f0f7f4;padding:13px;border-radius:8px}.notice{padding:12px;border-left:4px solid #b45309;background:#fffbeb}
    footer{margin-top:32px;border-top:1px solid #ddd;padding-top:12px;font-size:12px;color:#536977}
    @page{size:A4 landscape;margin:10mm}@media print{body{padding:0;background:white}main{padding:0;max-width:none}
    th,td,.metric,.legend span{-webkit-print-color-adjust:exact;print-color-adjust:exact}thead{display:table-header-group}
    tr,.metric{break-inside:avoid}h2{break-after:avoid}.scroll,.grid-wrap{overflow:visible}.grid{font-size:8px}.grid td,.grid th{padding:4px 2px}.grid .name{min-width:110px}}
    '''
    prl_caducados = sum(estado_prl(t)[0]=='Caducado' for t in equipo)
    resumen = [('Técnicos incluidos',len(equipo),''),('Vacaciones / VPA · días-persona',dias_vac,''),
               ('Días-centro sin cobertura',len(filas_cob),'danger' if filas_cob else ''),
               ('PRL por revisar',len(filas_prl),'danger' if prl_caducados else 'warn' if filas_prl else '')]
    tarjetas = ''.join(f'<div class="metric {clase}">{escape(label)}<strong>{valor}</strong></div>' for label,valor,clase in resumen)
    leyenda = ''.join(f'<span style="background:{color}">{escape(k)} · {escape(desc)}</span>' for k,(desc,color) in LEYENDA.items())
    nota_cob = '<p class="notice">Cobertura no evaluada en '+escape(', '.join(centros_parciales))+': el filtro no incluye a todo el centro.</p>' if centros_parciales else ''
    festivos = [{'Centro':c,'Fecha':date(anio,mes,d).strftime('%d/%m/%Y')} for c in centros for m,d in FESTIVOS_POR_ANIO.get(anio,{}).get(c,[]) if m==mes]
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Planificación CI · {MESES[mes]} {anio}</title><style>{css}</style></head><body><main>'
            f'<div class="muted">INDRA · INFRAESTRUCTURAS Y SISTEMAS · CI</div><h1>Planificación de {MESES[mes].lower()} {anio}</h1>'
            f'<p>Centros: {escape(", ".join(centros))} · {len(equipo)} técnicos incluidos</p>'
            f'<p class="muted">Emitido el {datetime.now():%d/%m/%Y %H:%M}. Fotografía de los registros en el momento de la descarga.</p>'
            f'<div class="metrics">{tarjetas}</div><p class="muted">Vacaciones: suma de días registrados por persona. HE/HLD planificadas en el mes: {horas_parciales:g} h. Disponibilidad prevista, no presencia confirmada.</p>'
            '<h2>1. Cuadrante mensual</h2>'+cuadrante_html(equipo,mes,anio)+f'<div class="legend">{leyenda}</div>'
            '<h2>2. Cobertura que requiere revisión</h2>'+nota_cob+tabla_html(filas_cob,'No se detectan días laborables sin cobertura en los centros evaluados.')+
            '<p class="muted">Se alerta si no queda ninguna persona con horas disponibles. No se validan mínimos de dotación ni solapamientos horarios de permisos parciales.</p>'
            '<h2>3. Reconocimientos PRL por revisar</h2>'+
            f'<p class="muted">Estado calculado a {hoy:%d/%m/%Y}. Incluye fechas desconocidas y caducidades hasta {max(fin,hoy+timedelta(days=60)):%d/%m/%Y}: fin del mes o próximos 60 días desde la emisión, lo que sea posterior.</p>'+
            tabla_html(filas_prl,'No hay reconocimientos pendientes de revisión en el horizonte indicado.')+
            '<h2>4. Detalle de ausencias, permisos y formación</h2>'+tabla_html(filas_aus,'No hay marcas registradas para este mes.')+
            '<h2>5. Saldos anuales disponibles</h2><p class="muted">Descuentan todos los registros del año, incluidos los de meses posteriores. No son saldos al cierre del mes.</p>'+
            tabla_html(filas_saldos,'Sin técnicos seleccionados.')+
            '<h2>6. Festivos del mes</h2>'+tabla_html(festivos,'No hay festivos configurados para el mes y los centros seleccionados.')+
            '<footer>Uso interno · Gestión de Técnicos CI · Juan Pedro Murillo Huete. No incluye DNI, NIP ni observaciones de reconocimientos.</footer></main></body></html>')

def render_cuadrante():
    cols = st.columns([1,1,2])
    mes = cols[0].selectbox('Mes',list(MESES),index=date.today().month-1,format_func=MESES.get)
    vista = cols[1].radio('Vista',['Equipo','Individual'],horizontal=True)
    seleccion = cols[2].selectbox('Técnico', ['Todos']+visibles if vista=='Equipo' else visibles)
    equipo = visibles if seleccion=='Todos' else [seleccion]
    contenido = cuadrante_html(equipo,mes,dd_anio)
    st.markdown(contenido,unsafe_allow_html=True)
    with st.expander('Leyenda de estados'):
        st.markdown(''.join(f'<span class="tag" style="background:{color}">{escape(k)} · {escape(desc)}</span>' for k,(desc,color) in LEYENDA.items()),unsafe_allow_html=True)
    export = informe_mensual_html(equipo,mes,dd_anio)
    st.download_button('Descargar informe mensual · HTML',export,file_name=f'informe_ci_{dd_anio}_{mes:02d}.html',mime='text/html')
    st.caption('Incluye cuadrante, cobertura, PRL, ausencias, saldos y festivos. Respeta los filtros de centro y técnico seleccionados.')
    if EDITOR:
        with st.expander('＋ Registrar ausencia / permiso',expanded=False): registrar_ausencia()
    else: st.caption('Modo consulta: no puedes modificar registros.')

def render_tecnicos():
    t = st.selectbox('Buscar técnico',visibles)
    st.subheader(t)
    st.caption(TECNICOS[t]['ci'])
    usados,pendientes = saldos(t,dd_anio)
    for col,k in zip(st.columns(4),['V','VPA','HLD','HE']):
        unidad = 'días' if k in ('V','VPA') else 'h'
        col.metric(f'{k} disponibles',f'{pendientes[k]:g} {unidad}')
        col.caption(f'Consumidos: {usados[k]:g} {unidad}')
    estado,f,d = estado_prl(t)
    st.subheader('Reconocimiento y acceso CI')
    st.write(f'Estado: **{estado}** · Caducidad: **{f or "Sin información"}**')
    datos = REGISTROS_PRL.get(t,{})
    if EDITOR:
        with st.expander('Editar datos de acceso'):
            with st.form(f'prl_{t}'):
                nip = st.text_input('NIP',value=datos.get('nip',''))
                dni = st.text_input('DNI',value=datos.get('dni',''))
                cad = st.date_input('Caducidad',value=f or date.today())
                obs = st.text_input('Observaciones',value=datos.get('obs',''))
                sin_fecha = st.checkbox('Fecha desconocida',value=f is None)
                guardar = st.form_submit_button('Guardar reconocimiento',type='primary')
            if guardar:
                nuevo = copy.deepcopy(REGISTROS_PRL)
                nuevo[t]={'nip':nip,'dni':dni,'fecha':None if sin_fecha else cad.isoformat(),'obs':obs}
                if guardar_cambios({RUTA_PRL:nuevo},f'Actualización PRL: {t}'): st.rerun()
    eventos = []
    for (a,n,m,dia),val in REGISTROS.items():
        if n==t and a==dd_anio:
            fecha = date(a,int(m),int(dia))
            eventos.append({'Fecha':fecha,'Tipo':LEYENDA.get(tipo_registro(val),(tipo_registro(val),''))[0]})
    st.subheader('Próximas ausencias / permisos')
    tabla(sorted([x for x in eventos if x['Fecha']>=date.today()],key=lambda x:x['Fecha']))
    with st.expander('Histórico del año'): tabla(sorted(eventos,key=lambda x:x['Fecha'],reverse=True))

def render_he():
    t = st.selectbox('Técnico',visibles)
    _,pendientes = saldos(t,dd_anio)
    st.metric('Horas disponibles',f'{pendientes["HE"]:g} h')
    st.caption('Se conserva el factor original: 1 hora realizada = 1,75 horas compensadas.')
    if EDITOR:
        with st.expander('＋ Registrar horas extra'):
            with st.form('he'):
                h = st.number_input('Horas reales (negativas para correcciones)',min_value=-100.,max_value=100.,value=1.,step=.5)
                motivo = st.text_input('Motivo obligatorio')
                guardar = st.form_submit_button('Guardar horas',type='primary')
            if guardar:
                if not motivo.strip() or h==0: st.error('Introduce un motivo y un número de horas distinto de cero.')
                elif pendientes['HE']+h*1.75<0: st.error('La corrección dejaría el saldo de HE negativo.')
                else:
                    nuevo = copy.deepcopy(REGISTROS_HE)
                    nuevo.setdefault(t,[]).append({'anio':dd_anio,'horas_reales':h,'motivo':motivo,'usuario':st.session_state.usuario_actual,'fecha':datetime.now().strftime('%d/%m/%Y %H:%M')})
                    if guardar_cambios({RUTA_HE:nuevo},f'HE: {t}, {h:g} horas reales'): st.rerun()
    filas = [{'ID':i,**v} for i,v in enumerate(REGISTROS_HE.get(t,[])) if v['anio']==dd_anio]
    tabla(filas)
    if EDITOR and filas:
        with st.expander('Eliminar registro erróneo'):
            idx = st.selectbox('Registro',[x['ID'] for x in filas],format_func=lambda i:f'{i} · {REGISTROS_HE[t][i].get("fecha","")} · {REGISTROS_HE[t][i]["horas_reales"]} h')
            confirmar = st.checkbox('Confirmar eliminación',key=f'borrar_he_{t}_{idx}')
            if st.button('Eliminar',disabled=not confirmar):
                nuevo = copy.deepcopy(REGISTROS_HE)
                retirado = nuevo[t].pop(idx)
                if pendientes['HE']-retirado['horas_reales']*1.75<0: st.error('La eliminación dejaría horas ya consumidas sin saldo.')
                elif guardar_cambios({RUTA_HE:nuevo},f'Eliminar HE: {t}, ID {idx}'): st.rerun()

def render_informes():
    opcion = st.radio('Informe',['Balance','PRL','Solapamientos','Auditoría'],horizontal=True)
    filas = []
    if opcion=='Balance':
        for t in visibles:
            usados,pendientes = saldos(t,dd_anio)
            fila = {'Técnico':t,'Centro':TECNICOS[t]['ci']}
            for k in usados:
                unidad = 'días' if k in ('V','VPA') else 'h'
                fila[f'{k} consumido ({unidad})']=usados[k]
                fila[f'{k} pendiente ({unidad})']=pendientes[k]
            filas.append(fila)
    elif opcion=='PRL':
        filas = [{'Técnico':t,'Centro':TECNICOS[t]['ci'],'Estado':estado_prl(t)[0],'Caducidad':estado_prl(t)[1]} for t in visibles]
    elif opcion=='Solapamientos':
        por_dia = {}
        for (a,t,m,d),v in REGISTROS.items():
            if a==dd_anio and t in visibles and tipo_registro(v):
                por_dia.setdefault((date(a,int(m),int(d)),TECNICOS[t]['ci']),[]).append(t)
        filas = [{'Fecha':f,'Centro':c,'Técnicos':', '.join(ts)} for (f,c),ts in sorted(por_dia.items()) if len(ts)>1]
        st.caption('Coincidencia de marcas, no necesariamente ausencia completa. Revisar cobertura antes de actuar.')
    else:
        if not EDITOR: st.info('Auditoría reservada a editores.'); return
        filas = [x for x in reversed(AUDITORIA) if x.get('fecha','').startswith(str(dd_anio))]
        st.caption('Auditoría global del año, sin filtro de centro. Persistida desde esta versión; el histórico de sesiones anteriores no estaba guardado.')
    tabla(filas)
    if filas:
        df = pd.DataFrame(filas)
        # Evitar fórmulas al abrir CSV en hojas de cálculo.
        seguro = df.map(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) if hasattr(df,'map') else df.applymap(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v)
        st.download_button('Descargar CSV',seguro.to_csv(index=False,sep=';').encode('utf-8-sig'),file_name=f'{opcion}_{dd_anio}.csv',mime='text/csv')

def render_config():
    if not EDITOR:
        st.info('Configuración reservada a editores.'); return
    opcion = st.radio('Ajustes',['Festivos','Horarios','HLD','Copias de seguridad'],horizontal=True)
    if opcion=='Copias de seguridad':
        datos = {RUTA_BDD:serializar_registros(REGISTROS),RUTA_HE:REGISTROS_HE,RUTA_PRL:REGISTROS_PRL,RUTA_FESTIVOS:FESTIVOS_POR_ANIO,RUTA_CONFIG_ANUAL:CONFIG_ANUAL_POR_ANIO,RUTA_HORARIOS_CI:HORARIOS_CI_ANUAL,RUTA_HLD_ANUAL:HLD_ANUAL_POR_ANIO,'auditoria_repsol.json':AUDITORIA}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for n,v in datos.items(): z.writestr(n,json_text(v))
        st.download_button('Descargar copia completa de los datos',buf.getvalue(),file_name=f'backup_ci_{date.today()}.zip',mime='application/zip')
        st.caption('Incluye todos los centros y años, no credenciales. Contiene datos personales: consérvala en un lugar restringido.')
        return
    c = st.selectbox('Centro a configurar',CENTROS,index=CENTROS.index(centro) if centro in CENTROS else 0)
    if opcion=='Festivos':
        actuales = FESTIVOS_POR_ANIO.get(dd_anio,{}).get(c,[])
        tabla([{'Fecha':date(dd_anio,m,d)} for m,d in actuales])
        f = st.date_input('Fecha',date(dd_anio,1,1),min_value=date(dd_anio,1,1),max_value=date(dd_anio,12,31))
        accion = st.radio('Operación',['Añadir','Eliminar'],horizontal=True)
        ok = st.checkbox('Confirmar eliminación') if accion=='Eliminar' else True
        if st.button('Guardar festivo',type='primary',disabled=not ok):
            nuevo = copy.deepcopy(FESTIVOS_POR_ANIO)
            dias = nuevo.setdefault(dd_anio,{}).setdefault(c,[])
            par = (f.month,f.day)
            if accion=='Añadir' and par not in dias: dias.append(par); dias.sort()
            elif accion=='Eliminar' and par in dias: dias.remove(par)
            else: st.info('No hay cambios que guardar.'); return
            if guardar_cambios({RUTA_FESTIVOS:nuevo},f'{accion} festivo: {c}, {f}'): st.rerun()
    elif opcion=='Horarios':
        actual = HORARIOS_CI_ANUAL.get(dd_anio,HORARIOS_CI_DEFAULT[dd_anio]).get(c,{})
        st.info('La descripción del horario es informativa. Se mantienen las reglas originales de cálculo de jornada; cambiar el texto no modifica esas reglas. La bolsa de parada sí afecta al cálculo.')
        with st.form(f'horario_{c}_{dd_anio}'):
            horario = st.text_input('Horario',actual.get('horario',''))
            semanal = st.text_input('Horas semanales (texto)',actual.get('h_sem',''))
            obs = st.text_input('Observaciones',actual.get('obs',''))
            bolsa = st.checkbox('Activar bolsa de parada (+2 h de lunes a jueves)',value=bool(actual.get('bolsa_ini')))
            ini = st.date_input('Inicio',actual.get('bolsa_ini') or date(dd_anio,9,28))
            fin = st.date_input('Fin',actual.get('bolsa_fin') or date(dd_anio,11,2))
            guardar = st.form_submit_button('Guardar horario',type='primary')
        if guardar:
            if bolsa and (fin<ini or ini.year!=dd_anio or fin.year!=dd_anio): st.error('Revisa el rango y el año de la bolsa.'); return
            nuevo = copy.deepcopy(HORARIOS_CI_ANUAL)
            nuevo.setdefault(dd_anio,{})[c]={'horario':horario,'h_sem':semanal,'obs':obs,'bolsa_ini':ini if bolsa else None,'bolsa_fin':fin if bolsa else None}
            if guardar_cambios({RUTA_HORARIOS_CI:nuevo},f'Horario: {c}, {dd_anio}'): st.rerun()
    else:
        valor = float(HLD_ANUAL_POR_ANIO.get(dd_anio,{}).get(c,87.))
        with st.form(f'hld_{c}_{dd_anio}'):
            horas = st.number_input('Horas HLD anuales',min_value=0.,max_value=1000.,value=valor,step=.5)
            guardar = st.form_submit_button('Guardar HLD',type='primary')
        if guardar:
            nuevo = copy.deepcopy(HLD_ANUAL_POR_ANIO)
            nuevo.setdefault(dd_anio,{})[c]=horas
            if guardar_cambios({RUTA_HLD_ANUAL:nuevo},f'HLD: {c}, {dd_anio}, {horas:g} h'): st.rerun()

{'Inicio':render_inicio,'Cuadrante':render_cuadrante,'Técnicos':render_tecnicos,
 'Horas extra':render_he,'Informes':render_informes,'Configuración':render_config}[pagina]()
st.divider()
st.caption('Gestión de Técnicos CI · Juan Pedro Murillo Huete · Indra / RPECII')

