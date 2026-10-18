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
def test_column_view_single_and_multiple_selection_models():
    """Exercise real GTK4 data views and their selection models together."""
    store = Gio.ListStore.new(_Job)
    rows = [_Job("alpha", 1), _Job("beta", 2), _Job("gamma", 3)]
    for row in rows:
        store.append(row)

    single = Gtk.SingleSelection.new(store)
    single.set_autoselect(False)
    single.set_can_unselect(True)
    single_view = Gtk.ColumnView.new(single)

    multiple = Gtk.MultiSelection.new(store)
    multiple_view = Gtk.ColumnView.new(multiple)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(single_view)
    box.append(multiple_view)
    window = Gtk.Window()
    window.set_child(box)
    window.present()
    try:
        assert _wait_for(lambda: single_view.get_realized() and multiple_view.get_realized())

        single.set_selected(1)
        assert single.get_selected() == 1
        assert single.get_selected_item() is rows[1]
        single.set_selected(Gtk.INVALID_LIST_POSITION)
        assert single.get_selected_item() is None

        multiple.select_item(0, False)
        multiple.select_item(2, False)
        selected = multiple.get_selection()
        assert selected.contains(0)
        assert not selected.contains(1)
        assert selected.contains(2)
        multiple.unselect_item(0)
        assert not multiple.get_selection().contains(0)
        assert multiple.get_selection().contains(2)
    finally:
        window.destroy()


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


@needs_display
def test_event_controllers_dispatch_mouse_and_keyboard_input():
    """Keep GTK4 gesture and key signal payloads covered on each native cell."""
    window = Gtk.Window()
    target = Gtk.DrawingArea()
    window.set_child(target)

    pointer_events = []
    click = Gtk.GestureClick()
    click.set_button(0)
    click.connect("pressed", lambda _gesture, count, x, y: pointer_events.append(
        ("pressed", count, x, y)
    ))
    click.connect("released", lambda _gesture, count, x, y: pointer_events.append(
        ("released", count, x, y)
    ))
    target.add_controller(click)

    key_events = []
    keys = Gtk.EventControllerKey()
    keys.connect("key-pressed", lambda _controller, keyval, keycode, state: (
        key_events.append(("pressed", keyval, keycode, state)) or True
    ))
    keys.connect("key-released", lambda _controller, keyval, keycode, state: key_events.append(
        ("released", keyval, keycode, state)
    ))
    target.add_controller(keys)

    window.present()
    try:
        assert _wait_for(target.get_realized)
        click.emit("pressed", 1, 12.0, 13.0)
        click.emit("released", 1, 14.0, 15.0)
        shift = Gdk.ModifierType.SHIFT_MASK
        assert keys.emit("key-pressed", Gdk.KEY_Escape, 9, shift) is True
        keys.emit("key-released", Gdk.KEY_Escape, 9, shift)

        assert pointer_events == [
            ("pressed", 1, 12.0, 13.0), ("released", 1, 14.0, 15.0)
        ]
        assert key_events == [
            ("pressed", Gdk.KEY_Escape, 9, shift),
            ("released", Gdk.KEY_Escape, 9, shift),
        ]
    finally:
        window.destroy()


def test_xtb_worker_callbacks_skip_closed_window_widgets():
    from gui.windows.setup.xtb_fragment_charges_window import XtbFragmentChargesWindow

    dialog = object.__new__(XtbFragmentChargesWindow)
    dialog._ui_generation = 2
    dialog.window = None
    dialog._running = True

    class DestroyedWidget:
        def __getattr__(self, name):
            raise AssertionError("stale callback accessed destroyed widget: " + name)

    dialog.progress = DestroyedWidget()
    dialog.btn_build = DestroyedWidget()
    dialog.btn_run = DestroyedWidget()
    dialog.btn_apply = DestroyedWidget()

    assert dialog._update_progress(1, 0.5, "late progress") is False
    result = {"converged": True, "cycles": 2, "max_dq": 0.001}
    assert dialog._run_done(1, result, None) is False
    assert dialog._running is False
    assert dialog.result is result


def test_stale_xtb_close_request_cannot_clear_reopened_window():
    from gui.windows.setup.xtb_fragment_charges_window import XtbFragmentChargesWindow

    dialog = object.__new__(XtbFragmentChargesWindow)
    old_window = object()
    current_window = object()
    dialog.window = current_window
    dialog._ui_generation = 4

    dialog._on_destroy(old_window, 2)

    assert dialog.window is current_window
    assert dialog._ui_generation == 4


def test_stale_xtb_completion_restores_reopened_window_controls():
    from gui.windows.setup.xtb_fragment_charges_window import XtbFragmentChargesWindow

    class Button:
        def __init__(self):
            self.sensitive = None

        def set_sensitive(self, value):
            self.sensitive = value

    dialog = object.__new__(XtbFragmentChargesWindow)
    dialog._ui_generation = 5
    dialog.window = object()
    dialog._running = True
    dialog.result = None
    dialog.btn_build = Button()
    dialog.btn_import_sel = Button()
    dialog.btn_run = Button()
    dialog.btn_apply = Button()

    result = {"converged": True}
    assert dialog._run_done(3, result, None) is False
    assert dialog._running is False
    assert dialog.result is result
    assert dialog.btn_build.sensitive is True
    assert dialog.btn_import_sel.sensitive is True
    assert dialog.btn_run.sensitive is True
    assert dialog.btn_apply.sensitive is True


