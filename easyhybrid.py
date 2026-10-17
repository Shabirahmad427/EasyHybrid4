#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: Selection utilities for pDynamo systems
#
#  Copyright 2022-2025 Fernando Bachega
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  Maintainer:
#      Fernando Bachega <ferbachega@gmail.com> or <easyhybrid3@gmail.com>
#
#  Description:
#      Provides functions for selecting atoms and residues in pDynamo systems
#      to facilitate QM/MM partitioning and molecular simulations.
#
#import gc
#gc.disable()          # teste de diagnostico: desliga o coletor de lixo automatico
#gc.set_threshold(0)   # garante que nao ha coleta automatica por contagem

from _version import EASYHYBRID_VERSION

import os, sys, time, re
import logging
from src.os_integration.gtk_startup import configure_startup_environment

# Prepare legacy graphics-driver environment before GTK/OpenGL imports.
configure_startup_environment(os.path.dirname(os.path.abspath(__file__)))

'''
O módulo re é nativo do Python (faz parte da biblioteca padrão).  
Você não precisa instalar nada.Ele implementa expressões regulares 
(regular expressions) para busca e manipulação de texto.
'''


'''
os.environ["PDYNAMO3_HOME"]         = "~/programs/pDynamo3"
os.environ["PDYNAMO3_PARAMETERS"]   = "~/programs/pDynamo3/parameters"
os.environ["PDYNAMO3_SCRATCH"]      = "~/programs/pDynamo3/scratch"
os.environ["PDYNAMO3_ORCACOMMAND"]  = "~/programs/orca_6_1_0_linux_x86-64_shared_openmpi418/orca"
os.environ["PDYNAMO3_XTBCOMMAND"]   = "~/programs/xtb-6.6.1/bin/xtb"
os.environ["PDYNAMO3_MOPACCOMMAND"] = "~/programs/MOPAC2016A/bin/mopac"
os.environ["PDYNAMO3_DFTBCOMMAND"]  = "~/programs/dftbplus-24.1.x86_64-linux/bin/dftb+"
sys.path.append("~/programs/pDynamo3")
#sys.path.append("~/programs/amber24_src/lib/python3.12/site-packages")
'''

#filepath = '~/programs/pDynamo3/installation/shellScripts/environment_bash.com'

def parse_bash_env_file(filepath):
    """
    Parse a bash environment file and return a dictionary
    with environment variables and values.
    """
    env_vars = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()

            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Remove inline comments
            line = line.split("#")[0].strip()

            # Remove "; export VAR"
            line = re.sub(r";\s*export\s+\w+", "", line)

            if "=" in line:
                var, value = line.split("=", 1)
                var = var.strip()
                value = value.strip()

                env_vars[var] = value

    # Expand variables
    for var, value in env_vars.items():
        # Expand variables like $HOME, $PDYNAMO3_HOME etc
        value = os.path.expandvars(value)
        # Expand ~
        value = os.path.expanduser(value)
        env_vars[var] = value
        # Add to environment
        os.environ[var] = value

    # Add pDynamo to python path
    if "PDYNAMO3_HOME" in env_vars:
        sys.path.append(env_vars["PDYNAMO3_HOME"])

    return env_vars


PDYNAMO_HOME = os.environ.get("PDYNAMO3_HOME")
try:
    from paths import PDYNAMO_HOME as _ConfiguredPDYNAMO_HOME
    PDYNAMO_HOME = _ConfiguredPDYNAMO_HOME
except ImportError:
    # The launcher may already have activated pDynamo3 without paths.py.
    pass

if PDYNAMO_HOME:
    shell_scripts = os.path.join(PDYNAMO_HOME, 'installation/shellScripts/environment_bash.com')
    environment_is_loaded = all(os.environ.get(name) for name in (
        "PDYNAMO3_HOME", "PDYNAMO3_PARAMETERS", "PDYNAMO3_SCRATCH"
    ))
    if os.path.isfile(shell_scripts) and not environment_is_loaded:
        parse_bash_env_file(shell_scripts)
        logging.info('Importing environment variables from: %s', shell_scripts)
