#!/usr/bin/env python3
"""Fresh-clone, install, launch and natively close the production app per matrix cell."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import shlex
import shutil
import site
import subprocess
import sys
import tempfile
import time


def _run_under_xvfb_if_needed() -> int | None:
    if not sys.platform.startswith("linux") or os.environ.get("DISPLAY"):
        return None
    if os.environ.get("EASYHYBRID_SOURCE_SMOKE_XVFB") == "1":
        raise RuntimeError("Xvfb wrapper did not provide DISPLAY")
    xvfb_run = shutil.which("xvfb-run")
    if xvfb_run is None:
        raise RuntimeError("Linux source-checkout smoke requires xvfb-run")
    environment = os.environ.copy()
    environment["EASYHYBRID_SOURCE_SMOKE_XVFB"] = "1"
    environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
    environment["GALLIUM_DRIVER"] = "llvmpipe"
    return subprocess.run(
        [xvfb_run, "-a", "-s", "-screen 0 1280x800x24 +extension GLX",
         sys.executable, str(Path(__file__).resolve())],
        env=environment,
        check=False,
    ).returncode


def _run(command: list[str], *, cwd: Path | None = None, env=None) -> None:
    print("SOURCE_CHECKOUT_COMMAND=" + shlex.join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _runtime_line() -> str:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib, Gtk

    gtk = ".".join(map(str, (
        Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
    )))
    glib = ".".join(map(str, (
        GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION
    )))
    return (
        "SOURCE_CHECKOUT_RUNTIME="
        f"OS:{platform.system()} ARCH:{platform.machine()} "
        f"PYTHON:{platform.python_version()} PYGOBJECT:{gi.__version__} "
        f"GTK:{gtk} GLIB:{glib}"
    )


def _source_environment(source: Path, matrix_checkout: Path, temporary_home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    pdynamo_home = Path(environment.get("PDYNAMO3_HOME", matrix_checkout / "pDynamo3")).resolve()
    if not pdynamo_home.is_dir():
        raise RuntimeError(f"matrix pDynamo3 checkout does not exist: {pdynamo_home}")

    environment["PDYNAMO3_HOME"] = str(pdynamo_home)
    environment["PDYNAMO3_PARAMETERS"] = str(pdynamo_home / "parameters")
    environment["PDYNAMO3_SCRATCH"] = environment.get("RUNNER_TEMP", str(temporary_home))
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if sys.platform == "win32":
        environment.setdefault("GALLIUM_DRIVER", "llvmpipe")
    # Keep `pip install --user` packages (distro cells) visible after HOME moves.
    environment.setdefault("PYTHONUSERBASE", site.getuserbase())
    environment["HOME"] = str(temporary_home)
    environment["USERPROFILE"] = str(temporary_home)
    environment["APPDATA"] = str(temporary_home / "AppData" / "Roaming")
    environment["LOCALAPPDATA"] = str(temporary_home / "AppData" / "Local")
    environment["XDG_CONFIG_HOME"] = str(temporary_home / ".config")
    environment["XDG_CACHE_HOME"] = str(temporary_home / ".cache")
    (temporary_home / ".VisMol").mkdir(parents=True, exist_ok=True)

    retained = []
    matrix_root = matrix_checkout.resolve()
    for entry in environment.get("PYTHONPATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            Path(entry).resolve().relative_to(matrix_root)
        except (OSError, ValueError):
            retained.append(entry)
    source_paths = [source, source / "src" / "graphics_engine" / "src", pdynamo_home]
    environment["PYTHONPATH"] = os.pathsep.join(map(str, [*source_paths, *retained]))
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def _fresh_clone(matrix_checkout: Path, destination: Path) -> Path:
    commit = os.environ.get("GITHUB_SHA")
    if not commit:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=matrix_checkout, text=True
        ).strip()
    if shutil.which("git") is None:
        raise RuntimeError("the fresh source-checkout check needs git on PATH")
    clone = destination / "EasyHybrid4"
    _run([
        "git", "clone", "--recurse-submodules", "--no-hardlinks",
        "--no-checkout", str(matrix_checkout), str(clone),
    ])
    _run(["git", "checkout", "--detach", commit], cwd=clone)
    _run(["git", "submodule", "update", "--init", "--recursive"], cwd=clone)
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=clone, text=True
    ).strip()
    if actual != commit:
        raise RuntimeError(f"fresh checkout {actual} differs from tested commit {commit}")
    print(f"SOURCE_CHECKOUT_COMMIT={actual}", flush=True)
    return clone


def _launch_and_close(source: Path, environment: dict[str, str]) -> None:
    # Import from the fresh source checkout; native keyboard details stay in
    # the shared XTest/Win32/Quartz adapter used by the existing app smoke.
    sys.path.insert(0, str(source / "tests"))
    from native_pointer_input import (
        inject_native_quit_shortcut,
        native_window_visible_for_process,
    )

    process = subprocess.Popen(
        [sys.executable, "-u", str(source / "easyhybrid.py")],
        cwd=source,
        env=environment,
    )
    try:
        deadline = time.monotonic() + 120
        while process.poll() is None and time.monotonic() < deadline:
            if native_window_visible_for_process(process.pid):
                print("SOURCE_CHECKOUT_WINDOW=EasyHybrid", flush=True)
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(
                "source entrypoint did not show a main window; "
                f"exit={process.poll()}"
            )

        # The main window maps while startup is still finishing (splash close,
        # first GL render); a key pressed then is dropped (run 40230196293).
        # Let it settle, and resend the shortcut while the process stays up.
        time.sleep(3)
        status = None
        for attempt in range(1, 7):
            if process.poll() is not None:
                break
            method = inject_native_quit_shortcut(process.pid)
            print(f"SOURCE_CHECKOUT_NATIVE_QUIT={method} ATTEMPT={attempt}", flush=True)
            try:
                status = process.wait(timeout=10)
                break
            except subprocess.TimeoutExpired:
                continue
        status = process.poll() if status is None else status
        if status is None:
            raise RuntimeError("source app did not exit after native quit shortcut")
        if status != 0:
            raise RuntimeError(f"source app exited with status {status}")
        print("SOURCE_CHECKOUT_NATIVE_CLOSE=PASS EXIT=0", flush=True)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def main() -> int:
    xvfb_status = _run_under_xvfb_if_needed()
    if xvfb_status is not None:
        return xvfb_status

    matrix_checkout = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd())).resolve()
    print(_runtime_line(), flush=True)
    with tempfile.TemporaryDirectory(prefix="easyhybrid-source-acceptance-") as temp:
        temporary_root = Path(temp)
        source = _fresh_clone(matrix_checkout, temporary_root)
        environment = _source_environment(
            source, matrix_checkout, temporary_root / "user-home"
        )
        _run([sys.executable, "install.py", "--ci"], cwd=source, env=environment)
        print("SOURCE_CHECKOUT_INSTALL=PASS", flush=True)
        # EH4-600: linked native libraries and bundled sample data, read
        # by the fresh install's own interpreter and paths.
        _run([sys.executable, str(Path(__file__).resolve().with_name("fresh_install_report.py")),
              str(source)], cwd=source, env=environment)
        _launch_and_close(source, environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
