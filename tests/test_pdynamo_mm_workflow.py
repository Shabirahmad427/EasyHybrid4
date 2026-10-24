"""Opt-in numerical smoke for the pDynamo MM energy/minimization path.

Set PDYNAMO3_HOME and PDYNAMO3_PARAMETERS to a compiled pDynamo3 checkout.
This deliberately uses pDynamo's bundled water parameter fixture rather than
shipping scientific input data with the EasyHybrid test suite.
"""
import os
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME") or not os.environ.get("PDYNAMO3_PARAMETERS"),
    reason="requires a compiled pDynamo3 checkout and parameter directory",
)
def test_dyff_energy_and_minimization_preserve_water_system():
    pytest.importorskip("pBabel")
    from pBabel import ImportSystem
    from pMolecule.MMModel import MMModelDYFF
    from pMolecule.NBModel import NBModelCutOff
    from pSimulation import ConjugateGradientMinimize_SystemGeometry

    parameters = Path(os.environ["PDYNAMO3_PARAMETERS"])
    fixture = parameters / "solventsAndCounterIons/solvents/mol/water.mol"
    assert fixture.is_file(), f"pDynamo water fixture not found: {fixture}"

    system = ImportSystem(str(fixture))
    atom_count = len(system.atoms)
    system.DefineMMModel(MMModelDYFF.WithParameterSet("dyff-1.0"), log=None)
    system.DefineNBModel(NBModelCutOff.WithDefaults())

    initial_energy = system.Energy(log=None)
    ConjugateGradientMinimize_SystemGeometry(
        system, log=None, maximumIterations=20
    )
    minimized_energy = system.Energy(log=None)

    assert len(system.atoms) == atom_count == 3
    assert initial_energy == pytest.approx(5.1044257614, abs=1.0e-8)
    assert minimized_energy == pytest.approx(0.0010421254, abs=1.0e-7)
    assert minimized_energy < initial_energy


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME") or not os.environ.get("PDYNAMO3_PARAMETERS"),
    reason="requires a compiled pDynamo3 checkout and parameter directory",
)
def test_am1_single_point_preserves_water_geometry():
    pytest.importorskip("pBabel")
    from pBabel import ImportSystem
    from pMolecule.QCModel import ElectronicState, QCModelMNDO

    parameters = Path(os.environ["PDYNAMO3_PARAMETERS"])
    fixture = parameters / "solventsAndCounterIons/solvents/mol/water.mol"
    assert fixture.is_file(), f"pDynamo water fixture not found: {fixture}"

    system = ImportSystem(str(fixture))
    original_coordinates = np.asarray(
        [list(system.coordinates3[i]) for i in range(len(system.atoms))],
        dtype=np.float64,
    )
    system.DefineQCModel(QCModelMNDO.WithOptions(hamiltonian="am1"))
    system.electronicState = ElectronicState.WithOptions(charge=0, multiplicity=1)

    energy = system.Energy(log=None)
    loaded_coordinates = np.asarray(
        [list(system.coordinates3[i]) for i in range(len(system.atoms))],
        dtype=np.float64,
    )

    assert len(system.atoms) == 3
    assert energy == pytest.approx(-247.6560770502, abs=1.0e-8)
    np.testing.assert_allclose(loaded_coordinates, original_coordinates, rtol=0.0, atol=1.0e-12)
