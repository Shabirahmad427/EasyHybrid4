"""Portable file, folder and colour choosers for every supported GTK4 minor.

Gtk.FileChooserDialog and Gtk.ColorChooserDialog are deprecated since GTK
4.10, while their replacements Gtk.FileDialog and Gtk.ColorDialog only exist
from GTK 4.10. These helpers detect the replacement by feature, not by
version number, and fall back to the older dialogs (not deprecated there)
on GTK 4.8. Either way the caller gets the same result through the same
callback, on Linux, Windows and macOS.

File results are local paths (``str``); multi-selection modes return a list
of paths, empty when cancelled. GTK4 always asks before overwriting in save
mode, so callers do not need to request it.
"""

import os
import sys
from logging import getLogger

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

logger = getLogger(__name__)

OPEN = "open"
OPEN_MULTIPLE = "open-multiple"
SAVE = "save"
SELECT_FOLDER = "select-folder"
SELECT_MULTIPLE_FOLDERS = "select-multiple-folders"

MULTIPLE_MODES = (OPEN_MULTIPLE, SELECT_MULTIPLE_FOLDERS)

# Gtk.FileDialog method used for each mode.
_FILE_DIALOG_METHODS = {
    OPEN: "open",
    OPEN_MULTIPLE: "open_multiple",
    SAVE: "save",
    SELECT_FOLDER: "select_folder",
    SELECT_MULTIPLE_FOLDERS: "select_multiple_folders",
}

_DEFAULT_TITLES = {
    OPEN: "Open File",
    OPEN_MULTIPLE: "Open Files",
    SAVE: "Save File",
    SELECT_FOLDER: "Select Folder",
    SELECT_MULTIPLE_FOLDERS: "Select Folders",
}

_DEFAULT_ACCEPT_LABELS = {
    OPEN: "Open",
    OPEN_MULTIPLE: "Open",
    SAVE: "Save",
    SELECT_FOLDER: "Select",
    SELECT_MULTIPLE_FOLDERS: "Select",
}


def has_file_dialog(gtk=Gtk):
    return hasattr(gtk, "FileDialog")


def has_color_dialog(gtk=Gtk):
    return hasattr(gtk, "ColorDialog")


def _parent_window(parent):
    if isinstance(parent, Gtk.Window):
        return parent
    root = parent.get_root() if isinstance(parent, Gtk.Widget) else None
    return root if isinstance(root, Gtk.Window) else None


def split_initial_path(initial_path, mode):
    """Return ``(folder, name)`` to preselect for ``initial_path``.

    ``folder`` is an existing directory or None. ``name`` is the suggested
    file name, only for save mode.
    """
    if not initial_path:
        return None, None
    candidate = os.path.abspath(os.path.expanduser(str(initial_path)))
    if os.path.isdir(candidate):
        return candidate, None
    folder = os.path.dirname(candidate)
    name = os.path.basename(candidate) if mode == SAVE else None
    return (folder if os.path.isdir(folder) else None), (name or None)


def _paths(files):
    paths = []
    for index in range(files.get_n_items() if files is not None else 0):
        path = files.get_item(index).get_path()
        if path:
            paths.append(path)
    return paths


def _is_cancel(error, gtk=Gtk):
    if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
        return True
    dialog_error = getattr(gtk, "DialogError", None)
    if dialog_error is None:
        return False
    return any(error.matches(dialog_error.quark(), int(code))
               for code in (dialog_error.CANCELLED, dialog_error.DISMISSED))


FILE_CHOOSER_SCHEMA = "org.gtk.gtk4.Settings.FileChooser"
COLOR_CHOOSER_SCHEMA = "org.gtk.gtk4.Settings.ColorChooser"


def gsettings_schema_installed(schema_id):
    """True if GLib can find ``schema_id`` (a compiled GSettings schema).

    GTK's own file and colour chooser widgets abort the whole process
    ("No GSettings schemas are installed") when their schema is missing,
    for example in an environment whose post-install step did not run
    glib-compile-schemas. Looking the schema up first is safe.
    """
    source = Gio.SettingsSchemaSource.get_default()
    return source is not None and source.lookup(schema_id, True) is not None


def _uses_gtk_chooser_widget(use_new_api, platform=None):
    # The old dialogs are GTK widgets everywhere. Gtk.FileDialog shows the
    # native Windows/macOS dialog; elsewhere it uses a desktop portal or,
    # without one, the same GTK widget.
    platform = sys.platform if platform is None else platform
    return not use_new_api or not platform.startswith(("win32", "darwin"))


def _report_missing_schema(window, schema_id):
    from gui.message_dialogs import show_message

    logger.error("GSettings schema %s is not installed", schema_id)
    show_message(
        window, "This chooser cannot open",
        "GTK's settings schema %s is not installed, so GTK would stop the "
        "program. Compile the schemas of this GTK installation "
        "(glib-compile-schemas <prefix>/share/glib-2.0/schemas) and restart." % schema_id,
        kind="error",
    )


