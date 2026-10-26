# Fresh source install check

This procedure checks a clean EasyHybrid4 source checkout with a working GTK 4
runtime, pDynamo3, and a Cython compiler. It reproduces the automated source
install acceptance used by the native GTK matrix. It does not create a
self-contained application bundle; platform GTK and scientific dependencies
must be installed separately.

## Prerequisites

- Python 3.12 and pip in an isolated environment.
- GTK 4.8 or newer, its GObject introspection data, PyGObject, and PyCairo.
- A C compiler and the native development headers required by GTK, Cairo,
  NumPy, and the graphics engine. On macOS, install the Xcode Command Line
  Tools before building Cython extensions.
- A built and configured pDynamo3 checkout. Set `PDYNAMO3_HOME` to its root
  and make its Python modules available to the selected Python environment.
- The Python packages listed by `install.py` and the graphics engine setup
  (`numpy`, `scipy`, `PyOpenGL`, `Pillow`, `PyYAML`, `freetype-py`, `pycairo`,
  `Cython`, and `psutil`). Install binary scientific dependencies using the
  method supported by your OS and pDynamo3 environment.
- A graphical desktop session and working OpenGL implementation for the
  final launch-and-close check.

EasyHybrid4 supports native source-checkout workflows. GTK development
packages and binary scientific libraries are platform-specific, so these
prerequisites are not one universal pip command. See the root
[installation instructions](../README.md#cloning-and-installation) and the
[compatibility report](EASYHYBRID4_REPORT.md) for current limits.

## Reproduce the install and data checks

Clone the repository and its recorded submodule metadata, then enter the
checkout:

```sh
git clone --recurse-submodules https://github.com/Shabirahmad427/EasyHybrid4.git
cd EasyHybrid4
```

Set `PDYNAMO3_HOME` in the shell, then run the installer's non-interactive CI
mode. This checks the current Python/GTK dependencies, locates pDynamo3, and
builds the seven graphics-engine Cython extensions.

```sh
export PDYNAMO3_HOME="/absolute/path/to/pDynamo3"
python install.py --ci
```

In Windows PowerShell, use the equivalent environment assignment:

```powershell
$env:PDYNAMO3_HOME = "C:\path\to\pDynamo3"
python install.py --ci
```

Run the fresh-install report with the same Python interpreter. It imports
GTK, pDynamo3 and each built extension; records loaded native libraries; loads
the bundled PDB, MOL2, XYZ and Amber samples with pDynamo3; and reads the PDB
through VisMol's parser.

```sh
python .github/scripts/fresh_install_report.py .
```

The check passes when it ends with `FRESH_INSTALL_REPORT=PASS`. The report
prints `FRESH_INSTALL_EXTENSION` for each extension, `FRESH_INSTALL_LIBRARY`
and `FRESH_INSTALL_LIBRARIES` for loaded native images, and a
`FRESH_INSTALL_SAMPLE` line for each sample type. A successful fresh install
does not by itself prove that the application can open a native window.

Launch the application from the same configured environment and close it
through its window controls to check the local desktop, GTK and GL stack:

```sh
./activate_easyhybrid4.sh
```

On Windows, launch the Python entry point from the configured environment:

```powershell
python easyhybrid.py
```

## Native matrix evidence

Run [40343882287](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40343882287)
passed all 30 configured jobs: Linux x86_64, Windows x86_64 and macOS arm64
for GTK 4.8 through 4.24, plus Intel macOS GTK 4.8 and 4.10. Each cell
performed the fresh source checkout, installer/build, extension and native
library report, pDynamo3 sample loads, VisMol PDB read, and a native window
launch and clean close. All 30 downloaded `platform-results.txt` artifacts
contain `FRESH_INSTALL_REPORT=PASS` and
`SOURCE_CHECKOUT_NATIVE_CLOSE=PASS EXIT=0`.

The exact GTK patch, OS and architecture, Python, PyGObject, GLib, and renderer
are recorded in each artifact. The GTK runtimes range from 4.8.2 through
4.24.1; source-built cells use their recorded patch versions. Linux used
hosted Xvfb/software GL, Windows used hosted Mesa WGL, and macOS used the
hosted Apple Software Renderer. These hosted checks do not establish support
for physical GPUs, Linux Wayland, Retina/HiDPI, trackpads, or a user's local
scientific-library configuration.
