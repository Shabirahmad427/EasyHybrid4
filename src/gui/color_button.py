"""A colour button that works on every supported GTK4 minor.

Gtk.ColorButton is deprecated since GTK 4.10 and its replacement,
Gtk.ColorDialogButton, does not exist on GTK 4.8. ColorButton keeps the
Gtk.ColorButton API EasyHybrid uses -- the ``rgba``, ``use-alpha`` and
``title`` properties, get_rgba()/set_rgba(), new_with_rgba() and the
``color-set`` signal (emitted only when the user picks a colour) -- and
opens the chooser through gui.file_dialogs.choose_color (Gtk.ColorDialog on
GTK 4.10+, its GTK 4.8 equivalent otherwise). The same code path runs on
Linux, Windows and macOS.

Builder files name it ``EasyHybridColorButton``; importing this module
registers that type (gui.gtk4_builder imports it).
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GObject, Gtk  # noqa: E402

from gui import file_dialogs  # noqa: E402


def _rgba(red, green, blue, alpha=1.0):
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


class ColorButton(Gtk.Button):
    """Gtk.Button showing a colour swatch; clicking it opens a colour chooser."""

    __gtype_name__ = "EasyHybridColorButton"
    __gsignals__ = {
        "color-set": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    title = GObject.Property(type=str, default="Pick a Color")
    use_alpha = GObject.Property(type=bool, default=False)

    def __init__(self, **properties):
        # Same initial colour as Gtk.ColorButton.
        self._rgba = _rgba(0.75, 0.25, 0.25)
        super().__init__(**properties)
        self.add_css_class("color")
        self._swatch = Gtk.DrawingArea(content_width=28, content_height=16)
        self._swatch.set_draw_func(self._draw_swatch)
        self.set_child(self._swatch)
        self.connect("clicked", self._on_clicked)
        self.chooser = None

    @classmethod
    def new_with_rgba(cls, rgba):
        return cls(rgba=rgba)

    @GObject.Property(type=Gdk.RGBA)
    def rgba(self):
        return self._rgba.copy()

    @rgba.setter
    def rgba(self, value):
        if value is None:
            return
        self._rgba = value.copy()
        swatch = getattr(self, "_swatch", None)
        if swatch is not None:
            swatch.queue_draw()

    def get_rgba(self):
        return self.rgba

    def set_rgba(self, rgba):
        self.rgba = rgba

    def _on_clicked(self, _button):
        self.chooser = file_dialogs.choose_color(
            self, self._on_color_chosen, title=self.title,
            initial=self._rgba, with_alpha=self.use_alpha,
        )

    def _on_color_chosen(self, rgba):
        self.chooser = None
        if rgba is None:
            return
        if not self.use_alpha:
            rgba = rgba.copy()
            rgba.alpha = 1.0
        self.rgba = rgba
        self.emit("color-set")

    def _draw_swatch(self, _area, context, width, height):
        color = self._rgba
        if color.alpha < 1.0:
            # Checkerboard so translucent colours remain visible.
            size = 4
            for row in range(0, height, size):
                for column in range(0, width, size):
                    shade = 0.8 if (row // size + column // size) % 2 else 0.6
                    context.set_source_rgb(shade, shade, shade)
                    context.rectangle(column, row, size, size)
                    context.fill()
        context.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        context.rectangle(0, 0, width, height)
        context.fill()
        context.set_source_rgba(0, 0, 0, 0.35)
        context.set_line_width(1)
        context.rectangle(0.5, 0.5, width - 1, height - 1)
        context.stroke()