elif os.path.isfile("paths.py"):
    logging.warning('paths.py does not define PDYNAMO_HOME; pDynamo3 environment '
                    'variables were not imported.')

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
from src.gtk4_compat import set_picture_contain


#               Installation is not necessary anymore.
#.This retrieves the absolute path of the script file that is currently being executed.
easy_main_file = os.path.abspath(__file__)

#.This extracts the directory (folder) from the absolute path obtained in the previous step.
EASYHYBRID_HOME = os.path.dirname(easy_main_file)

#.Adding GRAPHIC ENGINE LIB
sys.path.append(os.path.join(EASYHYBRID_HOME,"src/graphics_engine/src"))
sys.path.append(os.path.join(EASYHYBRID_HOME,"src/"))


from gui.main import MainWindow
from gui.eSession import EasyHybridSession
from gui.config   import VismolConfig
import time
import threading









# Splash Screen
class SplashScreen(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="splash.png")
        self.set_decorated(False)
        self.set_default_size(605 ,605)
        try:
            image = Gtk.Picture.new_for_filename(
                os.path.join(EASYHYBRID_HOME, "splash.png")
            )
            set_picture_contain(image, Gtk)
            self.set_child(image)
        except Exception as e:
            logging.warning('splash.png could not be loaded (%s) -- '
                             'showing an empty splash window instead.', e)

def load_modules(callback_final):
    def _load():
        logging.info("Starting module loading...")
        time.sleep(1.5)   
        GLib.idle_add(callback_final)  #Call the finalize function in the main loop
    threading.Thread(target=_load).start()


class EasyHybridApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.easyhybrid.EasyHybrid4",
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.pending_open_files = []

    def do_open(self, files, n_files, _hint):
        """Open files passed to the launcher after the GTK window is ready."""
        self.pending_open_files.extend(
            file.get_path() for file in files[:n_files] if file.get_path()
        )
        self.activate()

    def do_activate(self):
        self.hold()
        self.splash = SplashScreen(application=self)
        self.splash.present()

        def on_modules_loaded():
            logging.basicConfig(format="%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
                                datefmt="%Y-%m-%d:%H:%M:%S", level=logging.DEBUG)
    
            vconfig = VismolConfig(home = EASYHYBRID_HOME)
            # VismolConfig loads the saved configuration and validates the
            # startup path in its constructor. Loading it again here would
            # merge the unvalidated file values back into the corrected state.
            
            
            vm_session = EasyHybridSession(vm_config = vconfig)
            vm_session.vm_widget.insert_glmenu()
            self.main_window = MainWindow(vm_session = vm_session,
                                          home       = EASYHYBRID_HOME,
                                          version    = EASYHYBRID_VERSION)
            self.main_window.window.set_application(self)
            vm_session.main_session = self.main_window
            #print(vm_session.vm_config.gl_parameters)
            
            
            # Hide features that are not exposed by the EasyHybrid3 interface.
            
            #main_window.builder.get_object('toolbutton_export_img').hide()
            #main_window.builder.get_object('button_task_list')           .hide()
            
            # Experimental items are omitted by the GTK4 menu builder, just
            # as EasyHybrid3 hid them immediately after creating the window.
            #main_window.builder.get_object('toolbutton_terminal')   .hide()
            #main_window.builder.get_object('menuitem_reimaging')   .hide()
            #main_window.builder.get_object('menuitem_RMSD_tool')   .hide()
            
            #main_window.builder.get_object('menuitem_advanced_rc_scans').hide()
            
            self.splash.close()
            self.release()
            filenames, self.pending_open_files = self.pending_open_files, []
            if not filenames and len(sys.argv) > 1 and not sys.argv[-1].startswith("-"):
                filenames = [sys.argv[-1]]
            for filein in filenames:
                vm_session.load(filein)
            return 0

        load_modules(on_modules_loaded)


def main():
    application = EasyHybridApplication()
    return application.run(sys.argv)


if __name__ == "__main__":
    main()
