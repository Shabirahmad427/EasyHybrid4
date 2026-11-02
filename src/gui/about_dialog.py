"""Help -> About dialog with the runtime "System" report (EH4-510).

GTK4's Gtk.AboutDialog is a Gtk.Window: its logo is a Gdk.Paintable (a
GdkPixbuf.Pixbuf raises TypeError) and it has no GTK3 "response" signal; it
closes itself through the window close button.
"""

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

from src.os_integration.diagnostics import collect_diagnostics, format_diagnostics

LOGO_RELATIVE_PATH = os.path.join("src", "gui", "icons", "easyhybrid_solo_100x100.png")


def build_about_dialog(parent, app_home, gl_area=None):
    """Return a configured, unpresented About dialog transient for parent."""
    dialog = Gtk.AboutDialog(transient_for=parent, modal=True)
    dialog.set_program_name('EasyHybrid')
    dialog.set_version('4.0.0 Beta')
    dialog.set_comments(
        'EasyHybrid is a molecular modeling environment based on pDynamo3, '
        'with a focus on QC/MM hybrid simulations.'
    )
    dialog.set_website('https://github.com/ferbachega/EasyHybrid3')
    dialog.set_website_label('EasyHybrid - project page on GitHub')
    dialog.set_authors([
        'Fernando Bachega (main developer)',
        'Carlos Cerqueiros',
        'Luis Fernando S. Timmers',
        'Martin John Field',
    ])
    dialog.set_license_type(Gtk.License.GPL_3_0)
    # "System" tab: runtime/GL/pDynamo versions for bug reports. The
    # collector never raises, even without a realized GL context.
    dialog.set_system_information(format_diagnostics(collect_diagnostics(
        app_home=app_home, gl_area=gl_area,
    )))
    logo_path = os.path.join(app_home, LOGO_RELATIVE_PATH)
    if os.path.isfile(logo_path):
        dialog.set_logo(Gdk.Texture.new_from_filename(logo_path))
    return dialog
