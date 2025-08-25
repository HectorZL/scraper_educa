import os
import re
from academic_data import materias, grados_y_materias

def seleccionar_grado():
    """Permite al usuario seleccionar un grado escolar."""
    print("\nSeleccione el grado escolar:")
    for idx, grado in enumerate(grados_y_materias.keys(), 1):
        print(f"{idx}. {grado}")
    
    while True:
        try:
            seleccion = int(input("\nIngrese el número correspondiente al grado: "))
            if 1 <= seleccion <= len(grados_y_materias):
                return list(grados_y_materias.keys())[seleccion - 1]
            print("Número fuera de rango. Intente de nuevo.")
        except ValueError:
            print("Entrada no válida. Ingrese un número.")

def seleccionar_jornada():
    """Permite al usuario seleccionar la jornada (MATUTINA/VESPERTINA)."""
    print("\nSeleccione la jornada:")
    print("1. MATUTINA")
    print("2. VESPERTINA")
    
    while True:
        try:
            seleccion = input("\nIngrese el número correspondiente a la jornada (1-2): ").strip()
            if seleccion == '1':
                return "MATUTINA"
            elif seleccion == '2':
                return "VESPERTINA"
            print("Opción no válida. Por favor ingrese 1 o 2.")
        except Exception as e:
            print(f"Error: {e}. Intente nuevamente.")

def obtener_materia_usuario(grado_seleccionado, jornada):
    """Muestra las materias disponibles para el grado seleccionado."""
    print(f"\nMaterias disponibles para {grado_seleccionado} - Jornada {jornada}:")
    materias_grado = grados_y_materias[grado_seleccionado]
    
    for idx, materia in enumerate(materias_grado, 1):
        print(f"{idx}. {materia}")
    
    while True:
        try:
            seleccion = int(input("\nIngrese el número correspondiente a la materia: "))
            if 1 <= seleccion <= len(materias_grado):
                return {
                    'nombre': materias_grado[seleccion - 1],
                    'jornada': jornada
                }
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
