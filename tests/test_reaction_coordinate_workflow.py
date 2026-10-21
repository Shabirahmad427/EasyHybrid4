"""Regression for supported reaction-coordinate distance definitions."""
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires the pDynamo3 runtime used by reaction-coordinate workflows",
)
def test_reaction_coordinate_distance_variants():
    pytest.importorskip("pBabel")
    from pdynamo.p_methods.energy import compute_reaction_coordinate

    class Coordinates:
        def Distance(self, first, second):
            return abs(first - second) * 1.25

    xyz = Coordinates()
    assert compute_reaction_coordinate(
        xyz, {"rc_type": "simple_distance", "ATOMS": [1, 4]}
    ) == (3.75, None)
    assert compute_reaction_coordinate(
        xyz, {"rc_type": "multiple_distance", "ATOMS": [1, 4, 10]}
    ) == (3.75, 7.5)
    assert compute_reaction_coordinate(
        xyz, {"rc_type": "multiple_distance*4atoms", "ATOMS": [1, 4, 10, 2]}
    ) == (3.75, 10.0)
