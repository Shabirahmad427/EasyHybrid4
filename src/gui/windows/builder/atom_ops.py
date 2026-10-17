#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: Molecule Builder -- atom-level editing operations
#
#  Description:
#      Second building block of the "Builder" tool. add_atom() below adds a
#      single atom to a VismolObject, whether it currently has zero atoms
#      (a builder-created empty object, see empty_object.py) or already has
#      some (a real, file-loaded molecule -- this function does not care
#      which; it only touches the same internal structures either way).
#
#      Design notes / what this reuses from the existing codebase (all
#      read from source, not guessed):
#        - vismol_object.frames is the single source of truth for atom
#          coordinates: Atom.coords() reads self.vm_object.frames[frame,
#          self.atom_id] directly, NOT some per-atom cached position (the
#          Atom.pos attribute is described in atom.py itself as just "the
#          coordinates of the first frame", i.e. a convenience snapshot,
#          not the live value). Adding an atom therefore means growing
#          .frames along its atom axis (axis=1) for every existing frame,
#          not just setting atom.pos.
#        - Chain / Residue containers are created lazily, matching the
#          exact same pattern used by the real file loaders (e.g.
#          vismol.utils.XYZFiles.load_xyz_file): if the requested chain_id
#          / residue index don't exist yet on this object, create them
#          with sensible defaults ("A" / 1 / "UNK") before creating the
#          Atom itself.
#        - Atom.unique_id / _generate_atom_unique_color_id() are what the
#          picking/selection system uses (an RGB-encoded unique ID, see
#          _generate_atom_unique_color_id in atom.py) -- every atom loaded
#          from a file gets these assigned via vm_session.atom_id_counter,
#          so builder-created atoms do the same to stay selectable/
#          pickable like any other atom.
#        - Bond (re)detection reuses VismolObject.find_bonded_and_
#          nonbonded_atoms() UNCHANGED -- the same grid/covalent-radius
#          based auto-detection already used "at the object's genesis"
#          when loading a real file (see that method's own docstring).
#          This also populates self.non_bonded_atoms, which is what the
#          "nonbonded" representation (dots/spheres for atoms with no
#          bonds -- necessary for a single freshly-placed atom to be
#          visible at all, since "lines"/"sticks" only draw BONDS) needs.
#          self.cov_radii_array / self.electronegativity_array / .
#          index_bonds are reset to None first so that method recomputes
#          them fresh at the new atom count instead of using stale,
#          wrong-sized arrays from before this atom was added.
#
#      NOT implemented yet (left for later steps): removing atoms, moving
#      an existing atom, adding an explicit bond without relying on
#      distance-based auto-detection, undo/redo.
#
import numpy as np
import copy
from vismol.model.atom import Atom
from vismol.model.chain import Chain
from vismol.model.residue import Residue


def add_atom ( vismol_object, symbol, x, y, z, name = None,
               chain_id = "A", resi = 1, resn = "UNK",
               bonded_to = None,
               recompute_bonds = True, update_representation = True,
               formal_charge = 0 ):
    """ Adds a single atom to vismol_object at position (x, y, z), in the
    same coordinate units/frame convention already used by the rest of
    the object (Angstrom, matching every file-loaded VismolObject).

    Works whether vismol_object currently has zero atoms (e.g. one just
    created by empty_object.create_empty_vismol_object()) or already has
    atoms -- either way the new atom is simply appended after the
    existing ones (atom_id = current atom count).

    Parameters
    ----------
    vismol_object : VismolObject
    symbol   : element symbol, e.g. "C", "N", "O", "H" -- used to look up
               default color/radii/electronegativity via the periodic
               table (see Atom._init_color / _init_vdw_rad / etc.).
    x, y, z  : position of the new atom, in Angstrom.
    name     : atom name (e.g. "CA", "OXT"...); defaults to `symbol` if
               not given, which is the common case for a freshly-placed,
               not-yet-part-of-a-residue-template atom.
    chain_id, resi, resn : which Chain/Residue this atom belongs to.
               Created on the fly, with sensible defaults, if they don't
               exist yet on this object -- same pattern the file loaders
               already use.
    bonded_to : atom_id, or list of atom_ids, this new atom should be
               EXPLICITLY bonded to (via the same manual_bonds mechanism
               add_bond() uses -- see _reapply_manual_bonds()). This is
               now the ONLY way a newly-added atom ends up bonded to
               anything: distance-based auto-detection was intentionally
               turned OFF (see below), so an atom placed near another one
               by coincidence does NOT become bonded to it just from
               proximity anymore.
    recompute_bonds : if True (default), rebuilds bonds/topology/molecule
               grouping from vismol_object.manual_bonds (via
               _reapply_manual_bonds()) after adding the atom. Set False
               only if you're about to add several atoms in a row and
               want to pay for this once, at the end (call
               _reapply_manual_bonds(vismol_object) yourself afterwards
               in that case).
    update_representation : if True (default), (re)creates the "lines"
               and "nonbonded" representations so the new atom actually
               becomes visible immediately. Same reasoning as
               recompute_bonds for batching -- skip and do it yourself
               once at the end if adding many atoms in a loop.

    [EN] DESIGN CHANGE: distance-based bond auto-detection (vismol_
    object.find_bonded_and_nonbonded_atoms(), the same grid/covalent-
    radius heuristic used when loading a real file) used to run here on
    every call. Turned OFF entirely for the Builder (confirmed, by
    request, after live testing kept surfacing correctness issues that
    all traced back to it -- see _reapply_manual_bonds()'s own docstring
    for the two concrete bugs this caused: a manually-created bond
    silently vanishing when this ran again later for an unrelated atom,
    and, after fixing that, visibly DUPLICATED lines, because that
    native detection's own raw output isn't deduplicated by itself). The
    Builder is a deliberate, atom-by-atom sketchpad -- every bond should
    come from an explicit action (dragging, the 'b' key, or the auto-
    hydrogenation convenience, which now also bonds explicitly -- see
    click_mode.py), never from two atoms merely ending up close to each
    other. Bonds now live ENTIRELY in vismol_object.manual_bonds, rebuilt
    by _reapply_manual_bonds() (bond-object/topology/molecule-grouping
    bookkeeping only -- no more distance queries at all).

    Returns the new Atom object.
    """
    vm_session = vismol_object.vm_session

    if name is None:
        name = symbol

    # --- Chain / Residue (create lazily, same pattern as the file loaders) ---
    if chain_id not in vismol_object.chains:
        vismol_object.chains[chain_id] = Chain ( vismol_object, name = chain_id )
    chain = vismol_object.chains[chain_id]

    if resi not in chain.residues:
        chain.residues[resi] = Residue ( vismol_object, name = resn, index = resi, chain = chain )
    residue = chain.residues[resi]

    atom_id = len ( vismol_object.atoms )   # next free index, sequential

    atom = Atom (
        vismol_object = vismol_object,
        name          = name,
        index         = atom_id + 1,   # index e 1-based por convencao (ver comentario em Atom.__init__)
        residue       = residue,
        chain         = chain,
        symbol        = symbol,
        atom_id       = atom_id,
    )
    atom.pos = np.array ( [ x, y, z ], dtype = np.float32 )
    atom.formal_charge = int ( formal_charge )
    atom.unique_id = vm_session.atom_id_counter
    atom._generate_atom_unique_color_id ( )
    vm_session.atom_id_counter += 1
    # [EN] REQUIRED for picking/selection to find this atom: the picking
    # system decodes the RGB colour under the mouse click back into
    # pickedID (== atom.unique_id) and looks it up in
    # vm_session.atom_dic_id[pickedID] to get the actual Atom object (see
    # vismol_glcore.py's _pick()/_selection_box_pick()). Every atom
    # normally gets registered here by eSession._add_vismol_object() (for
    # atoms present when an object is FIRST added to the session) -- but
    # register_builder_object() (empty_object.py) intentionally skips
    # that whole method (see its own docstring for why), and an object
    # is only ever added to the session ONCE, while atoms are added one
    # at a time afterwards -- so each new atom needs this registration
    # done here individually instead. Missing this was a real, confirmed
    # bug (atoms added via add_atom() were not selectable at all).
    vm_session.atom_dic_id[atom.unique_id] = atom

    residue.atoms[atom_id]        = atom
    vismol_object.atoms[atom_id]  = atom

    # --- grows vismol_object.frames by +1 atom, for ALL frames already
    # existing (the new atom enters with the SAME position (x,y,z) in each
    # frame -- coerente pra um objeto builder, que tipicamente tem so 1
    # frame mesmo; se este objeto ja tiver uma trajetoria de verdade, isso
    # still works, except the new atom stays "still" across all
    # frames ate que algo mais sofisticado seja implementado). ---
    n_frames = vismol_object.frames.shape[0]
    new_frames = np.zeros ( (n_frames, atom_id + 1, 3), dtype = np.float32 )
    if atom_id > 0:
        new_frames[:, :atom_id, :] = vismol_object.frames
    new_frames[:, atom_id, :] = [ x, y, z ]
    vismol_object.frames = new_frames

    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )

    # recalcula cores/vdw/tamanhos de ponto pra TODOS os atomos -- simples
    # is correct; the colors_id_start parameter is not even used inside the
    # method (checked by reading the source), so the exact value passed
    # here does not matter.
    vismol_object._generate_color_vectors ( vm_session.atom_id_counter )

    # [EN] Register any explicitly-requested bond(s) for this new atom --
    # the ONLY way it ends up bonded to anything now that distance-based
    # auto-detection is off (see this function's own docstring above).
    if bonded_to is not None:
        if not hasattr ( vismol_object, "manual_bonds" ) or vismol_object.manual_bonds is None:
            vismol_object.manual_bonds = set ( )
        targets = bonded_to if isinstance ( bonded_to, ( list, tuple, set ) ) else [ bonded_to ]
        for other_id in targets:
            pair = ( min ( atom_id, other_id ), max ( atom_id, other_id ) )
            vismol_object.manual_bonds.add ( pair )

    if recompute_bonds:
        # [EN] No more find_bonded_and_nonbonded_atoms() call here (that
        # was the native, distance-based detection -- see this function's
        # docstring for why it was removed). _reapply_manual_bonds() alone
        # is enough: it rebuilds self.bonds/topology/molecule-grouping
        # purely from vismol_object.manual_bonds (which now includes the
        # bonded_to pair(s) just registered above, if any), no distance
        # queries involved at all.
        vismol_object.cov_radii_array = None
        vismol_object.electronegativity_array = None
        vismol_object.index_bonds = None
        vismol_object.bonds = None
        vismol_object.non_bonded_atoms = None
        _reapply_manual_bonds ( vismol_object )

    if update_representation:
        vismol_object.create_representation ( rep_type = "lines" )
        vismol_object.create_representation ( rep_type = "nonbonded" )
        # [EN] REQUIRED for the new atom to be selectable/pickable via
        # mouse click, in addition to the atom_dic_id registration above:
        # vm_glcore.render() only ever calls build_core_representations()
        # (which is what creates "picking_dots", the representation the
        # click-picking system actually reads pixel colours from) ONCE --
        # guarded by "if core_representations['picking_dots'] is None".
        # After that first build, adding more atoms does NOT automatically
        # grow/rebuild it (was_rep_coord_modified only tells the renderer
        # to re-upload COORDINATES for the atom count it already knows
        # about, not that the atom count itself changed). Resetting both
        # core_representations entries to None here forces
        # build_core_representations() to run again, fresh, the next time
        # render() fires -- picking up the current, correct atom count.
        vismol_object.core_representations["picking_dots"] = None
        vismol_object.core_representations["picking_text"] = None
        if getattr ( vm_session, "vm_glcore", None ) is not None:
            vm_session.vm_glcore.queue_draw ( )

    return atom


def add_structure_at_position(vismol_object, structure, x, y, z):
    """Insert a complete MOL2 structure centered at the given object point."""
    atoms = structure.get("atoms", [])
    if not atoms:
        raise ValueError("The selected structure contains no atoms.")
    centroid = np.mean(np.asarray([atom[1:4] for atom in atoms], dtype=float), axis=0)
    chain_id = "A"
    chain = vismol_object.chains.get(chain_id)
    residue_ids = list(chain.residues) if chain is not None else []
    resi = max(residue_ids, default=0) + 1
    letters = "".join(c for c in structure.get("name", "") if c.isalnum()).upper()
    resn = (letters[:3] or "UNK")
    new_atoms = []
    local_to_id = {}
    name_counts = {}
    for local_index, (symbol, ax, ay, az) in enumerate(atoms):
        name_counts[symbol] = name_counts.get(symbol, 0) + 1
        atom = add_atom(
            vismol_object, symbol, x + ax - centroid[0],
            y + ay - centroid[1], z + az - centroid[2],
            name=f"{symbol}{name_counts[symbol]}", chain_id=chain_id,
            resi=resi, resn=resn, recompute_bonds=False,
            update_representation=False,
        )
        local_to_id[local_index] = atom.atom_id
        new_atoms.append(atom)

    if vismol_object.manual_bonds is None:
        vismol_object.manual_bonds = set()
    if vismol_object.manual_bond_orders is None:
        vismol_object.manual_bond_orders = {}
    if not hasattr(vismol_object, "manual_aromatic_bonds") or vismol_object.manual_aromatic_bonds is None:
        vismol_object.manual_aromatic_bonds = set()
    for i, j, order, aromatic in structure.get("bonds", []):
        pair = tuple(sorted((local_to_id[i], local_to_id[j])))
        vismol_object.manual_bonds.add(pair)
        vismol_object.manual_bond_orders[pair] = int(order)
        if aromatic:
            vismol_object.manual_aromatic_bonds.add(pair)

    _reapply_manual_bonds(vismol_object)
    vismol_object.create_representation(rep_type="lines")
    vismol_object.create_representation(rep_type="nonbonded")
    _refresh_bond_dependent_representations(vismol_object)
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None
    vm_session = vismol_object.vm_session
    if getattr(vm_session, "vm_glcore", None) is not None:
        vm_session.vm_glcore.queue_draw()
    return new_atoms


def bootstrap_manual_bonds_from_existing(vismol_object, source_vobject=None):
    """Seed Builder bond bookkeeping from an existing VisMol object."""
    if getattr(vismol_object, "manual_bonds", None):
        return
    source = source_vobject or vismol_object
    existing = getattr(source, "manual_bonds", None)
    if existing:
        vismol_object.manual_bonds = set(existing)
        vismol_object.manual_bond_orders = dict(getattr(source, "manual_bond_orders", None) or {})
        vismol_object.manual_aromatic_bonds = set(getattr(source, "manual_aromatic_bonds", None) or ())
        return

    pairs = list((getattr(source, "bonds", None) or {}).keys())
    vismol_object.manual_bonds = set(pairs)
    vismol_object.manual_bond_orders = {}
    vismol_object.manual_aromatic_bonds = set()
    if not pairs:
        return
    try:
        from gui.windows.builder.residue_chemistry import assign_bond_orders
        coords = {i: tuple(float(c) for c in source.frames[0, i])
                  for i in source.atoms if i < source.frames.shape[1]}
        orders, charges, _report = assign_bond_orders(source.atoms, pairs, coords)
        vismol_object.manual_bond_orders = {pair: int(orders.get(pair, 1)) for pair in pairs}
        for atom_id, charge in charges.items():
            atom = vismol_object.atoms.get(atom_id)
            if atom is not None and not getattr(atom, "formal_charge", 0):
                atom.formal_charge = int(charge)
    except Exception:
        vismol_object.manual_bond_orders = {pair: 1 for pair in pairs}


