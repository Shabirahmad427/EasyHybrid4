"""Print the crashing thread of the newest macOS crash report.

A Python faulthandler trace stops at the GLib main loop; the native frames
(GTK, GLib, Cocoa) are only in the system crash report (.ips JSON) that
macOS writes to ~/Library/Logs/DiagnosticReports.
"""

import json
from pathlib import Path

MAX_FRAMES = 40


def main():
    folders = [Path.home() / "Library" / "Logs" / "DiagnosticReports",
               Path("/Library/Logs/DiagnosticReports")]
    reports = sorted((path for folder in folders if folder.is_dir()
                      for path in folder.glob("*.ips") if "ython" in path.name),
                     key=lambda path: path.stat().st_mtime, reverse=True)
    if not reports:
        print("No Python crash report found in", ", ".join(map(str, folders)))
        return
    report = reports[0]
    print("Crash report:", report)
    header, _newline, body = report.read_text(errors="replace").partition("\n")
    try:
        data = json.loads(body)
    except ValueError:
        print(body[:8000])
        return
    exception = data.get("exception", {})
    print("Exception:", exception.get("type"), exception.get("signal"), exception.get("subtype", ""))
    images = data.get("usedImages", [])
    threads = data.get("threads", [])
    faulting = data.get("faultingThread", 0)
    if faulting >= len(threads):
        print("No faulting thread in report")
        return
    for number, frame in enumerate(threads[faulting].get("frames", [])[:MAX_FRAMES]):
        image = images[frame["imageIndex"]] if frame.get("imageIndex", -1) < len(images) else {}
        name = Path(image.get("path", image.get("name", "?"))).name
        symbol = frame.get("symbol", "0x%x" % frame.get("imageOffset", 0))
        print("#%-2d %-28s %s" % (number, name, symbol))


if __name__ == "__main__":
    main()
