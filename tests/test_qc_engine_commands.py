"""EH4-602: external QC engine wrappers run without a shell.

The wrappers in src/util/extras are copied into pDynamo's pMolecule.QCModel
by install.py, so they are loaded here as part of that package. The external
programs are not run: subprocess.run is captured and the exact argument list
is checked, including executable and input paths that contain spaces.
"""

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires a compiled pDynamo3 checkout",
)


def _load_wrapper(file_name):
    pytest.importorskip("pBabel")
    import pMolecule.QCModel  # noqa: F401  (parent package for relative imports)

    spec = importlib.util.spec_from_file_location(
        "pMolecule.QCModel._eh4_" + Path(file_name).stem,
        ROOT / "src" / "util" / "extras" / file_name,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture_runs(module, monkeypatch):
    runs = []

    def fake_run(args, **kwargs):
        runs.append((list(args), kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return runs


def _target(charge=0, multiplicity=1):
    return SimpleNamespace(electronicState=SimpleNamespace(charge=charge, multiplicity=multiplicity))


def test_mopac_passes_paths_with_spaces_as_single_arguments(tmp_path, monkeypatch):
    module = _load_wrapper("QCModelMOPAC.py")
    runs = _capture_runs(module, monkeypatch)
    monkeypatch.chdir(tmp_path)  # Execute chdirs; monkeypatch restores the cwd
    job_dir = tmp_path / "QC Scratch"
    job_dir.mkdir()
    model = object.__new__(module.QCModelMOPAC)
    executable = str(tmp_path / "My Programs" / "MOPAC2016.exe")
    monkeypatch.setattr(type(model), "command", property(lambda self: executable))
    state = SimpleNamespace(paths={"Input": str(job_dir / "job.mop"), "Output": str(job_dir / "job.out")})

    assert model.Execute(state, _target()) is True

    assert len(runs) == 1
    args, kwargs = runs[0]
    assert args == [executable, str(job_dir / "job.mop")]
    assert kwargs["cwd"] == str(job_dir)
    assert kwargs["stdout"] is module.subprocess.DEVNULL
    assert kwargs["stderr"] is module.subprocess.DEVNULL
    assert "shell" not in kwargs


def test_sparrow_keeps_flags_and_splits_keywords_into_arguments(tmp_path, monkeypatch):
    module = _load_wrapper("QCModelSPARROW.py")
    runs = _capture_runs(module, monkeypatch)
    monkeypatch.chdir(tmp_path)
    model = object.__new__(module.QCModelSPARROW)
    executable = str(tmp_path / "My Programs" / "sparrow")
    monkeypatch.setattr(type(model), "command", property(lambda self: executable))
    model.keywords = "--scf_mixer diis  --max_scf_iterations 200"
    input_path = str(tmp_path / "QC Scratch" / "SPARROWJob.xyz")
    state = SimpleNamespace(paths={"Input": input_path})

    assert model.Execute(state, _target(charge=-1, multiplicity=2)) is True

    args, kwargs = runs[0]
    assert args == [
        executable, "-c", "-1", "-s", "2", "-M", "PM6", "-G", "-o",
        "--scf_mixer", "diis", "--max_scf_iterations", "200",
        "-x", input_path,
    ]
    assert "shell" not in kwargs and "cwd" not in kwargs
    # Output still goes to SPARROWJob.out in the working directory.
    assert (tmp_path / "SPARROWJob.out").is_file()
