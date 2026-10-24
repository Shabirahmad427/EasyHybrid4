"""Opt-in numerical smoke for the pDynamo MM energy/minimization path.

Set PDYNAMO3_HOME and PDYNAMO3_PARAMETERS to a compiled pDynamo3 checkout.
This deliberately uses pDynamo's bundled water parameter fixture rather than
shipping scientific input data with the EasyHybrid test suite.
"""
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a compiled pDynamo3 checkout",
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
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a compiled pDynamo3 checkout",
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
    np.testing.assert_allclose(
        loaded_coordinates, original_coordinates, rtol=0.0, atol=1.0e-12
    )


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a compiled pDynamo3 checkout",
)
def test_easyhybrid_am1_qmmm_setup_matches_pdynamo_reference(tmp_path, monkeypatch):
    """Exercise EasyHybrid's QC selection/model setup against pDynamo's API."""
    monkeypatch.setenv("PDYNAMO3_SCRATCH", str(tmp_path))
    pytest.importorskip("pBabel")

    from pBabel import ImportSystem
    from pCore import Selection, logFile
    from pMolecule.MMModel import MMModelOPLS
    from pMolecule.NBModel import NBModelCutOff
    from pMolecule.QCModel import ElectronicState, QCModelMNDO
    from pMolecule import SystemGeometryObjectiveFunction

    from pdynamo.pDynamo2EasyHybrid.session import pDynamoSession

    pdynamo_home = Path(os.environ["PDYNAMO3_HOME"])
    fixture = pdynamo_home / "examples/pMolecule/data/mol/waterDimer_cs.mol"
    assert fixture.is_file(), f"pDynamo QC/MM fixture not found: {fixture}"
    qc_atoms = [0, 1, 2]

    def make_reference_system():
        system = ImportSystem(str(fixture))
        system.DefineMMModel(MMModelOPLS.WithParameterSet("protein"))
        system.electronicState = ElectronicState.WithOptions(
            charge=0, multiplicity=1, isSpinRestricted=True
        )
        system.DefineQCModel(
            QCModelMNDO.WithOptions(hamiltonian="am1"),
            qcSelection=Selection.FromIterable(qc_atoms),
        )
        system.DefineNBModel(NBModelCutOff.WithDefaults())
        return system

    reference = make_reference_system()
    reference_energy = reference.Energy(log=None)
    reference_objective = SystemGeometryObjectiveFunction.FromSystem(reference)
    reference_gradient_deviation = reference_objective.TestGradients(
        delta=1.0e-4, log=logFile, tolerance=1.0e-3
    )

    easyhybrid_system = ImportSystem(str(fixture))
    easyhybrid_system.DefineMMModel(MMModelOPLS.WithParameterSet("protein"))
    easyhybrid_system.e_qc_table = list(qc_atoms)

    session = object.__new__(pDynamoSession)
    session.clean_QC_representation_to_vobject = lambda: None
    session.check_charge_fragmentation = lambda **_kwargs: None
    session.main = SimpleNamespace(
        refresh_widgets=lambda: None,
        selection_list_window=SimpleNamespace(visible=False),
    )
    session.vm_session = SimpleNamespace(vm_objects_dic={})

    parameters = {
        "charge": 0,
        "multiplicity": 1,
        "isSpinRestricted": True,
        "qcengine": "MNDO",
        "method": "am1",
        "energyTolerance": 1.0e-8,
        "densityTolerance": 1.0e-8,
        "maximumIterations": 100,
    }
    assert session._define_a_new_QCModel_impl(
        system=easyhybrid_system,
        parameters=parameters,
        vismol_object=object(),
    )

    original_coordinates = np.asarray(
        [
            list(easyhybrid_system.coordinates3[i])
            for i in range(len(easyhybrid_system.atoms))
        ],
        dtype=np.float64,
    )
    easyhybrid_energy = easyhybrid_system.Energy(log=None)
    calculated_coordinates = np.asarray(
        [
            list(easyhybrid_system.coordinates3[i])
            for i in range(len(easyhybrid_system.atoms))
        ],
        dtype=np.float64,
    )

    assert len(easyhybrid_system.atoms) == len(reference.atoms) == 6
    assert easyhybrid_system.qcModel.hamiltonian == "am1"
    assert list(easyhybrid_system.e_qc_table) == qc_atoms
    assert list(easyhybrid_system.qcState.qcAtoms) == qc_atoms
    assert easyhybrid_system.electronicState.charge == 0
    assert easyhybrid_system.electronicState.multiplicity == 1
    assert isinstance(easyhybrid_system.nbModel, NBModelCutOff)
    np.testing.assert_allclose(
        calculated_coordinates, original_coordinates, rtol=0.0, atol=1.0e-12
    )
    assert reference_energy == pytest.approx(-258.5075262422, abs=1.0e-6)
    assert reference_gradient_deviation <= 1.0e-3
    assert easyhybrid_energy == pytest.approx(reference_energy, abs=1.0e-8)
