"""GTK4 periodic-table element picker for the molecule Builder."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk


_MAIN_ROWS = [
    [("H", 1), ("He", 18)],
    [("Li", 1), ("Be", 2), ("B", 13), ("C", 14), ("N", 15), ("O", 16), ("F", 17), ("Ne", 18)],
    [("Na", 1), ("Mg", 2), ("Al", 13), ("Si", 14), ("P", 15), ("S", 16), ("Cl", 17), ("Ar", 18)],
    [("K", 1), ("Ca", 2), ("Sc", 3), ("Ti", 4), ("V", 5), ("Cr", 6), ("Mn", 7), ("Fe", 8),
     ("Co", 9), ("Ni", 10), ("Cu", 11), ("Zn", 12), ("Ga", 13), ("Ge", 14), ("As", 15),
     ("Se", 16), ("Br", 17), ("Kr", 18)],
    [("Rb", 1), ("Sr", 2), ("Y", 3), ("Zr", 4), ("Nb", 5), ("Mo", 6), ("Tc", 7), ("Ru", 8),
     ("Rh", 9), ("Pd", 10), ("Ag", 11), ("Cd", 12), ("In", 13), ("Sn", 14), ("Sb", 15),
     ("Te", 16), ("I", 17), ("Xe", 18)],
    [("Cs", 1), ("Ba", 2), ("La", 3), ("Hf", 4), ("Ta", 5), ("W", 6), ("Re", 7), ("Os", 8),
     ("Ir", 9), ("Pt", 10), ("Au", 11), ("Hg", 12), ("Tl", 13), ("Pb", 14), ("Bi", 15),
     ("Po", 16), ("At", 17), ("Rn", 18)],
    [("Fr", 1), ("Ra", 2), ("Ac", 3)],
]
_LANTHANIDES = ["Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"]
_ACTINIDES = ["Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr"]
_QUICK_PICKS = {"C", "N", "O", "H"}


def _elements_css(vm_session):
    rules = []
    elements = vm_session.periodic_table.elements_by_symbol
    for symbol, entry in elements.items():
        rgb = entry[2] if len(entry) > 2 else (0.7, 0.7, 0.7)
        red, green, blue = (round(max(0, min(1, value)) * 255) for value in rgb[:3])
        number = int(entry[0])
        border = "2px solid #333" if symbol in _QUICK_PICKS else "1px solid #888"
        rules.append(
            f"button.element-z{number} {{ background-color: rgba({red},{green},{blue},0.55); "
            f"border: {border}; padding: 3px; }}"
        )
    provider = Gtk.CssProvider()
    provider.load_from_data("\n".join(rules))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    return elements


def choose_element(main, parent_window=None, on_selected=None):
    """Present a searchable periodic table and call back with symbol or None."""
    vm_session = main.vm_session
    elements = _elements_css(vm_session)
    dialog = Gtk.Dialog(
        title="Periodic Table", transient_for=parent_window or main.window, modal=True
    )
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.set_default_size(620, 430)

    content = dialog.get_content_area()
    content.set_spacing(6)
    for side in ("top", "bottom", "start", "end"):
        getattr(content, f"set_margin_{side}")(8)

    search = Gtk.Entry()
    search.set_placeholder_text('Search by symbol or name (e.g. "Fe" or "iron") — press Enter')
    content.append(search)
    grid = Gtk.Grid(row_spacing=3, column_spacing=3)
    grid.set_row_homogeneous(True)
    grid.set_column_homogeneous(True)
    scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
    scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroller.set_child(grid)
    content.append(scroller)

    selected_symbol = None

    def pick(symbol):
        nonlocal selected_symbol
        selected_symbol = symbol
        dialog.response(Gtk.ResponseType.OK)

    def add_tile(symbol, row, column):
        entry = elements.get(symbol)
        name = str(entry[1]) if entry is not None else symbol
        number = int(entry[0]) if entry is not None else "?"
        button = Gtk.Button(label=symbol)
        button.add_css_class(f"element-z{number}")
        button.set_tooltip_text(f"{name} ({symbol}) — Z={number}")
        button.connect("clicked", lambda _button, element=symbol: pick(element))
        grid.attach(button, column - 1, row - 1, 1, 1)

    for row, entries in enumerate(_MAIN_ROWS, start=1):
        for symbol, column in entries:
            add_tile(symbol, row, column)
    lanthanide_row = len(_MAIN_ROWS) + 2
    for offset, symbol in enumerate(_LANTHANIDES):
        add_tile(symbol, lanthanide_row, 3 + offset)
    for offset, symbol in enumerate(_ACTINIDES):
        add_tile(symbol, lanthanide_row + 1, 3 + offset)

    def on_search_activate(entry):
        query = entry.get_text().strip().casefold()
        if not query:
            return
        exact = next((symbol for symbol in elements if symbol.casefold() == query), None)
        if exact is not None:
            pick(exact)
            return
        matches = [symbol for symbol, data in elements.items() if query in str(data[1]).casefold()]
        if len(matches) == 1:
            pick(matches[0])
        elif not matches:
            entry.add_css_class("error")
        else:
            entry.add_css_class("warning")

    search.connect("activate", on_search_activate)

    def on_response(current_dialog, response):
        current_dialog.destroy()
        if on_selected is not None:
            on_selected(selected_symbol if response == Gtk.ResponseType.OK else None)

    dialog.connect("response", on_response)
    dialog.present()
    return dialog
