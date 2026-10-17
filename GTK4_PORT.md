# EasyHybrid4 GTK4 port

EasyHybrid4 is a faithful GTK4 port of EasyHybrid3. EasyHybrid3 remains the
behavioral and visual reference. The port must not redesign workflows, rename
scientific concepts, remove features, or add placeholder features.

## Supported platforms

- Linux with GTK 4.0+ and PyGObject
- Windows with GTK 4.0+ and PyGObject
- macOS with GTK 4.0+ and PyGObject

Platform-specific code is allowed only for dependency discovery, packaging,
native file integration, and graphics behavior that cannot be implemented
portably. GTK4 `Gtk.GLArea` is the default renderer integration on every
platform. The EasyHybrid3 macOS workaround based on a hidden GLFW context must
not be copied unless native GTK4 testing demonstrates that it is still needed.

## Compatibility rules

1. Keep EasyHybrid3 unchanged. All port changes belong in `EasyHybrid4`.
2. Preserve window structure, labels, actions, defaults, shortcuts, and
   scientific behavior from EasyHybrid3.
3. Write all new source, comments, documentation, messages, and UI text in
   English.
4. Replace removed GTK3 APIs with their direct GTK4 equivalents. Do not use a
   visual redesign to avoid a difficult migration.
5. Keep pDynamo session data and EasyHybrid project formats compatible unless a
   documented format migration is unavoidable.
6. Verify each migrated window against EasyHybrid3 before marking it complete.

## Known GTK4 migrations

| EasyHybrid3 GTK3 API | Faithful GTK4 implementation |
| --- | --- |
| `Gtk.main()` / `Gtk.main_quit()` | `Gtk.Application.run()` / application quit |
| `Gtk.MenuBar`, `Gtk.Menu`, `Gtk.MenuItem` | `Gio.MenuModel`, actions, and `Gtk.PopoverMenuBar` |
| `add()` / `pack_start()` / `pack_end()` | `set_child()` / `append()` / `prepend()` |
| GTK event signals and event masks | GTK4 event controllers and gestures |
| legacy drag destination API | `Gtk.DropTarget` / `Gtk.DropTargetAsync` |
| blocking dialog `run()` | asynchronous response callbacks |
| Blocking file chooser dialogs | GTK4 `Gtk.FileChooserDialog` with response callbacks |
| Blocking color chooser dialogs | GTK4 `Gtk.ColorChooserDialog` with response callbacks |
| `show_all()` | widget visibility plus `present()` |
| GTK3 Glade packing nodes | GTK4 child properties and layouts |

## Current state — migration in progress

The application requests the GTK 4.0 introspection namespace and supports
GTK 4.0+ runtimes. Startup uses `Gtk.Application`; VisMol renders through
`Gtk.GLArea` on every platform. GtkBuilder signal connections use explicit
GTK4 helpers. The code does not monkeypatch GTK classes with GTK3 methods.
The signal loader resolves relative image paths against the original UI file
before using its temporary XML copy. Window-local styling uses GTK4 widget CSS
classes, and the terminal removes its display CSS provider when it closes.

The splash image uses `Gtk.Picture.set_content_fit()` when the runtime has it
(GTK 4.8+), and falls back to `set_can_shrink()` plus
`set_keep_aspect_ratio()` before GTK 4.8. VisMol uses GTK 4.8's scroll-unit
API to convert macOS trackpad surface-pixel deltas to calibrated wheel steps;
on earlier GTK4 versions the scroll controller asks GTK to emit discrete
wheel steps. The GTK3 Quartz `Gtk.DrawingArea`/hidden-GLFW workaround and
GTK3-only native accessibility bridge are not used by the GTK4 build.

The main browser uses `Gtk.TreeListModel`, `Gtk.ColumnView`, typed
`Gio.ListStore` rows, and GTK4 selection models. System and coordinate
selectors use `Gtk.DropDown`; tables and editable lists use column views with
list-item factories. The same native models are used across VisMol navigation,
analysis, simulation, import, restraint, and preferences workflows. Scientific
clone paths clear and restore interface row references around pDynamo cloning.
Full browser refresh rebuilds its tree and selector models together, preserves
the active system, and refreshes open interface windows. The old duplicate
RMSD and context-menu implementations and unreferenced Glade assets have been
removed or retired.