class ChooserHandle:
    """A presented chooser. ``cancel()`` closes it and reports no selection."""

    def __init__(self, dialog, uses_new_api, cancellable=None):
        self.dialog = dialog
        self._completed_dialog = None
        self.uses_new_api = uses_new_api
        self.cancellable = cancellable
        self.done = False

    def cancel(self):
        if self.done or self.dialog is None:
            return
        if self.cancellable is not None:
            self.cancellable.cancel()
        else:
            self.dialog.response(Gtk.ResponseType.CANCEL)


def choose_file(parent, callback, *, mode=OPEN, title=None, initial_path=None,
                filters=None, accept_label=None, gtk=Gtk, use_file_dialog=None):
    """Ask for a file or folder and call ``callback`` with the result.

    ``mode`` is one of OPEN, OPEN_MULTIPLE, SAVE, SELECT_FOLDER or
    SELECT_MULTIPLE_FOLDERS. ``filters`` is a sequence of Gtk.FileFilter; the
    first one is selected initially. ``callback`` receives a path or None,
    or a list of paths for the multiple modes. Returns a ChooserHandle.
    """
    if mode not in _FILE_DIALOG_METHODS:
        raise ValueError("unknown file chooser mode: %r" % (mode,))
    if use_file_dialog is None:
        use_file_dialog = has_file_dialog(gtk)
    title = title or _DEFAULT_TITLES[mode]
    accept_label = accept_label or _DEFAULT_ACCEPT_LABELS[mode]
    folder, name = split_initial_path(initial_path, mode)
    filters = list(filters or [])
    window = _parent_window(parent) if parent is not None else None
    if _uses_gtk_chooser_widget(use_file_dialog) and not gsettings_schema_installed(FILE_CHOOSER_SCHEMA):
        _report_missing_schema(window, FILE_CHOOSER_SCHEMA)
        handle = ChooserHandle(None, use_file_dialog)
        _report(handle, callback, mode, [])
        return handle
    if use_file_dialog:
        return _choose_with_file_dialog(
            gtk, window, callback, mode, title, accept_label, folder, name, filters)
    return _choose_with_file_chooser(
        gtk, window, callback, mode, title, accept_label, folder, name, filters)


def _report(handle, callback, mode, paths):
    if handle.done:
        return
    handle.done = True
    # Keep Gtk.FileDialog alive briefly after its async completion on Windows.
    # Its native COM dialog can still be unwinding the completion/cancel
    # callback when GTK returns to GLib; releasing the wrapper in that window
    # can disconnect the COM apartment (RPC_E_DISCONNECTED / 0x80010108).
    # Retain a separate reference while preserving the public closed-handle
    # state, then release it from the GTK main context.
    completed_dialog = handle.dialog
    handle.dialog = None
    if sys.platform == "win32" and handle.cancellable is not None:
        handle._completed_dialog = completed_dialog
        GLib.timeout_add_seconds(5, _release_completed_dialog, handle)
    if mode in MULTIPLE_MODES:
        callback(paths)
    else:
        callback(paths[0] if paths else None)


def _release_completed_dialog(handle):
    handle._completed_dialog = None
    return GLib.SOURCE_REMOVE


def _choose_with_file_dialog(gtk, window, callback, mode, title, accept_label,
                             folder, name, filters):
    dialog = gtk.FileDialog(title=title, modal=True)
    dialog.set_accept_label(accept_label)
    if folder:
        dialog.set_initial_folder(Gio.File.new_for_path(folder))
    if name:
        dialog.set_initial_name(name)
    if filters:
        store = Gio.ListStore.new(gtk.FileFilter)
        for file_filter in filters:
            store.append(file_filter)
        dialog.set_filters(store)
        dialog.set_default_filter(filters[0])

    method = _FILE_DIALOG_METHODS[mode]
    cancellable = Gio.Cancellable()
    handle = ChooserHandle(dialog, True, cancellable)

    def on_finish(source, result):
        try:
            selection = getattr(source, method + "_finish")(result)
        except GLib.Error as error:
            if not _is_cancel(error, gtk):
                logger.warning("%s dialog failed: %s", title, error.message)
            _report(handle, callback, mode, [])
            return
        if mode in MULTIPLE_MODES:
            paths = _paths(selection)
        else:
            path = selection.get_path() if selection is not None else None
            paths = [path] if path else []
        _report(handle, callback, mode, paths)

    getattr(dialog, method)(window, cancellable, on_finish)
    return handle


_CHOOSER_ACTIONS = {
    OPEN: "OPEN",
    OPEN_MULTIPLE: "OPEN",
    SAVE: "SAVE",
    SELECT_FOLDER: "SELECT_FOLDER",
    SELECT_MULTIPLE_FOLDERS: "SELECT_FOLDER",
}


