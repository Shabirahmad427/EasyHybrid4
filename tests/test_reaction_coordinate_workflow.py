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


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires the compiled pDynamo3 geometry runtime",
)
def test_reaction_coordinate_uses_real_pdynamo_coordinates():
    from pScientific.Geometry3 import Coordinates3
    from pdynamo.p_methods.energy import compute_reaction_coordinate

    xyz = Coordinates3.WithExtent(4)
    for index, point in enumerate(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0), (4.0, 2.0, 0.0))
    ):
        for axis, value in enumerate(point):
            xyz[index, axis] = value

    assert compute_reaction_coordinate(
        xyz, {"rc_type": "simple_distance", "ATOMS": [0, 1]}
    ) == pytest.approx((1.0, None))
    assert compute_reaction_coordinate(
        xyz, {"rc_type": "multiple_distance", "ATOMS": [0, 1, 2]}
    ) == pytest.approx((1.0, 2.0))
    assert compute_reaction_coordinate(
        xyz, {"rc_type": "multiple_distance*4atoms", "ATOMS": [0, 1, 2, 3]}
    ) == pytest.approx((1.0, 3.0))


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires the pDynamo3 runtime imported by the export dialog",
)
def test_simulation_export_script_covers_supported_simulation_types(tmp_path):
    pytest.importorskip("pBabel")
    from gui.windows.setup.windows_and_dialogs.dialogs.export_dialogs import (
        build_simulation_script,
    )

    expected = {
        "Relaxed_Surface_Scan": "RelaxedSurfaceScan",
        "Advanced_Relaxed_Surface_Scan": "AdvancedRelaxedSurfaceScan",
        "Umbrella_Sampling": "UmbrellaSampling",
        "Nudged_Elastic_Band": "ChainOfStatesOptimizePath",
    }
    for simulation_type, class_name in expected.items():
        parameters = {
            "simulation_type": simulation_type,
            "folder": str(tmp_path),
            "RC1": {"rc_type": "simple_distance", "ATOMS": [0, 1]},
        }
        if simulation_type == "Nudged_Elastic_Band":
            parameters.update(
                reac_coordinates="reactant.pkl", prod_coordinates="product.pkl"
            )
        script = build_simulation_script(parameters, str(tmp_path / "system.pkl"), "/app/src")
        compile(script, "exported_{}.py".format(simulation_type), "exec")
        assert "pMethods.{}()".format(class_name) in script
        assert "simObj.run(parameters)" in script
        assert "parameters['system'] = system" in script
        if simulation_type == "Nudged_Elastic_Band":
            assert "Unpickle(parameters['reac_coordinates'])" in script
            assert "Unpickle(parameters['prod_coordinates'])" in script


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires the pDynamo3 runtime imported by the export dialog",
)
def test_simulation_export_rejects_unknown_type():
    pytest.importorskip("pBabel")
    from gui.windows.setup.windows_and_dialogs.dialogs.export_dialogs import (
        build_simulation_script,
    )

    with pytest.raises(ValueError, match="Unsupported simulation type"):
        build_simulation_script({"simulation_type": "unknown"}, "system.pkl", "src")
