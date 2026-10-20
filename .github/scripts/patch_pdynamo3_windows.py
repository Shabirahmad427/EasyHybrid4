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
* MSVC only: its traditional preprocessor mis-expands pDynamo3's nested
  ``_MakeToken`` token pasting (Array1D_Header.i: "syntax error: missing
  ';' before '*'"), so ``/Zc:preprocessor`` is added; extensions link the
  Unix maths library ``m``; and the
  per-library optimisation levels (``-O0`` for LAPACK's dlamch, ``-O3`` for
  BLAS/LAPACK) are gcc flags; stripping them uses ``compiler_so``, which
  MSVCCompiler does not have.

* MSVC only: ``View1D_Fields`` ends in ``;`` and is used as
  ``View1D_Fields ;`` inside a struct, leaving an empty member declaration
  that gcc/clang accept and MSVC rejects (View1D.h(32): "syntax error:
  ';'"), which cascades into every pScientific array header.
  ``View2D_Fields`` already omits that semicolon; View1D is made to match.
* MSVC only: ViewND_MakeIterator uses C99 variable length arrays, which
  MSVC does not support (ViewND.c(364): "expected constant expression");
  they become equivalent _alloca stack allocations.
* MSVC only: <math.h> defines M_PI, M_LN10, ... only with
  ``_USE_MATH_DEFINES`` (addOns/pcetk EnergyModel.c: "'M_LN10':
  undeclared identifier"), so it is defined for the whole build.
* MinGW only: pBabel's fastio.h selects its native Win32 I/O only for
  ``_MSC_VER``, so MinGW took the Unix branch (``<sys/uio.h>``, absent);
  it now selects Win32 for any ``_WIN32`` compiler.

The edits touch only the installer, that macro, those two stack arrays
and that platform condition
(no field, type or calculation changes), and each must match the pinned upstream text
exactly. Usage:

    python patch_pdynamo3_windows.py <pDynamo3 checkout> [--force]

Without ``--force`` it does nothing outside Windows.
"""

import os
import shutil
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
        "_WindowsIncludePath = os.path.join ( os.path.dirname ( os.path.dirname ( os.path.abspath ( __file__ ) ) ), \"windows_include\" )\n"
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
        """            else: item = []
            setattr ( self, "_compilerFlags", item )
""",
        """            else: item = []
            # . MSVC's traditional preprocessor mis-expands the nested _MakeToken
            # . token pasting (pScientific Array*_Header.i); use the conforming one.
            # . Minimal POSIX headers missing on Windows (PRIMME timers, strcasecmp):
            # . MSVC lacks <unistd.h>, <strings.h>, <sys/time.h>, <sys/resource.h>;
            # . MinGW lacks <sys/resource.h>. See pDynamo3/windows_include.
            # . MSVC's <math.h> defines M_PI, M_LN10, ... only with _USE_MATH_DEFINES.
            if _UsesMSVC  : item = item + [ "/Zc:preprocessor", "/D_USE_MATH_DEFINES", "/I" + os.path.join ( _WindowsIncludePath, "msvc" ) ]
            elif _IsWindows: item = item + [ "-I" + os.path.join ( _WindowsIncludePath, "mingw" ) ]
            setattr ( self, "_compilerFlags", item )
""",
    ),
    (
        """                        build_info["macros"       ] = None
""",
        """                        build_info["macros"       ] = None
                        if _IsWindows and ( libraryName == "dcprimme" ):
                            # . PRIMME's gethostname() (diagnostics only) has no Windows declaration.
                            header = os.path.join ( _WindowsIncludePath, "primme_gethostname.h" )
                            build_info["extra_preargs"].extend ( [ "/FI" + header ] if _UsesMSVC else [ "-include", header ] )
""",
    ),
    (
        "runtime_library_dirs = libraryDirectories ) )",
        "runtime_library_dirs = ( None if _IsWindows else libraryDirectories ) ) )",
    ),
)


# . Portability edits outside the installer: (relative path, old, new).
SOURCE_EDITS = (
    (
        "pScientific/Arrays/__extensions__/cinclude/View1D.h",
        "    Integer size   ; \\\n    Integer stride ;\n",
        "    Integer size   ; \\\n    Integer stride\n",
    ),
    # . fastio.h picks its native Win32 file I/O only for MSVC; MinGW gcc fell
    # . into the Unix branch and its <sys/uio.h>. Use Win32 for any Windows.
    (
        "pBabel/__extensions__/cinclude/fastio.h",
        "#if defined(_MSC_VER)\n",
        "#if defined(_MSC_VER) || defined(_WIN32)\n",
    ),
    # . The only C99 variable length arrays in pDynamo3's C sources (gcc -Wvla
    # . over every extension file); MSVC has none. _alloca gives the same
    # . stack storage, size and lifetime.
    (
        "pScientific/Arrays/__extensions__/csource/ViewND.c",
        "# include <stdio.h>\n",
        "# include <stdio.h>\n# include <malloc.h>\n",
    ),
    (
        "pScientific/Arrays/__extensions__/csource/ViewND.c",
        "        auto Integer     rank, extents[self->rank], strides[self->rank] ;\n",
        "        auto Integer     rank ;\n"
        "        auto Integer    *extents = ( Integer * ) _alloca ( ( size_t ) self->rank * sizeof ( Integer ) ) ;\n"
        "        auto Integer    *strides = ( Integer * ) _alloca ( ( size_t ) self->rank * sizeof ( Integer ) ) ;\n",
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
    for relative, old, new in SOURCE_EDITS:
        source = Path(root) / relative
        content = source.read_text(encoding="utf-8")
        if content.count(old) != 1:
            raise SystemExit("pDynamo3 source changed; expected one match in %s" % relative)
        source.write_text(content.replace(old, new), encoding="utf-8")
    shutil.copytree(Path(__file__).with_name("pdynamo3_windows_include"),
                    # Outside installation/: setup() runs there and setuptools'
                    # flat-layout discovery rejects a second top-level folder.
                    Path(root) / "windows_include", dirs_exist_ok=True)
    print("PDYNAMO3_WINDOWS_PATCH=applied (%d installer edits, %d source edits)"
          % (len(EDITS), len(SOURCE_EDITS)))


if __name__ == "__main__":
    arguments = [argument for argument in sys.argv[1:] if argument != "--force"]
    if len(arguments) != 1:
        raise SystemExit(__doc__)
    patch(arguments[0], force="--force" in sys.argv)
