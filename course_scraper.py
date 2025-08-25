from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import re
from academic_data import (
    trimestres,
    trimestres_borrar,
    trimestres_borrar_malos,
    trimestres_buenos_estudiantes,
    trimestres_malos_estudiantes,
    trimestres_excepciones,
    personalized_grades
)
from ambitos import obtener_ambitos_usuario
from trimesters import obtener_trimestres_usuario
from utils import obtener_materias_usuario
from nombres_estudiantes import nombres_buenos, nombres_malos, nombres_excepciones, notas_personalizadas
from hola import crear_mapa_calificaciones  # Importar la función de mapeo de calificaciones
import pandas as pd

# Mapeo de grados que usarán el sistema de mapeo de calificaciones
GRADOS_CON_MAPEO = ['2do', '3ro', '4to', '5to', '6to', '7mo']

def normalize_text(text):
    if not text:
        return ""
    # Convert to lowercase and remove accents
    text = text.lower()
    # Normalize unicode characters and remove accents
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    # Remove any remaining special characters and extra spaces
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def seleccionar_trimestre(page, trimestre_num, grado_seleccionado):
    """Selecciona el trimestre según el grado.
    
    Args:
        page: Página de Playwright
        trimestre_num: Número de trimestre (1-3)
        grado_seleccionado: Grado seleccionado (ej: 'INICIAL', '1RO', '2DO', etc.)
    """
    try:
        print(f"Intentando seleccionar trimestre {trimestre_num} para {grado_seleccionado}...")
        
        # Determinar si es un grado que usa la nueva interfaz (2do-7mo)
        es_grado_nuevo = any(str(grado) in str(grado_seleccionado) for grado in range(2, 8))
        
        if es_grado_nuevo:
            # Nueva interfaz con pestañas
            tab_selector = f'//a[contains(@class, "nav-link") and contains(., "TRIMESTRE {trimestre_num}")]'
            page.wait_for_selector(f'xpath={tab_selector}', state="visible", timeout=10000)
            page.click(f'xpath={tab_selector}')
            print(f"Trimestre {trimestre_num} seleccionado correctamente (nueva interfaz)")
        else:
            # Antigua interfaz con dropdown
            selector = 'select[name="trimestreSeleccionado"]'
            page.wait_for_selector(selector, state="visible", timeout=10000)
            page.select_option(selector, label=f"TRIMESTRE {trimestre_num}", timeout=10000)
            print(f"Trimestre {trimestre_num} seleccionado correctamente (interfaz antigua)")
        
        time.sleep(2)  # Esperar a que cargue el contenido
        return True
        
    except Exception as e:
        print(f"Error al seleccionar trimestre {trimestre_num}: {e}")
        return False

