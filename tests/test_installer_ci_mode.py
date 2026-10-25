"""The native matrix installer path must never mutate shared environments."""

from pathlib import Path
from types import SimpleNamespace
import sys

import install


def test_ci_mode_declines_all_optional_changes(monkeypatch, capsys):
    monkeypatch.setattr(install, "CI_MODE", True)

    assert install.ask_yes_no("install optional module?") is False
    assert install.configure_xtb_command() is True
    assert install.install_qc_modules() is True
    assert install.create_desktop_icon() is None

    output = capsys.readouterr().out
    assert "optional change skipped" in output
    assert "skipping optional xTB" in output
    assert "skipping optional writes" in output
    assert "skipping desktop" in output


def test_ci_pdynamo_check_requires_declared_checkout(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "CI_MODE", True)
    monkeypatch.setattr(install.importlib, "import_module", lambda name: SimpleNamespace(
        __file__=str(tmp_path / name / "__init__.py")
    ))
    monkeypatch.delenv("PDYNAMO3_HOME", raising=False)

    assert install.check_pdynamo() == ["PDYNAMO3_HOME"]


def test_ci_pdynamo_check_rejects_modules_from_another_checkout(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "CI_MODE", True)
    declared_home = tmp_path / "declared"
    imported_home = tmp_path / "imported"
    monkeypatch.setenv("PDYNAMO3_HOME", str(declared_home))
    monkeypatch.setattr(install.importlib, "import_module", lambda name: SimpleNamespace(
        __file__=str(imported_home / name / "__init__.py")
    ))

    assert install.check_pdynamo() == ["PDYNAMO3_HOME"]


def test_ci_pdynamo_check_accepts_modules_from_declared_checkout(monkeypatch, tmp_path):
    monkeypatch.setattr(install, "CI_MODE", True)
    home = tmp_path / "pDynamo3"
    monkeypatch.setenv("PDYNAMO3_HOME", str(home))
    monkeypatch.setattr(install.importlib, "import_module", lambda name: SimpleNamespace(
        __file__=str(home / name / "__init__.py")
    ))
    monkeypatch.setattr(install, "EASYHYBRID_HOME", tmp_path)

    assert install.check_pdynamo() == []
    assert not (Path(tmp_path) / "paths.py").exists()


def test_ci_installer_builds_without_auto_installing_or_prompting(monkeypatch):
    calls = {}
    monkeypatch.setattr(sys, "argv", ["install.py", "--ci", "--yes"])
    monkeypatch.setattr(
        install,
        "check_external_libraries",
        lambda *, auto_install: calls.setdefault("auto_install", auto_install) or True,
    )
    monkeypatch.setattr(install, "check_pdynamo", lambda: [])
    monkeypatch.setattr(install, "check_qc_engines", lambda: None)
    monkeypatch.setattr(install, "install_vismol", lambda: True)

    assert install.main() is True
    assert calls["auto_install"] is False
    assert install.CI_MODE is True
    assert install.NON_INTERACTIVE is False


def test_vismol_build_uses_active_python_without_a_shell(monkeypatch, tmp_path):
    setup_script = tmp_path / "setup.py"
    setup_script.write_text("# fake setup script\n", encoding="utf-8")
    vismol_source = tmp_path / "src"
    vismol_source.mkdir()
    commands = []
    monkeypatch.setattr(install, "VISMOL_PATH", tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda command, **kwargs: commands.append((command, kwargs)),
    )
    monkeypatch.setattr(install.importlib, "import_module", lambda name: object())

    assert install.install_vismol() is True
    assert commands == [(
        [sys.executable, str(setup_script), "build_ext", "--inplace"],
        {"cwd": str(tmp_path), "check": True},
    )]
