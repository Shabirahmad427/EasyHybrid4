"""Guard selected scientific and state modules from GUI imports."""

import os
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def test_science_and_state_modules_import_without_gtk_or_vismol_gui():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    graphics_path = str(repo_root / "src" / "graphics_engine" / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, graphics_path, env.get("PYTHONPATH")))
    )
    code = """
import importlib.abc
import sys

class RejectPresentationImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'gi' or fullname.startswith('gi.'):
            raise AssertionError('scientific/state module imported PyGObject')
        if fullname == 'vismol.gui' or fullname.startswith('vismol.gui.'):
            raise AssertionError('scientific/state module imported VisMol GUI')

sys.meta_path.insert(0, RejectPresentationImports())
from pdynamo.pDynamo2EasyHybrid.state import SessionState
from util.easyplot.color_math import bilinear_interpolation, get_color
from util.md_analysis import compute_box_density, compute_rdf, compute_rmsf
from util.ramachandran import compute_phi_psi
from src.os_integration.gtk_startup import configure_startup_environment

assert 'gi' not in sys.modules
assert not any(name == 'vismol.gui' or name.startswith('vismol.gui.')
               for name in sys.modules)
assert SessionState().systems == {0: None}
assert callable(compute_rmsf) and callable(compute_rdf)
assert callable(compute_box_density) and callable(compute_phi_psi)
assert callable(get_color) and callable(bilinear_interpolation)
assert callable(configure_startup_environment)
"""
    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)


def test_pdynamo_workflow_package_imports_without_gtk():
    """Load calculation workflows with PyGObject deliberately unavailable."""
    if importlib.util.find_spec("pCore") is None:
        pytest.skip("pDynamo3 is not configured in this Python environment")

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
import sys
sys.modules['gi'] = None
import pdynamo.p_methods
assert 'pdynamo.p_methods.energy' in sys.modules
assert 'pdynamo.p_methods.geometry_optimization' in sys.modules
assert 'pdynamo.p_methods.molecular_dynamics' in sys.modules
assert sys.modules['gi'] is None
"""
    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)


def test_pdynamo_session_keeps_legacy_state_attributes_without_display():
    """Ensure the GTK-facing facade preserves the old state API."""
    if importlib.util.find_spec("pCore") is None:
        pytest.skip("pDynamo3 is not configured in this Python environment")

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    graphics_path = str(repo_root / "src" / "graphics_engine" / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, graphics_path, env.get("PYTHONPATH")))
    )
    for display_variable in ("DISPLAY", "WAYLAND_DISPLAY", "GDK_BACKEND"):
        env.pop(display_variable, None)
    code = """
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk
from pdynamo.pDynamo2EasyHybrid.session import pDynamoSession
from pdynamo.pDynamo2EasyHybrid.state import SessionState

session = pDynamoSession.__new__(pDynamoSession)
session.state = SessionState()
assert session.psystem is session.state.systems
session.psystem = {7: object()}
session.active_id = 7
assert session.get_system() is session.psystem[7]
session.changed = True
assert session.state.changed is True
assert Gdk.Display.get_default() is None
"""
    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)
