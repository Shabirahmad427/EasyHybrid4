"""EH4-403: run an exported simulation script as a real pDynamo3 calculation.

The export tests check script text; this runs the exported script in a fresh
process, as a user would, on pDynamo3's water-dimer example with OPLS
parameters shipped by pDynamo3 (no EasyHybrid-made parameters).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

pytestmark = pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a compiled pDynamo3 checkout",
)

# waterDimer_cs.mol: O3 accepts the H2 hydrogen bond (1.762 Å as shipped).
ACCEPTOR, DONOR_H = 3, 2


def _water_dimer_pickle(tmp_path):
    pytest.importorskip("pBabel")
    from pBabel import ImportSystem
    from pCore import Pickle
    from pMolecule.MMModel import MMModelOPLS
    from pMolecule.NBModel import NBModelCutOff

    source = Path(os.environ["PDYNAMO3_HOME"], "examples/pMolecule/data/mol/waterDimer_cs.mol")
    system = ImportSystem(str(source))
    system.DefineMMModel(MMModelOPLS.WithParameterSet("protein"))
    system.DefineNBModel(NBModelCutOff.WithDefaults())
    path = tmp_path / "water_dimer.pkl"
    Pickle(str(path), system)
    return path


def test_exported_relaxed_surface_scan_runs_and_follows_its_restraint(tmp_path):
    from gui.windows.setup.windows_and_dialogs.dialogs.export_dialogs import (
        build_simulation_script,
    )

    system_pickle = _water_dimer_pickle(tmp_path)
    targets = (1.80, 1.90, 2.00)
    parameters = {
        "simulation_type": "Relaxed_Surface_Scan",
        "folder": str(tmp_path),
        "traj_folder_name": "hbond_scan",
        "RC1": {
            "rc_type": "simple_distance",
            "ATOMS": [ACCEPTOR, DONOR_H],
            "ATOM_NAMES": ["O", "H"],
            "nsteps": len(targets),
            "dminimum": targets[0],
            "dincre": targets[1] - targets[0],
            "force_constant": 4000.0,
        },
        "rc_type_1": "simple_distance",
        "RC2": None,
        "_is_ts_centered": False,
        "maximumIterations": 500,
        "rmsGradientTolerance": 0.01,
        "logFrequency": 1000,
    }
    script = tmp_path / "exported_scan.py"
    script.write_text(
        build_simulation_script(parameters, str(system_pickle), str(ROOT / "src")),
        encoding="utf-8",
    )

    environment = dict(os.environ)
    environment.setdefault("PDYNAMO3_SCRATCH", str(tmp_path))
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]

    trajectory = tmp_path / "hbond_scan.ptGeo"
    rows = [
        line.split()
        for line in (trajectory / "output.log").read_text().splitlines()
        if line.startswith("DATA")
    ]
    assert [int(row[1]) for row in rows] == [0, 1, 2]
    # RelaxedSurfaceScan logs the relaxed distance it reached, not the target.
    logged_distances = [float(row[2]) for row in rows]
    energies = [float(row[3]) for row in rows]

    from pCore import Unpickle

    for step, target in enumerate(targets):
        coordinates = Unpickle(str(trajectory / "frame{}.pkl".format(step)))
        distance = coordinates.Distance(ACCEPTOR, DONOR_H)
        # k = 4000 kJ mol^-1 Å^-2 against the weak H-bond force keeps the
        # relaxed distance within a few hundredths of the target.
        assert distance == pytest.approx(target, abs=0.03)
        assert distance == pytest.approx(logged_distances[step], abs=1.0e-6)
    # Stretching the hydrogen bond beyond its 1.76 Å minimum raises the energy.
    assert energies[0] < energies[1] < energies[2]
