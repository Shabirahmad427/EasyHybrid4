# EasyHybrid4 Package and Dependency Inventory

## EH4-001 — package, dependency, and GTK API inventory

### Entrypoints and project areas

- `easyhybrid.py` is the application entrypoint. It loads pDynamo environment
  configuration, requests GTK 4, creates `Gtk.Application`, and initializes
  the GUI. The active launcher `activate_easyhybrid4.sh` sets `EASYHYBRID_HOME`
  and invokes the configured Python environment.
- `install.py` is the interactive prerequisite/build installer. `paths.py`
  optionally supplies `PDYNAMO_HOME`; `requirements.txt` lists Python runtime
  packages and `requirements-dev.txt` adds pytest. Root scientific example
  scripts live under `examples/scripts/`.
- `src/gui/` contains the main window, widgets, molecular builder, analysis,
  setup, and simulation dialogs. UI definitions are 53 `.glade` GtkBuilder
  resources; there are no `.ui` resources. Resources are loaded from GUI
  modules, including `src/gui/main/main_window.py` and
  `src/gui/windows/simulation/`.
- `src/pdynamo/pDynamo2EasyHybrid/` is the GUI-to-pDynamo session facade and
  mixins for analysis, simulation, restraints, representation, and data I/O.
  `src/pdynamo/p_methods/` implements simulation setup/workflows, while
  `src/pdynamo/opls/` and `src/util/extras/` contain force-field and QC
  integrations.
- `src/util/` provides plotting, geometry, trajectory, file, and analysis
  utilities. `tests/` has two scientific/data-logic test modules and
  fixtures; the coverage boundary is stated in `tests/README.md`.
- `src/graphics_engine/src/vismol/` contains the VisMol models and parsers
  (`model/`, `utils/`), application/session logic (`core/`), GTK widgets
  (`gui/`), OpenGL context and molecular rendering (`libgl/`), and GLSL
  shaders (`libgl/shaders/`). Seven Cython extension sources are built by
  `src/graphics_engine/setup.py` through `install.sh`.

### GTK, GLib, and UI resource API baseline

- Python GTK imports request `gi.require_version("Gtk", "4.0")`; a source
  audit found no GTK 3 namespace requests. GTK3 and GTK4 are distinct API
  majors; the GTK4 import request does not establish a supported runtime
  minor interval. `GTK_MIN` and `GTK_LATEST_VERIFIED` remain unset pending
  EH4-004 evidence.
- The 53 `.glade` resources declare GtkBuilder library version 4.0. The
  resource/API audit is descriptive only; no blanket claim that all builders
  work at every GTK4 minor is made here.
- GTK classes are used directly throughout GUI and pDynamo adapter modules.
  GLib provides idle scheduling in `easyhybrid.py` and the pDynamo/VisMol
  adapters. GTK feature compatibility currently has a small helper in
  `src/gtk4_compat.py`; EH4-101 is the planned comprehensive adapter/test
  task.
- `Gtk.GLArea` is embedded in `src/graphics_engine/src/vismol/gui/` and
  delegates rendering to `libgl/vismol_glcore.py` and the shader/representation
  modules. A real context and renderer were not inspected during this static
  inventory.

### Declared and optional dependencies

- Root Python requirements: NumPy, SciPy, PyOpenGL, Cython, freetype-py,
  pycairo, PyGObject, and psutil (`requirements.txt`). GTK4 and its
  introspection typelib are external native dependencies. pDynamo3 is an
  independently installed binary/scientific framework, not a pip requirement.
- The graphics package metadata (`src/graphics_engine/pyproject.toml` and
  `setup.py`) additionally declares NumPy, Cython, and PyOpenGL and compiles
  Cython extensions. Its metadata advertises Python `>=3.7` and Unix only;
  this does not establish compatibility of the whole application with those
  Python versions or with Windows/macOS.
- The installer checks Python packages in `install.py:PYTHON_LIBRARIES`, the
  GTK typelib/runtime, compiler tools, and pDynamo. Optional QC interfaces
  appear in setup dialogs for ORCA, xTB, MOPAC, Sparrow, DFTB+, and
  PySCF/GPU4PySCF. Vendored adapters under `src/util/extras/` include ORCA,
  xTB, and MOPAC; `install.py` currently offers installation of the xTB
  adapter and checks the ORCA/xTB executable environment variables.
  PySCF/GPU4PySCF and the other external engines are not installed by
  `requirements.txt`.
- Build/launch scripts include `install.py`,
  `src/graphics_engine/install.sh`, `activate_easyhybrid4.sh`, and standalone
  VisMol scripts under `src/graphics_engine/scripts/`. The latter two shell
  scripts require a Bash-compatible shell, so native Windows provisioning is
  not demonstrated by this inventory.

### Known source-boundary observations (not fixes in EH4-001)

- `.gitmodules` declares a graphics submodule, but Git stores the directory
  as ordinary files. `.gitmodules` URL, `pyproject.toml` project URLs, and the
  absent parent remote do not establish which upstream revision these files
  came from; preserve that as an EH4-000/EH4-200 issue.
- The root README's clone example names EasyHybrid3, while describing
  EasyHybrid4 as a separate local port. No EasyHybrid4 remote/fork URL is
  configured in Git.
- Native Windows, macOS, Wayland, and GTK minor-version test results remain
  **NOT TESTED**. This task changed documentation only and did not alter
  scientific behavior.

