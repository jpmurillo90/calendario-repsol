# ==============================================================================
# SISTEMA INTEGRAL DE GESTIÓN DE CALENDARIOS REPSOL (HASTA 2030 + CONFIG ANUAL CI + HLD)V2
# ==============================================================================


import calendar
import json
from datetime import datetime, date
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
from google.colab import drive

drive.mount('/content/drive', force_remount=True)
RUTA_BDD = '/content/drive/My Drive/datos_tecnicos_repsol.json'
RUTA_FESTIVOS = '/content/drive/My Drive/festivos_repsol.json'
RUTA_HE = '/content/drive/My Drive/horas_extra_repsol.json'
RUTA_CONFIG_ANUAL = '/content/drive/My Drive/config_anual_repsol.json'
RUTA_HORARIOS_CI = '/content/drive/My Drive/horarios_ci_anual_repsol.json'
RUTA_HLD_ANUAL = '/content/drive/My Drive/hld_anual_repsol.json'

ANOS_DISPONIBLES = [2026, 2027, 2028, 2029, 2030]

def guardar_en_drive(registros_dict):
    datos_json = {f"{a}|{t}|{m}|{d}": v for (a, t, m, d), v in registros_dict.items()}
    with open(RUTA_BDD, 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, ensure_ascii=False, indent=4)

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
HISTORIAL_AUDITORIA = []

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

# 3. WIDGETS
opciones_marca = [(f"{k} - {v[0]}", k) for k, v in LEYENDA.items() if k not in ['FEST', 'SAB', 'DOM']]
opciones_marca.append(('Limpiar Marca (Vacío)', ''))

dd_anio = widgets.Dropdown(options=ANOS_DISPONIBLES, value=ANOS_DISPONIBLES[0], description='Año:')
dd_vista = widgets.Dropdown(options=['Calendario Individual', 'Matriz Cuadrante Global (Equipo)'], description='Modo Vista:')
dd_tecnico = widgets.Dropdown(options=list(TECNICOS.keys()), description='Técnico:')
dd_mes = widgets.Dropdown(options=[(nombre, num) for num, nombre in MESES.items()], description='Mes:')
dd_dia_inicio = widgets.Dropdown(options=list(range(1, 32)), description='Día Inicio:')
dd_dia_fin = widgets.Dropdown(options=list(range(1, 32)), description='Día Fin:')
dd_tipo = widgets.Dropdown(options=opciones_marca, description='Marca:')

dd_horas_disfrute = widgets.Dropdown(options=[0.0], value=0.0, description='Horas a Gastar:')
fecha_cobertura = widgets.DatePicker(value=date(ANOS_DISPONIBLES[0], 8, 25), description='Fecha Cob.:')

btn_guardar = widgets.Button(description='Guardar Rango', button_style='success', icon='save')
btn_exportar = widgets.Button(description='Descargar Excel', button_style='info', icon='download')
btn_exportar_html = widgets.Button(description='Descargar HTML Detallado', button_style='warning', icon='file-code-o')

lista_cis = list(set(info['ci'] for info in TECNICOS.values()))
dd_cfg_centro = widgets.Dropdown(options=lista_cis, description='Centro (CI):')
dd_cfg_anio = widgets.Dropdown(options=ANOS_DISPONIBLES, value=ANOS_DISPONIBLES[0], description='Año:')
dd_cfg_mes = widgets.Dropdown(options=[(nombre, num) for num, nombre in MESES.items()], description='Mes:')
dd_cfg_dia = widgets.Dropdown(options=list(range(1, 32)), description='Día:')
btn_add_festivo = widgets.Button(description='Añadir Festivo', button_style='success', icon='plus')
btn_del_festivo = widgets.Button(description='Eliminar Festivo Seleccionado', button_style='danger', icon='trash')
dd_festivos_actuales = widgets.Dropdown(options=[], description='Festivos:', layout=widgets.Layout(width='300px'))

dd_ci_horario_anio = widgets.Dropdown(options=ANOS_DISPONIBLES, value=ANOS_DISPONIBLES[0], description='Año CI:')
dd_ci_horario_centro = widgets.Dropdown(options=lista_cis, description='Centro CI:')
txt_horario_texto = widgets.Text(value="L-V 07'15h-15'15h", description='Horario:')
txt_horario_sem = widgets.Text(value="40h", description='H/Semana:')
txt_horario_obs = widgets.Text(value="-", description='Observaciones:')
btn_guardar_horario_ci = widgets.Button(description='Guardar Horario CI', button_style='success', icon='save')

dd_hld_anio = widgets.Dropdown(options=ANOS_DISPONIBLES, value=ANOS_DISPONIBLES[0], description='Año HLD:')
dd_hld_centro = widgets.Dropdown(options=lista_cis, description='Centro HLD:')
txt_hld_valor_asig = widgets.FloatText(value=87.0, description='Total HLD:')
btn_guardar_hld_anual = widgets.Button(description='Guardar HLD Anual', button_style='success', icon='save')

dd_he_tecnico = widgets.Dropdown(options=list(TECNICOS.keys()), description='Técnico:')
dd_he_anio = widgets.Dropdown(options=ANOS_DISPONIBLES, value=ANOS_DISPONIBLES[0], description='Año:')
txt_he_horas = widgets.FloatText(value=1.0, description='Horas Reales:', tooltip='Horas reales trabajadas (1h real = 1h 45m compensadas)')
txt_he_motivo = widgets.Text(value='', description='Motivo / Aviso:', placeholder='Ej. Urgencia en planta')
btn_he_agregar = widgets.Button(description='Registrar Horas Extra', button_style='success', icon='plus-circle')
dd_he_historial = widgets.Dropdown(options=[], description='Registros HE:', layout=widgets.Layout(width='450px'))
btn_he_eliminar = widgets.Button(description='Eliminar HE Seleccionada', button_style='danger', icon='trash')

out_alertas = widgets.Output()
out_calendario = widgets.Output()
out_resumen = widgets.Output()
out_cobertura = widgets.Output()
out_saldo_tiempo_real = widgets.Output()
out_incidencias = widgets.Output()
out_auditoria = widgets.Output()
out_config = widgets.Output()
out_he_gestion = widgets.Output()
out_horarios_ci = widgets.Output()
out_hld_gestion = widgets.Output()

def actualizar_dias(change):
    num_dias = calendar.monthrange(dd_anio.value, dd_mes.value)[1]
    dd_dia_inicio.options = list(range(1, num_dias + 1))
    dd_dia_fin.options = list(range(1, num_dias + 1))

def actualizar_dias_cfg(change):
    num_dias = calendar.monthrange(dd_cfg_anio.value, dd_cfg_mes.value)[1]
    dd_cfg_dia.options = list(range(1, num_dias + 1))
    poblar_dropdown_festivos()

dd_mes.observe(actualizar_dias, names='value')
dd_anio.observe(actualizar_dias, names='value')
dd_cfg_mes.observe(actualizar_dias_cfg, names='value')
dd_cfg_anio.observe(actualizar_dias_cfg, names='value')
dd_cfg_centro.observe(lambda c: poblar_dropdown_festivos(), names='value')

def poblar_dropdown_festivos():
    anio = dd_cfg_anio.value
    ci = dd_cfg_centro.value
    festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(ci, [])
    festivos_ordenados = sorted(festivos, key=lambda x: (x[0], x[1]))
    opciones = [(f"{d}/{m} de {MESES[m]}", (m, d)) for m, d in festivos_ordenados]
    dd_festivos_actuales.options = opciones

