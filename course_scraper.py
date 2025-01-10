from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import re
from academic_data import trimestres
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

            next_button = page.query_selector('li.page-item:not(.disabled) a.page-link:has-text("Siguiente")')
            if next_button:
                next_button.click()
                pagina_actual += 1
                page.wait_for_load_state('networkidle')
            else:
                print("No hay más páginas disponibles.")
                break

        print(f"No se encontró la materia '{nombre}' con la jornada '{jornada}'.")
        return False
    except Exception as e:
        print(f"Error al seleccionar la materia '{nombre}': {e}")
        return False

def scrape_academic_data(page, ambito_seleccionado, trimestre_num):
    print(f"Procesando {ambito_seleccionado} para Trimestre {trimestre_num}...")
    try:
        print("Seleccionando ámbito...")
        #page.wait_for_selector('select[name="codigoAmbito"]', state="visible", timeout=10000)

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

        # Volver a la primera página antes de procesar filas
        print("Volviendo a la primera página...")
        while True:
            prev_button = page.query_selector('button.mat-paginator-navigation-previous')
            if prev_button and not prev_button.is_disabled():
                prev_button.click()
                time.sleep(1)
            else:
                print("Ya estamos en la primera página.")
                break

        page.wait_for_selector('table tbody tr', state="visible", timeout=10000)
        page.evaluate("""() => { window.scrollTo(0, 0); }""")
        time.sleep(1)

        while True:
            # Reobtención de filas en cada iteración
            rows = page.query_selector_all('table tbody tr')
            total_filas = len(rows)
            print(f"Encontradas {total_filas} filas en esta página.")

            fila_idx = 0
            while fila_idx < total_filas:
                try:
                    # Reobtener filas después de cada interacción
                    rows = page.query_selector_all('table tbody tr')
                    total_filas = len(rows)

                    if fila_idx >= total_filas:
                        break

                    row = rows[fila_idx]
                    print(f"  Procesando fila {fila_idx + 1} de {total_filas}")

                    row_inputs = row.query_selector_all('input.form-control.text-center.text-uppercase')
                    for input_element in row_inputs:
                        input_element.fill("")
                        input_element.fill(trimestres[trimestre_num][1])
                    time.sleep(1)

                    save_button = row.query_selector('button.btn.btn-icon.btn-outline-primary')
                    if not save_button:
                        print(f"  Fila {fila_idx + 1} sin botón de guardar, saltando...")
                        fila_idx += 1
                        continue

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

                    guardar_button = page.wait_for_selector('button.swal2-confirm.swal2-styled', state="visible", timeout=5000)
                    guardar_button.click()
                    print(f"    Fila {fila_idx + 1}: Confirmación guardada")
                    time.sleep(1)

                    ok_button = page.wait_for_selector('button.swal2-confirm.swal2-styled:has-text("OK")', state="visible", timeout=5000)
                    ok_button.click()
                    print(f"    Fila {fila_idx + 1}: OK confirmado")
                    time.sleep(1)

                except Exception as e:
                    print(f"Error en fila {fila_idx + 1}: {e}")

                # Incrementar índice manualmente
                fila_idx += 1

            next_button = page.query_selector('button.mat-paginator-navigation-next')
            if next_button and next_button.is_enabled():
                print("Avanzando a la siguiente página...")
                next_button.click()
                time.sleep(3)
                page.evaluate("""() => { window.scrollTo(0, 0); }""")
                time.sleep(1)
            else:
                print("No hay más páginas disponibles.")
                break

        print("Datos académicos actualizados correctamente.")
        return True

    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")
        return False


def obtener_ambito_y_scrapear(page):
    # Obtener materia seleccionada por el usuario
    materia = obtener_materia_usuario()
    if not seleccionar_materia(page, materia['nombre'], materia['jornada']):
        print(f"No se pudo seleccionar la materia {materia['nombre']}")
        return False

    # Obtener ámbitos seleccionados por el usuario
    ambitos = obtener_ambitos_usuario(materia)
    print(f"Ámbitos seleccionados para {materia['nombre']}: {ambitos}")

    # Obtener trimestres seleccionados por el usuario
    trimestres_seleccionados = obtener_trimestres_usuario()
    print(f"Trimestres seleccionados: {trimestres_seleccionados}")

    # Iterar por cada trimestre y ámbito
    for trimestre_num in trimestres_seleccionados:
        print(f"\nSeleccionando Trimestre {trimestre_num}...")
        seleccionar_trimestre(page, trimestre_num)

        for ambito in ambitos:
            print(f"Procesando Trimestre {trimestre_num} - {ambito}...")
            if scrape_academic_data(page, ambito, trimestre_num):
                print(f"Datos de {ambito} para el Trimestre {trimestre_num} procesados exitosamente.")
            else:
                print(f"Error al procesar {ambito} para el Trimestre {trimestre_num}.")

    print("Proceso de scraping finalizado.")
    return True
