
from academic_data import materias

def obtener_ambitos_usuario(materia):
    while True:
        try:
            print(f"Ámbitos disponibles para la materia '{materia['nombre']}':")
            for idx, ambito in enumerate(materia['ambitos'], 1):
                print(f"{idx}. {ambito}")

            entrada = input("Ingrese los números de ámbitos separados por comas (ejemplo: '1,2,3'): ")
            numeros = [int(num.strip()) for num in entrada.split(',')]
            ambitos_seleccionados = []

            for num in numeros:
                if 1 <= num <= len(materia['ambitos']):
                    ambitos_seleccionados.append(materia['ambitos'][num - 1])
                else:
                    print(f"Número {num} no válido, ignorando...")

            if ambitos_seleccionados:
                return ambitos_seleccionados
            print("Ningún ámbito válido ingresado. Por favor, intente nuevamente.")
        except ValueError:
            print("Entrada no válida. Use números separados por comas (ejemplo: '1,2,3')")
