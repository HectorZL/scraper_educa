from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PlaywrightTimeoutError

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

def volver_a_primera_pagina(page):
    """Navega al inicio de la tabla usando el botón 'Anterior' hasta que quede deshabilitado."""
    try:
        while True:
            prev_button = page.query_selector("button.btn-primary:has-text('Anterior')")
            if not prev_button or not prev_button.is_enabled():
                break
            page.evaluate("(btn) => btn.click()", prev_button)
            page.wait_for_load_state('networkidle')
            time.sleep(1)
    except Exception as e:
        print(f"  - No se pudo regresar a la primera página: {str(e)}")

def cerrar_dialogos_confirmacion(page, contexto=""):
    """Cierra todos los modales de SweetAlert en cola para evitar bloqueos."""
    while True:
        try:
            confirm_button = page.wait_for_selector('button.swal2-confirm', timeout=1500)
            if not confirm_button:
                break
            label = (confirm_button.inner_text() or "").strip() or "Confirmar"
            page.evaluate("(btn) => btn.click()", confirm_button)
            sufijo = f" ({contexto})" if contexto else ""
            print(f"    - Botón '{label}' presionado{sufijo}")
        except PlaywrightTimeoutError:
            break
        except Exception as e:
            print(f"    - Error al cerrar confirmación: {str(e)}")
            break

def obtener_calificacion_default(grupo, trimestre_num):
    """Obtiene la calificación por defecto según el grupo y trimestre."""
    mapeos = {
        "buenos": trimestres_buenos_estudiantes,
        "malos": trimestres_malos_estudiantes,
        "personalizado": trimestres_excepciones,
        "grados_personalizados": trimestres
    }

    data = mapeos.get(grupo, trimestres)
    registro = data.get(trimestre_num)
    if registro and len(registro) > 1:
        return registro[1]
    return "NE"

def _buscar_calificacion_personalizada(nombre_estudiante):
    """Busca coincidencias aproximadas dentro de personalized_grades usando tokens del nombre."""
    nombre_normalizado = normalize_text(nombre_estudiante)
    if not nombre_normalizado:
        return None, None

    tokens_nombre = set(nombre_normalizado.split())

    for clave, nota in personalized_grades.items():
        clave_normalizada = normalize_text(clave)
        if not clave_normalizada:
            continue

        if clave_normalizada == nombre_normalizado:
            return nota, clave

        tokens_clave = clave_normalizada.split()
        if tokens_clave and all(token in tokens_nombre for token in tokens_clave):
            return nota, clave

    return None, None

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
                posibles_selectores = [
                    "select#trimestreSeleccionado",
                    "select[name='trimestreSeleccionado']",
                    "select#trimestre"
                ]
                selector_encontrado = None
                for selector in posibles_selectores:
                    try:
                        page.wait_for_selector(selector, state='visible', timeout=3000)
                        selector_encontrado = selector
                        break
                    except Exception:
                        continue

                if not selector_encontrado:
                    raise Exception("No se encontró el selector de trimestre")

                print(f"  - Usando selector '{selector_encontrado}'")

                if "trimestreSeleccionado" in selector_encontrado:
                    trimestre_label = f"TRIMESTRE {trimestre_num}"
                    page.select_option(selector_encontrado, label=trimestre_label)
                else:
                    # Selector antiguo que usa valores numéricos
                    page.select_option(selector_encontrado, str(trimestre_num))

                # Validar que el trimestre se seleccionó correctamente
                selected_text = page.evaluate(
                    "(selector) => {\n"
                    "  const select = document.querySelector(selector);\n"
                    "  return select ? select.options[select.selectedIndex].text.trim() : '';\n"
                    "}",
                    selector_encontrado
                )
                esperado = f"TRIMESTRE {trimestre_num}"
                if esperado not in selected_text.upper():
                    raise Exception(f"Confirmación fallida: '{selected_text}'")

                print(f"  - Seleccionado TRIMESTRE {trimestre_num}")
                time.sleep(2)  # Esperar a que cargue
                return True
                
            except Exception as e:
                print(f"Error al seleccionar trimestre {trimestre_num}: {str(e)}")
                return False
                
    except Exception as e:
        print(f"Error inesperado al seleccionar trimestre: {str(e)}")
        return False

