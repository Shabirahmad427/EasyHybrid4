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


def _wait_for(predicate, timeout=10.0):
    """Run the GTK main loop until ``predicate()`` is true or ``timeout`` expires.

    Fixed sleeps race on slow or loaded runners; waiting for the observable
    state keeps these tests deterministic on every platform.
    """
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + int(timeout * 1_000_000)
    while not predicate():
        if GLib.get_monotonic_time() > deadline:
            return predicate()
        if not context.iteration(False):
            _iterate(10)
    return True


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
        r"Gtk\.MessageDialog\b": "deprecated since GTK 4.10 (use gui.message_dialogs)",
        r"Gdk\.cairo_surface_create_from_pixbuf": "absent from every GTK4 release",
        r"Gtk\.Dialog\b": "deprecated since GTK 4.10 (use gui.response_dialog)",
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
        ui_text = path.read_text(encoding="utf-8")
        if re.search(r'class="GtkComboBox(Text)?"', ui_text):
            offenders.append("%s GtkComboBox" % path.relative_to(PROJECT_ROOT))
        if re.search(r'class="Gtk(Message)?Dialog"', ui_text):
            offenders.append("%s GtkDialog (use GtkWindow)" % path.relative_to(PROJECT_ROOT))
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
        assert _wait_for(lambda: "MS (Murtagh-Sargent)" in _labels(rows)), _labels(rows)
        assert _wait_for(lambda: "beta" in _labels(strings)), _labels(strings)
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
        assert _wait_for(lambda: button.get_height() > 0 and anchor.get_height() > 0)
        menu = ContextMenu(anchor)
        menu.add_item("Delete", lambda _action: None)
        menu.present_at_widget(button)
        assert _wait_for(menu.popover.get_visible)
        found, bounds = button.compute_bounds(anchor)
        assert found
        _has_target, rectangle = menu.popover.get_pointing_to()
        assert rectangle.y == int(bounds.get_y() + bounds.get_height())
        assert menu.popover.get_visible()
    finally:
        menu.popover.popdown()
        window.destroy()


# --------------------------------------------------------------------------- #
#  Portable message dialogs (replace deprecated Gtk.MessageDialog).            #
# --------------------------------------------------------------------------- #

def _press_escape(window):
    for controller in window.observe_controllers():
        if isinstance(controller, Gtk.EventControllerKey):
            return controller.emit("key-pressed", Gdk.KEY_Escape, 0, 0)
    raise AssertionError("dialog has no key controller")


@needs_display
def test_show_message_ok_closes_once_and_reports():
    from gui.message_dialogs import show_message

    closed = []
    dialog = show_message(None, "Run finished", "Energy: -1.0 kJ/mol", kind="error",
                          on_close=lambda: closed.append(True))
    _iterate(100)
    assert dialog.get_title() == "Error"
    assert dialog.secondary_label.get_text() == "Energy: -1.0 kJ/mol"
    dialog.buttons["OK"].emit("clicked")
    dialog.respond(True)  # a second response must be ignored
    assert closed == [True]


@needs_display
def test_ask_yes_no_reports_yes_and_escape_as_no():
    from gui.message_dialogs import ask_yes_no

    answers = []
    yes_dialog = ask_yes_no(None, "Delete?", answers.append)
    _iterate(100)
    yes_dialog.buttons["Yes"].emit("clicked")
    escape_dialog = ask_yes_no(None, "Delete?", answers.append)
    _iterate(100)
    assert _press_escape(escape_dialog) is True
    assert answers == [True, False]


@needs_display
def test_closing_a_question_window_is_a_cancel():
    from gui.message_dialogs import choose

    answers = []
    parent = Gtk.Window()
    parent.present()
    try:
        dialog = choose(parent, "Save changes?",
                        (("Don't Save", "no"), ("Cancel", "cancel"), ("Save", "yes")),
                        answers.append, cancel_response="cancel", default_response="yes")
        _iterate(100)
        assert dialog.get_transient_for() is parent
        assert dialog.get_default_widget() is dialog.buttons["Save"]
        dialog.close()
        assert _wait_for(lambda: answers == ["cancel"]), answers
    finally:
        parent.destroy()


