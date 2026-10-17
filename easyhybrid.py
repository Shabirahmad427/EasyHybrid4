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

import os, sys, time, re, json
import logging

# --- Fix: engasgo de rotacao em GPUs integradas Intel (driver Mesa/GLX) ---
# Em GPUs integradas Intel com driver Mesa, um frame que atrasa levemente
# (jitter normal do loop do GTK/Python) perde a janela de vblank e o
# driver trava o frame seguinte ate o PROXIMO vblank, dobrando a latencia
# daquele frame. Isso aparece como engasgo aleatorio durante rotacao/pan/
# zoom do mouse, mesmo com o custo de render() baixo e estavel (medido e
# confirmado em testes). Desligar o vsync (vblank_mode=0) resolve, mas so
# fazemos isso quando detectamos uma GPU Intel: em GPUs NVIDIA o problema
# nao ocorre, entao nao vale a pena aceitar o tearing la sem necessidade.
# CRITICO: essa variavel de ambiente so tem efeito se for definida ANTES
# do contexto GL ser criado pelo Mesa - por isso essa deteccao roda aqui,
# no topo do arquivo, antes de qualquer import do GTK/OpenGL.
#
# O usuario pode sobrepor esse auto-detect via Preferences > Startup >
# "V-Sync (vblank_mode)" (ver setup_interface.py/.glade), que grava a
# preferencia ('auto'/'on'/'off') em gl_parameters['vblank_mode'] e persiste
# no .config.json (gui/config.py). Lemos esse arquivo aqui, como JSON cru
# (sem importar gui.config), porque isso precisa rodar antes do GTK ser
# importado -- so tem efeito na PROXIMA vez que o EasyHybrid for aberto.
def _load_vblank_mode_preference():
    """ Le a preferencia 'vblank_mode' salva em .config.json ('auto', 'on'
        ou 'off'). Retorna 'auto' (comportamento padrao/legado) se o
        arquivo nao existir, nao tiver a chave, ou nao puder ser lido.
    """
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config.json")
        with open(config_path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return data.get("vblank_mode", "auto")
    except (OSError, ValueError):
        return "auto"

def _maybe_disable_vsync_for_intel_igpu():
    if "vblank_mode" in os.environ:
        return  # usuario ou launcher ja definiu explicitamente; respeita

    preference = _load_vblank_mode_preference()
    if preference == "off":
        os.environ["vblank_mode"] = "0"
        return
    if preference == "on":
        os.environ["vblank_mode"] = "1"
        return
    # preference == "auto" (default): mantem o auto-detect de GPU Intel abaixo.

    if sys.platform != "linux":
        return
    try:
        import glob
        card_pattern = re.compile(r"^card\d+$")
        for vendor_path in glob.glob("/sys/class/drm/card*/device/vendor"):
            card_name = vendor_path.split("/")[-3]
            if not card_pattern.match(card_name):
                continue
            with open(vendor_path) as f:
                vendor_id = f.read().strip()
            if vendor_id == "0x8086":  # Intel
                os.environ["vblank_mode"] = "0"
                return
    except OSError:
        pass  # falha na deteccao nao deve impedir o programa de iniciar

_maybe_disable_vsync_for_intel_igpu()

# On newer GTK4 releases, prefer GLX on X11 because some NVIDIA driver
# combinations cannot create Gtk.GLArea contexts through EGL. These GDK_DEBUG
# options are not recognized by early GTK4 releases, so detect the loaded GTK
# runtime before adding them. Do not apply this on Wayland, Windows, or macOS.
def _gtk4_runtime_version():
    try:
        import ctypes
        import ctypes.util
        library_path = ctypes.util.find_library("gtk-4")
        if not library_path:
            return None
        gtk_library = ctypes.CDLL(library_path)
        major = gtk_library.gtk_get_major_version
        minor = gtk_library.gtk_get_minor_version
        major.restype = minor.restype = ctypes.c_uint
        return major(), minor()
    except (AttributeError, OSError):
        return None


if (sys.platform.startswith("linux") and os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")):
    gtk_runtime = _gtk4_runtime_version()
    if gtk_runtime is not None and gtk_runtime >= (4, 14):
        gdk_debug_flags = os.environ.get("GDK_DEBUG", "").replace(",", ":").split(":")
        for flag in ("gl-glx", "gl-prefer-gl"):
            if flag not in gdk_debug_flags:
                gdk_debug_flags.append(flag)
        os.environ["GDK_DEBUG"] = ":".join(flag for flag in gdk_debug_flags if flag)

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
            if hasattr(image, "set_content_fit"):
                image.set_content_fit(Gtk.ContentFit.CONTAIN)
            else:
                # Gtk.ContentFit was added in GTK 4.8; this is its GTK 4.0
                # equivalent for keeping the splash image inside the window.
                image.set_can_shrink(True)
                image.set_keep_aspect_ratio(True)
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