def poblar_dropdown_he_historial():
    tec = dd_he_tecnico.value
    anio = dd_he_anio.value
    registros = REGISTROS_HE.get(tec, [])
    opciones = []
    for idx, item in enumerate(registros):
        if item['anio'] == anio:
            eq = item['horas_reales'] * 1.75
            opciones.append((f"[{item['horas_reales']}h reales -> {eq:.2f}h comp.] {item['motivo']}", idx))
    dd_he_historial.options = opciones

dd_he_tecnico.observe(lambda c: poblar_he_panel(), names='value')
dd_he_anio.observe(lambda c: poblar_he_panel(), names='value')

def poblar_he_panel():
    poblar_dropdown_he_historial()
    with out_he_gestion:
        clear_output()
        tec = dd_he_tecnico.value
        anio = dd_he_anio.value
        total_reales = sum(i['horas_reales'] for i in REGISTROS_HE.get(tec, []) if i['anio'] == anio)
        total_comp = calcular_he_compensadas_totales(tec, anio)
        total_gastado = calcular_he_consumidas_horas(tec, anio)
        saldo_disponible = round(total_comp - total_gastado, 2)

        html = f"""
        <div style='background-color:#F8F9FA; border:1px solid #DCDCDC; border-radius:6px; padding:12px; font-family:sans-serif;'>
            <h4 style='margin:0 0 8px 0; color:#002A3A;'>⚡ Resumen de Horas Extra - {tec} ({anio})</h4>
            <p style='margin:4px 0;'><b>Total Horas Reales Hechas:</b> {total_reales} h</p>
            <p style='margin:4px 0;'><b>Total Horas Compensadas (x1.75):</b> {total_comp:.2f} h</p>
            <p style='margin:4px 0;'><b>Horas Disfrutadas en Calendario:</b> {total_gastado:.2f} h</p>
            <p style='margin:4px 0;'><b>Saldo de Horas Extra Disponibles:</b> <span style='color:{"red" if saldo_disponible < 0 else "green"}; font-weight:bold;'>{saldo_disponible:.2f} h</span></p>
        </div>
        """
        display(HTML(html))

def actualizar_saldo_tiempo_real(change=None):
    anio = dd_anio.value
    tec = dd_tecnico.value
    info = TECNICOS[tec]
    hld_totales_anio = obtener_hld_totales_tecnico(tec, anio)
    vpa_totales_anio = obtener_vpa_totales_tecnico(tec, anio)

    vac_cons = 0
    vpa_cons = 0
    hld_cons = 0.0

    for key, val in REGISTROS.items():
        parts = key.split('|') if isinstance(key, str) else None
        if parts and len(parts) == 4:
            a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
        elif isinstance(key, tuple) and len(key) == 4:
            a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
        else:
            continue

        if a == anio and t == tec:
            marca_str = val['tipo'] if isinstance(val, dict) else val
            if marca_str == 'V': vac_cons += 1
            elif marca_str == 'VPA': vpa_cons += 1
            elif marca_str == 'HLD':
                if isinstance(val, dict):
                    hld_cons += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, anio))
                else:
                    hld_cons += obtener_horas_hld(tec, m, d, anio)

    he_comp = calcular_he_compensadas_totales(tec, anio)
    he_gasto = calcular_he_consumidas_horas(tec, anio)
    he_disp = round(he_comp - he_gasto, 2)

    tipo_sel = dd_tipo.value
    opciones_he = []

    if tipo_sel == 'HE':
        val_max = max(0.0, he_disp)
        if val_max > 0:
            val_actual = 0.5
            while val_actual <= val_max:
                opciones_he.append((f"{val_actual:.1f}h", round(val_actual, 2)))
                val_actual += 0.5
            if round(val_max, 2) not in [x[1] for x in opciones_he]:
                opciones_he.append((f"{val_max:.2f}h (Exactas)", round(val_max, 2)))
        else:
            opciones_he.append(("0.0h (Sin saldo HE)", 0.0))
    elif tipo_sel == 'HLD':
        mes_sel = dd_mes.value
        dia_sel = dd_dia_inicio.value

        hld_max_teorico = obtener_horas_hld(tec, mes_sel, dia_sel, anio)
        if hld_max_teorico == 0.0:
            num_dias_mes = calendar.monthrange(anio, mes_sel)[1]
            for d_test in range(1, num_dias_mes + 1):
                h_t_test = obtener_horas_hld(tec, mes_sel, d_test, anio)
                if h_t_test > 0.0:
                    hld_max_teorico = h_t_test
                    break

        hld_pend_actual = hld_totales_anio - hld_cons
        val_max = min(hld_max_teorico if hld_max_teorico > 0 else 7.0, max(0.0, hld_pend_actual))

        if val_max > 0:
            val_actual = 0.5
            while val_actual <= val_max:
                opciones_he.append((f"{val_actual:.1f}h", round(val_actual, 2)))
                val_actual += 0.5
            if round(val_max, 2) not in [x[1] for x in opciones_he]:
                opciones_he.append((f"{val_max:.2f}h (Máx HLD)", round(val_max, 2)))
        else:
            opciones_he.append(("0.0h (Sin saldo HLD)", 0.0))
    else:
        opciones_he.append(("Día Completo / No aplica", 0.0))

    dd_horas_disfrute.options = opciones_he
    if opciones_he:
        dd_horas_disfrute.value = opciones_he[-1][1]

    vac_pend = info['vac_totales'] - vac_cons
    vpa_pend = vpa_totales_anio - vpa_cons
    hld_pend = hld_totales_anio - hld_cons

    with out_saldo_tiempo_real:
        clear_output()
        html = f"""
        <div style='background-color:#F2F4F7; border-left:4px solid #005B7F; padding:8px 12px; margin-bottom:10px; font-family:sans-serif; font-size:11px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;'>
            <div><b>👤 Técnico:</b> {tec} ({anio})</div>
            <div>🏖️ <b>Vac:</b> {vac_cons}/{info['vac_totales']} (<span style='color:{"red" if vac_pend < 0 else "green"};'><b>{vac_pend}</b></span>)</div>
            <div>⏱️ <b>VPA:</b> {vpa_cons}/{vpa_totales_anio} (<b>{vpa_pend}</b>)</div>
            <div>⏳ <b>HLD:</b> {hld_cons:.1f}h/{hld_totales_anio}h (<span style='color:{"red" if hld_pend < 0 else "green"};'><b>{hld_pend!r}h</b></span>)</div>
            <div>⚡ <b>HE Disp:</b> <span style='color:{"red" if he_disp < 0 else "green"};'><b>{he_disp:.2f}h</b></span></div>
        </div>
        """
        display(HTML(html))

dd_tecnico.observe(actualizar_saldo_tiempo_real, names='value')
dd_anio.observe(actualizar_saldo_tiempo_real, names='value')
dd_tipo.observe(actualizar_saldo_tiempo_real, names='value')
dd_dia_inicio.observe(actualizar_saldo_tiempo_real, names='value')

def renderizar_leyenda_html():
    html_leyenda = """
    <div style='background-color: #F8F9FA; border: 1px solid #DCDCDC; border-radius: 6px; padding: 12px; margin-top: 20px; font-family: sans-serif;'>
        <h4 style='margin: 0 0 8px 0; color: #002A3A; font-size: 13px;'>📖 Leyenda de Códigos y Estados</h4>
        <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
    """
    for k, (desc, color) in LEYENDA.items():
        html_leyenda += f"""
        <div style='display: flex; align-items: center; background: white; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; font-size: 11px;'>
            <span style='background-color: {color}; border: 1px solid #999; width: 14px; height: 14px; display: inline-block; margin-right: 6px; border-radius: 2px;'></span>
            <b>{k}:</b>&nbsp;{desc}
        </div>
        """
    html_leyenda += "</div></div>"
    return html_leyenda

