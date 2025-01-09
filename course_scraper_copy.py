from bs4 import BeautifulSoup
import time

# Diccionarios de mapeo
ambitos = {
    1: "IDENTIDAD Y AUTONOMÍA",
    2: "CONVIVENCIA",
    3: "RELACIONES CON EL MEDIO NATURAL Y CULTURAL",
    4: "RELACIONES LÓGICO-MATEMÁTICAS",
    5: "COMPRENSIÓN Y EXPRESIÓN DEL LENGUAJE",
    6: "EXPRESIÓN ARTÍSTICA",
    7: "EXPRESIÓN CORPORAL Y MOTRICIDAD"
}

trimestres = {
    1: ("TRIMESTRE 1", "B+"),
    2: ("TRIMESTRE 2", "A-"),
    3: ("TRIMESTRE 3", "A+")
}

def obtener_trimestres_usuario():
    while True:
        try:
            entrada = input("Ingrese los números de trimestres separados por comas (1-3), ejemplo '1,2': ")
            numeros = [int(num.strip()) for num in entrada.split(',')]
            trimestres_seleccionados = []
            
            for num in numeros:
                if num in trimestres:
                    trimestres_seleccionados.append(num)
                else:
                    print(f"Trimestre {num} no válido, ignorando...")
            
            if trimestres_seleccionados:
                return trimestres_seleccionados
            print("Ningún trimestre válido ingresado. Por favor, ingrese números entre 1 y 3.")
        except ValueError:
            print("Entrada no válida. Use números separados por comas (ejemplo: 1,2)")

def obtener_ambitos_usuario():
    while True:
        try:
            entrada = input("Ingrese los números de ámbitos separados por comas (1-7), ejemplo '1,2,3': ")
            numeros = [int(num.strip()) for num in entrada.split(',')]
            ambitos_seleccionados = []
            
            for num in numeros:
                if num in ambitos:
                    ambitos_seleccionados.append(ambitos[num])
                else:
                    print(f"Número {num} no válido, ignorando...")
            
            if ambitos_seleccionados:
                return ambitos_seleccionados
            print("Ningún número válido ingresado. Por favor, ingrese números entre 1 y 7.")
        except ValueError:
            print("Entrada no válida. Use números separados por comas (ejemplo: 1,2,3)")

def seleccionar_trimestre(page, trimestre_num):
    try:
        print(f"Intentando seleccionar trimestre {trimestre_num}...")

        label_icon = page.wait_for_selector('mat-icon.material-icons:has-text("label_important")', state="visible", timeout=20000)
        if label_icon:
            label_icon.click()
            time.sleep(1)

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


