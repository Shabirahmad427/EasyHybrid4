# EasyHybrid4 Architecture and Repository Baseline

## Baseline record

Recorded 2026-10-17 UTC while starting EH4-000. The checked-out EasyHybrid4
directory is `$HOME/software/EasyHybrid4`.

| Item | Evidence |
|---|---|
| EasyHybrid4 Git metadata | Reverified directly: repository root `$HOME/software/EasyHybrid4`, branch `main`, HEAD `bea94210ed7c23f71d2241f8abe3c849ade18561`, clean working tree, no tags, and **no remotes configured**. The canonical EasyHybrid4 fork URL cannot be identified from this clone. |
| EasyHybrid4 declared graphics submodule | `.gitmodules` declares `src/graphics_engine`, URL `https://github.com/casebor/graphics_engine`, branch `vismol_easyhybrid`. However, `git ls-tree HEAD src/graphics_engine` reports mode `040000` (ordinary tree), the index lists files individually, `git submodule status --recursive` is empty, and there is no nested `.git` or `.gitmodules`. The entry is stale: the source is vendored, not a resolvable submodule. No upstream graphics revision is present in Git metadata. |
| EasyHybrid3 reference checkout | `$HOME/software/EasyHybrid3`, branch `dev`, commit `b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098` (2026-10-16). Tracking `origin/dev`, 18 commits ahead. Remote `origin`: `git@github.com:Shabirahmad427/EasyHybrid3.git`. No tags were listed. Working tree is dirty: modified `docs/GPU4PySCF.md`, six source files, and untracked `bin/`. These user changes were left untouched. |
| EasyHybrid3 declared graphics submodule | `.gitmodules` names `src/graphics_engine`, URL `https://github.com/Shabirahmad427/Vismol`, branch `vismol_easyhybrid`. Resolved SHA `6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`; the submodule checkout is detached. Its `origin` is the same HTTPS URL. No submodule tags were listed. |
| Nested graphics submodules | No nested `.gitmodules` or `.git` entries were found under the vendored graphics-engine directory. |
| Licenses | EasyHybrid4 root `LICENSE` is GNU GPL version 3. `src/graphics_engine/LICENSE` is Creative Commons Attribution-NonCommercial 4.0 International. Preserve both notices; distribution compatibility needs a deliberate legal review before packaging. |
| Runtime observed | Linux x86_64, kernel `6.8.0-147-generic`; EasyHybrid Python `3.12.3`, PyGObject `3.48.2`, GTK `4.14.5`, GLib `2.80.0`. Display backend and OpenGL renderer were not measured for this baseline. |
| Existing test/CI inventory | `tests/` contains `test_bond_order_perception.py` and `test_atom_ops_bonds.py`; `tests/README.md` says these avoid GTK/display/OpenGL. No CI workflow directory was present in this checkout. The GUI has 53 `.glade` files and no `.ui` files. |

The first inspection in the prior session saw an empty `.git/` placeholder.
That observation was superseded when the repository metadata became available;
the direct Git results above are the current baseline.

## Layout and boundaries observed

- `easyhybrid.py` is the GTK4 application entry point; `activate_easyhybrid4.sh`
  selects the configured pDynamo Python environment and sets the application
  home.
- `install.py`, `requirements.txt`, and `requirements-dev.txt` manage
  prerequisites and Python packages. The current installer checks for GTK
  4.0+, but that is not yet a justified compatibility interval.
- `src/gui/` contains the main window, GTK widgets, workflow dialogs, and
  GtkBuilder `.glade` resources. `src/gtk4_compat.py` centralizes a fallback
  value for GTK builds that omit `Gtk.INVALID_LIST_POSITION` from introspection.
- `src/pdynamo/` adapts GUI actions to pDynamo systems and simulation
  workflows. Scientific regression scope is described in `tests/README.md`.
- `src/graphics_engine/` contains the vendored VisMol Python package, GTK4
  widget, OpenGL implementation, shaders, molecular parsers, Cython sources,
  and its own `setup.py`, `pyproject.toml`, and license. Git tracks its files
  directly, despite the stale `.gitmodules` entry.
- Detailed package, GTK API, UI resource, dependency, and installer inventory
  is recorded in `docs/DEPENDENCY_INVENTORY.md` (EH4-001).
- Existing planning and compatibility notes include `GTK4_PORT.md`,
  `MACOS_TRACKPAD_PAN.md`, `GPU_PYSCF_CHANGES.md`, and
  `[remote Linux host]_GPU_INTEGRATION.md`; these remain in place.

## EH4-000 remaining blockers

EH4-000 remains **in progress, not complete**. Branch, commit, and clean state
are verified, but the clone has no configured remote, so its EasyHybrid4 fork
root cannot be identified. The declared graphics submodule has no gitlink or
checked-out Git metadata, so there is no resolved upstream revision to record.
Keep these as unresolved issues; do not infer the graphics SHA from EasyHybrid3
or the URL in `.gitmodules`.
