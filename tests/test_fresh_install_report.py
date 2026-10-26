"""EH4-600: the fresh-install report checks exactly the extensions setup.py builds."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "fresh_install_report", ROOT / ".github" / "scripts" / "fresh_install_report.py")
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def test_commented_out_extensions_are_not_expected():
    text = '''ext = [
    Extension("vismol.utils.PDBFiles",
              sources=["src/vismol/utils/PDBFiles.pyx"]),
    #Extension("vismol.utils.cartoon",
    #          sources=["src/vismol/utils/cartoon.pyx"]),
]'''
    assert report.declared_extensions(text) == ["vismol.utils.PDBFiles"]


def test_graphics_engine_declares_the_seven_built_extensions():
    names = report.declared_extensions((ROOT / "src" / "graphics_engine" / "setup.py").read_text())
    assert len(names) == 7 and "vismol.utils.cartoon" not in names


def test_native_library_filter_is_platform_neutral():
    assert all(map(report._native, ["/usr/lib/libgtk-4.so.1", "C:/x/gtk-4-1.dll",
                                    "/opt/lib/libglib-2.0.0.dylib", "a/b.pyd"]))
    assert not report._native("/usr/share/fonts/DejaVuSans.ttf")