# 4. RENDERIZADOS
def renderizar_pantalla():
    with out_calendario:
        clear_output()
        anio = dd_anio.value
        mes_num = dd_mes.value
        mes_nom = MESES[mes_num]

        if dd_vista.value == 'Calendario Individual':
            tec = dd_tecnico.value
            ci = TECNICOS[tec]['ci']
            cal = calendar.monthcalendar(anio, mes_num)
            festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(ci, [])

            html = f"<h3 style='color:#002A3A;'>📅 Calendario: {tec} ({ci}) - {mes_nom} {anio}</h3>"
            html += "<table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; width:100%;'>"
            html += "<tr style='background-color:#002A3A; color:white;'><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th style='background-color:#7f7f7f;'>Sáb</th><th style='background-color:#7f7f7f;'>Dom</th></tr>"

            for semana in cal:
                html += "<tr>"
                for idx, dia in enumerate(semana):
                    if dia == 0:
                        html += "<td style='background-color:#f2f2f2;'></td>"
                    else:
                        val_reg = REGISTROS.get((anio, tec, str(mes_num), str(dia)), REGISTROS.get(f"{anio}|{tec}|{mes_num}|{dia}", ''))
                        marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
                        bg_color = '#ffffff'

                        weekday = calendar.weekday(anio, mes_num, dia)
                        if (mes_num, dia) in festivos:
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

                        texto_celda = f"<b>{marca}</b>"
                        if marca == 'HE' and isinstance(val_reg, dict):
                            h_g = val_reg.get('horas_gastadas', 0.0)
                            h_t = obtener_horas_jornada_real(tec, anio, mes_num, dia)
                            h_trab = round(max(0.0, h_t - h_g), 2)
                            texto_celda = f"<b>HE</b><br><span style='font-size:9px;'>({h_g}h g. / {h_trab}h t.)</span>"
                        elif marca == 'HLD':
                            if isinstance(val_reg, dict):
                                h_g = val_reg.get('horas_gastadas', obtener_horas_hld(tec, mes_num, dia, anio))
                                h_t = obtener_horas_hld(tec, mes_num, dia, anio)
                                if h_g < h_t:
                                    texto_celda = f"<b>HLD</b><br><span style='font-size:9px;'>({h_g}h g.parcial)</span>"
                                else:
                                    texto_celda = f"<b>HLD</b><br><span style='font-size:9px;'>({h_g}h)</span>"
                            else:
                                h_g = obtener_horas_hld(tec, mes_num, dia, anio)
                                texto_celda = f"<b>HLD</b><br><span style='font-size:9px;'>({h_g}h)</span>"

                        html += f"<td style='background-color:{bg_color}; height:54px; width:14%;'>"
                        html += f"<b>{dia}</b><br><span style='font-size:10px; color:#002A3A;'>{texto_celda}</span>"
                        html += "</td>"
                html += "</tr>"
            html += "</table>"
            display(HTML(html))
        else:
            num_dias = calendar.monthrange(anio, mes_num)[1]
            dias_semana_abrev = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
            html = f"<h3 style='color:#002A3A;'>👥 Cuadrante Mensual de Equipo - {mes_nom} {anio}</h3>"
            html += "<table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; font-size:11px; width:100%;'>"
            html += "<tr style='background-color:#002A3A; color:white;'><th>Técnico</th><th>CI</th>"
            for d in range(1, num_dias + 1):
                wd = calendar.weekday(anio, mes_num, d)
                html += f"<th style='width:28px;'>{d}<br><span style='font-size:9px; color:#ccc;'>{dias_semana_abrev[wd]}</span></th>"
            html += "</tr>"

            for tec, info in TECNICOS.items():
                html += f"<tr><td style='text-align:left; padding-left:5px;'><b>{tec}</b></td><td>{info['ci']}</td>"
                festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(info['ci'], [])
                for d in range(1, num_dias + 1):
                    val_reg = REGISTROS.get((anio, tec, str(mes_num), str(d)), REGISTROS.get(f"{anio}|{tec}|{mes_num}|{d}", ''))
                    marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
                    bg_color = '#ffffff'
                    weekday = calendar.weekday(anio, mes_num, d)

                    if (mes_num, d) in festivos:
                        bg_color = LEYENDA['FEST'][1]
                        if not marca: marca = 'FEST'
                    elif weekday >= 5:
                        bg_color = LEYENDA['SAB'][1] if weekday == 5 else LEYENDA['DOM'][1]
                        if not marca: marca = 'SAB' if weekday == 5 else 'DOM'
                    elif marca in LEYENDA:
                        bg_color = LEYENDA[marca][1]

                    etiqueta_matriz = marca
                    if marca == 'HLD' and isinstance(val_reg, dict):
                        h_g = val_reg.get('horas_gastadas', 0.0)
                        h_t = obtener_horas_hld(tec, mes_num, d, anio)
                        if h_g < h_t:
                            etiqueta_matriz = f"HLD*"
                    elif marca == 'HE' and isinstance(val_reg, dict):
                        etiqueta_matriz = f"HE*"

                    html += f"<td style='background-color:{bg_color};'><b>{etiqueta_matriz}</b></td>"
                html += "</tr>"
            html += "</table>"
            display(HTML(html))

        display(HTML(renderizar_leyenda_html()))

def renderizar_resumen():
    with out_resumen:
        clear_output()
        anio = dd_anio.value
        datos = []
        for tec, info in TECNICOS.items():
            hld_totales_tecnico = obtener_hld_totales_tecnico(tec, anio)
            vpa_totales_tecnico = obtener_vpa_totales_tecnico(tec, anio)
            vac_cons = 0
            vpa_cons = 0
            hld_cons = 0.0
            for key, val in REGISTROS.items():
                parts = key.split('|') if isinstance(key, str) else None
                if parts and len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                elif isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    continue
                if a == anio and t == tec:
                    marca_str = val['tipo'] if isinstance(val, dict) else val
                    if marca_str == 'V': vac_cons += 1
                    elif marca_str == 'VPA': vpa_cons += 1
                    elif marca_str == 'HLD':
                        if isinstance(val, dict):
                            hld_cons += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, anio))
                        else:
                            hld_cons += obtener_horas_hld(tec, m, d, anio)

            he_comp = calcular_he_compensadas_totales(tec, anio)
            he_gast = calcular_he_consumidas_horas(tec, anio)
            he_disp = round(he_comp - he_gast, 2)

            otras_aus = 0
            for key, val in REGISTROS.items():
                parts = key.split('|') if isinstance(key, str) else None
                if parts and len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                elif isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    continue
                if a == anio and t == tec:
                    marca_str = val['tipo'] if isinstance(val, dict) else val
                    if marca_str not in ['V', 'VPA', 'HLD', 'HE', 'FEST', 'SAB', 'DOM', ''] and marca_str:
                        otras_aus += 1

            datos.append({
                'Centro (CI)': info['ci'], 'Técnico': tec,
                'Vac. Cons.': vac_cons, 'Vac. Pend.': info['vac_totales'] - vac_cons,
                'VPA Cons.': vpa_cons, 'VPA Pend.': vpa_totales_tecnico - vpa_cons,
                'HLD Cons. (h)': round(hld_cons, 2), 'HLD Pend. (h)': round(hld_totales_tecnico - hld_cons, 2),
                'HE Comp. (h)': he_comp, 'HE Disp. (h)': he_disp,
                'Otras Aus.': otras_aus
            })
        display(HTML(f"<h3 style='color:#002A3A;'>📊 Balance Consolidado de Saldos - {anio}</h3>"))
        display(pd.DataFrame(datos))