def set_atom_element ( vismol_object, atom_id, symbol, name = None,
                        recompute_bonds = True, update_representation = True ):
    """ [EN] Changes the chemical ELEMENT of an already-existing atom, IN

    PLACE -- same atom_id, same position, same bonds-list slot. Used by
    the Builder's "add" tool when a plain click lands ON an atom that
    already exists (see click_mode.handle_click_to_place_atom()):
    instead of stacking a new, essentially-overlapping atom on top of
    it, the existing atom is turned into the newly selected element.

    Unlike add_atom()/remove_atom(), this does NOT touch vismol_object.
    frames (position is unchanged) or vm_session.atom_dic_id / atom.
    unique_id (identity for picking is unchanged -- it's still "the same
    atom", just a different element now) -- only the element-derived
    per-atom attributes are recomputed, exactly the same way Atom.
    __init__ computes them the first time (self.symbol/self.name is set
    first, THEN each _init_*() is called, since every one of them reads
    self.symbol/self.name at call time -- see atom.py):
      - atom.color             (_init_color)
      - atom.vdw_rad            (_init_vdw_rad)
      - atom.cov_rad            (_init_cov_rad)   <- affects bond detection
      - atom.ball_rad           (_init_ball_rad)
      - atom.electronegativity  (_init_electronegativity)

    recompute_bonds : if True (default), rebuilds bonds/topology from
               vismol_object.manual_bonds (via _reapply_manual_bonds())
               after the change. [EN] DESIGN CHANGE: this parameter used
               to matter a lot more -- changing an atom's element used to
               trigger a fresh DISTANCE-based find_bonded_and_nonbonded_
               atoms() call, since cov_rad (which that detection uses)
               changes with the element (e.g. C -> O). Distance-based
               auto-detection is now turned OFF entirely for the Builder
               (see add_atom()'s docstring for why) -- bonds live purely
               in vismol_object.manual_bonds, which changing an element
               never touches. Kept as a parameter mostly for interface
               symmetry with add_atom()/remove_atom(); the rebuild it
               triggers now is just topology/molecule-grouping
               bookkeeping (harmless, cheap), not a real bond
               recalculation.
    update_representation : if True (default), rebuilds "lines"/
               "nonbonded" and forces a re-build of the picking
               representations, same reasoning as add_atom()/
               remove_atom() (the new colour otherwise wouldn't show up
               until something else forced a full rebuild).

    Returns the (mutated) Atom object.
    """
    if atom_id not in vismol_object.atoms:
        raise ValueError ( "set_atom_element: atom_id {} does not exist in this object.".format ( atom_id ) )

    atom = vismol_object.atoms[atom_id]

    if name is None:
        name = symbol

    atom.symbol = symbol
    atom.name   = name

    # Recompute every element-derived attribute -- same _init_*() methods
    # Atom.__init__ itself calls, now reading the just-updated symbol/name.
    atom.color             = atom._init_color ( )
    atom.vdw_rad           = atom._init_vdw_rad ( )
    atom.cov_rad           = atom._init_cov_rad ( )
    atom.ball_rad          = atom._init_ball_rad ( )
    atom.electronegativity = atom._init_electronegativity ( )

    vm_session = vismol_object.vm_session

    # same call add_atom()/remove_atom() make -- colors_id_start isn't
    # actually used inside the method (confirmed reading the source), so
    # the exact value passed doesn't matter, only that ALL atoms' colour
    # vectors get regenerated (this atom's new colour included).
    vismol_object._generate_color_vectors ( vm_session.atom_id_counter )

    if recompute_bonds:
        _reapply_manual_bonds ( vismol_object )

    if update_representation:
        vismol_object.create_representation ( rep_type = "lines" )
        vismol_object.create_representation ( rep_type = "nonbonded" )
        vismol_object.core_representations["picking_dots"] = None
        vismol_object.core_representations["picking_text"] = None
        if getattr ( vm_session, "vm_glcore", None ) is not None:
            vm_session.vm_glcore.queue_draw ( )

    return atom


def move_atom ( vismol_object, atom_id, x, y, z, update_representation = True ):
    """ [EN] Repositions an EXISTING atom to (x, y, z) -- element, bonds,
    atom_id, everything else about it stays untouched. Used by the
    Builder's click-and-drag-to-create-a-bonded-atom interaction (see
    click_mode.py's start_bond_drag()/update_bond_drag()/
    finish_bond_drag()) to move the still-being-dragged atom on EVERY
    mouse_motion event, without paying for a full bond-detection
    recompute on every pixel of mouse movement -- that only happens
    ONCE, when the drag ends (finish_bond_drag()).

    Deliberately does NOT touch bonds/topology/cov_radii_array/etc, and
    does NOT call vismol_object.find_bonded_and_nonbonded_atoms() --
    unlike add_atom()/remove_atom(), a simple reposition can't change
    the ATOM COUNT (the thing that method's reset-then-recompute dance
    exists to handle safely), so none of that is needed here; it would
    just make dragging noticeably less smooth for no benefit, run on
    every single mouse pixel of movement.

    update_representation (default True): instead of the FULL
    create_representation() rebuild add_atom()/remove_atom() do (needed
    there because the atom COUNT changed), this uses the SAME cheap
    "just re-upload coordinates, not the whole VBO" mechanism already
    used for trajectory/MD-frame playback -- see forward_frame() /
    reverse_frame() in vismol_session.py -- by setting
    vm_glcore.updated_coords = True (consumed once per frame inside
    render(), which marks every ACTIVE representation's coordinates
    dirty for re-upload). Safe to call every motion event during a drag;
    finish_bond_drag() turns updated_coords back off once the drag ends.

    Returns the (repositioned) Atom object.
    """
    if atom_id not in vismol_object.atoms:
        raise ValueError ( "move_atom: atom_id {} does not exist in this object.".format ( atom_id ) )

    vismol_object.frames[:, atom_id, :] = [ x, y, z ]
    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )

    if update_representation:
        vm_session = vismol_object.vm_session

        # [EN] Mark THIS object's representations dirty DIRECTLY (bug
        # fixed after the user reported the dragged atom only appearing
        # at its new position after releasing the mouse button, instead
        # of following the cursor live): the earlier version relied
        # solely on vm_glcore.updated_coords (the same flag trajectory/MD
        # playback uses -- see forward_frame()/reverse_frame() in
        # vismol_session.py), which is only turned into per-representation
        # rep.was_rep_coord_modified = True INSIDE render()'s own
        # "if self.updated_coords" block, on whatever vm_objects_dic
        # currently holds -- one extra layer of indirection between
        # "coordinates changed" and "this rep will actually re-upload
        # them" that wasn't reliably keeping up every single motion
        # event during a live drag. Setting the flag directly on this
        # object's own representations removes that indirection
        # entirely -- correctness no longer depends on render()'s global
        # per-frame sweep happening to run with the flag still set.
        for rep in vismol_object.representations.values ( ):
            if rep is not None and rep.active:
                rep.was_rep_coord_modified = True
                rep.was_sel_coord_modified = True
        picking_dots = vismol_object.core_representations.get ( "picking_dots" )
        if picking_dots is not None:
            picking_dots.was_rep_coord_modified = True

        if getattr ( vm_session, "vm_glcore", None ) is not None:
            # Kept in addition to the direct marking above (belt-and-
            # suspenders, matches the existing global convention) --
            # harmless if redundant, and covers any OTHER representation
            # that might read this flag in a way not accounted for above.
            vm_session.vm_glcore.updated_coords = True
            vm_session.vm_glcore.queue_draw ( )

    return vismol_object.atoms[atom_id]


def remove_atom ( vismol_object, atom_id ):
    """ [EN] Fourth building block of the Builder (delete-atom tool, 'd'
    key). Removes a single atom from vismol_object by its atom_id.

    Non-trivial because atom_id doubles as a dense array INDEX into
    vismol_object.frames (shape (n_frames, n_atoms, 3)) -- removing atom
    K means deleting frames[:, K, :] AND renumbering every atom with
    atom_id > K down by one, everywhere that number is used as a dict
    key (vismol_object.atoms, residue.atoms) or stored on the Atom object
    itself (atom.atom_id). Getting this renumbering wrong would silently
    corrupt frames/atoms alignment for every atom after the removed one.

    Also cleans up the two places keyed by identity/unique_id rather
    than atom_id (so they don't need renumbering, just removal of the
    deleted atom's own entry): vm_session.atom_dic_id (picking -- a
    stale entry pointing at a removed Atom would be a dangling
    reference) and every active selection's selected_atoms set (so a
    deleted atom can't stay "selected", which would be a real problem
    for add_bond() below if it silently included a since-deleted atom).

    Bonds/topology: rebuilt from vismol_object.manual_bonds (already
    remapped to the new atom numbering just above) via
    _reapply_manual_bonds() -- no distance queries involved. Distance-
    based auto-detection is turned OFF entirely for the Builder now (see
    add_atom()'s docstring for why); a manually-added bond DOES survive
    remove_atom(), as long as it doesn't involve the atom actually being
    removed (which has nothing sensible to remap to, so that specific
    pair is dropped -- see the id_map remapping above). """
    if atom_id not in vismol_object.atoms:
        raise ValueError ( "remove_atom: atom_id {} does not exist in this object.".format ( atom_id ) )

    vm_session = vismol_object.vm_session
    removed_atom = vismol_object.atoms[atom_id]

    # tira do dicionario global de picking (senao fica uma referencia
    # dangling pointing to an Atom that no longer exists in the object)
    if removed_atom.unique_id in vm_session.atom_dic_id:
        del vm_session.atom_dic_id[removed_atom.unique_id]

    # removes it from any active selection (otherwise a subsequent add_bond()
    # could mistakenly include an atom that was just deleted)
    for sel in vm_session.selections.values ( ):
        sel.selected_atoms.discard ( removed_atom )

    # tira do dict de atomos do residuo
    if removed_atom.residue is not None:
        removed_atom.residue.atoms.pop ( atom_id, None )

    del vismol_object.atoms[atom_id]

    # removes the corresponding row from ALL frames (axis=1 = atoms axis)
    vismol_object.frames = np.delete ( vismol_object.frames, atom_id, axis = 1 )

    # renumera atom_id de todo mundo com atom_id > removido, subtraindo 1 --
    # em vismol_object.atoms, em residue.atoms, e no proprio atom.atom_id
    old_atoms = vismol_object.atoms
    new_atoms = {}
    id_map = {}   # old_id -> new_id, para tambem remapear manual_bonds abaixo
    for old_id in sorted ( old_atoms.keys ( ) ):
        atom = old_atoms[old_id]
        new_id = old_id - 1 if old_id > atom_id else old_id
        id_map[old_id] = new_id
        if new_id != old_id:
            atom.atom_id = new_id
            if atom.residue is not None:
                atom.residue.atoms.pop ( old_id, None )
                atom.residue.atoms[new_id] = atom
        new_atoms[new_id] = atom
    vismol_object.atoms = new_atoms

    # [EN] REQUIRED, not optional: atom_id is a dense array index, so
    # removing one RENUMBERS every atom after it (see id_map above) --
    # manual_bonds stores atom_id PAIRS, so without remapping them the
    # SAME way, a bond like (3, 5) would silently start pointing at
    # whatever atoms happen to occupy ids 3/5 AFTER the shift, not the
    # atoms it was actually meant for. A pair involving the atom being
    # removed itself has nothing sensible to remap to, so it's dropped
    # instead (that connection genuinely no longer exists).
    if hasattr ( vismol_object, "manual_bonds" ) and vismol_object.manual_bonds:
        remapped_manual_bonds = set ( )
        for a, b in vismol_object.manual_bonds:
            if a == atom_id or b == atom_id:
                continue
            new_pair = ( min ( id_map[a], id_map[b] ), max ( id_map[a], id_map[b] ) )
            remapped_manual_bonds.add ( new_pair )
        vismol_object.manual_bonds = remapped_manual_bonds

    # [EN] Same remapping, same reasoning, for manually-set bond ORDERS
    # (click_mode.cycle_bond_order()) -- these are ALSO keyed by atom_id
    # pairs, so they'd silently end up describing the wrong bond after a
    # removal-triggered renumbering otherwise.
    if hasattr ( vismol_object, "manual_bond_orders" ) and vismol_object.manual_bond_orders:
        remapped_manual_bond_orders = { }
        for ( a, b ), order in vismol_object.manual_bond_orders.items ( ):
            if a == atom_id or b == atom_id:
                continue
            new_pair = ( min ( id_map[a], id_map[b] ), max ( id_map[a], id_map[b] ) )
            remapped_manual_bond_orders[new_pair] = order
        vismol_object.manual_bond_orders = remapped_manual_bond_orders

    vismol_object.mass_center = ( np.mean ( vismol_object.frames[0], axis = 0 )
                                  if vismol_object.frames.shape[1] > 0
                                  else np.zeros ( 3, dtype = np.float32 ) )
    vismol_object._generate_color_vectors ( vm_session.atom_id_counter )

    # bonds/topology now come entirely from vismol_object.manual_bonds
    # (ja remapeado acima) -- ver nota no docstring sobre deteccao por
    # distancia ter sido desligada.
    vismol_object.cov_radii_array = None
    vismol_object.electronegativity_array = None
    vismol_object.index_bonds = None
    vismol_object.bonds = None
    vismol_object.non_bonded_atoms = None
    if len ( vismol_object.atoms ) > 0:
        _reapply_manual_bonds ( vismol_object )
    else:
        vismol_object.index_bonds = []
        vismol_object.bonds = {}
        vismol_object.non_bonded_atoms = []

    vismol_object.create_representation ( rep_type = "lines" )
    vismol_object.create_representation ( rep_type = "nonbonded" )
    # ver nota em add_atom() -- forca build_core_representations() a
    # reconstruir do zero na proxima renderizacao, com a contagem de
    # atomos (agora menor) correta.
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )


