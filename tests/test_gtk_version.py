"""Regression tests for the installer's GTK runtime minimum."""

from install import GTK4_MIN_VERSION, is_supported_gtk4_version


def test_gtk_46_is_below_the_supported_minimum():
    assert GTK4_MIN_VERSION == (4, 8)
    assert not is_supported_gtk4_version((4, 6))


def test_gtk_48_is_the_supported_minimum():
    assert is_supported_gtk4_version((4, 8))


def test_newer_gtk4_minors_are_supported():
    assert is_supported_gtk4_version((4, 14))
    assert is_supported_gtk4_version((4, 22))


def test_missing_gtk_runtime_is_not_supported():
    assert not is_supported_gtk4_version(None)
