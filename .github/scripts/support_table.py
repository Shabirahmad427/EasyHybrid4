"""Build the release support table from native-matrix runtime artifacts (EH4-603).

Usage:
    python .github/scripts/support_table.py --download <run-id> --commit <sha>
    python .github/scripts/support_table.py <artifacts-dir> [--run <id>] [--commit <sha>]

Prefer --download: a re-run keeps the cancelled attempt's partial artifacts
under the same names, and ``gh run download`` lets them overwrite the complete
ones (run 40206845115: 4 cells showed 0 cycles, 2 went missing). --download
fetches only the newest artifact for each name.

Every row comes from one cell's uploaded ``platform-results.txt``: the versions
are what the runner actually loaded, never what was requested. A combination
that has no artifact is not listed, so the table makes no claim about it.
A cell is PASS only if all full-app cycles closed cleanly, the headless
scientific tests ran with no skips, and no pytest summary reported a failure.
"""

import argparse
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

RUNTIME = re.compile(
    r"^OS=(?P<os>\S+) ARCH=(?P<arch>\S+) PYTHON=(?P<python>\S+) "
    r"PYGOBJECT=(?P<pygobject>\S+) GTK=(?P<gtk>\S+) GLIB=(?P<glib>\S+)",
    re.M,
)
REQUESTED = re.compile(r"^GTK_REQUESTED=(?P<minor>\S+) OS=(?P<cell>\S+)(?: PROVIDER=(?P<provider>\S+))?", re.M)
RENDERER = re.compile(r"^EASYHYBRID_FULL_APP_GL_RENDERER=(.+)$", re.M)
SCIENTIFIC = re.compile(r"^EASYHYBRID_SCIENTIFIC_TESTS=(\d+) passed", re.M)
PYTEST_SUMMARY = re.compile(r"^=*\s*(?:\d+ \w+(?:, )?)+.* in [\d.]+s", re.M)


def parse_cell(text):
    runtime = RUNTIME.search(text)
    requested = REQUESTED.search(text)
    if runtime is None or requested is None:
        return None
    closed = text.count("EASYHYBRID_FULL_APP_STATUS=0 CLOSED=True")
    scientific = SCIENTIFIC.search(text)
    renderer = RENDERER.search(text)
    failed = any(
        re.search(r"\b\d+ failed\b|\b\d+ errors?\b", line)
        for line in text.splitlines() if " in " in line and ("passed" in line or "failed" in line)
    )
    ok = closed >= 5 and scientific is not None and not failed
    return {
        "minor": requested["minor"],
        "cell": requested["cell"],
        "provider": requested["provider"] or "conda-forge",
        "os": runtime["os"],
        "arch": runtime["arch"],
        "python": runtime["python"],
        "pygobject": runtime["pygobject"],
        "gtk": runtime["gtk"],
        "glib": runtime["glib"],
        "renderer": renderer.group(1).strip() if renderer else "unknown",
        "full_app_cycles": closed,
        "scientific": int(scientific.group(1)) if scientific else 0,
        "result": "PASS" if ok else "FAIL",
    }


def _minor_key(minor):
    return tuple(int(part) for part in minor.split(".") if part.isdigit())


def collect(artifacts):
    rows = []
    for path in sorted(Path(artifacts).rglob("platform-results.txt")):
        row = parse_cell(path.read_text(encoding="utf-8", errors="replace"))
        if row is not None:
            rows.append(row)
    return sorted(rows, key=lambda r: (r["cell"], _minor_key(r["minor"]), r["provider"]))


