# Test Matrix and Baseline Results

This file records checks actually run in the EasyHybrid4 checkout. A passing
Linux result does not imply support on another operating system, GTK minor, or
display backend.

## Available environment

| Item | Observed value |
|---|---|
| OS / kernel | Linux x86_64, `Linux [remote Linux host] 6.8.0-147-generic`, Ubuntu userspace with glibc 2.39 |
| Python | 3.12.3 (`$HOME/software/envs/easyhybrid312/bin/python`) |
| PyGObject | 3.48.2 |
| GTK runtime | 4.14.5 |
| GLib runtime | 2.80.0 |
| pytest | 9.1.1 |
| NumPy / SciPy | 1.26.4 / 1.11.4 |
| Cython | 3.0.8 |
| PyOpenGL / psutil | 3.1.7 / 5.9.8 |
| Compiler | GCC 12.4.0 (Ubuntu) |
| Graphics renderer/context | NOT TESTED in this baseline |

The application launcher sources `$HOME/software/pdynamo3.sh`. With
that environment active, `pCore`, `pMolecule`, `pSimulation`, and `pScientific`
all resolve. A direct import probe without the launcher environment does not
represent the application's configured runtime.

## EH4-002 reproducible baseline

### Existing tests

Command:

```sh
$HOME/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/
```

Result: **PASS**, 23 passed in 0.02 seconds. Cache is disabled to avoid the
previous warning caused by a read-only shared pytest cache directory.

### Graphics engine extension build and import

The repository's graphics build command is `python3 setup.py build_ext
--inplace` (`src/graphics_engine/install.sh`). The test below runs that command
on a temporary source copy so generated C files and binaries do not modify the
checkout:

```sh
tmpdir=$(mktemp -d)
cp -a src/graphics_engine "$tmpdir/graphics_engine"
cd "$tmpdir/graphics_engine"
$HOME/software/envs/easyhybrid312/bin/python setup.py build_ext --inplace
PYTHONPATH="$tmpdir/graphics_engine/src" \
  $HOME/software/envs/easyhybrid312/bin/python -c 'import vismol.utils.matrix_operations, vismol.utils.PDBFiles, vismol.utils.GROFiles, vismol.utils.c_distances, vismol.utils.selectors, vismol.utils.mesh_decimation, vismol.utils.mesh_smoothing; print("7 graphics extension imports: PASS")'
```

Result: **PASS**; all seven Cython extensions compiled with GCC and imported.
Build emitted NumPy deprecated C API and setuptools metadata/license warnings.
The source checkout was not changed by this build.

### Package installation probe

An isolated `pip install --no-deps --no-build-isolation --target <temporary-dir>
<temporary graphics-engine copy>` probe **FAILED** during PEP 517 metadata
generation: `setup.py` raised `ModuleNotFoundError: No module named 'src'`.
The project's own `install.sh` build path and compiled-extension imports pass,
but generic pip package installation is not verified. Treat wheel/package
installation as a graphics-engine packaging issue for later task EH4-200 or
EH4-303; do not infer that pip installation works from `build_ext` success.

The full interactive EasyHybrid installer was **NOT RUN**: it can install
dependencies and modify the configured pDynamo environment, which would exceed
this non-invasive baseline check.

## Platform and GTK coverage

| Target | Status | Evidence / reason |
|---|---|---|
| Linux x86_64, GTK 4.14.5 / GLib 2.80.0 | PASS for existing tests and graphics extension build/import | Commands above; no real GUI or GL context test |
| GTK 4.0 selected minimum target | NOT TESTED | No GTK 4.0 runtime/build available |
| Other GTK4 minors / latest stable | NOT TESTED | Only GTK 4.14.5 is installed locally |
| Linux Wayland | NOT TESTED | No Wayland UI/GL session exercised |
| Linux X11 GUI / real OpenGL context | NOT TESTED | No GUI/context smoke test in EH4-002 |
| Windows native GTK4 | NOT TESTED | No Windows runner available in this session |
| macOS native GTK4 (arm64 / x86_64) | NOT TESTED | No macOS runner available in this session |

The GTK project website listed GTK 4.22.5 as the latest stable release on
2026-10-17 ([release status](https://www.gtk.org/)); this runtime was not
installed or tested. GTK 4.0 is the selected minimum target, not yet a
validated minimum. See `GTK4_COMPATIBILITY.md` for the API audit and target
contract.

No runtime application or scientific behavior was modified in EH4-002, so no
new behavioral regression test was needed; the existing test suite and a
compiled-extension import smoke check were run.