def test_trajectory_playback_uses_removable_glib_timer(monkeypatch):
    from types import SimpleNamespace
    from gui.widgets.custom_widgets import trajectory_frame

    scheduled = []
    removed = []
    monkeypatch.setattr(
        trajectory_frame.GLib, "timeout_add",
        lambda interval, callback: scheduled.append((interval, callback)) or 41,
    )
    monkeypatch.setattr(trajectory_frame.GLib, "source_remove", removed.append)
    calls = []
    frame = SimpleNamespace(
        running=False, _playback_source_id=None, frame_forward=True, upper=5,
        entry=SimpleNamespace(get_value=lambda: 25),
        entry_step=SimpleNamespace(get_value=lambda: 1),
        forward=lambda step: calls.append(("forward", step)) or 4,
        reverse=lambda step: calls.append(("reverse", step)) or 0,
    )
    frame._playback_tick = lambda: trajectory_frame.VismolTrajectoryFrame._playback_tick(frame)

    assert trajectory_frame.VismolTrajectoryFrame.play(frame, None) is False
    assert frame.running is True
    assert scheduled[0][0] == 40
    assert scheduled[0][1]() == trajectory_frame.GLib.SOURCE_CONTINUE
    assert calls == [("forward", 1)]
    assert frame.frame_forward is False

    trajectory_frame.VismolTrajectoryFrame.stop(frame, None)
    assert removed == [41]
    assert frame.running is False
    assert frame._playback_source_id is None


def test_normal_mode_playback_wraps_on_main_loop_and_stops(monkeypatch):
    from types import SimpleNamespace
    from gui.windows.analysis import normal_modes_analysis_window as nm

    scheduled = []
    removed = []
    monkeypatch.setattr(
        nm.GLib, "timeout_add",
        lambda interval, callback: scheduled.append((interval, callback)) or 73,
    )
    monkeypatch.setattr(nm.GLib, "source_remove", removed.append)
    frames = []
    player = SimpleNamespace(
        running=False, _playback_source_id=None, lower=2, upper=4,
        spin_button=SimpleNamespace(get_value=lambda: 20),
        vm_session=SimpleNamespace(set_frame=frames.append),
    )
    player._playback_tick = lambda: nm.NormalModesAnalysisWindow._playback_tick(player)

    assert nm.NormalModesAnalysisWindow.play(player, None) is False
    assert scheduled[0][0] == 50
    assert scheduled[0][1]() == nm.GLib.SOURCE_CONTINUE
    assert scheduled[0][1]() == nm.GLib.SOURCE_CONTINUE
    assert frames == [2, 3]
    assert player.value == 2

    nm.NormalModesAnalysisWindow.stop(player, None)
    assert removed == [73]
    assert player.running is False
    assert player._playback_source_id is None


def test_scroll_delta_conversion_preserves_smooth_steps_and_wheel_sign():
    from src.gtk4_compat import scroll_delta_to_steps

    steps, remainder = scroll_delta_to_steps(12, surface=True)
    assert steps == 0
    assert remainder == pytest.approx(-0.4)

    steps, remainder = scroll_delta_to_steps(19, surface=True, remainder=remainder)
    assert steps == -1
    assert remainder == pytest.approx(-1.0 / 30.0)

    steps, remainder = scroll_delta_to_steps(-2.5, surface=False, remainder=remainder)
    assert steps == -2
    assert remainder == pytest.approx(-0.5 - 1.0 / 30.0)

    steps, remainder = scroll_delta_to_steps(0.25, surface=False, remainder=0.0)
    assert steps == 0
    assert remainder == pytest.approx(0.25)
    steps, remainder = scroll_delta_to_steps(0.8, surface=False, remainder=remainder)
    assert steps == 1
    assert remainder == pytest.approx(0.05)

    steps, remainder = scroll_delta_to_steps(float("nan"), surface=True, remainder=0.25)
    assert steps == 0
    assert remainder == 0.25


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


# --------------------------------------------------------------------------- #
#  File, folder and colour choosers (gui.file_dialogs).                        #
# --------------------------------------------------------------------------- #

