"""Value-keyed Gtk.DropDown helpers: the shared GTK4 replacement for ComboBoxText.

GTK 4.10 deprecated Gtk.ComboBox/ComboBoxText, whose items carry a string id
that callers read with ``get_active_id()``. These helpers give a Gtk.DropDown
the same contract: each entry is a ``ChoiceRow(value, label)``, the label is
displayed, and the value (for example a pDynamo option name) is what callers
read and restore. Labels are bound with ``bind_dropdown_label_property``
because Gtk expressions cannot be created from Python on GTK 4.8.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk  # noqa: E402

from gui.model_rows import ChoiceRow  # noqa: E402
from src.gtk4_compat import GTK_INVALID_LIST_POSITION, bind_dropdown_label_property  # noqa: E402


def populate_choice_dropdown(dropdown, choices, current_value=None, fallback=None):
    """Fill ``dropdown`` with ``(value, label)`` pairs and select a value.

    Selects ``current_value`` if present, else ``fallback`` if present, else
    nothing (like a ComboBoxText with no active item).
    """
    model = Gio.ListStore.new(ChoiceRow)
    for value, label in choices:
        model.append(ChoiceRow(value, label))
    dropdown.set_model(model)
    bind_dropdown_label_property(dropdown, "label")
    position = _position_of(model, current_value)
    if position == GTK_INVALID_LIST_POSITION:
        position = _position_of(model, fallback)
    dropdown.set_selected(position)
    return dropdown


def new_choice_dropdown(choices, current_value=None, fallback=None):
    """Create a Gtk.DropDown populated by :func:`populate_choice_dropdown`."""
    return populate_choice_dropdown(Gtk.DropDown(), choices, current_value, fallback)


def selected_choice_value(dropdown):
    """Return the selected entry's value, or ``None`` when nothing is selected."""
    row = dropdown.get_selected_item()
    return row.value if row is not None else None


def select_choice_value(dropdown, value):
    """Select the entry whose value is ``value``.

    Returns whether it was found. An unknown value leaves the current
    selection unchanged, matching ``Gtk.ComboBox.set_active_id``, so loading
    saved parameters with an unrecognised option keeps the default.
    """
    position = _position_of(dropdown.get_model(), value)
    if position == GTK_INVALID_LIST_POSITION:
        return False
    dropdown.set_selected(position)
    return True


def _position_of(model, value):
    if model is None or value is None:
        return GTK_INVALID_LIST_POSITION
    for position in range(model.get_n_items()):
        if model.get_item(position).value == value:
            return position
    return GTK_INVALID_LIST_POSITION
