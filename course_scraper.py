from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import re
from academic_data import (
    trimestres,
    trimestres_borrar,
    trimestres_buenos_estudiantes,
    trimestres_malos_estudiantes
)
from ambitos import obtener_ambitos_usuario
from trimesters import obtener_trimestres_usuario
from utils import obtener_materia_usuario
from nombres_estudiantes import nombres_buenos, nombres_malos 

def normalize_text(text):
    text = text.strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    return text

def seleccionar_trimestre(page, trimestre_num):
    try:
        print(f"Intentando seleccionar trimestre {trimestre_num}...")

        # Usamos un selector más robusto que incluye múltiples atributos
        selector = f'div.mat-tab-label[role="tab"][aria-posinset="{trimestre_num}"]'
        tab = page.wait_for_selector(selector, state="visible", timeout=10000)
        if not tab:
            print(f"No se encontró el tab para el trimestre {trimestre_num}")
            return False

        # Nos aseguramos de que el elemento esté visible en la ventana antes de hacer clic
        page.evaluate("""(tab) => { tab.scrollIntoView({behavior: 'smooth', block: 'center'}); }""", tab)
        time.sleep(1)
        tab.click()
        time.sleep(2)

        # Verificamos si el trimestre está activo después de hacer clic
        parent_tab = page.query_selector(selector)
        if parent_tab and 'mat-tab-label-active' in parent_tab.get_attribute('class'):
            print(f"Trimestre {trimestre_num} seleccionado correctamente")
            return True

        print(f"El trimestre {trimestre_num} no se activó.")
        return False

    except Exception as e:
        print(f"Error al seleccionar trimestre {trimestre_num}: {e}")
        return False


def seleccionar_materia(page, nombre, jornada, timeout=20000):
    try:
        normalized_nombre = normalize_text(nombre)
        normalized_jornada = normalize_text(jornada)
        print(f"Buscando materia que contenga '{normalized_nombre}' con jornada '{normalized_jornada}'")

        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/calificacion_ordinaria")
        page.wait_for_load_state('networkidle')
        pagina_actual = 1
        while True:
            print(f"\nRevisando página {pagina_actual}...")
            page.wait_for_load_state('networkidle')
            page.wait_for_selector('table tbody tr.mat-row', state="visible", timeout=10000)
            filas = page.query_selector_all('table tbody tr.mat-row:not(.mat-header-row)')

            for fila in filas:
                nombre_element = fila.query_selector('td.cdk-column-descripcion')
                jornada_element = fila.query_selector('td.cdk-column-jornada')
                
                if nombre_element and jornada_element:
                    n_text = normalize_text(nombre_element.inner_text())
                    j_text = normalize_text(jornada_element.inner_text())
                    
                    if normalized_nombre in n_text and normalized_jornada in j_text:
                        print("Coincidencia encontrada.")
                        icon = fila.query_selector('mat-icon[data-mat-icon-type="font"]')
                        if icon:
                            icon.click()
                            return True

            next_button = page.query_selector('li.page-item a.page-link:has-text("Siguiente")')
            if next_button:
                parent = next_button.evaluate_handle("el => el.parentElement")
                parent_class = parent.get_attribute("class")
                if "disabled" not in parent_class:
                    print("Avanzando a la siguiente página...")
                    next_button.click()
                    pagina_actual += 1
                    time.sleep(2)
                    page.wait_for_load_state('networkidle')
                else:
                    print("El botón 'Siguiente' está deshabilitado.")
                    break
            else:
                print("No hay más páginas disponibles.")
                break

        print(f"No se encontró la materia '{nombre}' con la jornada '{jornada}'.")
        return False
    except Exception as e:
        print(f"Error al seleccionar la materia '{nombre}': {e}")
        return False

def procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=None, nombres_buenos=None, nombres_malos=None, accion="llenar", grupo="todos"):
    print(f"Procesando {ambito_seleccionado} para Trimestre {trimestre_num}...")

    try:
        print("Seleccionando ámbito...")

        options = page.query_selector_all('select[name="codigoAmbito"] option')
        value_to_select = None
        for option in options:
            if normalize_text(option.inner_text()) == normalize_text(ambito_seleccionado):
                value_to_select = option.get_attribute('value')
                break

        if value_to_select:
            page.select_option('select[name="codigoAmbito"]', value=value_to_select)
            print(f"Ámbito '{ambito_seleccionado}' seleccionado correctamente.")
        else:
            print(f"No se encontró el ámbito '{ambito_seleccionado}'.")
            return False

        # Volver a la primera página
        print("Volviendo a la primera página...")
        while True:
            prev_button = page.query_selector('button.mat-paginator-navigation-previous')
            if prev_button and not prev_button.is_disabled():
                prev_button.click()
                time.sleep(1)
            else:
                break

        page.wait_for_selector('table tbody tr', state="visible", timeout=10000)
        page.evaluate("""() => { window.scrollTo(0, 0); }""")
        time.sleep(1)

        while True:
            rows = page.query_selector_all('table tbody tr')
            total_filas = len(rows)
            print(f"Encontradas {total_filas} filas en esta página.")

            for row_idx in range(total_filas):
                try:
                    rows = page.query_selector_all('table tbody tr')
                    if row_idx >= len(rows):
                        print(f"Índice fuera de rango ({row_idx}). Recargando filas...")
                        break

                    row = rows[row_idx]

                    nombre_estudiante_element = row.query_selector('td.th-fixed')
                    if not nombre_estudiante_element:
                        print(f"Fila {row_idx}: No se encontró el elemento de nombre.")
                        continue

                    nombre_estudiante = normalize_text(nombre_estudiante_element.inner_text())

                    # Si se procesan "todos", no se deben aplicar filtros de buenos/malos
                    if grupo == "todos":
                        # Asignar la nota por defecto de trimestre si es "todos"
                        nota = trimestres[trimestre_num][1] if accion != "borrar" else trimestres_borrar[trimestre_num][1]
                        print(f"{nombre_estudiante} asignado con la nota normal: {nota}")
                    else:
                        # Si no es "todos", verificar si es "bueno" o "malo"
                        if nombres_buenos and nombre_estudiante not in [normalize_text(nombre) for nombre in nombres_buenos]:
                            print(f"  - {nombre_estudiante} no es un 'bueno'. Ignorando...")
                            continue

                        if nombres_malos and nombre_estudiante not in [normalize_text(nombre) for nombre in nombres_malos]:
                            print(f"  - {nombre_estudiante} no es un 'malo'. Ignorando...")
                            continue

                        # Asignar la nota de acuerdo a los tipos de estudiantes
                        if nombres_buenos and nombre_estudiante in [normalize_text(nombre) for nombre in nombres_buenos]:
                            nota = trimestres_buenos_estudiantes[trimestre_num][1]
                            print(f"{nombre_estudiante} identificado como 'bueno'. Nota: {nota}")
                        elif nombres_malos and nombre_estudiante in [normalize_text(nombre) for nombre in nombres_malos]:
                            nota = trimestres_malos_estudiantes[trimestre_num][1]
                            print(f"{nombre_estudiante} identificado como 'malo'. Nota: {nota}")
                        elif nombres_excepciones and nombre_estudiante in [normalize_text(nombre) for nombre in nombres_excepciones]:
                            nota = trimestres_excepciones[trimestre_num][1]
                            print(f"{nombre_estudiante} identificado como 'excepción'. Nota: {nota}")
                        else:
                            # Asignar la nota por defecto de trimestre si no es "bueno" ni "malo"
                            nota = trimestres[trimestre_num][1] if accion != "borrar" else trimestres_borrar[trimestre_num][1]
                            print(f"{nombre_estudiante} asignado con la nota normal: {nota}")

                    print(f"Procesando datos para {nombre_estudiante}...")

                    # Procesar los inputs para la calificación
                    row_inputs = row.query_selector_all('input.form-control.text-center.text-uppercase')
                    for idx, input_element in enumerate(row_inputs):
                        if not input_element:
                            print(f"  - Campo {idx + 1} no encontrado, saltando.")
                            continue

                        input_element.fill("")  # Limpiar el campo antes de llenarlo

                        # Llenar la calificación con la nota asignada
                        input_element.fill(nota)
                        print(f"  - Campo {idx + 1} rellenado con nota: {nota}")

                    # Manejo de popups después de llenar los campos
                    while True:
                        try:
                            warning_popup = page.query_selector('.swal2-popup.swal2-show')
                            if warning_popup:
                                print(f"Advertencia detectada, cerrando popup...")
                                ok_button = page.query_selector('button.swal2-confirm.swal2-styled')
                                if ok_button:
                                    ok_button.click()
                                    time.sleep(1)  # Esperar después del primer clic
                                print("  - Popup cerrado correctamente.")
                            else:
                                break  # No hay popup, continuar con el siguiente paso
                        except Exception as e:
                            print(f"Error al manejar popup de advertencia: {e}")
                            break

                    time.sleep(1)

                    # Hacer clic en el botón de guardar después de llenar la nota
                    save_button = row.query_selector('button.btn.btn-icon.btn-outline-primary')
                    if save_button:
                        page.evaluate(
                            """(btn) => {
                                btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                window.scrollBy(0, -100);
                            }""",
                            save_button
                        )
                        time.sleep(1)
                        save_button.click()
                        time.sleep(1)

                        # Esperar el popup de confirmación y hacer clic en el primer "Guardar"
                        try:
                            guardar_button = page.wait_for_selector(
                                'button.swal2-confirm.swal2-styled', state="visible", timeout=5000)
                            guardar_button.click()
                            print(f"  - Cambios guardados para {nombre_estudiante}")
                            time.sleep(1)

                            # Ahora esperamos el popup final con el botón "OK"
                            ok_button = page.wait_for_selector(
                                'button.swal2-confirm.swal2-styled:has-text("OK")', state="visible", timeout=5000)
                            ok_button.click()
                            print(f"  - Confirmación de guardado OK final para {nombre_estudiante}")
                        except Exception as e:
                            print(f"Error al esperar o hacer clic en el botón de guardar: {e}")
                            continue
                    else:
                        print(f"No se encontró el botón de guardar para {nombre_estudiante}")
                except Exception as e:
                    print(f"Error al procesar la fila {row_idx}: {str(e)}")

            # Navegar a la siguiente página si existe un botón "next"
            next_button = page.query_selector('button.mat-paginator-navigation-next:not([disabled])')
            if next_button:
                next_button.click()
                print("Avanzando a la siguiente página...")
                time.sleep(3)
                page.evaluate("""() => { window.scrollTo(0, 0); }""")
            else:
                print("No hay más páginas para procesar.")
                break

        print("Datos académicos actualizados correctamente.")
        return True

    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        return False

