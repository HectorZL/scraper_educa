from config import load_credentials
from auth import login
from course_scraper import obtener_ambito_y_scrapear
from utils import get_user_data_dir
import os

def main():
    try:
        os.system("taskkill /IM msedge.exe /F")
    except Exception as e:
        print(f"Error al cerrar instancias de Microsoft Edge: {str(e)}")

    correo_login, contraseña = load_credentials('credenciales.data')
    user_data_dir = get_user_data_dir()

    try:
        # Desempaquetar los tres valores retornados
        page, context, playwright = login(user_data_dir, correo_login, contraseña)
        if page:
            print("Login successful. Starting scraping...")
            try:
                obtener_ambito_y_scrapear(page)  # Pasar solo la página
            finally:
                context.close()
                playwright.stop()
        else:
            print("Login failed.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
