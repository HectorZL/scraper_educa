from pathlib import Path
import re
import unicodedata

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from academic_data import grados_y_materias
from config import load_credentials
from orozco_grades import GradeFileError, NameMatchError, OrozcoGradeBook

BASE_URL = "https://www.sistema-orozco.com/app_26_27_c"
PROJECT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = PROJECT_DIR / "c-d-o.data"
BASE_GRADES_FILE = PROJECT_DIR / "notas_orozco.xlsx"
LANGUAGE_GRADES_FILE = PROJECT_DIR / "notas_lengua.xlsx"

TRIMESTERS = [
    ("1t", "1er Trimestre"),
    ("2t", "2do Trimestre"),
    ("3t", "3er Trimestre"),
]

GRADE_ORDER = {
    "inicial": 0,
    "primero": 1,
    "segundo": 2,
    "tercero": 3,
    "cuarto": 4,
    "quinto": 5,
    "sexto": 6,
    "septimo": 7,
    "octavo": 8,
    "noveno": 9,
    "decimo": 10,
}

CANONICAL_SUBJECTS = tuple(
    dict.fromkeys(
        subject
        for subjects in grados_y_materias.values()
        for subject in subjects
    )
)


def normalize_label(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def login_as_teacher(page: Page, username: str, password: str) -> None:
    """Inicia sesión en Sistema Orozco con el perfil Profesor."""
    page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
    page.get_by_text("Ingreso al sistema", exact=True).click()

    form = page.locator("#frmIngresoCreate")
    form.wait_for(state="visible")
    form.locator("#UsuarioUserTypeId").select_option("3")
    form.locator("input[type='text']").fill(username)
    form.locator("input[type='password']").fill(password)
    form.locator("input[type='submit']").click()

    page.wait_for_url(f"{BASE_URL}/authorizations", timeout=20_000)
    print("Sesión de Profesor iniciada correctamente.", flush=True)


def choose_numbered_option(
    options: list[tuple[str, str]],
    title: str,
    prompt: str,
) -> tuple[str, str]:
    print(f"\n=== {title} ===")
    for index, (_, label) in enumerate(options, start=1):
        print(f"{index}. {label}")

    while True:
        selection = input(f"{prompt} (1-{len(options)}): ").strip()
        try:
            selected_index = int(selection) - 1
            if 0 <= selected_index < len(options):
                return options[selected_index]
        except ValueError:
            pass

        print("Selección no válida. Ingrese uno de los números mostrados.")


def course_sort_key(course: tuple[str, str]) -> tuple[int, str]:
    label = normalize_label(course[1])
    grade_position = next(
        (position for grade, position in GRADE_ORDER.items() if grade in label),
        99,
    )
    return grade_position, label


def get_available_courses(page: Page) -> list[tuple[str, str]]:
    """Obtiene los paralelos disponibles sin depender de sus IDs internos."""
    page.goto(f"{BASE_URL}/qualifications", wait_until="domcontentloaded")
    course_select = page.locator("#CourseId")
    course_select.wait_for(state="visible")

    courses = []
    for option in course_select.locator("option").all():
        value = (option.get_attribute("value") or "").strip()
        if not value:
            continue

        label = re.sub(r"\s*-\s*$", "", option.inner_text().strip())
        courses.append((value, label))

    if not courses:
        raise RuntimeError("No se encontraron paralelos disponibles para este profesor.")

    return sorted(courses, key=course_sort_key)


def select_course(page: Page) -> tuple[str, str]:
    courses = get_available_courses(page)
    course_id, course_label = choose_numbered_option(
        courses,
        "SELECCIÓN DE PARALELO",
        "Elija un paralelo",
    )

    page.locator("#CourseId").select_option(course_id)
    page.locator("#SubjectId").wait_for(state="visible", timeout=10_000)
    print(f"Paralelo seleccionado: {course_label}", flush=True)
    return course_id, course_label


def canonical_subject_name(portal_label: str) -> str:
    """Relaciona el texto sin tildes del portal con la materia ya configurada."""
    subject_name = portal_label.split(":", maxsplit=1)[0].strip()
    normalized_name = normalize_label(subject_name)

    for canonical_name in CANONICAL_SUBJECTS:
        if normalize_label(canonical_name) == normalized_name:
            return canonical_name

    return subject_name


def get_available_subjects(page: Page) -> list[tuple[str, str]]:
    """Lee las asignaturas del paralelo y conserva el orden mostrado por el portal."""
    subject_select = page.locator("#SubjectId")
    subject_select.wait_for(state="visible")

    subjects = []
    for option in subject_select.locator("option").all():
        value = (option.get_attribute("value") or "").strip()
        if not value:
            continue
        subjects.append((value, canonical_subject_name(option.inner_text())))

    if not subjects:
        raise RuntimeError("No se encontraron asignaturas para el paralelo seleccionado.")

    return subjects


def choose_subjects(subjects: list[tuple[str, str]]) -> list[tuple[str, str]]:
    scope, _ = choose_numbered_option(
        [
            ("all", "Todas las asignaturas"),
            ("one", "Elegir una asignatura"),
        ],
        "ALCANCE DE LA CARGA",
        "¿Qué notas desea subir?",
    )
    if scope == "all":
        return subjects

    return [
        choose_numbered_option(
            subjects,
            "SELECCIÓN DE ASIGNATURA",
            "Elija una asignatura",
        )
    ]


def choose_trimester() -> tuple[str, str]:
    return choose_numbered_option(
        TRIMESTERS,
        "SELECCIÓN DE TRIMESTRE",
        "Elija el trimestre",
    )


def choose_execution_mode() -> bool:
    print("\n=== MODO DE EJECUCIÓN ===")
    print("La revisión recorre formularios y compara estudiantes, pero no modifica notas.")
    confirmation = input(
        "Escriba GUARDAR para llenar y guardar; cualquier otro texto revisa sin guardar: "
    ).strip()
    return confirmation == "GUARDAR"


def prepare_subject(page: Page, course_id: str, subject_id: str) -> None:
    """Carga nuevamente el paralelo y la asignatura para evitar estado AJAX obsoleto."""
    page.goto(f"{BASE_URL}/qualifications", wait_until="domcontentloaded")
    page.locator("#CourseId").select_option(course_id)
    page.locator("#SubjectId").wait_for(state="visible", timeout=10_000)

    with page.expect_response(
        lambda response: "/qualifications/curso_estudiantes/" in response.url,
        timeout=15_000,
    ):
        page.locator("#SubjectId").select_option(subject_id)


def open_aportes_form(
    page: Page,
    course_id: str,
    subject_id: str,
    trimester_label: str,
):
    """Abre por AJAX el trimestre y luego el formulario Aportes 70%."""
    prepare_subject(page, course_id, subject_id)

    with page.expect_response(
        lambda response: "/qualifications/notas_elegir/" in response.url,
        timeout=15_000,
    ):
        page.get_by_text(trimester_label, exact=True).click()
    page.locator("#divVerNotasMateria").wait_for(state="attached", timeout=15_000)

    with page.expect_response(
        lambda response: "/qualifications/notas_parcial_lista_estudiantes/" in response.url,
        timeout=15_000,
    ):
        page.get_by_text("Aportes 70%", exact=True).click()

    form = page.locator("#frmAddNotas1")
    form.wait_for(state="attached", timeout=15_000)
    return form


def process_subject(
    page: Page,
    grade_book: OrozcoGradeBook,
    course_id: str,
    subject: tuple[str, str],
    trimester: tuple[str, str],
    save_changes: bool,
) -> dict[str, int | bool]:
    subject_id, subject_name = subject
    trimester_id, trimester_label = trimester
    form = open_aportes_form(
        page,
        course_id,
        subject_id,
        trimester_label,
    )

    student_rows = []
    for row in form.locator("tr").all():
        fields = row.locator("input[type='text'][name^='data[Qualification]']")
        if fields.count() >= 4:
            student_rows.append((row, fields))

    matched_students = 0
    skipped_without_notes = 0
    changed_fields = 0
    unmatched_students = []

    for row_index, (row, fields) in enumerate(student_rows, start=1):
        cells = row.locator("td")
        portal_name = cells.first.inner_text().strip() if cells.count() else ""
        try:
            notes = grade_book.get_notes(portal_name, subject_name)
        except NameMatchError:
            unmatched_students.append(row_index)
            continue

        matched_students += 1
        if not any(note is not None for note in notes):
            skipped_without_notes += 1
            continue

        week_fields = []
        for week_number in range(1, 5):
            field = row.locator(
                "input[type='text']"
                f"[name*='[semana_{week_number}_{trimester_id}]']"
            )
            if field.count() != 1:
                raise RuntimeError(
                    f"La fila {row_index} de {subject_name} no tiene un único "
                    f"campo para la semana {week_number}."
                )
            week_fields.append(field.first)

        for note_index, note in enumerate(notes):
            if note is None:
                continue
            field = week_fields[note_index]
            current_value = (field.input_value() or "").strip()
            if current_value == note:
                continue
            changed_fields += 1
            if save_changes:
                field.fill(note)

    saved = False
    if unmatched_students:
        print(
            f"  - No se guardará {subject_name}: hay filas sin coincidencia "
            f"{unmatched_students}."
        )
    elif save_changes and changed_fields:
        with page.expect_response(
            lambda response: "/qualifications/grabar_notas_parcial/" in response.url,
            timeout=20_000,
        ) as response_info:
            form.locator("input[type='submit']").first.click()
        response = response_info.value
        if response.status >= 400:
            raise RuntimeError(
                f"El portal respondió {response.status} al guardar {subject_name}."
            )
        saved = True

    return {
        "portal_students": len(student_rows),
        "matched_students": matched_students,
        "skipped_without_notes": skipped_without_notes,
        "unmatched_students": len(unmatched_students),
        "changed_fields": changed_fields,
        "saved": saved,
    }


def process_subjects(
    page: Page,
    grade_book: OrozcoGradeBook,
    course_id: str,
    subjects: list[tuple[str, str]],
    trimester: tuple[str, str],
    save_changes: bool,
) -> None:
    mode_label = "GUARDAR" if save_changes else "REVISAR"
    print(f"\nIniciando modo {mode_label} para {trimester[1]}...")

    for index, subject in enumerate(subjects, start=1):
        print(f"\n[{index}/{len(subjects)}] {subject[1]}")
        result = process_subject(
            page,
            grade_book,
            course_id,
            subject,
            trimester,
            save_changes,
        )
        print(
            "  - "
            f"estudiantes={result['portal_students']}, "
            f"coincidencias={result['matched_students']}, "
            f"sin_notas={result['skipped_without_notes']}, "
            f"sin_coincidencia={result['unmatched_students']}, "
            f"campos_por_cambiar={result['changed_fields']}, "
            f"guardado={result['saved']}"
        )


def main() -> None:
    username, password = load_credentials(CREDENTIALS_FILE)
    grade_book = OrozcoGradeBook.load(BASE_GRADES_FILE, LANGUAGE_GRADES_FILE)
    print(
        f"Notas cargadas: {len(grade_book.base_records)} estudiantes base y "
        f"{len(grade_book.language_corrections)} correcciones de Lengua."
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--start-maximized"],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            login_as_teacher(page, username, password)
            course_id, _ = select_course(page)
            subjects = choose_subjects(get_available_subjects(page))
            trimester = choose_trimester()
            save_changes = choose_execution_mode()

            process_subjects(
                page,
                grade_book,
                course_id,
                subjects,
                trimester,
                save_changes,
            )
            print("\nProceso finalizado. Cierre el navegador para terminar.", flush=True)

            while not page.is_closed():
                page.wait_for_timeout(1_000)
        except (GradeFileError, NameMatchError, RuntimeError) as error:
            print(f"Error: {error}")
        except PlaywrightError as error:
            print(f"Error de navegador: {error}")
        finally:
            if browser.is_connected():
                browser.close()


if __name__ == "__main__":
    main()
