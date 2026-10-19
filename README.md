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

EasyHybrid4 is currently maintained as a separate local port of EasyHybrid3.
The original EasyHybrid3 project remains available independently.

Clone it using:

```bash
git clone --recurse-submodules https://github.com/ferbachega/EasyHybrid3.git EasyHybrid4
```

This command obtains the upstream behavioral reference. The GTK4 port changes
must then be applied in the separate `EasyHybrid4` working tree.

## Verify Submodules

Make sure the graphics engine was cloned correctly by checking whether the following directory exists:

```bash
../EasyHybrid4/src/graphics_engine
```

If this folder is missing, the submodules were not downloaded properly.

## Installation

Navigate to the main EasyHybrid directory:

```bash
cd ../EasyHybrid4/
```

There, you will find the installation script:

```bash
python3 ./install.py
```

> **Note:** Make sure all required dependencies are installed before running the installer.

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