The EasyHybrid3 installation remains separate and has not been modified. A
source scan found no GTK3 typelib requests, GTK3 tree/combo widgets, GTK3
container methods, or GTK3 dialog `run()` calls in EasyHybrid4. Python modules
that import Gtk pin the `Gtk` namespace to 4.0, and all 53 GtkBuilder files
declare GTK 4.0.

The GTK-free RDF, RMSF, density, and Ramachandran calculations are available
in EasyHybrid4. RDF, box-density, RMSF, and trajectory Ramachandran analysis
windows are wired to the native GTK4 menu. They use GTK4 `DropDown`,
`SpinButton`, `DrawingArea`, motion controllers, and asynchronous file chooser
responses.

The Builder now exposes DYFF parameter inspection and editing, model
incorporation into pDynamo, and xTB torsion fitting through native GTK4
windows. Its parameter window uses GTK4 notebook/list widgets, and the
torsion-fit window builds controls in GTK4 rather than loading a GTK3 Glade
file. Builder undo snapshots include partial charges, manual atom types,
aromatic bonds, and DYFF parameter edits. The OPLS parameter inspector is also
ported to GTK4, with per-system tables, quality filters, structure projection,
editable values, model rebuilds, and xTB torsion fitting; it is available from
the System menu.
The remaining setup module,
`info_text_window.py` is an unreferenced standalone GTK3 demo that creates a
window and starts a GTK3 event loop at import time, so it is intentionally not
copied into EasyHybrid4. The Builder includes a GTK4
periodic-table picker and solvation window backed by the solvent library and
pure NumPy solvation engine, with 13 bundled solvent templates. DYFF atom
typing, editable type and charge values, protonation controls, residue rename,
hybridization display, and 3D atom highlighting use a native GTK4 ColumnView. Live selection translation and rotation use GTK4 scales and gesture controllers, with a single undo point per gesture.
The Builder can pick four atoms and adjust a rotatable bond dihedral with a
native GTK4 scale window; cyclic bonds are rejected and the linked pDynamo
system is synchronized when the adjustment ends. Its fragment library uses a
GTK4 category selector, fragment list, and GLArea preview. Selecting a
fragment arms hydrogen replacement; the selected molecule and formal charges
are carried into the Builder graph and pDynamo system. The fragment bundle
contains 27 MOL2 definitions across functional groups and rings.
The complete-structure library uses a native GTK4 category dropdown, list,
and GLArea preview. It places complete MOL2 molecules on a Builder click and
syncs their atoms and explicit bond orders to pDynamo. EasyHybrid4 now bundles
the same 663 structure templates as EasyHybrid3 across 31 categories.
The Builder toolbar opens a native GTK4 new/edit chooser. Existing systems are
cloned for editing; same-size edits fold back into the chosen molecular object,
while atom-count changes retain the clone as a separate system.
Remaining tools are migration work, not features considered complete by
absence from the GTK3 API scan.

The pDynamo layer exposes Baker saddle optimization and reaction-path
branches through the geometry-optimization worker, and dispatches Conjugate
Peak Refinement through pDynamo's `addOns.pyCPR`. All three workflows now
have GTK4 windows, native coordinate selectors, non-blocking error windows,
and GTK4 menu actions. Their Glade files declare GTK 4.0 and pass
`gtk4-builder-tool simplify` without property or class errors. The installed
pDynamo3 APIs and the EasyHybrid4 dispatch modules import successfully.

The current Builder, preferences, and reaction-coordinate modules compile and
import under GTK 4.14. The solvation library discovers all 13 solvent
templates, and a sphere solvation calculation placed solvent molecules. Gtk
imports in all 100 Python modules request GTK 4.0. All 53 GtkBuilder XML files
declare GTK 4.0; their object classes and properties resolve against the GTK4
introspection data, and no GTK3 packing nodes remain. The embedded preference
and reaction-coordinate UI definitions also pass the GTK4 property scan. The
menu JSON parses, and the Ramachandran Cairo renderer drew categorized points
on an image surface. The pDynamo typer classified both atoms in a bonded
two-carbon fragment. Live window construction and visual comparison remain
unverified in this environment: `Gtk.init_check()` succeeds, but constructing
a GTK window fails because the available display backend is not usable here.
Static verification also confirms all 53 GtkBuilder files request GTK 4.0 and
all 20 main-window image assets resolve from the original UI directory.
