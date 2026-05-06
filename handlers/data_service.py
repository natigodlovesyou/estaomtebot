import json
from pathlib import Path
from urllib.parse import quote, unquote

from config import DATA_DIR


# ---------------------------------------------------
# BASE DATA PATH
# ---------------------------------------------------

BASE_PATH = Path(DATA_DIR)


# ---------------------------------------------------
# SUBJECT LABELS (FOR DISPLAY ONLY)
# ---------------------------------------------------

SUBJECT_LABELS = {
    "maths": "🔥 Math",
    "english": "📘 English",
    "physics": "⚛ Physics",
    "chemistry": "🧪 Chemistry",
    "biology": "🧬 Biology",
    "aptitude": "🧠 Aptitude",
}


# ---------------------------------------------------
# GET AVAILABLE GRADES (DYNAMIC FROM FOLDERS)
# ---------------------------------------------------

def get_available_grades():
    """
    Returns:
        [("9", "🎓 Grade 9"), ("10", "🎓 Grade 10")]
    """

    grades = []

    for folder in BASE_PATH.glob("grade*"):
        if folder.is_dir():
            grade_id = folder.name.replace("grade", "")
            grades.append((grade_id, f"🎓 Grade {grade_id}"))

    return sorted(grades, key=lambda x: int(x[0]))


# ---------------------------------------------------
# FILE KEY / LABEL HELPERS
# ---------------------------------------------------

def _encode_file_key(stem: str) -> str:
    return quote(stem, safe="")


def _decode_file_key(key: str) -> str:
    return unquote(key)


def format_file_label(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


# ---------------------------------------------------
# GET SUBJECT LABEL
# ---------------------------------------------------

def get_subject_label(subject: str) -> str:
    return SUBJECT_LABELS.get(subject, subject.title())


# ---------------------------------------------------
# GET GRADE LABEL
# ---------------------------------------------------

def get_grade_label(grade: str) -> str:
    return f"🎓 Grade {grade}"


# ---------------------------------------------------
# GET AVAILABLE SUBJECTS (FROM FOLDERS)
# ---------------------------------------------------

def get_available_subjects(grade: str):
    """
    Reads:
    data/grade9/*
    """

    path = BASE_PATH / f"grade{grade}"

    if not path.exists():
        return []

    subjects = []

    for folder in path.iterdir():
        if folder.is_dir():
            subjects.append(folder.name)

    return subjects


# ---------------------------------------------------
# GET UNITS (FROM JSON FILES)
# ---------------------------------------------------

def get_units(grade: str, subject: str):
    """
    Reads:
    data/grade9/<subject>/*.json

    Returns a list of available file names encoded for callback data.
    """

    path = BASE_PATH / f"grade{grade}" / subject

    if not path.exists():
        return []

    units = []

    for file in path.glob("*.json"):
        stem = file.stem
        key = _encode_file_key(stem)
        label = format_file_label(stem)
        units.append((key, f"📖 {label}"))

    return sorted(units, key=lambda x: x[1])


# ---------------------------------------------------
# LOAD QUESTIONS FROM UNIT FILE
# ---------------------------------------------------

def load_unit_questions(grade: str, subject: str, unit: str, limit=None):
    """
    Returns list of questions from JSON file
    """

    file_path = BASE_PATH / f"grade{grade}" / subject / f"{unit}.json"

    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        if not isinstance(questions, list):
            return []

        return questions[:limit]

    except Exception:
        return []


# ---------------------------------------------------
# VALIDATE QUESTION FORMAT
# ---------------------------------------------------

def validate_questions(questions):
    """
    Ensures safe structure:
    question, options, correct, explanation
    """

    valid = []

    for q in questions:
        if (
            isinstance(q, dict)
            and "question" in q
            and "options" in q
            and "correct" in q
            and "explanation" in q
            and len(q["options"]) >= 2
        ):
            valid.append(q)

    return valid