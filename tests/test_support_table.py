"""EH4-603: the support table lists only what an artifact proves."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("support_table", ROOT / ".github" / "scripts" / "support_table.py")
support_table = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(support_table)

PASSING = """GTK_REQUESTED=4.24 OS=windows-x86_64 STATUS=SETUP_PENDING
OS=Windows-2022Server-10.0.20348-SP0 ARCH=AMD64 PYTHON=3.12.15 PYGOBJECT=3.58.1 GTK=4.24.1 GLIB=2.90.1 GDK_PIXBUF_API=2.0 (imported) PROVIDER=conda-forge
66 passed, 6 skipped in 18.09s
EASYHYBRID_SCIENTIFIC_TESTS=31 passed in 4.35s
EASYHYBRID_FULL_APP_GL_RENDERER=llvmpipe (LLVM 23.1.2, 256 bits)
""" + "EASYHYBRID_FULL_APP_STATUS=0 CLOSED=True\n" * 5 + "3 passed in 77.98s\n"


def _write(tmp_path, name, text):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "platform-results.txt").write_text(text, encoding="utf-8")


def test_passing_cell_records_loaded_versions(tmp_path):
    _write(tmp_path, "gtk-4.24-windows-x86_64-results", PASSING)
    (row,) = support_table.collect(tmp_path)
    assert row["result"] == "PASS"
    assert (row["cell"], row["gtk"], row["glib"], row["pygobject"]) == ("windows-x86_64", "4.24.1", "2.90.1", "3.58.1")
    assert row["renderer"].startswith("llvmpipe")
    assert (row["full_app_cycles"], row["scientific"]) == (5, 31)


def test_incomplete_or_failing_cells_are_never_pass(tmp_path):
    # A cancelled attempt's partial artifact: setup lines only.
    _write(tmp_path, "partial", PASSING.split("66 passed")[0])
    _write(tmp_path, "failed", PASSING.replace("3 passed in 77.98s", "1 failed, 2 passed in 77.98s"))
    _write(tmp_path, "four-cycles", PASSING.replace("EASYHYBRID_FULL_APP_STATUS=0 CLOSED=True\n", "", 1))
    _write(tmp_path, "no-science", PASSING.replace("EASYHYBRID_SCIENTIFIC_TESTS=31 passed in 4.35s\n", ""))
    rows = support_table.collect(tmp_path)
    assert len(rows) == 4 and all(row["result"] == "FAIL" for row in rows)


def test_cells_without_runtime_record_are_not_listed(tmp_path):
    _write(tmp_path, "no-runtime", "GTK_REQUESTED=4.8 OS=linux-x86_64 STATUS=SETUP_PENDING\n")
    assert support_table.collect(tmp_path) == []
    text = support_table.render([], run="1", commit="abc")
    assert "NOT TESTED" in text and "0 of 0 tested cells pass." in text
