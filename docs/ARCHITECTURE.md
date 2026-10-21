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
