from playwright.sync_api import sync_playwright
import time
import re

def login(user_data_dir, correo_login, contraseña):
    """Inicia sesión en el sistema usando Playwright y devuelve la página y el contexto."""
    p = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="msedge",
        headless=False,
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    
    try:
        # Navegar a la página de inicio
        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/inicio", 
                 wait_until="domcontentloaded")
        time.sleep(2)
        
        # Obtener la URL actual
        current_url = page.url
        print(f"URL actual después de navegar a inicio: {current_url}")
        
        # Patrón regex para detectar la página de login
        login_pattern = re.compile(r"https://academico\.educarecuador\.gob\.ec/academico-servicios/pages/authentication/login-v2\?returnUrl=%2Fpages%2Finicio")
        
        # Verificar si estamos en la página de login usando regex
        if re.match(login_pattern, current_url):
            print("Detectada página de login. Iniciando proceso de autenticación...")
            
            # Completar el formulario de login
            page.wait_for_selector("input[formcontrolname='usuario']", timeout=5000, state="visible")
            page.fill("input[formcontrolname='usuario']", correo_login)
            page.fill("input[formcontrolname='password']", contraseña)
            
            # Click en el botón de login
            login_button = page.wait_for_selector("button.btn.btn-primary.btn-block", timeout=3000, state="visible")
            login_button.click()
            
        else:
            print("No se detecta página de login. Asumiendo que el usuario ya está autenticado.")
            
        return page, context, p
        
    except Exception as e:
        print(f"Error en proceso de autenticación: {str(e)}")
        context.close()
        p.stop()
        raise
