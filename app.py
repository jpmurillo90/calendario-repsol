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
import smtplib
import ssl
from email.message import EmailMessage
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
RUTA_GUARDIAS = "guardias_repsol.json"
RUTA_ACTIVACIONES = "activaciones_guardia_repsol.json"

RUTA_TECNICOS = "tecnicos_repsol.json"

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

def he_compensadas_registro(item):
    if 'horas_compensadas' in item:
        return float(item.get('horas_compensadas', 0) or 0)
    return float(item.get('horas_reales', 0) or 0) * 1.75

def calcular_he_compensadas_totales(tecnico, anio):
    lista_he = REGISTROS_HE.get(tecnico, [])
    return round(sum(he_compensadas_registro(item) for item in lista_he if item.get('anio') == anio), 2)

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
:root {--ci-primary:#07566a;--ci-primary-dark:#123b49;--ci-bg:#f4f7f9;--ci-card:#ffffff;--ci-border:#e2e8f0;--ci-text:#172b3a;--ci-muted:#647785;--ci-radius:14px;}
.stApp {background:linear-gradient(180deg,#f7f9fb 0,#f4f7f9 240px);color:var(--ci-text);}
.block-container {padding-top:1.55rem;padding-bottom:2.5rem;max-width:1600px;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid var(--ci-border);box-shadow:4px 0 18px rgba(15,43,56,.035);}
[data-testid="stSidebar"] [data-testid="stImage"] {padding:8px 4px 4px;}
[data-testid="stSidebar"] h1 {font-size:1.18rem!important;margin-bottom:.7rem;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.2rem;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:.45rem .55rem;border-radius:9px;transition:.15s ease;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#f1f6f8;}
h1,h2,h3 {letter-spacing:-.025em;color:#12313d;}
h1 {font-weight:750!important;font-size:2rem!important;margin-bottom:.1rem!important;}
h2 {font-size:1.35rem!important;margin-top:1.4rem!important;}
h3 {font-size:1.05rem!important;}
p, .stCaption {line-height:1.5;}
[data-testid="stCaptionContainer"] {color:var(--ci-muted);}
hr {border-color:#e7edf1!important;margin:1.3rem 0!important;}
[data-testid="stMetric"] {background:#fff;padding:17px 18px;border:1px solid var(--ci-border);border-radius:var(--ci-radius);box-shadow:0 5px 16px rgba(15,43,56,.045);}
[data-testid="stMetricLabel"] {color:#607584;font-weight:650;}
[data-testid="stMetricValue"] {color:#12313d;font-weight:750;letter-spacing:-.03em;}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button {border-radius:9px!important;min-height:2.55rem;font-weight:650;border-color:#d7e1e7;transition:.15s ease;}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"]>button:hover {border-color:#7ba5b0;box-shadow:0 3px 10px rgba(7,86,106,.09);}
button[kind="primary"] {background:var(--ci-primary)!important;border-color:var(--ci-primary)!important;color:white!important;box-shadow:0 4px 12px rgba(7,86,106,.16);}
button[kind="primary"]:hover {background:#064b5d!important;border-color:#064b5d!important;}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,[data-testid="stDateInput"]>div>div {border-radius:9px!important;border-color:#dbe4e9!important;background:#fff;}
[data-testid="stExpander"] {background:#fff;border:1px solid var(--ci-border)!important;border-radius:12px!important;box-shadow:0 3px 12px rgba(15,43,56,.025);overflow:hidden;}
[data-testid="stExpander"] summary {font-weight:650;color:#274654;}
[data-testid="stDataFrame"] {border:1px solid var(--ci-border);border-radius:12px;overflow:hidden;background:#fff;box-shadow:0 3px 12px rgba(15,43,56,.025);}
[data-testid="stAlert"] {border-radius:11px!important;border-width:1px!important;}
[role="radiogroup"] {gap:.25rem;}
[role="radiogroup"] label {font-weight:550;}
.ci-statusbar {display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:.7rem 0 1.15rem;padding:9px 12px;background:rgba(255,255,255,.82);border:1px solid #e3eaee;border-radius:11px;box-shadow:0 3px 12px rgba(15,43,56,.025);}
.ci-statusitem {display:inline-flex;align-items:center;gap:6px;color:#536b78;font-size:12px;font-weight:650;padding:3px 7px;}
.ci-dot {width:7px;height:7px;border-radius:50%;background:#15803d;box-shadow:0 0 0 3px #dcfce7;}
.ci-sep {width:1px;height:16px;background:#e1e8ec;}
.ci-card {background:white;border:1px solid var(--ci-border);border-radius:var(--ci-radius);padding:20px;margin:8px 0 18px;box-shadow:0 5px 16px rgba(15,43,56,.04);min-height:150px;}
.ci-card h3 {margin:0 0 12px;font-size:19px;}
.subtle {color:#607584;font-size:14px;}
.grid-wrap {overflow:auto;border:1px solid #dee6ec;border-radius:13px;background:white;box-shadow:0 4px 14px rgba(15,43,56,.035);}
.grid {border-collapse:separate;border-spacing:0;width:100%;font-size:13px;white-space:nowrap;}
.grid th {background:#123b49;color:white;padding:12px 9px;position:sticky;top:0;font-weight:650;}
.grid td {border-bottom:1px solid #edf1f4;padding:12px 9px;text-align:center;min-width:42px;}
.grid tbody tr:hover td {filter:brightness(.985);}
.grid .name {position:sticky;left:0;text-align:left;background:white;min-width:200px;z-index:1;font-weight:600;}
.grid th.name {background:#123b49;z-index:2;}
.today {box-shadow:inset 0 0 0 2px #087c94;}
.tag {display:inline-block;padding:5px 9px;border-radius:999px;margin:4px;font-size:11px;font-weight:650;color:#172b3a;border:1px solid rgba(23,43,58,.07);}
@media (max-width:900px){.block-container{padding-top:1rem}.ci-sep{display:none}.ci-statusbar{gap:3px}h1{font-size:1.65rem!important;}}
</style>''', unsafe_allow_html=True)

BASE = Path(__file__).resolve().parent

def secreto(nombre, defecto=None):
    try:
        return st.secrets.get(nombre, defecto)
    except (FileNotFoundError, KeyError):
        return defecto

def enviar_email(asunto, mensaje, destinatario=None):
    """Envía un correo mediante Gmail SMTP usando una contraseña de aplicación."""
    gmail_usuario = str(secreto("GMAIL_USUARIO", "")).strip()
    gmail_password = str(secreto("GMAIL_APP_PASSWORD", "")).replace(" ", "").strip()
    gmail_destino = str(destinatario or secreto("GMAIL_DESTINATARIO", "")).strip()

    if not gmail_usuario or not gmail_password or not gmail_destino:
        return False, "Falta configurar GMAIL_USUARIO, GMAIL_APP_PASSWORD o GMAIL_DESTINATARIO en los Secrets de Streamlit."

    email = EmailMessage()
    email["From"] = gmail_usuario
    email["To"] = gmail_destino
    email["Subject"] = asunto
    email.set_content(mensaje)

    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto, timeout=15) as servidor:
            servidor.login(gmail_usuario, gmail_password)
            servidor.send_message(email)
        return True, f"Correo enviado correctamente a {gmail_destino}."
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail ha rechazado la autenticación. Revisa la cuenta y la contraseña de aplicación configuradas en Secrets."
    except (smtplib.SMTPException, OSError) as e:
        return False, f"No se pudo enviar el correo: {e}"


def avisos_prl_actuales():
    """PRL que requieren atención ahora: sin fecha, caducados o con 60 días o menos."""
    hoy = date.today()
    avisos = []
    for tecnico in sorted(TECNICOS):
        datos = REGISTROS_PRL.get(tecnico, {}) or {}
        valor = datos.get('fecha')
        try:
            fecha = date.fromisoformat(valor)
        except (ValueError, TypeError):
            avisos.append({'tecnico': tecnico, 'centro': TECNICOS[tecnico]['ci'], 'fecha': None, 'dias': None, 'obs': datos.get('obs','')})
            continue
        dias = (fecha - hoy).days
        if dias <= 60:
            avisos.append({'tecnico': tecnico, 'centro': TECNICOS[tecnico]['ci'], 'fecha': fecha, 'dias': dias, 'obs': datos.get('obs','')})
    return sorted(avisos, key=lambda x: (999999 if x['dias'] is None else x['dias'], x['tecnico']))

def texto_estado_prl(dias):
    if dias is None:
        return 'SIN FECHA REGISTRADA'
    if dias < 0:
        return f'CADUCADO HACE {abs(dias)} DÍAS'
    if dias == 0:
        return 'CADUCA HOY'
    return f'CADUCA EN {dias} DÍAS'

def siguiente_aviso_prl(dias):
    """Describe el siguiente hito usado por el workflow automático 60/30/15/7."""
    if dias is None:
        return 'Sin aviso automático hasta registrar una fecha'
    if dias < 0:
        return 'Siguiente día laborable (caducado)'
    if dias <= 7:
        return 'Siguiente día laborable (aviso diario)'
    for hito in (60, 30, 15, 7):
        if dias > hito:
            faltan = dias - hito
            return f'En {faltan} día' + ('s' if faltan != 1 else '') + f' · hito {hito} días'
    return 'Siguiente día laborable'

def enviar_resumen_prl_manual():
    avisos = avisos_prl_actuales()
    if not avisos:
        return False, 'No hay reconocimientos PRL que requieran atención en los próximos 60 días.'

    lineas = [
        'GESTIÓN DE TÉCNICOS CI · AVISO PRL FORZADO',
        '',
        f'Fecha de revisión: {date.today():%d/%m/%Y}',
        f'Reconocimientos que requieren atención: {len(avisos)}',
        ''
    ]
    for aviso in avisos:
        lineas.append(aviso['tecnico'])
        lineas.append(f"Centro: {aviso['centro']}")
        lineas.append('Caducidad: ' + (aviso['fecha'].strftime('%d/%m/%Y') if aviso['fecha'] else 'Sin fecha registrada'))
        lineas.append('Estado: ' + texto_estado_prl(aviso['dias']))
        if aviso['dias'] is None or aviso['dias'] <= 30:
            lineas.append('Acción: Gestionar/revisar la cita del reconocimiento.')
        else:
            lineas.append('Acción: Planificar la renovación.')
        if aviso['obs']:
            lineas.append(f"Observaciones: {aviso['obs']}")
        lineas.append('')

    lineas.extend([
        'Próximos avisos automáticos: hitos de 60, 30 y 15 días; aviso diario desde 7 días y mientras permanezca caducado.',
        'La comprobación automática está programada de lunes a viernes mediante GitHub Actions.',
        '',
        'Gestión de Técnicos CI · Indra / RPECII'
    ])
    return enviar_email(
        f"⚠️ PRL · {len(avisos)} reconocimiento{'s' if len(avisos) != 1 else ''} requiere{'n' if len(avisos) != 1 else ''} revisión",
        '\n'.join(lineas)
    )

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
            RUTA_HORARIOS_CI, RUTA_HLD_ANUAL, RUTA_PRL, RUTA_TECNICOS, RUTA_GUARDIAS, RUTA_ACTIVACIONES, 'auditoria_repsol.json']
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

# Catálogo dinámico de técnicos. Si tecnicos_repsol.json todavía no existe,
# se usan exactamente los técnicos definidos en esta versión como migración inicial.
# Esto NO modifica los registros históricos: vacaciones, ausencias, HE/HLD y PRL
# continúan identificándose por el mismo nombre del técnico.
TECNICOS = cargar_json(RUTA_TECNICOS, TECNICOS)
for _nombre, _datos in TECNICOS.items():
    _datos.setdefault('activo', True)
    _datos.setdefault('vac_totales', 22)
    _datos.setdefault('vpa_base', 0)
    _datos.setdefault('he_totales', 0.0)

REGISTROS = normalizar_registros(cargar_json(RUTA_BDD, {}))
REGISTROS_HE = cargar_json(RUTA_HE, {})
REGISTROS_PRL = cargar_json(RUTA_PRL, PRL_DEFAULT)
REGISTROS_GUARDIAS = cargar_json(RUTA_GUARDIAS, [])
ACTIVACIONES_GUARDIA = cargar_json(RUTA_ACTIVACIONES, [])
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
pagina = st.sidebar.radio('Navegación', ['Inicio', 'Cuadrante', 'Guardias', 'Técnicos', 'Horas extra', 'Informes', 'Configuración'])
dd_anio = st.sidebar.selectbox('Año', ANOS_DISPONIBLES, index=ANOS_DISPONIBLES.index(date.today().year) if date.today().year in ANOS_DISPONIBLES else 0)
centro = st.sidebar.selectbox('Centro', ['Todos'] + CENTROS)
visibles = [t for t,v in TECNICOS.items() if v.get('activo', True) and (centro == 'Todos' or v['ci'] == centro)]
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
st.markdown(
    f'<div class="ci-statusbar">'
    f'<span class="ci-statusitem"><span class="ci-dot"></span>{"Datos remotos conectados" if REMOTE else "Almacenamiento local"}</span>'
    f'<span class="ci-sep"></span><span class="ci-statusitem">👥 {len(visibles)} técnico{"s" if len(visibles) != 1 else ""}</span>'
    f'<span class="ci-sep"></span><span class="ci-statusitem">📍 {escape(centro)}</span>'
    f'<span class="ci-sep"></span><span class="ci-statusitem">📅 {dd_anio}</span>'
    f'<span class="ci-sep"></span><span class="ci-statusitem">{escape(st.session_state.usuario_actual)} · {escape(st.session_state.rol_actual)}</span>'
    f'</div>', unsafe_allow_html=True)

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
      border-top:4px solid var(--accent);border-radius:14px;padding:18px 19px;margin:8px 0 16px;box-shadow:0 5px 16px rgba(15,43,56,.04);}
    .home-box.success,.home-badge.success {--accent:#15803d;--surface:#f0fdf4;--ink:#166534;}
    .home-box.warning,.home-badge.warning {--accent:#b45309;--surface:#fffbeb;--ink:#92400e;}
    .home-box.danger,.home-badge.danger {--accent:#b91c1c;--surface:#fef2f2;--ink:#991b1b;}
    .home-box.info,.home-badge.info {--accent:#0369a1;--surface:#eff6ff;--ink:#075985;}
    .home-box.neutral,.home-badge.neutral {--accent:#64748b;--surface:#f1f5f9;--ink:#334155;}
    .home-value {font-size:36px;font-weight:780;letter-spacing:-.04em;line-height:1.15;margin:9px 0 7px;}
    .home-label {font-weight:700;font-size:13px;letter-spacing:.01em;}
    .home-note {font-size:13px;margin-top:8px;}
    .home-badge {display:inline-block;border-radius:999px;padding:5px 10px;
      background:var(--surface);color:var(--ink);border:1px solid var(--accent);
      font-size:12px;font-weight:700;margin:4px 4px 4px 0;}
    .home-person {padding:12px 0;border-top:1px solid #dbe3ea;margin-top:12px;}
    .home-person strong {display:block;color:#172b3a;margin-bottom:4px;}
    .home-guard {margin:13px 0 4px;padding:11px 12px;border-radius:10px;background:#e8f4f7;border:1px solid #b9dce5;color:#123f4d;}
    .home-guard-title {font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#0b667c;margin-bottom:4px;}
    .home-guard strong {display:block;font-size:14px;color:#123f4d;margin-bottom:3px;}
    .home-guard-next {font-size:12px;color:#536b78;margin-top:5px;}
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
            # Guardia del CI para la fecha de planificación seleccionada.
            # Los registros contiguos/solapados del mismo técnico se tratan como un único periodo real.
            guardia_actual = []
            proximas_guardias = []
            for tg in [x for x,v in TECNICOS.items() if v.get('activo', True) and v.get('ci') == c]:
                for ini_g, fin_g in periodos_guardia_reales(REGISTROS_GUARDIAS, tecnico=tg):
                    if ini_g <= fecha <= fin_g:
                        guardia_actual.append((tg, ini_g, fin_g))
                    elif ini_g > fecha:
                        proximas_guardias.append((ini_g, fin_g, tg))
            guardia_actual.sort(key=lambda x: (x[1], x[0]))
            proximas_guardias.sort(key=lambda x: (x[0], x[2]))
            if guardia_actual:
                tg, ini_g, fin_g = guardia_actual[0]
                guardia_html = (
                    f'<div class="home-guard"><div class="home-guard-title">🛡️ Guardia actual</div>'
                    f'<strong>{escape(tg)}</strong><div>{ini_g:%d/%m/%Y} → {fin_g:%d/%m/%Y}</div>'
                )
                if proximas_guardias:
                    p_ini, p_fin, p_t = proximas_guardias[0]
                    guardia_html += f'<div class="home-guard-next">Próxima: <b>{escape(p_t)}</b> · {p_ini:%d/%m/%Y} → {p_fin:%d/%m/%Y}</div>'
                guardia_html += '</div>'
            else:
                guardia_html = '<div class="home-guard"><div class="home-guard-title">🛡️ Guardia actual</div><strong>Sin guardia asignada</strong>'
                if proximas_guardias:
                    p_ini, p_fin, p_t = proximas_guardias[0]
                    guardia_html += f'<div class="home-guard-next">Próxima: <b>{escape(p_t)}</b> · {p_ini:%d/%m/%Y} → {p_fin:%d/%m/%Y}</div>'
                guardia_html += '</div>'
            detalle = guardia_html
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

    if fin < ini:
        st.error('La fecha final no puede ser anterior a la inicial.'); return
    fechas = [ini+timedelta(days=i) for i in range((fin-ini).days+1)]
    if solo_laborables:
        fechas = [f for f in fechas if obtener_horas_jornada_real(t,f.year,f.month,f.day)>0]
    if not fechas:
        st.info('No hay días aplicables en el rango.'); return

    # HE/HLD: por defecto se registra la jornada completa REAL de cada fecha.
    # Esto permite que un rango respete automáticamente viernes, verano, bolsas, etc.
    he,hld = 0.,0.
    jornada_completa = False
    if tipo in ('HE','HLD'):
        jornada_completa = st.checkbox('Registrar jornada completa', value=True,
                                       help='Calcula automáticamente las horas máximas de cada día según la jornada configurada.')
        if not jornada_completa:
            jornada_ref = max(0.0, obtener_horas_jornada_real(t,ini.year,ini.month,ini.day))
            etiqueta = 'HE' if tipo=='HE' else 'HLD'
            valor_defecto = float(jornada_ref) if len(fechas)==1 and jornada_ref>0 else 1.0
            manual = st.number_input(f'Horas {etiqueta} por día',min_value=0.,max_value=24.,value=valor_defecto,step=.5)
            if tipo=='HE': he=manual
            else: hld=manual
    elif tipo=='HE+HLD':
        st.caption('Para combinar HE + HLD indica el reparto diario. La suma no puede superar la jornada real de cada fecha.')
        jornada_ref = max(0.0, obtener_horas_jornada_real(t,ini.year,ini.month,ini.day))
        he = st.number_input('Horas HE por día',min_value=0.,max_value=24.,value=0.,step=.5)
        hld_defecto = float(jornada_ref) if len(fechas)==1 and jornada_ref>0 else 1.0
        hld = st.number_input('Horas HLD por día',min_value=0.,max_value=24.,value=hld_defecto,step=.5)

    # Desglose previo: muestra exactamente qué se va a registrar cada día.
    desglose = []
    for f in fechas:
        jornada = float(obtener_horas_jornada_real(t,f.year,f.month,f.day))
        he_dia = jornada if tipo=='HE' and jornada_completa else he if tipo in ('HE','HE+HLD') else 0.0
        hld_dia = jornada if tipo=='HLD' and jornada_completa else hld if tipo in ('HLD','HE+HLD') else 0.0
        desglose.append({'fecha':f,'jornada':jornada,'he':float(he_dia),'hld':float(hld_dia)})

    if tipo in ('HE','HLD','HE+HLD'):
        st.markdown('#### Desglose del periodo')
        filas_desglose=[]
        dias_semana=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
        for x in desglose:
            consumo_dia=x['he']+x['hld']
            filas_desglose.append({
                'Fecha':f"{dias_semana[x['fecha'].weekday()]} {x['fecha']:%d/%m/%Y}",
                'Jornada prevista':f"{x['jornada']:g} h",
                'HE':f"{x['he']:g} h" if x['he'] else '—',
                'HLD':f"{x['hld']:g} h" if x['hld'] else '—',
                'Total a registrar':f"{consumo_dia:g} h"
            })
        tabla(filas_desglose)
        total_he=sum(x['he'] for x in desglose); total_hld=sum(x['hld'] for x in desglose)
        partes=[]
        if total_he: partes.append(f'HE: {total_he:g} h')
        if total_hld: partes.append(f'HLD: {total_hld:g} h')
        st.info(f"Total del periodo: {' · '.join(partes)} · {len(fechas)} día{'s' if len(fechas)!=1 else ''} laborable{'s' if len(fechas)!=1 else ''}.")

    propuesta = copy.deepcopy(REGISTROS)
    existentes, conflictos = [], []
    for x in desglose:
        f=x['fecha']; jornada=x['jornada']; he_dia=x['he']; hld_dia=x['hld']
        key = (f.year,t,str(f.month),str(f.day))
        if propuesta.get(key): existentes.append(f)
        if tipo in ('HE','HLD','HE+HLD') and (he_dia+hld_dia<=0 or he_dia+hld_dia>jornada+1e-9):
            st.error(f'{f:%d/%m/%Y}: las horas deben ser positivas y no superar la jornada ({jornada:g} h).'); return
        if tipo=='BORRAR': propuesta.pop(key,None)
        elif tipo=='HE+HLD': propuesta[key]={'tipo':tipo,'he_horas':he_dia,'hld_horas':hld_dia,'anio':f.year,'tec':t}
        elif tipo in ('HE','HLD'): propuesta[key]={'tipo':tipo,'horas_gastadas':he_dia if tipo=='HE' else hld_dia,'anio':f.year,'tec':t}
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
    firma = hashlib.sha256(repr((t,ini,fin,tipo,[(x['fecha'].isoformat(),x['he'],x['hld']) for x in desglose],solo_laborables)).encode()).hexdigest()[:16]
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
    export_simple = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                     '<meta name="viewport" content="width=device-width,initial-scale=1">'
                     '<title>Cuadrante CI</title><style>body{font-family:Arial;padding:20px}'
                     'table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}'
                     '.grid-wrap{overflow-x:auto}.subtle{font-size:11px}</style></head><body>'
                     f'<h1>{MESES[mes]} {dd_anio}</h1>'+contenido+'</body></html>')
    descarga_simple, descarga_completa = st.columns(2)
    with descarga_simple:
        st.download_button('Descargar cuadrante filtrado · HTML',export_simple,
                           file_name=f'cuadrante_{dd_anio}_{mes}.html',mime='text/html',
                           key='descarga_cuadrante_simple')
        st.caption('Solo el cuadrante, según el mes, centro y técnico seleccionados.')
    with descarga_completa:
        export = informe_mensual_html(equipo,mes,dd_anio)
        st.download_button('Descargar informe mensual ampliado · HTML',export,
                           file_name=f'informe_ci_{dd_anio}_{mes:02d}.html',mime='text/html',
                           key='descarga_informe_ampliado')
        st.caption('Cuadrante, cobertura, PRL, ausencias, saldos y festivos. Respeta los mismos filtros.')
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

def _parse_fecha_iso(valor):
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        return None

def calcular_activacion_guardia(fecha, hora_inicio, hora_fin, centro_ci):
    """Condiciones 12x7: franja 08:00-20:00, HE x2 y abono tras superar 4 h."""
    ini = datetime.combine(fecha, hora_inicio)
    fin = datetime.combine(fecha, hora_fin)
    if fin <= ini:
        fin += timedelta(days=1)
    total = (fin-ini).total_seconds()/3600
    if total > 24:
        raise ValueError('La activación no puede superar 24 horas.')
    fuera = 0.0
    cursor = ini
    while cursor < fin:
        d = cursor.date()
        tramo_ini = max(ini, datetime.combine(d, datetime.min.time()))
        tramo_fin = min(fin, datetime.combine(d+timedelta(days=1), datetime.min.time()))
        g_ini = datetime.combine(d, datetime.strptime('08:00','%H:%M').time())
        g_fin = datetime.combine(d, datetime.strptime('20:00','%H:%M').time())
        dentro_ini, dentro_fin = max(tramo_ini,g_ini), min(tramo_fin,g_fin)
        dentro_dia = max(0.0,(dentro_fin-dentro_ini).total_seconds()/3600)
        fuera += max(0.0,(tramo_fin-tramo_ini).total_seconds()/3600-dentro_dia)
        cursor = tramo_fin
    dentro = max(0.0,total-fuera)
    exceso_dentro = max(0.0,dentro-4.0)
    he_generadas = 2.0*(fuera+exceso_dentro)
    horas_abono = max(0.0,total-4.0)
    es_festivo = (fecha.month,fecha.day) in FESTIVOS_POR_ANIO.get(fecha.year,{}).get(centro_ci,[])
    laborable = fecha.weekday() < 5 and not es_festivo
    tarifa = 20.0 if laborable else 25.0
    importe = horas_abono*tarifa
    return {'horas_totales':round(total,2),'horas_dentro':round(dentro,2),'horas_fuera':round(fuera,2),
            'horas_exceso_4':round(exceso_dentro,2),'he_generadas':round(he_generadas,2),
            'horas_abono':round(horas_abono,2),'tarifa':tarifa,'importe':round(importe,2),
            'tipo_dia':'Laborable' if laborable else 'Sábado/domingo/festivo'}


def periodos_guardia_reales(registros, tecnico=None, anio=None, mes=None):
    """Fusiona registros solapados o contiguos en periodos reales de guardia.
    Opcionalmente recorta el cálculo al año/mes solicitado.
    """
    if anio is not None:
        limite_ini = date(anio, mes or 1, 1)
        limite_fin = date(anio, mes, calendar.monthrange(anio, mes)[1]) if mes else date(anio, 12, 31)
    else:
        limite_ini = limite_fin = None

    intervalos = []
    for g in registros:
        if tecnico is not None and g.get('tecnico') != tecnico:
            continue
        ini = _parse_fecha_iso(g.get('inicio'))
        fin = _parse_fecha_iso(g.get('fin'))
        if not ini or not fin:
            continue
        if fin < ini:
            ini, fin = fin, ini
        if limite_ini is not None:
            ini = max(ini, limite_ini)
            fin = min(fin, limite_fin)
            if ini > fin:
                continue
        intervalos.append((ini, fin))

    intervalos.sort()
    fusionados = []
    for ini, fin in intervalos:
        if not fusionados or ini > fusionados[-1][1] + timedelta(days=1):
            fusionados.append([ini, fin])
        else:
            fusionados[-1][1] = max(fusionados[-1][1], fin)
    return [(ini, fin) for ini, fin in fusionados]

def resumen_guardias_tecnico(registros, tecnico, anio, mes=None):
    periodos = periodos_guardia_reales(registros, tecnico=tecnico, anio=anio, mes=mes)
    dias = sum((fin - ini).days + 1 for ini, fin in periodos)
    return len(periodos), dias

def guardias_calendario_html(equipo, mes, anio):
    ndias=calendar.monthrange(anio,mes)[1]; dias_sem=['L','M','X','J','V','S','D']; hoy=date.today()
    css="""<style>.gcal-wrap{overflow-x:auto;border:1px solid #dce5eb;border-radius:12px;background:white;margin:10px 0 18px}table.gcal{border-collapse:collapse;width:100%;min-width:1050px;font-size:11px}.gcal th{background:#123f4d;color:#fff;padding:8px 5px;border-right:1px solid #d7e0e5;text-align:center}.gcal th.name{min-width:190px;text-align:left;padding-left:12px}.gcal td{height:42px;text-align:center;border-right:1px solid #e3e9ed;border-bottom:1px solid #e3e9ed;padding:3px}.gcal td.name{text-align:left;padding:7px 10px;white-space:nowrap}.gcal .ci{display:block;color:#607584;font-size:10px;margin-top:2px}.gcal .weekend{background:#f1f3f5}.gcal .guard{background:#c9e7f0;color:#0b5267;font-weight:800}.gcal .today{box-shadow:inset 0 0 0 2px #008bb0}.gcal .dow{display:block;font-size:9px;margin-top:2px;opacity:.9}</style>"""
    head='<th class="name">Técnico / centro</th>'+''.join(f'<th>{d}<span class="dow">{dias_sem[date(anio,mes,d).weekday()]}</span></th>' for d in range(1,ndias+1))
    rows=[]
    for t in equipo:
        cells=[]
        for d in range(1,ndias+1):
            f=date(anio,mes,d); clases=[]
            if f.weekday()>=5: clases.append('weekend')
            if f==hoy: clases.append('today')
            en_guardia=any(g.get('tecnico')==t and (_parse_fecha_iso(g.get('inicio')) or date.max)<=f<=(_parse_fecha_iso(g.get('fin')) or date.min) for g in REGISTROS_GUARDIAS)
            if en_guardia: clases.append('guard')
            cells.append(f'<td class="{" ".join(clases)}">{"G" if en_guardia else "·"}</td>')
        rows.append(f'<tr><td class="name"><strong>{escape(t)}</strong><span class="ci">{escape(TECNICOS[t]["ci"])}</span></td>'+''.join(cells)+'</tr>')
    return css+'<div class="gcal-wrap"><table class="gcal"><thead><tr>'+head+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'

def informe_guardias_html(equipo, anio, mes=None):
    gs=[g for g in REGISTROS_GUARDIAS if int(g.get('anio',0))==anio and g.get('tecnico') in equipo]
    acts=[a for a in ACTIVACIONES_GUARDIA if int(a.get('anio',0))==anio and a.get('tecnico') in equipo]
    if mes:
        gs=[g for g in gs if any((_parse_fecha_iso(g.get('inicio')) or date.max)<=date(anio,mes,d)<=(_parse_fecha_iso(g.get('fin')) or date.min) for d in range(1,calendar.monthrange(anio,mes)[1]+1))]
        acts=[a for a in acts if _parse_fecha_iso(a.get('fecha')) and _parse_fecha_iso(a.get('fecha')).month==mes]
    total_he=sum(float(a.get('he_generadas',0) or 0) for a in acts); total_imp=sum(float(a.get('importe',0) or 0) for a in acts)
    def th(rows): return '<p class="empty">Sin registros.</p>' if not rows else '<div class="scroll">'+pd.DataFrame(rows).to_html(index=False,escape=True,border=0)+'</div>'
    resumen=[]
    for t in equipo:
        gt=[g for g in gs if g.get('tecnico')==t]; at=[a for a in acts if a.get('tecnico')==t]
        n_periodos, dias_guardia = resumen_guardias_tecnico(gs, t, anio, mes)
        resumen.append({'Técnico':t,'CI':TECNICOS[t]['ci'],'Periodos':n_periodos,'Días de guardia':dias_guardia,'Activaciones':len(at),'HE generadas':round(sum(float(a.get('he_generadas',0) or 0) for a in at),2),'Importe bruto (€)':round(sum(float(a.get('importe',0) or 0) for a in at),2)})
    detalle_g=[{'Periodo':f"{date.fromisoformat(g['inicio']):%d/%m/%Y} – {date.fromisoformat(g['fin']):%d/%m/%Y}",'Técnico':g.get('tecnico'),'CI':g.get('centro'),'Observaciones':g.get('nota','')} for g in sorted(gs,key=lambda x:x.get('inicio',''))]
    detalle_a=[{'Fecha':date.fromisoformat(a['fecha']).strftime('%d/%m/%Y'),'Técnico':a.get('tecnico'),'CI':a.get('centro'),'Inicio':a.get('inicio'),'Fin':a.get('fin'),'Intervención (h)':a.get('horas_totales',0),'Fuera 08–20 (h)':a.get('horas_fuera',0),'HE generadas':a.get('he_generadas',0),'Importe (€)':a.get('importe',0),'Motivo':a.get('motivo','')} for a in sorted(acts,key=lambda x:(x.get('fecha',''),x.get('inicio','')))]
    css="""body{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f9;color:#18313e;margin:0;padding:28px}main{max-width:1500px;margin:auto;background:white;padding:30px;border-radius:14px}h1{margin:8px 0;font-size:28px}h2{font-size:20px;margin-top:30px;border-bottom:2px solid #e2e8f0;padding-bottom:9px}.muted{color:#607584;font-size:12px}.metrics{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0}.metric{flex:1;min-width:160px;background:#edf6f8;border-top:4px solid #07566a;border-radius:10px;padding:15px}.metric strong{display:block;font-size:27px;margin-top:5px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:11px}th{background:#123f4d;color:white;text-align:left;padding:9px}td{border-bottom:1px solid #e2e8f0;padding:8px}tbody tr:nth-child(even){background:#f8fafc}.empty{padding:12px;background:#f4f7f9;border-radius:8px}@page{size:A4 landscape;margin:9mm}@media print{body{padding:0;background:#fff}main{padding:0;max-width:none}.metric,th,td{-webkit-print-color-adjust:exact;print-color-adjust:exact}tr{break-inside:avoid}}"""
    total_periodos=sum(resumen_guardias_tecnico(gs,t,anio,mes)[0] for t in equipo)
    total_dias=sum(resumen_guardias_tecnico(gs,t,anio,mes)[1] for t in equipo)
    periodo=MESES[mes] if mes else 'Año completo'; calendario=''
    for m in ([mes] if mes else list(range(1,13))): calendario+=f'<h3>{MESES[m]}</h3>'+guardias_calendario_html(equipo,m,anio)
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Informe guardias 12x7</title><style>'+css+'</style></head><body><main>'+f'<div class="muted">GESTIÓN DE TÉCNICOS CI · GUARDIAS 12x7</div><h1>Informe de guardias · {escape(periodo)} {anio}</h1><p class="muted">Emitido el {datetime.now():%d/%m/%Y %H:%M} · {len(equipo)} técnicos incluidos</p>'+f'<div class="metrics"><div class="metric">Periodos de guardia<strong>{total_periodos}</strong></div><div class="metric">Días de guardia<strong>{total_dias}</strong></div><div class="metric">Activaciones<strong>{len(acts)}</strong></div><div class="metric">HE generadas<strong>{total_he:g} h</strong></div><div class="metric">Importe activaciones<strong>{total_imp:,.2f} €</strong></div></div>'+'<h2>1. Resumen por técnico</h2>'+th(resumen)+'<h2>2. Calendario de guardias</h2>'+calendario+'<h2>3. Periodos registrados</h2>'+th(detalle_g)+'<h2>4. Detalle de activaciones</h2>'+th(detalle_a)+'<p class="muted">Los importes corresponden a activaciones registradas según las condiciones configuradas en la aplicación.</p></main></body></html>')

def render_guardias():
    st.markdown("""<style>
    .guard-kpi{background:#fff;border:1px solid #dfe7ed;border-radius:14px;padding:16px 18px;box-shadow:0 5px 16px rgba(18,49,61,.045);min-height:102px}
    .guard-kpi small{color:#718493;font-weight:700}.guard-kpi strong{display:block;font-size:27px;color:#12313d;margin-top:5px}
    </style>""",unsafe_allow_html=True)
    st.caption('Guardias 12x7 · horario de referencia 08:00–20:00. Un mismo CI no puede tener dos técnicos de guardia en fechas solapadas.')
    guardias_anio=[g for g in REGISTROS_GUARDIAS if int(g.get('anio',0))==dd_anio]
    acts_anio=[a for a in ACTIVACIONES_GUARDIA if int(a.get('anio',0))==dd_anio]
    total_importe=sum(float(a.get('importe',0) or 0) for a in acts_anio)
    total_he=sum(float(a.get('he_generadas',0) or 0) for a in acts_anio)
    total_periodos_anio=sum(resumen_guardias_tecnico(guardias_anio,t,dd_anio)[0] for t in TECNICOS)
    total_dias_anio=sum(resumen_guardias_tecnico(guardias_anio,t,dd_anio)[1] for t in TECNICOS)
    c1,c2,c3,c4,c5=st.columns(5)
    for col,label,val in [(c1,'Periodos de guardia',total_periodos_anio),(c2,'Días de guardia',total_dias_anio),(c3,'Activaciones',len(acts_anio)),(c4,'HE por activaciones',f'{total_he:g} h'),(c5,'Importe activaciones',f'{total_importe:,.2f} €')]:
        col.markdown(f'<div class="guard-kpi"><small>{label}</small><strong>{val}</strong></div>',unsafe_allow_html=True)
    tab_plan,tab_act,tab_calc,tab_res,tab_inf=st.tabs(['📅 Planificación','⚡ Activaciones','🧮 Calculadora','📊 Resumen','📄 Informe'])
    perfil_usuario = usuarios.get(st.session_state.get('usuario_id',''), {}) if hasattr(usuarios, 'get') else {}
    tecnico_vinculado = perfil_usuario.get('tecnico', st.session_state.usuario_actual)
    tecnico_sesion = tecnico_vinculado if tecnico_vinculado in TECNICOS else None
    with tab_plan:
        st.markdown('#### Registrar guardia')
        st.caption('La guardia puede abarcar cualquier periodo: lunes–domingo, miércoles–miércoles o el rango excepcional que corresponda.')
        if EDITOR:
            candidatos=visibles
        elif tecnico_sesion and TECNICOS.get(tecnico_sesion,{}).get('activo',True):
            candidatos=[tecnico_sesion]
        else:
            candidatos=[]
            st.info('Tu usuario no está vinculado a un técnico con el mismo nombre. Un Editor puede registrar la guardia o ajustar el nombre del usuario en Secrets.')
        if candidatos:
            fecha_base=date.today() if date.today().year==dd_anio else date(dd_anio,1,1)
            fecha_fin_base=min(fecha_base+timedelta(days=6),date(dd_anio,12,31))
            with st.form('form_guardia'):
                tg=st.selectbox('Técnico',candidatos,disabled=not EDITOR)
                cg1,cg2=st.columns(2)
                with cg1:
                    inicio_guardia=st.date_input('Fecha de inicio',value=fecha_base,min_value=date(dd_anio,1,1),max_value=date(dd_anio,12,31),key='guardia_inicio')
                with cg2:
                    fin_guardia=st.date_input('Fecha de fin',value=fecha_fin_base,min_value=date(dd_anio,1,1),max_value=date(dd_anio,12,31),key='guardia_fin')
                nota=st.text_input('Observaciones (opcional)')
                guardar=st.form_submit_button('Registrar guardia',type='primary')
            if inicio_guardia<=fin_guardia:
                dias_guardia=(fin_guardia-inicio_guardia).days+1
                st.caption(f'Periodo propuesto: {inicio_guardia:%d/%m/%Y} → {fin_guardia:%d/%m/%Y} · {dias_guardia} día(s)')
            else:
                st.warning('La fecha de fin debe ser igual o posterior a la fecha de inicio.')
            if guardar:
                ci=TECNICOS[tg]['ci']; conflicto=[]
                for g in REGISTROS_GUARDIAS:
                    if g.get('centro')!=ci or g.get('tecnico')==tg: continue
                    gi,gf=_parse_fecha_iso(g.get('inicio')),_parse_fecha_iso(g.get('fin'))
                    if gi and gf and inicio_guardia<=gf and fin_guardia>=gi: conflicto.append(g)
                duplicada=any(
                    g.get('tecnico')==tg and
                    g.get('inicio')==inicio_guardia.isoformat() and
                    g.get('fin')==fin_guardia.isoformat()
                    for g in REGISTROS_GUARDIAS
                )
                if inicio_guardia>fin_guardia:
                    st.error('La fecha de fin debe ser igual o posterior a la fecha de inicio.')
                elif duplicada:
                    st.info('Ese periodo ya está registrado para el técnico.')
                elif conflicto:
                    detalle=', '.join(f"{x.get('tecnico','')} ({(_parse_fecha_iso(x.get('inicio')) or date.min):%d/%m}–{(_parse_fecha_iso(x.get('fin')) or date.min):%d/%m})" for x in conflicto)
                    st.error('No se puede guardar: existe otra guardia que se solapa en el mismo CI: '+detalle)
                else:
                    nuevo=copy.deepcopy(REGISTROS_GUARDIAS)
                    gid=hashlib.sha256(f'{tg}|{inicio_guardia.isoformat()}|{fin_guardia.isoformat()}'.encode()).hexdigest()[:16]
                    nuevo.append({'id':gid,'anio':dd_anio,'tecnico':tg,'centro':ci,'inicio':inicio_guardia.isoformat(),'fin':fin_guardia.isoformat(),'nota':nota.strip(),'usuario':st.session_state.usuario_actual})
                    if guardar_cambios({RUTA_GUARDIAS:nuevo},f'Guardia 12x7: {tg}, {inicio_guardia} a {fin_guardia}'): st.rerun()
        filas=[]
        for g in sorted(guardias_anio,key=lambda x:x.get('inicio','')):
            if centro!='Todos' and g.get('centro')!=centro: continue
            filas.append({'Periodo':f"{date.fromisoformat(g['inicio']):%d/%m/%Y} – {date.fromisoformat(g['fin']):%d/%m/%Y}",'Días':(date.fromisoformat(g['fin'])-date.fromisoformat(g['inicio'])).days+1,'Técnico':g.get('tecnico'),'CI':g.get('centro'),'Observaciones':g.get('nota','')})
        st.markdown('#### Calendario de guardias')
        mes_guardia=st.selectbox('Mes',list(MESES),index=(date.today().month-1 if date.today().year==dd_anio else 0),format_func=MESES.get,key='mes_cal_guardias')
        equipo_guardia=[t for t in visibles if centro=='Todos' or TECNICOS[t]['ci']==centro]
        st.markdown(guardias_calendario_html(equipo_guardia,mes_guardia,dd_anio),unsafe_allow_html=True)
        st.caption('G = guardia asignada · fines de semana sombreados · el día actual queda enmarcado.')
        with st.expander('Ver listado de periodos registrados',expanded=False): tabla(filas)
        propias=[g for g in guardias_anio if EDITOR or g.get('tecnico')==tecnico_sesion]
        if propias:
            with st.expander('Eliminar una guardia registrada'):
                gid=st.selectbox('Guardia',[g['id'] for g in propias],format_func=lambda i:next(f"{g['tecnico']} · {date.fromisoformat(g['inicio']):%d/%m/%Y}" for g in propias if g['id']==i))
                conf=st.checkbox('Confirmar eliminación',key='conf_del_guardia')
                if st.button('Eliminar guardia',disabled=not conf):
                    nuevo=[g for g in REGISTROS_GUARDIAS if g.get('id')!=gid]
                    if guardar_cambios({RUTA_GUARDIAS:nuevo},f'Eliminar guardia {gid}'): st.rerun()
    with tab_act:
        st.markdown('#### Registrar activación')
        if not EDITOR:
            st.info('Las activaciones y su repercusión económica/HE solo pueden registrarlas los Editores.')
        else:
            with st.form('form_activacion'):
                ta=st.selectbox('Técnico activado',visibles,key='act_tec')
                fa=st.date_input('Fecha de activación',value=date.today() if date.today().year==dd_anio else date(dd_anio,1,1),min_value=date(dd_anio,1,1),max_value=date(dd_anio,12,31))
                ca,cb=st.columns(2); hi=ca.time_input('Hora inicio',value=datetime.strptime('18:00','%H:%M').time()); hf=cb.time_input('Hora fin',value=datetime.strptime('20:00','%H:%M').time())
                motivo=st.text_area('Motivo / detalle de la activación')
                calcular=st.form_submit_button('Calcular activación',type='primary')
            if calcular:
                calc=calcular_activacion_guardia(fa,hi,hf,TECNICOS[ta]['ci'])
                st.session_state['act_preview']={'tecnico':ta,'fecha':fa.isoformat(),'inicio':hi.strftime('%H:%M'),'fin':hf.strftime('%H:%M'),'motivo':motivo.strip(),**calc}
            prev=st.session_state.get('act_preview')
            if prev:
                st.markdown('##### Resultado')
                a1,a2,a3,a4=st.columns(4); a1.metric('Intervención',f"{prev['horas_totales']:g} h"); a2.metric('Fuera 08–20',f"{prev['horas_fuera']:g} h"); a3.metric('HE generadas',f"{prev['he_generadas']:g} h"); a4.metric('Importe bruto',f"{prev['importe']:,.2f} €")
                st.caption(f"{prev['tipo_dia']} · {prev['horas_abono']:g} h a abonar × {prev['tarifa']:g} €/h. Las HE se incorporarán automáticamente a la bolsa del técnico.")
                confirmar=st.checkbox('Confirmo los datos y quiero registrar la activación.',key='confirm_act')
                if st.button('Guardar activación',type='primary',disabled=not confirmar):
                    aid=hashlib.sha256(f"{prev['tecnico']}|{prev['fecha']}|{prev['inicio']}|{prev['fin']}|{time.time()}".encode()).hexdigest()[:16]
                    act={**prev,'id':aid,'anio':dd_anio,'centro':TECNICOS[prev['tecnico']]['ci'],'usuario':st.session_state.usuario_actual,'registrado':datetime.now().isoformat(timespec='seconds')}
                    nuevas_act=copy.deepcopy(ACTIVACIONES_GUARDIA); nuevas_act.append(act)
                    nuevas_he=copy.deepcopy(REGISTROS_HE)
                    if prev['he_generadas']:
                        nuevas_he.setdefault(prev['tecnico'],[]).append({'anio':dd_anio,'horas_reales':prev['horas_totales'],'horas_compensadas':prev['he_generadas'],'motivo':f"Activación guardia {prev['fecha']} · {prev['motivo'] or 'Sin detalle'}",'usuario':st.session_state.usuario_actual,'fecha':datetime.now().strftime('%d/%m/%Y %H:%M'),'origen':'guardia','activacion_id':aid})
                    if guardar_cambios({RUTA_ACTIVACIONES:nuevas_act,RUTA_HE:nuevas_he},f"Activación guardia: {prev['tecnico']} · {prev['fecha']} · {prev['he_generadas']:g} HE · {prev['importe']:.2f} €"):
                        st.session_state.pop('act_preview',None); st.rerun()
        filas_act=[]
        for a in sorted(acts_anio,key=lambda x:(x.get('fecha',''),x.get('inicio','')),reverse=True):
            if centro!='Todos' and a.get('centro')!=centro: continue
            filas_act.append({'Fecha':date.fromisoformat(a['fecha']).strftime('%d/%m/%Y'),'CI':a.get('centro'),'Técnico':a.get('tecnico'),'Inicio':a.get('inicio'),'Fin':a.get('fin'),'Fuera horario (h)':a.get('horas_fuera',0),'HE':a.get('he_generadas',0),'Importe bruto (€)':a.get('importe',0),'Motivo':a.get('motivo','')})
        st.markdown('#### Histórico de activaciones'); tabla(filas_act)
        if EDITOR and acts_anio:
            with st.expander('Eliminar activación errónea'):
                aid=st.selectbox('Activación',[a['id'] for a in acts_anio],format_func=lambda i:next(f"{a['fecha']} · {a['tecnico']} · {a.get('he_generadas',0)} HE" for a in acts_anio if a['id']==i),key='del_act')
                conf=st.checkbox('Confirmar eliminación de la activación y de las HE asociadas',key='conf_del_act')
                if st.button('Eliminar activación',disabled=not conf):
                    nuevas_act=[a for a in ACTIVACIONES_GUARDIA if a.get('id')!=aid]
                    nuevas_he=copy.deepcopy(REGISTROS_HE)
                    for tec in nuevas_he: nuevas_he[tec]=[h for h in nuevas_he[tec] if h.get('activacion_id')!=aid]
                    if guardar_cambios({RUTA_ACTIVACIONES:nuevas_act,RUTA_HE:nuevas_he},f'Eliminar activación guardia {aid}'): st.rerun()
    with tab_calc:
        st.markdown('#### Calculadora 12x7')
        st.caption('Simulación sin guardar datos. Condiciones trasladadas de la hoja “Condiciones Guardias”.')
        cc=st.selectbox('CI para festivos/tarifa',CENTROS,key='calc_ci')
        fc=st.date_input('Fecha',value=date.today() if date.today().year==dd_anio else date(dd_anio,1,1),key='calc_fecha')
        x1,x2=st.columns(2); hic=x1.time_input('Inicio',value=datetime.strptime('18:00','%H:%M').time(),key='calc_ini'); hfc=x2.time_input('Fin',value=datetime.strptime('23:00','%H:%M').time(),key='calc_fin')
        r=calcular_activacion_guardia(fc,hic,hfc,cc)
        tabla([{'Tipo día':r['tipo_dia'],'Horas totales':r['horas_totales'],'Dentro 08–20':r['horas_dentro'],'Fuera 08–20':r['horas_fuera'],'Exceso dentro tras 4 h':r['horas_exceso_4'],'HE generadas':r['he_generadas'],'Horas a abonar':r['horas_abono'],'€/h':r['tarifa'],'Importe bruto (€)':r['importe']}])
        st.info('Regla aplicada: las horas fuera de 08:00–20:00 y las horas dentro de guardia que excedan las primeras 4 h generan 2 HE por hora. El abono económico se aplica a las horas totales que exceden de 4: 20 €/h laborable y 25 €/h sábado, domingo o festivo.')
    with tab_res:
        st.markdown('#### Resumen mensual por CI')
        filas=[]
        for ci in CENTROS:
            if centro!='Todos' and ci!=centro: continue
            for mes in range(1,13):
                tecnicos_ci=[t for t in TECNICOS if TECNICOS[t]['ci']==ci]
                periodos_mes=sum(resumen_guardias_tecnico(guardias_anio,t,dd_anio,mes)[0] for t in tecnicos_ci)
                dias_mes=sum(resumen_guardias_tecnico(guardias_anio,t,dd_anio,mes)[1] for t in tecnicos_ci)
                aa=[a for a in acts_anio if a.get('centro')==ci and _parse_fecha_iso(a.get('fecha')) and _parse_fecha_iso(a.get('fecha')).month==mes]
                if periodos_mes or aa: filas.append({'CI':ci,'Mes':MESES[mes],'Periodos':periodos_mes,'Días de guardia':dias_mes,'Activaciones':len(aa),'HE generadas':round(sum(float(a.get('he_generadas',0) or 0) for a in aa),2),'Importe bruto (€)':round(sum(float(a.get('importe',0) or 0) for a in aa),2)})
        tabla(filas)
        st.caption('La hoja original indica una estimación de 5 activaciones de guardia máximo al año por cada CCII; se muestra como referencia, no como bloqueo.')

    with tab_inf:
        st.markdown('#### Informe de guardias')
        st.caption('Genera un informe completo con resumen, calendarios, periodos registrados y activaciones. Se puede abrir en el navegador, imprimir o guardar como PDF.')
        ir1,ir2=st.columns(2)
        alcance=ir1.radio('Periodo',['Año completo','Mes'],horizontal=True,key='guard_inf_periodo')
        mes_inf=ir2.selectbox('Mes',list(MESES),index=(date.today().month-1 if date.today().year==dd_anio else 0),format_func=MESES.get,key='guard_inf_mes',disabled=alcance=='Año completo')
        equipo_inf=[t for t in visibles if centro=='Todos' or TECNICOS[t]['ci']==centro]
        html_inf=informe_guardias_html(equipo_inf,dd_anio,None if alcance=='Año completo' else mes_inf)
        st.download_button('📄 Descargar informe HTML',html_inf.encode('utf-8'),file_name=f'Informe_Guardias_{dd_anio}_{"Anual" if alcance=="Año completo" else MESES[mes_inf]}.html',mime='text/html')
        st.markdown('##### Vista rápida')
        vista_mes=mes_inf if alcance=='Mes' else (date.today().month if date.today().year==dd_anio else 1)
        st.markdown(guardias_calendario_html(equipo_inf,vista_mes,dd_anio),unsafe_allow_html=True)

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
                if pendientes['HE']-he_compensadas_registro(retirado)<0: st.error('La eliminación dejaría horas ya consumidas sin saldo.')
                elif guardar_cambios({RUTA_HE:nuevo},f'Eliminar HE: {t}, ID {idx}'): st.rerun()

def render_informes():
    opcion = st.radio('Informe',['Balance','Guardias','PRL','Solapamientos','Auditoría'],horizontal=True)
    filas = []
    if opcion=='Balance':
        st.markdown('''<style>
        .balance-head{margin:8px 0 18px}.balance-head h3{margin:0 0 4px;color:#12313d;font-size:20px}
        .balance-head p{margin:0;color:#718493;font-size:13px}
        .balance-kpi{background:#fff;border:1px solid #dfe7ed;border-radius:14px;padding:16px 18px;box-shadow:0 5px 16px rgba(18,49,61,.045);min-height:104px}
        .balance-kpi .k-label{font-size:12px;font-weight:700;color:#607584;text-transform:uppercase;letter-spacing:.035em}
        .balance-kpi .k-value{font-size:28px;font-weight:800;color:#12313d;line-height:1.15;margin:6px 0 3px}
        .balance-kpi .k-note{font-size:12px;color:#8293a0}
        .balance-legend{margin:12px 0 16px;color:#718493;font-size:12px}
        </style>''', unsafe_allow_html=True)
        for t in visibles:
            usados, pendientes = saldos(t, dd_anio)
            totales = {k: round(usados[k] + pendientes[k], 2) for k in usados}
            acciones = []
            if pendientes['VPA'] > 0: acciones.append('Planificar VPA pendientes')
            if pendientes['V'] >= 20: acciones.append('Planificar vacaciones pendientes')
            if pendientes['HLD'] >= 40: acciones.append('Planificar HLD pendientes')
            accion = ' · '.join(acciones) if acciones else 'Sin acción'
            filas.append({'Centro':TECNICOS[t]['ci'],'Técnico':t,
                'V Total':totales['V'],'V Consumidas':usados['V'],'V Pendientes':pendientes['V'],
                'VPA Total':totales['VPA'],'VPA Consumidas':usados['VPA'],'VPA Pendientes':pendientes['VPA'],
                'HLD Total (h)':totales['HLD'],'HLD Consumidas (h)':usados['HLD'],'HLD Pendientes (h)':pendientes['HLD'],
                'HE Total (h)':totales['HE'],'HE Consumidas (h)':usados['HE'],'HE Pendientes (h)':pendientes['HE'],
                'Acción recomendada':accion})
        st.markdown(f'<div class="balance-head"><h3>Resumen anual de saldos · {dd_anio}</h3><p>Totales asignados, consumo, saldo pendiente y necesidades de planificación del equipo seleccionado.</p></div>',unsafe_allow_html=True)
        if filas:
            total_v=sum(x['V Total'] for x in filas); consum_v=sum(x['V Consumidas'] for x in filas)
            pend_hld=sum(x['HLD Pendientes (h)'] for x in filas); pend_he=sum(x['HE Pendientes (h)'] for x in filas)
            con_accion=sum(x['Acción recomendada']!='Sin acción' for x in filas)
            kpis=[('Vacaciones consumidas',f'{consum_v:g} / {total_v:g}','días-persona'),('HLD pendientes',f'{pend_hld:g} h','saldo conjunto del equipo'),('HE pendientes',f'{pend_he:g} h','horas compensadas disponibles'),('Requieren planificación',str(con_accion),f'de {len(filas)} técnicos')]
            for col,(label,value,note) in zip(st.columns(4),kpis):
                col.markdown(f'<div class="balance-kpi"><div class="k-label">{escape(label)}</div><div class="k-value">{escape(value)}</div><div class="k-note">{escape(note)}</div></div>',unsafe_allow_html=True)
            st.markdown('<div class="balance-legend">Los resaltados ayudan a localizar saldos pendientes. La acción recomendada es una ayuda visual y no modifica ningún registro.</div>',unsafe_allow_html=True)
            df_balance=pd.DataFrame(filas)
            def estilo_balance(row):
                estilos=['']*len(row); columnas=list(row.index)
                def marcar(col,cond,color):
                    if col in columnas and cond: estilos[columnas.index(col)]=f'background-color:{color};font-weight:700'
                marcar('V Pendientes',row['V Pendientes']>=20,'#fff8c5')
                marcar('VPA Pendientes',row['VPA Pendientes']>0,'#fff8c5')
                marcar('HLD Pendientes (h)',row['HLD Pendientes (h)']>=40,'#fff8c5')
                if row['Acción recomendada']!='Sin acción': estilos[columnas.index('Acción recomendada')]='background-color:#fff8c5;font-weight:700;color:#6b5200'
                else: estilos[columnas.index('Acción recomendada')]='color:#527064'
                return estilos
            st.dataframe(df_balance.style.apply(estilo_balance,axis=1).format(precision=2,na_rep=''),use_container_width=True,hide_index=True,height=min(520,38*len(filas)+42))
        else: st.info('No hay técnicos para la selección actual.')
    elif opcion=='Guardias':
        st.markdown(f'### Guardias 12x7 · {dd_anio}')
        equipo_inf=[t for t in visibles if centro=='Todos' or TECNICOS[t]['ci']==centro]
        gs=[g for g in REGISTROS_GUARDIAS if int(g.get('anio',0))==dd_anio and g.get('tecnico') in equipo_inf]
        acts=[a for a in ACTIVACIONES_GUARDIA if int(a.get('anio',0))==dd_anio and a.get('tecnico') in equipo_inf]
        total_he=sum(float(a.get('he_generadas',0) or 0) for a in acts); total_imp=sum(float(a.get('importe',0) or 0) for a in acts)
        total_periodos=sum(resumen_guardias_tecnico(gs,t,dd_anio)[0] for t in equipo_inf)
        total_dias=sum(resumen_guardias_tecnico(gs,t,dd_anio)[1] for t in equipo_inf)
        for col,(lab,val) in zip(st.columns(5),[('Periodos',total_periodos),('Días de guardia',total_dias),('Activaciones',len(acts)),('HE generadas',f'{total_he:g} h'),('Importe',f'{total_imp:,.2f} €')]): col.metric(lab,val)
        mes_rep=st.selectbox('Vista mensual',list(MESES),index=(date.today().month-1 if date.today().year==dd_anio else 0),format_func=MESES.get,key='inf_guard_mes')
        st.markdown(guardias_calendario_html(equipo_inf,mes_rep,dd_anio),unsafe_allow_html=True)
        filas=[]
        for t in equipo_inf:
            gt=[g for g in gs if g.get('tecnico')==t]; at=[a for a in acts if a.get('tecnico')==t]
            n_periodos, dias_guardia = resumen_guardias_tecnico(gs,t,dd_anio)
            filas.append({'Técnico':t,'CI':TECNICOS[t]['ci'],'Periodos':n_periodos,'Días de guardia':dias_guardia,'Activaciones':len(at),'HE generadas':round(sum(float(a.get('he_generadas',0) or 0) for a in at),2),'Importe bruto (€)':round(sum(float(a.get('importe',0) or 0) for a in at),2)})
        tabla(filas)
        html_guard=informe_guardias_html(equipo_inf,dd_anio,None)
        st.download_button('📄 Descargar informe completo HTML',html_guard.encode('utf-8'),file_name=f'Informe_Guardias_{dd_anio}.html',mime='text/html')
    elif opcion=='PRL':
        filas=[{'Técnico':t,'Centro':TECNICOS[t]['ci'],'Estado':estado_prl(t)[0],'Caducidad':estado_prl(t)[1]} for t in visibles]
        tabla(filas)
    elif opcion=='Solapamientos':
        por_dia={}
        for (a,t,m,d),v in REGISTROS.items():
            if a==dd_anio and t in visibles and tipo_registro(v): por_dia.setdefault((date(a,int(m),int(d)),TECNICOS[t]['ci']),[]).append(t)
        filas=[{'Fecha':f,'Centro':c,'Técnicos':', '.join(ts)} for (f,c),ts in sorted(por_dia.items()) if len(ts)>1]
        st.caption('Coincidencia de marcas, no necesariamente ausencia completa. Revisar cobertura antes de actuar.'); tabla(filas)
    else:
        if not EDITOR: st.info('Auditoría reservada a editores.'); return
        filas=[x for x in reversed(AUDITORIA) if x.get('fecha','').startswith(str(dd_anio))]
        st.caption('Auditoría global del año, sin filtro de centro. Persistida desde esta versión; el histórico de sesiones anteriores no estaba guardado.'); tabla(filas)
    if filas:
        df=pd.DataFrame(filas)
        seguro=df.map(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) if hasattr(df,'map') else df.applymap(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v)
        st.download_button('Descargar CSV',seguro.to_csv(index=False,sep=';').encode('utf-8-sig'),file_name=f'{opcion}_{dd_anio}.csv',mime='text/csv')

def render_config():
    if not EDITOR:
        st.info('Configuración reservada a editores.'); return
    opcion = st.radio('Ajustes',['Técnicos','Festivos','Horarios','HLD','Avisos por email','Copias de seguridad'],horizontal=True)
    if opcion=='Técnicos':
        st.subheader('Gestión de técnicos')
        st.caption('Añade nuevos técnicos o modifica su centro y asignaciones. Los registros históricos existentes no se alteran.')

        activos = sum(1 for d in TECNICOS.values() if d.get('activo', True))
        c1, c2, c3 = st.columns(3)
        c1.metric('Técnicos activos', activos)
        c2.metric('Técnicos históricos', len(TECNICOS))
        c3.metric('Centros', len({d.get('ci','') for d in TECNICOS.values() if d.get('ci')}))

        tab_nuevo, tab_editar = st.tabs(['➕ Añadir técnico','✏️ Editar / desactivar'])
        centros_existentes = sorted({d.get('ci','') for d in TECNICOS.values() if d.get('ci')})

        with tab_nuevo:
            st.markdown('#### Alta de nuevo técnico')
            with st.form('alta_tecnico', clear_on_submit=False):
                nombre = st.text_input('Nombre y apellidos')
                ci = st.selectbox('CI asignado', centros_existentes)
                ca, cb = st.columns(2)
                vac = ca.number_input('Vacaciones anuales (días)', min_value=0, max_value=60, value=22, step=1)
                vpa = cb.number_input('VPA iniciales (días)', min_value=0, max_value=60, value=0, step=1)
                st.markdown('**Datos PRL (opcionales)**')
                cp1, cp2 = st.columns(2)
                nip = cp1.text_input('NIP')
                dni = cp2.text_input('DNI')
                fecha_prl = st.date_input('Caducidad PRL', value=None)
                obs_prl = st.text_input('Observaciones PRL')
                confirmar = st.checkbox('Confirmo el alta del nuevo técnico')
                alta = st.form_submit_button('Añadir técnico', type='primary', disabled=not confirmar)
            if alta:
                nombre = ' '.join(nombre.split()).strip()
                if not nombre:
                    st.error('Indica el nombre y apellidos del técnico.')
                elif nombre in TECNICOS:
                    st.error('Ya existe un técnico con ese nombre. Usa Editar / desactivar para modificarlo.')
                else:
                    nuevos_tecnicos = copy.deepcopy(TECNICOS)
                    nuevos_tecnicos[nombre] = {'ci':ci,'vac_totales':int(vac),'vpa_base':int(vpa),'he_totales':0.0,'activo':True}
                    nuevo_prl = copy.deepcopy(REGISTROS_PRL)
                    nuevo_prl[nombre] = {'nip':nip.strip(),'dni':dni.strip(),'fecha':fecha_prl.isoformat() if fecha_prl else '', 'obs':obs_prl.strip()}
                    if guardar_cambios({RUTA_TECNICOS:nuevos_tecnicos,RUTA_PRL:nuevo_prl},f'Alta técnico: {nombre} · {ci}'):
                        st.rerun()

        with tab_editar:
            st.markdown('#### Editar técnico existente')
            elegido = st.selectbox('Técnico', sorted(TECNICOS), key='config_tecnico_editar')
            actual = TECNICOS[elegido]
            ci_actual = actual.get('ci','')
            opciones_ci = centros_existentes if ci_actual in centros_existentes else centros_existentes + [ci_actual]
            with st.form(f'editar_tecnico_{elegido}'):
                nuevo_ci = st.selectbox('CI asignado', opciones_ci, index=opciones_ci.index(ci_actual))
                ce1, ce2 = st.columns(2)
                nuevas_vac = ce1.number_input('Vacaciones anuales (días)', min_value=0, max_value=60, value=int(actual.get('vac_totales',22)), step=1)
                nuevo_vpa = ce2.number_input('VPA base (días)', min_value=0, max_value=60, value=int(actual.get('vpa_base',0)), step=1)
                activo = st.checkbox('Técnico activo', value=bool(actual.get('activo',True)))
                st.caption('Desactivar oculta al técnico de la operativa habitual, pero conserva vacaciones, ausencias, HE/HLD, PRL y auditoría históricas.')
                guardar_tec = st.form_submit_button('Guardar cambios', type='primary')
            if guardar_tec:
                nuevos_tecnicos = copy.deepcopy(TECNICOS)
                nuevos_tecnicos[elegido].update({'ci':nuevo_ci,'vac_totales':int(nuevas_vac),'vpa_base':int(nuevo_vpa),'activo':activo})
                if guardar_cambios({RUTA_TECNICOS:nuevos_tecnicos},f'Actualizar técnico: {elegido} · {nuevo_ci} · activo={activo}'):
                    st.rerun()
        return

    if opcion=='Avisos por email':
        st.subheader('Avisos por email')
        remitente = str(secreto('GMAIL_USUARIO', '')).strip()
        destinatario = str(secreto('GMAIL_DESTINATARIO', '')).strip()
        configurado = bool(remitente and secreto('GMAIL_APP_PASSWORD', '') and destinatario)

        if configurado:
            st.success('Gmail está configurado en los Secrets de Streamlit.')
            c1, c2 = st.columns(2)
            c1.write(f'**Remitente:** {remitente}')
            c2.write(f'**Destinatario:** {destinatario}')
        else:
            st.warning('Falta configurar Gmail en los Secrets de Streamlit.')

        st.markdown('#### Envío manual')
        col_prueba, col_prl = st.columns(2)
        with col_prueba:
            st.caption('Comprueba únicamente que Gmail puede enviar correctamente.')
            if st.button('Enviar correo de prueba', disabled=not configurado, use_container_width=True):
                ok, resultado = enviar_email(
                    'Prueba · Gestión de Técnicos CI',
                    'Hola,\n\n'
                    'Este es un correo de prueba enviado desde la aplicación Gestión de Técnicos CI.\n\n'
                    'La configuración de avisos por Gmail funciona correctamente.\n\n'
                    'Gestión de Técnicos CI · Indra / RPECII'
                )
                st.success(resultado) if ok else st.error(resultado)
        with col_prl:
            st.caption('Fuerza ahora un resumen con todos los PRL caducados, sin fecha o que vencen en ≤60 días.')
            if st.button('⚠️ Enviar avisos PRL ahora', type='primary', disabled=not configurado, use_container_width=True):
                ok, resultado = enviar_resumen_prl_manual()
                st.success(resultado) if ok else st.warning(resultado)

        st.divider()
        st.markdown('#### Próximos avisos automáticos')
        st.caption('GitHub Actions realiza la comprobación de lunes a viernes. Hitos: 60 días · 30 días · 15 días · aviso diario desde 7 días · aviso diario mientras esté caducado.')
        pendientes = avisos_prl_actuales()
        if pendientes:
            filas_avisos = []
            for aviso in pendientes:
                filas_avisos.append({
                    'Técnico': aviso['tecnico'],
                    'Centro': aviso['centro'],
                    'Caducidad': aviso['fecha'].strftime('%d/%m/%Y') if aviso['fecha'] else 'Sin fecha',
                    'Estado actual': texto_estado_prl(aviso['dias']),
                    'Siguiente aviso automático': siguiente_aviso_prl(aviso['dias'])
                })
            st.dataframe(pd.DataFrame(filas_avisos), use_container_width=True, hide_index=True)
        else:
            st.success('No hay PRL caducados, sin fecha ni con vencimiento en los próximos 60 días.')

        st.info('Automatización configurada mediante GitHub Actions. El botón manual de PRL no altera la programación automática: únicamente fuerza un envío en ese momento.')
        return

    if opcion=='Copias de seguridad':
        datos = {RUTA_BDD:serializar_registros(REGISTROS),RUTA_HE:REGISTROS_HE,RUTA_PRL:REGISTROS_PRL,RUTA_TECNICOS:TECNICOS,RUTA_FESTIVOS:FESTIVOS_POR_ANIO,RUTA_CONFIG_ANUAL:CONFIG_ANUAL_POR_ANIO,RUTA_HORARIOS_CI:HORARIOS_CI_ANUAL,RUTA_HLD_ANUAL:HLD_ANUAL_POR_ANIO,RUTA_GUARDIAS:REGISTROS_GUARDIAS,RUTA_ACTIVACIONES:ACTIVACIONES_GUARDIA,'auditoria_repsol.json':AUDITORIA}
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
 'Guardias':render_guardias,'Horas extra':render_he,'Informes':render_informes,'Configuración':render_config}[pagina]()
st.divider()
st.caption('Gestión de Técnicos CI · Juan Pedro Murillo Huete · Indra / RPECII')
