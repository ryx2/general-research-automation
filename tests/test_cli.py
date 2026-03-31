"""Tests for CLI utility functions."""

from gra.cli import _parse_duration


def test_parse_seconds():
    assert _parse_duration("300s") == 300
    assert _parse_duration("60s") == 60


def test_parse_minutes():
    assert _parse_duration("5m") == 300
    assert _parse_duration("1.5m") == 90


def test_parse_hours():
    assert _parse_duration("2h") == 7200
    assert _parse_duration("0.5h") == 1800


def test_parse_bare_number():
    assert _parse_duration("120") == 120


def test_parse_strips_whitespace():
    assert _parse_duration("  5m  ") == 300