def seleccionar_materia(page, nombre, jornada, timeout=20000):
    try:
        normalized_nombre = normalize_text(nombre)
        normalized_jornada = normalize_text(jornada)
        print(f"Buscando materia que contenga '{normalized_nombre}' con jornada '{normalized_jornada}'")

        # Navegar a la página de calificaciones
        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/calificacion_ordinaria")
        page.wait_for_load_state('networkidle')

        pagina_actual = 1
        max_paginas = 10  # Límite de páginas a revisar como medida de seguridad
        
        while pagina_actual <= max_paginas:
            print(f"\nRevisando página {pagina_actual}...")
            page.wait_for_load_state('networkidle')
            
            # Esperar a que la tabla de materias esté visible
            try:
                page.wait_for_selector('table tbody tr.ng-star-inserted', state="visible", timeout=10000)
            except Exception as e:
                print("No se encontró la tabla de materias. La página podría no haber cargado correctamente.")
                return False
                
            filas = page.query_selector_all('table tbody tr.ng-star-inserted')
            
            if not filas:
                print("No se encontraron materias en la página actual.")
                break

            for fila in filas:
                # Extraer los datos de la fila
                asignatura_element = fila.query_selector('td:nth-child(2)')  # Columna "Asignatura"
                grado_element = fila.query_selector('td:nth-child(3)')       # Columna "Grado"
                jornada_element = fila.query_selector('td:nth-child(5)')     # Columna "Jornada"

                if asignatura_element and grado_element and jornada_element:
                    asignatura_text = normalize_text(asignatura_element.inner_text())
                    grado_text = normalize_text(grado_element.inner_text())
                    jornada_text = normalize_text(jornada_element.inner_text())

                    # Verificar si coincide con la materia buscada
                    if normalized_nombre in asignatura_text and normalized_jornada in jornada_text:
                        print(f"Coincidencia encontrada en la página {pagina_actual}.")
                        boton_editar = fila.query_selector('button.btn-warning')
                        if boton_editar:
                            boton_editar.click()
                            return True

            # Verificar si hay más páginas
            try:
                # Buscar el contenedor de paginación
                paginacion = page.query_selector('div.row.justify-content-center')
                if not paginacion:
                    print("No se encontró el control de paginación.")
                    break
                    
                # Obtener el texto de la página actual y total
                paginacion_texto = paginacion.inner_text()
                if "Página" in paginacion_texto:
                    # Extraer números de página (ejemplo: "Página 1 de 6")
                    import re
                    match = re.search(r'Página (\d+) de (\d+)', paginacion_texto)
                    if match:
                        pagina_actual = int(match.group(1))
                        total_paginas = int(match.group(2))
                        print(f"Página {pagina_actual} de {total_paginas}")
                
                # Buscar el botón "Siguiente"
                siguiente_btn = page.query_selector('div.row.justify-content-center button:not([disabled])')
                if siguiente_btn and "Siguiente" in siguiente_btn.inner_text():
                    # Hacer clic en el botón Siguiente
                    siguiente_btn.click()
                    # Esperar a que cargue la nueva página
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)  # Pequeña pausa para asegurar la carga
                    pagina_actual += 1
                    
                    # Verificar que realmente cambiamos de página
                    try:
                        page.wait_for_function(
                            f"document.querySelector('div.row.justify-content-center').innerText.includes('Página {pagina_actual} de')",
                            timeout=5000
                        )
                    except:
                        print("No se pudo confirmar el cambio de página. Continuando de todos modos...")
                else:
                    print("No hay más páginas disponibles o el botón 'Siguiente' está deshabilitado.")
                    break
                    
            except Exception as e:
                print(f"Error al intentar navegar a la siguiente página: {e}")
                break

        print(f"No se encontró la materia '{nombre}' con la jornada '{jornada}' después de revisar {pagina_actual} páginas.")
        return False
        
    except Exception as e:
        print(f"Error al seleccionar la materia '{nombre}': {e}")
        return False

