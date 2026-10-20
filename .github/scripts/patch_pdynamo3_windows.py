"""Make pDynamo3's Unix-only installer build on Windows (CI only).

pDynamo3's installation/InstallUtilities.py assumes a Unix toolchain. On
Windows it fails before any scientific code is involved:

* every Cython extension gets ``runtime_library_dirs`` (an rpath), which
  setuptools rejects on Windows (MSYS2/MinGW: "Unable to set runtime
  library search path on Windows");
* built extensions are looked up as ``<name>.<cache_tag>*.so`` and renamed
  to ``.so``; Windows extensions are ``<name><EXT_SUFFIX>`` ending in .pyd;
* static libraries are assumed to be ``lib<name>.a``; MSVC writes
  ``<name>.lib`` (conda: "The system cannot find the file specified:
  ...\\libdcCore.a");
* MSVC only: extensions link the Unix maths library ``m``, and the
  per-library optimisation levels (``-O0`` for LAPACK's dlamch, ``-O3`` for
  BLAS/LAPACK) are gcc flags; stripping them uses ``compiler_so``, which
  MSVCCompiler does not have.

This script edits only the installer, never pDynamo3's scientific sources,
and each edit must match the pinned upstream text exactly. Usage:

    python patch_pdynamo3_windows.py <pDynamo3 checkout> [--force]

Without ``--force`` it does nothing outside Windows.
"""

import os
import sys
from pathlib import Path

MARKER = "# . EasyHybrid4 CI: Windows toolchain support"

EDITS = (
    (
        '_SharedObjectBuildPathExtension = ( "." + sys.implementation.cache_tag + "*" + _SharedObjectExtension )\n',
        '_SharedObjectBuildPathExtension = ( "." + sys.implementation.cache_tag + "*" + _SharedObjectExtension )\n'
        + MARKER + ".\n"
        "# . Windows extensions are <name><EXT_SUFFIX> (.pyd); static library names and\n"
        "# . flags follow the active compiler (MinGW gcc or MSVC); no rpath exists.\n"
        "_IsWindows = ( os.name == \"nt\" )\n"
        "_UsesMSVC  = _IsWindows and ( \"GCC\" not in sys.version )\n"
        "if _IsWindows:\n"
        "    import importlib.machinery\n"
        "    _SharedObjectExtension          = \".pyd\"\n"
        "    _SharedObjectBuildPathExtension = importlib.machinery.EXTENSION_SUFFIXES[0]\n"
        "def _StaticLibraryFileName ( name ):\n"
        "    \"\"\"The static library file name the active compiler writes.\"\"\"\n"
        "    from distutils.ccompiler import new_compiler\n"
        "    return new_compiler ( ).library_filename ( name, lib_type = \"static\" )\n",
    ),
    (
        '_SystemLibraries    = [ "m" ]\n',
        '_SystemLibraries    = [ "m" ]\n'
        "if _UsesMSVC: _SystemLibraries = [ ]  # . The maths functions are in the MSVC C runtime.\n",
    ),
    (
        '_OptimizationFlagPrefix = "-O"\n',
        '_OptimizationFlagPrefix = "-O"\n'
        "if _UsesMSVC:\n"
        "    _FullOptimizationFlag   = \"/O2\"\n"
        "    _NoOptimizationFlag     = \"/Od\"\n"
        "    _OptimizationFlagPrefix = \"/O\"\n",
    ),
    (
        """            if build_info.get ( "removeOptimizationFlags", False ):
                new = []
                for token in self.compiler.compiler_so:
                    if not token.startswith ( _OptimizationFlagPrefix ): new.append ( token )
                self.compiler.compiler_so = new
""",
        """            if build_info.get ( "removeOptimizationFlags", False ):
                if _UsesMSVC:
                    # . MSVCCompiler initialises lazily; its /O defaults would follow (and override) extra_preargs.
                    if not getattr ( self.compiler, "initialized", True ): self.compiler.initialize ( )
                    self.compiler.compile_options = [ token for token in self.compiler.compile_options if not token.startswith ( _OptimizationFlagPrefix ) ]
                else:
                    new = []
                    for token in self.compiler.compiler_so:
                        if not token.startswith ( _OptimizationFlagPrefix ): new.append ( token )
                    self.compiler.compiler_so = new
""",
    ),
    (
        'os.rename ( os.path.join ( buildPath, "lib" + libraryName + _LibraryExtension ), os.path.join ( self.cLibraryPath, "lib" + libraryName + _LibraryExtension ) )',
        'os.rename ( os.path.join ( buildPath, _StaticLibraryFileName ( libraryName ) ), os.path.join ( self.cLibraryPath, _StaticLibraryFileName ( libraryName ) ) )',
    ),
    (
        "runtime_library_dirs = libraryDirectories ) )",
        "runtime_library_dirs = ( None if _IsWindows else libraryDirectories ) ) )",
    ),
)


def patch(root, force=False):
    path = Path(root) / "installation" / "InstallUtilities.py"
    if os.name != "nt" and not force:
        print("PDYNAMO3_WINDOWS_PATCH=not-needed")
        return
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print("PDYNAMO3_WINDOWS_PATCH=already-applied")
        return
    for old, new in EDITS:
        count = text.count(old)
        if count != 1:
            raise SystemExit("pDynamo3 installer changed; expected one match, found %d: %r" % (count, old[:80]))
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("PDYNAMO3_WINDOWS_PATCH=applied (%d edits)" % len(EDITS))


if __name__ == "__main__":
    arguments = [argument for argument in sys.argv[1:] if argument != "--force"]
    if len(arguments) != 1:
        raise SystemExit(__doc__)
    patch(arguments[0], force="--force" in sys.argv)