def test_deprecated_choosers_only_in_the_portable_adapter():
    """Gtk.FileChooserDialog/ColorChooserDialog live only in gui.file_dialogs,
    which uses them solely on GTK 4.8 (no Gtk.FileDialog/ColorDialog there)."""
    forbidden = {
        r"Gtk\.(FileChooser(Dialog|Native|Widget)?|ColorChooser(Dialog|Widget)?)\b":
            "deprecated since GTK 4.10 (use gui.file_dialogs)",
        r"\.set_do_overwrite_confirmation\(": "absent from every GTK4 release",
        r"\bchoose_path\(": "removed (use gui.file_dialogs.choose_file)",
        r"Gtk\.ColorButton\b": "deprecated since GTK 4.10 (use gui.color_button.ColorButton)",
        r"(?<!\bplt)\.(show|hide)\(\)": "deprecated since GTK 4.10 (use set_visible)",
        r"\.get_allocated_(width|height|baseline)\(": "deprecated since GTK 4.12 (use get_width/get_height)",
        r"\.set_from_pixbuf\(|\.set_pixbuf\(|\.new_from_pixbuf\(|\.new_for_pixbuf\(":
            "deprecated since GTK 4.12/4.20 (use gtk4_compat.texture_from_pixbuf)",
        r"Gtk\.Statusbar\b": "deprecated since GTK 4.10 (use gui.status_label.StatusLabel)",
        r"\.get_style_context\(": "deprecated since GTK 4.10",
        r"(list|tuple)\([^()]*get_rgba\(\)\)|\blist\(color\)": "Gdk.RGBA is iterable only from PyGObject 3.58 (use gtk4_compat.rgba_components)",
    }
    adapter = SRC / "gui" / "file_dialogs.py"
    compat = SRC / "gtk4_compat.py"
    offenders = []
    for path in SRC.rglob("*.py"):
        if path in (adapter, compat):
            continue
        for number, code in _code_lines(path):
            code = code.replace(" . ", ".").replace(" ( ", "(").replace(" (", "(")
            for pattern, why in forbidden.items():
                if re.search(pattern, code):
                    offenders.append("%s:%d %s" % (path.relative_to(PROJECT_ROOT), number, why))
    for path in list(SRC.rglob("*.glade")) + list(SRC.rglob("*.ui")):
        if re.search(r'class="Gtk(FileChooser|ColorChooser|ColorButton|Statusbar)\w*"', path.read_text(encoding="utf-8")):
            offenders.append("%s GtkFileChooser/GtkColorChooser/GtkColorButton" % path.relative_to(PROJECT_ROOT))
    for path in SRC.rglob("*.py"):
        if 'class="GtkColorButton"' in path.read_text(encoding="utf-8"):
            offenders.append("%s inline GtkColorButton UI" % path.relative_to(PROJECT_ROOT))
    assert not offenders, "\n".join(offenders)


def test_split_initial_path_selects_folder_and_save_name(tmp_path):
    from gui import file_dialogs as fd

    target = tmp_path / "result.png"
    assert fd.split_initial_path(None, fd.SAVE) == (None, None)
    assert fd.split_initial_path(str(tmp_path), fd.OPEN) == (str(tmp_path), None)
    assert fd.split_initial_path(str(target), fd.SAVE) == (str(tmp_path), "result.png")
    assert fd.split_initial_path(str(target), fd.OPEN) == (str(tmp_path), None)
    missing = tmp_path / "missing" / "x.txt"
    assert fd.split_initial_path(str(missing), fd.SAVE) == (None, "x.txt")
    with pytest.raises(ValueError):
        fd.choose_file(None, lambda _result: None, mode="bogus")


def test_native_glib_log_handler_only_below_gtk_4_10():
    from src.os_integration import gtk_startup

    class FakeFunction:
        def __init__(self, result=1):
            self.calls = []
            self.result = result

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    class FakeGLib:
        def __init__(self):
            self.g_log_set_handler = FakeFunction()
            # Any C function pointer works for the cast; use a real one.
            import ctypes
            self.g_log_default_handler = ctypes.CFUNCTYPE(None)(lambda: None)

    for version, expected in (((4, 8), True), ((4, 9), True), ((4, 10), False), ((4, 24), False), (None, False)):
        assert gtk_startup.needs_native_glib_log_handler(version) is expected
        glib = FakeGLib()
        installed = gtk_startup.install_native_glib_log_handler(runtime_version=version or (99, 0), glib_library=glib) \
            if version is not None else False
        assert installed is expected
        calls = glib.g_log_set_handler.calls
        assert len(calls) == (1 if expected else 0)
        if expected:
            assert calls[0][0] == b"GLib-GObject"
            assert calls[0][1] & 0b11011 == 0b11011  # recursion, fatal, critical, warning