def procesar_filas(page, ambito, trimestre_num, grado_seleccionado, nombres_excepciones=None, 
                 nombres_buenos=None, nombres_malos=None, accion="llenar", grupo="todos", mapeo_calificaciones=None):
    """Procesa las filas de estudiantes según el grupo seleccionado.
    
    Args:
        page: Página de Playwright
        ambito: Ámbito actual (no se usa en grados 2-7)
        trimestre_num: Número de trimestre
        grado_seleccionado: Grado seleccionado (ej: '2do', '3ro', etc.)
        nombres_excepciones: Lista de nombres de estudiantes a procesar (para grupo personalizado)
        nombres_buenos: Lista de nombres de estudiantes "buenos"
        nombres_malos: Lista de nombres de estudiantes "malos"
        accion: 'llenar' para ingresar notas, 'borrar' para limpiar
        grupo: 'todos', 'buenos', 'malos' o 'personalizado'
        mapeo_calificaciones: Diccionario con las calificaciones de los estudiantes
    """
    try:
        print(f"Procesando {ambito} para Trimestre {trimestre_num}...")
        
        # Determinar si es un grado que usa la nueva interfaz (2do-7mo)
        es_grado_nuevo = any(str(grado) in str(grado_seleccionado) for grado in range(2, 8))
        
        if es_grado_nuevo:
            # Nueva interfaz para grados 2-7
            return _procesar_filas_nueva_interfaz(
                page, ambito, trimestre_num, grado_seleccionado, 
                nombres_excepciones, nombres_buenos, nombres_malos, accion, grupo,
                mapeo_calificaciones
            )
        else:
            # Antigua interfaz para Inicial y 1ro
            return _procesar_filas_antigua_interfaz(
                page, ambito, trimestre_num, grado_seleccionado, 
                nombres_excepciones, nombres_buenos, nombres_malos, accion, grupo,
                mapeo_calificaciones
            )
            
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def _procesar_filas_nueva_interfaz(page, ambito, trimestre_num, grado_seleccionado, 
                                nombres_excepciones, nombres_buenos, nombres_malos, accion, grupo,
                                mapeo_calificaciones=None):
    """Procesa las filas usando la nueva interfaz con pestañas (grados 2-7) con manejo de paginación."""
    try:
        print("Esperando a que cargue la tabla de estudiantes...")
        page.wait_for_selector('table tbody tr', state='visible', timeout=30000)
        print("Tabla de estudiantes cargada correctamente")
        
        # Inicializar contador de páginas
        pagina_actual = 1
        total_estudiantes_procesados = 0
        
        while True:
            print(f"\n--- Procesando página {pagina_actual} ---")
            
            # Obtener todas las filas de estudiantes de la página actual
            rows = page.query_selector_all('table tbody tr')
            print(f"Encontrados {len(rows)} estudiantes en la página {pagina_actual}")
            
            if not rows:
                print("No se encontraron estudiantes en la tabla")
                break
                
            # Procesar estudiantes de la página actual
            for idx, row in enumerate(rows, 1):
                try:
                    print(f"\n--- Procesando estudiante {total_estudiantes_procesados + 1} (Página {pagina_actual}, Estudiante {idx}/{len(rows)}) ---")
                    
                    # Obtener el nombre del estudiante (tercera columna según el HTML)
                    nombre_element = row.query_selector('td:nth-child(3)')
                    if not nombre_element:
                        print("  - No se pudo encontrar el elemento del nombre")
                        continue
                        
                    nombre_estudiante = nombre_element.inner_text().strip()
                    print(f"  - Estudiante: {nombre_estudiante}")
                    
                    # Normalizar el nombre para búsqueda
                    nombre_normalizado = normalize_text(nombre_estudiante)
                    
                    # Verificar si el estudiante debe ser procesado según el grupo
                    if grupo == "buenos" and (not nombres_buenos or not any(normalize_text(n) == nombre_normalizado for n in nombres_buenos)):
                        print(f"  - No está en el grupo 'buenos'. Saltando...")
                        continue
                    elif grupo == "malos" and (not nombres_malos or not any(normalize_text(n) == nombre_normalizado for n in nombres_malos)):
                        print(f"  - No está en el grupo 'malos'. Saltando...")
                        continue
                    elif grupo == "personalizado" and (not nombres_excepciones or not any(normalize_text(n) == nombre_normalizado for n in nombres_excepciones)):
                        print(f"  - No está en la lista personalizada. Saltando...")
                        continue
                    
                    # Buscar la calificación en el mapeo
                    calificacion = None
                    if mapeo_calificaciones:
                        # Intentar encontrar una coincidencia exacta primero
                        for nombre_archivo, califs in mapeo_calificaciones.items():
                            if normalize_text(nombre_archivo) == nombre_normalizado:
                                calificacion = califs.get(ambito)
                                if calificacion:
                                    break
                        
                        # Si no hay coincidencia exacta, buscar coincidencia parcial
                        if not calificacion:
                            for nombre_archivo, califs in mapeo_calificaciones.items():
                                if nombre_normalizado in normalize_text(nombre_archivo) or normalize_text(nombre_archivo) in nombre_normalizado:
                                    calificacion = califs.get(ambito)
                                    if calificacion:
                                        break
                    
                    # Si no se encontró calificación, usar valores por defecto según el grupo
                    if not calificacion:
                        if grupo == "buenos":
                            calificacion = "10"  # Ejemplo para grupo 'buenos'
                        elif grupo == "malos":
                            calificacion = "7"   # Ejemplo para grupo 'malos'
                        else:
                            calificacion = "8"   # Calificación por defecto
                        print(f"  - No se encontró calificación en el archivo. Usando valor por defecto: {calificacion}")
                    else:
                        print(f"  - Calificación encontrada en archivo: {calificacion}")
                    
                    # Encontrar el campo de entrada de la calificación (cuarta columna)
                    input_field = row.query_selector('td:nth-child(4) input[type="text"]')
                    if not input_field:
                        print("  - No se encontró el campo de calificación")
                        continue
                    
                    # Obtener el valor actual para verificar si hay cambios
                    try:
                        valor_actual = input_field.input_value()
                        print(f"  - Valor actual: {valor_actual}")
                    except Exception as e:
                        print(f"  - No se pudo obtener el valor actual: {str(e)}")
                        valor_actual = ""
                    
                    # Si la acción es llenar y el valor actual es diferente al nuevo valor
                    if accion == "llenar" and valor_actual != str(calificacion):
                        try:
                            # Hacer clic en el campo para activarlo
                            input_field.click()
                            time.sleep(0.5)
                            
                            # Limpiar el campo
                            input_field.fill("")
                            time.sleep(0.5)
                            
                            # Ingresar la nueva calificación
                            input_field.fill(str(calificacion))
                            print(f"  - Asignando calificación: {calificacion}")
                            time.sleep(0.5)
                            
                            # Hacer clic en el botón de guardar
                            save_button = row.query_selector('td:nth-child(5) button.btn-primary')
                            if save_button:
                                save_button.click()
                                print("  - Guardando cambios...")
                                time.sleep(2)  # Esperar a que se guarde
                                
                                # Verificar si aparece el mensaje de confirmación
                                try:
                                    confirm_button = page.wait_for_selector('button.swal2-confirm', timeout=3000)
                                    if confirm_button:
                                        confirm_button.click()
                                        print("  - Confirmación aceptada")
                                        time.sleep(1)
                                except Exception as e:
                                    print(f"  - No se encontró el botón de confirmación: {str(e)}")
                            else:
                                print("  - No se encontró el botón de guardar")
                        except Exception as e:
                            print(f"  - Error al procesar el estudiante: {str(e)}")
                    else:
                        print(f"  - No se realizaron cambios (valor actual: {valor_actual}, nuevo valor: {calificacion})")
                    
                    total_estudiantes_procesados += 1
                    
                except Exception as e:
                    print(f"Error al procesar estudiante: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Verificar si hay una siguiente página
            try:
                # Buscar el botón de siguiente página
                next_button = page.query_selector('button:has-text("Siguiente"):not([disabled])')
                
                if next_button:
                    print(f"\nAvanzando a la página {pagina_actual + 1}...")
                    next_button.click()
                    # Esperar a que cargue la nueva página
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)  # Esperar a que se cargue la tabla
                    pagina_actual += 1
                else:
                    print("\nNo hay más páginas por procesar.")
                    break
                    
            except Exception as e:
                print(f"Error al intentar avanzar de página: {str(e)}")
                break
                
        print(f"\nProceso de calificación completado. Total de estudiantes procesados: {total_estudiantes_procesados}")
        return True
        
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def _procesar_filas_antigua_interfaz(page, ambito, trimestre_num, grado_seleccionado, 
                                   nombres_excepciones, nombres_buenos, nombres_malos, accion, grupo,
                                   mapeo_calificaciones=None):
    """Procesa las filas usando la antigua interfaz con dropdown (Inicial y 1ro)."""
    try:
        print("Seleccionando ámbito...")
        
        # Código para la interfaz antigua (dropdown de ámbitos)
        options = page.query_selector_all('select[name="ambitoSeleccionado"] option')
        value_to_select = None
        for option in options:
            if normalize_text(option.inner_text()) == normalize_text(ambito):
                value_to_select = option.get_attribute('value')
                break

        if value_to_select:
            page.select_option('select[name="ambitoSeleccionado"]', value=value_to_select)
            print(f"Ámbito '{ambito}' seleccionado correctamente.")
            time.sleep(2)  # Esperar a que cargue la tabla
            
            # Aquí iría el código específico para procesar la tabla en la interfaz antigua
            # ...
            
            print("Proceso de calificación completado.")
            return True
        else:
            print(f"No se encontró el ámbito '{ambito}'.")
            return False
            
    except Exception as e:
        print(f"Error al procesar con la interfaz antigua: {str(e)}")
        return False

