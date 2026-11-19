# Gestión Técnicos CI v20 — interfaz HTML real

Este proyecto parte íntegramente de `app (9)(1).py` (v17.5). No se han borrado las funciones ni módulos originales. El dashboard de Inicio (para Editor) se ha sustituido por un **componente HTML/JS real**, integrado mediante `streamlit.components.v1.declare_component`. El componente comunica los clics de navegación a Python; las demás pantallas siguen siendo las originales, sin migrar todavía a HTML.

## Instalación sin pérdida de datos

1. **No sobrescribas tu repositorio ni tus archivos JSON.** Haz una rama de pruebas, o un repositorio nuevo, con este `app.py`, `requirements.txt` y toda la carpeta `frontend/employeehub/`.
2. Copia también tu logo y los archivos JSON actuales al entorno de pruebas si usas almacenamiento local.
3. En Streamlit Cloud configura los Secrets de prueba. **No conectes el Gist de producción para pruebas de escritura**: usa una copia de tu Gist, o prueba en modo lectura sin editar.
4. Ejecuta `streamlit run app.py` o despliega la rama de pruebas.
5. Inicia sesión con tus usuarios habituales; la pantalla Inicio de Editor muestra el dashboard HTML y los botones navegan a los módulos Python existentes.

## Alcance real

- HTML/JS real para el dashboard, menú, tarjetas, gráfico y tabla, con valores obtenidos de Python.
- Autenticación y persistencia permanecen del lado Python, sin contraseñas ni datos guardados en el navegador.
- Los módulos originales de cuadrante, guardias, solicitudes, técnicos, PRL, etc. se conservan, **pero todavía no tienen interfaz HTML nueva**.
- No se ha podido ejecutar una prueba end-to-end con tus Secrets y datos reales; se ha verificado sintaxis Python y estructura del paquete.
- La página Inicio de rol Técnico conserva su pantalla original.

## Seguridad

No subas `.streamlit/secrets.toml` a GitHub. El archivo HTML del compañero se usa como referencia visual, no se han incorporado sus contraseñas ni su `localStorage`.
