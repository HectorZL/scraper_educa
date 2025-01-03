def load_credentials(file_path):
    """Carga correo y contraseña desde un archivo de credenciales."""
    with open(file_path, 'r') as f:
        correo_login = f.readline().strip()
        contraseña = f.readline().strip()
    return correo_login, contraseña
