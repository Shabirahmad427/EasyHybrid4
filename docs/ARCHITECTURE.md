# EasyHybrid4 architecture boundaries

This document records the implemented boundaries and the remaining coupling
found during EH4-100. It describes the current code, not a claim that all
workflows are already independent or cross-platform verified.

## Layers and current ownership

| Boundary | Current code | Contract and status |
|---|---|---|
| Scientific calculations | `src/util/md_analysis.py`, `src/util/ramachandran.py`, `src/util/geometric_analysis.py`, `src/pdynamo/p_methods/`, `src/pdynamo/opls/` | Analysis and geometry routines operate on arrays or narrow model protocols and do not import GTK. pDynamo workflow methods own numerical job setup/calculation. The selected analysis, state, and color-math modules are checked by an import guard. Not every pDynamo adapter is GTK-free. |
| Application/session state | `src/pdynamo/pDynamo2EasyHybrid/state.py` | `SessionState` owns loaded-system bookkeeping, active ID, counters, dirty/autosave flags, random token, and process pool. It is standard-library-only. `pDynamoSession` retains old public attributes as properties that delegate to this model. Project serialization remains in the existing I/O adapter. |
| pDynamo/GUI adapter | `src/pdynamo/pDynamo2EasyHybrid/session.py` and mixins | Adapts user actions to pDynamo and VisMol. It remains coupled to GTK, the main window, and graphics types. It is not the scientific-core import surface; new calculations should be placed in `p_methods` or GTK-free utility services and accept data/protocol inputs. |
| GTK presentation | `easyhybrid.py`, `src/gui/`, `src/util/easyplot/{canvas,image_plot,xy_plots}.py`, `src/util/rama_plot.py` | Owns windows, dialogs, GtkBuilder resources, event controllers, and drawing widgets. The plotting package lazily loads presentation exports so importing its numerical color helpers does not import GTK. Existing widget import names remain available. |
| Molecular graphics/OpenGL | `src/graphics_engine/src/vismol/{model,core,gui,libgl}/` | Molecular model/parser code, GTK `GLArea` adapter, OpenGL renderer, and shaders are bundled together as tracked parent-repository files, not an active Git submodule. Keep GTK imports in `gui/`, GL calls in `libgl/`, and data/model behavior in `model/` and non-rendering `core/`. The native matrix builds the seven Cython extensions and exercises the production renderer across its GTK/OS cells; physical GPUs, native OS pointer injection in the full app, and Wayland remain unverified. See EH4-200/EH4-202 in the roadmap. |
| Platform integration | `src/os_integration/gtk_startup.py`, launcher/installer, and a few graphics input paths | Startup driver environment configuration is kept in a standard-library-only module with Linux/X11 behavior guarded and regression-tested; saved preferences are honored across OSes. Native dependency discovery, paths, packaging, and unavoidable input differences belong at this edge. The Bash launcher/build scripts and platform-dependent trackpad handling mean portability is not yet established. No platform compatibility is inferred from Linux unit tests. |

## Supported dependency direction

```text
GTK presentation ───────► application/session adapters ───────► pDynamo services
       │                                  │
       └──────────────► graphics UI ──────┴────► VisMol model/data
                               │
                               └───────────────► OpenGL renderer

Scientific services and SessionState must remain importable without GTK,
display initialization, OpenGL, or an instantiated application window.
```

The existing `pDynamoSession` is a compatibility facade, not a pure domain
object: it coordinates pDynamo, VisMol, and main-window operations. The new
`SessionState` extraction reduces that coupling without changing the public
session attribute names or the historical `restart()` reset behavior.

## Regression boundary

- `tests/test_dependency_boundaries.py` imports selected scientific and state
  modules in a subprocess that rejects PyGObject and VisMol GUI imports. When
  pDynamo3 is configured, all `p_methods` workflows import with PyGObject
  blocked and the legacy `pDynamoSession` state facade behaves without a
  display.
- `tests/test_session_state.py` checks independent defaults, active-system
  lookup, reset semantics, and preservation of dirty/job metadata.
- `tests/test_easyplot_boundaries.py` checks numerical color behavior and the
  legacy package-level plotting exports.
- `tests/test_os_integration.py` checks preference precedence and ensures
  Linux/X11 graphics workarounds do not leak onto Windows, macOS, or Wayland.
- Existing analysis, bond editing, and bond-order tests remain the workflow
  regression suite. They do not replace a real pDynamo calculation or GUI/GL
  run.

## Remaining work

