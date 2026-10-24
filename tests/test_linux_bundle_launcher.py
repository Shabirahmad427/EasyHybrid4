"""Exercise the Linux bundle launch boundary without starting the GUI."""

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "packaging" / "linux" / "run-easyhybrid4.sh"


def make_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    app = bundle / "app"
    runtime_bin = bundle / "runtime" / "bin"
    activation_dir = bundle / "runtime" / "etc" / "conda" / "activate.d"
    schema_dir = bundle / "runtime" / "share" / "glib-2.0" / "schemas"
    launcher = bundle / "run-easyhybrid4.sh"
    pdynamo = tmp_path / "pDynamo3"
    (app / "src" / "graphics_engine" / "src").mkdir(parents=True)
    runtime_bin.mkdir(parents=True)
    activation_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    (activation_dir / "runtime.sh").write_text(
        'export GSETTINGS_SCHEMA_DIR="$CONDA_PREFIX/share/glib-2.0/schemas"\n',
        encoding="utf-8",
    )
    (app / "easyhybrid.py").write_text("# fixture entry point\n", encoding="utf-8")
    (pdynamo / "pCore").mkdir(parents=True)
    (pdynamo / "parameters" / "ccsStyleSheets").mkdir(parents=True)
    shutil.copy2(LAUNCHER, launcher)

    fake_python = runtime_bin / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$@\" > \"$CAPTURE_ARGS\"\n"
        "printf '%s\\n' \"$PDYNAMO3_HOME\" \"$PDYNAMO3_PARAMETERS\" "
        "\"$PDYNAMO3_SCRATCH\" \"$PDYNAMO3_STYLE\" \"$PYTHONNOUSERSITE\" "
        "\"$PYTHONPATH\" \"$PYOPENGL_PLATFORM\" \"$CONDA_PREFIX\" "
        "\"$GSETTINGS_SCHEMA_DIR\" > \"$CAPTURE_ENV\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    return bundle, pdynamo, launcher


def test_linux_bundle_launcher_sets_runtime_and_external_pdynamo_paths(tmp_path):
    bundle, pdynamo, launcher = make_bundle(tmp_path)
    capture_args = tmp_path / "args.txt"
    capture_env = tmp_path / "env.txt"
    unpack_count = tmp_path / "unpack-count.txt"
    conda_unpack = bundle / "runtime" / "bin" / "conda-unpack"
    conda_unpack.write_text(
        "#!/usr/bin/env bash\nprintf x >> \"$UNPACK_COUNT\"\n",
        encoding="utf-8",
    )
    conda_unpack.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "PDYNAMO3_HOME": str(pdynamo),
            "HOME": str(tmp_path),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "PYTHONPATH": "/existing/python/path",
            "CAPTURE_ARGS": str(capture_args),
            "CAPTURE_ENV": str(capture_env),
            "UNPACK_COUNT": str(unpack_count),
        }
    )

    result = subprocess.run(
        [str(launcher), "--smoke-argument"],
        cwd=bundle,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert capture_args.read_text(encoding="utf-8").splitlines() == [
        str(bundle / "app" / "easyhybrid.py"),
        "--smoke-argument",
    ]
    values = capture_env.read_text(encoding="utf-8").splitlines()
    assert values[:5] == [
        str(pdynamo),
        str(pdynamo / "parameters"),
        str(tmp_path / "cache" / "easyhybrid4" / "scratch"),
        str(pdynamo / "parameters" / "ccsStyleSheets" / "defaultStyle.css"),
        "1",
    ]
    assert values[5].split(":") == [
        str(bundle / "app"),
        str(bundle / "app" / "src" / "graphics_engine" / "src"),
        str(pdynamo),
        "/existing/python/path",
    ]
    assert values[6] == "egl"
    assert values[7] == str(bundle / "runtime")
    assert values[8] == str(
        bundle / "runtime" / "share" / "glib-2.0" / "schemas"
    )
    second_run = subprocess.run(
        [str(launcher)], cwd=bundle, env=environment, capture_output=True,
        text=True, check=False,
    )
    assert second_run.returncode == 0, second_run.stderr
    assert unpack_count.read_text(encoding="utf-8") == "x"


def test_linux_bundle_launcher_reports_missing_pdynamo_checkout(tmp_path):
    bundle, _, launcher = make_bundle(tmp_path)
    environment = os.environ.copy()
    environment.pop("PDYNAMO3_HOME", None)

    result = subprocess.run(
        [str(launcher)],
        cwd=bundle,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Set PDYNAMO3_HOME" in result.stderr