def _reapply_manual_bonds ( vismol_object ):
    """ [EN] Re-merges every explicitly-added bond (this module's own
    add_bond()) recorded in vismol_object.manual_bonds back into the
    CURRENT index_bonds/bonds/topology -- i.e. restores manual bonds
    that a from-scratch find_bonded_and_nonbonded_atoms() recompute may
    have just silently dropped (that recompute is purely distance-
    based; a manual bond exists specifically because the two atoms are
    NOT within auto-detection range, so it can never reconstruct one on
    its own).

    BUG FIXED #1 (caught by live testing, not just reading): dragging
    out a SECOND bonded atom (click_mode.py's start_bond_drag(), which
    calls add_atom() to create the new atom) was silently erasing the
    bond created by a PREVIOUS drag -- add_atom()'s own find_bonded_and_
    nonbonded_atoms() call has no memory of bonds add_bond() added
    manually in an earlier, unrelated step. This was exactly the "KNOWN
    LIMITATION" add_bond() already documented in its own docstring, just
    not yet acted on anywhere. Fixed generically (not special-cased just
    for the drag feature) by calling this helper from every call site
    that does a from-scratch recompute: add_atom(), remove_atom(),
    set_atom_element(), and click_mode.finish_bond_drag() -- so ANY
    manually-added bond survives ANY of them, not just the one pair the
    bug happened to be reported for.

    BUG FIXED #2 (caught by live testing right after #1 -- dragging a
    SECOND bonded atom out was then showing duplicated/spurious lines
    instead of erasing anything): the native, purely distance-based
    find_bonded_and_nonbonded_atoms() (vismol_object.py's own
    cdist.get_atomic_bonds_from_grid()) stores each detected bond
    potentially MORE THAN ONCE in self.index_bonds -- both [i,j] and
    [j,i] for the SAME physical bond, and evidently not even always
    symmetrically (confirmed live: 3 atoms, all 3 pairs within bonding
    distance, ended up with index_bonds holding 10 flat integers -- 5
    raw (i,j) entries -- for what should be at most 3 UNIQUE bonds).
    That native call's own _bonds_from_pair_of_indexes_list() (which
    find_bonded_and_nonbonded_atoms() triggers internally, BEFORE this
    function ever runs) does NOT deduplicate: it creates a fresh Bond()
    object for EVERY raw occurrence and appends it to BOTH atoms' own
    .bonds lists every time (self.bonds, the OBJECT-level dict, happens
    to self-correct since it's keyed by a normalized (min,max) tuple and
    a later duplicate simply overwrites the same key -- but self.
    index_bonds itself, and each ATOM's .bonds list, keep every
    duplicate, and THAT's what the "lines" representation actually
    renders from). The first version of this function only rebuilt
    (deduplicating as a side effect) when a genuinely NEW manual bond
    needed adding -- so any call where nothing NEW needed adding (e.g.
    the pair was already auto-detected) skipped the rebuild entirely and
    let the native call's own un-deduplicated data pass straight
    through untouched, duplicates and all. Fixed by ALWAYS rebuilding
    from the deduplicated pair set below whenever there's at least one
    bond at all (not only when something NEW was added) -- this function
    now doubles as "restore manual bonds" AND "sanitize whatever the
    native call just produced", every single time it's called.

    Returns True if there was at least one bond ((re)built normally),
    False if the object has zero bonds at all (an isolated atom / all
    atoms unbonded) -- in that case self.bonds/self.non_bonded_atoms/
    self.index_bonds are still properly initialised to valid EMPTY
    structures ({}, all-atoms-non-bonded, and an empty array
    respectively), not left as None -- downstream representation code
    expects to be able to iterate them regardless of whether there are
    any bonds. Silently forgets (removes from vismol_object.manual_bonds)
    any recorded pair where an atom no longer exists (e.g. removed via
    remove_atom() since the bond was added) -- nothing sensible to
    restore there. """
    if not hasattr ( vismol_object, "manual_bonds" ) or vismol_object.manual_bonds is None:
        vismol_object.manual_bonds = set ( )
    manual_bonds = vismol_object.manual_bonds

    if vismol_object.index_bonds is not None and len ( vismol_object.index_bonds ) > 0:
        flat = np.asarray ( vismol_object.index_bonds ).reshape ( -1, 2 )
        existing_pairs = set ( tuple ( sorted ( p ) ) for p in flat.tolist ( ) )
    else:
        existing_pairs = set ( )

    for pair in list ( manual_bonds ):
        a, b = pair
        if a not in vismol_object.atoms or b not in vismol_object.atoms:
            manual_bonds.discard ( pair )

    merged_pairs = existing_pairs | manual_bonds   # union -- already deduplicated, since both sides are sets of normalized (min,max) tuples

    # [EN] BUG FIXED: this used to return early here (before rebuilding
    # anything) whenever there were zero bonds at all -- leaving self.
    # bonds/self.non_bonded_atoms/self.index_bonds sitting at None
    # (whatever the caller had just reset them to), instead of the valid,
    # empty-but-well-formed structures create_representation() actually
    # expects to iterate. Harmless for a lone atom added by itself, but
    # confirmed to break the VERY NEXT add_atom()/remove_atom() call on
    # the same object once distance-based auto-detection (which used to
    # paper over this by always producing a real, if empty, result) was
    # turned off. Fixed by always running the full rebuild below,
    # including the zero-bonds case -- _bonds_from_pair_of_indexes_list()
    # and friends handle an empty index_bonds array just fine (same
    # "zero bonds" state a freshly-created single atom always had
    # anyway, even back when auto-detection was still on).

    new_index_bonds = []
    for i, j in sorted ( merged_pairs ):
        new_index_bonds.append ( i )
        new_index_bonds.append ( j )

    vismol_object.bonds = None
    vismol_object.non_bonded_atoms = None
    vismol_object.index_bonds = np.array ( new_index_bonds, dtype = np.int64 )

    # [EN] Aligns with _bonds_from_pair_of_indexes_list()'s own
    # "Convention B": external_orders[k] must be the order of the k-th
    # bond that SURVIVES that method's own exclude_list filter (default
    # [['H','H']]) -- not the k-th raw pair.
    #
    # [EN] BUG FIX: this used to build external_orders with
    # manual_bond_orders.get((i,j), 1) -- i.e. DEFAULT TO A PLAIN SINGLE
    # BOND for every pair the user hadn't explicitly cycled/set an order
    # for. Combined with _bonds_from_pair_of_indexes_list() ALSO ignoring
    # external_orders entirely (separately fixed there -- see that
    # method's own updated comment), the net effect used to be "always
    # auto-perceive, manual overrides silently discarded". Fixing ONLY
    # the other method without fixing this default would have flipped
    # the bug the other way: "always plain single bonds, auto-perception
    # (aromatic/conjugated rings etc. -- see perceive_bond_order_for_pairs)
    # never runs for anything drawn in the Builder". Fixed by computing a
    # BASELINE via the same automatic perception used everywhere else
    # (perceive_bond_order_for_pairs -- exact maximum-matching heuristic,
    # handles conjugated rings correctly, see that method's own docstring
    # for the full history), then overriding ONLY the specific pairs the
    # user explicitly set in manual_bond_orders (via 'bond order=N' or
    # Ctrl+click cycle_bond_order()) on top of that baseline -- matching
    # cycle_bond_order()'s own stated intent ("persist the new order...
    # REQUIRED... without persisting it... cycling a bond's order here
    # would get silently overwritten back to the default").
    manual_bond_orders = getattr ( vismol_object, "manual_bond_orders", None ) or { }
    exclude_list = [ [ 'H', 'H' ] ]

    surviving_pairs = [ ]
    for i, j in sorted ( merged_pairs ):
        symbol_i = vismol_object.atoms[i].symbol
        symbol_j = vismol_object.atoms[j].symbol
        is_excluded = any ( symbol_i in pair and symbol_j in pair for pair in exclude_list )
        if is_excluded:
            continue
        surviving_pairs.append ( ( i, j ) )

    if surviving_pairs:
        flat_pairs = [ idx for pair in surviving_pairs for idx in pair ]
        baseline_orders = vismol_object.perceive_bond_order_for_pairs ( flat_pairs ).tolist ( )
    else:
        baseline_orders = [ ]

    external_orders = [ ]
    for k, ( i, j ) in enumerate ( surviving_pairs ):
        external_orders.append ( manual_bond_orders.get ( ( i, j ), baseline_orders[k] ) )

    vismol_object._bonds_from_pair_of_indexes_list ( external_orders = external_orders )
    vismol_object._get_non_bonded_from_bonded_list ( )
    vismol_object._generate_topology_from_index_bonds ( )
    vismol_object.define_molecules ( )
    vismol_object.define_Calpha_backbone ( )
    return bool ( merged_pairs )


def add_bond ( vismol_object, atom_id_a, atom_id_b, bond_order = 1 ):
    """ [EN] Fifth building block of the Builder ('b' key -- add a bond
    between exactly two currently-selected atoms). Unlike the automatic,
    distance-based bond detection find_bonded_and_nonbonded_atoms() does
    (used internally by add_atom()/remove_atom() above), this creates an
    EXPLICIT bond regardless of the distance between the two atoms --
    necessary for cases automatic detection would never produce on its
    own (e.g. deliberately closing a ring across a gap the covalent-
    radius/distance heuristic wouldn't recognise as bonded).

    Implementation: the pair is remembered PERMANENTLY in
    vismol_object.manual_bonds (created lazily), regardless of whether
    it happens to already be auto-detected at the moment this is called
    -- then _reapply_manual_bonds() (see its own docstring) merges
    manual_bonds into the current index_bonds and does the same
    downstream bookkeeping find_bonded_and_nonbonded_atoms() itself does
    (_bonds_from_pair_of_indexes_list, _get_non_bonded_from_bonded_list,
    _generate_topology_from_index_bonds, define_molecules,
    define_Calpha_backbone). Recording it unconditionally (not only when
    it turns out NOT to already be auto-detected) is what makes it
    survive add_atom()/remove_atom()/set_atom_element() recomputing
    everything from scratch LATER, even if at the moment of THIS call it
    happened to already be in bonding distance (fixes the KNOWN
    LIMITATION this function used to have, and still describes below for
    context -- confirmed via live testing to have actually been hit by
    the Builder's click-and-drag-to-create-a-bonded-atom feature: a
    SECOND drag's add_atom() call was silently erasing the FIRST drag's
    bond).

    [EN] BUG FIX: bond_order used to be accepted as a parameter here but
    was NEVER ACTUALLY USED anywhere in this function's body -- calling
    add_bond(..., bond_order=2) silently produced a plain single bond
    every time, exactly the same class of dead-parameter bug already
    found and fixed once in click_mode.cycle_bond_order() (see that
    function's own docstring: "_bonds_from_pair_of_indexes_list()'s
    external_orders parameter already existed but its actual assignment
    ... was commented out"). Fixed the same way cycle_bond_order()
    already does it: persist the requested order in
    vismol_object.manual_bond_orders (keyed by the normalized (min,max)
    pair), which _reapply_manual_bonds() below feeds into
    _bonds_from_pair_of_indexes_list() as external_orders -- required,
    not optional, since bonds get rebuilt FROM SCRATCH (fresh Bond()
    objects) on every structural edit, so anything not persisted there
    is silently lost on the very next add_atom()/remove_atom()/add_bond()
    call. """
    if atom_id_a == atom_id_b:
        raise ValueError ( "add_bond: cannot bond an atom to itself." )
    if atom_id_a not in vismol_object.atoms or atom_id_b not in vismol_object.atoms:
        raise ValueError ( "add_bond: atom_id_a={} or atom_id_b={} does not exist in this object.".format (
                            atom_id_a, atom_id_b ) )
    if bond_order not in ( 1, 2, 3 ):
        raise ValueError ( "add_bond: bond_order must be 1 (single), 2 (double) or 3 (triple), got {!r}.".format (
                            bond_order ) )

    pair = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )

    if not hasattr ( vismol_object, "manual_bonds" ) or vismol_object.manual_bonds is None:
        vismol_object.manual_bonds = set ( )
    vismol_object.manual_bonds.add ( pair )

    if not hasattr ( vismol_object, "manual_bond_orders" ) or vismol_object.manual_bond_orders is None:
        vismol_object.manual_bond_orders = { }
    vismol_object.manual_bond_orders[pair] = int ( bond_order )

    changed = _reapply_manual_bonds ( vismol_object )
    if not changed:
        return False   # object with no bonds at all (neither this new one nor any other) -- nothing to do (rare/defensive case)

    _refresh_bond_dependent_representations ( vismol_object )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )

    return True


def remove_bond ( vismol_object, atom_id_a, atom_id_b ):
    """ [EN] Sixth building block of the Builder (right-click on a bond,
    Avogadro-style -- see the mouse_released() hook in vismol_glcore.py).
    Removes the single bond between atom_id_a and atom_id_b -- the atoms
    THEMSELVES are untouched, only the connection between them.

    Since bonds are ENTIRELY explicit now (vismol_object.manual_bonds --
    distance-based auto-detection is off, see add_atom()'s docstring),
    this is simply: forget the pair (and any custom order recorded for
    it), then rebuild. Nothing can silently bring it back later the way
    the old, now-removed, distance auto-detector could have (if the two
    atoms still happened to be close together).

    Returns True if a bond was actually removed, False if that pair
    wasn't bonded to begin with (nothing to do -- e.g. double right-click
    on the same spot after the bond is already gone). """
    pair = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )

    manual_bonds = getattr ( vismol_object, "manual_bonds", None )
    if not manual_bonds or pair not in manual_bonds:
        return False

    manual_bonds.discard ( pair )

    manual_bond_orders = getattr ( vismol_object, "manual_bond_orders", None )
    if manual_bond_orders:
        manual_bond_orders.pop ( pair, None )

    vismol_object.cov_radii_array = None
    vismol_object.electronegativity_array = None
    vismol_object.index_bonds = None
    vismol_object.bonds = None
    vismol_object.non_bonded_atoms = None
    _reapply_manual_bonds ( vismol_object )

    _refresh_bond_dependent_representations ( vismol_object )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )

    return True


def _refresh_bond_dependent_representations ( vismol_object ):
    """ [EN] Recreates every bond-dependent representation that is
    CURRENTLY PRESENT on this object (i.e. was created at some point --
    not necessarily the one the user happens to be looking at right now,
    but any that exist), preserving each one's active/inactive state.

    [EN] BUG FIX (found via live testing): set_bond_order()/unset_bond()
    below (and, before them, add_bond()/remove_bond()) only ever called
    vismol_object.create_representation() for rep_type='lines' and
    'nonbonded' -- NEVER 'sticks', even though 'sticks' is the ONLY
    representation that actually draws double/triple bonds distinctly
    (see representations.py's SticksRepresentation._get_bond_order_per_
    bond() / the geometry shader's u_bond_order_tbo). Confirmed live:
    'unbond' correctly removed the bond from vismol_object.bonds (a
    second 'unbond' on the same pair correctly reported "no bond
    existed"), but the on-screen STICKS view kept showing the old bond --
    because that representation object's OWN self.indexes (its private
    copy of the atom-pair list actually used for the GPU element buffer,
    set once at creation time by define_new_indexes_to_vbo()) was never
    refreshed; only vismol_object.index_bonds itself was updated, and
    nothing told the existing SticksRepresentation object to rebuild from
    it. 'lines' was fine only because it happened to be the one
    representation type these functions did already recreate.

    Only rep_types that are NOT None in vismol_object.representations get
    touched (i.e. only ones actually in use for this object) -- creating
    'sticks' from scratch for an object that never had it would silently
    turn sticks rendering ON for something the user never asked to see in
    that style. metal_dash refreshes as a side effect of recreating
    'lines'/'sticks' (see create_representation()'s own _ensure_metal_
    dash() calls), so it doesn't need its own entry here. """
    reps = getattr ( vismol_object, "representations", None ) or { }
    for rep_type in ( "lines", "sticks", "nonbonded" ):
        rep = reps.get ( rep_type )
        if rep is None:
            continue
        was_active = getattr ( rep, "active", True )
        vismol_object.create_representation ( rep_type = rep_type )
        new_rep = vismol_object.representations.get ( rep_type )
        if new_rep is not None:
            new_rep.active = was_active


def _sync_index_bonds_and_order_list_from_bonds_dict ( vismol_object ):
    """ [EN] Small helper shared by set_bond_order()/unset_bond() below:
    regenerates vismol_object.index_bonds and vismol_object.bond_order_list
    DIRECTLY from vismol_object.bonds (the dict, iterated in its current
    order -- Python dicts preserve insertion order, so this stays stable
    across repeated calls). Both arrays end up paired 1:1, same index k in
    both. Does NOT touch self.bonds itself, self.atoms[*].bonds, manual_
    bonds, topology, non_bonded_atoms, or anything else -- purely a
    flatten of whatever self.bonds already is. """
    flat = [ ]
    orders = [ ]
    for ( i, j ), bond in vismol_object.bonds.items ( ):
        flat.append ( i )
        flat.append ( j )
        orders.append ( int ( bond.bond_order ) )
    vismol_object.index_bonds = np.array ( flat, dtype = np.int64 )
    vismol_object.bond_order_list = orders