@needs_display
def test_widget_cycles_freed_by_garbage_collection_do_not_abort(tmp_path):
    """Regression for GTK 4.8: GtkImage finalization criticals freed from a
    garbage-collected cycle inside PyGObject's warning handler were a
    recursive (always fatal) GLib log message."""
    import subprocess
    from src.os_integration.gtk_startup import needs_native_glib_log_handler

    if not needs_native_glib_log_handler((Gtk.get_major_version(), Gtk.get_minor_version())):
        pytest.skip("GTK %d.%d has no GtkImage finalization critical (fixed in 4.10)"
                    % (Gtk.get_major_version(), Gtk.get_minor_version()))

    script = tmp_path / "cycles.py"
    script.write_text(
        "import sys\n"
        "sys.path[:0] = [%r, %r]\n"
        "from src.os_integration.gtk_startup import configure_startup_environment\n"
        "configure_startup_environment(%r)\n"
        "import gc, gi\n"
        "gi.require_version('Gtk', '4.0')\n"
        "from gi.repository import GLib, Gtk\n"
        "from gui import file_dialogs as fd\n"
        "window = Gtk.Window(); window.present()\n"
        "context = GLib.MainContext.default()\n"
        "def spin(n):\n"
        "    for _ in range(n):\n"
        "        context.iteration(False)\n"
        "class Holder: pass\n"
        "for index in range(6):\n"
        "    holder = Holder()\n"
        "    holder.dialog = Gtk.FileChooserDialog(title='cycle', action=fd.Gtk.FileChooserAction.OPEN)\n"
        "    holder.dialog.set_transient_for(window)\n"
        "    holder.dialog.connect('response', lambda d, r, h=holder: d.destroy())\n"
        "    holder.dialog.present(); spin(200)\n"
        "    holder.dialog.response(Gtk.ResponseType.CANCEL); spin(200)\n"
        "    del holder\n"
        "    spin(50)\n"
        "gc.collect(); spin(50)\n"
        "print('cycles-ok')\n" % (str(PROJECT_ROOT), str(SRC), str(PROJECT_ROOT))
    )
    environ = dict(os.environ)
    environ.pop("G_DEBUG", None)
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            timeout=180, env=environ)
    assert result.returncode == 0 and "cycles-ok" in result.stdout, (
        result.returncode, result.stdout[-2000:], result.stderr[-2000:])


def _file_modes():
    from gui import file_dialogs as fd
    return (fd.OPEN, fd.OPEN_MULTIPLE, fd.SAVE, fd.SELECT_FOLDER, fd.SELECT_MULTIPLE_FOLDERS)


def _chooser_paths(use_new_api):
    """Run each real file chooser where the app uses it.

    Windows uses Gtk.FileChooserDialog on all GTK4 minors to avoid the native
    COM dialog cancellation failure. Other platforms use Gtk.FileDialog when
    available and the GTK 4.8 fallback below that.
    """
    from gui import file_dialogs as fd
    version = "GTK %d.%d" % (Gtk.get_major_version(), Gtk.get_minor_version())
    if sys.platform == "win32":
        if use_new_api:
            pytest.skip("Windows uses the GTK chooser widget to avoid GTK COM cancellation failure")
        return
    if use_new_api and not fd.has_file_dialog():
        pytest.skip("Gtk.FileDialog needs GTK 4.10+; %s uses the GTK 4.8 chooser (tested)" % version)
    if not use_new_api and fd.has_file_dialog():
        pytest.skip("%s: the app uses Gtk.FileDialog (tested); the GTK 4.8 chooser runs "
                    "only where Gtk.FileDialog is absent" % version)


def _dismiss(handle):
    """Cancel through the chooser handle used by the application."""
    handle.cancel()


@needs_display
@pytest.mark.parametrize("use_new_api", [False, True], ids=["gtk48-path", "file-dialog"])
def test_file_chooser_cancel_reports_nothing_once(tmp_path, use_new_api):
    from gui import file_dialogs as fd

    _chooser_paths(use_new_api)
    window = Gtk.Window(title="parent")
    window.present()
    try:
        for mode in _file_modes():
            results = []
            handle = fd.choose_file(
                window, results.append, mode=mode, title="Pick %s" % mode,
                initial_path=str(tmp_path / "out.txt"),
                filters=[fd.file_filter("Text (*.txt)", "*.txt")],
                use_file_dialog=use_new_api,
            )
            assert handle.uses_new_api is use_new_api
            _iterate(100)
            _dismiss(handle)
            assert _wait_for(lambda: results), mode
            _iterate(50)
            handle.cancel()  # a second cancel is ignored
            expected = [] if mode in fd.MULTIPLE_MODES else None
            assert results == [expected], (mode, results)
            assert handle.dialog is None
    finally:
        window.destroy()


