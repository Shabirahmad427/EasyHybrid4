"""GPU4PySCF must reject unsupported pDynamo systems before calculation."""
import os
from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a configured pDynamo3 checkout",
)


def _adapter_and_target(*, symmetry=None, restricted=False, multiplicity=1):
    pytest.importorskip("addOns.pySCF.QCModelPySCF")
    from addOns.pySCF.QCModelPySCF import QCModelPySCF

    model = QCModelPySCF.WithDefaults()
    model.useGPU = True
    # Energy() only needs a non-None PySCF sentinel before these guards.
    # CreateMole is replaced to prove no molecule/scientific work is started.
    model.pyscf = object()
    model.CreateMole = lambda *args: pytest.fail("scientific calculation started")
    target = SimpleNamespace(
        qcState=SimpleNamespace(atomicNumbers=[], qcAtoms=[]),
        atoms=[],
        symmetry=symmetry,
        symmetryParameters=None,
        electronicState=SimpleNamespace(
            isSpinRestricted=restricted,
            multiplicity=multiplicity,
        ),
        scratch=SimpleNamespace(doGradients=False),
    )
    return model, target


def test_gpu4pyscf_rejects_periodic_system_before_calculation():
    from pMolecule.QCModel import QCModelError

    model, target = _adapter_and_target(symmetry=object())
    with pytest.raises(QCModelError, match="molecular calculations only"):
        model.Energy(target)


def test_gpu4pyscf_rejects_restricted_open_shell_before_calculation():
    from pMolecule.QCModel import QCModelError

    model, target = _adapter_and_target(restricted=True, multiplicity=2)
    with pytest.raises(QCModelError, match="restricted open-shell"):
        model.Energy(target)
