import pytest

from threatalert.alerting import should_alert
from threatalert.models import Score
from threatalert.scoring import average_score


def make_scores(*values):
    return [Score(reasoning="test", score=value) for value in values]


def test_average_of_three_scores():
    assert average_score(make_scores(10, 9, 8)) == 9


def test_average_of_empty_list_raises_error():
    with pytest.raises(ValueError):
        average_score([])


def test_alert_above_threshold():
    assert should_alert(7.1, 7.0) is True


def test_no_alert_below_threshold():
    assert should_alert(6.9, 7.0) is False


def test_no_alert_exactly_at_threshold():
    assert should_alert(7.0, 7.0) is False
