"""GTK4 window for trajectory backbone phi/psi analysis."""

import os

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
import cairo

from gui.gtk4_builder import choose_path
from gui.widgets.custom_widgets import CoordinatesComboBox, FolderChooserButton, SystemComboBox
from util import ramachandran
from util.rama_plot import CATEGORY_LABELS, RamachandranPlot


class RamachandranAnalysisWindow:
    """Compute and display one phi/psi scatter point per residue and frame."""

    def __init__(self, main=None):
        self.main = main
        self.home = main.home
        self.p_session = main.p_session
        self.vm_session = main.vm_session
        self.Visible = False
        self._last_results = []

    def open_window(self):
        if self.Visible:
            self.window.present()
            return

        self.window = Gtk.Window(title="Ramachandran Analysis", transient_for=self.main.window)
        self.window.set_default_size(720, 850)
        self.window.set_resizable(True)
        self.window.connect("close-request", self.close_window)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(10)
        self.window.set_child(root)

        trajectory = Gtk.Frame(label="Trajectory")
        trajectory_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(trajectory_grid, f"set_margin_{side}")(8)
        trajectory.set_child(trajectory_grid)
        root.append(trajectory)
        trajectory_grid.attach(Gtk.Label(label="System:", xalign=0), 0, 0, 1, 1)
        system_box = Gtk.Box()
        trajectory_grid.attach(system_box, 1, 0, 1, 1)
        trajectory_grid.attach(Gtk.Label(label="Object:", xalign=0), 0, 1, 1, 1)
        coordinate_box = Gtk.Box()
        trajectory_grid.attach(coordinate_box, 1, 1, 1, 1)
        self.combobox_systems = SystemComboBox(self.main)
        self.combobox_systems.connect("notify::selected", self.on_combobox_systems_changed)
        system_box.append(self.combobox_systems)
        self.coordinates_combobox = CoordinatesComboBox()
        self.coordinates_combobox.connect("notify::selected", self.on_coordinates_changed)
        coordinate_box.append(self.coordinates_combobox)

        options = Gtk.Frame(label="Analysis options")
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        for side in ("top", "bottom", "start", "end"):
            getattr(options_box, f"set_margin_{side}")(8)
        options.set_child(options_box)
        root.append(options)
        self.chk_limit_to_selection = Gtk.CheckButton(label="Limit to residues containing selected atoms")
        self.chk_limit_to_selection.set_tooltip_text(
            "Backbone atoms from neighboring residues are still used to calculate each selected residue's angles."
        )
        options_box.append(self.chk_limit_to_selection)
        self.chk_all_frames = Gtk.CheckButton(label="Analyse a trajectory frame range")
        self.chk_all_frames.connect("toggled", self.on_all_frames_checkbox)
        options_box.append(self.chk_all_frames)

        self.frame_range = Gtk.Frame(label="Frame range (last frame included)")
        range_grid = Gtk.Grid(column_spacing=8, row_spacing=5)
        for side in ("top", "bottom", "start", "end"):
            getattr(range_grid, f"set_margin_{side}")(6)
        self.frame_range.set_child(range_grid)
        self.frame_range.set_sensitive(False)
        options_box.append(self.frame_range)
        self.entry_frame_init = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000000, 1, 10, 0), 1, 0)
        self.entry_frame_last = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000000, 1, 10, 0), 1, 0)
        range_grid.attach(Gtk.Label(label="First:", xalign=0), 0, 0, 1, 1)
        range_grid.attach(self.entry_frame_init, 1, 0, 1, 1)
        range_grid.attach(Gtk.Label(label="Last:", xalign=0), 2, 0, 1, 1)
        range_grid.attach(self.entry_frame_last, 3, 0, 1, 1)
        self.chk_step_size = Gtk.CheckButton(label="Use step")
        self.chk_step_size.connect("toggled", self.on_step_size_checkbox)
        range_grid.attach(self.chk_step_size, 0, 1, 2, 1)
        self.entry_step_size = Gtk.SpinButton.new(Gtk.Adjustment.new(1, 1, 1000000, 1, 10, 0), 1, 0)
        self.entry_step_size.set_sensitive(False)
        range_grid.attach(self.entry_step_size, 2, 1, 2, 1)

        save_frame = Gtk.Frame(label="Text output")
        save_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        for side in ("top", "bottom", "start", "end"):
            getattr(save_box, f"set_margin_{side}")(8)
        save_frame.set_child(save_box)
        root.append(save_frame)
        self.chk_save_file = Gtk.CheckButton(label="Save angle table")
        self.chk_save_file.connect("toggled", self.on_save_file_checkbox)
        save_box.append(self.chk_save_file)
        self.grid_save_output = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.grid_save_output.set_sensitive(False)
        save_box.append(self.grid_save_output)
        self.output_folder_chooser = FolderChooserButton(
            self.main, "folder", self.home, parent=self.window
        )
        self.grid_save_output.append(self.output_folder_chooser.btn)
        self.entry_output_filename = Gtk.Entry(text="ramachandran.txt", hexpand=True)
        self.grid_save_output.append(self.entry_output_filename)

        self.label_status = Gtk.Label(
            label="Uncheck trajectory range to analyse the current frame.",
            wrap=True, xalign=0,
        )
        root.append(self.label_status)
        self._default_status_text = self.label_status.get_text()

        self.plot = RamachandranPlot()
        self.plot.on_hover_callback = self._on_plot_hover
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(self.plot)
        root.append(scroll)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        root.append(buttons)
        self.btn_export_png = Gtk.Button(label="Export PNG…")
        self.btn_export_png.connect("clicked", self.on_btn_export_png_clicked)
        buttons.append(self.btn_export_png)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.close_window)
        buttons.append(close)
        run = Gtk.Button(label="Run Analysis")
        run.add_css_class("suggested-action")
        run.connect("clicked", self.on_btn_run_analysis)
        buttons.append(run)

        if self.p_session.psystem:
            self.combobox_systems.set_active_system(e_id=self.p_session.active_id)
        self.window.present()
        self.Visible = True

    def on_save_file_checkbox(self, widget):
        self.grid_save_output.set_sensitive(widget.get_active())

    def on_all_frames_checkbox(self, widget):
        self.frame_range.set_sensitive(widget.get_active())

    def on_step_size_checkbox(self, widget):
        self.entry_step_size.set_sensitive(widget.get_active())

    def on_combobox_systems_changed(self, _widget, _pspec=None):
        system_id = self.combobox_systems.get_system_id()
        if system_id is None:
            return
        system = self.p_session.psystem.get(system_id)
        if system is not None and getattr(system, "e_working_folder", None):
            self.output_folder_chooser.set_folder(folder=system.e_working_folder)
        model = self.main.vobject_liststore_dict.get(system_id)
        self.coordinates_combobox.set_model(model)
        count = model.get_n_items() if model is not None else 0
        self.coordinates_combobox.set_active_vobject(count - 1)

    def on_coordinates_changed(self, _widget, _pspec=None):
        object_id = self.coordinates_combobox.get_vobject_id()
        vismol_object = self.vm_session.vm_objects_dic.get(object_id)
        if vismol_object is None:
            return
        last_frame = max(0, int(vismol_object.frames.shape[0]) - 1)
        for spin in (self.entry_frame_init, self.entry_frame_last):
            spin.get_adjustment().set_upper(last_frame)
        self.entry_frame_init.set_value(0)
        self.entry_frame_last.set_value(last_frame)

    def close_window(self, *_args):
        if self.Visible:
            self.window.destroy()
            self.Visible = False
        return True

    def _on_plot_hover(self, point):
        if point is None:
            self.label_status.set_text(self._default_status_text)
            return
        frame = "" if point["frame"] is None else f" (frame {point['frame']})"
        category = CATEGORY_LABELS.get(point["category"], point["category"])
        self.label_status.set_text(
            f"{point['resname']}{point['resnum']} — chain {point['chain'] or '-'} — "
            f"φ = {point['phi']:.1f}°, ψ = {point['psi']:.1f}°{frame} — {category}"
        )

    def _save_text_to_file(self, text):
        folder = self.output_folder_chooser.get_folder()
        if not folder:
            self.main.simple_dialog.info(msg="Please choose an output folder.")
            return False
        filename = self.entry_output_filename.get_text().strip() or "ramachandran.txt"
        if not filename.lower().endswith(".txt"):
            filename += ".txt"
        try:
            with open(os.path.join(folder, filename), "w", encoding="utf-8") as output:
                output.write(text)
        except OSError as error:
            self.main.simple_dialog.info(msg=f"Could not save the results:\n{error}")
            return False
        return True

    def _residues_with_selected_atoms(self, vismol_object):
        atom_indices, _residues, selected_object = self.vm_session.build_index_list_from_atom_selection(
            return_vobject=True
        )
        if selected_object is not vismol_object or not atom_indices:
            return None
        keys = set()
        for atom_index in atom_indices:
            residue = vismol_object.atoms[atom_index].residue
            if residue is not None:
                chain = residue.chain.name if residue.chain is not None else None
                keys.add((chain, residue.index))
        return keys

    @staticmethod
    def _results_to_text(results):
        lines = ["chain\tresidue\tresnum\tcategory\tframe\tphi\tpsi"]
        for result in results:
            lines.append(
                "{}\t{}\t{}\t{}\t{}\t{:.4f}\t{:.4f}".format(
                    result["chain"], result["resname"], result["resnum"],
                    result["category"], "" if result["frame"] is None else result["frame"],
                    result["phi"], result["psi"],
                )
            )
        return "\n".join(lines) + "\n"

    def on_btn_run_analysis(self, _button):
        object_id = self.coordinates_combobox.get_vobject_id()
        if object_id is None:
            self.main.simple_dialog.info(msg="Please select a System and an Object first.")
            return
        vismol_object = self.vm_session.vm_objects_dic.get(object_id)
        if vismol_object is None:
            self.main.simple_dialog.info(msg="Please select a valid Object.")
            return

        if self.chk_all_frames.get_active():
            n_frames = int(vismol_object.frames.shape[0])
            first = self.entry_frame_init.get_value_as_int()
            last = self.entry_frame_last.get_value_as_int()
            step = self.entry_step_size.get_value_as_int() if self.chk_step_size.get_active() else 1
            if first < 0 or last >= n_frames or first > last or step < 1:
                self.main.simple_dialog.info(
                    msg=f"Choose a frame range within 0–{max(0, n_frames - 1)} and a positive step."
                )
                return
            frame_indices = list(range(first, last + 1, step))
        else:
            current_frame = int(self.vm_session.frame)
            n_frames = int(vismol_object.frames.shape[0])
            if not 0 <= current_frame < n_frames:
                self.main.simple_dialog.info(
                    msg="The current viewer frame is outside the selected Object's trajectory."
                )
                return
            frame_indices = [current_frame]

        self._last_results = []
        self.plot.set_data([])
        results = ramachandran.compute_phi_psi(vismol_object, frame_indices=frame_indices)
        if self.chk_limit_to_selection.get_active():
            selected_residues = self._residues_with_selected_atoms(vismol_object)
            if not selected_residues:
                self.main.simple_dialog.info(
                    msg="There is no atom selection on the chosen Object. Select atoms in the 3D view or disable the selection filter."
                )
                return
            results = [r for r in results if (r["chain"], r["resnum"]) in selected_residues]
        if not results:
            self.main.simple_dialog.info(
                msg="No phi/psi angles could be calculated. Protein residues need backbone N, CA, and C atoms and an intact peptide bond to a neighboring residue."
            )
            return

        self._last_results = results
        self.plot.set_data(results)
        residue_count = len({(r["chain"], r["resnum"]) for r in results})
        frame_count = len({r["frame"] for r in results})
        self.label_status.set_text(
            f"Plotted {len(results)} points from {residue_count} residues across {frame_count} frame(s). Hover over a point for residue details."
        )
        if self.chk_save_file.get_active():
            self._save_text_to_file(self._results_to_text(results))

    def on_btn_export_png_clicked(self, _button):
        if not self._last_results:
            self.main.simple_dialog.info(msg="Run the analysis first.")
            return

        def save_plot(path):
            if not path:
                return
            if not path.lower().endswith(".png"):
                path += ".png"
            width = max(460, self.plot.get_width())
            height = max(460, self.plot.get_height())
            scale = 4
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * scale, height * scale)
            context = cairo.Context(surface)
            self.plot.render(context, width, height, scale=scale)
            try:
                surface.write_to_png(path)
            except OSError as error:
                self.main.simple_dialog.info(msg=f"Could not export the plot:\n{error}")
            finally:
                surface.finish()

        choose_path(
            self.window, save_plot, title="Export Ramachandran plot",
            action=Gtk.FileChooserAction.SAVE,
            initial_path=os.path.join(self.output_folder_chooser.get_folder() or self.home,
                                      "ramachandran.png"),
            overwrite_confirmation=True,
        )