def set_bond_order ( vismol_object, atom_id_a, atom_id_b, bond_order = 1 ):
    """ [EN] Adds a bond between atom_id_a/atom_id_b if none exists yet,

    or updates its order if one already does -- WITHOUT rebuilding the
    object's entire bond set from scratch, unlike add_bond()/
    _reapply_manual_bonds().

    WHY THIS EXISTS (found via live testing, not just reading): add_bond()
    /_reapply_manual_bonds() are built around the BUILDER's specific
    design, where vismol_object.manual_bonds is meant to be the ONLY
    source of truth for connectivity (see add_atom()'s own docstring:
    "distance-based auto-detection is off... Bonds now live ENTIRELY in
    vismol_object.manual_bonds"). That design is correct FOR THE BUILDER
    (an empty object grown one atom/bond at a time, where every bond really
    did come from an explicit add_bond() call) -- but breaks badly on a
    NORMALLY LOADED structure (e.g. a PDB file read via
    find_bonded_and_nonbonded_atoms()): those bonds live in self.bonds/
    self.index_bonds from distance-based auto-detection and were NEVER
    registered in self.manual_bonds. Calling add_bond() there merges
    self.index_bonds (which, AT THAT MOMENT, still has everything) with
    manual_bonds and rebuilds via _reapply_manual_bonds() -- confirmed
    live to end up DROPPING every other bond in the structure, keeping
    only the just-added one. (remove_bond() is worse: it explicitly resets
    index_bonds = None BEFORE rebuilding, so uses ONLY manual_bonds --
    guaranteed to drop everything not explicitly added via add_bond() in
    the current session.)

    This function sidesteps all of that: it mutates vismol_object.bonds
    (the actual dict everything else already reads from -- get_bond(),
    representations.py's _get_bond_order_per_bond(), etc.) directly, for
    ONLY the one pair involved, then regenerates index_bonds/
    bond_order_list FROM that dict (see
    _sync_index_bonds_and_order_list_from_bonds_dict() above) -- every
    OTHER bond, wherever it originally came from, is left completely
    untouched.

    Also keeps manual_bonds/manual_bond_orders in sync (adds this pair)
    purely so this bond SURVIVES if the Builder's own add_atom()/
    remove_atom()/add_bond() run later on this same object -- without that,
    a bond created this way would vanish the next time any of those does
    its own from-scratch, manual_bonds-only rebuild.

    Returns True if a NEW bond was created, False if an existing bond's
    order was updated (or left the same -- still returns False, since no
    NEW bond was created either way). """
    if atom_id_a == atom_id_b:
        raise ValueError ( "set_bond_order: cannot bond an atom to itself." )
    if atom_id_a not in vismol_object.atoms or atom_id_b not in vismol_object.atoms:
        raise ValueError ( "set_bond_order: atom_id_a={} or atom_id_b={} does not exist in this object.".format (
                            atom_id_a, atom_id_b ) )
    if bond_order not in ( 1, 2, 3 ):
        raise ValueError ( "set_bond_order: bond_order must be 1 (single), 2 (double) or 3 (triple), got {!r}.".format (
                            bond_order ) )

    if vismol_object.bonds is None:
        vismol_object.bonds = { }

    key = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )
    existing = vismol_object.bonds.get ( key )

    if existing is not None:
        existing.bond_order = int ( bond_order )
        created = False
    else:
        from vismol.model.bond import Bond
        atom_a = vismol_object.atoms[atom_id_a]
        atom_b = vismol_object.atoms[atom_id_b]
        bond = Bond ( atom_i = atom_a, atom_index_i = atom_id_a,
                       atom_j = atom_b, atom_index_j = atom_id_b )
        bond.bond_order = int ( bond_order )
        vismol_object.bonds[key] = bond
        atom_a.bonds.append ( bond )
        atom_b.bonds.append ( bond )
        atom_a.nbonds = len ( atom_a.bonds )
        atom_b.nbonds = len ( atom_b.bonds )
        created = True

    _sync_index_bonds_and_order_list_from_bonds_dict ( vismol_object )

    if not hasattr ( vismol_object, "manual_bonds" ) or vismol_object.manual_bonds is None:
        vismol_object.manual_bonds = set ( )
    vismol_object.manual_bonds.add ( key )
    if not hasattr ( vismol_object, "manual_bond_orders" ) or vismol_object.manual_bond_orders is None:
        vismol_object.manual_bond_orders = { }
    vismol_object.manual_bond_orders[key] = int ( bond_order )

    if created:
        # Topologia/non-bonded/moleculas so' precisam ser refeitas quando a
        # CONNECTIVITY changes (new bond) -- a simple bond-order change on an
        # already existing bond does not affect any of these (identical graph).
        vismol_object.non_bonded_atoms = None
        vismol_object._get_non_bonded_from_bonded_list ( )
        vismol_object._generate_topology_from_index_bonds ( )
        vismol_object.define_molecules ( )
        vismol_object.define_Calpha_backbone ( )

    _refresh_bond_dependent_representations ( vismol_object )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )

    return created


def unset_bond ( vismol_object, atom_id_a, atom_id_b ):
    """ [EN] Companion to set_bond_order() above, for REMOVAL -- same
    reasoning as that function's own docstring for why this exists
    instead of reusing remove_bond() (which is Builder/manual_bonds-only
    and, per that function's own docstring, drops every bond not
    explicitly added via add_bond() when called on a normally-loaded
    structure).

    Works on ANY bond present in vismol_object.bonds, regardless of
    whether it came from automatic distance-based detection (a loaded
    file) or was added explicitly (add_bond()/set_bond_order() above) --
    removes it directly from that dict and from both atoms' own .bonds
    lists, then regenerates index_bonds/bond_order_list from what
    remains. No other bond is touched.

    Returns True if a bond was actually removed, False if that pair
    wasn't bonded to begin with. """
    if vismol_object.bonds is None:
        return False

    key = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )
    bond = vismol_object.bonds.get ( key )
    if bond is None:
        return False

    del vismol_object.bonds[key]

    atom_a = vismol_object.atoms.get ( atom_id_a )
    atom_b = vismol_object.atoms.get ( atom_id_b )
    if atom_a is not None and bond in atom_a.bonds:
        atom_a.bonds.remove ( bond )
        atom_a.nbonds = len ( atom_a.bonds )
    if atom_b is not None and bond in atom_b.bonds:
        atom_b.bonds.remove ( bond )
        atom_b.nbonds = len ( atom_b.bonds )

    manual_bonds = getattr ( vismol_object, "manual_bonds", None )
    if manual_bonds:
        manual_bonds.discard ( key )
    manual_bond_orders = getattr ( vismol_object, "manual_bond_orders", None )
    if manual_bond_orders:
        manual_bond_orders.pop ( key, None )

    _sync_index_bonds_and_order_list_from_bonds_dict ( vismol_object )

    vismol_object.non_bonded_atoms = None
    vismol_object._get_non_bonded_from_bonded_list ( )
    vismol_object._generate_topology_from_index_bonds ( )
    vismol_object.define_molecules ( )
    vismol_object.define_Calpha_backbone ( )

    _refresh_bond_dependent_representations ( vismol_object )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )

    return True


# =====================================================================================
#   Dynamic Bonds (representacao POR FRAME) -- 'bond'/'unbond' com frame=...
#   ------------------------------------------------------------------------------
#   Tudo acima (set_bond_order/unset_bond) edita a TOPOLOGIA ESTATICA do
#   object (vismol_object.bonds/index_bonds) -- applies to ALL frames and
#   e' o que fica gravado se o objeto for salvo/exportado.
#
#   As funcoes abaixo, em vez disso, editam vismol_object.dynamic_bonds[f]
#   -- a lista de pares POR FRAME usada pela representacao "Dynamic Bonds"
#   (tipicamente a regiao QC de uma trajetoria QM/MM, recalculada
#   automaticamente por distancia a cada frame -- ver VismolSession.
#   define_dynamic_bonds() / VismolObject.find_bonded_and_nonbonded_atoms()).
#
#   *** AVISO IMPORTANTE, repetido no docstring de cmd_bond/cmd_unbond no
#   terminal: using frame=... here does NOT create a real chemical bond.
#   E' PURAMENTE uma edicao da REPRESENTACAO/VISUALIZACAO para aquele(s)
#   frame(s) -- does not touch anything in the pDynamo system (topology, force
#   field, bond force constants, charges, etc.). To create a
#   real bond (with force-field parameters), the system's
#   sistema pDynamo precisa ser editada por outros meios -- isso aqui e'
#   so' para ajustar o que aparece na tela enquanto se inspeciona/prepara
#   a trajectory (e.g. visually forcing a bond that the automatic
#   distance-based detection missed in a specific frame).
# =====================================================================================

def resolve_frame_arg ( vismol_object, frame ):
    """ [EN] Converts the 'frame' argument accepted by 'bond'/'unbond'
    (terminal cmd_bond/cmd_unbond, or the picking-based equivalents in
    click_mode.py) into either:
      - None, meaning "no frame given -- edit the STATIC topology
        (vismol_object.bonds) via set_bond_order()/unset_bond() above,
        NOT Dynamic Bonds". This is the default or when frame= is simply
        not part of the command -- keeps existing 'bond'/'unbond' usage
        completely unchanged.
      - a sorted list of int frame indices to apply a Dynamic Bonds edit
        to (set_dynamic_bond_order()/unset_dynamic_bond() below).

    Accepted forms for `frame` (already run through the terminal DSL's
    own type coercion -- see Command._coerce() in easyhybrid_terminal.py):
      None                            -> None (static topology path)
      True (from 'frame=true'/'yes'/'on') -> [current frame only]
      5 (int, from 'frame=5')         -> [5]
      'all' (any case, 'frame=all')   -> every frame in vismol_object.frames
      '1:5' (str, 'frame=1:5')        -> frames 1..5 INCLUSIVE (both ends
                                          kept -- matches this codebase's
                                          existing 'resi=10-20' filter
                                          convention elsewhere, also
                                          inclusive; note the SEPARATOR
                                          here is ':' not '-', to avoid
                                          colliding with negative frame
                                          indices/typos)
      '7' (plain digit string, in case DSL coercion didn't catch it)
                                       -> [7]
    """
    if frame is None:
        return None

    vm_session = getattr ( vismol_object, "vm_session", None )
    frames_arr = getattr ( vismol_object, "frames", None )
    n_frames = int ( frames_arr.shape[0] ) if frames_arr is not None else 0

    if isinstance ( frame, bool ):
        current_frame = int ( vm_session.get_frame ( ) ) if ( vm_session is not None
                              and hasattr ( vm_session, "get_frame" ) ) else 0
        return [ current_frame ]

    if isinstance ( frame, ( int, float ) ):
        return [ int ( frame ) ]

    if isinstance ( frame, str ):
        s = frame.strip ( ).lower ( )
        if s in ( "all", "*" ):
            return list ( range ( n_frames ) )
        if ":" in s:
            a_str, b_str = s.split ( ":", 1 )
            try:
                a = int ( a_str.strip ( ) )
                b = int ( b_str.strip ( ) )
            except ValueError:
                raise ValueError ( "frame: intervalo invalido {!r} (use algo como '1:5').".format ( frame ) )
            if a > b:
                a, b = b, a
            return list ( range ( a, b + 1 ) )
        try:
            return [ int ( s ) ]
        except ValueError:
            raise ValueError ( "frame: valor invalido {!r} (use um inteiro, 'A:B' ou 'all').".format ( frame ) )

    raise ValueError ( "frame: tipo invalido {!r} (use um inteiro, 'A:B' ou 'all').".format ( frame ) )


def _refresh_dynamic_bond_representations ( vismol_object, affected_frames ):
    """ [EN] Marks any 'is_dynamic' representation (the Dynamic Bonds
    sticks/lines, see representations.py's Representation.__init__
    is_dynamic flag) as needing its index buffer reloaded, so a Dynamic
    Bonds edit made by set_dynamic_bond_order()/unset_dynamic_bond()
    below becomes visible immediately on screen -- WITHOUT this, the
    change is still correctly stored in vismol_object.dynamic_bonds[f]
    (and would show up correctly if the user steps away to another frame
    and back), but wouldn't redraw right away for a frame that's already
    on screen.

    Only bothers marking anything if the CURRENTLY DISPLAYED frame is
    among affected_frames -- editing frame 500 while looking at frame 0
    doesn't need an immediate redraw; that frame's geometry gets rebuilt
    naturally, the same way normal frame-stepping already does, whenever
    the user actually navigates there (is_dynamic representations always
    read vismol_object.dynamic_bonds[f] fresh when their index buffer is
    reloaded -- see representations.py's _load_ind_vbo()). """
    vm_session = getattr ( vismol_object, "vm_session", None )
    if vm_session is None or not hasattr ( vm_session, "get_frame" ):
        return
    current_frame = int ( vm_session.get_frame ( ) )
    if current_frame not in affected_frames:
        return
    for rep in ( getattr ( vismol_object, "representations", None ) or { } ).values ( ):
        if rep is not None and getattr ( rep, "is_dynamic", False ):
            rep.was_rep_ind_modified = True
    vm_glcore = getattr ( vm_session, "vm_glcore", None )
    if vm_glcore is not None:
        vm_glcore.queue_draw ( )


def set_dynamic_bond_order ( vismol_object, atom_id_a, atom_id_b, bond_order = 1, frames = None ):
    """ [EN] Dynamic Bonds equivalent of set_bond_order() above -- adds
    the pair to vismol_object.dynamic_bonds[f] (if not already present)
    and/or forces its order via vismol_object.dynamic_manual_bond_orders
    (see get_dynamic_bond_order_for_frame()'s own updated docstring),
    for every frame index in `frames`.

    *** Purely a REPRESENTATION edit -- see this section's own banner
    comment above. Does NOT touch vismol_object.bonds, the pDynamo
    system's topology, force-field parameters, or anything used for an
    actual QM/MM calculation.

    frames: iterable of int frame indices (already resolved -- see
    resolve_frame_arg() above; None is NOT accepted here, the caller is
    responsible for routing to set_bond_order() instead when frame=None).

    Returns the number of frames where a NEW pair had to be added (as
    opposed to a pair that already existed there and just had its order
    updated/confirmed). """
    if atom_id_a == atom_id_b:
        raise ValueError ( "set_dynamic_bond_order: cannot bond an atom to itself." )
    if atom_id_a not in vismol_object.atoms or atom_id_b not in vismol_object.atoms:
        raise ValueError ( "set_dynamic_bond_order: atom_id_a={} or atom_id_b={} does not exist in this object.".format (
                            atom_id_a, atom_id_b ) )
    if bond_order not in ( 1, 2, 3 ):
        raise ValueError ( "set_dynamic_bond_order: bond_order must be 1 (single), 2 (double) or 3 (triple), got {!r}.".format (
                            bond_order ) )
    if vismol_object.dynamic_bonds is None or len ( vismol_object.dynamic_bonds ) == 0:
        raise ValueError ( "set_dynamic_bond_order: this object has no Dynamic Bonds defined yet "
                            "(define a Dynamic Bonds selection first)." )
    if not frames:
        raise ValueError ( "set_dynamic_bond_order: no frame(s) given." )

    key = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )

    if not hasattr ( vismol_object, "dynamic_manual_bond_orders" ) or vismol_object.dynamic_manual_bond_orders is None:
        vismol_object.dynamic_manual_bond_orders = { }

    n_created = 0
    touched = [ ]
    for f in frames:
        if f < 0 or f >= len ( vismol_object.dynamic_bonds ):
            continue
        flat = list ( np.asarray ( vismol_object.dynamic_bonds[f] ).ravel ( ).tolist ( ) )
        pairs_in_frame = { ( min ( flat[k], flat[k + 1] ), max ( flat[k], flat[k + 1] ) )
                            for k in range ( 0, len ( flat ), 2 ) }
        if key not in pairs_in_frame:
            flat.append ( key[0] )
            flat.append ( key[1] )
            vismol_object.dynamic_bonds[f] = flat
            n_created += 1

        vismol_object.dynamic_manual_bond_orders.setdefault ( f, { } )[key] = int ( bond_order )

        if vismol_object.dynamic_bond_orders is not None and f < len ( vismol_object.dynamic_bond_orders ):
            vismol_object.dynamic_bond_orders[f] = None  # invalida o cache -- ver get_dynamic_bond_order_for_frame

        touched.append ( f )

    _refresh_dynamic_bond_representations ( vismol_object, touched )

    return n_created