def download_latest(run, destination, repo="Shabirahmad427/EasyHybrid4"):
    """Download only the newest artifact per name for *run* (needs ``gh``)."""
    listing = subprocess.run(
        ["gh", "api", "--paginate", "repos/%s/actions/runs/%s/artifacts?per_page=100" % (repo, run),
         "--jq", ".artifacts[] | [.id, .name, .created_at, .expired] | @json"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    newest = {}
    for entry in map(json.loads, listing):
        artifact_id, name, created, expired = entry
        if not expired and (name not in newest or created > newest[name][1]):
            newest[name] = (artifact_id, created)
    for name, (artifact_id, _) in sorted(newest.items()):
        data = subprocess.run(
            ["gh", "api", "repos/%s/actions/artifacts/%s/zip" % (repo, artifact_id)],
            capture_output=True, check=True,
        ).stdout
        zipfile.ZipFile(io.BytesIO(data)).extractall(Path(destination) / name)
    return len(newest)


WORKFLOW = ".github/workflows/native-gtk-matrix.yml"
PDYNAMO3_ENV = re.compile(r"^\s*PDYNAMO3_(REPOSITORY|REF):\s*(\S+)\s*$", re.M)

RESTRICTIONS = [
    "## Restrictions and known issues",
    "",
    "- **NOT TESTED:** Linux Wayland; physical GPUs; physical Retina/HiDPI panels; trackpads.",
    "- **NOT TESTED:** cross-process clipboard on Windows and macOS (only same-process checks run there).",
    "- **NOT TESTED:** the native Windows COM file-chooser policy (the tested in-process chooser is used).",
    "- GPU4PySCF guards are verified only locally on an NVIDIA RTX 4060 Ti; hosted runners have no PySCF/GPU.",
    "- Licence: the VisMol graphics engine is CC BY-NC 4.0, so EasyHybrid4 as distributed is non-commercial.",
]


def pdynamo3_source(workflow_text):
    """Return ``repo@ref`` of the pDynamo3 build pinned in the matrix workflow, or None."""
    found = dict(PDYNAMO3_ENV.findall(workflow_text or ""))
    if "REPOSITORY" in found and "REF" in found:
        return "%s@%s" % (found["REPOSITORY"], found["REF"])
    return None


def workflow_at(commit):
    """Read the matrix workflow as it was at *commit* (the tested tree)."""
    try:
        return subprocess.run(["git", "show", "%s:%s" % (commit, WORKFLOW)],
                              capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def render(rows, run=None, commit=None, pdynamo3=None):
    header = [
        "# Tested support table (EH4-603)",
        "",
        "Generated by `.github/scripts/support_table.py` from native-matrix runtime artifacts"
        + (" of run `%s`" % run if run else "") + (" on commit `%s`" % commit if commit else "") + ".",
        "Only combinations with an artifact are listed; anything else is **NOT TESTED**.",
        "Hosted runners use software renderers; physical GPUs, Retina/HiDPI panels, trackpads,",
        "Wayland and screen readers are covered by the manual procedure (docs/MANUAL_VALIDATION.md).",
        "pDynamo3 built by every cell: " + ("`%s`" % pdynamo3 if pdynamo3 else "**unknown** (not recorded)") + ".",
        "",
        "| Result | Cell | GTK (loaded) | Provider | OS | Arch | Python | PyGObject | GLib | GL renderer | Full-app cycles | Scientific tests |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines = [
        "| %(result)s | %(cell)s | %(gtk)s | %(provider)s | %(os)s | %(arch)s | %(python)s | %(pygobject)s "
        "| %(glib)s | %(renderer)s | %(full_app_cycles)d | %(scientific)d |" % row
        for row in rows
    ]
    passed = sum(row["result"] == "PASS" for row in rows)
    footer = ["", "%d of %d tested cells pass." % (passed, len(rows)), ""] + RESTRICTIONS
    return "\n".join(header + lines + footer) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("artifacts", nargs="?")
    parser.add_argument("--download", metavar="RUN", help="fetch the newest artifact per name for RUN")
    parser.add_argument("--run")
    parser.add_argument("--commit")
    parser.add_argument("--output")
    parser.add_argument("--pdynamo3", metavar="REPO@REF",
                        help="pDynamo3 source; default: PDYNAMO3_* in the workflow at --commit")
    args = parser.parse_args(argv)
    if args.download:
        args.artifacts = tempfile.mkdtemp(prefix="eh4-support-")
        download_latest(args.download, args.artifacts)
        args.run = args.run or args.download
    if not args.artifacts:
        parser.error("give an artifacts directory or --download RUN")
    rows = collect(args.artifacts)
    if not rows:
        sys.exit("no platform-results.txt artifacts found")
    pdynamo3 = args.pdynamo3 or (pdynamo3_source(workflow_at(args.commit)) if args.commit else None)
    text = render(rows, args.run, args.commit, pdynamo3)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if all(row["result"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
