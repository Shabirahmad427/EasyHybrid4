"""Guard the colour-ID picking pass against driver line-width limits.

macOS core-profile OpenGL clamps glLineWidth() to 1 pixel, so selection
geometry that relies on wide GL lines leaves atoms nearly unclickable there.
The real-context hit-region check is in test_gtk_icon_theme_smoke.py; these
fast checks keep the portable shader design from regressing.
"""

import ast
import importlib
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GRAPHICS = REPO / "src" / "graphics_engine" / "src"
REPRESENTATIONS = GRAPHICS / "vismol" / "libgl" / "representations.py"

# (shader module, geometry shader, fragment shader, representation class)
PICK_SHADERS = (
    ("lines", "sel_geometry_shader_lines", "sel_fragment_shader_lines",
     "LinesRepresentation"),
    ("nonbonded", "sel_geometry_shader_non_bonded",
     "sel_fragment_shader_non_bonded", "NonBondedRepresentation"),
    ("dashed_lines", "sel_geometry_shader_dashed_lines",
     "sel_fragment_shader_dashed_lines", "DashedLinesRepresentation"),
)


@pytest.fixture(scope="module")
def shader_modules():
    sys.path.insert(0, str(GRAPHICS))
    try:
        return {
            name: importlib.import_module("vismol.libgl.shaders." + name)
            for name, *_ in PICK_SHADERS
        }
    finally:
        sys.path.remove(str(GRAPHICS))


@pytest.mark.parametrize("module, geometry, fragment, _rep", PICK_SHADERS)
def test_pick_geometry_emits_wide_triangles(shader_modules, module, geometry,
                                            fragment, _rep):
    source = getattr(shader_modules[module], geometry)
    assert re.search(r"layout\s*\(\s*triangle_strip", source)
    assert "line_strip" not in source
    assert "emit_wide_segment(" in source
    assert "uniform float u_pick_line_width" in source
    assert "flat out vec3 frag_color" in source
    assert "flat in vec3 frag_color" in getattr(shader_modules[module], fragment)


def _selection_method(class_name):
    tree = ast.parse(REPRESENTATIONS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (isinstance(item, ast.FunctionDef)
                        and item.name == "draw_background_sel_representation"):
                    return item
    raise AssertionError("%s has no selection draw method" % class_name)


def _called_names(function):
    return {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


@pytest.mark.parametrize("_module, _geometry, _fragment, rep", PICK_SHADERS)
def test_pick_width_uses_uniform_not_gl_line_width(_module, _geometry,
                                                   _fragment, rep):
    method = _selection_method(rep)
    called = _called_names(method)
    assert "load_pick_line_uniforms" in called
    for node in ast.walk(method):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "glLineWidth"):
            # Only the reset to the core-profile default remains.
            assert [ast.literal_eval(arg) for arg in node.args] == [1]
