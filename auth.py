import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def is_logged_in(page):
    """
    Verifica si el usuario está autenticado comprobando la presencia de un elemento específico en la página de inicio.
    """
    try:
        # Intentar localizar el elemento de usuario en la navbar
        return page.is_visible("li.nav-item.dropdown-user.dropdown")
    except Exception:
        return False

def perform_login(page, correo_login, contraseña):
    """
    Completa el formulario de login y envía las credenciales.
    """
    try:
        print("Iniciando proceso de autenticación...")
        # Esperar y llenar el campo de usuario
        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/authentication/login-v2")
        page.wait_for_selector("input[formcontrolname='usuario']", timeout=20000)
        page.fill("input[formcontrolname='usuario']", correo_login)
        
        # Esperar y llenar el campo de contraseña
        page.wait_for_selector("input[formcontrolname='password']", timeout=20000)
        page.fill("input[formcontrolname='password']", contraseña)
        
        # Click en el botón de login
        page.click("button.btn.btn-primary.btn-block")
        
        # Esperar a que la URL cambie a la página de inicio después de login
        page.wait_for_url("https://academico.educarecuador.gob.ec/academico-servicios/pages/inicio", timeout=3000)
        print("Autenticación completada y redirigido a la página de inicio.")
    except PlaywrightTimeoutError:
        print("Timeout al intentar autenticarse. Verifica tus credenciales o la conectividad.")
        raise
    except Exception as e:
        print(f"Error durante la autenticación: {e}")
        raise

def navigate_and_authenticate(context, correo_login, contraseña):
    """
    Navega a la página de inicio y verifica si el usuario está autenticado. Si no lo está, realiza el login.
    Retorna la página autenticada.
    """
    page = context.new_page()
    
    try:
        # Navegar a la página de inicio
        page.goto("https://academico.educarecuador.gob.ec/academico-servicios/pages/inicio", wait_until="domcontentloaded")
        
        # Verificar si el usuario está autenticado
        if not is_logged_in(page):
            print("El usuario aún no está autenticado. Procediendo con login...")
            perform_login(page, correo_login, contraseña)
            
            # Verificar nuevamente después del login
            if is_logged_in(page):
                print("Login exitoso.")
            else:
                print("Login fallido. Verifica tus credenciales.")
                raise Exception("Autenticación fallida.")
        else:
            print("El usuario ya está autenticado.")
        
        return page  # Retornar la página para uso posterior
    except Exception as e:
        print(f"Error en navigate_and_authenticate: {e}")
        context.close()
        raise


