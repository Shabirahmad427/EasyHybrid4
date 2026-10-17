# EasyHybrid4 Architecture and Repository Baseline

## Baseline record

Recorded 2026-10-17 UTC while starting EH4-000. The checked-out EasyHybrid4
directory is `$HOME/software/EasyHybrid4`.

| Item | Evidence |
|---|---|
| EasyHybrid4 Git metadata | **Unavailable in this checkout.** `.git/` is an empty, read-only directory. `git status`, `git rev-parse`, branch, tag, and remote queries fail with “not a git repository”. EasyHybrid4 branch, commit, tags, dirty-tree status, and remote URL therefore remain unknown. No attempt was made to initialize or replace Git metadata. |
| EasyHybrid4 declared graphics submodule | `.gitmodules`: path `src/graphics_engine`; URL `https://github.com/casebor/graphics_engine`; branch `vismol_easyhybrid`. Its directory has source files but no `.git` metadata, so its checked-out SHA and recursive submodule state cannot be verified from this copy. |
| EasyHybrid3 reference checkout | `$HOME/software/EasyHybrid3`, branch `dev`, commit `b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098` (2026-10-16). Tracking `origin/dev`, 18 commits ahead. Remote `origin`: `git@github.com:Shabirahmad427/EasyHybrid3.git`. No tags were listed. Working tree is dirty: modified `docs/GPU4PySCF.md`, six source files, and untracked `bin/`. These user changes were left untouched. |
| EasyHybrid3 declared graphics submodule | `.gitmodules` names `src/graphics_engine`, URL `https://github.com/Shabirahmad427/Vismol`, branch `vismol_easyhybrid`. Resolved SHA `6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`; the submodule checkout is detached. Its `origin` is the same HTTPS URL. No submodule tags were listed. |
| Nested graphics submodules | No nested `.gitmodules` or `.git` entries were found under the EasyHybrid4 graphics-engine directory. This does not prove the missing parent submodule metadata is clean. |
| Licenses | EasyHybrid4 root `LICENSE` is GNU GPL version 3. `src/graphics_engine/LICENSE` is Creative Commons Attribution-NonCommercial 4.0 International. Preserve both notices; distribution compatibility needs a deliberate legal review before packaging. |
| Runtime observed | Linux x86_64, kernel `6.8.0-147-generic`; EasyHybrid Python `3.12.3`, PyGObject `3.48.2`, GTK `4.14.5`, GLib `2.80.0`. Display backend and OpenGL renderer were not measured for this baseline. |
| Existing test/CI inventory | `tests/` contains `test_bond_order_perception.py` and `test_atom_ops_bonds.py`; `tests/README.md` says these avoid GTK/display/OpenGL. No CI workflow directory was present in this checkout. GTK4 UI definitions include 53 `.glade` files. |

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
- `src/graphics_engine/` contains the VisMol Python package, GTK4 widget,
  OpenGL implementation, shaders, molecular parsers, Cython sources, and its
  own `setup.py`, `pyproject.toml`, and license. It is intended to be a Git
  submodule, but this checkout has only its files, not its Git metadata.
- Existing planning and compatibility notes include `GTK4_PORT.md`,
  `MACOS_TRACKPAD_PAN.md`, `GPU_PYSCF_CHANGES.md`, and
  `[remote Linux host]_GPU_INTEGRATION.md`; these remain in place.

## EH4-000 blocker and next evidence needed

EH4-000 is **in progress, not complete**. A normal EasyHybrid4 Git checkout
or its original `.git` metadata is required to record the actual EasyHybrid4
remote, branch, commit, tags, dirty state, and graphics submodule SHA. The
current README identifies EasyHybrid3 as the upstream behavioral reference,
but does not identify a canonical EasyHybrid4 fork remote. Do not infer these
values from the sibling EasyHybrid3 checkout or from `.gitmodules` alone.

Next action: restore/open the actual EasyHybrid4 Git checkout metadata (without
discarding working files), then repeat the baseline queries before proceeding
to EH4-001. Until then the Phase 0 gate remains closed.
