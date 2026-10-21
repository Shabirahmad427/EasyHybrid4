"""Keep installer dependency checks aligned with runtime imports."""

from pathlib import Path
import re

import install


def test_graphics_runtime_dependencies_are_declared_and_checked():
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    requirement_names = {
        re.split(r"[<>=!~]", line, maxsplit=1)[0].strip().lower()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert install.PYTHON_LIBRARIES["PIL"] == "Pillow"
    assert "pillow" in requirement_names
    assert install.PYTHON_LIBRARIES["yaml"] == "PyYAML"
    assert "pyyaml" in requirement_names


def test_linux_install_lock_pins_gtk_python_and_core_graphics_runtime():
    lock = (
        Path(__file__).resolve().parents[1]
        / "environments"
        / "easyhybrid4-linux-64.lock"
    )
    lines = lock.read_text(encoding="utf-8").splitlines()
    packages = [line for line in lines if line.startswith("https://")]

    assert "# platform: linux-64" in lines
    assert "@EXPLICIT" in lines
    assert any("/linux-64/gtk4-4.24.1-" in package for package in packages)
    assert any("/linux-64/python-3.12.15-" in package for package in packages)
    assert any("/linux-64/numpy-2.5.4-" in package for package in packages)
    assert all("conda.anaconda.org/conda-forge/" in package for package in packages)
