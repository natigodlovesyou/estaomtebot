"""
Question loader for MegaMind Quiz Bot.
Handles loading, validating, and caching quiz questions.
"""

import json
import logging
import random
from pathlib import Path
from typing import Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)

BASE_PATH = Path(DATA_DIR)

QUESTION_CACHE: dict = {}


# ---------------------------------------------------
# Load Questions
# ---------------------------------------------------
def load_questions(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    unit: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Load questions based on grade, subject, and file name.

    Example path:
    data/grade9/maths/cell.json
    """

    if not grade or not subject or not unit:
        logger.warning("load_questions called with incomplete parameters")
        return []

    cache_key = f"{grade}:{subject}:{unit}"

    if cache_key in QUESTION_CACHE:
        questions = QUESTION_CACHE[cache_key]
    else:

        possible_names = [f"{unit}.json", f"{unit.title()}.json"]
        file_path = None
        for name in possible_names:
            candidate = BASE_PATH / f"grade{grade}" / subject / name
            if candidate.exists():
                file_path = candidate
                break
        if not file_path:
            logger.warning(f"Question file not found for grade{grade}/{subject}/unit{unit}.json")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error(f"Invalid question file format: {file_path}")
                return []

        except Exception:
            logger.exception(f"Failed to load questions from {file_path}")
            return []

        questions = validate_questions(data)

        if not questions:
            logger.warning(f"No valid questions in file: {file_path}")
            return []

        QUESTION_CACHE[cache_key] = questions

        logger.info(
            f"Loaded {len(questions)} questions for {grade}/{subject}/{unit}"
        )

    if limit is None:
        return questions

    return random.sample(questions, min(limit, len(questions)))


# ---------------------------------------------------
# Load All Questions
# ---------------------------------------------------
def load_all_questions():

    all_questions = []

    try:

        for grade_folder in BASE_PATH.glob("grade*"):

            if not grade_folder.is_dir():
                continue

            for subject_folder in grade_folder.iterdir():

                if not subject_folder.is_dir():
                    continue

                for file in subject_folder.glob("*.json"):

                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        if not isinstance(data, list):
                            logger.warning(f"Invalid question format in {file}")
                            continue

                        valid = validate_questions(data)
                        all_questions.extend(valid)

                    except Exception:
                        logger.exception(f"Failed reading question file {file}")

        random.shuffle(all_questions)

        logger.info(f"Loaded total questions: {len(all_questions)}")

        return all_questions

    except Exception:
        logger.exception("Error loading all questions")
        return []


# ---------------------------------------------------
# Validate Questions
# ---------------------------------------------------
def validate_questions(questions: list):

    valid = []

    for q in questions:

        try:
            if not isinstance(q, dict):
                logger.warning(f"Invalid question skipped: {q}")
                continue

            if "correct" not in q:
                if "correct_option" in q:
                    q["correct"] = q["correct_option"]
                elif "correct_option_id" in q:
                    q["correct"] = q["correct_option_id"]

            if "explanation" not in q and "description" in q:
                q["explanation"] = q["description"]

            if (
                "question" in q
                and "options" in q
                and "correct" in q
                and isinstance(q["options"], list)
                and len(q["options"]) >= 2
                and isinstance(q["correct"], int)
                and 0 <= q["correct"] < len(q["options"])
            ):
                valid.append(q)
            else:
                logger.warning(f"Invalid question skipped: {q}")

        except Exception:
            logger.exception("Error validating question")

    return valid