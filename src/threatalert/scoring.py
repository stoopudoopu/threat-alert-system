from threatalert.models import Score


def average_score(scores: list[Score]) -> float:
    if not scores:
        raise ValueError("Cannot average an empty list of scores")
    return sum(score.score for score in scores) / len(scores)
