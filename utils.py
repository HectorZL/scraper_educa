import os
import re
from academic_data import materias

def obtener_materia_usuario():
    print("Seleccione una materia:")
    for idx, materia in enumerate(materias, 1):
        print(f"{idx}. {materia['nombre']} - {materia['jornada']}")

    while True:
        try:
            seleccion = int(input("Ingrese el número correspondiente a la materia: "))
            if 1 <= seleccion <= len(materias):
                return materias[seleccion - 1]
            else:
                print("Número fuera de rango. Intente de nuevo.")
        except ValueError:
            print("Entrada no válida. Ingrese un número.")

def get_user_data_dir():
    """Obtiene el directorio de datos de usuario de Microsoft Edge."""
    username = os.getlogin()
    possible_drives = ['C', 'D', 'E']
    for drive in possible_drives:
        user_data_dir = f"{drive}:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"
        if os.path.exists(user_data_dir):
            return user_data_dir
    raise FileNotFoundError("No se encontró el directorio de datos de usuario en los discos C, D o E.")