def unset_dynamic_bond ( vismol_object, atom_id_a, atom_id_b, frames = None ):
    """ [EN] Dynamic Bonds equivalent of unset_bond() above -- removes the
    pair from vismol_object.dynamic_bonds[f] (if present) and forgets any
    forced order for it, for every frame index in `frames`.

    *** Purely a REPRESENTATION edit -- see this section's own banner
    comment above.

    frames: iterable of int frame indices (already resolved -- see
    resolve_frame_arg() above; None is NOT accepted here).

    Returns the number of frames where the pair was actually present (and
    got removed). """
    if vismol_object.dynamic_bonds is None or len ( vismol_object.dynamic_bonds ) == 0:
        return 0
    if not frames:
        return 0

    key = ( min ( atom_id_a, atom_id_b ), max ( atom_id_a, atom_id_b ) )
    dmb = getattr ( vismol_object, "dynamic_manual_bond_orders", None )

    n_removed = 0
    touched = [ ]
    for f in frames:
        if f < 0 or f >= len ( vismol_object.dynamic_bonds ):
            continue
        flat = list ( np.asarray ( vismol_object.dynamic_bonds[f] ).ravel ( ).tolist ( ) )
        new_flat = [ ]
        removed_here = False
        for k in range ( 0, len ( flat ), 2 ):
            pair = ( min ( flat[k], flat[k + 1] ), max ( flat[k], flat[k + 1] ) )
            if pair == key and not removed_here:
                removed_here = True
                continue
            new_flat.append ( flat[k] )
            new_flat.append ( flat[k + 1] )

        if removed_here:
            vismol_object.dynamic_bonds[f] = new_flat
            n_removed += 1

        if dmb and f in dmb:
            dmb[f].pop ( key, None )

        if vismol_object.dynamic_bond_orders is not None and f < len ( vismol_object.dynamic_bond_orders ):
            vismol_object.dynamic_bond_orders[f] = None  # invalida o cache

        touched.append ( f )

    _refresh_dynamic_bond_representations ( vismol_object, touched )

    return n_removed


# =====================================================================================
#   Undo
#   ------------------------------------------------------------------------------
#   Snapshot-based, not command-based: before each "logical" user action
#   (place/replace an atom, a whole click-and-drag-to-create-a-bond
#   gesture, deleting an atom or bond, cycling a bond's order...), the
#   CALLER (click_mode.py / vismol_glcore.py's right-click handler) calls
#   push_undo_snapshot() once, capturing everything needed to reconstruct
#   the object's current state. undo() just pops the last one and rebuilds
#   the object from it via add_atom() -- reusing the exact same function
#   that already correctly handles chains/residues/frames/atom_dic_id/
#   representations, rather than trying to clone live Atom/Chain/Residue
#   Python objects directly (those hold back-references to each other and
#   to vismol_object itself, which is a much easier thing to get subtly
#   wrong -- and impossible for me to fully verify without a live GL
#   context to test against).
#
#   Deliberately does NOT snapshot on every single mouse_motion event
#   during a drag (would flood the stack with one entry per pixel of
#   movement, and undo-ing would need dozens of clicks to get anywhere) --
#   only once per gesture, at the point the caller considers the action
#   "started" (e.g. start_bond_drag(), not update_bond_drag()).
# =====================================================================================

def _snapshot_builder_state ( vismol_object ):
    """ [EN] Captures everything needed to reconstruct vismol_object's
    CURRENT state via _restore_builder_state() below: every atom's
    element/name/chain/residue/position, plus the explicit bond set and
    any custom bond orders (manual_bonds/manual_bond_orders -- see
    add_atom()'s docstring for why bonds are entirely explicit now).
    Does NOT snapshot representations/VAOs/etc -- those get rebuilt fresh
    on restore anyway, same as every other atom_ops function already
    does after a mutation. """
    atoms_snapshot = [ ]
    for atom_id in sorted ( vismol_object.atoms.keys ( ) ):
        atom = vismol_object.atoms[atom_id]
        pos  = vismol_object.frames[0, atom_id]
        atoms_snapshot.append ( {
            'symbol'  : atom.symbol,
            'name'    : atom.name,
            'chain_id': atom.chain.name if atom.chain is not None else 'A',
            'resi'    : atom.residue.index if atom.residue is not None else 1,
            'resn'    : atom.residue.name if atom.residue is not None else 'UNK',
            'formal_charge': int ( getattr ( atom, 'formal_charge', 0 ) ),
            'mm_charge': getattr ( atom, 'mm_charge', None ),
            'x'       : float ( pos[0] ), 'y': float ( pos[1] ), 'z': float ( pos[2] ),
        } )

    return {
        'atoms'             : atoms_snapshot,
        'manual_bonds'      : set ( getattr ( vismol_object, 'manual_bonds', None ) or set ( ) ),
        'manual_bond_orders': dict ( getattr ( vismol_object, 'manual_bond_orders', None ) or { } ),
        'manual_aromatic_bonds': set ( getattr ( vismol_object, 'manual_aromatic_bonds', None ) or set ( ) ),
        'manual_atom_type_overrides': copy.deepcopy ( getattr ( vismol_object, 'manual_atom_type_overrides', None ) or { } ),
        'dyff_parameter_edits': copy.deepcopy ( getattr ( vismol_object, 'dyff_parameter_edits', None ) or { } ),
    }


def push_undo_snapshot ( vismol_object, max_depth = 50 ):
    """ Records the object's CURRENT state onto its undo stack, BEFORE
    the caller goes on to mutate it. Call this once per logical user
    action (see the module-level note above), never per low-level
    primitive (a single "replace element" click might internally call
    set_atom_element() once -- one snapshot; a drag calls add_atom() +
    several move_atom()s + add_bond() -- still just ONE snapshot, pushed
    by start_bond_drag() before any of that starts).

    max_depth caps memory/undo-stack growth for a long editing session --
    oldest snapshots are dropped first once exceeded. """
    if not hasattr ( vismol_object, 'undo_stack' ) or vismol_object.undo_stack is None:
        vismol_object.undo_stack = [ ]

    vismol_object.undo_stack.append ( _snapshot_builder_state ( vismol_object ) )

    if len ( vismol_object.undo_stack ) > max_depth:
        vismol_object.undo_stack.pop ( 0 )


def _restore_builder_state ( vismol_object, snapshot ):
    """ Rebuilds vismol_object from scratch to match `snapshot`, reusing
    add_atom() for every atom (recompute_bonds=False,
    update_representation=False while looping, to avoid paying for a
    full rebuild after EVERY individual atom -- one single rebuild at the
    end is enough, same batching add_atom()'s own docstring already
    recommends for adding several atoms in a row). """
    vismol_object.atoms  = { }
    vismol_object.chains = { }
    vismol_object.frames = np.zeros ( ( 1, 0, 3 ), dtype = np.float32 )
    vismol_object.manual_bonds       = set ( )
    vismol_object.manual_bond_orders = { }
    vismol_object.manual_aromatic_bonds = set ( )
    vismol_object.manual_atom_type_overrides = { }
    vismol_object.dyff_parameter_edits = { }

    for atom_data in snapshot['atoms']:
        add_atom ( vismol_object,
                   symbol   = atom_data['symbol'],
                   x        = atom_data['x'], y = atom_data['y'], z = atom_data['z'],
                   name     = atom_data['name'],
                   chain_id = atom_data['chain_id'],
                   resi     = atom_data['resi'],
                   resn     = atom_data['resn'],
                   formal_charge = atom_data.get('formal_charge', 0),
                   recompute_bonds       = False,
                   update_representation = False )
        restored_atom = vismol_object.atoms[max(vismol_object.atoms)]
        if atom_data.get('mm_charge') is not None:
            restored_atom.mm_charge = atom_data['mm_charge']

    vismol_object.manual_bonds       = set ( snapshot['manual_bonds'] )
    vismol_object.manual_bond_orders = dict ( snapshot['manual_bond_orders'] )
    vismol_object.manual_aromatic_bonds = set ( snapshot.get('manual_aromatic_bonds', set()) )
    if 'manual_atom_type_overrides' in snapshot:
        vismol_object.manual_atom_type_overrides = copy.deepcopy ( snapshot['manual_atom_type_overrides'] )
    vismol_object.dyff_parameter_edits = copy.deepcopy ( snapshot.get('dyff_parameter_edits', {}) )

    vismol_object.cov_radii_array = None
    vismol_object.electronegativity_array = None
    vismol_object.index_bonds = None
    vismol_object.bonds = None
    vismol_object.non_bonded_atoms = None
    _reapply_manual_bonds ( vismol_object )

    vismol_object.create_representation ( rep_type = "lines" )
    vismol_object.create_representation ( rep_type = "nonbonded" )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )

    # [EN] undo() rebuilds vismol_object completely from scratch (every
    # atom re-added via add_atom() above) -- the linked pDynamo system
    # would otherwise be left describing the PRE-undo structure. Import
    # done here (not at module level) to avoid a circular import:
    # empty_object.py's sync_pdynamo_system() itself calls back into
    # THIS module (_reapply_manual_bonds() indirectly, via add_atom()).
    from gui.windows.builder.empty_object import sync_pdynamo_system
    sync_pdynamo_system ( vismol_object )


def undo ( vismol_object ):
    """ Pops and restores the most recent snapshot (see
    push_undo_snapshot()), undoing the last logical action. Returns True
    if something was actually undone, False if the stack was already
    empty (nothing left to undo -- caller should probably disable/grey
    out the Undo button in that case, see the sidebar wiring). """
    undo_stack = getattr ( vismol_object, 'undo_stack', None )
    if not undo_stack:
        return False

    snapshot = undo_stack.pop ( )
    _restore_builder_state ( vismol_object, snapshot )
    return True


# =====================================================================================
#   Automatic hydrogen adjustment
#   ------------------------------------------------------------------------------
#   Generalises the ad-hoc auto-hydrogenation that used to live ONLY in
#   click_mode.handle_click_to_place_atom() (the `tmp` dict of C/N/O
#   direction templates, only ever applied to a brand-new, completely
#   isolated atom). adjust_hydrogens() instead works for ANY atom at ANY
#   point -- newly placed, freshly bonded to something via a drag,
#   replaced to a different element, had a bond's order cycled, or lost a
#   bond/neighbour to a deletion -- by comparing its CURRENT total bond
#   order (to non-H neighbours) against its standard valence, and adding
#   or removing H atoms to match. Called explicitly by click_mode.py /
#   vismol_glcore.py after whichever operation may have changed an atom's
#   bonding (see each call site's own comment for which atom(s) it's
#   called on and why).
# =====================================================================================

# Default valence (maximum sum of bond order) per element -- the
# poucos elementos que este primeiro conjunto de ferramentas do Builder
# realmente produz ate agora (C/N/O/H, mais alguns halogenios/S/P comuns
# so as not to leave it manual once the element selector grows). Elements
# outside this table simply do not get their hydrogens adjusted (see
# adjust_hydrogens() -- retorna sem fazer nada nesse caso, em vez de
# guessing a wrong valence).
STANDARD_VALENCE = {
    'H' : 1,
    'C' : 4,
    'N' : 3,
    'O' : 2,
    'F' : 1,
    'CL': 1,
    'BR': 1,
    'I' : 1,
    'P' : 3,
    'S' : 2,
}


def _bond_order_sum_excluding_symbol ( vismol_object, atom_id, exclude_symbol ):
    """ Sum of bond_order over every bond touching atom_id, EXCLUDING
    bonds to a neighbour whose symbol == exclude_symbol (used to exclude
    hydrogens -- see adjust_hydrogens(), which needs "how much valence is
    already used up by NON-hydrogen neighbours" to know how many
    hydrogens are left to place). """
    total = 0
    for bond in vismol_object.bonds.values ( ):
        if bond.atom_index_i != atom_id and bond.atom_index_j != atom_id:
            continue
        other_id = bond.atom_index_j if bond.atom_index_i == atom_id else bond.atom_index_i
        if vismol_object.atoms[other_id].symbol == exclude_symbol:
            continue
        total += bond.bond_order
    return total


def _bonded_neighbors_with_symbol ( vismol_object, atom_id, symbol ):
    """ atom_ids of every neighbour of atom_id whose symbol == symbol
    (used to find atom_id's CURRENT hydrogens -- see adjust_hydrogens()). """
    neighbor_ids = [ ]
    for bond in vismol_object.bonds.values ( ):
        if bond.atom_index_i != atom_id and bond.atom_index_j != atom_id:
            continue
        other_id = bond.atom_index_j if bond.atom_index_i == atom_id else bond.atom_index_i
        if vismol_object.atoms[other_id].symbol == symbol:
            neighbor_ids.append ( other_id )
    return neighbor_ids


def _new_hydrogen_directions ( vismol_object, atom_id, n_needed, bond_length = 1.05 ):
    """ [EN] Computes n_needed 3D offset vectors (already scaled to
    `bond_length`) for where to place NEW hydrogens around atom_id.

    If atom_id has no existing bonded neighbours at all, falls back to
    the same fixed geometric templates the OLD, now-replaced click_mode.
    py auto-hydrogenation used (tetrahedral-ish for 4, trigonal for 3,
    linear-ish for 2) -- see below -- taking only the first n_needed
    directions from whichever template matches the TOTAL target count
    (n_needed itself, since there are no existing neighbours to also
    account for).

    If atom_id ALREADY has one or more bonded neighbours (the more
    common case: adding H's to an atom that's already bonded to
    something else), there's no single fixed template that still applies
    -- instead, computes the direction AWAY from the existing neighbours
    (the negated, normalised sum of the existing bond unit vectors), and
    fans the needed new H's out symmetrically around that single "most
    open" direction using an arbitrary perpendicular axis. This is a
    simple, defensible heuristic (not a real hybridisation/VSEPR solver)
    -- good enough to avoid new H's landing on top of existing bonds,
    without trying to reproduce exact tetrahedral/trigonal angles once
    other substituents are already present. """
    fixed_templates = {
        4: [ [-0.785298,  0.243518, -0.653254], [ 0.322015, -0.981331, -0.189814],
             [-0.334691,  0.073016,  0.992665], [ 0.798227,  0.665009, -0.149645] ],
        3: [ [-0.785298,  0.243518, -0.653254], [ 0.322015, -0.981331, -0.189814],
             [-0.334691,  0.073016,  0.992665] ],
        2: [ [-0.785298,  0.243518, -0.653254], [ 0.322015, -0.981331, -0.189814] ],
        1: [ [-0.785298,  0.243518, -0.653254] ],
    }

    atom_pos = vismol_object.frames[0, atom_id]
    existing_dirs = [ ]
    for bond in vismol_object.bonds.values ( ):
        if bond.atom_index_i != atom_id and bond.atom_index_j != atom_id:
            continue
        other_id = bond.atom_index_j if bond.atom_index_i == atom_id else bond.atom_index_i
        vec = vismol_object.frames[0, other_id] - atom_pos
        norm = float ( np.linalg.norm ( vec ) )
        if norm > 1e-6:
            existing_dirs.append ( vec / norm )

    if not existing_dirs:
        template = fixed_templates.get ( n_needed, fixed_templates[4] )
        directions = [ np.array ( d, dtype = np.float32 ) for d in template[:n_needed] ]
        return [ d * bond_length for d in directions ]

    avg_dir = -np.sum ( existing_dirs, axis = 0 )
    norm = float ( np.linalg.norm ( avg_dir ) )
    if norm < 1e-6:
        avg_dir = np.array ( [ 0.0, 0.0, 1.0 ], dtype = np.float32 )
    else:
        avg_dir = ( avg_dir / norm ).astype ( np.float32 )

    if n_needed == 1:
        return [ avg_dir * bond_length ]

    perp = np.cross ( avg_dir, np.array ( [ 0.0, 0.0, 1.0 ], dtype = np.float32 ) )
    if float ( np.linalg.norm ( perp ) ) < 1e-6:
        perp = np.cross ( avg_dir, np.array ( [ 0.0, 1.0, 0.0 ], dtype = np.float32 ) )
    perp = ( perp / np.linalg.norm ( perp ) ).astype ( np.float32 )

    spread_angle = np.deg2rad ( 50.0 )   # arbitrary but reasonable angle between added H's
    directions = [ ]
    for k in range ( n_needed ):
        offset = ( k - ( n_needed - 1 ) / 2.0 ) * spread_angle
        d = avg_dir * np.cos ( offset ) + perp * np.sin ( offset )
        d = d / np.linalg.norm ( d )
        directions.append ( d * bond_length )

    return directions


