import time


# ---------------------------------------------------
# CORE ANSWER EVALUATION ENGINE
# ---------------------------------------------------

def evaluate_answer(session, question: dict, selected: int, time_taken: float):
    """
    Pure evaluation engine.
    DOES NOT mutate session.
    Returns structured result only.
    """

    time_limit = session.time_limit

    is_timeout = time_taken > time_limit
    is_correct = selected == question["correct"]
    topic = question.get("topic", "general")

    # ---------------------------------------------------
    # BASE RESULT STRUCTURE
    # ---------------------------------------------------

    result = {
        "is_correct": False,
        "is_timeout": False,
        "score_change": 0,
        "streak_change": 0,
        "topic": topic,
        "selected": selected,
        "correct_index": question["correct"]
    }

    # ---------------------------------------------------
    # ⏱ TIMEOUT CASE
    # ---------------------------------------------------

    if is_timeout:
        return {
            **result,
            "is_timeout": True,
            "feedback": "⏱ Time's up! Answer counted as wrong.",
            "score_change": 0,
            "streak_change": 0  # No streak penalty for timeout
        }

    # ---------------------------------------------------
    # ✅ CORRECT CASE
    # ---------------------------------------------------

    if is_correct:
        return {
            **result,
            "is_correct": True,
            "score_change": 1,
            "streak_change": 1,
            "feedback": f"✅ Correct! 🔥"
        }

    # ---------------------------------------------------
    # ❌ WRONG CASE
    # ---------------------------------------------------

    return {
        **result,
        "feedback": "❌ Wrong answer."
    }