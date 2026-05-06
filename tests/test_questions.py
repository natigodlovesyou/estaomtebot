from quiz.questions import load_questions


def test_load_questions_returns_all_questions():
    questions = load_questions("9", "biology", "unit1")
    assert isinstance(questions, list)
    assert len(questions) > 0
    assert all(isinstance(q, dict) for q in questions)
    assert all("question" in q and "options" in q and "correct" in q for q in questions)