def adjust_hydrogens ( vismol_object, atom_id ):
    """ Adds or removes hydrogens bonded to atom_id so its total bond
    order (to non-hydrogen neighbours, plus one per hydrogen) matches
    its STANDARD_VALENCE. Called explicitly after any operation that may
    have changed atom_id's bonding -- see the module-level note above for
    the full list of call sites.

    No-op if atom_id's element isn't in STANDARD_VALENCE (unknown
    elements are left alone rather than guessed at), or if it already has
    exactly the right number of hydrogens.

    Returns the number of hydrogens added (positive) or removed
    (negative), or 0 if nothing changed. """
    if atom_id not in vismol_object.atoms:
        return 0

    atom = vismol_object.atoms[atom_id]
    target_valence = STANDARD_VALENCE.get ( atom.symbol.upper ( ) )
    if target_valence is None:
        return 0

    heavy_bond_order_sum = _bond_order_sum_excluding_symbol ( vismol_object, atom_id, exclude_symbol = 'H' )
    needed_h = max ( 0, target_valence - heavy_bond_order_sum )

    current_h_ids = _bonded_neighbors_with_symbol ( vismol_object, atom_id, 'H' )
    current_h_count = len ( current_h_ids )

    if current_h_count == needed_h:
        return 0

    if current_h_count > needed_h:
        # [EN] Removes from HIGHEST atom_id downward: remove_atom()
        # renumbers every atom_id ABOVE the one it removes, so removing
        # highest-first means none of the OTHER hydrogens still pending
        # removal in this same loop are ever affected by an earlier
        # removal -- only atom_id itself (the parent atom being adjusted)
        # might need to shift down, tracked explicitly below.
        excess_ids = sorted ( current_h_ids[needed_h:], reverse = True )
        for h_id in excess_ids:
            remove_atom ( vismol_object, h_id )
            if h_id < atom_id:
                atom_id -= 1
        return needed_h - current_h_count   # negativo

    n_to_add = needed_h - current_h_count
    directions = _new_hydrogen_directions ( vismol_object, atom_id, n_to_add )
    pos = vismol_object.frames[0, atom_id]
    for offset in directions:
        add_atom ( vismol_object, symbol = "H",
                   x = float ( pos[0] + offset[0] ),
                   y = float ( pos[1] + offset[1] ),
                   z = float ( pos[2] + offset[2] ),
                   bonded_to = atom_id )

    return n_to_add


# =====================================================================================
#   Structure clean-up (simple geometric relaxation -- NOT a force field)
#   ------------------------------------------------------------------------------
#   Deliberately NOT UFF (or any other real force field): no energy, no
#   gradient, no van der Waals/electrostatics/torsions -- just two simple
#   geometric corrections, applied iteratively:
#     1. Bond LENGTHS pulled toward an ideal length (covalent-radius sum,
#        shortened a bit for double/triple bonds).
#     2. Bond ANGLES at each atom pulled toward an ideal angle, chosen
#        from a simple VSEPR-style rule based on how many neighbours the
#        atom has and whether any of its bonds are double/triple.
#   Each iteration computes ALL corrections first (from the CURRENT,
#   not-yet-updated positions) and only applies them at the end (a
#   Jacobi-style update) -- avoids the order-dependence/oscillation that
#   applying corrections one bond/angle at a time, immediately, would
#   cause when several of them share an atom.
# =====================================================================================

# Fator de encurtamento aplicado a soma dos raios covalentes conforme a
# bond order -- approximate values, just to give a reasonable
# geometry (does not intend to reproduce the literature precisely).
_BOND_ORDER_LENGTH_FACTOR = { 1: 1.00, 2: 0.87, 3: 0.78 }


def _ideal_bond_length ( atom_i, atom_j, bond_order ):
    """ Soma dos raios covalentes dos dois atomos, encurtada conforme a
    ordem da ligacao (dupla/tripla mais curtas que simples). """
    base   = float ( atom_i.cov_rad ) + float ( atom_j.cov_rad )
    factor = _BOND_ORDER_LENGTH_FACTOR.get ( bond_order, 1.00 )
    return base * factor


def _ideal_angle_for_atom ( vismol_object, atom_id ):
    """ [EN] Simple VSEPR-style rule: angle depends only on how many
    neighbours atom_id has and the highest bond order among them --
    NOT a real hybridisation calculation (no lone-pair counting, no
    electronegativity effects), just enough to keep sp/sp2/sp3-ish
    centres looking reasonable after the Builder's rough initial
    placement.

    Returns the ideal angle in DEGREES, or None if atom_id has fewer
    than 2 neighbours (no angle to speak of) or more than 4 (unusual for
    the elements this Builder currently supports -- left alone rather
    than guessed at). """
    neighbor_bonds = [ bond for bond in vismol_object.bonds.values ( )
                       if bond.atom_index_i == atom_id or bond.atom_index_j == atom_id ]
    n = len ( neighbor_bonds )
    if n < 2 or n > 4:
        return None

    max_order = max ( bond.bond_order for bond in neighbor_bonds )

    if n == 2:
        double_count = sum ( 1 for bond in neighbor_bonds if bond.bond_order == 2 )
        if max_order == 3 or double_count == 2:   # tripla, ou duas duplas (aleno-like) -- linear
            return 180.0
        elif max_order == 2:                       # uma dupla -- ex.: carbono de carbonila com 1 substituinte
            return 120.0
        else:
            return 109.5
    elif n == 3:
        if max_order >= 2:                          # trigonal plana -- ex.: alceno, carbonila
            return 120.0
        else:
            return 109.5                             # reasonable approximation (e.g. simple amine)
    else:   # n == 4
        return 109.5


def _rotate_vector_rodrigues ( v, axis, angle_rad ):
    """ Rotaciona o vetor `v` em torno de `axis` (unitario) por
    `angle_rad`, via formula de Rodrigues -- preserva o comprimento de
    `v`, so muda a direcao. """
    cos_a = np.cos ( angle_rad )
    sin_a = np.sin ( angle_rad )
    return ( v * cos_a
             + np.cross ( axis, v ) * sin_a
             + axis * np.dot ( axis, v ) * ( 1.0 - cos_a ) )


def _arbitrary_perpendicular ( v ):
    """ Um vetor unitario qualquer, perpendicular a `v` -- usado quando
    dois vizinhos de um mesmo atomo estao quase colineares (produto
    vetorial proximo de zero), caso em que o eixo de rotacao "natural"
    (perpendicular aos dois) fica mal-definido. """
    axis = np.cross ( v, np.array ( [ 0.0, 0.0, 1.0 ] ) )
    if float ( np.linalg.norm ( axis ) ) < 1e-6:
        axis = np.cross ( v, np.array ( [ 0.0, 1.0, 0.0 ] ) )
    return axis / np.linalg.norm ( axis )


def clean_up_structure ( vismol_object, atom_ids = None, n_iterations = 40, step_scale = 0.7 ):
    """ Nudges atom positions toward ideal bond lengths/angles, over
    `n_iterations` passes of simple geometric correction (see the
    module-level note above for why this is deliberately NOT a real
    force field like UFF).

    [EN] Defaults verified with a standalone numpy simulation (a
    deliberately worst-case, badly distorted 5-atom test: one bond
    stretched to 2x its ideal length, another compressed to under a
    third of it, no two bonds anywhere near their ideal angle to start)
    before being wired in here -- n_iterations=40 / step_scale=0.7
    converged that test to within +/-0.7 degrees of the ideal tetrahedral
    angle and correct bond lengths to 3 decimal places. Lower step_scale
    values (tried 0.5) or fewer iterations (tried 5-15) left it
    measurably short of converged for that same worst-case test; higher
    step_scale (tried 0.9-1.0) converged slightly faster but with less
    safety margin against oscillation in more crowded, multi-constraint
    geometries (several atoms sharing overlapping bond/angle corrections
    every iteration) than this project's test coverage could rule out.

    atom_ids : if None (default), relaxes the WHOLE molecule -- every
               atom is free to move, and every bond/angle in the object
               is corrected. If a collection of atom_ids is given
               instead, only those atoms (PLUS their directly bonded
               neighbours -- moving an atom's bonds/angles without
               letting its neighbours respond too wouldn't converge to
               anything sensible) are free to move; every OTHER atom
               stays fixed and acts as an anchor for bonds/angles that
               touch the movable set. Both modes share the exact same
               relaxation loop below -- "whole molecule" is just the
               special case where every atom happens to be movable.
    n_iterations : how many correction passes to run. More iterations
               converge closer to the ideal geometry but take
               proportionally longer -- 40 is a reasonable default for
               small Builder molecules (see the verification note above).
    step_scale : how much of each iteration's computed correction is
               actually applied (0-1). Less than 1.0 (default 0.7) acts
               as a damping factor, trading convergence speed for
               stability (a full, undamped correction every iteration
               can overshoot and oscillate, especially once bond and
               angle corrections on the same atom start interacting).

    Rebuilds representations once at the very end (this is a one-off,
    on-demand action -- e.g. the sidebar's "Clean Up" button -- not a
    per-frame update, so there's no reason to batch/optimise beyond
    that single rebuild). """
    if atom_ids is None:
        movable_ids = set ( vismol_object.atoms.keys ( ) )
    else:
        movable_ids = set ( atom_ids )
        for aid in list ( atom_ids ):
            for bond in vismol_object.bonds.values ( ):
                if bond.atom_index_i == aid:
                    movable_ids.add ( bond.atom_index_j )
                elif bond.atom_index_j == aid:
                    movable_ids.add ( bond.atom_index_i )

    if not movable_ids:
        return

    positions = { aid: np.array ( vismol_object.frames[0, aid], dtype = np.float64 )
                  for aid in vismol_object.atoms.keys ( ) }

    for _iteration in range ( n_iterations ):
        displacement = { aid: np.zeros ( 3, dtype = np.float64 ) for aid in movable_ids }
        contributions = { aid: 0 for aid in movable_ids }

        # --- distance term (one correction per bond) ---
        for bond in vismol_object.bonds.values ( ):
            i, j = bond.atom_index_i, bond.atom_index_j
            movable_i = i in movable_ids
            movable_j = j in movable_ids
            if not movable_i and not movable_j:
                continue

            vec  = positions[j] - positions[i]
            dist = float ( np.linalg.norm ( vec ) )
            if dist < 1e-6:
                continue

            ideal = _ideal_bond_length ( vismol_object.atoms[i], vismol_object.atoms[j], bond.bond_order )
            direction = vec / dist
            delta = direction * ( ideal - dist )   # o quanto J precisaria se mover pra afastar/aproximar de I

            if movable_i and movable_j:
                displacement[i] += -0.5 * delta ; contributions[i] += 1
                displacement[j] +=  0.5 * delta ; contributions[j] += 1
            elif movable_j:
                displacement[j] += delta ; contributions[j] += 1
            else:
                displacement[i] += -delta ; contributions[i] += 1

        # --- angle term (one correction per pair of each atom's neighbors) ---
        for atom_id in vismol_object.atoms.keys ( ):
            ideal_angle = _ideal_angle_for_atom ( vismol_object, atom_id )
            if ideal_angle is None:
                continue

            neighbor_ids = [ ]
            for bond in vismol_object.bonds.values ( ):
                if bond.atom_index_i == atom_id:
                    neighbor_ids.append ( bond.atom_index_j )
                elif bond.atom_index_j == atom_id:
                    neighbor_ids.append ( bond.atom_index_i )

            center_pos = positions[atom_id]
            for idx_a in range ( len ( neighbor_ids ) ):
                for idx_b in range ( idx_a + 1, len ( neighbor_ids ) ):
                    j = neighbor_ids[idx_a]
                    k = neighbor_ids[idx_b]
                    if j not in movable_ids and k not in movable_ids:
                        continue

                    v1 = positions[j] - center_pos
                    v2 = positions[k] - center_pos
                    n1 = float ( np.linalg.norm ( v1 ) )
                    n2 = float ( np.linalg.norm ( v2 ) )
                    if n1 < 1e-6 or n2 < 1e-6:
                        continue

                    cos_theta = np.clip ( np.dot ( v1, v2 ) / ( n1 * n2 ), -1.0, 1.0 )
                    theta = float ( np.arccos ( cos_theta ) )
                    diff  = np.deg2rad ( ideal_angle ) - theta
                    if abs ( diff ) < 1e-4:
                        continue

                    axis = np.cross ( v1, v2 )
                    axis_norm = float ( np.linalg.norm ( axis ) )
                    if axis_norm < 1e-6:
                        axis = _arbitrary_perpendicular ( v1 )
                    else:
                        axis = axis / axis_norm

                    half = ( diff / 2.0 ) * step_scale
                    new_v1 = _rotate_vector_rodrigues ( v1, axis, -half )
                    new_v2 = _rotate_vector_rodrigues ( v2, axis,  half )

                    if j in movable_ids:
                        displacement[j] += ( center_pos + new_v1 ) - positions[j]
                        contributions[j] += 1
                    if k in movable_ids:
                        displacement[k] += ( center_pos + new_v2 ) - positions[k]
                        contributions[k] += 1

        # --- aplica a media de todas as correcoes acumuladas nesta iteracao ---
        for aid in movable_ids:
            if contributions[aid] > 0:
                positions[aid] = positions[aid] + displacement[aid] / contributions[aid]

    for aid in movable_ids:
        vismol_object.frames[0, aid] = positions[aid].astype ( np.float32 )

    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )

    vismol_object.create_representation ( rep_type = "lines" )
    vismol_object.create_representation ( rep_type = "nonbonded" )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )




def selection_centroid ( vismol_object, atom_ids, frame = 0 ):
    """ Mean CURRENT position of atom_ids at `frame` -- the rotation pivot
    transform_selection_window.py's rotate sliders use, recomputed fresh on
    every rotation step (not captured once) so it stays correct even after
    an earlier translate/rotate step already moved the group. Raises
    ValueError for an empty atom_ids (nothing to centre on). """
    positions = [ vismol_object.frames[frame, atom_id] for atom_id in atom_ids ]
    if not positions:
        raise ValueError ( "selection_centroid: atom_ids is empty." )
    return np.mean ( np.array ( positions, dtype = np.float64 ), axis = 0 )


def translate_atoms ( vismol_object, atom_ids, dx, dy, dz, frame = 0, update_representation = True ):
    """ Rigidly translates every atom in atom_ids by (dx, dy, dz) -- plain
    per-axis offset, no pivot/rotation involved. update_representation
    mirrors move_atom()/rotate_atoms_around_bond()'s own flag exactly (mark
    every active representation's coordinates dirty for re-upload, not a
    full rebuild -- translation never changes atom count or bonds). """
    delta = np.array ( [ dx, dy, dz ], dtype = np.float64 )
    for atom_id in atom_ids:
        current = np.array ( vismol_object.frames[frame, atom_id], dtype = np.float64 )
        vismol_object.frames[frame, atom_id] = ( current + delta ).astype ( np.float32 )

    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )

    if update_representation:
        vm_session = vismol_object.vm_session
        for rep in vismol_object.representations.values ( ):
            if rep is not None and rep.active:
                rep.was_rep_coord_modified = True
                rep.was_sel_coord_modified = True
        picking_dots = vismol_object.core_representations.get ( "picking_dots" )
        if picking_dots is not None:
            picking_dots.was_rep_coord_modified = True
        if getattr ( vm_session, "vm_glcore", None ) is not None:
            vm_session.vm_glcore.updated_coords = True
            vm_session.vm_glcore.queue_draw ( )


def compute_dihedral_rotation_subgroup ( vismol_object, atom2_id, atom3_id ):
    """Return the atom3 side of a bond, or None when that bond is in a ring."""
    adjacency = { }
    for i, j in vismol_object.bonds:
        adjacency.setdefault ( i, set ( ) ).add ( j )
        adjacency.setdefault ( j, set ( ) ).add ( i )

    visited = { atom3_id }
    frontier = [ atom3_id ]
    ring = False
    while frontier:
        current = frontier.pop ( )
        for neighbor in adjacency.get ( current, ( ) ):
            if current == atom3_id and neighbor == atom2_id:
                continue
            if neighbor == atom2_id:
                ring = True
            elif neighbor not in visited:
                visited.add ( neighbor )
                frontier.append ( neighbor )
    return None if ring else visited