def renderizar_cobertura():
    with out_cobertura:
        clear_output()
        dt = fecha_cobertura.value
        if not dt: return
        anio, mes, dia = dt.year, dt.month, dt.day
        fecha_str = dt.strftime("%d/%m/%Y")

        tecnicos_detalle = []
        conteo_ci = {}
        total_trabajando = 0

        for tec, info in TECNICOS.items():
            ci = info['ci']
            if ci not in conteo_ci:
                conteo_ci[ci] = {'asignados': 0, 'trabajando': 0, 'ausentes': 0}
            conteo_ci[ci]['asignados'] += 1

            val_reg = REGISTROS.get((anio, tec, str(mes), str(dia)), REGISTROS.get(f"{anio}|{tec}|{mes}|{dia}", ''))
            marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg

            weekday = calendar.weekday(anio, mes, dia)
            festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(ci, [])
            es_festivo = (mes, dia) in festivos or weekday >= 5

            if marca == '' and not es_festivo:
                horas_jornada = obtener_horas_jornada_real(tec, anio, mes, dia)
                codigo = f"{horas_jornada:.2f}".replace('.', ',')
                estado = "<b style='color:#008000;'>TRABAJA</b>"
                obs = f"Trabaja {codigo} h"
                conteo_ci[ci]['trabajando'] += 1
                total_trabajando += 1
            elif marca in ['HE', 'HLD'] and isinstance(val_reg, dict):
                h_g = val_reg.get('horas_gastadas', 0.0)
                h_t = obtener_horas_jornada_real(tec, anio, mes, dia) if marca == 'HE' else obtener_horas_hld(tec, mes, dia, anio)
                h_trab = round(max(0.0, h_t - h_g), 2)
                codigo = f"{marca} ({h_g}h g.)"
                if h_trab > 0:
                    estado = f"<b style='color:#008000;'>TRABAJA ({marca} PARC.)</b>"
                    obs = f"Gasta {h_g}h {marca}, trabaja {h_trab}h"
                    conteo_ci[ci]['trabajando'] += 1
                    total_trabajando += 1
                else:
                    estado = "<b style='color:#FF0000;'>NO TRABAJA</b>"
                    desc = LEYENDA.get(marca, ('Ausencia', ''))[0]
                    obs = f"Gasta {h_g}h {marca} (Día completo)"
                    conteo_ci[ci]['ausentes'] += 1
            else:
                if marca:
                    codigo = marca
                else:
                    codigo = 'FEST' if (mes, dia) in festivos else ('SAB' if weekday == 5 else 'DOM')

                estado = "<b style='color:#FF0000;'>NO TRABAJA</b>"
                desc = LEYENDA.get(codigo, ('Festivo / Fin de Semana', ''))[0]
                obs = desc
                conteo_ci[ci]['ausentes'] += 1

            tecnicos_detalle.append({
                'CI': ci, 'TÉCNICO': tec, 'CÓDIGO DE ESTADO': codigo,
                'ESTADO HOY': estado, 'OBSERVACIONES': obs
            })

        pct_global = round((total_trabajando / len(TECNICOS)) * 100) if len(TECNICOS) > 0 else 0
        estado_servicio = "<span style='color:green;'>🟢 OK</span>" if pct_global >= 70 else "<span style='color:#B45F06;'>🟡 REVISAR</span>"

        html = f"""
        <div style='background-color:#005B7F; color:white; text-align:center; padding:10px; font-weight:bold; font-size:14px; margin-top:15px; border-radius:3px;'>COBERTURA TÉCNICOS - {fecha_str}</div>
        <div style='display:flex; justify-content:space-between; margin-top:10px;'>
            <div style='width:68%;'>
                <table border='1' style='border-collapse:collapse; text-align:center; font-family:sans-serif; width:100%; font-size:11px;'>
                    <tr style='background-color:#002A3A; color:white;'><th>CI</th><th>TÉCNICO</th><th>CÓDIGO</th><th>ESTADO</th><th>OBSERVACIONES</th></tr>
        """
        for r in tecnicos_detalle:
            html += f"<tr><td>{r['CI']}</td><td style='text-align:left; padding-left:5px;'><b>{r['TÉCNICO']}</b></td><td>{r['CÓDIGO DE ESTADO']}</td><td>{r['ESTADO HOY']}</td><td style='text-align:left; padding-left:5px;'>{r['OBSERVACIONES']}</td></tr>"
        html += f"""
                </table>
            </div>
            <div style='width:30%;'>
                <table border='1' style='border-collapse:collapse; text-align:left; font-family:sans-serif; width:100%; font-size:11px;'>
                    <tr style='background-color:#002A3A; color:white;'><th colspan='2' style='text-align:center;'>Resumen Global</th></tr>
                    <tr><td style='padding:4px;'><b>Disponibles</b></td><td style='text-align:center;'>{total_trabajando}/{len(TECNICOS)}</td></tr>
                    <tr><td style='padding:4px;'><b>Disponibilidad</b></td><td style='text-align:center;'><b>{pct_global}%</b></td></tr>
                    <tr><td style='padding:4px;'><b>Estado</b></td><td style='text-align:center;'><b>{estado_servicio}</b></td></tr>
                </table>
            </div>
        </div>
        """
        display(HTML(html))

def renderizar_incidencias():
    with out_incidencias:
        clear_output()
        anio = dd_anio.value
        html = f"<h3 style='color:#002A3A;'>🛠️ Resumen de Incidencias, Solapamientos y Saldos ({anio})</h3>"

        alertas_saldos = []
        for tec, info in TECNICOS.items():
            hld_totales_anio = obtener_hld_totales_tecnico(tec, anio)
            vpa_totales_anio = obtener_vpa_totales_tecnico(tec, anio)
            vac_cons = 0
            vpa_cons = 0
            hld_cons = 0.0
            for key, val in REGISTROS.items():
                parts = key.split('|') if isinstance(key, str) else None
                if parts and len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                elif isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    continue
                if a == anio and t == tec:
                    marca_str = val['tipo'] if isinstance(val, dict) else val
                    if marca_str == 'V': vac_cons += 1
                    elif marca_str == 'VPA': vpa_cons += 1
                    elif marca_str == 'HLD':
                        if isinstance(val, dict):
                            hld_cons += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, anio))
                        else:
                            hld_cons += obtener_horas_hld(tec, m, d, anio)

            he_comp = calcular_he_compensadas_totales(tec, anio)
            he_gast = calcular_he_consumidas_horas(tec, anio)

            if vac_cons > info['vac_totales']:
                alertas_saldos.append(f"Exceso de Vacaciones: <b>{tec}</b> ha consumido {vac_cons} de {info['vac_totales']} permitidas.")
            if vpa_cons > vpa_totales_anio:
                alertas_saldos.append(f"Exceso de VPA (Año Anterior): <b>{tec}</b> ha consumido {vpa_cons} de {vpa_totales_anio} permitidas.")
            if hld_cons > hld_totales_anio:
                alertas_saldos.append(f"Exceso de HLD: <b>{tec}</b> ha consumido {hld_cons:.1f}h de {hld_totales_anio}h permitidas para {anio}.")
            if he_gast > he_comp:
                alertas_saldos.append(f"Exceso de Horas Extra: <b>{tec}</b> ha gastado {he_gast:.1f}h de HE pero solo tiene {he_comp:.1f}h compensadas.")

        if alertas_saldos:
            html += "<div style='background-color:#FFC7CE; border:1px solid #9C0006; padding:10px; border-radius:5px; color:#9C0006; margin-bottom:15px;'><b>⚠️ Alertas de Exceso de Saldo:</b><ul>"
            for al in alertas_saldos: html += f"<li>{al}</li>"
            html += "</ul></div>"
        else:
            html += "<div style='background-color:#C6EFCE; padding:8px; border-radius:5px; color:#006100; margin-bottom:15px;'>✅ Ningún técnico supera sus topes de saldo actuales.</div>"

        display(HTML(html))