@needs_display
def test_file_dialog_is_configured_like_the_request(tmp_path):
    from gui import file_dialogs as fd

    if not fd.has_file_dialog():
        pytest.skip("Gtk.FileDialog needs GTK 4.10+")
    pngs = fd.file_filter("PNG image (*.png)", "*.png")
    results = []
    gtk_api = Gtk
    if sys.platform == "win32":
        class RecordingFileDialog:
            def __init__(self, *, title, modal):
                self.title = title
                self.modal = modal
                self.filters = None
                self.default_filter = None
                self.call = None

            def set_accept_label(self, value):
                self.accept_label = value

            def set_initial_folder(self, value):
                self.initial_folder = value

            def set_initial_name(self, value):
                self.initial_name = value

            def set_filters(self, value):
                self.filters = value

            def set_default_filter(self, value):
                self.default_filter = value

            def save(self, window, cancellable, callback):
                self.call = (window, cancellable, callback)

        class GtkApi:
            FileDialog = RecordingFileDialog
            FileFilter = Gtk.FileFilter

        gtk_api = GtkApi
    handle = fd.choose_file(None, results.append, mode=fd.SAVE, title="Export PNG",
                            initial_path=str(tmp_path / "plot.png"), filters=[pngs],
                            use_file_dialog=True, gtk=gtk_api)
    dialog = handle.dialog
    if sys.platform == "win32":
        assert dialog.title == "Export PNG"
        assert dialog.accept_label == "Save"
        assert dialog.modal
        assert dialog.initial_name == "plot.png"
        assert os.path.samefile(dialog.initial_folder.get_path(), str(tmp_path))
        assert dialog.filters.get_n_items() == 1
        assert dialog.default_filter is pngs
        assert dialog.call is not None
    else:
        try:
            assert dialog.get_title() == "Export PNG"
            assert dialog.get_accept_label() == "Save"
            assert dialog.get_modal()
            assert dialog.get_initial_name() == "plot.png"
            assert os.path.samefile(dialog.get_initial_folder().get_path(), str(tmp_path))
            assert dialog.get_filters().get_n_items() == 1
            assert dialog.get_default_filter() is pngs
        finally:
            _dismiss(handle)
        assert _wait_for(lambda: results == [None]), results


def test_windows_file_dialog_mode_mapping_avoids_native_dialog_launches(monkeypatch, tmp_path):
    from gui import file_dialogs as fd

    monkeypatch.setattr(sys, "platform", "win32")

    class RecordingFileDialog:
        def __init__(self, **_kwargs):
            self.filters = None
            self.operation = None

        def set_accept_label(self, _value):
            pass

        def set_initial_folder(self, _value):
            pass

        def set_initial_name(self, _value):
            pass

        def set_filters(self, _value):
            pass

        def set_default_filter(self, _value):
            pass

        def __getattr__(self, name):
            if name.endswith("_finish"):
                def finish(_result):
                    raise GLib.Error.new_literal(
                        Gio.io_error_quark(), "cancelled", Gio.IOErrorEnum.CANCELLED
                    )
                return finish

            def start(window, cancellable, callback):
                self.operation = (name, window, cancellable, callback)
            return start

    class GtkApi:
        FileDialog = RecordingFileDialog
        FileFilter = Gtk.FileFilter

    expected = {
        fd.OPEN: "open",
        fd.OPEN_MULTIPLE: "open_multiple",
        fd.SAVE: "save",
        fd.SELECT_FOLDER: "select_folder",
        fd.SELECT_MULTIPLE_FOLDERS: "select_multiple_folders",
    }
    file_filter = fd.file_filter("Data", "*.dat")
    for mode, method in expected.items():
        results = []
        handle = fd.choose_file(None, results.append, mode=mode,
                                initial_path=str(tmp_path / "item.dat"),
                                filters=[file_filter], use_file_dialog=True, gtk=GtkApi)
        assert handle.uses_new_api
        assert handle.dialog is not None
        name, _window, _cancellable, callback = handle.dialog.operation
        assert name == method
        callback(handle.dialog, object())
        assert results == ([[]] if mode in fd.MULTIPLE_MODES else [None])
        assert handle.dialog is None


@needs_display
@pytest.mark.parametrize("mode_name", ["OPEN", "OPEN_MULTIPLE", "SAVE", "SELECT_FOLDER"])
def test_gtk48_file_chooser_path_returns_selected_paths(tmp_path, mode_name):
    """The GTK 4.8 chooser returns the real local paths the user selected."""
    from gui import file_dialogs as fd

    _chooser_paths(False)
    mode = getattr(fd, mode_name)
    (tmp_path / "data.txt").write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    results = []
    handle = fd.choose_file(None, results.append, mode=mode, initial_path=str(tmp_path) + os.sep,
                            use_file_dialog=False)
    dialog = handle.dialog
    assert isinstance(dialog, Gtk.FileChooserDialog)
    assert dialog.get_select_multiple() is (mode in fd.MULTIPLE_MODES)

    def same(path, target):
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(str(target)))

    try:
        assert _wait_for(dialog.get_mapped)
        assert _wait_for(lambda: dialog.get_current_folder() is not None
                         and same(dialog.get_current_folder().get_path(), tmp_path))
        if mode == fd.SAVE:
            dialog.set_current_name("saved.txt")
            expected = tmp_path / "saved.txt"
        else:
            expected = tmp_path / ("sub" if mode == fd.SELECT_FOLDER else "data.txt")

        last_attempt = [None]

        def selected():
            # The folder loads asynchronously and GTK may then move the
            # cursor to its first row, replacing a selection made earlier.
            # Select again (at most once a second, so each attempt can
            # finish) until the choice holds.
            current = dialog.get_file()
            if current is not None and same(current.get_path(), expected):
                return True
            now = GLib.get_monotonic_time()
            if mode != fd.SAVE and (last_attempt[0] is None or now - last_attempt[0] > 1_000_000):
                last_attempt[0] = now
                dialog.set_file(Gio.File.new_for_path(str(expected)))
            return False

        assert _wait_for(selected)
        # Accept at once: the adapter hides the chooser and destroys it
        # later, so a folder lookup still running cannot crash GTK.
        dialog.response(Gtk.ResponseType.ACCEPT)
        assert _wait_for(lambda: results), results
        assert not dialog.get_visible()
    finally:
        if handle.dialog is not None:
            handle.dialog.destroy()
    selected = results[0] if mode not in fd.MULTIPLE_MODES else results[0][0]
    assert same(selected, expected), (selected, str(expected))
    if mode in fd.MULTIPLE_MODES:
        assert isinstance(results[0], list) and len(results[0]) == 1


