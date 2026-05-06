from handlers.data_service import get_available_grades, get_units, format_file_label, _decode_file_key


def test_get_available_grades():
    grades = get_available_grades()
    assert grades == [
        ("9", "🎓 Grade 9"),
        ("10", "🎓 Grade 10"),
        ("11", "🎓 Grade 11"),
        ("12", "🎓 Grade 12"),
    ]


def test_get_units_returns_dynamic_file_names():
    units = get_units("9", "biology")
    assert len(units) >= 1
    assert any(_decode_file_key(key).startswith("unit") for key, _ in units)


def test_format_file_label():
    assert format_file_label("cell") == "Cell"
    assert format_file_label("human_biology") == "Human Biology"
    assert format_file_label("solving-equation") == "Solving Equation"
