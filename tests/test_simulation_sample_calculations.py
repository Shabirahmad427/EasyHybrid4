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


def test_exported_umbrella_sampling_feeds_wham_a_finite_pmf(tmp_path):
    import glob
    import math

    from gui.windows.setup.windows_and_dialogs.dialogs.export_dialogs import (
        build_simulation_script,
    )

    system_pickle = _water_dimer_pickle(tmp_path)
    targets = (1.80, 1.85, 1.90)
    md = {
        "integrator": "Langevin", "steps_eq": 200, "steps_dc": 4000, "timeStep": 0.001,
        "temperatureStart": 300.0, "collisionFrequency": 25.0, "seed": 314159,
        "logFrequency": 100000, "trajectory_frequency": 100,
        "trajectory_frequency_dc_ptRes": 1, "trajectory_frequency_dc_ptGeo": 400,
    }
    parameters = {
        "simulation_type": "Umbrella_Sampling",
        "folder": str(tmp_path),
        "traj_folder_name": "hbond_us",
        "RC1": {
            "rc_type": "simple_distance",
            "ATOMS": [ACCEPTOR, DONOR_H],
            "ATOM_NAMES": ["O", "H"],
            "nsteps": len(targets),
            "dminimum": targets[0],
            "dincre": targets[1] - targets[0],
            # sigma = sqrt(kT/k) ~ 0.05 Å at 300 K: adjacent windows overlap.
            "force_constant": 1000.0,
        },
        "RC2": None,
        "input_type": 0,  # serial windows
        "MD_parm": md,
        "OPT_parm": {"optimizer": "ConjugatedGradient", "maximumIterations": 300,
                     "rmsGradientTolerance": 0.05},
        "NmaxThreads": 1,
        "maximumIterations": 300,
        "rmsGradientTolerance": 0.05,
        "logFrequency": 100000,
    }
    script = tmp_path / "exported_umbrella.py"
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

    from pCore import Unpickle

    run = tmp_path / "hbond_us"
    for window, target in enumerate(targets):
        frames = run / "data_collection_traj" / "window{}.ptGeo".format(window)
        # 4000 data-collection steps saved every 400 steps, plus the start.
        assert len(list(frames.glob("frame*"))) == 11
        assert (run / "data_collection" / "window{}.ptRes".format(window) / "block0.pkl").is_file()
        optimized = Unpickle(str(run / "optmization.ptGeo" / "frame{}.pkl".format(window)))
        assert optimized.Distance(ACCEPTOR, DONOR_H) == pytest.approx(target, abs=0.05)

    # EasyHybrid's WHAM on exactly these windows, as the WHAM window would run it.
    from pdynamo.p_methods.wham import WHAMAnalysis

    ok, results = WHAMAnalysis().run({
        "folder": str(tmp_path), "logfile": "wham", "system": None,
        "file_names": sorted(glob.glob(str(run / "data_collection" / "window*.ptRes"))),
        "bins": [20], "logFrequency": 1000, "maximumIterations": 2000,
        "rmsGradientTolerance": 1.0e-3, "temperature": 300.0, "type": 0,
    })
    assert ok, results
    rows = [
        [float(value) for value in line.split()]
        for line in open(results["pmf"]) if line.strip()
    ]
    assert len(rows) == 20
    assert rows[0][0] < targets[0] and rows[-1][0] > targets[-1]
    # Langevin trajectories differ per platform (Windows MSYS2 GTK 4.16 left a
    # sparse tail bin empty at 1000 steps). Require a continuous PMF between
    # the window centres, where adjacent windows overlap; tails may be sparse.
    core = [pmf for centre, pmf in rows if targets[0] <= centre <= targets[-1]]
    assert len(core) >= 5 and all(math.isfinite(pmf) for pmf in core), rows
    finite = [pmf for _, pmf in rows if math.isfinite(pmf)]
    assert min(finite) == pytest.approx(0.0, abs=1.0e-6)


def _minimized_endpoints(tmp_path, stretched_distance):
    from pCore import Pickle, Unpickle
    from pMolecule import RestraintDistance, RestraintEnergyModel, RestraintModel
    from pSimulation import ConjugateGradientMinimize_SystemGeometry

    system = Unpickle(str(_water_dimer_pickle(tmp_path)))
    minimize = lambda: ConjugateGradientMinimize_SystemGeometry(  # noqa: E731
        system, logFrequency=100000, maximumIterations=500, rmsGradientTolerance=0.01
    )
    minimize()
    reactant = tmp_path / "reactant.pkl"
    Pickle(str(reactant), system.coordinates3)
    restraints = RestraintModel()
    system.DefineRestraintModel(restraints)
    restraints["hbond"] = RestraintDistance.WithOptions(
        energyModel=RestraintEnergyModel.Harmonic(stretched_distance, 4000.0),
        point1=ACCEPTOR, point2=DONOR_H,
    )
    minimize()
    system.DefineRestraintModel(None)
    product = tmp_path / "product.pkl"
    Pickle(str(product), system.coordinates3)
    return reactant, product


def test_exported_nudged_elastic_band_builds_a_continuous_path(tmp_path):
    from gui.windows.setup.windows_and_dialogs.dialogs.export_dialogs import (
        build_simulation_script,
    )

    reactant, product = _minimized_endpoints(tmp_path, 2.20)
    images = 5
    # chain_of_states_opt_window.py defaults, with fewer images/iterations.
    parameters = {
        "simulation_type": "Nudged_Elastic_Band",
        "number_of_structures": images, "logFrequency": 100000,
        "maximumIterations": 200, "rmsGradientTolerance": 0.1,
        "trajectory_name": "hbond_neb", "folder": str(tmp_path),
        "external_coords": False,
        "reac_coordinates": str(reactant), "prod_coordinates": str(product),
        "fixedTerminalImages": True, "forceOneSingleImageOptimization": False,
        "forceSingleImageOptimizations": False,
        "forceSplineRedistributionCheckPerIteration": False,
        "freezeRMSGradientTolerance": 0.0, "optimizer": None, "poolFactory": None,
        "rmsGradientToleranceScale": 0.25, "splineRedistributionTolerance": 1.5,
        "springForceConstant": 500.0, "useSplineRedistribution": False,
    }
    script = tmp_path / "exported_neb.py"
    script.write_text(
        build_simulation_script(parameters, str(_water_dimer_pickle(tmp_path)), str(ROOT / "src")),
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment.setdefault("PDYNAMO3_SCRATCH", str(tmp_path))
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]

    from pCore import Unpickle

    path = tmp_path / "hbond_neb.ptGeo"
    frames = sorted(path.glob("frame*.pkl"), key=lambda f: int(f.stem[5:]))
    assert len(frames) == images
    coordinates = [Unpickle(str(frame)) for frame in frames]
    distances = [c.Distance(ACCEPTOR, DONOR_H) for c in coordinates]
    # Fixed terminal images keep the supplied endpoints.
    assert distances[0] == pytest.approx(Unpickle(str(reactant)).Distance(ACCEPTOR, DONOR_H), abs=1.0e-6)
    assert distances[-1] == pytest.approx(Unpickle(str(product)).Distance(ACCEPTOR, DONOR_H), abs=1.0e-6)
    assert distances[-1] == pytest.approx(2.20, abs=0.03)
    # The optimized path stretches the hydrogen bond step by step.
    assert all(a < b for a, b in zip(distances, distances[1:])), distances
