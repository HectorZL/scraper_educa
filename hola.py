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
        
        # 1. Buscar la fila que contiene los nombres ('APELLIDOS/NOMBRES')
        names_row_idx = None
        names_col_idx = None
        
        # Buscar en las primeras 20 filas
        for i in range(min(20, len(df))):
            row_vals = df.iloc[i].astype(str).str.upper().str.strip().tolist()
            if 'APELLIDOS/NOMBRES' in row_vals:
                names_row_idx = i
                names_col_idx = row_vals.index('APELLIDOS/NOMBRES')
                break
        
        if names_row_idx is None:
            print("No se encontró la fila de 'APELLIDOS/NOMBRES'. Usando fila 10 como fallback.")
            names_row_idx = 9
            names_col_idx = 1
        
        # 2. Mapeo de variaciones de nombres de materias
        mapeo_materias = {
            'LENGUA': 'LENGUA Y LITERATURA',
            'LENGUAJE': 'LENGUA Y LITERATURA',
            'MATEMATICAS': 'MATEMÁTICA',
            'MATE': 'MATEMÁTICA',
            'SOCIALES': 'ESTUDIOS SOCIALES',
            'CIENCIAS': 'CIENCIAS NATURALES',
            'NATURALES': 'CIENCIAS NATURALES',
            'CULTURAL': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'ARTE': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'ARTÍSTICA': 'EDUCACIÓN CULTURAL Y ARTÍSTICA',
            'ARÍSTICA': 'EDUCACIÓN CULTURAL Y ARTÍSTICA', # Typo en Excel
            'FISICA': 'EDUCACIÓN FÍSICA',
            'INGLES': 'INGLÉS',
            'CIVICA': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'INTEGRAAL': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'ACOMPAÑAMIENTO': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'ACOMPANAMIENTO': 'CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA',
            'LECTURA': 'ANIMACIÓN A LA LECTURA',
            'LECTUARA': 'ANIMACIÓN A LA LECTURA',
            'ANIMACION': 'ANIMACIÓN A LA LECTURA'
        }
        
        # 3. Detectar qué columna corresponde a cada materia
        # Buscamos el nombre de la materia en las filas superiores
        col_to_materia = {}
        
        # En sb2.xlsx, la fila 6 tiene los nombres de las materias
        # La fila 7 tiene 'PROMEDIO' o 'CALIFICACIÓN' para las materias numéricas
        row_materias = 6
        row_detalles = 7
        
        if len(df) > row_materias:
            row_vals_materias = df.iloc[row_materias].tolist()
            for col_idx, val in enumerate(row_vals_materias):
                cell_val = str(val).upper().strip()
                materia_asignada = None
                for key, mapped_val in mapeo_materias.items():
                    if key in cell_val:
                        materia_asignada = mapped_val
                        break
                
                if materia_asignada:
                    # Si es Cívica o Animación, el valor está en la columna actual (letras)
                    if materia_asignada in ['CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA', 'ANIMACIÓN A LA LECTURA']:
                        col_to_materia[col_idx] = materia_asignada
                    else:
                        # Para otras materias, buscar PROMEDIO o CALIFICACIÓN en las siguientes columnas de la fila 7
                        found_col = False
                        # Revisar desde la columna actual hasta encontrar el siguiente encabezado de materia o 6 columnas
                        for offset in range(0, 7):
                            if col_idx + offset >= df.shape[1]: break
                            
                            # Si es una columna nueva con otro nombre de materia, detener búsqueda
                            if offset > 0:
                                next_val = str(df.iloc[row_materias, col_idx + offset]).upper().strip()
                                if next_val not in ('', 'NAN', 'NONE'): break
                                
                            label_detalle = str(df.iloc[row_detalles, col_idx + offset]).upper().strip()
                            if 'PROMEDIO' in label_detalle or 'CALIFICACIÓN' in label_detalle:
                                col_to_materia[col_idx + offset] = materia_asignada
                                found_col = True
                                break
                        
                        # Fallback: si no encontró PROMEDIO, usar la columna actual
                        if not found_col:
                            col_to_materia[col_idx] = materia_asignada

        print(f"Materias detectadas en columnas: {col_to_materia}")
        
        # Función para mapear letras a palabras descriptivas
        def mapear_calificacion_cualitativa(valor):
            if not valor or pd.isna(valor):
                return None
            val_str = str(valor).upper().strip()
            if 'A+' in val_str or 'A-' in val_str or val_str == 'A':
                return 'SIEMPRE'
            if 'B+' in val_str or 'B-' in val_str or val_str == 'B':
                return 'FRECUENTEMENTE'
            if any(char in val_str for char in ['C', 'D', 'E']):
                return 'OCASIONALMENTE'
            return valor

        # 4. Construir el DataFrame con los datos reales
        estudiantes_data = []
        # Los datos de estudiantes empiezan en names_row_idx + 1
        for i in range(names_row_idx + 1, len(df)):
            nombre_estudiante = str(df.iloc[i, names_col_idx]).strip()
            # Si el nombre es muy corto o vacío, saltar (fin de lista)
            if not nombre_estudiante or len(nombre_estudiante) < 4 or 'PROFESOR' in nombre_estudiante.upper():
                continue
            
            row_dict = {'ESTUDIANTE': nombre_estudiante}
            for col_idx, materia_name in col_to_materia.items():
                val = df.iloc[i, col_idx]
                
                # Aplicar mapeo cualitativo para Cívica y Animación
                if materia_name in ['CÍVICA Y ACOMPAÑAMIENTO INTEGRAL EN EL AULA', 'ANIMACIÓN A LA LECTURA']:
                    val = mapear_calificacion_cualitativa(val)
                
                row_dict[materia_name] = val
            
            estudiantes_data.append(row_dict)
        
        df_ordenado = pd.DataFrame(estudiantes_data)
        
        if df_ordenado.empty:
            print("No se encontraron datos de estudiantes.")
            return {}
        
        # Asegurarse de que todas las materias estén en el DataFrame
        for materia in MATERIAS_ORDENADAS:
            if materia not in df_ordenado.columns:
                df_ordenado.loc[:, materia] = None
                
        # Ordenar las columnas según el orden especificado
        columnas_ordenadas = ['ESTUDIANTE'] + [m for m in MATERIAS_ORDENADAS if m in df_ordenado.columns]
        df_ordenado = df_ordenado[columnas_ordenadas].copy()
        
        # Aplicar las reglas especiales
        for i, row in df_ordenado.iterrows():
            # Para ANIMACIÓN A LA LECTURA, copiar el valor exacto de LENGUA Y LITERATURA
            if 'ANIMACIÓN A LA LECTURA' in df_ordenado.columns and 'LENGUA Y LITERATURA' in df_ordenado.columns:
                lengua = row['LENGUA Y LITERATURA']
                if pd.notna(lengua) and lengua != '':
                    df_ordenado.at[i, 'ANIMACIÓN A LA LECTURA'] = lengua
        
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
    nombre_archivo = 'sb2.xlsx'
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