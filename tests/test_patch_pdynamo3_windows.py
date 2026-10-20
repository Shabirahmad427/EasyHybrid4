"""Regression tests for the pDynamo3 Windows source compatibility patch."""

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "patch_pdynamo3_windows.py"


def _write_patch_fixture(root, namespace):
    installer = root / "installation" / "InstallUtilities.py"
    installer.parent.mkdir(parents=True)
    installer.write_text("".join(old for old, _new in namespace["EDITS"]), encoding="utf-8")

    by_path = {}
    for relative, old, _new in namespace["SOURCE_EDITS"]:
        by_path.setdefault(relative, []).append(old)
    for relative, snippets in by_path.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(snippets), encoding="utf-8")

    # This is the pinned source's term-count/loop structure. The patch must
    # leave it untouched: a sentinel is valid only because the count is zero.
    utility = root / "pMolecule/QCModel/__extensions__/csource/MNDOIntegralUtilities.c"
    utility.parent.mkdir(parents=True, exist_ok=True)
    utility.write_text(
        "const Integer NNEGATIVE[3][3] = { { 0, 0, 0 }, { 0, 0, 7 }, { 0, 7, 50 } };\n"
        "nnegative = NNEGATIVE[iam][jam];\n"
        "if (jam == 0) negative = SNEGATIVE;\n"
        "for (c = t = 0; c < nnegative; c++, t += 4) use(negative[t]);\n",
        encoding="utf-8",
    )


def test_windows_patch_replaces_empty_mndo_table_with_unused_zero_sentinel(tmp_path):
    namespace = runpy.run_path(str(SCRIPT))
    _write_patch_fixture(tmp_path, namespace)

    namespace["patch"](tmp_path, force=True)

    header = (tmp_path / "pMolecule/QCModel/__extensions__/cinclude/MNDOIntegralDefinitions.h").read_text()
    source = (tmp_path / "pMolecule/QCModel/__extensions__/csource/MNDOIntegralDefinitions.c").read_text()
    utility = (tmp_path / "pMolecule/QCModel/__extensions__/csource/MNDOIntegralUtilities.c").read_text()
    assert "extern const Integer  SNEGATIVE   [  1] ;" in header
    assert "const Integer  SNEGATIVE[ 1] = { 0 } ;" in source
    assert "SNEGATIVE   [  0]" not in header
    assert "SNEGATIVE[ 0]" not in source
    assert "{ { 0, 0, 0 }, { 0, 0, 7 }, { 0, 7, 50 } }" in utility
    assert "if (jam == 0) negative = SNEGATIVE;" in utility
    assert "c < nnegative" in utility

    # Applying the compatibility patch to a cached/retried checkout is safe.
    namespace["patch"](tmp_path, force=True)
    assert "const Integer  SNEGATIVE[ 1] = { 0 } ;" in source

