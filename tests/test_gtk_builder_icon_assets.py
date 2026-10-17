"""Keep file-backed GtkBuilder image assets resolvable from their UI files."""

from pathlib import Path
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_glade_image_files_exist():
    missing = []
    references = []
    for ui_file in sorted((PROJECT_ROOT / "src").rglob("*.glade")):
        root = ET.parse(ui_file).getroot()
        for image in root.iter("object"):
            if image.get("class") != "GtkImage":
                continue
            for prop in image.findall("property"):
                if prop.get("name") != "file" or not prop.text:
                    continue
                relative_path = prop.text.strip()
                references.append((ui_file, relative_path))
                if not (ui_file.parent / relative_path).is_file():
                    missing.append((ui_file, relative_path))

    assert references, "expected file-backed GtkBuilder images to be inventoried"
    assert not missing, "missing GtkBuilder image assets: %r" % (missing,)