def seleccionar_materia(page, nombre, jornada, grado_seleccionado=None, timeout=20000):
    try:
        normalized_nombre = normalize_text(nombre)
        normalized_jornada = normalize_text(jornada)
        normalized_grado_param = normalize_text(grado_seleccionado) if grado_seleccionado else ""
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

                    # Logs de depuración para entender por qué no se encuentra la fila
                    print("  - Fila encontrada:")
                    print(f"    asignatura_text = '{asignatura_text}'")
                    print(f"    grado_text      = '{grado_text}'")
                    print(f"    jornada_text    = '{jornada_text}'")

                    coincide_materia = normalized_nombre in asignatura_text and normalized_jornada in jornada_text
                    if not coincide_materia:
                        continue

                    # Filtrar por grado cuando se proporcione grado_seleccionado
                    if normalized_grado_param:
                        # Caso especial: para INICIAL no filtramos por el texto del grado,
                        # ya que la plataforma puede mostrar "GRUPO DE 4 AÑOS", "INCIAL", etc.
                        # Solo usamos materia + jornada para identificar la fila.
                        if normalized_grado_param != "inicial":
                            if normalized_grado_param not in grado_text:
                                continue

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
                 nombres_buenos=None, nombres_malos=None, accion="llenar", grupo="todos", mapeo_calificaciones=None, materia_nombre=None):
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
                mapeo_calificaciones, materia_nombre  # Pasar el nombre de la materia
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
                                mapeo_calificaciones=None, materia_nombre=None):
    """Procesa las filas usando la nueva interfaz con pestañas (grados 2-7) con manejo de paginación.
    Args:
        materia_nombre: Nombre de la materia actual (usado como clave en mapeo_calificaciones cuando ambito es None).
    """
    try:
        print("Esperando a que cargue la tabla de estudiantes...")
        page.wait_for_selector('table tbody tr', state='visible', timeout=30000)
        print("Tabla de estudiantes cargada correctamente")

        volver_a_primera_pagina(page)
        
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
                    elif grupo == "grados_personalizados":
                        calif_personalizada, clave_match = _buscar_calificacion_personalizada(nombre_estudiante)
                        if not calif_personalizada:
                            print("  - No está en personalized_grades. Saltando...")
                            continue
                        else:
                            print(f"  - Coincidencia personalizada con '{clave_match}'.")

                    # Buscar la calificación en el mapeo
                    calificacion = None
                    if grupo == "grados_personalizados":
                        calificacion, _ = _buscar_calificacion_personalizada(nombre_estudiante)

                    if mapeo_calificaciones and not calificacion:
                        # Determinar la clave a usar para buscar la calificación
                        clave_busqueda = ambito
                        if ambito is None and materia_nombre:
                            # Para grados 2-7, usar el nombre de la materia como clave
                            clave_busqueda = materia_nombre
                        
                        if clave_busqueda:
                            # Intentar encontrar una coincidencia exacta primero
                            for nombre_archivo, califs in mapeo_calificaciones.items():
                                if normalize_text(nombre_archivo) == nombre_normalizado:
                                    calificacion = califs.get(clave_busqueda)
                                    if calificacion:
                                        break
                            
                            # Si no hay coincidencia exacta, buscar coincidencia parcial
                            if not calificacion:
                                for nombre_archivo, califs in mapeo_calificaciones.items():
                                    if nombre_normalizado in normalize_text(nombre_archivo) or normalize_text(nombre_archivo) in nombre_normalizado:
                                        calificacion = califs.get(clave_busqueda)
                                        if calificacion:
                                            break
                    
                    # Si no se encontró calificación, usar valores por defecto según el grupo
                    if not calificacion:
                        calificacion = obtener_calificacion_default(grupo, trimestre_num)
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
                                cerrar_dialogos_confirmacion(page, "fila")
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

            volver_a_primera_pagina(page)

            try:
                page.evaluate("() => window.scrollTo(0, 0)")
            except Exception:
                pass

            total_estudiantes_procesados = 0
            pagina_actual = 1

            while True:
                print(f"\n--- Procesando página {pagina_actual} ---")
                page.wait_for_selector('table tbody tr', state='visible', timeout=30000)
                rows = page.query_selector_all('table tbody tr')
                if not rows:
                    print("No se encontraron estudiantes en la tabla")
                    break

                for idx, row in enumerate(rows, 1):
                    try:
                        indice_global = total_estudiantes_procesados + idx
                        print(f"\n--- Procesando estudiante {indice_global} (Página {pagina_actual}, Estudiante {idx}/{len(rows)}) ---")

                        nombre_element = row.query_selector('td.th-fixed') or row.query_selector('td:nth-child(1)')
                        if not nombre_element:
                            print("  - No se pudo encontrar el elemento del nombre")
                            continue

                        nombre_estudiante = nombre_element.inner_text().strip()
                        print(f"  - Estudiante: {nombre_estudiante}")

                        nombre_normalizado = normalize_text(nombre_estudiante)

                        if grupo == "buenos" and (not nombres_buenos or not any(normalize_text(n) == nombre_normalizado for n in nombres_buenos)):
                            print("  - No está en el grupo 'buenos'. Saltando...")
                            continue
                        elif grupo == "malos" and (not nombres_malos or not any(normalize_text(n) == nombre_normalizado for n in nombres_malos)):
                            print("  - No está en el grupo 'malos'. Saltando...")
                            continue
                        elif grupo == "personalizado" and (not nombres_excepciones or not any(normalize_text(n) == nombre_normalizado for n in nombres_excepciones)):
                            print("  - No está en la lista personalizada. Saltando...")
                            continue
                        elif grupo == "grados_personalizados":
                            calif_personalizada, clave_match = _buscar_calificacion_personalizada(nombre_estudiante)
                            if not calif_personalizada:
                                print("  - No está en personalized_grades. Saltando...")
                                continue
                            else:
                                print(f"  - Coincidencia personalizada con '{clave_match}'.")

                        calificacion = None
                        if grupo == "grados_personalizados":
                            calificacion, _ = _buscar_calificacion_personalizada(nombre_estudiante)

                        if mapeo_calificaciones and not calificacion:
                            for nombre_archivo, califs in mapeo_calificaciones.items():
                                if normalize_text(nombre_archivo) == nombre_normalizado:
                                    calificacion = califs.get(ambito)
                                    if calificacion:
                                        break

                            if not calificacion:
                                for nombre_archivo, califs in mapeo_calificaciones.items():
                                    if nombre_normalizado in normalize_text(nombre_archivo) or normalize_text(nombre_archivo) in nombre_normalizado:
                                        calificacion = califs.get(ambito)
                                        if calificacion:
                                            break

                        if not calificacion:
                            calificacion = obtener_calificacion_default(grupo, trimestre_num)
                            print(f"  - No se encontró calificación en el archivo. Usando valor por defecto de academic_data: {calificacion}")
                        else:
                            print(f"  - Calificación encontrada en archivo: {calificacion}")

                        input_fields = row.query_selector_all('td input[type="text"]')
                        if not input_fields:
                            print("  - No se encontraron campos de calificación en la fila")
                            continue

                        debe_guardar = False

                        for campo_idx, input_field in enumerate(input_fields, 1):
                            try:
                                valor_actual = (input_field.input_value() or "").strip()
                            except Exception as e:
                                print(f"    - No se pudo obtener el valor del campo {campo_idx}: {str(e)}")
                                valor_actual = ""

                            if accion == "llenar":
                                if valor_actual != str(calificacion):
                                    try:
                                        input_field.evaluate(
                                            "(el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); }",
                                            str(calificacion)
                                        )
                                        print(f"    - Campo {campo_idx}: asignando {calificacion}")
                                        debe_guardar = True
                                    except Exception as e:
                                        print(f"    - Error al llenar el campo {campo_idx}: {str(e)}")
                                else:
                                    print(f"    - Campo {campo_idx}: ya contiene {valor_actual}")
                            elif accion == "borrar":
                                if valor_actual:
                                    try:
                                        input_field.evaluate(
                                            "(el) => { el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })); }"
                                        )
                                        print(f"    - Campo {campo_idx}: valor limpiado")
                                        debe_guardar = True
                                    except Exception as e:
                                        print(f"    - Error al limpiar el campo {campo_idx}: {str(e)}")

                        if not debe_guardar:
                            print("  - No hubo cambios en la fila. Saltando guardado.")
                            total_estudiantes_procesados += 1
                            continue

                        save_button = row.query_selector("button.btn-primary:has-text('Guardar')") or row.query_selector('td button.btn-primary')
                        if save_button:
                            try:
                                page.evaluate("(btn) => btn.click()", save_button)
                                print("  - Guardando cambios...")
                                cerrar_dialogos_confirmacion(page, "fila")
                            except Exception as e:
                                print(f"  - Error al guardar la fila: {str(e)}")
                        else:
                            print("  - No se encontró el botón de guardar en la fila")

                        total_estudiantes_procesados += 1

                    except Exception as e:
                        print(f"Error al procesar estudiante: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue

                # Verificar paginación
                try:
                    pagination_span = page.query_selector('span:has-text("Página")')
                    if not pagination_span:
                        print("No se encontró información de paginación. Terminando...")
                        break

                    page_text = pagination_span.inner_text().strip()
                    import re
                    match = re.search(r'Página\s+(\d+)\s+de\s+(\d+)', page_text, re.IGNORECASE)
                    if not match:
                        print(f"Formato de paginación no reconocido: '{page_text}'")
                        break

                    current_page = int(match.group(1))
                    total_pages = int(match.group(2))

                    if current_page >= total_pages:
                        print("No hay más páginas por procesar.")
                        break

                    next_button = page.query_selector("button.btn-primary:has-text('Siguiente')")
                    if not next_button or not next_button.is_enabled():
                        print("El botón 'Siguiente' no está disponible.")
                        break

                    print(f"Avanzando a la página {current_page + 1} de {total_pages}...")
                    next_button.click()
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)
                    pagina_actual = current_page + 1

                except Exception as e:
                    print(f"Error al manejar la paginación: {str(e)}")
                    break

            print(f"\nProceso de calificación completado. Total de estudiantes procesados: {total_estudiantes_procesados}")
            try:
                final_ok = page.query_selector("button.swal2-confirm")
                if final_ok:
                    page.evaluate("(btn) => btn.click()", final_ok)
                    print("  - Botón final 'Aceptar' presionado")
            except Exception as e:
                print(f"  - No se pudo cerrar el diálogo final: {str(e)}")
            return total_estudiantes_procesados > 0

        else:
            print(f"No se encontró el ámbito '{ambito}'.")
            return False
            
    except Exception as e:
        print(f"Error al procesar con la interfaz antigua: {str(e)}")
        return False

