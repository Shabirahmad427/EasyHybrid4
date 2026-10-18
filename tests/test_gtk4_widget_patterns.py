"""Deterministic GTK4 widget-pattern tests for EH4-103.

Widget tests create real GTK4 widgets and need a display; they skip with an
explicit reason otherwise. They must pass on every GTK4 minor from 4.8: GTK
4.8 cannot create Gtk expressions from Python, and GTK 4.20+ auto-selects the
first Gtk.DropDown item where older minors keep an empty selection, so these
tests avoid both and check the portable helpers instead.
"""

import ast
import io
import os
import re
import sys
import tokenize
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
# Self-contained import paths (no PYTHONPATH, whose separator differs on
# Windows), so CI can run this file in every GTK cell with --noconftest.
for _path in (str(PROJECT_ROOT), str(SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Apply the application's own GTK startup policy before GTK initializes.
from src.os_integration.gtk_startup import configure_startup_environment  # noqa: E402

configure_startup_environment(str(PROJECT_ROOT))

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

needs_display = pytest.mark.skipif(
    Gdk.Display.get_default() is None,
    reason="GTK widget tests need a native or virtual display",
)


def test_display_available_when_required():
    """CI sets EASYHYBRID_REQUIRE_GTK_DISPLAY=1 so widget tests cannot silently skip."""
    if os.environ.get("EASYHYBRID_REQUIRE_GTK_DISPLAY") == "1":
        assert Gdk.Display.get_default() is not None, "no GTK display in a cell that requires one"


def _iterate(milliseconds=200):
    loop = GLib.MainLoop()
    GLib.timeout_add(milliseconds, loop.quit)
    loop.run()


def _labels(widget):
    found = []
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, Gtk.Label) and child.get_text():
            found.append(child.get_text())
        found.extend(_labels(child))
        child = child.get_next_sibling()
    return found


def _code_lines(path):
    """Yield (line number, code) with comments and string literals removed."""
    lines = {}
    source = path.read_text(encoding="utf-8")
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        lines.setdefault(token.start[0], []).append(token.string)
    for number in sorted(lines):
        yield number, " ".join(lines[number])


def _module_constant(relative_path, name):
    """Read a tuple constant from a window module without importing it."""
    tree = ast.parse((SRC / relative_path).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("%s not found in %s" % (name, relative_path))


# --------------------------------------------------------------------------- #
#  Scientific option values must survive the ComboBoxText -> DropDown move.    #
# --------------------------------------------------------------------------- #

def test_migrated_choices_keep_exact_scientific_values():
    assert [value for value, _ in _module_constant(
        "gui/windows/simulation/conjugate_peak_refinement_window.py", "BETA_TYPE_CHOICES"
    )] == ["PRP", "FR", "HS"]
    assert [value for value, _ in _module_constant(
        "gui/windows/simulation/transition_state_search_window.py", "HESSIAN_UPDATING_CHOICES"
    )] == ["BOFILL", "BFGS", "MS", "POWELL"]
    assert [value for value, _ in _module_constant(
        "gui/windows/builder/torsion_fit_window.py", "XTB_METHOD_CHOICES"
    )] == ["2", "1"]
    assert [value for value, _ in _module_constant(
        "gui/windows/builder/torsion_fit_window.py", "XTB_SOLVENT_CHOICES"
    )] == ["none", "water", "methanol"]


@pytest.mark.parametrize("ui_file, object_id", [
    ("gui/windows/simulation/conjugate_peak_refinement_window.glade", "combobox_beta_type"),
    ("gui/windows/simulation/transition_state_search_window.glade", "combobox_hessian_updating"),
])
def test_builder_choices_are_gtk4_dropdowns(ui_file, object_id):
    objects = {
        node.get("id"): node.get("class")
        for node in ET.parse(SRC / ui_file).getroot().iter("object")
    }
    assert objects[object_id] == "GtkDropDown"


def test_no_gtk3_or_gtk48_incompatible_patterns_remain():
    """Guard against reintroducing APIs that break on a supported GTK4 minor."""
    forbidden = {
        r"Gtk\.PropertyExpression\.new": "fails on GTK 4.8 (use gtk4_compat helpers)",
        r"Gtk\.(String|Numeric)Sorter\.new": "needs an expression (use property_sorter)",
        r"Gtk\.ComboBox(Text)?\b": "deprecated since GTK 4.10 (use gui.choice_dropdown)",
        r"\.popup_at_(widget|pointer)\(": "GTK3 Gtk.Menu API (use ContextMenu)",
        r"\.get_active_id\(|\.set_active_id\(": "ComboBox API (use gui.choice_dropdown)",
    }
    offenders = []
    for path in SRC.rglob("*.py"):
        if "graphics_engine" in path.parts:
            continue
        for number, code in _code_lines(path):
            code = code.replace(" . ", ".").replace(" ( ", "(").replace(" (", "(")
            for pattern, why in forbidden.items():
                if re.search(pattern, code):
                    offenders.append("%s:%d %s" % (path.relative_to(PROJECT_ROOT), number, why))
    for path in SRC.rglob("*.glade"):
        if re.search(r'class="GtkComboBox(Text)?"', path.read_text(encoding="utf-8")):
            offenders.append("%s GtkComboBox" % path.relative_to(PROJECT_ROOT))
    assert not offenders, "\n".join(offenders)


# --------------------------------------------------------------------------- #
#  Portable helpers, exercised with real widgets.                              #
# --------------------------------------------------------------------------- #

@needs_display
def test_choice_dropdown_selects_and_reads_values():
    from gui.choice_dropdown import new_choice_dropdown, select_choice_value, selected_choice_value

    dropdown = new_choice_dropdown((("PRP", "PRP (Polak-Ribiere)"), ("FR", "FR")), "FR")
    assert selected_choice_value(dropdown) == "FR"
    assert select_choice_value(dropdown, "PRP") is True
    assert selected_choice_value(dropdown) == "PRP"
    # An unknown saved value keeps the current choice, like ComboBox.set_active_id.
    assert select_choice_value(dropdown, "UNKNOWN") is False
    assert selected_choice_value(dropdown) == "PRP"


@needs_display
def test_choice_dropdown_falls_back_to_default_value():
    from gui.choice_dropdown import new_choice_dropdown, selected_choice_value

    dropdown = new_choice_dropdown((("a", "A"), ("b", "B")), "missing", fallback="b")
    assert selected_choice_value(dropdown) == "b"


@needs_display
def test_dropdown_label_factory_and_string_list_display_labels():
    from gui.choice_dropdown import new_choice_dropdown

    window = Gtk.Window()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    window.set_child(box)
    rows = new_choice_dropdown((("MS", "MS (Murtagh-Sargent)"), ("BFGS", "BFGS")), "MS")
    strings = Gtk.DropDown.new(Gtk.StringList.new(["alpha", "beta"]), None)
    strings.set_selected(1)
    box.append(rows)
    box.append(strings)
    window.present()
    try:
        _iterate()
        assert "MS (Murtagh-Sargent)" in _labels(rows)
        assert "beta" in _labels(strings)
    finally:
        window.destroy()


class _Job(GObject.Object):
    name = GObject.Property(type=str, default="")
    pid = GObject.Property(type=float, default=0.0)

    def __init__(self, name, pid):
        super().__init__()
        self.name = name
        self.pid = pid


@needs_display
def test_property_sorter_orders_text_and_numbers():
    from src.gtk4_compat import property_sorter

    store = Gio.ListStore.new(_Job)
    for name, pid in (("beta", 10), ("Alpha", 2), ("gamma", 33)):
        store.append(_Job(name, pid))
    by_name = Gtk.SortListModel.new(store, property_sorter("name"))
    by_pid = Gtk.SortListModel.new(store, property_sorter("pid", numeric=True))
    assert [row.name for row in by_name] == ["Alpha", "beta", "gamma"]
    assert [row.pid for row in by_pid] == [2, 10, 33]


@needs_display
def test_context_menu_presents_below_a_button():
    from gui.gtk4_context_menu import ContextMenu

    window = Gtk.Window()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    anchor = Gtk.DrawingArea()
    anchor.set_size_request(200, 100)
    button = Gtk.Button(label="Actions")
    box.append(anchor)
    box.append(button)
    window.set_child(box)
    window.present()
    try:
        _iterate()
        menu = ContextMenu(anchor)
        menu.add_item("Delete", lambda _action: None)
        menu.present_at_widget(button)
        _iterate(100)
        found, bounds = button.compute_bounds(anchor)
        assert found
        _has_target, rectangle = menu.popover.get_pointing_to()
        assert rectangle.y == int(bounds.get_y() + bounds.get_height())
        assert menu.popover.get_visible()
    finally:
        menu.popover.popdown()
        window.destroy()