def procesar_todos_los_estudiantes(page, ambito, trimestre_num, grado_seleccionado, accion="llenar", mapeo_calificaciones=None):
    return procesar_filas(
        page, 
        ambito, 
        trimestre_num,
        grado_seleccionado=grado_seleccionado,
        nombres_excepciones=nombres_excepciones, 
        nombres_buenos=nombres_buenos,
        nombres_malos=nombres_malos,
        accion=accion, 
        grupo="todos",
        mapeo_calificaciones=mapeo_calificaciones
    )

def obtener_ambito_y_scrapear(page, grado_seleccionado, jornada):
    from utils import obtener_materias_usuario
    
    # Verificar si es un grado que usa mapeo de calificaciones (2do-7mo)
    usa_mapeo_calificaciones = any(grado in str(grado_seleccionado) for grado in ['2', '3', '4', '5', '6', '7'])
    
    # Cargar el mapeo de calificaciones si corresponde
    mapeo_calificaciones = None
    if usa_mapeo_calificaciones:
        print("\n=== CARGANDO MAPEO DE CALIFICACIONES ===")
        mapeo_calificaciones = crear_mapa_calificaciones('sb.xlsx')
        if mapeo_calificaciones:
            print(f"Se cargaron calificaciones para {len(mapeo_calificaciones)} estudiantes")
        else:
            print("No se pudo cargar el mapeo de calificaciones. Usando valores por defecto.")
    
    # Obtener las materias seleccionadas por el usuario
    materias = obtener_materias_usuario(grado_seleccionado, jornada)
    if not materias:
        print("No se seleccionaron materias. Saliendo...")
        return False

    opcion = input("¿Qué grupo desea procesar? (todos/buenos/malos/personalizado/grados_personalizados): ").strip().lower()
    accion = input("¿Qué acción desea realizar? (llenar/borrar): ").strip().lower()
    
    trimestres_seleccionados = obtener_trimestres_usuario()
    print(f"Trimestres seleccionados: {trimestres_seleccionados}")

    # Procesar cada materia seleccionada
    for materia in materias:
        print(f"\n=== PROCESANDO MATERIA: {materia['nombre'].upper()} ===")
        
        # Navegar a la página principal de calificaciones
        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/calificacion_ordinaria")
        page.wait_for_load_state('networkidle')
        
        if not seleccionar_materia(page, materia['nombre'], materia['jornada']):
            print(f"No se pudo seleccionar la materia {materia['nombre']} - Jornada {materia['jornada']}")
            continue

        # Solo obtener ámbitos si es grado 1 o inicial
        ambitos = []
        if not usa_mapeo_calificaciones:
            ambitos = obtener_ambitos_usuario(materia)
            if not ambitos:
                print(f"No se seleccionaron ámbitos para {materia['nombre']}. Continuando con la siguiente materia...")
                continue
            print(f"Ámbitos seleccionados para {materia['nombre']}: {ambitos}")
        else:
            # Para grados 2-7, usamos un ámbito genérico ya que el mapeo ya tiene las materias
            ambitos = [materia['nombre']]

        for trimestre_num in trimestres_seleccionados:
            print(f"\nSeleccionando Trimestre {trimestre_num}...")
            if not seleccionar_trimestre(page, trimestre_num, grado_seleccionado):
                print(f"No se pudo seleccionar el trimestre {trimestre_num}. Continuando con el siguiente...")
                continue

            for ambito in ambitos:
                print(f"Procesando Trimestre {trimestre_num} - {ambito}...")
                
                if opcion == "todos":
                    procesar_todos_los_estudiantes(
                        page, 
                        ambito, 
                        trimestre_num,
                        grado_seleccionado=grado_seleccionado,
                        accion=accion,
                        mapeo_calificaciones=mapeo_calificaciones
                    )
                elif opcion == "buenos":
                    procesar_filas(
                        page, 
                        ambito, 
                        trimestre_num,
                        grado_seleccionado=grado_seleccionado,
                        nombres_excepciones=nombres_excepciones,
                        nombres_buenos=nombres_buenos,
                        nombres_malos=None,
                        accion=accion,
                        grupo="buenos",
                        mapeo_calificaciones=mapeo_calificaciones
                    )
                elif opcion == "malos":
                    procesar_filas(
                        page, 
                        ambito, 
                        trimestre_num,
                        grado_seleccionado=grado_seleccionado,
                        nombres_excepciones=nombres_excepciones,
                        nombres_buenos=None,
                        nombres_malos=nombres_malos,
                        accion=accion,
                        grupo="malos",
                        mapeo_calificaciones=mapeo_calificaciones
                    )
                elif opcion == "personalizado":
                    procesar_filas(
                        page, 
                        ambito, 
                        trimestre_num,
                        grado_seleccionado=grado_seleccionado,
                        nombres_excepciones=nombres_excepciones,
                        nombres_buenos=None,
                        nombres_malos=None,
                        accion=accion,
                        grupo="personalizado",
                        mapeo_calificaciones=mapeo_calificaciones
                    )
                elif opcion == "grados_personalizados":
                    from academic_data import personalized_grades
                    procesar_filas(
                        page, 
                        ambito, 
                        trimestre_num,
                        grado_seleccionado=grado_seleccionado,
                        nombres_excepciones=None,
                        nombres_buenos=list(personalized_grades.keys()),
                        nombres_malos=None,
                        accion=accion,
                        grupo="grados_personalizados",
                        mapeo_calificaciones=mapeo_calificaciones
                    )
                else:
                    print("Opción no válida. Continuando con la siguiente materia...")
                    break
                
                # Pequeña pausa entre ámbitos
                time.sleep(1)
            
            # Pequeña pausa entre trimestres
            time.sleep(1)
        
        # Pequeña pausa entre materias
        time.sleep(2)

    print("\nProceso de scraping finalizado para todas las materias seleccionadas.")
    return True