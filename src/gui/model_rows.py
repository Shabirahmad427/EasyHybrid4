"""Typed GTK4 list rows shared by system and coordinate selectors."""

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GObject


class SystemChoiceRow(GObject.Object):
    name = GObject.Property(type=str, default="")
    system_id = GObject.Property(type=int, default=-1)
    icon = GObject.Property(type=GdkPixbuf.Pixbuf)

    def __init__(self, name, system_id, icon=None):
        super().__init__()
        self.name = name
        self.system_id = system_id
        self.icon = icon


class CoordinateChoiceRow(GObject.Object):
    name = GObject.Property(type=str, default="")
    object_id = GObject.Property(type=int, default=-1)
    system_id = GObject.Property(type=int, default=-1)
    icon = GObject.Property(type=GdkPixbuf.Pixbuf)

    def __init__(self, name, object_id, system_id, icon=None):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.system_id = system_id
        self.icon = icon


class ReactionCoordinateRow(GObject.Object):
    atom1_name = GObject.Property(type=str, default="")
    atom1_index = GObject.Property(type=str, default="")
    atom2_name = GObject.Property(type=str, default="")
    atom2_index = GObject.Property(type=str, default="")
    weight = GObject.Property(type=str, default="")
    distance = GObject.Property(type=str, default="")

    def __init__(self, values):
        super().__init__()
        (self.atom1_name, self.atom1_index, self.atom2_name,
         self.atom2_index, self.weight, self.distance) = values

    def as_list(self):
        return [self.atom1_name, self.atom1_index, self.atom2_name,
                self.atom2_index, self.weight, self.distance]


class ChoiceRow(GObject.Object):
    value = GObject.Property(type=str, default="")
    label = GObject.Property(type=str, default="")

    def __init__(self, value, label):
        super().__init__()
        self.value = value
        self.label = label


class SelectionChoiceRow(GObject.Object):
    name = GObject.Property(type=str, default="")
    atom_count = GObject.Property(type=int, default=0)

    def __init__(self, name, atom_count):
        super().__init__()
        self.name = name
        self.atom_count = atom_count


class PeriodicElementRow(GObject.Object):
    atomic_number = GObject.Property(type=int, default=0)
    symbol = GObject.Property(type=str, default="")
    color = GObject.Property(type=GdkPixbuf.Pixbuf)
    mass = GObject.Property(type=str, default="")
    covalent_radius = GObject.Property(type=str, default="")
    van_der_waals_radius = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="")

    def __init__(self, atomic_number, symbol, color, mass, covalent_radius,
                 van_der_waals_radius, name):
        super().__init__()
        self.atomic_number = atomic_number
        self.symbol = symbol
        self.color = color
        self.mass = mass
        self.covalent_radius = covalent_radius
        self.van_der_waals_radius = van_der_waals_radius
        self.name = name


class AtomTypeRow(GObject.Object):
    """One atom in the GTK4 Builder DYFF inspector."""
    atom_id = GObject.Property(type=int, default=-1)
    symbol = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="")
    type_label = GObject.Property(type=str, default="?")
    source = GObject.Property(type=str, default="auto")
    tooltip = GObject.Property(type=str, default="")
    formal_charge = GObject.Property(type=int, default=0)
    hybridization = GObject.Property(type=str, default="")

    def __init__(self, atom_id, symbol, name, type_label, source, tooltip,
                 formal_charge, hybridization):
        super().__init__()
        self.atom_id = atom_id
        self.symbol = symbol
        self.name = name
        self.type_label = type_label
        self.source = source
        self.tooltip = tooltip
        self.formal_charge = formal_charge
        self.hybridization = hybridization


class OPLSParameterRow(GObject.Object):
    """Display and quality metadata for one OPLS parameter table row."""
    cells = GObject.Property(type=object)
    level = GObject.Property(type=str, default="gray")
    quality = GObject.Property(type=str, default="unknown")
    row_id = GObject.Property(type=int, default=-1)

    def __init__(self, row_id, cells, level, quality):
        super().__init__()
        self.row_id = row_id
        self.cells = list(cells)
        self.level = level
        self.quality = quality
