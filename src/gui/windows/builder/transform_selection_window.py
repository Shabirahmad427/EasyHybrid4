"""Native GTK4 live translation and rotation controls for Builder selections."""

import math

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from gui.windows.builder.atom_ops import (
    push_undo_snapshot,
    rotate_atoms_around_point,
    selection_centroid,
    translate_atoms,
)


_AXIS_VECTORS = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
                 "z": (0.0, 0.0, 1.0)}
_SLIDERS = (
    ("tx", "Translate X (Å)", -5.0, 5.0, 0.01, 0.5, 2),
    ("ty", "Translate Y (Å)", -5.0, 5.0, 0.01, 0.5, 2),
    ("tz", "Translate Z (Å)", -5.0, 5.0, 0.01, 0.5, 2),
    ("rx", "Rotate X (°)", -180.0, 180.0, 1.0, 10.0, 0),
    ("ry", "Rotate Y (°)", -180.0, 180.0, 1.0, 10.0, 0),
    ("rz", "Rotate Z (°)", -180.0, 180.0, 1.0, 10.0, 0),
)


class TransformSelectionWindow:
    """Live selection transforms, with one undo point per slider gesture."""

    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session
        self.visible = False
        self.target_object = None
        self.atom_ids = []
        self.scales = {}
        self._last_slider_values = {key: 0.0 for key, *_ in _SLIDERS}
        self._suppress_signal = False
        self._undo_pushed_this_gesture = False

    def open_window(self, target_object, atom_ids):
        self.target_object = target_object
        self.atom_ids = sorted(atom_ids)
        self._reset_sliders()
        if not self.visible:
            self._build_window()
        else:
            self.window.present()
        for scale in self.scales.values():
            scale.set_sensitive(bool(self.atom_ids))
        self.header_label.set_text(
            f"{target_object.name} — {len(self.atom_ids)} atom(s) selected"
        )
        self.status_label.set_text("")

    def _build_window(self):
        self.window = Gtk.Window(title="Transform Selection", transient_for=self.main.window)
        self.window.set_default_size(340, 400)
        self.window.connect("close-request", self.on_close_request)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(10)
        self.window.set_child(root)
        self.header_label = Gtk.Label(xalign=0)
        self.header_label.set_wrap(True)
        root.append(self.header_label)

        self.scales = {}
        for key, title, lower, upper, step, page, digits in _SLIDERS:
            label = Gtk.Label(label=title, xalign=0)
            root.append(label)
            scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, lower, upper, step
            )
            scale.set_digits(digits)
            scale.set_draw_value(True)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            scale.set_hexpand(True)
            scale.get_adjustment().set_page_increment(page)
            scale.set_sensitive(False)
            scale.connect("value-changed", self._on_scale_changed, key)
            gesture = Gtk.GestureDrag.new()
            gesture.connect("drag-end", self._on_scale_gesture_end, scale)
            scale.add_controller(gesture)
            self.scales[key] = scale
            root.append(scale)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_halign(Gtk.Align.END)
        refresh = Gtk.Button(label="Refresh")
        refresh.connect("clicked", self.on_refresh)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.close_window)
        actions.append(refresh)
        actions.append(close)
        root.append(actions)
        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_wrap(True)
        root.append(self.status_label)
        self.visible = True
        self.window.present()

    def _live_atom_ids(self):
        if self.target_object is None:
            return []
        return [aid for aid in self.atom_ids if aid in self.target_object.atoms]

    def _on_scale_changed(self, scale, key):
        self._apply_delta(key, scale.get_value())

    def _apply_delta(self, key, new_value):
        if self._suppress_signal:
            return
        atom_ids = self._live_atom_ids()
        if not atom_ids:
            return
        delta = new_value - self._last_slider_values[key]
        self._last_slider_values[key] = new_value
        if abs(delta) < 1e-9:
            return
        if not self._undo_pushed_this_gesture:
            push_undo_snapshot(self.target_object)
            self._undo_pushed_this_gesture = True
        if key[0] == "t":
            offset = {"x": (delta, 0.0, 0.0), "y": (0.0, delta, 0.0),
                      "z": (0.0, 0.0, delta)}[key[1]]
            translate_atoms(self.target_object, atom_ids, *offset)
        else:
            pivot = selection_centroid(self.target_object, atom_ids)
            rotate_atoms_around_point(
                self.target_object, atom_ids, pivot, _AXIS_VECTORS[key[1]],
                math.radians(delta),
            )

    def _on_scale_gesture_end(self, gesture, offset_x, offset_y, scale):
        if self._undo_pushed_this_gesture:
            from gui.windows.builder.empty_object import sync_pdynamo_system
            sync_pdynamo_system(self.target_object)
        self._reset_sliders()

    def _reset_sliders(self):
        self._last_slider_values = {key: 0.0 for key, *_ in _SLIDERS}
        self._undo_pushed_this_gesture = False
        if not self.scales:
            return
        self._suppress_signal = True
        for scale in self.scales.values():
            scale.set_value(0.0)
        self._suppress_signal = False

    def on_refresh(self, button):
        target = getattr(self.vm_session, "builder_target_object", None)
        if target is None:
            self.status_label.set_text("No Builder target object.")
            return
        selection = self.vm_session.selections.get(self.vm_session.current_selection)
        selected = getattr(selection, "selected_atoms", None) or set()
        atom_ids = {atom.atom_id for atom in selected if atom.vm_object is target}
        self.open_window(target, atom_ids)
        self.status_label.set_text("Refreshed.")

    def close_window(self, *args):
        if getattr(self, "window", None) is not None:
            self.window.destroy()
        self.visible = False
        return True

    def on_close_request(self, *args):
        return self.close_window()