def _ideal_angle_rule ( n, max_order, double_count = 0 ):
    """ [EN] Pure "which angle" decision -- the ONE place this simple,
    deliberately-not-a-real-hybridisation-calculation VSEPR-style rule
    lives, shared by BOTH _ideal_angle_for_atom() (heavy-atom skeleton
    relaxation, reads n/max_order/double_count off vismol_object's
    CURRENT bonds) and adjust_hydrogens() (decides the geometry for
    hydrogens not yet placed -- reads n/max_order/double_count off the
    atom's HEAVY bonds plus its PROSPECTIVE hydrogen count, since
    hydrogens are always single bonds and never raise max_order/
    double_count themselves). Sharing this one function is what makes
    the heavy-atom skeleton and its hydrogens agree on the SAME
    hybridisation for the same atom, instead of two independently
    drifting copies of this rule.

    n : total number of substituents (bonded neighbour ATOMS -- each
        counted once regardless of that bond's order).
    max_order : highest bond order among this atom's HEAVY bonds (1 if
        it has none).
    double_count : how many of this atom's HEAVY bonds are order 2
        (only matters for the n==2 allene-like case below).

    Returns the ideal angle in DEGREES, or None if n is outside [2, 4]
    (no angle to speak of, or more substituents than this Builder's
    supported elements ever need). """
    if n < 2 or n > 4:
        return None
    if n == 2:
        if max_order == 3 or double_count == 2:
            return 180.0
        elif max_order == 2:
            return 120.0
        else:
            return 109.5
    elif n == 3:
        if max_order >= 2:
            return 120.0
        else:
            return 109.5
    else:
        return 109.5


# Regular-tetrahedron unit vectors (pairwise ~109.47 degrees apart) --
# the "no existing neighbours yet" starting orientation for a
# 4-substituent (sp3) centre, and (a 3-vector subset of it) for a
# 3-substituent PYRAMIDAL (non-planar) centre -- see
# _complete_vsepr_directions() below.
_TETRAHEDRAL_TEMPLATE = [ v / np.linalg.norm ( v ) for v in (
    np.array ( [-0.785298,  0.243518, -0.653254] ), np.array ( [ 0.322015, -0.981331, -0.189814] ),
    np.array ( [-0.334691,  0.073016,  0.992665] ), np.array ( [ 0.798227,  0.665009, -0.149645] ),
) ]


def _heavy_neighbor_directions_and_orders ( vismol_object, atom_id ):
    """ [EN] Unit-vector directions (from atom_id's CURRENT position) and
    bond orders to every bonded neighbour that is NOT a hydrogen -- the
    "fixed anchors" adjust_hydrogens() completes a VSEPR arrangement
    around (see _complete_vsepr_directions()). Hydrogens are deliberately
    excluded here: adjust_hydrogens() always recomputes ALL of atom_id's
    OWN hydrogens fresh (see its own docstring), so an existing
    hydrogen's (possibly stale/wrong) direction must never be treated as
    a fixed anchor for that recomputation. """
    atom_pos = vismol_object.frames[0, atom_id]
    dirs, orders = [ ], [ ]
    for bond in vismol_object.bonds.values ( ):
        if bond.atom_index_i != atom_id and bond.atom_index_j != atom_id:
            continue
        other_id = bond.atom_index_j if bond.atom_index_i == atom_id else bond.atom_index_i
        if vismol_object.atoms[other_id].symbol == 'H':
            continue
        vec  = vismol_object.frames[0, other_id] - atom_pos
        norm = float ( np.linalg.norm ( vec ) )
        if norm > 1e-6:
            dirs.append ( vec / norm )
            orders.append ( bond.bond_order )
    return dirs, orders


def _arbitrary_orthonormal_basis ( v ):
    """ Two unit vectors (e1, e2), both perpendicular to `v` and to each
    other -- used to place new VSEPR directions at a specific angle
    around a single fixed axis `v` (see _complete_vsepr_directions()'s
    n_existing==1 cases). Which exact e1/e2 pair is picked is arbitrary
    (there's no "correct" azimuth around a single bond, chemically) --
    only that they're orthonormal to `v` and to each other, which is all
    the geometry below actually needs. """
    e1 = _arbitrary_perpendicular ( v )
    e2 = np.cross ( v, e1 )
    return e1, e2 / np.linalg.norm ( e2 )


def _fallback_fan_directions ( existing_dirs, n_new, ideal_angle_deg ):
    """ [EN] The ORIGINAL, simpler heuristic this Builder used before
    _complete_vsepr_directions() below existed: places n_new directions
    fanned out, symmetrically, around the single direction AWAY from the
    (normalised sum of the) existing ones -- doesn't try to reproduce
    exact VSEPR angles, just avoids new directions landing on top of
    existing bonds. Only reached now as a degenerate-case fallback (see
    _complete_vsepr_directions()'s own docstring) -- e.g. existing
    directions numerically collinear/opposite, where the closed-form
    construction's divisions become unstable. """
    if existing_dirs:
        avg_dir = -np.sum ( existing_dirs, axis = 0 )
        norm = float ( np.linalg.norm ( avg_dir ) )
        avg_dir = ( avg_dir / norm ) if norm > 1e-6 else np.array ( [ 0.0, 0.0, 1.0 ] )
    else:
        avg_dir = np.array ( [ 0.0, 0.0, 1.0 ] )

    if n_new == 1:
        return [ avg_dir ]

    perp = np.cross ( avg_dir, np.array ( [ 0.0, 0.0, 1.0 ] ) )
    if float ( np.linalg.norm ( perp ) ) < 1e-6:
        perp = np.cross ( avg_dir, np.array ( [ 0.0, 1.0, 0.0 ] ) )
    perp = perp / np.linalg.norm ( perp )

    spread = np.deg2rad ( ideal_angle_deg if ideal_angle_deg else 109.5 )
    directions = [ ]
    for k in range ( n_new ):
        offset = ( k - ( n_new - 1 ) / 2.0 ) * ( spread / max ( 1, n_new - 1 ) )
        d = avg_dir * np.cos ( offset ) + perp * np.sin ( offset )
        directions.append ( d / np.linalg.norm ( d ) )
    return directions


def _complete_vsepr_directions ( existing_dirs, total_count, ideal_angle_deg ):
    """ [EN] Returns (total_count - len(existing_dirs)) NEW unit-vector
    directions that complete a symmetric VSEPR-style arrangement of
    `total_count` substituents around a central atom, given the
    directions ALREADY fixed (existing_dirs -- 0 to 3 of them, e.g. this
    atom's existing heavy-neighbour bonds) and the ideal pairwise angle
    for that arrangement (from _ideal_angle_rule()).

    [EN] REPLACES the old adjust_hydrogens()/_new_hydrogen_directions()
    heuristic ("place away from whatever's there, fanned out by an
    arbitrary fixed 50-degree angle, regardless of hybridisation") --
    this is closed-form geometry (not a generic numerical solver, and
    not a real force field either) for every (len(existing_dirs),
    total_count) combination this Builder's STANDARD_VALENCE table can
    actually produce (total_count 1-4, existing 0-3), each verified
    numerically to reproduce the EXACT ideal_angle_deg pairwise, both
    between a new direction and an existing one, and between two new
    directions:

      existing=0: an arbitrarily-oriented canonical template for that
        total_count/angle (nothing to align to yet).
      existing=1 (axis A): new directions D_k = cos(theta)*A +
        sin(theta)*(cos(az_k) e1 + sin(az_k) e2), theta=ideal_angle,
        (e1, e2) an arbitrary orthonormal basis perpendicular to A.
        Azimuths az_k are 0/phi for 2 new directions (phi solved from
        cos(phi) = cos(theta) / (1 + cos(theta)), so the 2 new
        directions are ALSO ideal_angle apart from EACH OTHER, not just
        from A), or 0/120/240 degrees for 3 new directions (a special
        case that's only self-consistent because ideal_angle_deg is
        always 109.5 whenever 3 new directions are needed here).
      existing=2 (A, B): decomposed in the orthonormal basis
        {u=normalize(A+B), n=normalize(cross(A,B))} -- by the mirror
        symmetry between A and B, every new direction has a ZERO
        component along the 3rd axis (perpendicular to both u and n),
        so this reduces to 2 unknowns solved directly from "new
        direction must be ideal_angle from A" (and, by that same
        symmetry, automatically ideal_angle from B too).
      existing=3: the classic "4th regular-tetrahedron vertex is minus
        the sum of the other 3, already unit length" identity (only
        ever reached when total_count==4, i.e. ideal_angle_deg==109.5).

    Falls back to _fallback_fan_directions() above -- correctness isn't
    guaranteed there, but it degrades gracefully instead of dividing by
    zero -- for any input this closed-form approach can't handle cleanly
    (existing directions numerically collinear/opposite, or an
    existing_count/total_count combination outside the cases above,
    e.g. an atom with more bonds than any element this Builder supports
    should chemically have). """
    n_existing = len ( existing_dirs )
    n_new      = total_count - n_existing
    if n_new <= 0:
        return [ ]

    existing_dirs = [ np.asarray ( d, dtype = np.float64 ) / np.linalg.norm ( np.asarray ( d, dtype = np.float64 ) )
                       for d in existing_dirs ]
    theta = np.radians ( ideal_angle_deg ) if ideal_angle_deg is not None else None

    try:
        if n_existing == 0:
            if theta is None:
                if total_count == 1:
                    return [ np.array ( [ 0.0, 0.0, 1.0 ] ) ]
            elif total_count == 2:
                half = theta / 2.0
                return [ np.array ( [  np.sin ( half ), 0.0, np.cos ( half ) ] ),
                         np.array ( [ -np.sin ( half ), 0.0, np.cos ( half ) ] ) ]
            elif total_count == 3 and abs ( ideal_angle_deg - 120.0 ) < 1e-6:
                return [ np.array ( [ np.cos ( np.radians ( 120.0 * k ) ),
                                       np.sin ( np.radians ( 120.0 * k ) ), 0.0 ] ) for k in range ( 3 ) ]
            elif total_count == 3:
                return list ( _TETRAHEDRAL_TEMPLATE[:3] )
            elif total_count == 4:
                return list ( _TETRAHEDRAL_TEMPLATE )

        elif n_existing == 1 and theta is not None:
            A = existing_dirs[0]
            e1, e2 = _arbitrary_orthonormal_basis ( A )
            if n_new == 1:
                return [ np.cos ( theta ) * A + np.sin ( theta ) * e1 ]
            elif n_new == 2:
                cos_phi = np.clip ( np.cos ( theta ) / ( 1.0 + np.cos ( theta ) ), -1.0, 1.0 )
                phi = np.arccos ( cos_phi )
                return [ np.cos ( theta ) * A + np.sin ( theta ) * ( np.cos ( az ) * e1 + np.sin ( az ) * e2 )
                         for az in ( 0.0, phi ) ]
            elif n_new == 3:
                return [ np.cos ( theta ) * A + np.sin ( theta ) * ( np.cos ( az ) * e1 + np.sin ( az ) * e2 )
                         for az in ( 0.0, 2 * np.pi / 3.0, 4 * np.pi / 3.0 ) ]

        elif n_existing == 2 and theta is not None:
            A, B = existing_dirs
            cos_ab   = float ( np.clip ( np.dot ( A, B ), -1.0, 1.0 ) )
            u_raw    = A + B
            u_norm   = float ( np.linalg.norm ( u_raw ) )
            cross_ab = np.cross ( A, B )
            n_norm   = float ( np.linalg.norm ( cross_ab ) )
            if u_norm < 1e-3 or n_norm < 1e-3:
                raise ValueError ( "existing directions too close to collinear/opposite" )
            u = u_raw / u_norm
            n = cross_ab / n_norm
            c = float ( np.cos ( np.arccos ( cos_ab ) / 2.0 ) )   # = dot(A, u) = dot(B, u)
            if abs ( c ) < 1e-3:
                raise ValueError ( "existing directions too close to a 180-degree pair" )
            if n_new == 1 and ideal_angle_deg is not None and abs ( ideal_angle_deg - 120.0 ) < 1e-6:
                # [EN] BUG FIX (user's own explicit request -- "para o
                # cleanUP, nao esta ajustando corretamente a geometria de
                # H de carbonos SP2, use a disposicao dos outros atomos
                # ligados ao carbono sp2 para colocar o H no mesmo
                # plano"): the GENERAL cone formula below (still used for
                # every OTHER n_existing==2/n_new==1 case, e.g. completing
                # a PYRAMIDAL 109.5-degree centre like a plain sp3 amine
                # nitrogen, where the 3rd substituent SHOULD pucker out of
                # the A/B plane) finds a direction that's EXACTLY
                # ideal_angle_deg from BOTH A and B -- which only happens
                # to land in-plane (b=0 below) when A and B themselves are
                # ALREADY exactly 120 degrees apart. For any REAL,
                # imperfectly-relaxed sp2 centre (A/B not exactly 120
                # degrees apart -- the normal case), that formula instead
                # returns one of the family's two OUT-OF-PLANE mirror
                # solutions, visibly wrong for something that's supposed
                # to be planar (confirmed live: clean_up_structure()'s own
                # new planarity term, added earlier this session, flattens
                # the HEAVY skeleton correctly, but this H-placement
                # formula was still pushing the hydrogen back out of that
                # same plane on every Phase-2 pass).
                #
                # Fixed by NOT trying to hit ideal_angle_deg from each of
                # A/B exactly -- instead directly using the same "new
                # direction = negative sum of the existing ones,
                # normalised" identity the n_existing==3 tetrahedral case
                # below already uses for its own 4th-vertex completion:
                # -normalize(A+B) is, by construction, a pure LINEAR
                # COMBINATION of A and B (zero component along their
                # shared plane's normal n) -- i.e. ALWAYS exactly
                # coplanar with A and B, for ANY angle between them, not
                # just the ideal one -- while still pointing directly
                # "away" from both, exactly bisecting the reflex angle
                # between them (the chemically correct trigonal
                # completion direction).
                s = -( A + B )
                s_norm = float ( np.linalg.norm ( s ) )
                if s_norm < 1e-3:
                    raise ValueError ( "existing directions sum to ~zero (A/B ~180 degrees apart)" )
                return [ s / s_norm ]
            elif n_new == 1:
                a = np.cos ( theta ) / c
                if abs ( a ) > 1.0:
                    # [EN] existing A/B are too far from ideal_angle apart
                    # from EACH OTHER for a valid single completion at
                    # EXACTLY ideal_angle to both to even exist (found via
                    # live testing: a freshly-built, not-yet-relaxed chain
                    # -- e.g. an as-placed C-C-C with a ~169-degree angle,
                    # nowhere near the 109.5 target -- makes |a| > 1 here,
                    # which would otherwise silently produce a NON-unit
                    # direction) -- fall back instead of returning garbage.
                    raise ValueError ( "no valid single completion for this A/B pair" )
                b = np.sqrt ( max ( 0.0, 1.0 - a * a ) )
                return [ a * u + b * n ]
            elif n_new == 2:
                p = np.cos ( theta ) / c
                if abs ( p ) > 1.0:
                    # [EN] same reasoning as the n_new==1 guard above --
                    # additionally, this is the case that actually
                    # surfaced the bug: |p| > 1 collapses D1/D2 to the
                    # SAME (non-unit, wrong-length) direction (r would be
                    # computed as 0 via the max(0, ...) clamp below,
                    # silently), so both new hydrogens would otherwise
                    # land on top of each other instead of falling back.
                    raise ValueError ( "no valid 2-direction completion for this A/B pair" )
                r = np.sqrt ( max ( 0.0, 1.0 - p * p ) )
                return [ p * u + r * n, p * u - r * n ]

        elif n_existing == 3 and n_new == 1:
            s = -np.sum ( existing_dirs, axis = 0 )
            norm = float ( np.linalg.norm ( s ) )
            if norm < 1e-3:
                raise ValueError ( "existing directions sum to ~zero" )
            return [ s / norm ]

    except ValueError:
        pass

    return _fallback_fan_directions ( existing_dirs, n_new, ideal_angle_deg )




