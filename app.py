import streamlit as st

# Supongamos que estas variables vienen de tu estado o base de datos actual
# vac_pend = saldo disponible actual de vacaciones
# reg_tipo = tipo de ausencia seleccionada ('V' para vacaciones, etc.)
# reg_d_ini y reg_d_fin = fechas de inicio y fin del registro

st.subheader("Registro de Ausencias y Vacaciones")

# Ejemplo de inputs para simular la interfaz
reg_tipo = st.selectbox("Tipo de registro", ["V", "Permiso", "Enfermedad"])
reg_d_ini = 1
reg_d_fin = 5
vac_pend = 3  # Días disponibles de ejemplo

# Inicializamos la variable de control
guardar_permitido = True

# Lógica de validación
if reg_tipo == 'V':
    dias_a_registrar = (reg_d_fin - reg_d_ini) + 1
    if dias_a_registrar > vac_pend:
        st.error(f"❌ Error de saldo: Intentas registrar {dias_a_registrar} días de vacaciones, pero solo te quedan {vac_pend} días disponibles. No se permite saldo negativo.")
        guardar_permitido = False

# Botón de guardado condicionado
if st.button("Guardar Registro"):
    if guardar_permitido:
        # Aquí iría tu código para guardar en la base de datos o session_state
        st.success("¡Registro guardado exitosamente!")
    else:
        st.warning("No se pudo guardar el registro debido a un error de validación de saldo.")
