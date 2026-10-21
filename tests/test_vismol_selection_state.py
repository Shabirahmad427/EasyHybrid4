"""Regression coverage for viewing-selection state transitions."""

from types import SimpleNamespace

import numpy as np
import pytest

import vismol.core.vismol_selections as selections_module
from vismol.core.vismol_selections import (
    VismolPickingSelection,
    VismolViewingSelection,
)


def test_clearing_viewing_selection_clears_atom_flags_and_object_ids():
    class FakeVismolObject:
        def __init__(self):
            self.frames = np.zeros((1, 2, 3), dtype=np.float32)
            self.atoms = {}
            self.selected_atom_ids = set()

    class FakeAtom:
        def __init__(self, atom_id, vm_object):
            self.atom_id = atom_id
            self.selected = False
            self.vm_object = vm_object

    molecule = FakeVismolObject()
    atoms = [FakeAtom(index, molecule) for index in range(2)]
    molecule.atoms = {index: atom for index, atom in enumerate(atoms)}
    session = SimpleNamespace(vm_objects_dic={0: molecule}, frame=0)
    selection = VismolViewingSelection(session)
    selection.selection_mode = "atom"

    selection.selection_function_viewing_set([atoms[0], atoms[1]])
    assert selection.selected_atoms == set(atoms)
    assert all(atom.selected for atom in atoms)
    assert molecule.selected_atom_ids == {0, 1}

    selection.selection_function_viewing_set(None)

    assert selection.selected_atoms == set()
    assert not any(atom.selected for atom in atoms)
    assert molecule.selected_atom_ids == set()
    assert selection.active is False


def test_picked_atom_pair_reports_current_frame_distance(monkeypatch):
    class FakeAtom:
        def __init__(self, name, xyz):
            self.name = name
            self.xyz = np.asarray(xyz, dtype=np.float32)

        def coords(self, frame=None):
            assert frame is None
            return self.xyz

    oxygen = FakeAtom("O", (0.0, 0.0, 0.0))
    hydrogen = FakeAtom("H1", (0.957, 0.0, 0.0))
    messages = []
    monkeypatch.setattr(selections_module, "dprint", messages.append)

    selection = object.__new__(VismolPickingSelection)
    selection.vm_session = SimpleNamespace(get_frame=lambda: 0)
    selection.picking_selections_list = [oxygen, hydrogen, None, None]
    selection.print_pk_distances()

    assert len(messages) == 1
    assert "O-H1: 0.95700" in messages[0]


def test_picked_atom_triplet_angle_uses_middle_atom_as_vertex():
    selection = object.__new__(VismolPickingSelection)
    selection.xyz1 = np.array((1.0, 0.0, 0.0), dtype=np.float32)
    selection.xyz2 = np.array((0.0, 0.0, 0.0), dtype=np.float32)
    selection.xyz3 = np.array((0.0, 0.0, 1.0), dtype=np.float32)

    assert selection.get_angle_pk1_pk2_pk3() == pytest.approx(90.0)
