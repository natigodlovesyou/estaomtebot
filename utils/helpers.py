import random


# ---------------------------------------------------
# Calculate Percentage
# ---------------------------------------------------

def calculate_percentage(score, total):

    if total <= 0:
        return 0

    return round((score / total) * 100, 1)


# ---------------------------------------------------
# Shuffle Questions (without mutating original)
# ---------------------------------------------------

def shuffle_questions(questions):

    shuffled = questions.copy()

    random.shuffle(shuffled)

    return shuffled


# ---------------------------------------------------
# Format Score
# ---------------------------------------------------

def format_score(score, total):

    percent = calculate_percentage(score, total)

    return (
        f"📊 Score: {score}/{total}\n"
        f"🎯 Accuracy: {percent}%"
    )