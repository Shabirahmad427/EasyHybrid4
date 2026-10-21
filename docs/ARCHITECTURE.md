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
