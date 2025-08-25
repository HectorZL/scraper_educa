from config import load_credentials
from auth import navigate_and_authenticate
from utils import get_user_data_dir, seleccionar_grado, seleccionar_jornada
from course_scraper import obtener_ambito_y_scrapear
from playwright.sync_api import sync_playwright
import os

def main():
    try:
        os.system("taskkill /IM msedge.exe /F")
    except Exception as e:
        print(f"Error al cerrar instancias de Microsoft Edge: {str(e)}")

    correo_login, contraseña = load_credentials('credenciales.data')
    user_data_dir = get_user_data_dir()

    # Seleccionar grado y jornada
    print("\n=== SELECCIÓN DE GRADO Y JORNADA ===")
    grado_seleccionado = seleccionar_grado()
    jornada = seleccionar_jornada()
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=False, args=["--start-maximized"])
            context = browser.new_context(viewport={"width": 1920, "height": 1080})

            try:
                page = navigate_and_authenticate(context, correo_login, contraseña)
                if page:
                    print("\nLogin exitoso. Iniciando scraping...")
                    obtener_ambito_y_scrapear(page, grado_seleccionado, jornada)
                else:
                    print("Fallo en autenticación.")
            except Exception as e:
                print(f"Error en el flujo principal: {e}")
            finally:
                browser.close()
        except Exception as e:
            print(f"Error al lanzar el navegador: {e}")

if __name__ == "__main__":
    main()
