from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ---------------------------------------------------
# SUBJECT CONFIG (GAMIFIED SYSTEM)
# ---------------------------------------------------

SUBJECTS = {
    "maths": "🔥 Math",
    "english": "📘 English",
    "physics": "⚛ Physics",
    "chemistry": "🧪 Chemistry",
    "biology": "🧬 Biology",
    "aptitude": "🧠 Aptitude",
}


# ---------------------------------------------------
# CORE HELPER
# ---------------------------------------------------

def row(*buttons):
    return list(buttons)


def button(text, callback):
    return InlineKeyboardButton(text, callback_data=callback)


# ---------------------------------------------------
# SUBJECT MENU
# ---------------------------------------------------

def subject_menu():
    buttons = []

    for key, label in SUBJECTS.items():
        buttons.append(row(
            button(label, f"subject_{key}")
        ))

    # ---------------------------------------------------
    # 🔥 NEW: REPORT CARD ACCESS
    # ---------------------------------------------------
    buttons.append(row(
        button("📊 Report Card", "main_report")
    ))

    buttons.append(row(
        button("🏠 Menu", "back_menu")
    ))

    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------
# GRADE MENU
# ---------------------------------------------------

def grade_menu():
    grades = ["9", "10", "11", "12"]

    buttons = [
        row(button(f"🎓 Grade {g}", f"grade_{g}")) for g in grades
    ]

    buttons.append(row(
        button("⬅ Back", "back_subject"),
        button("🏠 Menu", "back_menu")
    ))

    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------
# UNIT MENU
# ---------------------------------------------------

def unit_menu(units):
    buttons = []

    for unit_id, label in units:
        buttons.append(row(
            button(label, f"unit_{unit_id}")
        ))

    buttons.append(row(
        button("⬅ Back", "back_grade"),
        button("🏠 Menu", "back_menu")
    ))

    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------
# CONFIRM MENU
# ---------------------------------------------------

def confirm_menu():
    buttons = [
        row(button("🚀 Start Quiz", "quiz_start")),

        # ---------------------------------------------------
        # 🔥 NEW: QUICK ACCESS REPORT (optional but powerful UX)
        # ---------------------------------------------------
        row(button("📊 Report Card", "main_report")),

        row(
            button("⬅ Back", "back_options"),
            button("🏠 Menu", "back_menu")
        )
    ]

    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------
# QUIZ OPTIONS MENU
# ---------------------------------------------------

def quiz_options_menu():
    buttons = [
        row(button("⏱ Timed Mode", "mode_timed"), button("📚 Practice Mode", "mode_practice")),
        row(button("⬅ Back", "back_unit"), button("🏠 Menu", "back_menu"))
    ]

    return InlineKeyboardMarkup(buttons)