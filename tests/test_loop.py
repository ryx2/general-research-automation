"""Tests for loop utilities."""

from gra.loop import is_improvement


def test_minimize_lower_is_better():
    assert is_improvement(0.3, 0.5, "minimize") is True
    assert is_improvement(0.5, 0.3, "minimize") is False
    assert is_improvement(0.3, 0.3, "minimize") is False


def test_maximize_higher_is_better():
    assert is_improvement(0.8, 0.5, "maximize") is True
    assert is_improvement(0.5, 0.8, "maximize") is False
    assert is_improvement(0.5, 0.5, "maximize") is False
