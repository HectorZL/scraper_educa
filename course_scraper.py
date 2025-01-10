from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import re
from academic_data import trimestres, trimestres_borrar, trimestres_excepciones
from ambitos import obtener_ambitos_usuario
from trimesters import obtener_trimestres_usuario
from utils import obtener_materia_usuario

def normalize_text(text):
    text = text.strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    return text

def seleccionar_trimestre(page, trimestre_num):
    try:
        print(f"Intentando seleccionar trimestre {trimestre_num}...")

        selector = f'div[role="tab"][aria-posinset="{trimestre_num}"]'
        tab = page.wait_for_selector(selector, state="visible", timeout=10000)
        if not tab:
            print(f"No se encontró el tab para el trimestre {trimestre_num}")
            return False

        page.evaluate("""(tab) => { tab.scrollIntoView({behavior: 'smooth', block: 'center'}); }""", tab)
        time.sleep(1)
        tab.click()
        time.sleep(2)

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

def procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=None, accion="llenar"):
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

            for row_idx in range(len(rows)):
                try:
                    rows = page.query_selector_all('table tbody tr')
                    row = rows[row_idx]

                    nombre_estudiante_element = row.query_selector('td.th-fixed')
                    if not nombre_estudiante_element:
                        continue

                    nombre_estudiante = normalize_text(nombre_estudiante_element.inner_text())

                    if nombres_excepciones:
                        if nombre_estudiante in [normalize_text(nombre) for nombre in nombres_excepciones]:
                            nota = trimestres_excepciones[trimestre_num][1]
                        else:
                            nota = trimestres_borrar[trimestre_num][1] if accion == "borrar" else trimestres[trimestre_num][1]
                    else:
                        nota = trimestres_borrar[trimestre_num][1] if accion == "borrar" else trimestres[trimestre_num][1]

                    print(f"Procesando datos para {nombre_estudiante}...")
                    row_inputs = row.query_selector_all('input.form-control.text-center.text-uppercase')
                    for idx, input_element in enumerate(row_inputs):
                        if not input_element:
                            print(f"  - Campo {idx + 1} no encontrado, saltando.")
                            continue

                        input_element.fill("")
                        input_element.fill(nota)
                        print(f"  - Campo {idx + 1} rellenado con nota: {nota}")
                    time.sleep(1)

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

                        guardar_button = page.wait_for_selector(
                            'button.swal2-confirm.swal2-styled', state="visible", timeout=5000)
                        guardar_button.click()
                        print(f"  - Cambios guardados para {nombre_estudiante}")
                        time.sleep(1)

                        ok_button = page.wait_for_selector(
                            'button.swal2-confirm.swal2-styled:has-text(\"OK\")', state="visible", timeout=5000)
                        ok_button.click()
                        print(f"  - Confirmación de guardado OK para {nombre_estudiante}")
                        time.sleep(1)
                    else:
                        print(f"No se encontró el botón de guardar para {nombre_estudiante}")
                except Exception as e:
                    print(f"Error al procesar una fila: {e}")

            next_button = page.query_selector('button.mat-paginator-navigation-next')
            if next_button and next_button.is_enabled():
                next_button.click()
                time.sleep(3)
                page.evaluate("""() => { window.scrollTo(0, 0); }""")
            else:
                break

        print("Datos académicos actualizados correctamente.")
        return True

    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")
        return False

def procesar_todos_los_estudiantes(page, ambito_seleccionado, trimestre_num, accion="llenar"):
    return procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=None, accion=accion)

def procesar_estudiantes_excepciones(page, ambito_seleccionado, trimestre_num, nombres_excepciones, accion="llenar"):
    return procesar_filas(page, ambito_seleccionado, trimestre_num, nombres_excepciones=nombres_excepciones, accion=accion)

def obtener_ambito_y_scrapear(page):
    materia = obtener_materia_usuario()
    if not seleccionar_materia(page, materia['nombre'], materia['jornada']):
        print(f"No se pudo seleccionar la materia {materia['nombre']}")
        return False

    ambitos = obtener_ambitos_usuario(materia)
    print(f"Ámbitos seleccionados para {materia['nombre']}: {ambitos}")

    trimestres_seleccionados = obtener_trimestres_usuario()
    print(f"Trimestres seleccionados: {trimestres_seleccionados}")

    nombres_excepciones = [
        "FONSECA YUGCHA SHIFER MARIOLY",
        "MERA LOOR EILEEN MARIED",
        "VERDUGA RODRIGUEZ EMILIO ALEJANDRO"
    ]

    opcion = input("¿Desea procesar todos los estudiantes o solo las excepciones? (todos/excepciones): ").strip().lower()
    accion = input("¿Qué acción desea realizar? (llenar/borrar): ").strip().lower()
    
    for trimestre_num in trimestres_seleccionados:
        print(f"\nSeleccionando Trimestre {trimestre_num}...")
        seleccionar_trimestre(page, trimestre_num)

        for ambito in ambitos:
            print(f"Procesando Trimestre {trimestre_num} - {ambito}...")
            if opcion == "todos":
                procesar_todos_los_estudiantes(page, ambito, trimestre_num,accion=accion)
            elif opcion == "excepciones":
                procesar_estudiantes_excepciones(page, ambito, trimestre_num, nombres_excepciones,accion=accion)
            else:
                print("Opción no válida. Finalizando...")
                return False

    print("Proceso de scraping finalizado.")
    return True
