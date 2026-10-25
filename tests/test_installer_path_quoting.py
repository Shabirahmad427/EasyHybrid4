"""EH4-602: installer writes user paths as inert data, not as code."""

import ast
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("eh4_install", ROOT / "install.py")
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

AWKWARD_PATH = "/opt/My Programs/xtb $HOME `id` \"quoted\" it's/bin/xtb"


@pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None,
                    reason="sources a bash environment script")
def test_environment_script_keeps_path_literal_when_sourced(tmp_path):
    script = tmp_path / "environment_bash.com"
    script.write_text("export XTB_COMMAND=\"/old/xtb\"\n# keep me\n")

    assert install._write_env_var_to_script(script, "XTB_COMMAND", AWKWARD_PATH)

    text = script.read_text()
    assert text.count("XTB_COMMAND=") == 1 and "# keep me" in text
    shown = subprocess.run(
        ["bash", "-c", 'source "$1"; printf %s "$XTB_COMMAND"', "bash", str(script)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert shown == AWKWARD_PATH


@pytest.mark.parametrize("path", [
    r"C:\Users\New User\pDynamo3",  # \U and \N would be escapes in "..."
    "/home/user/pDynamo3",
    AWKWARD_PATH,
])
def test_paths_py_is_valid_python_for_any_path(path):
    source = install._pdynamo_paths_source(path)
    namespace = {}
    exec(compile(source, "paths.py", "exec"), namespace)
    assert namespace["PDYNAMO_HOME"] == path
    assert isinstance(ast.parse(source).body[0], ast.Assign)
