"""EH4-202 real-context render validation at display scale 1 and 2.

Runs tests/render_validation_scene.py in a fresh process per scale. That
script checks GL capabilities, every representation's draw, impostor sphere
size against the exact projection, the 2x offscreen export, colour-ID
picking and resize on a live Gtk.GLArea. Here the two scales are compared:
geometry covers the same fraction of the view at any pixel density.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "render_validation_scene.py"

# Filled geometry must cover the same fraction of the view at 1x and 2x;
# 5% allows silhouette pixels at the two densities. lines/nonbonded are
# fixed-pixel-width GL lines by design and are excluded.
SCALE_INVARIANT = ("sticks", "spheres", "vdw_spheres", "stick_spheres", "dots", "impostor")
COVERAGE_TOLERANCE = 0.05


def run_scene(scale):
    environment = os.environ.copy()
    environment["GDK_SCALE"] = str(scale)
    environment["G_DEBUG"] = "fatal-criticals"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
        env=environment,
        check=False,
    )
    lines = [line for line in completed.stdout.splitlines()
             if line.startswith("EASYHYBRID_RENDER_VALIDATION=")]
    assert lines, completed.stdout[-4000:] + completed.stderr[-4000:]
    result = json.loads(lines[-1].split("=", 1)[1])
    print("EASYHYBRID_RENDER_SCALE=%d %s" % (scale, lines[-1]), flush=True)
    failed = {name: result["checks"].get(name) for name in result["failures"]}
    assert completed.returncode == 0 and not result["failures"], (
        failed, result.get("exception", ""), completed.stderr[-4000:])
    return result


@pytest.mark.skipif(
    os.environ.get("EASYHYBRID_RUN_GRAPHICS_TESTS") != "1",
    reason="requires bundled graphics extensions and a native GTK display",
)
def test_vismol_render_validation_at_scale_1_and_2():
    base = run_scene(1)
    hidpi = run_scene(2)

    if not hidpi["scale_applied"]:
        # Some backends (macOS Quartz) ignore GDK_SCALE; the scale-2 run
        # then repeats 1x and HiDPI stays NOT TESTED in that cell.
        assert os.environ.get("EASYHYBRID_REQUIRE_HIDPI_RENDER") != "1", (
            "GDK_SCALE=2 did not enlarge the GL framebuffer", hidpi["framebuffer"])
        print("EASYHYBRID_RENDER_HIDPI=NOT_APPLIED", flush=True)
        return

    assert hidpi["framebuffer"] == [2 * value for value in base["framebuffer"]]
    for name in SCALE_INVARIANT:
        if name == "impostor" and any(
                size["clamped"] for size in hidpi["impostor_sizes"].values()):
            continue  # capped by GL_POINT_SIZE_RANGE; checked per sphere
        one, two = base["coverage"][name], hidpi["coverage"][name]
        assert abs(two - one) <= COVERAGE_TOLERANCE * one, (name, one, two)
    print("EASYHYBRID_RENDER_HIDPI=APPLIED", flush=True)
