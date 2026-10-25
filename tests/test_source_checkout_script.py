"""Pure checks for the generic fresh-source-checkout matrix driver."""

import importlib.util
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "check_source_checkout.py"
_SPEC = importlib.util.spec_from_file_location("check_source_checkout", SCRIPT_PATH)
check_source_checkout = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_source_checkout)


def _git(*arguments: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *arguments], cwd=cwd, text=True).strip()


def test_fresh_clone_checks_out_the_requested_commit(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _git("init", cwd=source)
    _git("config", "user.name", "EasyHybrid test", cwd=source)
    _git("config", "user.email", "test@example.invalid", cwd=source)
    (source / "tracked.txt").write_text("tracked source\n", encoding="utf-8")
    _git("add", "tracked.txt", cwd=source)
    _git("commit", "-m", "fixture source", cwd=source)
    commit = _git("rev-parse", "HEAD", cwd=source)
    _git("checkout", "--detach", commit, cwd=source)
    monkeypatch.setenv("GITHUB_SHA", commit)

    clone = check_source_checkout._fresh_clone(source, tmp_path / "matrix")

    assert _git("rev-parse", "HEAD", cwd=clone) == commit
    assert (clone / "tracked.txt").read_text(encoding="utf-8") == "tracked source\n"


def test_source_environment_points_at_fresh_tree_and_isolates_user_settings(
    monkeypatch, tmp_path
):
    matrix = tmp_path / "matrix"
    source = tmp_path / "fresh" / "EasyHybrid4"
    pdynamo = matrix / "pDynamo3"
    pdynamo.mkdir(parents=True)
    source.mkdir(parents=True)
    temp_home = tmp_path / "user-home"
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join((str(matrix), str(matrix / "src"))))
    monkeypatch.setenv("PDYNAMO3_HOME", str(pdynamo))

    environment = check_source_checkout._source_environment(source, matrix, temp_home)

    assert environment["PYTHONPATH"].split(os.pathsep) == [
        str(source), str(source / "src" / "graphics_engine" / "src"), str(pdynamo)
    ]
    assert environment["HOME"] == str(temp_home)
    assert environment["XDG_CONFIG_HOME"] == str(temp_home / ".config")
    assert environment["PDYNAMO3_PARAMETERS"] == str(pdynamo / "parameters")
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert (temp_home / ".VisMol").is_dir()