@needs_display
def test_error_details_are_shown_in_an_expander():
    from gui.message_dialogs import show_message

    dialog = show_message(None, "Import failed", details="Traceback: boom", kind="error")
    _iterate(100)
    buffer = dialog.details_view.get_buffer()
    text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
    assert text == "Traceback: boom"
    dialog.respond(True)


# --------------------------------------------------------------------------- #
#  ResponseDialog (drop-in replacement for deprecated Gtk.Dialog).             #
# --------------------------------------------------------------------------- #

@needs_display
def test_response_dialog_buttons_emit_their_response():
    from gui.response_dialog import ResponseDialog

    responses = []
    dialog = ResponseDialog(title="Rename Residue", modal=True)
    dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "OK", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    entry = Gtk.Entry()
    dialog.get_content_area().append(entry)
    dialog.connect("response", lambda _dialog, response: responses.append(response))
    dialog.present()
    try:
        assert _wait_for(dialog.get_mapped)
        assert dialog.get_default_widget() is dialog.get_widget_for_response(Gtk.ResponseType.OK)
        assert entry.get_parent() is dialog.get_content_area()
        dialog.get_widget_for_response(Gtk.ResponseType.OK).emit("clicked")
        dialog.response(Gtk.ResponseType.CANCEL)
        assert responses == [Gtk.ResponseType.OK, Gtk.ResponseType.CANCEL]
        assert responses[0] == Gtk.ResponseType.OK  # int compares with the enum
    finally:
        dialog.destroy()


@needs_display
def test_response_dialog_close_and_escape_emit_delete_event():
    from gui.response_dialog import ResponseDialog

    responses = []
    for trigger in ("close", "escape"):
        dialog = ResponseDialog(title="Save Preset")
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.connect("response", lambda _dialog, response: responses.append(response))
        dialog.present()
        assert _wait_for(dialog.get_mapped)
        if trigger == "close":
            dialog.close()
        else:
            assert _press_escape(dialog) is True
        assert _wait_for(lambda: not dialog.get_visible())
    assert responses == [Gtk.ResponseType.DELETE_EVENT] * 2


@needs_display
def test_response_dialog_subclass_like_gtk_dialog():
    from gui.response_dialog import ResponseDialog

    class Picker(ResponseDialog):
        def __init__(self, parent):
            super().__init__(transient_for=parent)
            self.add_button("Cancel", Gtk.ResponseType.CANCEL)
            self.add_button("OK", Gtk.ResponseType.OK)
            self.set_response_sensitive(Gtk.ResponseType.OK, False)

    parent = Gtk.Window()
    parent.present()
    try:
        picker = Picker(parent)
        assert picker.get_transient_for() is parent
        assert not picker.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive()
        picker.destroy()
    finally:
        parent.destroy()


@needs_display
@pytest.mark.parametrize("ui_file, object_id", [
    ("gui/windows/setup/edit_frames_dialog.glade", "dialog"),
    ("gui/windows/setup/add_harmonic_restraint_dialog.glade", "dialog"),
    ("gui/windows/setup/add_position_restraint_dialog.glade", "dialog"),
    ("gui/windows/setup/export_script_window2.glade", "dialog"),
    ("gui/windows/setup/windows_and_dialogs.glade", "dialog_prune"),
])
def test_builder_dialogs_are_windows_with_buttons_at_the_bottom(ui_file, object_id):
    """Former GtkDialog UI files: plain GtkWindow, action buttons still last."""
    from gui.gtk4_builder import load_builder_file

    builder = Gtk.Builder()
    load_builder_file(builder, str(SRC / ui_file))
    window = builder.get_object(object_id)
    try:
        assert type(window) is Gtk.Window
        content = window.get_child()
        children = []
        child = content.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()

        def has_button(widget):
            if isinstance(widget, Gtk.Button):
                return True
            inner = widget.get_first_child()
            while inner is not None:
                if has_button(inner):
                    return True
                inner = inner.get_next_sibling()
            return False

        button_rows = [index for index, row in enumerate(children)
                       if isinstance(row, Gtk.Box) and row.get_halign() == Gtk.Align.END and has_button(row)]
        assert button_rows == [len(children) - 1]
    finally:
        window.destroy()
