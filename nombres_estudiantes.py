def normalize_text(text):
    text = text.strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'\s+', ' ', text)
    return text
import unicodedata
import re



trimestres_borrar = {
    1: ("TRIMESTRE 1", "NE"),
    2: ("TRIMESTRE 2", "NE"),
    3: ("TRIMESTRE 3", "NE")
}

trimestres_borrar_malos= {
    1: ("TRIMESTRE 1", "NE"),
    2: ("TRIMESTRE 2", "NE"),
    3: ("TRIMESTRE 3", "NE")
}

trimestres = {
    1: ("TRIMESTRE 1", "C+"),
    2: ("TRIMESTRE 2", "B+"),
    3: ("TRIMESTRE 3", "A+")
}

trimestres_excepciones = {
    1: ("TRIMESTRE 1", "NE"),
    2: ("TRIMESTRE 2", "NE"),
    3: ("TRIMESTRE 3", "NE")
}

notas_personalizadas = {
    normalize_text("CAGUA MURILLO ELIAN JARED"): {
        1: "B+",
        2: "B+",
        3: "B+"
    }
}

# Lista de estudiantes con notas especificas (bulk import)
lista_estudiantes_notas = {
    "ARTEAGA MONTES DANNA NARCISA": "A+",
    "BENAVIDES SABANDO KEYLER FERNANDO": "A-",
    "BRAVO CHEME HELI YASU": "B+",
    "CAGUA CHILA KEYSI ALEJANDRA": "A+",
    "CEDEÑO DELGADO FERNANDO IZAEL": "A+",
    "COBEÑA GUDIÑO NOAH JONAIKER": "A+",
    "COTERA GARCIA BAYOLETH ISABELLA": "A+",
    "DÁVILA VERA MÍA SALOMÉ": "A+",
    "ESPINOZA JAMA BRIANA ISABELLA": "A+",
    "GARCÍA GRACIA EITHAN ORLEY": "A-",
    "GRACIA MARTÍNEZ KAREN LIXE": "B+",
    "LUCAS FIGUEROA ELIF VALENTINA": "A+",
    "MARCILLO CHILLA KEISHA FIORELLA": "A+",
    "MEJIA ZAMBRANO JAHDIEL ISAAC": "A+",
    "ORTIZ CHAVEZ MELINA LORELY": "A+",
    "PÀRRAGA OBANDO LEAH MERELIN": "A+",
    "PINARGOTE ORTIZ MARA PAULETH": "A+",
    "PUERTAS MERA EDITH SARAI": "A+",
    "QUIJIJE PILAMUNGA JHOAN SEBASTIAN": "A+",
    "ROBLES ANCHUNDIA AYTHANA VICTORIA": "A+",
    "SANTANA LOOR ORIANA VALENTINA": "A-",
    "TUMBACO DOMINGUEZ SARAI BETSABETH": "A+",
    "VALENCIA BERMÙDEZ ELENA SOFIA": "A+",
    "VALLE ROMERO SARAHI NICOLE": "A+",
    "VELÁSQUEZ FALCON ASLAN FABIÁN": "A-",
    "VELIZ ZAMBRANO ALEXANDER RICARDO": "A+",
    "ZAMBRANO ZAMBRANO MARIA JOSE": "A+"
}