# Funciones para procesar todos los estudiantes o excepciones
def procesar_todos_los_estudiantes(page, ambito_seleccionado, trimestre_num, accion="llenar"):
    return procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=None, accion=accion, grupo="todos")

def procesar_estudiantes_excepciones(page, ambito_seleccionado, trimestre_num, nombres_excepciones, accion="llenar"):
    return procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=nombres_excepciones, accion=accion, grupo="excepciones")

def obtener_ambito_y_scrapear(page):
    materia = obtener_materia_usuario()
    if not seleccionar_materia(page, materia['nombre'], materia['jornada']):
        print(f"No se pudo seleccionar la materia {materia['nombre']}")
        return False

    ambitos = obtener_ambitos_usuario(materia)
    print(f"Ámbitos seleccionados para {materia['nombre']}: {ambitos}")

    trimestres_seleccionados = obtener_trimestres_usuario()
    print(f"Trimestres seleccionados: {trimestres_seleccionados}")

    opcion = input("¿Qué grupo desea procesar? (todos/buenos/malos): ").strip().lower()
    accion = input("¿Qué acción desea realizar? (llenar/borrar): ").strip().lower()

    for trimestre_num in trimestres_seleccionados:
        print(f"\nSeleccionando Trimestre {trimestre_num}...")
        seleccionar_trimestre(page, trimestre_num)

        for ambito in ambitos:
            print(f"Procesando Trimestre {trimestre_num} - {ambito}...")
            if opcion == "todos":
                procesar_filas(page, ambito, trimestre_num, nombres_buenos=nombres_buenos, nombres_malos=nombres_malos, accion=accion)
            elif opcion == "buenos":
                procesar_filas(page, ambito, trimestre_num, nombres_buenos=nombres_buenos, nombres_malos=None, accion=accion)
            elif opcion == "malos":
                procesar_filas(page, ambito, trimestre_num, nombres_buenos=None, nombres_malos=nombres_malos, accion=accion)
            else:
                print("Opción no válida. Finalizando...")
                return False

    print("Proceso de scraping finalizado.")
    return True
