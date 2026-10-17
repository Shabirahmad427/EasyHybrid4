"""Disposable GTK4 VisMol preview for Builder fragments."""

import numpy as np

from vismol.core.vismol_session import VismolSession
from vismol.core.vismol_object import VismolObject
from gui.windows.builder.atom_ops import add_atom, _reapply_manual_bonds


def _install_zoom_and_rotate_only_filter(vm_glcore):
    original = vm_glcore.mouse_pressed

    def filtered(button_number, mouse_x, mouse_y, button_state=None):
        button = int(button_number)
        if button == 2 or (button == 1 and getattr(vm_glcore, "shift", False)):
            return
        return original(button_number, mouse_x, mouse_y, button_state)

    vm_glcore.mouse_pressed = filtered


class MoleculePreview:
    """Own one GTK4 render session and show one fragment at a time."""

    def __init__(self):
        self.vm_session = VismolSession(toolkit="Gtk_4.0")
        self.widget = self.vm_session.vm_widget
        _install_zoom_and_rotate_only_filter(self.vm_session.vm_glcore)
        self.vm_session.vm_config.gl_parameters["sticks_radius"] = 0.16

    def show(self, name, atoms, bonds):
        self.clear()
        obj = VismolObject(
            vismol_session=self.vm_session, index=0, name=name, active=True
        )
        obj.frames = np.zeros((1, 0, 3), dtype=np.float32)
        obj.manual_bonds = set()
        obj.manual_bond_orders = {}

        for symbol, x, y, z in atoms:
            add_atom(
                obj, symbol, x, y, z, recompute_bonds=False,
                update_representation=False,
            )
        for bond in bonds:
            i, j, order = bond[:3]
            pair = (min(i, j), max(i, j))
            obj.manual_bonds.add(pair)
            obj.manual_bond_orders[pair] = int(order)

        if obj.atoms:
            _reapply_manual_bonds(obj)
            obj.create_representation(rep_type="lines")
            obj.create_representation(rep_type="nonbonded")
        self.vm_session.vm_objects_dic[0] = obj
        if obj.atoms:
            self.vm_session.vm_glcore.center_on_coordinates(obj, obj.mass_center)
        self.vm_session.vm_glcore.queue_draw()

    def clear(self):
        self.vm_session.vm_objects_dic = {}
        self.vm_session.atom_dic_id = {}
        self.vm_session.atom_id_counter = np.uint32(0)
        self.vm_session.vm_glcore.queue_draw()
