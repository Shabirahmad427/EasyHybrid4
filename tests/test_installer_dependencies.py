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