def renderizar_auditoria():
    with out_auditoria:
        clear_output()
        html = "<h3 style='color:#002A3A;'>📋 Historial de Cambios / Auditoría (Sesión Actual)</h3>"
        if not HISTORIAL_AUDITORIA:
            html += "<p><i>No se han registrado modificaciones en esta sesión todavía.</i></p>"
        else:
            html += "<table border='1' style='border-collapse:collapse; text-align:left; font-family:sans-serif; width:100%; font-size:12px;'>"
            html += "<tr style='background-color:#002A3A; color:white;'><th>Hora</th><th>Técnico</th><th>Fecha Afectada</th><th>Marca Aplicada</th></tr>"
            for h in reversed(HISTORIAL_AUDITORIA):
                html += f"<tr><td style='padding:4px;'>{h['hora']}</td><td><b>{h['tec']}</b></td><td>{h['rango']}</td><td>{h['tipo']}</td></tr>"
            html += "</table>"
        display(HTML(html))

def renderizar_config():
    with out_config:
        clear_output()
        poblar_dropdown_festivos()
        html = "<h3 style='color:#002A3A;'>⚙️ Configuración del Equipo y Festivos</h3>"
        display(HTML(html))

        datos_conf = []
        for tec, info in TECNICOS.items():
            hld_t = obtener_hld_totales_tecnico(tec, dd_cfg_anio.value)
            vpa_t = obtener_vpa_totales_tecnico(tec, dd_cfg_anio.value)
            datos_conf.append({
                'Técnico': tec, 'Centro (CI)': info['ci'],
                'Vacaciones Totales': info['vac_totales'],
                f'VPA Totales ({dd_cfg_anio.value})': vpa_t,
                f'HLD Totales ({dd_cfg_anio.value})': hld_t
            })
        display(pd.DataFrame(datos_conf))

def renderizar_horarios_ci():
    with out_horarios_ci:
        clear_output()
        anio_sel = dd_ci_horario_anio.value
        horarios_anio = HORARIOS_CI_ANUAL.get(anio_sel, HORARIOS_CI_DEFAULT.get(anio_sel, {}))

        html = f"""
        <h3 style='color:#002A3A;'>⏰ Horarios Reales de Cliente por CI ({anio_sel})</h3>
        <p style='font-size:12px; color:#555;'>Detalle de los turnos oficiales y cómputo de horas semanales por centro de trabajo configurables por año:</p>
        <table border='1' style='border-collapse:collapse; text-align:left; font-family:sans-serif; width:100%; font-size:12px;'>
            <tr style='background-color:#002A3A; color:white;'>
                <th style='padding:8px;'>Centro</th>
                <th style='padding:8px;'>Horario</th>
                <th style='padding:8px; text-align:center;'>H/Sem</th>
                <th style='padding:8px;'>Observaciones / Excepciones Temporales</th>
            </tr>
        """
        for ci, datos in horarios_anio.items():
            html += f"""
            <tr>
                <td style='padding:6px;'><b>{ci}</b></td>
                <td style='padding:6px;'>{datos['horario']}</td>
                <td style='padding:6px; text-align:center;'><b>{datos['h_sem']}</b></td>
                <td style='padding:6px;'>{datos['obs']}</td>
            </tr>
            """
        html += "</table>"
        display(HTML(html))

def renderizar_hld_gestion():
    with out_hld_gestion:
        clear_output()
        anio_sel = dd_hld_anio.value
        hld_anio = HLD_ANUAL_POR_ANIO.get(anio_sel, HLD_ANUAL_DEFAULT.get(anio_sel, {}))

        html = f"""
        <h3 style='color:#002A3A;'>⏳ Configuración de HLD Totales por Centro e Año ({anio_sel})</h3>
        <p style='font-size:12px; color:#555;'>Asignación de horas de libre disposición totales que recibe cada Complejo Industrial para este año:</p>
        <table border='1' style='border-collapse:collapse; text-align:left; font-family:sans-serif; width:50%; font-size:12px;'>
            <tr style='background-color:#002A3A; color:white;'>
                <th style='padding:8px;'>Centro (CI)</th>
                <th style='padding:8px; text-align:center;'>Total HLD (h)</th>
            </tr>
        """
        for ci, val_hld in hld_anio.items():
            html += f"""
            <tr>
                <td style='padding:6px;'><b>{ci}</b></td>
                <td style='padding:6px; text-align:center;'>{val_hld}h</td>
            </tr>
            """
        html += "</table>"
        display(HTML(html))

# 5. CONTROLADORES
def on_guardar_clicked(b):
    anio = dd_anio.value
    tec, mes = dd_tecnico.value, str(dd_mes.value)
    d_ini, d_fin, tipo = dd_dia_inicio.value, dd_dia_fin.value, dd_tipo.value

    if d_ini > d_fin:
        with out_alertas:
            clear_output()
            print("❌ Error: El día de inicio debe ser menor o igual al día fin.")
        return

    coincidencias_totales = []
    for dia in range(d_ini, d_fin + 1):
        c = verificar_coincidencias(tec, mes, str(dia), tipo, anio)
        if c: coincidencias_totales.append((dia, c))

        clave_reg = (anio, tec, mes, str(dia))
        if tipo == '':
            REGISTROS.pop(clave_reg, None)
            REGISTROS.pop(f"{anio}|{tec}|{mes}|{dia}", None)
        elif tipo == 'HE':
            horas_jornada_dia = obtener_horas_jornada_real(tec, anio, int(mes), dia)
            h_efectivas = min(round(dd_horas_disfrute.value, 2), horas_jornada_dia)
            REGISTROS[clave_reg] = {
                'tipo': 'HE',
                'horas_gastadas': h_efectivas,
                'anio': anio,
                'tec': tec
            }
        elif tipo == 'HLD':
            hld_teorico_dia = obtener_horas_hld(tec, int(mes), dia, anio)
            h_efectivas = min(round(dd_horas_disfrute.value, 2), hld_teorico_dia)
            REGISTROS[clave_reg] = {
                'tipo': 'HLD',
                'horas_gastadas': h_efectivas,
                'anio': anio,
                'tec': tec
            }
        else:
            REGISTROS[clave_reg] = tipo

    guardar_en_drive(REGISTROS)

    texto_marca_historial = tipo
    if tipo in ['HE', 'HLD']:
        texto_marca_historial = f"{tipo} ({dd_horas_disfrute.value}h)"
    elif not tipo:
        texto_marca_historial = 'Limpieza (Vacío)'

    HISTORIAL_AUDITORIA.append({
        'hora': datetime.now().strftime("%H:%M:%S"),
        'tec': tec,
        'rango': f"Del {d_ini} al {d_fin} de {MESES[int(mes)]} {anio}",
        'tipo': texto_marca_historial
    })

    with out_alertas:
        clear_output()
        print(f"✅ Registros guardados del {d_ini} al {d_fin} de {MESES[int(mes)]} de {anio} para {tec}.")
        if coincidencias_totales:
            ci = TECNICOS[tec]['ci']
            html_alerta = f"<div style='background-color:#FFC7CE; border:1px solid #9C0006; padding:10px; margin-top:5px; border-radius:5px; color:#9C0006;'>"
            html_alerta += f"<b>⚠️ ¡ALERTAS DE SOLAPAMIENTO EN {ci.upper()}!</b><br><ul>"
            for dia, coinc in coincidencias_totales:
                for c_tec, c_marca, c_desc in coinc:
                    html_alerta += f"<li>Día {dia}/{mes}: Coincide con <b>{c_tec}</b> ({c_marca} - {c_desc})</li>"
            html_alerta += "</ul></div>"
            display(HTML(html_alerta))

    actualizar_saldo_tiempo_real()
    renderizar_pantalla()
    renderizar_resumen()
    renderizar_cobertura()
    renderizar_incidencias()
    renderizar_auditoria()

