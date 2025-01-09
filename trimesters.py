
from academic_data import trimestres

def obtener_trimestres_usuario():
    while True:
        try:
            entrada = input("Ingrese los números de trimestres separados por comas (1-3), ejemplo '1,2': ")
            numeros = [int(num.strip()) for num in entrada.split(',')]
            trimestres_seleccionados = []

            for num in numeros:
                if num in trimestres:
                    trimestres_seleccionados.append(num)
                else:
                    print(f"Trimestre {num} no válido, ignorando...")

            if trimestres_seleccionados:
                return trimestres_seleccionados
            print("Ningún trimestre válido ingresado. Por favor, ingrese números entre 1 y 3.")
        except ValueError:
            print("Entrada no válida. Use números separados por comas (ejemplo: 1,2)")
