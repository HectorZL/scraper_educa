import os
import re
from academic_data import materias, grados_y_materias


def _construir_materia(nombre, jornada):
    """Devuelve un diccionario de materia con sus ámbitos si existen."""
    jornada_normalizada = jornada.lower()
    nombre_normalizado = nombre.lower()
    for materia in materias:
        if materia['nombre'].lower() == nombre_normalizado and materia['jornada'].lower() == jornada_normalizada:
            return {
                'nombre': nombre,
                'jornada': jornada,
                'ambitos': materia.get('ambitos', [])
            }

    print(f"Advertencia: no se encontraron ámbitos configurados para la materia '{nombre}' en la jornada '{jornada}'.")
    return {
        'nombre': nombre,
        'jornada': jornada,
        'ambitos': []
    }

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
    
    # Llamar a la función de múltiples materias pero devolver solo la primera
    materias_seleccionadas = obtener_materias_usuario(grado_seleccionado, jornada, multiple=False)
    return materias_seleccionadas[0] if materias_seleccionadas else None

def obtener_materias_usuario(grado_seleccionado, jornada, multiple=True):
    """Muestra las materias disponibles para el grado seleccionado y permite seleccionar una o varias.
    
    Args:
        grado_seleccionado: Grado seleccionado por el usuario
        jornada: Jornada seleccionada (MATUTINA/VESPERTINA)
        multiple: Si es True, permite seleccionar múltiples materias. Si es False, solo una.
    
    Returns:
        Lista de diccionarios con las materias seleccionadas, cada una con nombre y jornada.
    """
    print(f"\nMaterias disponibles para {grado_seleccionado} - Jornada {jornada}:")
    materias_grado = grados_y_materias[grado_seleccionado]
    
    # Mostrar las materias disponibles
    for idx, materia in enumerate(materias_grado, 1):
        print(f"{idx}. {materia}")
    
    while True:
        try:
            if multiple:
                print("\nIngrese los números de las materias separados por comas (ejemplo: 1,3,5)")
                print("O ingrese 't' para seleccionar todas las materias")
                seleccion = input("Selección: ").strip()
                
                if seleccion.lower() == 't':
                    # Seleccionar todas las materias
                    return [_construir_materia(m, jornada) for m in materias_grado]
                
                # Procesar múltiples selecciones
                try:
                    selecciones = [int(s.strip()) for s in seleccion.split(',')]
                    if all(1 <= s <= len(materias_grado) for s in selecciones):
                        return [
                            _construir_materia(materias_grado[s-1], jornada)
                            for s in sorted(set(selecciones))  # Eliminar duplicados y ordenar
                        ]
                    print("Algunos números están fuera de rango. Intente de nuevo.")
                except ValueError:
                    print("Entrada no válida. Ingrese números separados por comas.")
            else:
                # Comportamiento para selección única (compatibilidad con código existente)
                seleccion = int(input("\nIngrese el número correspondiente a la materia: "))
                if 1 <= seleccion <= len(materias_grado):
                    return [_construir_materia(materias_grado[seleccion - 1], jornada)]
                print("Número fuera de rango. Intente de nuevo.")
                
        except ValueError:
            print("Entrada no válida. Ingrese un número.")
        except Exception as e:
            print(f"Error: {e}. Intente nuevamente.")

def get_user_data_dir():
    """Obtiene el directorio de datos de usuario de Microsoft Edge."""
    username = os.getlogin()
    possible_drives = ['C', 'D', 'E']
    for drive in possible_drives:
        user_data_dir = f"{drive}:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"
        if os.path.exists(user_data_dir):
            return user_data_dir
    raise FileNotFoundError("No se encontró el directorio de datos de usuario en los discos C, D o E.")
