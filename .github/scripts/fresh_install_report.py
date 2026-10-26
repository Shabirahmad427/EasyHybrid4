#!/usr/bin/env python3
"""Report what a fresh source install actually links and loads (EH4-600).

Run with the checkout's Python after ``install.py --ci``. It imports every
compiled VisMol extension, GTK 4 and pDynamo3, then lists the native
libraries mapped into the process (psutil works the same on Linux, Windows
and macOS). Finally it reads the bundled sample data through pDynamo3 and
the VisMol readers and fails unless every sample yields atoms.
"""

from __future__ import annotations

import importlib
import os
import re
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path.cwd()).resolve()
NATIVE_SUFFIXES = (".so", ".dylib", ".dll", ".pyd")
# Samples read through pDynamo3: (label, system file, optional coordinates).
SAMPLES = (
    ("pdb", "examples/pdb/1l2y.pdb", None),
    ("mol2", "examples/mol2/Fe_EDTA.mol2", None),
    ("xyz", "examples/cube/teste_molecula.xyz", None),
    ("amber", "examples/amber/crambin.top", "examples/amber/crambin.crd"),
)


def _native(path: str) -> bool:
    name = path.lower()
    return name.endswith(NATIVE_SUFFIXES) or ".so." in name


def declared_extensions(setup_text: str) -> list[str]:
    """Extension module names in setup.py; commented-out ones (cartoon) are not built."""
    return re.findall(r'^\s*Extension\(\s*"([\w.]+)"', setup_text, re.M)


def loaded_library_paths() -> list[str]:
    """Paths of native images loaded in this process, on any supported OS."""
    import psutil

    process = psutil.Process()
    if hasattr(process, "memory_maps"):  # Linux, Windows
        return [mapping.path for mapping in process.memory_maps() if mapping.path]
    if sys.platform == "darwin":  # psutil has no memory_maps() on macOS
        import ctypes

        dyld = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        dyld._dyld_image_count.restype = ctypes.c_uint32
        dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
        dyld._dyld_get_image_name.restype = ctypes.c_char_p
        return [dyld._dyld_get_image_name(i).decode()
                for i in range(dyld._dyld_image_count())]
    raise RuntimeError("cannot list loaded native libraries on " + sys.platform)


def report_linked_libraries() -> int:
    sys.path.insert(0, str(ROOT / "src" / "graphics_engine" / "src"))
    # The extensions setup.py declares; every one must import from this build.
    declared = declared_extensions((ROOT / "src" / "graphics_engine" / "setup.py").read_text())
    if not declared:
        raise RuntimeError("no Cython extensions declared in the graphics-engine setup.py")
    for name in declared:
        module = importlib.import_module(name)
        print(f"FRESH_INSTALL_EXTENSION={name} PATH={module.__file__}", flush=True)

    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk  # noqa: F401  (maps the GTK libraries)
    import pCore  # noqa: F401  (maps the pDynamo3 extensions)

    libraries = sorted(path for path in set(loaded_library_paths()) if _native(path))
    for path in libraries:
        print("FRESH_INSTALL_LIBRARY=" + path, flush=True)
    for marker in ("gtk-4", "glib-2.0", "epoxy"):
        if not any(marker in Path(path).name.lower() for path in libraries):
            raise RuntimeError(f"no loaded native library matches {marker!r}")
    print(f"FRESH_INSTALL_LIBRARIES={len(libraries)}", flush=True)
    return len(libraries)


def read_samples() -> None:
    from pBabel import ImportCoordinates3, ImportSystem

    for label, system_file, coordinates in SAMPLES:
        system = ImportSystem(str(ROOT / system_file), log=None)
        if coordinates:
            system.coordinates3 = ImportCoordinates3(str(ROOT / coordinates), log=None)
        atoms = len(system.atoms)
        if atoms == 0 or system.coordinates3 is None or system.coordinates3.rows != atoms:
            raise RuntimeError(f"sample {system_file} did not load atoms with coordinates")
        print(f"FRESH_INSTALL_SAMPLE={label} FILE={system_file} ATOMS={atoms}", flush=True)

    from vismol.utils import PDBFiles

    atoms, _frames = PDBFiles.get_topology(str(ROOT / "examples/pdb/1l2y.pdb"))
    if not atoms:
        raise RuntimeError("VisMol PDB reader returned no atoms for 1l2y.pdb")
    print(f"FRESH_INSTALL_VISMOL_PDB=PASS ATOMS={len(atoms)}", flush=True)


def main() -> int:
    os.chdir(ROOT)
    report_linked_libraries()
    read_samples()
    print("FRESH_INSTALL_REPORT=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