def procesar_todos_los_estudiantes(page, ambito, trimestre_num, grado_seleccionado, accion="llenar", mapeo_calificaciones=None, materia_nombre=None):
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
        mapeo_calificaciones=mapeo_calificaciones,
        materia_nombre=materia_nombre
    )

def procesar_civica(page, trimestre_num, grado_seleccionado, usar_notas_personalizadas=False):
    """Procesa la materia de Cívica.
    
    Si usar_notas_personalizadas es True, se usa personalized_grades para decidir
    qué valor seleccionar en los dropdowns por estudiante:
      - A-  => SIEMPRE
      - B+, B- => FRECUENTEMENTE
      - cualquier otra nota => SIEMPRE (comportamiento por defecto)
    """
    def _obtener_etiqueta_civica(nombre_estudiante):
        if not usar_notas_personalizadas:
            return "SIEMPRE"

        nota, clave = _buscar_calificacion_personalizada(nombre_estudiante)
        if not nota:
            print("    - No hay nota personalizada para Cívica, usando 'SIEMPRE'.")
            return "SIEMPRE"

        print(f"    - Nota personalizada para Cívica ({clave}): {nota}")

        if nota == "A-":
            return "SIEMPRE"
        if nota in ("B+", "B-"):
            return "FRECUENTEMENTE"

        # Cualquier otra nota cae al modo por defecto
        return "SIEMPRE"

    def procesar_pagina_actual(trimestre_num):
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
                    # Hacer clic usando JavaScript para mayor confiabilidad
                    page.evaluate('''(button) => {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                    }''', select_button)
                    page.wait_for_load_state('networkidle')
                    time.sleep(2)
                except Exception as e:
                    print(f"  - Error al hacer clic en Seleccionar: {str(e)}")
                    page.reload()
                    page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                    continue
                
                # Seleccionar el trimestre
                try:
                    print("  - Seleccionando trimestre...")
                    # Esperar a que el selector de trimestre esté disponible
                    page.wait_for_selector('select#trimestreSeleccionado', state='visible', timeout=5000)
                    
                    # Seleccionar el trimestre usando el texto exacto
                    trimestre_texto = f"TRIMESTRE {trimestre_num}"
                    page.select_option('select#trimestreSeleccionado', label=trimestre_texto)
                    time.sleep(1)  # Esperar a que se actualice el formulario
                    
                    # Verificar que se haya seleccionado correctamente
                    selected_trimestre = page.evaluate('''() => {
                        const select = document.querySelector('select#trimestreSeleccionado');
                        return select ? select.options[select.selectedIndex].text.trim() : '';
                    }''')
                    
                    if not selected_trimestre.endswith(str(trimestre_num)):
                        print(f"    - Error al seleccionar el trimestre: seleccionado '{selected_trimestre}', esperado '{trimestre_texto}'")
                        raise Exception("Error al seleccionar el trimestre")
                    
                    print(f"    - {trimestre_texto} seleccionado correctamente")
                    
                except Exception as e:
                    print(f"    - Error al seleccionar el trimestre: {str(e)}")
                    # Tomar captura de pantalla para depuración
                    try:
                        page.screenshot(path=f'error_trimestre_{idx}.png')
                    except:
                        pass
                    # Volver a la lista de estudiantes
                    try_volver()
                    continue
                
                # Procesar los dropdowns de Cívica (SIEMPRE o FRECUENTEMENTE según el modo)
                try:
                    print("  - Procesando opciones del formulario...")
                    # Esperar a que los dropdowns estén visibles
                    page.wait_for_selector('select.form-control.wide-select', state='visible', timeout=5000)
                    
                    # Determinar la etiqueta a usar para este estudiante
                    etiqueta_objetivo = _obtener_etiqueta_civica(nombre_estudiante)
                    print(f"    - Etiqueta objetivo para Cívica: {etiqueta_objetivo}")

                    # Si la etiqueta es 'NE', no llenar nada y pasar al siguiente estudiante
                    if str(etiqueta_objetivo).strip().upper() == "NE":
                        print("    - Etiqueta 'NE' detectada: no se modifican los valores y se pasa al siguiente estudiante.")
                        # Volver a la lista de estudiantes sin guardar cambios
                        if not try_volver():
                            return False
                        continue

                    # Seleccionar la etiqueta objetivo en todos los dropdowns
                    dropdowns = page.query_selector_all('select.form-control.wide-select')
                    if not dropdowns:
                        print("    - No se encontraron dropdowns para llenar")
                    else:
                        for i, dropdown in enumerate(dropdowns, 1):
                            try:
                                # Verificar si el dropdown está habilitado
                                if not dropdown.is_enabled():
                                    print(f"    - Dropdown {i} está deshabilitado, omitiendo...")
                                    continue
                                    
                                # Verificar opciones disponibles
                                options = dropdown.query_selector_all('option')
                                if len(options) <= 1:  # Solo tiene 'Seleccione una opción'
                                    print(f"    - Dropdown {i} no tiene opciones válidas")
                                    continue

                                # Buscar el value cuya etiqueta contenga la palabra clave deseada
                                valor_a_seleccionar = None
                                etiqueta_min = etiqueta_objetivo.lower()
                                for opt in options:
                                    txt = (opt.inner_text() or "").strip().lower()
                                    if not txt:
                                        continue
                                    # Coincidencia flexible: contiene "siempre" o "frecuent" según la etiqueta objetivo
                                    if "siempre" in txt and "siempre" in etiqueta_min:
                                        valor_a_seleccionar = opt.get_attribute("value")
                                        break
                                    if "frecuent" in txt and "frecuent" in etiqueta_min:
                                        valor_a_seleccionar = opt.get_attribute("value")
                                        break

                                if not valor_a_seleccionar:
                                    print(f"    - No se encontró opción que coincida con '{etiqueta_objetivo}', usando valor por defecto si existe.")
                                    # Fallback: intentar usar directamente la primera opción distinta de 'Seleccione una opción'
                                    for opt in options:
                                        txt = (opt.inner_text() or "").strip().lower()
                                        if txt and "seleccione" not in txt:
                                            valor_a_seleccionar = opt.get_attribute("value")
                                            break

                                if valor_a_seleccionar:
                                    dropdown.select_option(value=valor_a_seleccionar)
                                    print(f"    - Dropdown {i}: seleccionando '{etiqueta_objetivo}' (value={valor_a_seleccionar})")
                                else:
                                    print(f"    - No se pudo determinar un valor para el dropdown {i}, se omite.")
                                time.sleep(0.3)  # Pequeña pausa entre interacciones
                                
                            except Exception as e:
                                print(f"    - Error en dropdown {i}: {str(e)}")
                                continue
                    
                    # Hacer clic en Guardar si el botón está habilitado
                    save_button = page.wait_for_selector('button.btn-success:has-text(\'Guardar\')', state='visible', timeout=5000)
                    if save_button and save_button.is_enabled():
                        print("  - Guardando cambios...")
                        # Hacer clic usando JavaScript para evitar problemas de visibilidad
                        page.evaluate('''(btn) => {
                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                            btn.click();
                        }''', save_button)
                        # Cerrar diálogos de confirmación (SweetAlert) como en el flujo antiguo
                        cerrar_dialogos_confirmacion(page, "civica")
                        time.sleep(2)  # Esperar a que se guarde
                        
                        # Verificar si se guardó correctamente
                        try:
                            page.wait_for_selector('.alert-success', timeout=3000)
                            print("    - Cambios guardados exitosamente")
                        except:
                            print("    - No se pudo confirmar el guardado, continuando...")
                    else:
                        print("  - El botón Guardar no está disponible")
                
                except Exception as e:
                    print(f"    - Error al procesar el formulario: {str(e)}")
                    # Tomar captura de pantalla para depuración
                    try:
                        page.screenshot(path=f'error_formulario_{idx}.png')
                    except:
                        pass
                
                # Volver a la lista de estudiantes
                if not try_volver():
                    return False
                
            except Exception as e:
                print(f"Error al procesar estudiante: {str(e)}")
                import traceback
                traceback.print_exc()
                if not try_volver():
                    return False
                continue
        
        return True
    
    def try_volver():
        """Intenta volver a la lista de estudiantes"""
        try:
            back_button = page.wait_for_selector('button.btn-warning:has-text(\'Volver\')', timeout=10000)
            if back_button:
                # Hacer clic usando JavaScript para mayor confiabilidad
                page.evaluate('''(btn) => {
                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    btn.click();
                }''', back_button)
                # Esperar a que la tabla de estudiantes esté visible
                page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                time.sleep(1)
                return True
        except Exception as e:
            print(f"  - Error al volver a la lista: {str(e)}")
            try:
                # Si falla, intentar recargar la página
                page.reload()
                page.wait_for_selector('table tbody tr', state='visible', timeout=10000)
                return True
            except:
                return False
        return False

    try:
        print(f"\n=== PROCESANDO MATERIA: CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA ===")
        
        # Esperar a que cargue la tabla de estudiantes
        print("Esperando a que cargue la tabla de estudiantes...")
        page.wait_for_selector('table tbody tr', state='visible', timeout=30000)
        print("Tabla de estudiantes cargada correctamente")
        
        # Procesar la primera página
        if not procesar_pagina_actual(trimestre_num):
            return False
        
        # Verificar si hay paginación
        try:
            pagination = page.wait_for_selector('.row.justify-content-center', timeout=3000)
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
                    # Hacer clic usando JavaScript para mayor confiabilidad
                    page.evaluate('''(btn) => {
                        btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                        btn.click();
                    }''', next_button)
                    
                    # Esperar a que se cargue la nueva página
                    try:
                        page.wait_for_load_state('networkidle')
                        # Esperar a que la tabla se actualice verificando que el número de página cambió
                        page.wait_for_function(f'''() => {{
                            const pageInfo = document.querySelector('.row.justify-content-center span');
                            return pageInfo && pageInfo.textContent.includes('{current_page + 1}');
                        }}''', timeout=10000)
                        time.sleep(1)  # Espera adicional para asegurar la carga
                    except Exception as e:
                        print(f"  - No se pudo confirmar el cambio de página: {str(e)}")
                    
                    # Procesar la página actual
                    if not procesar_pagina_actual(trimestre_num):
                        break
                        
                    current_page += 1
                    
            except Exception as e:
                print(f"Error al manejar la paginación: {str(e)}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            print(f"Error al verificar paginación: {str(e)}")
        
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

        # Separar materias de Cívica del resto (búsqueda flexible)
        materias_civica = [m for m in materias if any(term in m['nombre'].lower() for term in ['civica', 'cívica', 'civico', 'cívico'])]
        materias_restantes = [m for m in materias if m not in materias_civica]

        # === BLOQUE ESPECIAL PARA CÍVICA ===
        if materias_civica:
            print("\n=== DETECTADA MATERIA DE CÍVICA ===")
            print("Se procesará automáticamente la materia de Cívica.")

            # Elegir modo de Cívica
            modo_civica = input("\nModo de Cívica: ingrese 'd' para modo por defecto (todo SIEMPRE) o 'p' para usar notas personalizadas (A-/B+/B-). [d/p]: ").strip().lower()
            usar_notas_personalizadas_civica = (modo_civica == 'p')
            if usar_notas_personalizadas_civica:
                print("\nCívica se procesará en modo BASADO EN NOTAS PERSONALIZADAS (A- => SIEMPRE, B+/B- => FRECUENTEMENTE).")
            else:
                print("\nCívica se procesará en modo POR DEFECTO (todos los indicadores en SIEMPRE).")

            for materia in materias_civica:
                print(f"\n=== PROCESANDO MATERIA: {materia['nombre'].upper()} ===")

                # Buscar la materia de Cívica en la tabla de la plataforma
                if not seleccionar_materia(page, materia['nombre'], jornada, grado_seleccionado=grado_seleccionado):
                    print(f"No se pudo encontrar la materia {materia['nombre']}. Continuando con la siguiente...")
                    continue

                # Preguntar trimestres para Cívica
                trimestres_input = input("\nIngrese los números de trimestres para Cívica separados por comas (1-3), ejemplo '1,2': ")
                trimestres_civica = [int(t.strip()) for t in trimestres_input.split(',')]

                for trimestre_num in trimestres_civica:
                    print(f"\n=== Procesando Cívica - Trimestre {trimestre_num} ===")
                    procesar_civica(page, trimestre_num, grado_seleccionado, usar_notas_personalizadas=usar_notas_personalizadas_civica)

            # Eliminar Cívica de la lista de materias a procesar con el flujo normal
            materias = materias_restantes

        # === FLUJO NORMAL PARA EL RESTO DE MATERIAS (manteniendo tu lógica anterior) ===
        if not materias:
            print("No hay más materias para procesar.")
            return True

        print("\nMaterias restantes para procesar:")
        for i, materia in enumerate(materias, 1):
            print(f"{i}. {materia['nombre']}")

        seleccion = input("\n¿Desea procesar las materias restantes? (s/n): ").lower()
        if seleccion != 's':
            print("Proceso cancelado por el usuario.")
            return False

        for materia in materias:
            # Ya se excluyeron las materias de Cívica; aquí solo llegan materias normales
            print(f"\n=== PROCESANDO MATERIA: {materia['nombre'].upper()} ===")

            # Buscar la materia en la página
            if not seleccionar_materia(page, materia['nombre'], jornada, grado_seleccionado=grado_seleccionado):
                print(f"No se pudo encontrar la materia {materia['nombre']}. Continuando con la siguiente...")
                continue

            # Preguntar acción y trimestres
            accion = input("¿Qué acción desea realizar? (llenar/borrar): ").lower()
            trimestres_input = input("Ingrese los números de trimestres separados por comas (1-3), ejemplo '1,2': ")
            trimestres_materia = [int(t.strip()) for t in trimestres_input.split(',')]

            # Cargar el mapeo de calificaciones si es necesario
            mapeo_calificaciones = None
            if accion == 'llenar':
                mapeo_calificaciones = crear_mapa_calificaciones('sb.xlsx')

            # Para grados 2do en adelante (nueva interfaz con Excel), usar siempre todos los estudiantes
            # y las notas del archivo, sin preguntar grupo
            if any(str(g) in str(grado_seleccionado) for g in range(2, 8)):
                opcion = "todos"
                print("\nGrado con mapeo de Excel (2do-7mo): se procesarán TODOS los estudiantes usando las notas del archivo.")
            else:
                # Preguntar qué grupo procesar solo para Inicial y 1ro
                opcion = input("¿Qué grupo desea procesar? (todos/buenos/malos/personalizado/grados_personalizados): ").lower()

            for trimestre_num in trimestres_materia:
                print(f"\nSeleccionando Trimestre {trimestre_num}...")

                # Seleccionar el trimestre (no es Cívica aquí)
                if not seleccionar_trimestre(page, trimestre_num, grado_seleccionado, es_civica=False):
                    print(f"No se pudo seleccionar el trimestre {trimestre_num}. Continuando con el siguiente...")
                    continue

                # Procesar cada ámbito
                # Para grados 2do-7mo, la nueva interfaz no usa ámbitos; evitamos preguntar ámbitos
                if any(str(g) in str(grado_seleccionado) for g in range(2, 8)):
                    ambitos = [None]
                else:
                    ambitos = obtener_ambitos_usuario(materia)

                for ambito in ambitos:
                    print(f"Procesando Trimestre {trimestre_num} - {ambito}...")

                    if opcion == "todos":
                        procesar_todos_los_estudiantes(
                            page,
                            ambito,
                            trimestre_num,
                            grado_seleccionado=grado_seleccionado,
                            accion=accion,
                            mapeo_calificaciones=mapeo_calificaciones,
                            materia_nombre=materia['nombre']
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
                            mapeo_calificaciones=mapeo_calificaciones,
                            materia_nombre=materia['nombre']
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
                            mapeo_calificaciones=mapeo_calificaciones,
                            materia_nombre=materia['nombre']
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
                            mapeo_calificaciones=mapeo_calificaciones,
                            materia_nombre=materia['nombre']
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
                            mapeo_calificaciones=mapeo_calificaciones,
                            materia_nombre=materia['nombre']
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