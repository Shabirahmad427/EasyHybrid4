"""Regression coverage for missing relaxed-scan step counts."""

from gui.scan_validation import has_positive_step_counts


def test_scan_requires_positive_step_count_for_each_active_coordinate():
    assert has_positive_step_counts(10)
    assert has_positive_step_counts("10", "2")
    assert not has_positive_step_counts(None)
    assert not has_positive_step_counts(0)
    assert not has_positive_step_counts(" ")
    assert not has_positive_step_counts(10, None)
