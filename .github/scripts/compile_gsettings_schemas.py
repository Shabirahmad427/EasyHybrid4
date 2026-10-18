"""Compile the GSettings schemas of the active conda environment.

A normal conda install compiles them in GLib's post-link script, but some
cells skip link scripts (Windows GTK 4.8/4.10) and Linux/macOS conda GTK
does not ship a compiled cache. Without it GTK's file and colour choosers
abort the process ("No GSettings schemas are installed"). The schema
sources live in <prefix>/share/glib-2.0/schemas, or under Library\\ on
Windows.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    prefix = Path(sys.prefix)
    candidates = [prefix / "share" / "glib-2.0" / "schemas",
                  prefix / "Library" / "share" / "glib-2.0" / "schemas"]
    schemas = next((path for path in candidates if any(path.glob("org.gtk.gtk4.*.gschema.xml"))), None)
    if schemas is None:
        sys.exit("No GTK4 schema sources in: %s" % ", ".join(map(str, candidates)))
    compiler = shutil.which("glib-compile-schemas")
    if compiler is None:
        sys.exit("glib-compile-schemas is not installed (conda package glib-tools)")
    subprocess.run([compiler, str(schemas)], check=True)
    compiled = schemas / "gschemas.compiled"
    if not compiled.is_file():
        sys.exit("glib-compile-schemas did not write %s" % compiled)
    print("Compiled GSettings schemas: %s (%d bytes)" % (compiled, compiled.stat().st_size))


if __name__ == "__main__":
    main()
