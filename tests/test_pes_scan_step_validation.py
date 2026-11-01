"""Regression coverage for missing relaxed-scan step counts."""

from gui.windows.simulation.PES_scan_window import PotentialEnergyScanWindow


def test_scan_requires_positive_step_count_for_each_active_coordinate():
    base = {"RC1": {"nsteps": 10}, "RC2": None}
    assert PotentialEnergyScanWindow._has_valid_step_counts(base)
    assert not PotentialEnergyScanWindow._has_valid_step_counts(
        {"RC1": {"nsteps": None}, "RC2": None}
    )
    assert not PotentialEnergyScanWindow._has_valid_step_counts(
        {"RC1": {"nsteps": 0}, "RC2": None}
    )
    assert not PotentialEnergyScanWindow._has_valid_step_counts(
        {"RC1": {"nsteps": 10}, "RC2": {"nsteps": None}}
    )
