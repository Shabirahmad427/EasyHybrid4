# EasyHybrid4

EasyHybrid4 is the GTK4 port of Bachega's EasyHybrid3 graphical environment
for pDynamo3. It aims to preserve EasyHybrid3's interface, scientific
workflows, VisMol graphics engine, and project compatibility while using GTK4
APIs. See the [consolidated development report](docs/EASYHYBRID4_REPORT.md)
for compatibility, parity, and testing status.

> **Development status:** EasyHybrid4 requests the GTK 4.0 introspection
> namespace and has a GTK 4.8 runtime minimum. The full native GTK matrix passed
> on 2026-10-19 (30/30 cells): Linux x86_64, Windows x86_64, and macOS arm64
> across GTK 4.8–4.24, plus provisioned Intel macOS GTK 4.8/4.10. Each cell
> opened the EasyHybrid production menu and VisMol molecular scene, rendered
> twice, and closed cleanly. Linux uses Xvfb/llvmpipe, Windows uses Mesa WGL,
> and macOS uses the hosted Apple OpenGL runtime. Physical GPU coverage,
> Wayland, Retina/trackpad behavior, packaging, and pDynamo3 scientific
> validation on Windows/macOS remain separate checks. See the
> [consolidated report](docs/EASYHYBRID4_REPORT.md#3-gtk4-python-and-dependency-compatibility)
> and [exact GTK matrix evidence](docs/GTK4_COMPATIBILITY.md#full-gtk4-minor-matrix-2026-10-19).
> Full GUI verification needs a graphical desktop session.
> EasyHybrid3 remains unchanged and usable. The migration summary and GTK
> rules are in the consolidated report.

**HiDPI input follow-up:** GTK event positions use logical widget coordinates,
while VisMol picking uses GL framebuffer pixels. A shared measured-scale
conversion now handles pointer input. The oxygen atom was picked through the
real GTK event path twice at GTK 4.14.5 on Linux X11/NVIDIA with `GDK_SCALE=2`;
the full GTK/OS matrix (run `39317377076`, 30/30) accepted it together with
the portable fixed-width picking fix for macOS.

EasyHybrid is developed using Python, Cython, GTK, and modern OpenGL. It
allows users to run common pDynamo routines in a graphical interface and to
inspect, edit, and export pDynamo systems for simulations using Python scripts.

<img width="1589" height="908" alt="image" src="https://github.com/user-attachments/assets/fd399057-fd9d-47f4-b325-92f98f270b98" />

The interface has been designed to make it easy to determine reaction pathways in biological systems, particularly when using hybrid quantum mechanics/molecular mechanics (QC/MM) methods. EasyHybrid allows users to access a variety of pDynamo capabilities within its graphical environment, including:

Pure quantum chemistry (QC) simulations, both ab initio and semi-empirical

Pure molecular mechanics (MM) simulations using AMBER, CHARMM, or OPLS force fields

Hybrid QC/MM simulations

Single point calculations

Energy minimization

Molecular dynamics

Reaction coordinate scanning

Umbrella sampling

Reaction path calculations

# Cloning and Installation

Clone the EasyHybrid4 repository using:

```bash
git clone --recurse-submodules https://github.com/Shabirahmad427/EasyHybrid4.git EasyHybrid4
```

EasyHybrid4 includes the graphics engine as ordinary tracked files under
`src/graphics_engine`. The `.gitmodules` entry is historical metadata; there
is no graphics-engine gitlink for `--recurse-submodules` to fetch. EasyHybrid3
remains an independent behavioral reference and is not cloned by this command.

## Verify the graphics engine source

After cloning, verify that the vendored engine sources are present:

```bash
test -f EasyHybrid4/src/graphics_engine/setup.py
test -f EasyHybrid4/src/graphics_engine/src/vismol/__init__.py
```

Build its Cython extensions from the repository root:

```bash
cd EasyHybrid4/src/graphics_engine
python3 setup.py build_ext --inplace
```

## Installation

The application uses native GTK 4, GLib and GObject-introspection packages;
`pip install -r requirements.txt` alone is not enough. The commands below
create a developer environment; they do not install pDynamo3 or create a
standalone application package. Use Micromamba 2.9.0 or newer (the Windows
GTK 4.8/4.10 workflow needs its `--skip-run-link-scripts` support) and
conda-forge. The Linux x86_64 explicit lock is the exact replay option; the
other commands are compatible baseline specifications, not full transitive
locks.

On Linux x86_64, replay the verified explicit lock:

```bash
micromamba create --yes --prefix "$PWD/.conda/easyhybrid4-linux-64" \
  --file environments/easyhybrid4-linux-64.lock
micromamba run --prefix "$PWD/.conda/easyhybrid4-linux-64" python --version
```

On Windows x86_64, in PowerShell:

```powershell
micromamba create -n easyhybrid4 -c conda-forge `
  python=3.12 gtk4=4.24.1 glib-tools pygobject pycairo pyopengl `
  numpy scipy cython pillow freetype-py pyyaml psutil pytest setuptools
micromamba activate easyhybrid4
$env:PYTHONNOUSERSITE = '1'
```

On macOS arm64, in a terminal:

```bash
micromamba create -n easyhybrid4 -c conda-forge \
  python=3.12 gtk4=4.24.1 glib-tools pygobject pycairo pyopengl \
  numpy scipy cython pillow freetype-py pyyaml psutil pytest setuptools
micromamba activate easyhybrid4
export PYTHONNOUSERSITE=1
```

The baseline developer environment for GTK 4.24 can also be created on Linux
with:

```bash
micromamba create -n easyhybrid4 -c conda-forge \
  python=3.12 gtk4=4.24.1 glib-tools pygobject pycairo pyopengl \
  numpy scipy cython pillow freetype-py pyyaml psutil pytest setuptools
micromamba activate easyhybrid4
```

The explicit lock is Linux x86_64 only. The native GTK workflow provisions
clean environments on Linux, Windows and macOS, but uses platform-specific
GTK providers for some matrix cells; this does not make its workflow a general
installer or qualify every GTK minor for interactive use. Exact hosted runtime
evidence is recorded in [`docs/GTK4_COMPATIBILITY.md`](docs/GTK4_COMPATIBILITY.md).

When building from an environment on a machine with user-installed Python
packages, disable the user site so NumPy headers and Python packages come from
the selected environment. For Bash, run `export PYTHONNOUSERSITE=1` before the
build; in PowerShell, run `$env:PYTHONNOUSERSITE = '1'`.

Install a native compiler toolchain before building the graphics extensions:
GCC and Python development headers on Linux (for example, `build-essential`),
Visual Studio 2022 C++ Build Tools on Windows, or Xcode Command Line Tools on
macOS. GTK 4.24.1 is the verified baseline pin here; change it only to a patch
version available from conda-forge for the chosen OS. This does not lock every
transitive package. The native matrix documents its separate providers for
GTK minors that conda-forge does not publish.

Build the bundled VisMol Cython extensions from the repository root:

```bash
cd src/graphics_engine
python setup.py build_ext --inplace
cd ../..
```

Install and compile pDynamo3 separately, then set `PDYNAMO3_HOME`,
`PDYNAMO3_PARAMETERS` and `PDYNAMO3_SCRATCH` for that checkout. On Linux and
macOS, add the repository and pDynamo3 checkout to `PYTHONPATH`; in PowerShell
use semicolons between paths. For example, from the repository root:

```bash
export PDYNAMO3_HOME="$HOME/software/pDynamo3"
export PDYNAMO3_PARAMETERS="$PDYNAMO3_HOME/parameters"
export PDYNAMO3_SCRATCH="${TMPDIR:-/tmp}/easyhybrid-scratch"
export PYTHONPATH="$PWD:$PWD/src/graphics_engine/src:$PDYNAMO3_HOME${PYTHONPATH:+:$PYTHONPATH}"
python easyhybrid.py
```

The equivalent PowerShell setup is:

```powershell
$env:PDYNAMO3_HOME = 'C:\pDynamo3'
$env:PDYNAMO3_PARAMETERS = "$env:PDYNAMO3_HOME\parameters"
$env:PDYNAMO3_SCRATCH = "$env:TEMP\easyhybrid-scratch"
$env:PYTHONPATH = "$PWD;$PWD\src\graphics_engine\src;$env:PDYNAMO3_HOME"
python .\easyhybrid.py
```

`install.py` can check dependencies, build extensions, and create a launcher
for the configured environment, but it does not install GTK or pDynamo3. The
shell launcher `activate_easyhybrid4.sh` is Linux/macOS-only. The supported
GTK/OS provisioning used by native compatibility tests is maintained in
[`.github/workflows/native-gtk-matrix.yml`](.github/workflows/native-gtk-matrix.yml).
Windows and macOS interactive installation has not yet been qualified as a
release path.

## Candidate distribution paths

Distribution should follow each platform's native runtime model rather than
trying to ship one identical archive everywhere:

- **Linux:** provide a relocatable conda environment archive with a small
  desktop-entry installer. The bundle launcher is
  [`packaging/linux/run-easyhybrid4.sh`](packaging/linux/run-easyhybrid4.sh);
  it expects `app/` and a conda-packed `runtime/` alongside it and uses an
  external compiled pDynamo3 checkout. Keep system display and OpenGL drivers
  outside the archive; verify GTK typelibs and graphics-driver discovery on
  the target distribution.
- **Windows:** provide a per-user installer/bootstrapper that creates or
  updates a pinned micromamba environment and registers a Start-menu shortcut.
  Keep the GTK DLL and typelib environment together, and do not rely on a
  system-wide GTK installation.
- **macOS:** provide a signed `.app` launcher that uses a managed arm64 conda
  environment and resolves its GTK frameworks, typelibs and OpenGL runtime
  from that environment. Intel macOS would require a separate x86_64 build.

These are candidate designs only. No Linux archive, Windows installer, or
macOS app bundle has yet been built, independently installed, launched, or
qualified with a separately configured pDynamo3 installation. They are not
release artifacts or platform support claims.

## Running EasyHybrid

Once the graphics engine has been successfully compiled, you can launch EasyHybrid by running:

```bash
./activate_easyhybrid4.sh
```

## Development and compatibility status

See the [consolidated development report](docs/EASYHYBRID4_REPORT.md). The
permanent task queue is [`docs/ROADMAP.md`](docs/ROADMAP.md).


# References
pDynamo:

  The second edition of the book M. J. Field, A Practical Introduction to the Simulation of Molecular Systems published by Cambridge University Press in 2007 [Amazon UK, Amazon US, CUP].

  The paper M. J. Field, The pDynamo Library for Molecular Simulations using Hybrid Quantum Mechanical and Molecular Mechanical Potentials, J. Chem. Theo. Comp. 4, 1151–1161 (2008) [Link]. This paper provides a general introduction to pDynamo and its QC models and hybrid potentials.

  pDynamo3 paper Martin J. Field Journal of Chemical Information and Modeling 2022 62 (23), 5849-5854 DOI: 10.1021/acs.jcim.2c01239 

EasyHybrid:
  Bachega, J. F. R., Hagen, G., Sequeiros-Borja, C., Nikklas, K., Chahine, J., Timmers, L. F. M., & Field, M. J. (2025). EasyHybrid: An interactive graphical environment for quantum, classical and hybrid simulations with pDynamo3. Journal of Chemical Information and Modeling.


important links:

https://sites.google.com/view/easyhybrid/home?authuser=0  (docs and tutorials)

https://github.com/casebor/graphics_engines (engine based on OpenGL)

https://www.pdynamo.org/home (pDynamo website)

https://github.com/pdynamo/pDynamo3 
