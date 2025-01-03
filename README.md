# scapper_e_evirtual

## Descripción 📄

El proyecto **scapper_e_evirtual** es una herramienta automatizada para la extracción de datos de cursos en la plataforma eVirtual de la Universidad Técnica de Manabí (UTM). Utiliza la biblioteca Playwright para automatizar la navegación en el navegador y BeautifulSoup para el análisis del contenido HTML.

## Funcionalidades 🚀

- **Inicio de sesión automático** 🔐: Inicia sesión en la plataforma eVirtual utilizando credenciales almacenadas de manera segura.
- **Extracción de datos de estudiantes** 🎓: Navega a la página del curso especificado y extrae información de los estudiantes, incluyendo nombres y correos electrónicos.
- **Validación de URL** 🔍: Verifica que la URL del curso ingresada por el usuario tenga el formato correcto.
- **Manejo de errores** ⚠️: Gestiona errores comunes, como la ausencia del botón para mostrar más estudiantes.
- **Progreso dinámico** 📊: Muestra el progreso de la extracción de datos en la consola, indicando el número de estudiantes procesados y el porcentaje completado.

## Cómo usarlo 🛠️

1. **Configurar credenciales**: Asegúrate de tener un archivo `credenciales.data` con tu correo y contraseña en la misma carpeta que el script.
2. **Ejecutar el script**: Ejecuta el script `scapper_course_data.py` y sigue las instrucciones en la consola para ingresar la URL del curso.
3. **Ver el progreso**: Observa el progreso de la extracción de datos directamente en la consola.

## Requisitos 📋

- Python 3.x
- Playwright
- BeautifulSoup
- Un navegador compatible (Microsoft Edge)

## Instalación 🔧

1. Clona este repositorio:
    ```sh
    git clone https://github.com/tu_usuario/scapper_e_evirtual.git
    ```
2. Instala las dependencias:
    ```sh
    pip install playwright beautifulsoup4
    ```
3. Configura Playwright:
    ```sh
    playwright install
    ```

## Contribuciones 🤝

¡Las contribuciones son bienvenidas! Si deseas mejorar este proyecto, por favor abre un issue o envía un pull request.

## Licencia 📄

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.
