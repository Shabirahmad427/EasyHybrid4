# Third-party notices and audit findings (EH4-602)

Audit date: 2026-10-25. Licenses below were read from the components
themselves (license files, font name tables, installed package metadata in a
conda-forge GTK 4.24.1 / Python 3.12.15 environment), not inferred.

## EasyHybrid4

| Component | License | Source |
|---|---|---|
| EasyHybrid4 application (`src/`, except the graphics engine) | GPL-3.0 | `LICENSE` |

## Bundled in this repository

| Component | Path | License | Source of the license statement |
|---|---|---|---|
| VisMol graphics engine | `src/graphics_engine/` | **CC BY-NC 4.0** | `src/graphics_engine/LICENSE` |
| Amiko fonts (Regular, SemiBold, Bold) © 2014 Impallari Type | `src/graphics_engine/src/vismol/libgl/fonts/` | SIL OFL 1.1 | font name table; full text in `LICENSE-Amiko-OFL.txt` |
| Bitstream Vera Sans / Sans Mono © 2003 Bitstream, Inc. | same folder | Bitstream Vera license | font name table; full text in `LICENSE-Bitstream-Vera.txt` |
| Application icons (`src/gui/icons/`, 50 files) | `src/gui/icons/` | **unknown** | no license or provenance recorded |

## Required at run time (installed separately, not bundled)

| Component | Version checked | License (from package metadata) |
|---|---|---|
| pDynamo3 | `6b28dd8` | GPL-3.0 (`gpl-3.0.txt` in pDynamo3) |
| GTK 4 | 4.24.1 | LGPL-2.0-or-later |
| Pango | 1.58.2 | LGPL-2.1-or-later |
| cairo | 1.18.6 | LGPL-2.1-only or MPL-1.1 |
| GdkPixbuf | 2.44.8 | LGPL-2.1-or-later |
| FreeType | 2.14.3 | GPL-2.0-only OR FTL |
| Python | 3.12.15 | Python-2.0 (PSF) |
| PyGObject | 3.58.1 | LGPL-2.1-or-later |
| pycairo | 1.29.2 | LGPL-2.1-only OR MPL-1.1 |
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| SciPy | 1.18.1 | BSD License |
| PyOpenGL | 3.1.10 | BSD License |
| Pillow | 13.0.0 | MIT-CMU |
| PyYAML | 6.0.3 | MIT |
| Cython (build) | 3.3.0 | Apache-2.0 |
| freetype-py | 2.5.1 | BSD License |
| psutil | 7.2.2 | BSD-3-Clause |

Development tools (not distributed): pytest (MIT), Ruff, mypy.

## Findings

| # | Finding | Status |
|---|---|---|
| 1 | **License conflict.** The application is GPL-3.0 but the bundled VisMol graphics engine is CC BY-NC 4.0. A non-commercial restriction is not GPL-compatible, and Creative Commons licenses are not intended for software. Distributing both together under a single license is not consistent. | **Accepted and documented (maintainer decision, 2026-10-26).** The conflict is not resolved by relicensing; instead it is stated plainly: the application code is GPL-3.0, the graphics engine in `src/graphics_engine/` remains CC BY-NC 4.0, and because EasyHybrid4 cannot run without it, **EasyHybrid4 as distributed may be used and redistributed for non-commercial purposes only**. The README License section says the same, and the project must never be described as GPL-only. Commercial use needs separate permission from the VisMol copyright holders. |
| 2 | Bundled fonts shipped without their license texts (OFL 1.1 and the Bitstream Vera license require distribution with the fonts). | **Fixed:** license files added next to the fonts, from the fonts' own name tables and the canonical SPDX OFL-1.1 text. Packages must keep them. |
| 3 | Icons have no recorded license or provenance. | **Open — needs the maintainer** to state their origin. |
| 4 | The MOPAC and SPARROW wrappers (`src/util/extras`, installed into pDynamo by `install.py`) built shell commands with unquoted paths and the POSIX-only `> /dev/null`, run through `os.system`: paths with spaces (common on Windows) broke, and shell metacharacters in a path would be interpreted. | **Fixed:** argument lists through `subprocess.run`, same flags and output handling (`tests/test_qc_engine_commands.py`). The xTB wrapper already used this pattern; its `os.system` is in a dead docstring. |
| 5 | `.easy` projects and pDynamo worker/trajectory data use Python `pickle`. Loading a pickle can execute code. | **Accepted with rationale:** these are local project files the user created; format and version are validated before loading (EH4-404). Users must not open `.easy` files from untrusted sources. |
| 6 | GLib warning `g_error_free: assertion 'error != NULL' failed` during chooser cancel tests on headless Linux GTK 4.10–4.14 (found by Codex in run `40161896666`); suites pass. | **Accepted:** raised by GTK while tearing down choosers without a desktop portal, not by EasyHybrid code (inferred, not proven upstream). |
| 7 | `install.py` wrote user paths as code: the xTB path into a sourced bash script as `export VAR="…"` (`$`, backticks and quotes still expand), and the pDynamo3 path into `paths.py` as a plain Python string, where a Windows path like `C:\Users\…` makes `\U` a unicode escape — a SyntaxError that stops EasyHybrid from starting (`easyhybrid.py` imports it). | **Fixed:** `shlex.quote` for the shell line, `repr()` for the Python literal (`tests/test_installer_path_quoting.py`, which sources the script in bash and compiles `paths.py` for a Windows path). |
