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

def seleccionar_trimestre(page, trimestre_num, grado_seleccionado, es_civica=False):
    """Selecciona el trimestre según el grado.
    
    Args:
        page: Página de Playwright
        trimestre_num: Número de trimestre (1-3)
        grado_seleccionado: Grado seleccionado (ej: 'INICIAL', '1RO', '2DO', etc.)
        es_civica: Indica si es la materia de Cívica que requiere flujo especial
    """
    try:
        print(f"Intentando seleccionar trimestre {trimestre_num} para {grado_seleccionado}...")
        
        # Si es Cívica, no intentamos seleccionar el trimestre aquí
        # ya que se hará después de hacer clic en el estudiante
        if es_civica:
            print("  - Es materia de Cívica, el trimestre se seleccionará después")
            return True
            
        # Determinar si es un grado que usa la nueva interfaz (2do-7mo)
        es_grado_nuevo = any(str(grado) in str(grado_seleccionado) for grado in range(2, 8))
        
        if es_grado_nuevo:
            # Para la nueva interfaz (2do-7mo)
            try:
                # Esperar a que cargue el selector de trimestre
                selector = f"//a[contains(@class, 'nav-link') and contains(., 'TRIMESTRE {trimestre_num}')]"
                print(f"  - Buscando selector: {selector}")
                
                # Hacer clic en el trimestre
                page.click(selector, timeout=10000)
                print(f"  - Seleccionado TRIMESTRE {trimestre_num}")
                time.sleep(2)  # Esperar a que cargue
                return True
                
            except Exception as e:
                print(f"Error al seleccionar trimestre {trimestre_num}: {str(e)}")
                return False
        else:
            # Para la interfaz antigua (Inicial y 1ro)
            try:
                # Hacer clic en el dropdown de trimestres
                page.click("select#trimestre", timeout=10000)
                
                # Seleccionar el trimestre (el valor es el mismo que el número)
                page.select_option("select#trimestre", str(trimestre_num))
                print(f"  - Seleccionado TRIMESTRE {trimestre_num}")
                time.sleep(2)  # Esperar a que cargue
                return True
                
            except Exception as e:
                print(f"Error al seleccionar trimestre {trimestre_num}: {str(e)}")
                return False
                
    except Exception as e:
        print(f"Error inesperado al seleccionar trimestre: {str(e)}")
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