def scrape_academic_data(page, ambito_seleccionado, trimestre_num):
    print(f"Procesando {ambito_seleccionado} para Trimestre {trimestre_num}...")
    try:
        base_url = "https://academico.educarecuador.gob.ec/academico-servicios/pages/calificacion_ordinaria"
        
        # Navegar a la página
        page.goto(base_url, wait_until="networkidle", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # NUEVO: Primer clic en el ícono label_important para abrir el panel
        print("Abriendo panel de selección...")
        label_icon = page.wait_for_selector('mat-icon.material-icons:has-text("label_important")',
                                          state="visible",
                                          timeout=20000)
        if not label_icon:
            print("No se encontró el ícono de selección")
            return False
            
        # Hacer clic en el ícono
        label_icon.click()
        time.sleep(2)

        # Ahora sí procedemos con la selección de trimestre
        if not seleccionar_trimestre(page, trimestre_num):
            print("No se pudo seleccionar el trimestre")
            return False

        # Continuar con la selección del ámbito
        try:
            print("Seleccionando ámbito...")
            page.select_option('select[name="codigoAmbito"]', label=ambito_seleccionado)
            time.sleep(2)
        except Exception as e:
            print(f"Error al seleccionar ámbito: {e}")
            return False

        # Verificar que la tabla se ha cargado
        page.wait_for_selector('table tbody tr', state="visible", timeout=10000)

        # Bucle de paginación
        while True:
            # Esperar a que la tabla sea visible
            page.wait_for_selector('table tbody tr', state="visible", timeout=5000)
            time.sleep(1)

            # Identificar cuántas filas hay en la tabla
            rows = page.query_selector_all('table tbody tr')
            total_filas = len(rows)
            print(f"Encontradas {total_filas} filas en esta página.")

            # Índice manual para poder relocalizar las filas tras cada guardado
            fila_idx = 0

            while fila_idx < total_filas:
                try:
                    # Reobtenemos las filas en cada iteración,
                    # por si la tabla se re-renderiza al guardar la anterior
                    rows = page.query_selector_all('table tbody tr')
                    total_filas = len(rows)

                    if (fila_idx >= total_filas):
                        break  # Si la tabla cambió radicalmente, evitamos error

                    row = rows[fila_idx]
                    print(f"  Procesando fila {fila_idx+1} de {total_filas}")

                    # Llenar inputs de la fila actual
                    row_inputs = row.query_selector_all('input.form-control.text-center.text-uppercase')
                    for input_element in row_inputs:
                        input_element.fill("")
                        input_element.fill(trimestres[trimestre_num][1])  # Usa la nota correspondiente al trimestre
                    time.sleep(1)

                    # Botón de guardar de la fila
                    save_button = row.query_selector('button.btn.btn-icon.btn-outline-primary')
                    if not save_button:
                        print(f"  Fila {fila_idx+1} sin botón de guardar, saltando...")
                        fila_idx += 1
                        continue

                    # Scroll para visibilizarlo
                    page.evaluate(
                        """(btn) => {
                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                            window.scrollBy(0, -100);
                        }""", 
                        save_button
                    )
                    time.sleep(1)

                    # Clic en guardar
                    save_button.click()
                    time.sleep(1)

                    # Confirmar guardado
                    guardar_button = page.wait_for_selector(
                        'button.swal2-confirm.swal2-styled',
                        state="visible",
                        timeout=5000
                    )
                    guardar_button.click()
                    print(f"    Fila {fila_idx+1}: Confirmación guardada")
                    time.sleep(2)

                    # Confirmar con OK
                    ok_button = page.wait_for_selector(
                        'button.swal2-confirm.swal2-styled:has-text("OK")',
                        state="visible",
                        timeout=5000
                    )
                    ok_button.click()
                    print(f"    Fila {fila_idx+1}: OK confirmado")
                    time.sleep(2)

                    # Esperar a que la tabla se re-renderice
                    page.wait_for_selector('table tbody tr', state="visible", timeout=5000)
                    time.sleep(1)

                except Exception as e:
                    print(f"Error en fila {fila_idx+1}: {e}")

                # Pasar a la siguiente fila
                fila_idx += 1

            # Revisión del paginador para ver si se continúa o se termina
            paginator = page.query_selector('.mat-paginator-range-label')
            if paginator:
                range_text = paginator.inner_text()
                current_end = int(range_text.split('–')[1].split('of')[0].strip())
                # Ajustar 30 al total de tu caso real
                if current_end >= 30:
                    break
                # Botón siguiente
                next_button = page.query_selector('button.mat-paginator-navigation-next')
                if next_button and next_button.is_visible():
                    print("Avanzando a la siguiente página...")
                    next_button.click()
                    time.sleep(3)
                    continue
            break

        print("Datos académicos actualizados correctamente.")
        return True

    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")
        return False

# course_scraper.py
def obtener_ambito_y_scrapear(page):
    # Primero seleccionar trimestres
    trimestres_seleccionados = obtener_trimestres_usuario()
    print(f"Trimestres seleccionados: {trimestres_seleccionados}")
    
    # Luego seleccionar ámbitos
    ambitos_seleccionados = obtener_ambitos_usuario()
    print(f"Ámbitos seleccionados: {ambitos_seleccionados}")
    
    # Procesar cada combinación de trimestre y ámbito
    for trimestre in trimestres_seleccionados:
        for ambito in ambitos_seleccionados:
            print(f"\nProcesando Trimestre {trimestre} - {ambito}")
            success = scrape_academic_data(page, ambito, trimestre)
            if success:
                print(f"Completado: Trimestre {trimestre} - {ambito}")
            else:
                print(f"Error en: Trimestre {trimestre} - {ambito}")