EH4-100 does not claim complete decoupling: the session facade and several
VisMol-facing adapters still import GTK or graphics classes. Further moves
must be driven by actual reusable logic and tests, not by adding unused
abstraction packages. GTK runtime capability policy belongs in
`src/gtk4_compat.py`; EH4-101 covers its feature checks and tested fallback
branches. Full GtkBuilder/window lifecycle and real graphics validation are
tracked by EH4-102 and EH4-200 onward.

## Repository and source provenance (2026-10-20)

The EasyHybrid4 working copy is at `/home/shabir/software/EasyHybrid4`.
`origin` is `https://github.com/Shabirahmad427/EasyHybrid4.git`; local `main`
and `origin/main` both point to `0f21022a345e1fda80b2cc18b048e9ed91c1b867`.
The task branch for the current provenance audit started from that commit. At
inspection there were 26 local branches, only `origin/main` as a remote ref,
no tags, and a clean working tree before the audit edits.

The root application license is GPL-3.0. `src/graphics_engine/LICENSE` says
CC BY-NC 4.0. Graphics metadata conflicts: `pyproject.toml` lists an MIT
classifier while `setup.py` lists CC BY-NC 4.0; some individual graphics
source files also contain GPL notices. These declarations do not establish
which contributors own each file or resolve distribution compatibility.

`src/graphics_engine` is vendored as an ordinary tracked tree (Git tree mode
`040000`), not a submodule; recursive submodule status is empty. The root
`.gitmodules` entry naming `https://github.com/casebor/graphics_engine` and
branch `vismol_easyhybrid` is historical/stale metadata. The declared public
branch head and the EasyHybrid3 submodule revision are not evidence of the
vendored tree's base revision. Do not publish these graphics changes or
convert the directory to a submodule before source ancestry and ownership are
authoritatively reconciled.

An additional GitHub API comparison on 2026-10-21 found public commit
`2827f069355f990e3022fba41aac23239e0cda2e` (2022-07-15, “Moved to
development package”) in `casebor/Vismol` history. Its `.gitignore`, `LICENSE`,
`README.md`, and `build_vismol_BCK.py` blob IDs match the vendored files
byte-for-byte. The candidate's `MANIFEST.in` and `setup.py` differ, it has no
matching `pyproject.toml` or `scripts` directory, and its `src` tree object
`115eacd3b61152a5abb65fa0b53c26ce0a6ec7f5` differs from the vendored `src`
tree `1868dfde6e3d80681635f96778507e4fc15bc788`. This is a partial content
match, not proof that this commit is the base revision or that later
contributors authorized the vendored changes.

The read-only EasyHybrid3 comparison checkout is
`/home/shabir/software/EasyHybrid3`, branch `dev`, commit
`b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098`, remote
`git@github.com:Shabirahmad427/EasyHybrid3.git`, 18 commits ahead of
`origin/dev`. Its pre-existing edits to seven tracked files and untracked
`bin/` were preserved. Its graphics submodule points at
`6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`; that comparison SHA does not
establish the EasyHybrid4 vendored source SHA. EH4-000 remains open for this
unresolved graphics ancestry and contributor/license ownership evidence.

### Repository-state re-audit (2026-10-21)

This read-only audit was performed on `eh4-000-repository-provenance` at
`12ec192857a0d765149c9671f57bf5685b09efef`, clean before the documentation
update. The owner-supplied `origin` fetch/push URL is
`https://github.com/Shabirahmad427/EasyHybrid4.git`. `main` and
`origin/main` are both `0f21022a345e1fda80b2cc18b048e9ed91c1b867` with zero
ahead/behind commits. There are 32 local branches, only the `origin/main`
remote-tracking ref, and no tags. The graphics subtree object at this audited
HEAD is `e2dd787a9b1f20d1e47ccba3bd484c45573bef73`; it is mode `040000`, its
files are individually indexed, and `git submodule status --recursive` is
empty. The subtree object ID identifies the current content tree only; it
does not identify the source revision from which it was copied.

Local branch refs at the audit (branch : commit):