def on_he_agregar_clicked(b):
    tec = dd_he_tecnico.value
    anio = dd_he_anio.value
    horas = txt_he_horas.value
    motivo = txt_he_motivo.value.strip() or 'Sin motivo especificado'

    if horas <= 0:
        print("❌ Las horas reales deben ser mayores a 0.")
        return

    if tec not in REGISTROS_HE:
        REGISTROS_HE[tec] = []

    REGISTROS_HE[tec].append({
        'anio': anio,
        'horas_reales': horas,
        'motivo': motivo
    })

    guardar_he_drive()
    poblar_he_panel()
    actualizar_saldo_tiempo_real()
    renderizar_resumen()
    print(f"✅ Se han registrado {horas}h extra reales a {tec} (Equivalen a {horas * 1.75:.2f}h compensadas).")

def on_he_eliminar_clicked(b):
    tec = dd_he_tecnico.value
    seleccion = dd_he_historial.value
    if seleccion is None:
        print("❌ Selecciona un registro de horas extra de la lista para eliminar.")
        return

    registros = REGISTROS_HE.get(tec, [])
    if 0 <= seleccion < len(registros):
        eliminado = registros.pop(seleccion)
        guardar_he_drive()
        poblar_he_panel()
        actualizar_saldo_tiempo_real()
        renderizar_resumen()
        print(f"🗑️ Registro de {eliminado['horas_reales']}h eliminado correctamente.")

btn_guardar.on_click(on_guardar_clicked)
btn_he_agregar.on_click(on_he_agregar_clicked)
btn_he_eliminar.on_click(on_he_eliminar_clicked)

def on_add_festivo_clicked(b):
    anio = dd_cfg_anio.value
    ci = dd_cfg_centro.value
    mes = dd_cfg_mes.value
    dia = dd_cfg_dia.value

    if anio not in FESTIVOS_POR_ANIO: FESTIVOS_POR_ANIO[anio] = {}
    if ci not in FESTIVOS_POR_ANIO[anio]: FESTIVOS_POR_ANIO[anio][ci] = []

    par = (mes, dia)
    if par not in FESTIVOS_POR_ANIO[anio][ci]:
        FESTIVOS_POR_ANIO[anio][ci].append(par)
        guardar_festivos_drive()
        poblar_dropdown_festivos()
        renderizar_pantalla()
        renderizar_cobertura()
        print(f"✅ Festivo {dia}/{mes}/{anio} añadido para {ci}.")

def on_del_festivo_clicked(b):
    anio = dd_cfg_anio.value
    ci = dd_cfg_centro.value
    seleccion = dd_festivos_actuales.value
    if not seleccion:
        print("❌ Selecciona un festivo para eliminar.")
        return
    if anio in FESTIVOS_POR_ANIO and ci in FESTIVOS_POR_ANIO[anio]:
        if seleccion in FESTIVOS_POR_ANIO[anio][ci]:
            FESTIVOS_POR_ANIO[anio][ci].remove(seleccion)
            guardar_festivos_drive()
            poblar_dropdown_festivos()
            renderizar_pantalla()
            renderizar_cobertura()
            print(f"🗑️ Festivo eliminado de {ci}.")

btn_add_festivo.on_click(on_add_festivo_clicked)
btn_del_festivo.on_click(on_del_festivo_clicked)

def on_guardar_horario_ci_clicked(b):
    anio = dd_ci_horario_anio.value
    ci = dd_ci_horario_centro.value
    if anio not in HORARIOS_CI_ANUAL:
        HORARIOS_CI_ANUAL[anio] = HORARIOS_CI_DEFAULT[2026].copy()

    HORARIOS_CI_ANUAL[anio][ci] = {
        'horario': txt_horario_texto.value,
        'h_sem': txt_horario_sem.value,
        'obs': txt_horario_obs.value
    }
    guardar_horarios_ci_drive()
    renderizar_horarios_ci()
    print(f"✅ Horario de {ci} para el año {anio} actualizado correctamente.")

btn_guardar_horario_ci.on_click(on_guardar_horario_ci_clicked)

def on_guardar_hld_anual_clicked(b):
    anio = dd_hld_anio.value
    ci = dd_hld_centro.value
    valor = txt_hld_valor_asig.value

    if anio not in HLD_ANUAL_POR_ANIO:
        HLD_ANUAL_POR_ANIO[anio] = HLD_ANUAL_DEFAULT[2026].copy()

    HLD_ANUAL_POR_ANIO[anio][ci] = float(valor)
    guardar_hld_anual_drive()
    renderizar_hld_gestion()
    actualizar_saldo_tiempo_real()
    renderizar_resumen()
    print(f"✅ Configuración HLD actualizada: {ci} tendrá {valor}h para el año {anio}.")

btn_guardar_hld_anual.on_click(on_guardar_hld_anual_clicked)

