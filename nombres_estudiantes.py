def normalize_text(text):
    text = text.strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    return text
import unicodedata
import re

nombres_buenos = [
    "LARA MEDINA JOSIMAR BLADIMIR"
]

nombres_malos = [
    "ÑACATA FUENTES RIHANNA FERNANDA",
    "GARCIA ROBLES JUNIOR SANTHIAGO"
]

nombres_excepciones = [
    "BRIONES PACHECO DAVANID MARTIN",
    "RODRIGUEZ SINCHIGUANO KATY EMILIANA",
    # Agrega aquí más nombres de estudiantes que serán excepciones
]

notas_personalizadas = {
    normalize_text("LARA MEDINA JOSIMAR BLADIMIR"): {
        1: "C+",
        2: "C+",
        3: "C+"
    },
    normalize_text("MALDONADO GONZALEZ GERALD ALFREDO"): {
        1: "C-",
        2: "C-",
        3: "C-"
    },
    normalize_text("CHERNE CASTILLO JEISY EMIR"): {
        1: "D+",
        2: "D+",
        3: "D+"
    },
    normalize_text("CHERNE BATIOJA CESAR GERALDO"): {
        1: "D-",
        2: "D-",
        3: "D-"
    },
    normalize_text("BARRAGAN NAPA GREY ESCARLETH"): {
        1: "C+",
        2: "E-",
        3: "E-"
    }
}