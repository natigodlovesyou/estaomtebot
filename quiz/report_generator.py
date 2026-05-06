from quiz.learning_tracker import get_user_insights
def format_list(items):
    if not items:
        return "• None"
    return "\n".join([f"• {item}" for item in items])
def _get_session_value(session, key, default=None):
    if isinstance(session, dict):
        return session.get(key, default)
    return getattr(session, key, default)


def build_study_report_message(user_id: int, session, insights: dict) -> str:
    """
    Builds a formatted Telegram report card message (no PDF).
    """

    # ---------------------------------------------------
    # SESSION DATA
    # ---------------------------------------------------
    score = _get_session_value(session, "score", 0)
    questions = _get_session_value(session, "questions", []) or []
    total = len(questions)
    accuracy = round((score / total) * 100) if total else 0

    # ---------------------------------------------------
    # PERFORMANCE STATUS
    # ---------------------------------------------------
    if accuracy >= 80:
        status = "🔥 Excellent"
    elif accuracy >= 50:
        status = "👍 Good"
    else:
        status = "⚠️ Needs Improvement"

    # ---------------------------------------------------
    # INSIGHTS
    # ---------------------------------------------------
    weak = insights.get("weak_topics", [])
    strong = insights.get("strong_topics", [])
    neutral = insights.get("neutral_topics", [])

    # ---------------------------------------------------
    # MESSAGE BUILD
    # ---------------------------------------------------
    message = f"""
📊 *Your Study Report Card*

🎯 *Performance*
• Score: {score}/{total}
• Accuracy: {accuracy}%
• Status: {status}

⚠️ *Weak Topics*
{format_list(weak)}

📘 *Needs Practice*
{format_list(neutral)}

✅ *Strong Topics*
{format_list(strong)}

💡 *AI Tip*
Focus on weak topics daily for faster improvement 🚀
"""

    return message