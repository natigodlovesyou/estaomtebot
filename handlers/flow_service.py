# ---------------------------------------------------
# FLOW STATE MANAGER (CORE LOGIC LAYER)
# ---------------------------------------------------


# ---------------------------------------------------
# SETTERS
# ---------------------------------------------------

def set_subject(context, subject: str):
    context.user_data["subject"] = subject


def set_grade(context, grade: str):
    context.user_data["grade"] = grade


def set_unit(context, unit: str):
    context.user_data["unit"] = unit


def set_mode(context, mode: str):
    context.user_data["mode"] = mode


# ---------------------------------------------------
# GET FLOW STATE
# ---------------------------------------------------

def get_flow_state(context):
    return {
        "subject": context.user_data.get("subject"),
        "grade": context.user_data.get("grade"),
        "unit": context.user_data.get("unit"),
        "mode": context.user_data.get("mode", "timed"),
    }


# ---------------------------------------------------
# RESET FUNCTIONS
# ---------------------------------------------------

def reset_all(context):
    context.user_data.pop("subject", None)
    context.user_data.pop("grade", None)
    context.user_data.pop("unit", None)
    context.user_data.pop("mode", None)


def reset_subject(context):
    context.user_data.pop("subject", None)
    context.user_data.pop("grade", None)
    context.user_data.pop("unit", None)
    context.user_data.pop("mode", None)


def reset_grade(context):
    context.user_data.pop("grade", None)
    context.user_data.pop("unit", None)
    context.user_data.pop("mode", None)


def reset_unit(context):
    context.user_data.pop("unit", None)
    context.user_data.pop("mode", None)


def reset_options(context):
    context.user_data.pop("mode", None)


# ---------------------------------------------------
# VALIDATION HELPERS
# ---------------------------------------------------

def has_subject(context) -> bool:
    return context.user_data.get("subject") is not None


def has_grade(context) -> bool:
    return context.user_data.get("grade") is not None


def has_unit(context) -> bool:
    return context.user_data.get("unit") is not None


# ---------------------------------------------------
# FLOW READINESS CHECK
# ---------------------------------------------------

def is_ready_to_start(context) -> bool:
    return (
        has_subject(context)
        and has_grade(context)
        and has_unit(context)
    )