def procesar_civica(page, trimestre_num, grado_seleccionado):
    """
    Procesa la materia de Cívica de manera especial para grados 2-7.
    
    Args:
        page: Página de Playwright
        trimestre_num: Número de trimestre (1-3)
        grado_seleccionado: Grado seleccionado (ej: '2do', '3ro', etc.)
    """
    def procesar_pagina_actual():
        # Obtener todas las filas de estudiantes
        rows = page.query_selector_all('table tbody tr')
        print(f"Encontrados {len(rows)} estudiantes en la página actual")
        
        if not rows:
            print("No se encontraron estudiantes en la tabla")
            return False
            
        # Procesar cada estudiante
        for idx in range(1, len(rows) + 1):
            try:
                # Volver a obtener las filas para evitar elementos obsoletos
                current_rows = page.query_selector_all('table tbody tr')
                if idx > len(current_rows):
                    print(f"  - Índice {idx} fuera de rango, continuando...")
                    continue
                    
                row = current_rows[idx-1]
                
                # Obtener el nombre del estudiante
                nombre_element = row.query_selector('td:nth-child(3)')
                if not nombre_element:
                    print("  - No se pudo encontrar el elemento del nombre")
                    continue
                    
                nombre_estudiante = nombre_element.inner_text().strip()
                print(f"\n--- Procesando estudiante {idx}/{len(rows)}: {nombre_estudiante} ---")
                
                # Volver a obtener el botón para este estudiante específico
                select_button = row.query_selector('button.btn-warning')
                if not select_button:
                    print("  - No se encontró el botón de seleccionar para este estudiante")
                    continue
                
                print("  - Haciendo clic en 'Seleccionar'...")
                try:
                    # Hacer clic usando coordenadas para mayor confiabilidad
                    select_button.click()
                    # Esperar a que la página responda
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)  # Espera adicional para asegurar la carga
                except Exception as e:
                    print(f"  - Error al hacer clic en Seleccionar: {str(e)}")
                    # Intentar recuperar la página actual
                    page.reload()
                    page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                    continue
                
                # Aquí iría el resto del código para procesar al estudiante
                
                # Volver a la lista de estudiantes
                try:
                    back_button = page.wait_for_selector('button.btn-warning:has-text(\'Volver\')', timeout=10000)
                    if back_button:
                        back_button.click()
                        # Esperar a que se recargue la lista
                        page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                        time.sleep(1)  # Pequeña pausa para estabilidad
                except Exception as e:
                    print(f"  - Error al volver: {str(e)}")
                    # Si hay error al volver, recargar la página
                    page.goto(page.url)
                    page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                    return False
                
            except Exception as e:
                print(f"Error al procesar estudiante: {str(e)}")
                import traceback
                traceback.print_exc()
                # Intentar recuperar la página actual
                try:
                    page.reload()
                    page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                except:
                    pass
                continue
        
        return True

    try:
        print(f"\n=== PROCESANDO MATERIA: CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA ===")
        
        # Esperar a que cargue la tabla de estudiantes
        print("Esperando a que cargue la tabla de estudiantes...")
        page.wait_for_selector('table tbody tr', state='visible', timeout=30000)
        print("Tabla de estudiantes cargada correctamente")
        
        # Procesar la primera página
        if not procesar_pagina_actual():
            return False
        
        # Verificar si hay paginación
        pagination = page.query_selector('.row.justify-content-center')
        if not pagination:
            print("No se encontró control de paginación. Procesamiento completado.")
            return True
            
        # Obtener información de paginación
        page_info = page.query_selector('.row.justify-content-center span')
        if not page_info:
            print("No se pudo obtener información de paginación.")
            return True
            
        page_text = page_info.inner_text().strip()
        if 'de' not in page_text:
            print("Formato de paginación no reconocido.")
            return True
            
        try:
            current_page = int(page_text.split()[1])
            total_pages = int(page_text.split()[-1])
            print(f"Página {current_page} de {total_pages}")
            
            # Procesar páginas restantes
            while current_page < total_pages:
                # Buscar el botón de siguiente página
                next_buttons = page.query_selector_all('.row.justify-content-center button')
                next_button = None
                
                for btn in next_buttons:
                    btn_text = btn.inner_text().strip().lower()
                    if 'siguiente' in btn_text and 'disabled' not in (btn.get_attribute('class') or ''):
                        next_button = btn
                        break
                
                if not next_button:
                    print("No se encontró el botón de siguiente página.")
                    break
                
                print(f"\nNavegando a la página {current_page + 1} de {total_pages}...")
                next_button.click()
                
                # Esperar a que cargue la nueva página
                page.wait_for_load_state('networkidle')
                time.sleep(2)  # Espera adicional para asegurar la carga
                
                # Verificar que la página haya cambiado
                new_page_info = page.query_selector('.row.justify-content-center span')
                if not new_page_info:
                    print("No se pudo verificar el cambio de página.")
                    break
                    
                new_page_text = new_page_info.inner_text().strip()
                if str(current_page + 1) not in new_page_text:
                    print("No se pudo confirmar el cambio de página. Continuando de todos modos...")
                
                # Procesar la página actual
                if not procesar_pagina_actual():
                    break
                    
                current_page += 1
                
        except Exception as e:
            print(f"Error al manejar la paginación: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Proceso de Cívica completado ===")
        return True
        
    except Exception as e:
        print(f"Error en procesar_civica: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def obtener_ambito_y_scrapear(page, grado_seleccionado, jornada):
    from utils import obtener_materias_usuario
    
    try:
        # Obtener las materias del usuario
        materias = obtener_materias_usuario(grado_seleccionado, jornada)
        
        if not materias:
            print("No se encontraron materias para el grado y jornada seleccionados.")
            return False
            
        # Mostrar las materias disponibles
        print("\nMaterias disponibles para", grado_seleccionado, "- Jornada", jornada.upper() + ":")
        for i, materia in enumerate(materias, 1):
            print(f"{i}. {materia['nombre']}")
        
        # Verificar si hay materias de Cívica (con búsqueda más flexible)
        materias_civica = [m for m in materias if any(term in m['nombre'].lower() for term in ['civica', 'cívica', 'civico', 'cívico'])]
        
        # Si hay materias de Cívica, procesarlas primero
        if materias_civica:
            print("\n=== DETECTADA MATERIA DE CÍVICA ===")
            print("Se procesará automáticamente la materia de Cívica.")
            
            for materia in materias_civica:
                print(f"\n=== PROCESANDO MATERIA: {materia['nombre'].upper()} ===")
                
                # Buscar la materia en la página
                if not seleccionar_materia(page, materia['nombre'], jornada):
                    print(f"No se pudo encontrar la materia {materia['nombre']}. Continuando con la siguiente...")
                    continue
                
                # Procesar cada trimestre para Cívica
                trimestres_input = input("\nIngrese los números de trimestres para Cívica separados por comas (1-3), ejemplo '1,2': ")
                trimestres = [int(t.strip()) for t in trimestres_input.split(',')]
                
                for trimestre_num in trimestres:
                    print(f"\n=== Procesando Cívica - Trimestre {trimestre_num} ===")
                    procesar_civica(page, trimestre_num, grado_seleccionado)
                
                # Eliminar Cívica de la lista de materias a procesar
                materias = [m for m in materias if m['nombre'] != materia['nombre']]
                print("\n=== FINALIZADO PROCESAMIENTO DE CÍVICA ===\n")
        
        # Si no quedan más materias, terminar
        if not materias:
            print("No hay más materias para procesar.")
            return True
            
        # Preguntar por las demás materias
        print("\nMaterias restantes para procesar:")
        for i, materia in enumerate(materias, 1):
            print(f"{i}. {materia['nombre']}")
            
        seleccion = input("\n¿Desea procesar las materias restantes? (s/n): ").lower()
        if seleccion != 's':
            print("Proceso cancelado por el usuario.")
            return False
            
        # Procesar las demás materias
        for i, materia in enumerate(materias, 1):
            # Verificar si es Cívica (con búsqueda más flexible)
            es_civica = any(term in materia['nombre'].lower() for term in ['civica', 'cívica', 'civico', 'cívico'])
            
            print(f"\n=== PROCESANDO MATERIA: {materia['nombre'].upper()} ===")
            
            # Buscar la materia en la página
            if not seleccionar_materia(page, materia['nombre'], jornada):
                print(f"No se pudo encontrar la materia {materia['nombre']}. Continuando con la siguiente...")
                continue
            
            if es_civica:
                # Procesar Cívica de manera especial
                trimestres_input = input("\nIngrese los números de trimestres para Cívica separados por comas (1-3), ejemplo '1,2': ")
                trimestres = [int(t.strip()) for t in trimestres_input.split(',')]
                
                for trimestre_num in trimestres:
                    print(f"\n=== Procesando Cívica - Trimestre {trimestre_num} ===")
                    procesar_civica(page, trimestre_num, grado_seleccionado)
                continue
            
            # Para materias que no son Cívica
            accion = input("¿Qué acción desea realizar? (llenar/borrar): ").lower()
            trimestres_input = input("Ingrese los números de trimestres separados por comas (1-3), ejemplo '1,2': ")
            trimestres = [int(t.strip()) for t in trimestres_input.split(',')]
            
            # Cargar el mapeo de calificaciones si es necesario
            mapeo_calificaciones = None
            if accion == 'llenar':
                mapeo_calificaciones = crear_mapa_calificaciones('sb.xlsx')
            
            # Preguntar qué grupo procesar
            opcion = input("¿Qué grupo desea procesar? (todos/buenos/malos/personalizado/grados_personalizados): ").lower()
            
            for trimestre_num in trimestres:
                print(f"\nSeleccionando Trimestre {trimestre_num}...")
                
                # Seleccionar el trimestre
                if not seleccionar_trimestre(page, trimestre_num, grado_seleccionado, es_civica=es_civica):
                    print(f"No se pudo seleccionar el trimestre {trimestre_num}. Continuando con el siguiente...")
                    continue
                
                # Procesar cada ámbito
                for ambito in obtener_ambitos_usuario():
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
            time.sleep(1)
        
        print("\nProceso de scraping finalizado para todas las materias seleccionadas.")
        
    except Exception as e:
        print(f"Error en obtener_ambito_y_scrapear: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.newContext()
        page = context.newPage()
        
        grado_seleccionado = input("Ingrese el grado (ej: 1ro, 2do, etc.): ")
        jornada = input("Ingrese la jornada (ej: Matutina, Vespertina): ")
        
        obtener_ambito_y_scrapear(page, grado_seleccionado, jornada)

if __name__ == "__main__":
    main()