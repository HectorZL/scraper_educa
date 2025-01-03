from config import load_credentials
from auth import navigate_and_authenticate  # Actualizar la importación
from course_scraper import obtener_ambito_y_scrapear
from utils import get_user_data_dir
from playwright.sync_api import sync_playwright
import os  # Asegurarse de importar 'os'

def main():
    try:
        # Intentar cerrar todas las instancias de Microsoft Edge
        os.system("taskkill /IM msedge.exe /F")
    except Exception as e:
        print(f"Error al cerrar instancias de Microsoft Edge: {str(e)}")

    # Cargar credenciales desde el archivo 'credenciales.data'
    correo_login, contraseña = load_credentials('credenciales.data')

    # Obtener el directorio de datos de usuario si es necesario
    user_data_dir = get_user_data_dir()

    with sync_playwright() as p:
        try:
            # Lanzar el navegador Microsoft Edge
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
                args=["--start-maximized"],
                # Removido 'viewport' de aquí
            )

            # Crear un nuevo contexto con el viewport especificado
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                # user_data_dir=user_data_dir  # Descomenta si necesitas reutilizar datos de usuario
            )

            try:
                # Autenticar y obtener la página autenticada
                page = navigate_and_authenticate(context, correo_login, contraseña)

                if page:
                    print("Login successful. Starting scraping...")
                    # Continuar con otras acciones, por ejemplo:
                    obtener_ambito_y_scrapear(page)
                else:
                    print("Login failed.")
            except Exception as e:
                print(f"Error en el flujo principal: {e}")
            finally:
                # Cerrar el navegador
                browser.close()

        except Exception as e:
            print(f"Error al lanzar el navegador: {e}")

if __name__ == "__main__":
    main()
