"""GTK4 helpers for GtkBuilder signal declarations and UI loading."""

import os
import tempfile
import xml.etree.ElementTree as ET

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

# Registers EasyHybridColorButton, which Builder files name directly.
from gui import color_button  # noqa: F401,E402


def load_builder_file(builder, filename):
    """Load a UI and defer its signal hookups to GTK4's GObject API.

    GTK4's Builder does not support ``connect_signals()``. It also rejects
    unresolved handler names while parsing a file, so signal declarations
    must be held out of the Builder input and connected explicitly after
    loading.
    """
    try:
        root = ET.parse(filename).getroot()
    except (OSError, ET.ParseError):
        return builder.add_from_file(filename)

    _remember_builder_signals(builder, root)
    # ElementTree elements are falsey when they have no child elements. A
    # <signal/> node is therefore a false value even though it is present;
    # test for an actual node instead of using any() on the elements.
    if next(root.iter("signal"), None) is None:
        # Keep GtkBuilder's file context for layouts without callbacks
        # (needed by filename-valued properties and some special widgets).
        return builder.add_from_file(filename)
    # The temporary XML file lives outside the UI directory. Resolve
    # GtkImage.file values before moving the document so GtkBuilder still
    # loads assets relative to the original UI file (not /tmp).
    _resolve_relative_file_properties(root, os.path.dirname(os.path.abspath(filename)))
    _remove_signal_elements(root)
    xml = ET.tostring(root, encoding="unicode")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ui", delete=False
        ) as temporary_ui:
            temporary_path = temporary_ui.name
            temporary_ui.write(xml)
        return builder.add_from_file(temporary_path)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _resolve_relative_file_properties(root, base_directory):
    """Keep relative GtkImage file paths anchored to their source UI file."""
    for obj in root.iter("object"):
        if obj.get("class") != "GtkImage":
            continue
        for prop in obj.findall("property"):
            if prop.get("name") != "file" or not prop.text:
                continue
            path = prop.text.strip()
            if not path or os.path.isabs(path) or "://" in path:
                continue
            prop.text = os.path.normpath(os.path.join(base_directory, path))


def _remove_signal_elements(root):
    """Remove Builder signal declarations after preserving their metadata."""
    for obj in root.iter("object"):
        for signal in obj.findall("signal"):
            obj.remove(signal)


def _remember_builder_signals(builder, root):
    """Store Glade signal declarations; Gtk4 Builder has no connect_signals()."""
    specs = getattr(builder, "_easyhybrid_signal_specs", None)
    if specs is None:
        specs = []
        builder._easyhybrid_signal_specs = specs
    for obj in root.iter("object"):
        object_id = obj.get("id")
        if not object_id:
            continue
        for signal in obj.findall("signal"):
            specs.append((
                object_id,
                signal.get("name"),
                signal.get("handler"),
                signal.get("after") == "yes",
                signal.get("swapped") == "yes",
                signal.get("object"),
            ))


def load_builder_string(builder, text):
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return builder.add_from_string(text)
    _remember_builder_signals(builder, root)
    _remove_signal_elements(root)
    return builder.add_from_string(ET.tostring(root, encoding="unicode"))


def _builder_connect_signals(builder, handlers):
    """Connect Glade handlers explicitly, as required by GTK4."""
    connected = getattr(builder, "_easyhybrid_connected_signals", None)
    if connected is None:
        connected = set()
        builder._easyhybrid_connected_signals = connected

    for object_id, signal, handler_name, after, swapped, connect_object_id in getattr(
        builder, "_easyhybrid_signal_specs", ()
    ):
        key = (id(handlers), object_id, signal, handler_name, connect_object_id)
        if key in connected:
            continue
        widget = builder.get_object(object_id)
        if widget is None:
            raise ValueError(f"GTK Builder object {object_id!r} was not found")
        if isinstance(handlers, dict):
            callback = handlers.get(handler_name)
        else:
            callback = getattr(handlers, handler_name, None)
        if callback is None or not callable(callback):
            raise AttributeError(f"GTK signal handler {handler_name!r} was not found")

        target = builder.get_object(connect_object_id) if connect_object_id else None
        if swapped:
            target = target if target is not None else handlers
            widget.connect_object(signal, callback, target, after=after)
        elif after:
            widget.connect_after(signal, callback)
        else:
            widget.connect(signal, callback)
        connected.add(key)


def connect_builder_signals(builder, handlers):
    """Connect GtkBuilder XML signals using GTK4's GObject signal API."""
    _builder_connect_signals(builder, handlers)
