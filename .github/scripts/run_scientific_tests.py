"""Run pDynamo-dependent scientific and project tests without a display (EH4-504).

Usage: python run_scientific_tests.py   (PDYNAMO3_HOME must name the built
pDynamo3 checkout). Display variables are removed so these tests prove they
run where graphics are unavailable. Any skipped test fails the step: a skip
here means the scientific runtime was not actually exercised.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = (
    "tests/test_pdynamo_mm_workflow.py",
    "tests/test_reaction_coordinate_workflow.py",
    "tests/test_simulation_sample_calculations.py",
    "tests/test_qc_engine_commands.py",
    "tests/test_simulation_process_errors.py",
    "tests/test_process_cancellation.py",
    "tests/test_project_persistence.py",
    "tests/test_project_file.py",
    "tests/test_session_row_serialization.py",
    "tests/test_molecular_fixtures.py",
)


def main():
    home = os.environ.get("PDYNAMO3_HOME")
    if not home or not Path(home, "pCore").is_dir():
        sys.exit("PDYNAMO3_HOME must name the compiled pDynamo3 checkout")
    environment = os.environ.copy()
    for name in ("DISPLAY", "WAYLAND_DISPLAY"):
        environment.pop(name, None)
    scratch = Path(tempfile.gettempdir(), "easyhybrid-scientific-scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    environment.update(
        PDYNAMO3_PARAMETERS=os.path.join(home, "parameters"),
        PDYNAMO3_SCRATCH=str(scratch),
        PDYNAMO3_STYLE=os.path.join(home, "parameters", "ccsStyleSheets", "defaultStyle.css"),
        PYTHONPATH=os.pathsep.join(
            part for part in (home, environment.get("PYTHONPATH", "")) if part
        ),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", *TESTS],
        cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)
    summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if "skipped" in summary or "passed" not in summary:
        sys.exit("scientific tests did not all run: " + summary)
    print("EASYHYBRID_SCIENTIFIC_TESTS=" + summary)


if __name__ == "__main__":
    main()