def on_exportar_clicked(b):
    anio = dd_anio.value
    mes_num = dd_mes.value
    mes_nom = MESES[mes_num]
    num_dias = calendar.monthrange(anio, mes_num)[1]
    ruta_excel = f'Informe_Calendario_{mes_nom}_{anio}.xlsx'

    with pd.ExcelWriter(ruta_excel, engine='openpyxl') as writer:
        datos_resumen = []
        for tec, info in TECNICOS.items():
            hld_totales_tecnico = obtener_hld_totales_tecnico(tec, anio)
            vpa_totales_tecnico = obtener_vpa_totales_tecnico(tec, anio)
            vac_cons = 0
            vpa_cons = 0
            hld_cons = 0.0
            for key, val in REGISTROS.items():
                parts = key.split('|') if isinstance(key, str) else None
                if parts and len(parts) == 4:
                    a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
                elif isinstance(key, tuple) and len(key) == 4:
                    a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
                else:
                    continue
                if a == anio and t == tec:
                    marca_str = val['tipo'] if isinstance(val, dict) else val
                    if marca_str == 'V': vac_cons += 1
                    elif marca_str == 'VPA': vpa_cons += 1
                    elif marca_str == 'HLD':
                        if isinstance(val, dict):
                            hld_cons += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, anio))
                        else:
                            hld_cons += obtener_horas_hld(tec, m, d, anio)

            he_comp = calcular_he_compensadas_totales(tec, anio)
            he_gast = calcular_he_consumidas_horas(tec, anio)

            datos_resumen.append({
                'Centro (CI)': info['ci'], 'Técnico': tec,
                'Vac. Cons.': vac_cons, 'Vac. Pend.': info['vac_totales'] - vac_cons,
                'VPA Cons.': vpa_cons, 'VPA Pend.': vpa_totales_tecnico - vpa_cons,
                'HLD Cons. (h)': round(hld_cons, 2), 'HLD Pend. (h)': round(hld_totales_tecnico - hld_cons, 2),
                'HE Comp. (h)': he_comp, 'HE Disp. (h)': round(he_comp - he_gast, 2)
            })
        pd.DataFrame(datos_resumen).to_excel(writer, sheet_name='Balance Saldos', index=False)

        filas_cuadrante = []
        for tec, info in TECNICOS.items():
            fila = {'Técnico': tec, 'Centro (CI)': info['ci']}
            for d in range(1, num_dias + 1):
                val_reg = REGISTROS.get((anio, tec, str(mes_num), str(d)), REGISTROS.get(f"{anio}|{tec}|{mes_num}|{d}", ''))
                marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
                if isinstance(val_reg, dict) and marca in ['HE', 'HLD']:
                    h_g = val_reg.get('horas_gastadas', 0.0)
                    fila[f'Día {d}'] = f"{marca} ({h_g}h)"
                else:
                    fila[f'Día {d}'] = marca
            filas_cuadrante.append(fila)
        pd.DataFrame(filas_cuadrante).to_excel(writer, sheet_name=f'Cuadrante {mes_nom}', index=False)

    from google.colab import files
    files.download(ruta_excel)
    with out_alertas:
        clear_output()
        print(f"📥 Excel '{ruta_excel}' generado con éxito.")

btn_exportar.on_click(on_exportar_clicked)