@needs_display
@pytest.mark.parametrize("use_new_api", [False, True], ids=["gtk48-path", "color-dialog"])
def test_color_chooser_cancel_reports_none_once(use_new_api):
    from gui import file_dialogs as fd

    if use_new_api and sys.platform == "win32":
        pytest.skip("Windows uses the GTK color chooser widget to avoid native dialog cancellation failure")
    if use_new_api and not fd.has_color_dialog():
        pytest.skip("Gtk.ColorDialog needs GTK 4.10+; GTK %d.%d uses the tested fallback"
                    % (Gtk.get_major_version(), Gtk.get_minor_version()))
    window = Gtk.Window(title="parent")
    window.present()
    try:
        initial = Gdk.RGBA()
        assert initial.parse("rgb(10,200,30)")
        results = []
        handle = fd.choose_color(window, results.append, title="Colour", initial=initial,
                                 use_color_dialog=use_new_api)
        assert handle.uses_new_api is use_new_api
        if use_new_api:
            assert handle.dialog.get_title() == "Colour" and handle.dialog.get_modal()
        _iterate(100)
        handle.cancel()
        assert _wait_for(lambda: results), results
        _iterate(50)
        assert results == [None]
    finally:
        window.destroy()


@needs_display
def test_gtk48_color_chooser_path_returns_the_chosen_rgba():
    from gui import file_dialogs as fd

    initial = Gdk.RGBA()
    assert initial.parse("rgb(255,0,0)")
    results = []
    handle = fd.choose_color(None, results.append, initial=initial, use_color_dialog=False)
    dialog = handle.dialog
    assert _wait_for(dialog.get_mapped)
    assert dialog.get_rgba().equal(initial)
    chosen = Gdk.RGBA()
    assert chosen.parse("rgb(0,0,255)")
    dialog.set_rgba(chosen)
    dialog.response(Gtk.ResponseType.OK)
    assert _wait_for(lambda: results), results
    assert results[0] is not None and results[0].equal(chosen)


def test_gtk_chooser_schemas_installed_when_required():
    """GTK's choosers abort without their compiled schemas; CI cells must
    provide them so the real dialogs are exercised (not silently refused)."""
    from gui import file_dialogs as fd

    if os.environ.get("EASYHYBRID_REQUIRE_GTK_DISPLAY") != "1":
        pytest.skip("only enforced in cells that require the real GTK runtime")
    for schema in (fd.FILE_CHOOSER_SCHEMA, fd.COLOR_CHOOSER_SCHEMA):
        assert fd.gsettings_schema_installed(schema), (
            "%s missing: run glib-compile-schemas on this GTK's schema directory" % schema)


def _message_windows():
    return [window for window in Gtk.Window.list_toplevels()
            if window.has_css_class("easyhybrid-message-dialog") and window.get_visible()]


@needs_display
@pytest.mark.parametrize("use_new_api", [False, True], ids=["gtk48-path", "new-api"])
def test_missing_schema_shows_an_error_instead_of_aborting(monkeypatch, use_new_api):
    from gui import file_dialogs as fd

    monkeypatch.setattr(fd, "gsettings_schema_installed", lambda _schema: False)
    monkeypatch.setattr(fd.sys, "platform", "linux")  # where Gtk.FileDialog may use the GTK widget
    for message in _message_windows():
        message.destroy()
    try:
        files, colours = [], []
        handle = fd.choose_file(None, files.append, mode=fd.OPEN_MULTIPLE, use_file_dialog=use_new_api)
        assert files == [[]] and handle.dialog is None and handle.done
        handle.cancel()
        assert files == [[]]
        fd.choose_color(None, colours.append, use_color_dialog=use_new_api)
        assert colours == [None]
        assert _wait_for(lambda: len(_message_windows()) == 2)
        assert all(window.dialog_kind == "error" for window in _message_windows())
    finally:
        for message in _message_windows():
            message.destroy()


# --------------------------------------------------------------------------- #
#  Colour buttons (gui.color_button).                                          #
# --------------------------------------------------------------------------- #