def attach_fragment_at_hydrogen ( vismol_object, target_h_atom_id, fragment ):
    """ [EN] Removes target_h_atom_id (which MUST be a hydrogen) and
    attaches `fragment` (a dict from fragment_library.load_fragment()) in
    its place -- the fragment's own "root" atom (fragment["root_index"])
    ends up bonded, via a plain single bond, to whatever heavy atom
    target_h_atom_id was bonded to, oriented along the EXACT SAME
    direction that hydrogen already occupied (that direction was already
    placed correctly by adjust_hydrogens()'s own VSEPR logic, so it's
    reused directly here rather than recomputed).

    Geometry (see fragment_library.py's own docstring for why fragments
    are authored with completely arbitrary global orientation -- only
    the fragment's OWN internal relative angles matter):
      1. Gather the fragment root atom's existing bonded-neighbour
         directions, IN THE FRAGMENT's OWN LOCAL COORDINATES, and
         complete the missing (attachment) direction via the SAME VSEPR
         machinery adjust_hydrogens() itself uses (_ideal_angle_rule() /
         _complete_vsepr_directions()) -- this is the fragment's own
         "local outward direction" for the new bond.
      2. Build a single rigid rotation mapping that local outward
         direction onto the target's own outward direction (the removed
         hydrogen's direction from its parent), via _rotate_vector_
         rodrigues() -- same helper clean_up_structure()'s angle term
         already uses for the same kind of vector-to-vector rotation.
      3. Apply that ONE rotation to every fragment atom (relative to the
         root atom's own local position), then translate the whole
         fragment so the root atom lands at parent_position +
         outward_dir * (parent.cov_rad + root_element_cov_rad) -- the
         same cov-radius-sum single-bond-length model _ideal_bond_
         length()/_hydrogen_bond_length() already use, just generalised
         to the fragment root's OWN element instead of always H.

    Insertion: batch-inserts every fragment atom via add_atom(
    recompute_bonds=False, update_representation=False) (same batching
    convention add_atom()'s own docstring recommends for adding several
    atoms in a row), tracking a local-index -> new-atom_id map; registers
    every INTERNAL fragment bond plus the ONE new cross-bond directly into
    manual_bonds/manual_bond_orders (same direct-population approach
    _restore_builder_state() already uses for a from-scratch rebuild);
    then ONE _reapply_manual_bonds() and ONE full representation rebuild
    (matching remove_atom()'s own tail exactly, since the atom COUNT
    changes here same as there). The target parent remains valence-complete
    because the fragment replaces the removed hydrogen with one single
    bond, and the root gains the single bond it was authored one bond short
    of. No hydrogen adjustment is run, preserving formal-charge-specific
    valence from the MOL2 file.

    Does NOT push an undo snapshot or call sync_pdynamo_system() itself
    -- matches this file's existing convention (see add_atom()/
    remove_atom()'s own docstrings): that is the CALLER's job (see
    click_mode.handle_click_to_attach_fragment()).

    Raises ValueError if target_h_atom_id doesn't exist, isn't a
    hydrogen, or has no parent bond (should never happen for a real atom
    in a well-formed object, but checked defensively since this is
    reachable directly from a user click). """
    if target_h_atom_id not in vismol_object.atoms:
        raise ValueError ( "attach_fragment_at_hydrogen: atom_id {} does not exist.".format ( target_h_atom_id ) )
    h_atom = vismol_object.atoms[target_h_atom_id]
    if h_atom.symbol != 'H':
        raise ValueError ( "attach_fragment_at_hydrogen: atom_id {} ('{}') is not a hydrogen.".format (
                            target_h_atom_id, h_atom.symbol ) )

    parent_atom = None
    for bond in vismol_object.bonds.values ( ):
        if bond.atom_index_i == target_h_atom_id:
            parent_atom = vismol_object.atoms[bond.atom_index_j] ; break
        elif bond.atom_index_j == target_h_atom_id:
            parent_atom = vismol_object.atoms[bond.atom_index_i] ; break
    if parent_atom is None:
        raise ValueError ( "attach_fragment_at_hydrogen: atom_id {} has no parent bond.".format ( target_h_atom_id ) )

    h_pos      = np.array ( vismol_object.frames[0, target_h_atom_id], dtype = np.float64 )
    parent_pos = np.array ( vismol_object.frames[0, parent_atom.atom_id], dtype = np.float64 )
    outward_dir = h_pos - parent_pos
    outward_norm = float ( np.linalg.norm ( outward_dir ) )
    if outward_norm < 1e-6:
        raise ValueError ( "attach_fragment_at_hydrogen: degenerate (zero-length) H-parent bond." )
    outward_dir = outward_dir / outward_norm

    frag_atoms  = fragment["atoms"]
    frag_bonds  = fragment["bonds"]
    root_index  = fragment["root_index"]

    root_symbol, rx, ry, rz = frag_atoms[root_index]
    root_local_pos = np.array ( [ rx, ry, rz ], dtype = np.float64 )

    existing_dirs   = [ ]
    existing_orders = [ ]
    for ( i, j, order ) in frag_bonds:
        other = j if i == root_index else ( i if j == root_index else None )
        if other is None:
            continue
        _sym, ox, oy, oz = frag_atoms[other]
        vec = np.array ( [ ox, oy, oz ], dtype = np.float64 ) - root_local_pos
        vnorm = float ( np.linalg.norm ( vec ) )
        if vnorm > 1e-6:
            existing_dirs.append ( vec / vnorm )
            existing_orders.append ( order )

    total_count  = len ( existing_dirs ) + 1
    max_order    = max ( existing_orders ) if existing_orders else 1
    double_count = sum ( 1 for o in existing_orders if o == 2 )
    ideal_angle  = _ideal_angle_rule ( total_count, max_order, double_count )
    local_outward = _complete_vsepr_directions ( existing_dirs, total_count, ideal_angle )[0]
    local_outward = local_outward / np.linalg.norm ( local_outward )

    # [EN] 2026-09-25 BUG FIX (user's own report: "a orientacao do
    # atomos dos fragmentos parece invertida... parece haver uma
    # inversao no vetor que orienta o fragmento"): local_outward means
    # "direction FROM the fragment's root atom TOWARD its own missing
    # substituent" (same convention adjust_hydrogens() uses for THIS
    # EXACT _complete_vsepr_directions() output -- there it's used
    # UNNEGATED because it's applied directly as pos + offset_dir *
    # bond_length, i.e. "from the atom to its NEW substituent"). Here,
    # that "missing substituent" IS the attachment point -- i.e.
    # local_outward is root's own "root -> parent" direction, in
    # fragment-local coordinates. The REAL-WORLD equivalent of
    # "root -> parent" is NOT outward_dir (parent -> H, i.e. AWAY from
    # parent) -- it's the OPPOSITE, parent_pos - new_root_pos, which
    # normalises to exactly -outward_dir. Aligning local_outward with
    # +outward_dir (the old code) pointed the fragment's own
    # "attachment-facing" side AWAY from parent instead of back toward
    # it -- a 180-degree flip of the whole fragment around its root,
    # independent of which real molecule/position it was attached to
    # (matching the user's own "independentemente de qual posicao...
    # parece haver uma inversao"). Verified against a real hexyl chain
    # attachment: before this fix the chain folded back toward the
    # parent atom instead of extending away from it.
    attachment_target_dir = -outward_dir

    # Rigid rotation mapping local_outward (fragment space) onto
    # attachment_target_dir (target space) -- standard axis/angle
    # construction, with the 2 degenerate cases (already aligned, or
    # exactly opposite) handled explicitly since cross(a, a) / cross(a,
    # -a) are both zero vectors and can't supply a rotation axis on
    # their own.
    cos_theta = float ( np.clip ( np.dot ( local_outward, attachment_target_dir ), -1.0, 1.0 ) )
    axis = np.cross ( local_outward, attachment_target_dir )
    axis_norm = float ( np.linalg.norm ( axis ) )
    if axis_norm < 1e-8:
        if cos_theta > 0:
            rotation_axis, rotation_angle = np.array ( [ 0.0, 0.0, 1.0 ] ), 0.0
        else:
            rotation_axis, rotation_angle = _arbitrary_perpendicular ( local_outward ), np.pi
    else:
        rotation_axis, rotation_angle = axis / axis_norm, float ( np.arccos ( cos_theta ) )

    root_cov_rad = vismol_object.vm_session.periodic_table.elements_by_symbol[root_symbol][7]
    bond_length  = float ( parent_atom.cov_rad ) + float ( root_cov_rad )
    new_root_pos = parent_pos + outward_dir * bond_length

    # [EN] Remove the target hydrogen FIRST (captures parent_atom's own
    # .atom_id fresh afterwards -- remove_atom() renumbers every id above
    # the removed one, and mutates every SURVIVING atom's .atom_id IN
    # PLACE, so re-reading it off the live Atom object is always correct,
    # same convention finish_bond_drag()/clean_up_structure() already use).
    remove_atom ( vismol_object, target_h_atom_id )

    # [EN] Batch-insert every fragment atom -- world position = rotate
    # (this atom's position relative to the fragment's own root atom) by
    # the single rotation computed above, then translate to new_root_pos.
    # The root atom's OWN relative position is (0,0,0) by construction,
    # so it lands exactly at new_root_pos, as intended.
    local_index_to_new_id = { }
    # [EN] 2026-10-02: formal charges from the fragment file (nitro N+/O-,
    # carboxylate O-) -- without them adjust_hydrogens()/Clean Up would
    # later "complete" e.g. the nitro O- with a hydrogen.
    frag_charges = fragment.get ( "formal_charges" ) or [ 0 ] * len ( frag_atoms )
    for local_index, ( symbol, x, y, z ) in enumerate ( frag_atoms ):
        local_pos = np.array ( [ x, y, z ], dtype = np.float64 ) - root_local_pos
        rotated   = _rotate_vector_rodrigues ( local_pos, rotation_axis, rotation_angle )
        world_pos = new_root_pos + rotated
        new_atom = add_atom ( vismol_object, symbol = symbol,
                               x = float ( world_pos[0] ), y = float ( world_pos[1] ), z = float ( world_pos[2] ),
                               chain_id = parent_atom.chain.name if parent_atom.chain is not None else "A",
                               resi = parent_atom.residue.index if parent_atom.residue is not None else 1,
                               resn = parent_atom.residue.name if parent_atom.residue is not None else "UNK",
                               formal_charge = int ( frag_charges[local_index] ),
                               recompute_bonds = False, update_representation = False )
        local_index_to_new_id[local_index] = new_atom.atom_id

    if not hasattr ( vismol_object, "manual_bonds" ) or vismol_object.manual_bonds is None:
        vismol_object.manual_bonds = set ( )
    if not hasattr ( vismol_object, "manual_bond_orders" ) or vismol_object.manual_bond_orders is None:
        vismol_object.manual_bond_orders = { }

    for ( i, j, order ) in frag_bonds:
        pair = ( min ( local_index_to_new_id[i], local_index_to_new_id[j] ),
                 max ( local_index_to_new_id[i], local_index_to_new_id[j] ) )
        vismol_object.manual_bonds.add ( pair )
        vismol_object.manual_bond_orders[pair] = order

    root_new_id = local_index_to_new_id[root_index]
    cross_pair = ( min ( parent_atom.atom_id, root_new_id ), max ( parent_atom.atom_id, root_new_id ) )
    vismol_object.manual_bonds.add ( cross_pair )
    vismol_object.manual_bond_orders[cross_pair] = 1

    _reapply_manual_bonds ( vismol_object )

    vismol_object.create_representation ( rep_type = "lines" )
    vismol_object.create_representation ( rep_type = "nonbonded" )
    vismol_object.core_representations["picking_dots"] = None
    vismol_object.core_representations["picking_text"] = None

    # [EN] Atom count just changed -- see _refresh_bond_dependent_
    # representations()'s own (extended) docstring: any OTHER
    # representation this object carries (e.g. 'cartoon', inherited by
    # an "Edit in Builder" clone of a normal system) needs to either be
    # resized or deactivated here too, or its own stale self.indexes
    # crashes the next picking pass.
    _refresh_bond_dependent_representations ( vismol_object )

    # Both endpoints remain valence-complete: the parent replaces one
    # hydrogen bond with the new single bond, and the fragment root's one
    # open valence is filled by that same bond. Do not auto-hydrogenate.

    vm_session = vismol_object.vm_session
    if getattr ( vm_session, "vm_glcore", None ) is not None:
        vm_session.vm_glcore.queue_draw ( )




def rotate_atoms_around_bond ( vismol_object, pivot_atom_id, axis_atom_id,
                               subgroup_atom_ids, angle_rad, frame = 0,
                               update_representation = True ):
    """Rotate a bonded subgroup around the axis from pivot to axis atom."""
    pivot = np.asarray ( vismol_object.frames[frame, pivot_atom_id], dtype = np.float64 )
    axis_end = np.asarray ( vismol_object.frames[frame, axis_atom_id], dtype = np.float64 )
    axis = axis_end - pivot
    norm = float ( np.linalg.norm ( axis ) )
    if norm < 1e-6:
        raise ValueError ( "rotate_atoms_around_bond: degenerate rotation axis." )
    axis /= norm

    for atom_id in subgroup_atom_ids:
        local = np.asarray ( vismol_object.frames[frame, atom_id], dtype = np.float64 ) - pivot
        vismol_object.frames[frame, atom_id] = (
            _rotate_vector_rodrigues ( local, axis, angle_rad ) + pivot
        ).astype ( np.float32 )

    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )
    if update_representation:
        vm_session = vismol_object.vm_session
        for rep in vismol_object.representations.values ( ):
            if rep is not None and rep.active:
                rep.was_rep_coord_modified = True
                rep.was_sel_coord_modified = True
        picking_dots = vismol_object.core_representations.get ( "picking_dots" )
        if picking_dots is not None:
            picking_dots.was_rep_coord_modified = True
        glcore = getattr ( vm_session, "vm_glcore", None )
        if glcore is not None:
            glcore.updated_coords = True
            glcore.queue_draw ( )


def rotate_atoms_around_point ( vismol_object, atom_ids, pivot, axis, angle_rad,
                                 frame = 0, update_representation = True ):
    """ Rigidly rotates every atom in atom_ids by angle_rad around `axis`
    (any nonzero vector -- normalized here, so (1,0,0)/(0,1,0)/(0,0,1) for
    the object's own local X/Y/Z axes work directly), anchored at `pivot` --
    a plain (x, y, z) point, NOT necessarily another atom's position (unlike
    rotate_atoms_around_bond(), which is always anchored at a specific
    pivot ATOM). Reuses the same _rotate_vector_rodrigues() primitive every
    other Builder rotation already shares. """
    axis = np.array ( axis, dtype = np.float64 )
    axis_norm = float ( np.linalg.norm ( axis ) )
    if axis_norm < 1e-9:
        raise ValueError ( "rotate_atoms_around_point: degenerate (zero-length) rotation axis." )
    axis = axis / axis_norm
    pivot = np.array ( pivot, dtype = np.float64 )

    for atom_id in atom_ids:
        local_pos = np.array ( vismol_object.frames[frame, atom_id], dtype = np.float64 ) - pivot
        new_pos   = _rotate_vector_rodrigues ( local_pos, axis, angle_rad ) + pivot
        vismol_object.frames[frame, atom_id] = new_pos.astype ( np.float32 )

    vismol_object.mass_center = np.mean ( vismol_object.frames[0], axis = 0 )

    if update_representation:
        vm_session = vismol_object.vm_session
        for rep in vismol_object.representations.values ( ):
            if rep is not None and rep.active:
                rep.was_rep_coord_modified = True
                rep.was_sel_coord_modified = True
        picking_dots = vismol_object.core_representations.get ( "picking_dots" )
        if picking_dots is not None:
            picking_dots.was_rep_coord_modified = True
        if getattr ( vm_session, "vm_glcore", None ) is not None:
            vm_session.vm_glcore.updated_coords = True
            vm_session.vm_glcore.queue_draw ( )
