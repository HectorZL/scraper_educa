from bs4 import BeautifulSoup
import time

# Diccionario que mapea números a ámbitos
ambitos = {
    1: "IDENTIDAD Y AUTONOMÍA",
    2: "CONVIVENCIA",
    3: "RELACIONES CON EL MEDIO NATURAL Y CULTURAL",
    4: "RELACIONES LÓGICO-MATEMÁTICAS",
    5: "COMPRENSIÓN Y EXPRESIÓN DEL LENGUAJE",
    6: "EXPRESIÓN ARTÍSTICA",
    7: "EXPRESIÓN CORPORAL Y MOTRICIDAD"
}

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
            else:
                print("Ningún número válido ingresado. Por favor, ingrese números entre 1 y 7.")
        except ValueError:
            print("Entrada no válida. Use números separados por comas (ejemplo: 1,2,3)")

def scrape_academic_data(page, ambito_seleccionado):
    print("Scraping academic data...")
    try:
        base_url = "https://academico.educarecuador.gob.ec/academico-servicios/pages/calificacion_ordinaria"
        page.goto(base_url, wait_until="domcontentloaded")

        # Ajustar viewport y pequeñas esperas de sincronización
        page.set_viewport_size({"width": 1920, "height": 1080})
        time.sleep(1)

        # Seleccionar ámbito
        page.wait_for_selector('mat-icon.material-icons:has-text("label_important")',
                               state="visible",
                               timeout=20000)
        page.click('mat-icon.material-icons:has-text("label_important")')
        time.sleep(2)
        page.select_option('select[name="codigoAmbito"]', label=ambito_seleccionado)
        time.sleep(2)

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

                    if fila_idx >= total_filas:
                        break  # Si la tabla cambió radicalmente, evitamos error

                    row = rows[fila_idx]
                    print(f"  Procesando fila {fila_idx+1} de {total_filas}")

                    # Llenar inputs de la fila actual
                    row_inputs = row.query_selector_all('input.form-control.text-center.text-uppercase')
                    for input_element in row_inputs:
                        input_element.fill("")
                        input_element.fill("C+")
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
    ambitos_seleccionados = obtener_ambitos_usuario()
    print(f"Procesando ámbitos: {ambitos_seleccionados}")
    
    for ambito in ambitos_seleccionados:
        print(f"\nProcesando ámbito: {ambito}")
        success = scrape_academic_data(page, ambito)
        if success:
            print(f"Scraping completado exitosamente para {ambito}")
        else:
            print(f"Error durante el scraping de {ambito}")