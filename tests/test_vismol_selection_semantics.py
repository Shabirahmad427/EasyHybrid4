"""Regression coverage for production VisMol atom and residue selection state."""

from types import SimpleNamespace

from vismol.core.vismol_selections import VismolViewingSelection
from vismol.libgl.representations import compute_atom_label_text


def _water_selection(make_vismol_object, vm_session):
    molecule = make_vismol_object(["O", "H", "H"], [0, 1, 0, 2])
    vm_session.frame = 0
    vm_session.vm_objects_dic = {0: molecule}
    residue = SimpleNamespace(atoms=molecule.atoms)
    for atom in molecule.atoms.values():
        atom.residue = residue
        atom.atom_id = atom.index
    return molecule, VismolViewingSelection(vm_session)


def test_atom_mode_tracks_only_the_clicked_atom(make_vismol_object, vm_session):
    molecule, selection = _water_selection(make_vismol_object, vm_session)
    oxygen = molecule.atoms[0]
    selection.selection_mode = "atom"

    selection.selection_function_viewing_set({oxygen})

    assert selection.selected_atoms == {oxygen}
    assert molecule.selected_atom_ids == {oxygen.atom_id}
    assert oxygen.selected
    assert all(not atom.selected for atom in molecule.atoms.values() if atom is not oxygen)


def test_residue_mode_selects_and_toggles_the_whole_residue(
    make_vismol_object, vm_session
):
    molecule, selection = _water_selection(make_vismol_object, vm_session)
    oxygen = molecule.atoms[0]

    selection.selection_function_viewing_set({oxygen})

    assert selection.selected_atoms == set(molecule.atoms.values())
    assert molecule.selected_atom_ids == {atom.atom_id for atom in molecule.atoms.values()}
    assert all(atom.selected for atom in molecule.atoms.values())

    selection.selection_function_viewing_set({oxygen})

    assert selection.selected_atoms == set()
    assert molecule.selected_atom_ids == set()
    assert all(not atom.selected for atom in molecule.atoms.values())
    assert selection.selected_objects == set()
    assert selection.selected_coords is None


def test_clearing_viewing_selection_resets_atom_flags_and_id_buffer(
    make_vismol_object, vm_session
):
    molecule, selection = _water_selection(make_vismol_object, vm_session)
    selection.selection_function_viewing_set({molecule.atoms[0]})
    assert any(atom.selected for atom in molecule.atoms.values())

    selection.selection_function_viewing_set(None)

    assert selection.selected_atoms == set()
    assert molecule.selected_atom_ids == set()
    assert all(not atom.selected for atom in molecule.atoms.values())
    assert selection.selected_objects == set()
    assert selection.selected_coords is None


def test_index_selection_rebuilds_all_derived_state(make_vismol_object, vm_session):
    molecule, selection = _water_selection(make_vismol_object, vm_session)
    selection.selecting_by_indexes(molecule, [0, 2], clear=True)

    expected = {molecule.atoms[0], molecule.atoms[2]}
    assert selection.selected_atoms == expected
    assert selection.selected_objects == {molecule}
    assert molecule.selected_atom_ids == {0, 2}
    assert {atom for atom in molecule.atoms.values() if atom.selected} == expected


def test_invert_selection_updates_flags_ids_and_objects(make_vismol_object, vm_session):
    molecule, selection = _water_selection(make_vismol_object, vm_session)
    selection.selection_mode = "atom"
    selection.selection_function_viewing_set({molecule.atoms[0]})

    selection.invert_selection(molecule)

    expected = {molecule.atoms[1], molecule.atoms[2]}
    assert {atom for atom in molecule.atoms.values() if atom.selected} == expected
    assert selection.selected_atoms == expected
    assert selection.selected_objects == {molecule}
    assert molecule.selected_atom_ids == {1, 2}


def test_atom_label_content_supports_name_symbol_index_and_residue(make_vismol_object, vm_session):
    molecule, _selection = _water_selection(make_vismol_object, vm_session)
    oxygen = molecule.atoms[0]
    oxygen.chain = SimpleNamespace(name="A")
    oxygen.residue.name = "HOH"
    oxygen.residue.index = 1

    assert compute_atom_label_text(oxygen, "name") == "O"
    assert compute_atom_label_text(oxygen, "symbol") == "O"
    assert compute_atom_label_text(oxygen, "index") == str(oxygen.index)
    assert compute_atom_label_text(oxygen, "residue_name") == "HOH"
    assert compute_atom_label_text(oxygen, "residue_index") == "1"
    assert compute_atom_label_text(oxygen, "chain") == "A"
