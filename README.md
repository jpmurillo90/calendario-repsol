# Gestión Técnicos CI — v19 EmployeeHub

Rediseño global de la aplicación Streamlit original v17.5.

## Instalación
1. Copia `app.py` y la carpeta `frontend/` a tu repositorio actual.
2. **Conserva todos los JSON**, el logo `AF_INDRA_SIM_POS.png` y tus Secrets de Streamlit Cloud.
3. Instala dependencias de `requirements.txt` y ejecuta `streamlit run app.py`.
4. Prueba en una rama o despliegue independiente antes de publicar.

## Qué se ha cambiado
- Sistema visual EmployeeHub global, menú oscuro, botones, formularios, tablas, fichas, diálogos, tarjetas y responsive.
- Dashboard con gráfico HTML de disponibilidad calculado desde la lógica Python original.
- Los módulos existentes siguen siendo Streamlit; no se ha creado una API ni migrado a frontend JavaScript independiente.

## Qué se ha conservado
- Autenticación y roles existentes, reglas de negocio, solicitudes, PRL, guardias, cuadrante, seguimiento CI y reportes.
- Persistencia JSON local / GitHub Gist según configuración. No se incluyen credenciales ni datos personales en este paquete.

## Limitaciones
- No se ha ejecutado una prueba funcional completa con tus datos y Secrets.
- El Gist existente no admite escrituras transaccionales simultáneas.
- El HTML original de tu compañero no se incrusta tal cual: contenía almacenamiento local y contraseñas del lado del cliente. El estilo se ha reconstruido para la app existente.
