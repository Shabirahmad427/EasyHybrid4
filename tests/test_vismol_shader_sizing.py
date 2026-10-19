"""Guard VisMol point-sprite sizing against display-scale regressions.

The real-context checks are in tests/render_validation_scene.py; these fast
checks keep the fixes in place on every platform.
"""

import ast
import importlib
import sys
from pathlib import Path

GRAPHICS = Path(__file__).resolve().parents[1] / "src" / "graphics_engine" / "src"
REPRESENTATIONS = GRAPHICS / "vismol" / "libgl" / "representations.py"


def _method(class_name, method_name):
    tree = ast.parse(REPRESENTATIONS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError("%s.%s not found" % (class_name, method_name))


def _uniform_names(function):
    names = set()
    for node in ast.walk(function):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_get_uniform_location"):
            names.update(arg.value for arg in node.args if isinstance(arg, ast.Constant))
    return names


def test_impostor_sprite_size_follows_viewport_height():
    sys.path.insert(0, str(GRAPHICS))
    try:
        shaders = importlib.import_module("vismol.libgl.shaders.impostor")
    finally:
        sys.path.remove(str(GRAPHICS))
    source = shaders.shader_type[0]["vertex_shader"]
    # A fixed pixel scale ignored window size and halved spheres at 2x.
    assert "256.0" not in source
    assert "uniform float u_viewport_height" in source
    assert "u_viewport_height" in source.split("void main", 1)[1]
    assert "u_viewport_height" in _uniform_names(
        _method("ImpostorRepresentation", "_load_camera_pos"))


def test_impostor_selection_size_uses_selection_program():
    method = _method("ImpostorRepresentation", "_make_gl_sel_representation_vao_and_vbos")
    calls = [node for node in ast.walk(method)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == "_make_gl_impostor_buffer"]
    assert [ast.unparse(call.args[1]) for call in calls] == ["self.sel_shader_program"]


def test_dots_send_point_size_uniform():
    # With program point size enabled, glPointSize is ignored; without the
    # uniform the dot size is driver-defined (zero on Mesa).
    for method in ("draw_representation", "draw_background_sel_representation"):
        assert "point_size" in _uniform_names(_method("DotsRepresentation", method))
