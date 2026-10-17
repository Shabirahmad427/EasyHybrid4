"""GTK4 window for interactively setting a picked Builder dihedral."""

import math

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class DihedralAngleWindow:
    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session
        self.visible = False
        self._suppress_value_changed = False

    def open_window(self, angle_deg):
        if not self.visible:
            self.window = Gtk.Window(title="Dihedral Angle", transient_for=self.main.window)
            self.window.set_default_size(300, -1)
            self.window.connect("close-request", self.on_close_button_clicked)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            root.set_margin_top(8)
            root.set_margin_bottom(8)
            root.set_margin_start(8)
            root.set_margin_end(8)
            root.append(Gtk.Label(label="Dihedral angle (degrees)", xalign=0))

            self.dihedral_angle_scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, -180.0, 180.0, 1.0
            )
            self.dihedral_angle_scale.set_digits(0)
            self.dihedral_angle_scale.set_draw_value(True)
            self.dihedral_angle_scale.set_value_pos(Gtk.PositionType.RIGHT)
            self.dihedral_angle_scale.connect(
                "value-changed", self.on_dihedral_slider_value_changed
            )
            release = Gtk.GestureClick()
            release.set_button(0)
            release.connect("released", self.on_dihedral_slider_released)
            self.dihedral_angle_scale.add_controller(release)
            drag = Gtk.GestureDrag()
            drag.connect("drag-end", self.on_dihedral_drag_ended)
            self.dihedral_angle_scale.add_controller(drag)
            key_release = Gtk.EventControllerKey()
            key_release.connect("key-released", self.on_dihedral_key_released)
            self.dihedral_angle_scale.add_controller(key_release)
            root.append(self.dihedral_angle_scale)

            close_button = Gtk.Button(label="Close", halign=Gtk.Align.END)
            close_button.connect("clicked", self.on_close_button_clicked)
            root.append(close_button)
            self.window.set_child(root)
            self.visible = True
        else:
            self.window.present()

        self._suppress_value_changed = True
        self.dihedral_angle_scale.set_value(angle_deg)
        self._suppress_value_changed = False
        self.window.present()

    def close_window(self, *args):
        if getattr(self, "window", None) is not None:
            self.window.destroy()
        self.visible = False
        return True

    def on_dihedral_slider_value_changed(self, scale):
        if self._suppress_value_changed:
            return
        target = getattr(self.vm_session, "builder_target_object", None)
        axis = getattr(self.vm_session, "builder_dihedral_axis", None)
        subgroup = getattr(self.vm_session, "builder_dihedral_subgroup", None)
        picked = getattr(self.vm_session, "builder_dihedral_pick_atoms", None)
        if target is None or axis is None or subgroup is None or len(picked or ()) != 4:
            return

        from util.geometric_analysis import get_dihedral
        from gui.windows.builder.atom_ops import rotate_atoms_around_bond

        atom_ids = [atom.atom_id for atom in picked]
        try:
            current = get_dihedral(target, *atom_ids)
        except (ValueError, IndexError):
            return
        delta = (scale.get_value() - current + 180.0) % 360.0 - 180.0
        if abs(delta) > 1e-9:
            rotate_atoms_around_bond(
                target, axis[0], axis[1], subgroup, math.radians(delta)
            )

    def on_dihedral_slider_released(self, gesture, n_press, x, y):
        self._sync_target_system()

    def on_dihedral_drag_ended(self, gesture, offset_x, offset_y):
        self._sync_target_system()

    def on_dihedral_key_released(self, controller, keyval, keycode, state):
        self._sync_target_system()

    def _sync_target_system(self):
        target = getattr(self.vm_session, "builder_target_object", None)
        if target is not None:
            from gui.windows.builder.empty_object import sync_pdynamo_system
            sync_pdynamo_system(target)

    def on_close_button_clicked(self, *args):
        return self.close_window()
