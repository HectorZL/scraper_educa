import pandas as pd
import openpyxl
from collections import OrderedDict

def crear_mapa_calificaciones(ruta_archivo: str) -> dict:
    """
    Crea un mapa de calificaciones de estudiantes con materias específicas en orden.
    """
    # Lista de materias en el orden específico
    MATERIAS_ORDENADAS = [
        'LENGUA Y LITERATURA',
        'MATEMÁTICA',
        'ESTUDIOS SOCIALES',
        'CIENCIAS NATURALES',
        'EDUCACIÓN CULTURAL Y ARTÍSTICA',
        'EDUCACIÓN FÍSICA',
        'INGLÉS',
        'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
        'ANIMACIÓN A LA LECTURA'
    ]
    
    try:
        print(f"Procesando archivo: {ruta_archivo}")

        # Detectar hojas disponibles y permitir que el usuario elija
        libro = openpyxl.load_workbook(ruta_archivo, read_only=True)
        hojas = libro.sheetnames
        print("\nHojas disponibles en el archivo:")
        for i, nombre_hoja in enumerate(hojas, 1):
            print(f"{i}. {nombre_hoja}")

        while True:
            try:
                seleccion_hoja = int(input("\nIngrese el número de la hoja a usar para las notas: ").strip())
                if 1 <= seleccion_hoja <= len(hojas):
                    hoja_seleccionada = hojas[seleccion_hoja - 1]
                    break
                else:
                    print("Número fuera de rango. Intente nuevamente.")
            except ValueError:
                print("Entrada no válida. Ingrese un número de la lista.")

        print(f"\nUsando la hoja: {hoja_seleccionada}")

        # Leer el archivo sin asumir estructura usando la hoja seleccionada
        df = pd.read_excel(
            ruta_archivo,
            sheet_name=hoja_seleccionada,
            header=None,
            engine='openpyxl'
        )
        
        # Buscar la fila que contiene los encabezados
        header_row = None
        for i in range(min(20, len(df))):  # Buscar en las primeras 20 filas
            row = df.iloc[i].astype(str).str.upper().str.strip()
            # Verificar si alguna celda de la fila contiene 'APELLIDOS/NOMBRES'
            if 'APELLIDOS/NOMBRES' in row.values:
                header_row = i
                break
        
        if header_row is None:
            print("No se encontró la fila de encabezados. Usando la primera fila.")
            header_row = 0
        
        # Volver a leer el archivo con los encabezados correctos
        df = pd.read_excel(
            ruta_archivo,
            sheet_name=hoja_seleccionada,
            header=header_row,
            engine='openpyxl'
        )
        
        # Limpiar nombres de columnas
        df.columns = df.columns.astype(str).str.upper().str.strip()
        
        # Buscar la columna de estudiantes
        col_estudiante = None
        posibles_nombres = ['APELLIDOS/NOMBRES', 'NOMBRE', 'ESTUDIANTE', 'ALUMNO']
        for nombre in posibles_nombres:
            if nombre in df.columns:
                col_estudiante = nombre
                break
        
        if not col_estudiante:
            # Usar la primera columna no numérica
            for col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    col_estudiante = col
                    break
        
        if not col_estudiante:
            print("No se pudo identificar la columna de estudiantes.")
            return {}
        
        print(f"\nColumna de estudiantes: {col_estudiante}")
        
        # Filtrar solo las columnas que necesitamos
        columnas_necesarias = [col_estudiante]
        
        # Mapeo de variaciones de nombres de materias
        mapeo_materias = {
            'LENGUA': 'LENGUA Y LITERATURA',
            'LENGUAJE': 'LENGUA Y LITERATURA',
            'LENGUA Y LIT': 'LENGUA Y LITERATURA',
            'MATEMATICAS': 'MATEMÁTICA',
            'MATE': 'MATEMÁTICA',
            'SOCIALES': 'ESTUDIOS SOCIALES',
            'CIENCIAS': 'CIENCIAS NATURALES',
            'NATURALES': 'CIENCIAS NATURALES',
            'CULTURAL': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'ARTE': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'ARTÍSTICA': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'EDUCACION CULTURAL': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'FISICA': 'EDUCACIÓN FÍSICA',
            'EDUCACION FISICA': 'EDUCACIÓN FÍSICA',
            'INGLES': 'INGLÉS',
            'CIVICA': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'ACOMPAÑAMIENTO': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'LECTURA': 'ANIMACIÓN A LA LECTURA',
            'ANIMACION': 'ANIMACIÓN A LA LECTURA'
        }
        
        # Normalizar nombres de materias
        materias_encontradas = {}
        for col in df.columns:
            if col == col_estudiante:
                continue
                
            # Convertir a mayúsculas y limpiar
            materia = str(col).upper().strip()
            
            # Buscar coincidencias parciales
            for key, value in mapeo_materias.items():
                if key in materia:
                    materia = value
                    break
            
            # Si la materia está en nuestra lista de materias ordenadas, la añadimos
            if materia in MATERIAS_ORDENADAS:
                materias_encontradas[col] = materia
                columnas_necesarias.append(col)
        
        # Filtrar el dataframe
        df_filtrado = df[columnas_necesarias].copy()
        
        # Renombrar columnas de materias
        rename_cols = {col_estudiante: 'ESTUDIANTE'}
        for col, materia in materias_encontradas.items():
            rename_cols[col] = materia
        
        df_filtrado = df_filtrado.rename(columns=rename_cols)
        
        # Eliminar filas vacías o con nombres muy cortos
        df_filtrado = df_filtrado[df_filtrado['ESTUDIANTE'].notna()]
        df_filtrado = df_filtrado[df_filtrado['ESTUDIANTE'].astype(str).str.strip().str.len() > 3]
        
        if df_filtrado.empty:
            print("No se encontraron datos de estudiantes después de la limpieza.")
            return {}
        
        # Ordenar las columnas según el orden especificado
        columnas_ordenadas = ['ESTUDIANTE'] + [m for m in MATERIAS_ORDENADAS if m in df_filtrado.columns]
        df_ordenado = df_filtrado[columnas_ordenadas].copy()
        
        # Asegurarse de que todas las materias estén en el DataFrame
        for materia in MATERIAS_ORDENADAS:
            if materia not in df_ordenado.columns:
                df_ordenado.loc[:, materia] = None
        
        # Aplicar las reglas especiales
        for i, row in df_ordenado.iterrows():
            # 1. Para CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA, establecer valor por defecto
            if 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA' in df_ordenado.columns:
                if pd.isna(row['CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA']) or row['CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA'] == '':
                    df_ordenado.at[i, 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA'] = 'FRECUENTEMENTE'
            
            # 2. Para ANIMACIÓN A LA LECTURA, copiar el valor de LENGUA Y LITERATURA si está vacío
            if 'ANIMACIÓN A LA LECTURA' in df_ordenado.columns and 'LENGUA Y LITERATURA' in df_ordenado.columns:
                if (pd.isna(row['ANIMACIÓN A LA LECTURA']) or row['ANIMACIÓN A LA LECTURA'] == '') and pd.notna(row['LENGUA Y LITERATURA']):
                    df_ordenado.at[i, 'ANIMACIÓN A LA LECTURA'] = row['LENGUA Y LITERATURA']
        
        # Debug: mostrar un resumen del DataFrame resultante
        print("\n=== RESUMEN DEL DATAFRAME DE NOTAS (df_ordenado) ===")
        print(f"Filas: {len(df_ordenado)}, Columnas: {len(df_ordenado.columns)}")
        print("Columnas:")
        for col in df_ordenado.columns:
            print(f"  - {col}")

        print("\nPrimeros 10 estudiantes con sus notas:")
        try:
            print(df_ordenado.head(10).to_string(index=False))
        except Exception as e:
            print(f"Error al imprimir df_ordenado: {e}")

        # Convertir a diccionario ordenado
        mapa_final = OrderedDict()
        for _, row in df_ordenado.iterrows():
            estudiante = row['ESTUDIANTE']
            calificaciones = {}
            for materia in MATERIAS_ORDENADAS:
                if materia in row:
                    calificaciones[materia] = row[materia] if pd.notna(row[materia]) else None
            mapa_final[estudiante] = calificaciones
        
        print(f"\nProcesamiento completado. Se encontraron {len(mapa_final)} estudiantes.")
        print("Materias encontradas:")
        for i, materia in enumerate(MATERIAS_ORDENADAS, 1):
            print(f"{i}. {materia}")
        
        return mapa_final
        
    except Exception as e:
        print(f"\nError al procesar el archivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    nombre_archivo = 'sb.xlsx'
    print(f"Iniciando procesamiento de archivo: {nombre_archivo}")
    
    # Llamar a la función para crear el mapa de calificaciones
    mapa_de_estudiantes = crear_mapa_calificaciones(nombre_archivo)

    # Mostrar una muestra de los datos procesados
    if mapa_de_estudiantes:
        print("\n--- Muestra de estudiantes procesados ---")
        for i, (estudiante, calificaciones) in enumerate(mapa_de_estudiantes.items()):
            if i >= 3:  # Mostrar solo los primeros 3 estudiantes
                print("...")
                break
            print(f"\nEstudiante: {estudiante}")
            print("Calificaciones:")
            for materia, calificacion in calificaciones.items():
                if pd.notna(calificacion):
                    print(f"  - {materia}: {calificacion}")
    else:
        print("\nNo se pudieron procesar los datos. Verifica el archivo y la estructura de la hoja.")