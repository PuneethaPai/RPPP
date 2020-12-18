import pytest
from src.reddit_utils import calculate_metrics


def test_calculate_metrics():
    expected = set(
        ["roc_auc", "average_precision", "accuracy", "precision", "recall", "f1"]
    )
    actual = calculate_metrics([1, 0], [0.5, 0.5], [0, 1]).keys()
    assert expected == actual
