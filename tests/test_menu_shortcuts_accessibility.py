"""EH4-301: menu keyboard conventions and accessible names, per native OS."""

import glob
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "src" / "graphics_engine" / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

import importlib.util  # noqa: E402

# Load the module from its file: importing the gui.main package would pull in
# MainWindow and pDynamo3, which this menu-only test does not need.
_spec = importlib.util.spec_from_file_location(
    "eh4_gtk4_menu", ROOT / "src" / "gui" / "main" / "gtk4_menu.py"
)
_menu_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_menu_module)
ACCELERATORS, Gtk4MainMenu = _menu_module.ACCELERATORS, _menu_module.Gtk4MainMenu

MENU = ROOT / "src" / "gui" / "MainMenu.json"


def test_standard_menu_shortcuts_cover_existing_menu_items():
    ids = set()

    def walk(entries):
        for entry in entries:
            if entry.get("id"):
                ids.add(entry["id"])
            walk(entry.get("items") or [])

    walk(json.loads(MENU.read_text(encoding="utf-8")))
    assert set(ACCELERATORS) <= ids
    # Command on macOS (GTK maps <Primary> to Control there), Ctrl elsewhere.
    prefix = "<Meta>" if sys.platform == "darwin" else "<Primary>"
    assert all(accel.startswith(prefix) for accel in ACCELERATORS.values())


def test_primary_accelerator_parses_to_a_platform_modifier():
    if Gdk.Display.get_default() is None:
        pytest.skip("requires a native GTK display")
    parsed = Gtk.accelerator_parse("<Primary>o")
    keyval, modifiers = parsed[-2], parsed[-1]
    assert keyval == Gdk.KEY_o
    # GTK 4.24.1 on macOS arm64 parses <Primary> as Control (run 40149611393),
    # not Meta. Whether the Command key then triggers the shortcut is checked
    # natively by the real-app cycle, which presses Cmd+N through Quartz.
    allowed = {Gdk.ModifierType.CONTROL_MASK}
    if sys.platform == "darwin":
        allowed.add(Gdk.ModifierType.META_MASK)
    assert modifiers in allowed, (sys.platform, modifiers)


class _Owner:
    def __init__(self):
        self.activated = []

    def on_main_menu_activate(self, action):
        self.activated.append(action.get_name())


def test_window_shortcuts_activate_the_menu_actions_and_menu_shows_accels():
    if Gdk.Display.get_default() is None:
        pytest.skip("requires a native GTK display")
    owner = _Owner()
    menu = Gtk4MainMenu(owner, str(MENU))
    window = Gtk.Window(title="EH4-301 shortcuts")
    controller = menu.attach_shortcuts(window)
    try:
        assert controller.get_propagation_phase() == Gtk.PropagationPhase.CAPTURE
        shortcuts = [controller.get_item(i) for i in range(controller.get_n_items())]
        bound = {s.get_action().get_action_name(): s.get_trigger().to_string() for s in shortcuts}
        assert bound == {
            "main.%s" % item_id: Gtk.ShortcutTrigger.parse_string(accel).to_string()
            for item_id, accel in ACCELERATORS.items()
        }
        # Each named action resolves through the window's action muxer.
        for item_id in ACCELERATORS:
            assert window.activate_action("main.%s" % item_id, None)
        assert owner.activated == list(ACCELERATORS)

        # The menu model advertises the accelerator next to each label.
        shown = {}

        def collect(model):
            for index in range(model.get_n_items()):
                accel = model.get_item_attribute_value(index, "accel", GLib.VariantType.new("s"))
                action = model.get_item_attribute_value(index, "action", GLib.VariantType.new("s"))
                if accel is not None and action is not None:
                    shown[action.get_string()] = accel.get_string()
                for link in ("section", "submenu"):
                    child = model.get_item_link(index, link)
                    if child is not None:
                        collect(child)

        collect(menu.model)
        assert shown == {"main.%s" % k: v for k, v in ACCELERATORS.items()}
    finally:
        window.destroy()


def test_icon_only_buttons_have_accessible_names():
    unnamed = []
    for path in glob.glob(str(ROOT / "src" / "gui" / "**" / "*.glade"), recursive=True):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for obj in root.iter("object"):
            if obj.get("class") not in ("GtkButton", "GtkToggleButton", "GtkMenuButton"):
                continue
            props = {p.get("name"): (p.text or "").strip() for p in obj.findall("property")}
            icon = props.get("icon-name") or any(
                child.find("object") is not None and child.find("object").get("class") == "GtkImage"
                for child in obj.findall("child")
            )
            if not icon or props.get("label"):
                continue
            accessible = obj.find("accessibility")
            named = props.get("tooltip-text") or (
                accessible is not None and accessible.find("property[@name='label']") is not None
            )
            if not named:
                unnamed.append("%s:%s" % (Path(path).relative_to(ROOT), obj.get("id")))
    assert unnamed == []