def on_exportar_html_clicked(b):
    anio = dd_anio.value
    fecha_actual_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    html_leyenda = f"""
    <div style='background-color: #F8F9FA; border: 1px solid #DCDCDC; border-radius: 6px; padding: 12px; margin-top: 20px; margin-bottom: 25px; font-family: sans-serif;'>
        <h4 style='margin: 0 0 8px 0; color: #002A3A; font-size: 14px;'>📖 Leyenda de Códigos y Estados</h4>
        <div style='display: flex; flex-wrap: wrap; gap: 8px;'>
    """
    for k, (desc, color) in LEYENDA.items():
        html_leyenda += f"""
        <div style='display: flex; align-items: center; background: white; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; font-size: 11px;'>
            <span style='background-color: {color}; border: 1px solid #999; width: 14px; height: 14px; display: inline-block; margin-right: 6px; border-radius: 2px;'></span>
            <b>{k}:</b>&nbsp;{desc}
        </div>
        """
    html_leyenda += "</div></div>"

    datos_resumen = []
    for tec, info in TECNICOS.items():
        hld_totales_tecnico = obtener_hld_totales_tecnico(tec, anio)
        vpa_totales_tecnico = obtener_vpa_totales_tecnico(tec, anio)
        vac_cons = 0
        vpa_cons = 0
        hld_cons = 0.0
        for key, val in REGISTROS.items():
            parts = key.split('|') if isinstance(key, str) else None
            if parts and len(parts) == 4:
                a, t, m, d = int(parts[0]), parts[1], int(parts[2]), int(parts[3])
            elif isinstance(key, tuple) and len(key) == 4:
                a, t, m, d = key[0], key[1], int(key[2]), int(key[3])
            else:
                continue
            if a == anio and t == tec:
                marca_str = val['tipo'] if isinstance(val, dict) else val
                if marca_str == 'V': vac_cons += 1
                elif marca_str == 'VPA': vpa_cons += 1
                elif marca_str == 'HLD':
                    if isinstance(val, dict):
                        hld_cons += val.get('horas_gastadas', obtener_horas_hld(tec, m, d, anio))
                    else:
                        hld_cons += obtener_horas_hld(tec, m, d, anio)

        he_comp = calcular_he_compensadas_totales(tec, anio)
        he_gast = calcular_he_consumidas_horas(tec, anio)

        datos_resumen.append({
            'Centro': info['ci'], 'Técnico': tec,
            'Vac. Cons.': vac_cons, 'Vac. Pend.': info['vac_totales'] - vac_cons,
            'VPA Cons.': vpa_cons, 'VPA Pend.': vpa_totales_tecnico - vpa_cons,
            'HLD Cons.': round(hld_cons, 2), 'HLD Pend.': round(hld_totales_tecnico - hld_cons, 2),
            'HE Comp.': he_comp, 'HE Disp.': round(he_comp - he_gast, 2)
        })
    tabla_resumen_html = pd.DataFrame(datos_resumen).to_html(index=False, classes='tabla-corporativa', border=0)

    dias_semana_abrev = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
    secciones_meses_html = ""
    for mes_num, mes_nom in MESES.items():
        num_dias = calendar.monthrange(anio, mes_num)[1]
        t_html = "<table class='tabla-corporativa tabla-detalle'><thead><tr><th>Técnico</th><th>Centro</th>"
        for d in range(1, num_dias + 1):
            weekday = calendar.weekday(anio, mes_num, d)
            t_html += f"<th>{d}<br><span style='font-size:9px; color:#ccc;'>{dias_semana_abrev[weekday]}</span></th>"
        t_html += "</tr></thead><tbody>"

        for tec, info in TECNICOS.items():
            t_html += f"<tr><td><b>{tec}</b></td><td>{info['ci']}</td>"
            festivos = FESTIVOS_POR_ANIO.get(anio, {}).get(info['ci'], [])
            for d in range(1, num_dias + 1):
                val_reg = REGISTROS.get((anio, tec, str(mes_num), str(d)), REGISTROS.get(f"{anio}|{tec}|{mes_num}|{d}", ''))
                marca = val_reg['tipo'] if isinstance(val_reg, dict) else val_reg
                bg_color = '#ffffff'
                weekday = calendar.weekday(anio, mes_num, d)
                if (mes_num, d) in festivos:
                    bg_color = LEYENDA['FEST'][1]
                    if not marca: marca = 'FEST'
                elif weekday >= 5:
                    bg_color = LEYENDA['SAB'][1] if weekday == 5 else LEYENDA['DOM'][1]
                    if not marca: marca = 'SAB' if weekday == 5 else 'DOM'
                elif marca in LEYENDA:
                    bg_color = LEYENDA[marca][1]

                etiqueta_celda = marca
                if marca == 'HLD' and isinstance(val_reg, dict):
                    h_g = val_reg.get('horas_gastadas', 0.0)
                    h_t = obtener_horas_hld(tec, mes_num, d, anio)
                    if h_g < h_t:
                        etiqueta_celda = f"HLD*"
                elif marca == 'HE' and isinstance(val_reg, dict):
                    etiqueta_celda = f"HE*"

                t_html += f"<td style='background-color: {bg_color}; text-align: center;'><b>{etiqueta_celda}</b></td>"
            t_html += "</tr>"
        t_html += "</tbody></table>"
        secciones_meses_html += f"<div class='mes-container'><h3>📅 Mes: {mes_nom} {anio}</h3><div class='table-responsive'>{t_html}</div></div>"

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>Calendario SAT CI Repsol - {anio}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #F4F6F8; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1400px; margin: auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ color: #002A3A; border-bottom: 3px solid #005B7F; padding-bottom: 10px; font-size: 22px; margin-bottom: 5px; }}
        .fecha-generacion {{ font-size: 12px; color: #666; margin-bottom: 20px; }}
        h2 {{ color: #005B7F; margin-top: 30px; font-size: 18px; border-left: 4px solid #005B7F; padding-left: 10px; }}
        .table-responsive {{ overflow-x: auto; }}
        table.tabla-corporativa {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; text-align: left; white-space: nowrap; }}
        table.tabla-corporativa th {{ background-color: #002A3A; color: white; padding: 8px; text-align: center; }}
        table.tabla-corporativa td {{ padding: 6px; border: 1px solid #ddd; }}
        .filtro-container {{ margin: 20px 0; }}
        .filtro-container input {{ padding: 8px; width: 320px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Calendario SAT CI Repsol - {anio}</h1>
        <div class="fecha-generacion">Fecha de generación: <b>{fecha_actual_str}</b></div>
        {html_leyenda}

        <div class="filtro-container">
            <input type="text" id="inputFiltro" placeholder="🔍 Filtrar por Técnico o Centro (CI)..." onkeyup="filtrarTablas()">
        </div>

        <h2>📈 Balance Consolidado de Saldos</h2>{tabla_resumen_html}
        <h2>🗓️ Detalle de Cuadrantes por Meses</h2>{secciones_meses_html}
    </div>

    <script>
    function filtrarTablas() {{
        var input = document.getElementById("inputFiltro");
        var filtro = input.value.toLowerCase();
        var tablas = document.querySelectorAll("table.tabla-corporativa");

        tablas.forEach(function(tabla) {{
            var filas = tabla.getElementsByTagName("tr");
            for (var i = 1; i < filas.length; i++) {{
                var fila = filas[i];
                var textoFila = fila.textContent || fila.innerText;
                if (textoFila.toLowerCase().indexOf(filtro) > -1) {{
                    fila.style.display = "";
                }} else {{
                    fila.style.display = "none";
                }}
            }}
        }});
    }}
    </script>
</body>
</html>"""
    nombre_archivo = f"Calendario_SAT_CI_Repsol_{anio}.html"
    with open(nombre_archivo, 'w', encoding='utf-8') as f: f.write(html_template)
    from google.colab import files
    files.download(nombre_archivo)

btn_exportar_html.on_click(on_exportar_html_clicked)

dd_anio.observe(lambda c: (renderizar_pantalla(), renderizar_resumen(), renderizar_cobertura(), renderizar_incidencias()), names='value')
dd_vista.observe(lambda c: renderizar_pantalla(), names='value')
dd_tecnico.observe(lambda c: renderizar_pantalla(), names='value')
dd_mes.observe(lambda c: renderizar_pantalla(), names='value')
fecha_cobertura.observe(lambda c: renderizar_cobertura(), names='value')
dd_ci_horario_anio.observe(lambda c: renderizar_horarios_ci(), names='value')
dd_hld_anio.observe(lambda c: renderizar_hld_gestion(), names='value')

# 6. ESTRUCTURA DE PESTAÑAS PRINCIPALES (TABS)
pestanas = widgets.Tab()

seccion_gestion = widgets.VBox([
    widgets.HTML("<h3 style='color:#002A3A;'>📝 Registro de Calendarios y Ausencias</h3>"),
    widgets.HBox([dd_anio, dd_tecnico, dd_mes]),
    widgets.HBox([dd_dia_inicio, dd_dia_fin, dd_tipo]),
    widgets.HBox([dd_horas_disfrute, btn_guardar]),
    out_saldo_tiempo_real,
    out_alertas,
    out_calendario
])

seccion_he = widgets.VBox([
    widgets.HTML("<h3 style='color:#002A3A;'>⚡ Gestión y Acumulación de Horas Extra</h3>"),
    widgets.HTML("<p style='font-size:12px;'>Añade las horas reales trabajadas. Se multiplicarán automáticamente por 1.75 (equivalente a 1h 45min).</p>"),
    widgets.HBox([dd_he_anio, dd_he_tecnico]),
    widgets.HBox([txt_he_horas, txt_he_motivo, btn_he_agregar]),
    out_he_gestion,
    widgets.HTML("<br><b>Historial de Horas Extra registradas para este técnico:</b>"),
    widgets.HBox([dd_he_historial, btn_he_eliminar])
])

seccion_cobertura = widgets.VBox([widgets.HBox([fecha_cobertura]), out_cobertura])
seccion_balance = widgets.VBox([out_resumen])
seccion_incidencias = widgets.VBox([out_incidencias])
seccion_auditoria = widgets.VBox([out_auditoria])
seccion_config = widgets.VBox([
    out_config,
    widgets.HTML("<hr style='margin:15px 0;'>"),
    widgets.HTML("<h4 style='color:#002A3A;'>🗓️ Gestión Interactiva de Festivos por Centro</h4>"),
    widgets.HBox([dd_cfg_anio, dd_cfg_centro]),
    widgets.HBox([dd_cfg_mes, dd_cfg_dia, btn_add_festivo]),
    widgets.HTML("<br><b>Festivos actuales registrados para este centro:</b>"),
    widgets.HBox([dd_festivos_actuales, btn_del_festivo])
])

seccion_horarios = widgets.VBox([
    out_horarios_ci,
    widgets.HTML("<hr style='margin:15px 0;'>"),
    widgets.HTML("<h4 style='color:#002A3A;'>⚙️ Modificar Horario de CI por Año</h4>"),
    widgets.HBox([dd_ci_horario_anio, dd_ci_horario_centro]),
    widgets.HBox([txt_horario_texto, txt_horario_sem]),
    widgets.HBox([txt_horario_obs, btn_guardar_horario_ci])
])

seccion_hld = widgets.VBox([
    out_hld_gestion,
    widgets.HTML("<hr style='margin:15px 0;'>"),
    widgets.HTML("<h4 style='color:#002A3A;'>⚙️ Configurar Total de HLD por Centro y Año</h4>"),
    widgets.HBox([dd_hld_anio, dd_hld_centro]),
    widgets.HBox([txt_hld_valor_asig, btn_guardar_hld_anual])
])

pestanas.children = [seccion_gestion, seccion_he, seccion_cobertura, seccion_balance, seccion_incidencias, seccion_auditoria, seccion_config, seccion_horarios, seccion_hld]
pestanas.set_title(0, '🛠️ Registrar')
pestanas.set_title(1, '⚡ Horas Extra')
pestanas.set_title(2, '👥 Cobertura')
pestanas.set_title(3, '📈 Balance')
pestanas.set_title(4, '⚠️ Incidencias')
pestanas.set_title(5, '📋 Auditoría')
pestanas.set_title(6, '⚙️ Configuración')
pestanas.set_title(7, '⏰ Horarios / CI')
pestanas.set_title(8, '⏳ Config. HLD')

display(widgets.VBox([
    widgets.HTML("<h2 style='color:#005B7F; margin:0;'>Cuadrante de Calendarios Técnicos - SAT CI REPSOL</h2>"),
    widgets.HBox([dd_vista, btn_exportar, btn_exportar_html]),
    pestanas
]))

# Inicializar vistas
poblar_he_panel()
actualizar_saldo_tiempo_real()
renderizar_pantalla()
renderizar_resumen()
renderizar_cobertura()
renderizar_incidencias()
renderizar_auditoria()
renderizar_config()
renderizar_horarios_ci()
renderizar_hld_gestion()
actualizar_dias_cfg(None)
