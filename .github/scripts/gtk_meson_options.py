"""Print Meson arguments for a minimal GTK4 source build in CI.

GTK renames and adds build options between minor releases (for example
``demos`` became ``build-demos``, ``gtk_doc`` became ``documentation``).
This reads the release's own ``meson.options``/``meson_options.txt`` and
emits only options it defines, typed as boolean or feature, so one CI step
can build GTK 4.8 through 4.18 without per-version argument lists.

Usage: python gtk_meson_options.py SOURCE_DIR [macos|win32]
"""

import re
import sys
from pathlib import Path

BACKENDS = ("macos", "win32")

# Desired value per option name; absent options are skipped. The selected
# native backend is enabled by ``meson_arguments``.
DESIRED = {
    "macos-backend": False,
    "introspection": True,
    "x11-backend": False,
    "wayland-backend": False,
    "broadway-backend": False,
    "win32-backend": False,
    "android-backend": False,
    "media-ffmpeg": False,
    "media-gstreamer": False,
    "print-cups": False,
    "print-cpdb": False,
    "vulkan": False,
    "cloudproviders": False,
    "sysprof": False,
    "tracker": False,
    "colord": False,
    "accesskit": False,
    "gtk_doc": False,
    "documentation": False,
    "update_screenshots": False,
    "screenshots": False,
    "man-pages": False,
    "demos": False,
    "build-demos": False,
    "build-examples": False,
    "build-tests": False,
    "build-testsuite": False,
    "install-tests": False,
}

_OPTION = re.compile(r"option\(\s*'([^']+)'\s*,\s*type\s*:\s*'([a-z]+)'", re.S)


def parse_option_types(text):
    """Map each Meson option name to its declared type."""
    return {name: kind for name, kind in _OPTION.findall(text)}


def meson_arguments(option_types, backend="macos"):
    """Return ``-Dname=value`` arguments for the options this release has."""
    if backend not in BACKENDS:
        raise ValueError("unsupported GTK backend: %s" % backend)
    desired = dict(DESIRED)
    desired["%s-backend" % backend] = True
    arguments = []
    for name, enabled in desired.items():
        kind = option_types.get(name)
        if kind == "boolean":
            value = "true" if enabled else "false"
        elif kind == "feature":
            value = "enabled" if enabled else "disabled"
        else:
            continue
        arguments.append("-D%s=%s" % (name, value))
    return arguments


def main(argv):
    source = Path(argv[1])
    backend = argv[2] if len(argv) > 2 else "macos"
    for filename in ("meson.options", "meson_options.txt"):
        path = source / filename
        if path.is_file():
            print(" ".join(meson_arguments(parse_option_types(path.read_text()), backend)))
            return 0
    print("no Meson options file in %s" % source, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
