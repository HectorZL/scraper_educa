import os
import re

def get_user_data_dir():
    """Obtiene el directorio de datos de usuario de Microsoft Edge."""
    username = os.getlogin()
    possible_drives = ['C', 'D', 'E']
    for drive in possible_drives:
        user_data_dir = f"{drive}:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"
        if os.path.exists(user_data_dir):
            return user_data_dir
    raise FileNotFoundError("No se encontró el directorio de datos de usuario en los discos C, D o E.")


