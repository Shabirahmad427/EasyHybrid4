"""Tests that plotting calculations remain importable without GTK."""

import os
import subprocess
import sys
from pathlib import Path


def test_color_calculations_import_without_loading_gtk():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
import importlib.abc
import sys

class RejectGtkImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'gi' or fullname.startswith('gi.'):
            raise AssertionError('pure plotting calculations imported GTK')

sys.meta_path.insert(0, RejectGtkImports())
from util.easyplot import bilinear_interpolation, get_color, interpolate_color

assert 'gi' not in sys.modules
assert interpolate_color((0.0, 2.0), (2.0, 4.0), 0.5) == [1.0, 3.0]
assert get_color(0.5, {0.0: (0, 0, 0), 1.0: (2, 4, 6)}) == [1.0, 2.0, 3.0]
assert bilinear_interpolation((0, 0, 0, 0), (10, 0, 0, 0),
                              (10, 10, 0, 0), (0, 10, 0, 0), 0.5, 0.5) == (5, 5, 0, 0)
"""

    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)


def test_easyplot_package_preserves_public_plot_widget_exports():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
from util.easyplot import Canvas, ImagePlot, XYPlot, XYScatterPlot, export_plot_to_png

assert Canvas.__name__ == 'Canvas'
assert ImagePlot.__name__ == 'ImagePlot'
assert XYPlot.__name__ == 'XYPlot'
assert XYScatterPlot.__name__ == 'XYScatterPlot'
assert callable(export_plot_to_png)
"""

    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)


def test_color_square_draws_with_cairo_without_gtk():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
import importlib.abc

class RejectGtkImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'gi' or fullname.startswith('gi.'):
            raise AssertionError('Cairo color renderer imported GTK')

import sys
sys.meta_path.insert(0, RejectGtkImports())
import cairo
from util.easyplot.color_utils import ColorSquareBilinearInterpolation

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
ColorSquareBilinearInterpolation(
    surface, 0, 0, 2,
    (255, 0, 0, 255), (0, 255, 0, 255),
    (0, 0, 255, 255), (255, 255, 255, 255),
).draw()
surface.flush()
assert 'gi' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)


def test_plot_pointer_callbacks_ignore_missing_or_stale_transform():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
from types import SimpleNamespace
from util.easyplot import Canvas

event = SimpleNamespace(x=12.0, y=7.0)
unset = SimpleNamespace()
assert Canvas.get_i_and_j_from_click_event(unset, event) == (None, None, 12, 7)
stale = SimpleNamespace(bx=2, by=1, factor_x=None, factor_y=None)
assert Canvas.get_i_and_j_from_click_event(stale, event) == (None, None, 12, 7)
zero = SimpleNamespace(bx=2, by=1, factor_x=0, factor_y=3)
assert Canvas.get_i_and_j_from_click_event(zero, event) == (None, None, 12, 7)
valid = SimpleNamespace(bx=2, by=1, factor_x=5, factor_y=3)
assert Canvas.get_i_and_j_from_click_event(valid, event) == (2, 2, 12, 7)
assert Canvas.check_clicked_points(unset, None, None) is False
stale.get_i_and_j_from_click_event = lambda e: Canvas.get_i_and_j_from_click_event(stale, e)
assert Canvas.on_motion(stale, None, event) is False
"""

    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)