COLOR_BUTTON_UI_FILES = [
    ("gui/windows/setup/merge_system.glade", ["button_color"]),
    ("gui/windows/setup/import_system_window_new.glade", ["button_color"]),
    ("gui/windows/setup/import_system_window.glade", ["button_color"]),
    ("gui/windows/setup/windows_and_dialogs.glade", ["button_color"]),
    ("gui/windows/setup/add_position_restraint_dialog.glade", ["colorbutton_position"]),
    ("gui/windows/analysis/surface_analysis_window.glade", ["btn_color_plus", "btn_color_minus"]),
    ("gui/windows/setup/setup_interface.glade", [
        "btn_background_color", "btn_seqviewer_bg_color", "btn_seqviewer_label_color",
        "color_btn_view_sel_dots", "color_btn_pk_label", "color_btn_pk_sphr_1",
        "color_btn_pk_sphr_2", "color_btn_pk_sphr_3", "color_btn_pk_sphr_4",
        "color_btn_pk_dist_label", "color_btn_pk_dist_lines", "btn_stick_unique_color",
        "btn_dbond_unique_color", "btn_light_color", "btn_light_spec_color"]),
]


@needs_display
@pytest.mark.parametrize("ui_file,object_ids", COLOR_BUTTON_UI_FILES,
                         ids=[Path(ui).stem for ui, _ids in COLOR_BUTTON_UI_FILES])
def test_builder_color_buttons_are_portable_with_their_colours(ui_file, object_ids):
    from gui.color_button import ColorButton
    from gui.gtk4_builder import load_builder_file

    builder = Gtk.Builder()
    load_builder_file(builder, str(SRC / ui_file))
    text = (SRC / ui_file).read_text(encoding="utf-8")
    for object_id in object_ids:
        button = builder.get_object(object_id)
        assert isinstance(button, ColorButton), object_id
        declared = re.search(r'id="%s">(.*?)</object>' % object_id, text, re.S).group(1)
        match = re.search(r'<property name="rgba">([^<]+)<', declared)
        if match:
            expected = Gdk.RGBA()
            assert expected.parse(match.group(1))
            assert button.get_rgba().equal(expected), (object_id, button.get_rgba().to_string())
    for toplevel in [builder.get_object(name) for name in ("dialog", "window", "dialog_prune")]:
        if isinstance(toplevel, Gtk.Window):
            toplevel.destroy()


@needs_display
def test_preferences_inline_ui_uses_the_portable_color_button():
    from gui.color_button import ColorButton

    ui = re.search(r'<object class="EasyHybridColorButton" id="button_color">.*?</object>',
                   (SRC / "gui" / "main" / "preferences_window.py").read_text(encoding="utf-8"),
                   re.S).group(0)
    builder = Gtk.Builder()
    builder.add_from_string("<interface>%s</interface>" % ui)
    button = builder.get_object("button_color")
    assert isinstance(button, ColorButton)
    assert button.get_rgba().to_string() == "rgb(138,226,52)"


def test_color_button_keeps_the_gtk_color_button_api():
    from gui.color_button import ColorButton

    builder = Gtk.Builder()
    builder.add_from_string(
        '<interface><object class="EasyHybridColorButton" id="b">'
        '<property name="use-alpha">False</property>'
        '<property name="title">Pick the dots color</property>'
        '<property name="rgba">#000000000000</property></object></interface>')
    button = builder.get_object("b")
    assert button.get_property("use-alpha") is False
    assert button.get_property("title") == "Pick the dots color"
    from src.gtk4_compat import rgba_components
    assert rgba_components(button.get_rgba()) == [0.0, 0.0, 0.0, 1.0]

    colour = Gdk.RGBA()
    assert colour.parse("rgba(10,20,30,0.5)")
    default = ColorButton()
    assert default.get_rgba().to_string() == "rgb(191,64,64)"  # Gtk.ColorButton's default
    changes = []
    default.connect("notify::rgba", lambda *_args: changes.append("notify"))
    default.connect("color-set", lambda *_args: changes.append("color-set"))
    default.set_rgba(colour)
    assert default.get_rgba().equal(colour)
    returned = default.get_rgba()
    returned.red = 1.0  # a copy; the button keeps its colour
    assert default.get_rgba().equal(colour)
    assert changes == ["notify"]  # set_rgba never emits color-set
    assert ColorButton.new_with_rgba(colour).get_rgba().equal(colour)


@needs_display
@pytest.mark.parametrize("use_new_api", [False, True], ids=["gtk48-path", "color-dialog"])
def test_color_button_click_cancel_keeps_colour_and_emits_nothing(monkeypatch, use_new_api):
    from gui import color_button, file_dialogs as fd

    if use_new_api and not fd.has_color_dialog():
        pytest.skip("Gtk.ColorDialog needs GTK 4.10+; GTK %d.%d uses the tested fallback"
                    % (Gtk.get_major_version(), Gtk.get_minor_version()))
    real_choose = fd.choose_color
    monkeypatch.setattr(color_button.file_dialogs, "choose_color",
                        lambda *args, **kw: real_choose(*args, use_color_dialog=use_new_api, **kw))
    window = Gtk.Window(title="colours")
    button = color_button.ColorButton()
    window.set_child(button)
    window.present()
    try:
        before = button.get_rgba()
        emitted = []
        button.connect("color-set", lambda *_args: emitted.append(True))
        button.emit("clicked")
        handle = button.chooser
        assert handle is not None and handle.uses_new_api is use_new_api
        if use_new_api:
            assert handle.dialog.get_with_alpha() is False
        _iterate(100)
        handle.cancel()
        assert _wait_for(lambda: button.chooser is None)
        _iterate(50)
        assert emitted == [] and button.get_rgba().equal(before)
    finally:
        window.destroy()


