"""Regression coverage for viewing-selection state transitions."""

from types import SimpleNamespace

import numpy as np

from vismol.core.vismol_selections import VismolViewingSelection


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