```text
eh4-000-repository-provenance: 12ec192857a0
eh4-200-graphics-engine-provenance: 0f21022a345e
eh4-202-cross-platform-pointer-injection: 139d6c455fc3
eh4-202-gtk-gesture-release-marshalling: 4cd83bac348f
eh4-202-native-pointer-cross-platform: 44afbc66c739
eh4-202-native-pointer-windows-macos: dcf19b1c6504
eh4-203-input-semantics: fe1220fa1678
eh4-203-scroll-input-semantics: 60e0c3deeb1f
eh4-203-scroll-input-semantics-stacked: 31ba850f1b7d
eh4-204-molecular-interaction-regression: c0fa66042746
eh4-204-selection-camera-state: d151f33ccf81
eh4-204-selection-camera-state-stacked: 981cd8e0c279
eh4-205-graphics-fallback-diagnostics: 687762da83ca
eh4-205-graphics-fallback-messaging: d8f0ad121e54
eh4-205-graphics-fallback-messaging-stacked: f14d6249f6bf
eh4-301-native-os-integration: e34ccbf491c1
eh4-302-display-scaling: 2ea775576f75
eh4-303-reproducible-installation: 9e2320a01e63
eh4-304-platform-packaging: a25e29042578
eh4-400-visualization-fixture-integrity: 93ee5bacc381
eh4-401-selection-edit-undo-roundtrip: c91031bfb8ac
eh4-402-mm-qmmm-workflow-validation: ae66eee605b9
eh4-403-simulation-export-regressions: 4dd8a4fe20a2
eh4-404-project-persistence-recovery: 8e1356f96d23
eh4-404-project-persistence-roundtrip: f071794064e8
eh4-405-background-computation-cancellation: 131aa3bdee64
eh4-405-background-job-cancellation: e834fb01f575
eh4-500-ci-quality-gates: 0c94b9dd50c9
eh4-501-gtk-version-matrix-guard: 38cb0909a932
eh4-502-native-ui-acceptance: ceafa14450a9
eh4-503-gl-smoke-evidence: 0f21022a345e
main: 0f21022a345e
```

The separate EasyHybrid3 checkout was inspected read-only at
`b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098` (`dev`, 18 commits ahead of
`origin/dev`), with remote
`git@github.com:Shabirahmad427/EasyHybrid3.git`. It remains dirty in seven
tracked paths and untracked `bin/`; none were changed. Its declared graphics
submodule resolves recursively to
`6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`, comparison evidence only. The
EasyHybrid4 root license is GPL-3.0; the vendored engine license file says CC
BY-NC 4.0, while its package metadata also includes an MIT classifier and
`setup.py` declares CC BY-NC. No license or contributor ownership conclusion
is inferred from these conflicting notices.

**Superseded (2026-10-29):** the statements above that the vendored graphics
base revision is not identifiable, and that the `casebor/Vismol` candidates
are the closest evidence, are superseded by the base-revision match below. The
"no tags" and branch-count statements describe the 2026-10-20/21 state only.

### Graphics engine base revision (2026-10-29)

Method (read-only on EasyHybrid3; nothing was checked out or modified there):
the vendored tree added by EasyHybrid4 commit
`c2668e2bfe71ead802caaac7356db52bf5f41bb1` ("Initial EasyHybrid4 baseline",
committer Shabirjan427, 2026-10-17; 91 files under `src/graphics_engine`) was
compared by path and blob ID (`git ls-tree -r`) with every commit reachable in
the EasyHybrid3 graphics submodule
`/home/shabir/software/EasyHybrid3/src/graphics_engine` (remote
`https://github.com/Shabirahmad427/Vismol`, 162 commits). For each candidate,
total changed lines were counted with `git diff --no-index --numstat` between
the exported candidate tree and the exported EasyHybrid4 import tree.
EasyHybrid3's `.gitmodules` still names
`https://github.com/casebor/graphics_engine`, branch `vismol_easyhybrid`; the
checkout's actual remote is `Shabirahmad427/Vismol`.

| Candidate | Author / date | Identical files (of 91) | Imported files missing | Candidate-only files | Changed lines |
|---|---|---|---|---|---|
| `8360a7131d5a19464929a03d1583a6d457ae29e7` "macOS port: glViewport resize_window _zoom_view" | ferbachega, 2026-08-29 18:47 -0300 | 79 | 0 | 6 | 3562 (minimum) |
| `bb51688953779543eb3621523c89e4b763fb0985` "representations.py vismol_glcore.py" | ferbachega, 2026-09-08 | 79 | 0 | 6 | 3608 |
| `ea14fbce26067792e2094cf420fcb3202b4399d2` "label bug fixed" | ferbachega, 2026-08-29 11:14 -0300 | 79 | 0 | 6 | 3704 |

`8360a71` is the direct child of `ea14fbc`; `bb51688` is a later descendant.
All three are contained in `origin/vismol_easyhybrid`,
`origin/macos-trackpad-black-screen` and `origin/builder-tools-wip` of that
Vismol repository. No commit matched more than 79 files. **Best-supported base
revision: `8360a7131d5a19464929a03d1583a6d457ae29e7`** (fewest changed lines,
maximum identical files). This is a content match, not a recorded import
pointer: `c2668e2` does not name its source commit.