@needs_display
def test_color_button_pick_sets_opaque_colour_and_emits_color_set(monkeypatch):
    """The GTK 4.8 chooser path, on every minor: a picked colour becomes the
    button's colour (alpha dropped as use-alpha is off) and color-set fires once."""
    from gui import color_button, file_dialogs as fd

    real_choose = fd.choose_color
    monkeypatch.setattr(color_button.file_dialogs, "choose_color",
                        lambda *args, **kw: real_choose(*args, use_color_dialog=False, **kw))
    button = color_button.ColorButton(title="Pick")
    window = Gtk.Window()
    window.set_child(button)
    window.present()
    try:
        emitted = []
        button.connect("color-set", lambda widget: emitted.append(widget.get_rgba().to_string()))
        button.emit("clicked")
        dialog = button.chooser.dialog
        assert dialog.get_title() == "Pick"
        assert _wait_for(dialog.get_mapped)
        picked = Gdk.RGBA()
        assert picked.parse("rgba(0,0,255,0.25)")
        dialog.set_rgba(picked)
        dialog.response(Gtk.ResponseType.OK)
        assert _wait_for(lambda: emitted), emitted
        _iterate(50)
        assert emitted == ["rgb(0,0,255)"]
        assert button.get_rgba().to_string() == "rgb(0,0,255)"
    finally:
        window.destroy()


# --------------------------------------------------------------------------- #
#  Deprecation sweep: textures and status line.                                #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("has_alpha", [True, False], ids=["rgba", "rgb"])
def test_texture_from_pixbuf_keeps_size_and_pixels(has_alpha):
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    from src.gtk4_compat import texture_from_pixbuf

    assert texture_from_pixbuf(None) is None
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, has_alpha, 8, 5, 3)
    pixbuf.fill(0x204060FF)  # opaque rgb(32,64,96)
    texture = texture_from_pixbuf(pixbuf)
    assert isinstance(texture, Gdk.Texture)
    assert (texture.get_width(), texture.get_height()) == (5, 3)
    # Round-trip through GTK's own PNG encoder (GTK 4.6+) to read pixels.
    loader = GdkPixbuf.PixbufLoader.new_with_type("png")
    loader.write_bytes(texture.save_to_png_bytes())
    loader.close()
    decoded = loader.get_pixbuf()
    assert (decoded.get_width(), decoded.get_height()) == (5, 3)
    pixels = decoded.get_pixels()
    channels = decoded.get_n_channels()
    last = decoded.get_rowstride() * 2 + 4 * channels  # bottom-right pixel
    assert tuple(pixels[0:3]) == (32, 64, 96) and tuple(pixels[last:last + 3]) == (32, 64, 96)
    if channels == 4:
        assert pixels[3] == 255


@needs_display
def test_texture_is_shown_by_image_and_picture():
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    from src.gtk4_compat import texture_from_pixbuf

    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 10, 10)
    pixbuf.fill(0xFF0000FF)
    image, picture = Gtk.Image(), Gtk.Picture()
    image.set_from_paintable(texture_from_pixbuf(pixbuf))
    picture.set_paintable(texture_from_pixbuf(pixbuf))
    assert image.get_paintable().get_intrinsic_width() == 10
    assert picture.get_paintable().get_intrinsic_height() == 10
    image.set_from_paintable(texture_from_pixbuf(None))
    assert image.get_paintable() is None


def test_status_label_keeps_a_statusbar_message_stack():
    from gui.status_label import StatusLabel

    status = StatusLabel()
    assert status.get_text() == ""
    first = status.push(1, "Welcome")
    second = status.push(2, "Loading")
    assert second > first and status.get_text() == "Loading"
    status.push(1, "system: 12 atoms")
    assert status.get_text() == "system: 12 atoms"
    status.pop(1)
    assert status.get_text() == "Loading"
    status.remove_all(2)
    assert status.get_text() == "Welcome"
    status.pop(1)
    assert status.get_text() == ""


@needs_display
def test_main_window_status_line_is_portable():
    from gui.gtk4_builder import load_builder_file
    from gui.status_label import StatusLabel

    builder = Gtk.Builder()
    load_builder_file(builder, str(SRC / "gui" / "MainWindow.glade"))
    status = builder.get_object("statusbar1")
    assert isinstance(status, StatusLabel)
    status.push(1, "Welcome to EasyHybrid")
    assert status.get_text() == "Welcome to EasyHybrid"
    for name in ("window1", "main_window", "MainWindow"):
        window = builder.get_object(name)
        if isinstance(window, Gtk.Window):
            window.destroy()
