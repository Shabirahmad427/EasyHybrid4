"""Native GTK4 chooser for a new Builder canvas or an existing system."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from src.gtk4_compat import GTK_INVALID_LIST_POSITION


def _close_active_builder(main, discard_target=False):
    sidebar = getattr(main, "builder_sidebar_window", None)
    if sidebar is not None and sidebar.visible:
        sidebar.close_window()
    if discard_target:
        main.vm_session.builder_target_object = None


def choose_and_open_builder(main):
    """Present a non-blocking GTK4 choice dialog and start the selected mode."""
    vm = main.vm_session
    p_session = main.p_session
    existing = [eid for eid, system in p_session.psystem.items() if system is not None]
    if not existing:
        _close_active_builder(main, discard_target=True)
        main.builder_sidebar_window.open_window()
        return

    from gui.widgets.custom_widgets.comboboxes import SystemComboBox

    dialog = Gtk.Dialog(title="Open Builder", transient_for=main.window, modal=True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Continue", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    content = dialog.get_content_area()
    content.set_spacing(8)
    for side in ("top", "bottom", "start", "end"):
        getattr(content, f"set_margin_{side}")(12)

    new_mode = Gtk.CheckButton(label="New blank molecule")
    edit_mode = Gtk.CheckButton(label="Edit an existing system")
    edit_mode.set_group(new_mode)
    new_mode.set_active(True)
    content.append(new_mode)
    content.append(edit_mode)

    system_dropdown = SystemComboBox(main=main)
    content.append(system_dropdown)
    object_dropdown = Gtk.DropDown.new(Gtk.StringList.new([]), None)
    content.append(Gtk.Label(label="Molecular object to edit:", xalign=0))
    content.append(object_dropdown)
    system_dropdown.set_sensitive(False)
    object_dropdown.set_sensitive(False)
    object_ids = []

    def update_objects(*_args):
        nonlocal object_ids
        eid = system_dropdown.get_system_id()
        objects = [obj for obj in vm.vm_objects_dic.values()
                   if getattr(obj, "e_id", None) == eid
                   and not getattr(obj, "is_surface", False)]
        object_ids = [obj.index for obj in objects]
        model = Gtk.StringList.new([obj.name for obj in objects])
        object_dropdown.set_model(model)
        object_dropdown.set_selected(0 if objects else GTK_INVALID_LIST_POSITION)

    def toggle_edit(*_args):
        editing = edit_mode.get_active()
        system_dropdown.set_sensitive(editing)
        object_dropdown.set_sensitive(editing)
        if editing:
            update_objects()

    system_dropdown.connect("notify::selected", update_objects)
    new_mode.connect("toggled", toggle_edit)
    edit_mode.connect("toggled", toggle_edit)
    dialog.connect("response", lambda current, response: on_response(
        current, response, main, new_mode, system_dropdown,
        object_dropdown, object_ids))
    dialog.present()


def on_response(dialog, response, main, new_mode, system_dropdown, object_dropdown, object_ids):
    editing = not new_mode.get_active()
    eid = system_dropdown.get_system_id() if editing else None
    selected = object_dropdown.get_selected()
    object_index = object_ids[selected] if editing and selected < len(object_ids) else None
    dialog.destroy()
    if response != Gtk.ResponseType.OK:
        return
    if editing:
        obj = main.vm_session.vm_objects_dic.get(object_index)
        if eid is None or obj is None:
            main.bottom_notebook.status_teeview_add_new_item(
                message="Edit in Builder: select a system and molecular object.", system=None)
            return
        from gui.windows.builder.empty_object import begin_editing_existing_system
        begin_editing_existing_system(main.vm_session, eid, vismol_object=obj)
    else:
        _close_active_builder(main, discard_target=True)
        main.builder_sidebar_window.open_window()