The six candidate-only files are GTK3 widgets absent from EasyHybrid4
(`src/vismol/gui/gtk_widgets/{MainTreeview.glade, VisMolPlayer.glade,
main_treeview.glade, main_treeview.py, player.py, player2.py}`, 1388 lines).
The 12 differing files against `8360a71` (EasyHybrid4 added/removed lines):

| File | +/- | Nature |
|---|---|---|
| `MANIFEST.in` | 0/1 | drop GTK3 `.glade` include |
| `setup.py` | 0/2 | drop GTK3 `.glade` package data |
| `scripts/vismol_simple.py`, `scripts/vismol_simple_local_installation.py` | 22/13 each | GTK 4.0 `Gtk.Application` demo |
| `src/vismol/__main__.py` | 2/2 | `Gtk 4.0`, toolkit `Gtk_4.0` |
| `src/vismol/core/vismol_session.py` | 3/3 | toolkit check `Gtk_3.0` -> `Gtk_4.0` |
| `src/vismol/core/vismol_object.py` | 3/4 | GTK3 `TreeIter` fields -> GTK4 row fields |
| `src/vismol/gui/filechooser.py` | 17/17 | GTK3 `FileChooserDialog` -> GTK4 chooser |
| `src/vismol/gui/vismol_gtkwidget.py` | 319/387 | GTK4 `GLArea`/event controllers; upstream GTK3 macOS GLFW offscreen workaround absent |
| `src/vismol/gui/vismol_tools.py` | 331/811 | GTK4 controllers/widgets |
| `src/vismol/libgl/vismol_glcore.py` | 82/118 | GTK4 event/scroll handling |
| `src/vismol/libgl/representations.py` | 1/1 | comment path `/home/fernando/...` -> `~/...` |

Characterisation: every difference is a GTK3 -> GTK4 port edit (or removal of
GTK3-only assets) present in the EasyHybrid4 import; none was identified as a
later upstream feature missing from EasyHybrid4 (only the diff headlines above
were reviewed, not every hunk). Who wrote those port edits, and where they
were developed before `c2668e2`, is **not recorded in Git**: the import is a
single commit by Shabirjan427, and no earlier history of the GTK4 port was
found in either repository. All 26 later commits touching `src/graphics_engine`
on `origin/main` are by Shabirjan427. Upstream authorship of the base is
ferbachega (Fernando Bachega, the EasyHybrid maintainer named in source
headers) on top of earlier casebor history. License, as decided by the
maintainer: VisMol stays CC BY-NC 4.0, documented as-is in
`THIRD_PARTY_NOTICES.md`; EasyHybrid4 as distributed is non-commercial only
and must not be described as GPL-only.

### Current-state baseline (2026-10-29)

Verified on this date with Git (Linux 6.8.0-147-generic x86_64, docs only):

- `origin` = `https://github.com/Shabirahmad427/EasyHybrid4.git`;
  `origin/main` = `83434e60d032677f2de71414af4ef4d00c2dfc42`.
  `git ls-remote --heads origin` also listed `eh4-603-support-table`
  (`4c3540a6`), an in-progress task branch, so `main` was not the only GitHub
  branch at this check.
- Local branches in the shared repository: `main`, `eh4-603-support-table`,
  this task branch `eh4-000-200-provenance`, and agent worktree branches.
  30 local `archive/*` tags (not pushed) preserve deleted superseded branches.
- No submodules: `git submodule status` is empty. `src/graphics_engine` is an
  ordinary tree (current object `281fc190482a248cd22a6340d8f9831759e12620`).
- **Stale metadata, documented and kept:** root `.gitmodules` still exists on
  `origin/main` and declares `graphics_engine` ->
  `https://github.com/casebor/graphics_engine` branch `vismol_easyhybrid`. It
  has no matching gitlink, so Git ignores it; the actual base revision is the
  `Shabirahmad427/Vismol` commit above.
- pDynamo3 dependency: maintainer fork `https://github.com/Shabirahmad427/pDynamo3`
  commit `e007e44ca4ccd5e24714adcae6194d04c1bc36be` (upstream pdynamo/pDynamo3
  `6b28dd8` plus GPU4PySCF adapter), pinned as `PDYNAMO3_REF` in
  `.github/workflows/native-gtk-matrix.yml`.
- EasyHybrid3 reference checkout `/home/shabir/software/EasyHybrid3` was read
  only; no files, refs or submodule state there were changed.