_CHOOSER_DESTROY_DELAY_SECONDS = 5


def _destroy_once(widget):
    widget.destroy()
    return GLib.SOURCE_REMOVE


def _choose_with_file_chooser(gtk, window, callback, mode, title, accept_label,
                              folder, name, filters):
    # GTK 4.8 path: Gtk.FileDialog does not exist there and
    # Gtk.FileChooserDialog is not yet deprecated.
    action = getattr(gtk.FileChooserAction, _CHOOSER_ACTIONS[mode])
    dialog = gtk.FileChooserDialog(title=title, action=action, modal=True)
    if window is not None:
        dialog.set_transient_for(window)
    dialog.add_buttons("Cancel", gtk.ResponseType.CANCEL, accept_label, gtk.ResponseType.ACCEPT)
    dialog.set_default_response(gtk.ResponseType.ACCEPT)
    dialog.set_select_multiple(mode in MULTIPLE_MODES)
    for file_filter in filters:
        dialog.add_filter(file_filter)
    if filters:
        dialog.set_filter(filters[0])
    if folder:
        try:
            dialog.set_current_folder(Gio.File.new_for_path(folder))
        except GLib.Error as error:
            logger.debug("Could not preselect %s: %s", folder, error.message)
    if name:
        dialog.set_current_name(name)

    handle = ChooserHandle(dialog, False)

    def on_response(chooser, response):
        paths = []
        if response in (gtk.ResponseType.ACCEPT, gtk.ResponseType.OK):
            paths = _paths(chooser.get_files())
        # Hide now, destroy later: on GTK 4.10+ (seen on Linux and macOS)
        # destroying the chooser while its path bar is still looking up a
        # folder crashes in gtk_path_bar_set_file_finish. Lookups of local
        # folders finish long before the delay.
        chooser.set_visible(False)
        GLib.timeout_add_seconds(_CHOOSER_DESTROY_DELAY_SECONDS, _destroy_once, chooser)
        _report(handle, callback, mode, paths)

    dialog.connect("response", on_response)
    dialog.present()
    return handle


def file_filter(name, *patterns, gtk=Gtk):
    """Return a Gtk.FileFilter named ``name`` matching glob ``patterns``."""
    result = gtk.FileFilter()
    result.set_name(name)
    for pattern in patterns:
        result.add_pattern(pattern)
    return result


def choose_color(parent, callback, *, title="Choose color", initial=None,
                 with_alpha=True, gtk=Gtk, use_color_dialog=None):
    """Ask for a colour and call ``callback`` with a Gdk.RGBA or None.

    ``with_alpha`` offers an opacity control (on by default, as in GTK).
    """
    if use_color_dialog is None:
        use_color_dialog = has_color_dialog(gtk)
    window = _parent_window(parent) if parent is not None else None
    # Gtk.ColorDialog shows the GTK colour chooser widget on every platform.
    if not gsettings_schema_installed(COLOR_CHOOSER_SCHEMA):
        _report_missing_schema(window, COLOR_CHOOSER_SCHEMA)
        handle = ChooserHandle(None, use_color_dialog)
        handle.done = True
        callback(None)
        return handle

    if use_color_dialog:
        dialog = gtk.ColorDialog(title=title, modal=True, with_alpha=with_alpha)
        cancellable = Gio.Cancellable()
        handle = ChooserHandle(dialog, True, cancellable)

        def on_finish(source, result):
            try:
                rgba = source.choose_rgba_finish(result)
            except GLib.Error as error:
                if not _is_cancel(error, gtk):
                    logger.warning("%s dialog failed: %s", title, error.message)
                rgba = None
            if not handle.done:
                handle.done = True
                handle.dialog = None
                callback(rgba)

        dialog.choose_rgba(window, initial, cancellable, on_finish)
        return handle

    # GTK 4.8 path: Gtk.ColorDialog does not exist there.
    dialog = gtk.ColorChooserDialog(title=title, modal=True, use_alpha=with_alpha)
    if window is not None:
        dialog.set_transient_for(window)
    if initial is not None:
        dialog.set_rgba(initial)
    handle = ChooserHandle(dialog, False)

    def on_response(chooser, response):
        rgba = chooser.get_rgba() if response in (gtk.ResponseType.OK, gtk.ResponseType.ACCEPT) else None
        # Defer destruction until GTK has returned from the native response
        # callback. Destroying Gtk.ColorChooserDialog in that callback can
        # access-violate on Windows GTK 4.8.
        chooser.set_visible(False)
        GLib.timeout_add_seconds(_CHOOSER_DESTROY_DELAY_SECONDS, _destroy_once, chooser)
        if not handle.done:
            handle.done = True
            handle.dialog = None
            callback(rgba)

    dialog.connect("response", on_response)
    dialog.present()
    return handle
