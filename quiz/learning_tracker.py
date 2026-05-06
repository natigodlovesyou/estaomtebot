import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# UPDATE LEARNING PROFILE
# ---------------------------------------------------

async def update_learning(user_id: int, topic: str, is_correct: bool):
    """
    Update stats after each answer.
    """

    from state.storage import get_user_state, update_user_state

    user_state = get_user_state(user_id)
    player = user_state.players.get(user_id)

    if not player:
        return

    if topic not in player.learning_topics:
        player.learning_topics[topic] = {"correct": 0, "wrong": 0}

    stats = player.learning_topics[topic]

    if is_correct:
        stats["correct"] += 1
    else:
        stats["wrong"] += 1

    _recalculate_strength(player, topic)

    # Persist
    await update_user_state(user_id, user_state)


# ---------------------------------------------------
# STRENGTH ENGINE (IMPROVED)
# ---------------------------------------------------

def _recalculate_strength(data, topic: str):
    """
    Classifies topic based on performance.
    """

    stats = data.learning_topics[topic]

    correct = stats["correct"]
    wrong = stats["wrong"]
    total = correct + wrong

    if total < 3:
        # not enough data → neutral zone
        data.neutral_topics.add(topic)
        data.weak_topics.discard(topic)
        data.strong_topics.discard(topic)
        return

    accuracy = correct / total

    # ---------------------------------------------------
    # STRONG
    # ---------------------------------------------------
    if accuracy >= 0.75:
        data.strong_topics.add(topic)
        data.weak_topics.discard(topic)
        data.neutral_topics.discard(topic)

    # ---------------------------------------------------
    # WEAK
    # ---------------------------------------------------
    elif accuracy < 0.5:
        data.weak_topics.add(topic)
        data.strong_topics.discard(topic)
        data.neutral_topics.discard(topic)

    # ---------------------------------------------------
    # NEUTRAL
    # ---------------------------------------------------
    else:
        data.neutral_topics.add(topic)
        data.weak_topics.discard(topic)
        data.strong_topics.discard(topic)


# ---------------------------------------------------
# GET USER INSIGHTS (REPORT READY)
# ---------------------------------------------------

def get_user_insights(user_id: int):
    """
    Returns structured learning summary for reports/AI.
    """

    from state.storage import get_user_state

    user_state = get_user_state(user_id)
    player = user_state.players.get(user_id)

    if not player:
        return {
            "weak_topics": [],
            "strong_topics": [],
            "neutral_topics": [],
            "topics": {}
        }

    return {
        "weak_topics": list(player.weak_topics),
        "strong_topics": list(player.strong_topics),
        "neutral_topics": list(player.neutral_topics),
        "topics": player.learning_topics
    }


# ---------------------------------------------------
# RESET USER
# ---------------------------------------------------

async def reset_learning(user_id: int):
    """Clear learning data for user."""

    from state.storage import get_user_state, update_user_state

    user_state = get_user_state(user_id)
    player = user_state.players.get(user_id)

    if player:
        player.learning_topics = {}
        player.weak_topics = set()
        player.strong_topics = set()
        player.neutral_topics = set()

    await update_user_state(user_id, user_state)