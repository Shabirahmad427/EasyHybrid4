"""Real-context VisMol render validation (EH4-202); run by
tests/test_vismol_render_validation.py in its own process.

Prints one ``EASYHYBRID_RENDER_VALIDATION=<json>`` line and exits 0 only if
every in-process check passes. Checks, all on the live Gtk.GLArea context:

* GL capabilities required by VisMol (core 3.3, GLSL 3.30, render-target
  limits large enough for the 2x offscreen export).
* Every representation drawn alone leaves visible pixels and no GL error.
* Impostor sprite spheres match their exact projected diameter, or are
  clamped to GL_POINT_SIZE_RANGE where the driver caps point sprites.
* The 2x offscreen framebuffer export (render_to_image) matches the
  on-screen frame and restores framebuffer/viewport state.
* Colour-ID picking on the spheres and impostor representations.
* After a resize, viewport/projection follow the new size, spheres keep
  their aspect and picking still hits.

Cross-scale comparisons (GDK_SCALE=1 vs 2) are made by the pytest wrapper.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from src.os_integration.gtk_startup import configure_startup_environment  # noqa: E402

configure_startup_environment(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "src", "graphics_engine", "src"))

import numpy as np  # noqa: E402
import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402
from OpenGL import GL  # noqa: E402
from vismol.core.vismol_selections import VismolViewingSelection  # noqa: E402
from vismol.core.vismol_session import VismolSession  # noqa: E402
from vismol.utils import parser  # noqa: E402

# Representations drawn one at a time. "lines"/"nonbonded" are 1-pixel GL
# lines by design and are only required to be visible.
REPRESENTATIONS = ("lines", "nonbonded", "sticks", "spheres", "vdw_spheres",
                   "stick_spheres", "dots", "impostor")
# A water molecule (bonded representations) and three isolated atoms 4 A
# apart, so each impostor sphere can be measured on its own.
ATOMS = (
    ("O", "HOH", 1, 0.000, 3.000, "O"),
    ("H1", "HOH", 1, 0.957, 3.000, "H"),
    ("H2", "HOH", 1, -0.240, 3.927, "H"),
    ("C", "CAA", 2, -4.000, -2.000, "C"),
    ("N", "NAA", 3, 0.000, -2.000, "N"),
    ("S", "SAA", 4, 4.000, -2.000, "S"),
)
ISOLATED = ("C", "N", "S")
PICK_OFFSETS = ((0, 0), (3, 0), (-3, 0), (0, 3), (0, -3),
                (2, 2), (2, -2), (-2, 2), (-2, -2))
WINDOW = (420, 300)
RESIZED = (560, 240)

result = {"checks": {}, "failures": []}
state = {"pending": None, "capture": None, "busy": False}


def check(name, ok, detail):
    result["checks"][name] = {"ok": bool(ok), "detail": detail}
    if not ok:
        result["failures"].append(name)


def fixture_pdb(directory):
    lines = [
        "HETATM%5d %-4s %3s A%4d    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  "
        % (index, name, residue, number, x, y, 0.0, 1.0, 0.0, element)
        for index, (name, residue, number, x, y, element) in enumerate(ATOMS, 1)
    ]
    path = os.path.join(directory, "render_validation.pdb")
    with open(path, "w", encoding="ascii") as handle:
        handle.write("\n".join(lines) + "\nEND\n")
    return path


def wrap_render(glcore):
    """Read the GLArea framebuffer inside render(), where GTK binds it."""
    original = glcore.render

    def render(rotating=False):
        value = original(rotating)
        request = state["pending"]
        if request and not state["busy"]:
            state["pending"] = None
            state["busy"] = True
            try:
                viewport = [int(v) for v in GL.glGetIntegerv(GL.GL_VIEWPORT)]
                GL.glFinish()
                GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
                data = GL.glReadPixels(0, 0, viewport[2], viewport[3],
                                       GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
                image = np.frombuffer(data, np.uint8).reshape(viewport[3], viewport[2], 4)
                capture = {
                    "image": np.ascontiguousarray(np.flip(image, 0)),
                    "viewport": viewport,
                    "error": int(GL.glGetError()),
                    "framebuffer": int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)),
                }
                if request == "export":
                    capture["export"] = glcore.render_to_image(2)
                    capture["framebuffer_after"] = int(
                        GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
                    capture["viewport_after"] = [
                        int(v) for v in GL.glGetIntegerv(GL.GL_VIEWPORT)]
                    capture["export_error"] = int(GL.glGetError())
                state["capture"] = capture
            finally:
                state["busy"] = False
        return value

    glcore.render = render


def save_image(name, image):
    """Optional PNG dump for debugging (EASYHYBRID_RENDER_VALIDATION_DIR)."""
    directory = os.environ.get("EASYHYBRID_RENDER_VALIDATION_DIR")
    if directory:
        from PIL import Image

        Image.fromarray(image).save(os.path.join(directory, name + ".png"))


def foreground(image, background):
    return np.abs(image[..., :3].astype(int) - np.array(background[:3])).max(-1) > 8


def component_at(mask, x, y):
    """Pixels of the connected foreground blob containing (x, y)."""
    x, y = int(round(x)), int(round(y))
    if not (0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]) or not mask[y, x]:
        return np.zeros_like(mask)
    region = np.zeros_like(mask)
    region[y, x] = True
    while True:
        grown = region.copy()
        grown[1:, :] |= region[:-1, :]
        grown[:-1, :] |= region[1:, :]
        grown[:, 1:] |= region[:, :-1]
        grown[:, :-1] |= region[:, 1:]
        grown &= mask
        if (grown == region).all():
            return region
        region = grown


def capabilities(widget):
    widget.make_current()
    caps = {
        name: GL.glGetString(getattr(GL, name)).decode("utf-8", "replace")
        for name in ("GL_VERSION", "GL_RENDERER", "GL_VENDOR",
                     "GL_SHADING_LANGUAGE_VERSION")
    }
    for name in ("GL_MAX_TEXTURE_SIZE", "GL_MAX_RENDERBUFFER_SIZE", "GL_MAX_SAMPLES"):
        caps[name] = int(GL.glGetIntegerv(getattr(GL, name)))
    caps["GL_MAX_VIEWPORT_DIMS"] = [int(v) for v in GL.glGetIntegerv(GL.GL_MAX_VIEWPORT_DIMS)]
    for name in ("GL_POINT_SIZE_RANGE", "GL_LINE_WIDTH_RANGE"):
        caps[name] = [float(v) for v in GL.glGetFloatv(getattr(GL, name))]
    caps["widget_scale_factor"] = int(widget.get_scale_factor())
    return caps


def version_tuple(text):
    import re

    match = re.search(r"(\d+)\.(\d+)", text)
    return tuple(int(part) for part in match.groups()) if match else (0, 0)


def projected(core, molecule, atom):
    from gui.windows.builder.click_mode import _project_local_point_to_pixel

    x, y, view_z = _project_local_point_to_pixel(core, molecule, atom.coords(state["session"].frame))
    return x, y, view_z


def pick(core, widget, x_fb, y_fb):
    """Pick through the production GTK gesture path (logical coordinates)."""
    from gi.repository import Gdk

    class Click:
        def get_current_button(self):
            return 1

        def get_current_event_state(self):
            return Gdk.ModifierType(0)

        def get_current_event(self):
            return None

    x = x_fb * widget.get_width() / core.width
    y = y_fb * widget.get_height() / core.height
    widget._on_mouse_pressed(Click(), 1, x, y)
    widget._on_mouse_released(Click(), 1, x, y)


def run_steps():
    """Yield-driven script; each yield waits one main-loop tick."""
    session = state["session"]
    widget = session.vm_widget
    core = widget.vm_glcore
    while not widget.get_realized():
        yield

    caps = capabilities(widget)
    result["caps"] = caps
    gl_version = version_tuple(caps["GL_VERSION"])
    check("gl_core_3_3", gl_version >= (3, 3), caps["GL_VERSION"])
    check("glsl_3_30", version_tuple(caps["GL_SHADING_LANGUAGE_VERSION"]) >= (3, 30),
          caps["GL_SHADING_LANGUAGE_VERSION"])

    with tempfile.TemporaryDirectory(prefix="easyhybrid-render-") as directory:
        molecule, show = parser.parse_file(session, fixture_pdb(directory))
    molecule._generate_color_vectors(session.atom_id_counter)
    molecule.active = True
    VismolSession._add_vismol_object(session, molecule, show_molecule=show)
    selection = VismolViewingSelection(session)
    selection.selecting_by_indexes(molecule, list(molecule.atoms.keys()), clear=True)
    for name in REPRESENTATIONS:
        session.show_or_hide(rep_type=name, selection=selection, show=True)
    atoms = {atom.name: atom for atom in molecule.atoms.values()}
    check("fixture_bonds", len(molecule.bonds) == 2, len(molecule.bonds))

    # Wait for the animated auto-centre to finish.
    for _ in range(12):
        yield

    def inside_margin():
        for atom in atoms.values():
            x, y, _ = projected(core, molecule, atom)
            if x is None or not (0.2 * core.width <= x <= 0.8 * core.width
                                 and 0.2 * core.height <= y <= 0.8 * core.height):
                return False
        return True

    def spread():
        values = []
        for atom in atoms.values():
            x, y, _ = projected(core, molecule, atom)
            if x is None:
                return float("inf")
            values.append(max(abs(x / core.width - 0.5), abs(y / core.height - 0.5)))
        return max(values)

    # Frame the whole fixture with VisMol's zoom (camera dolly used by the
    # zoom drag); the mouse wheel moves clipping planes, not the camera.
    before = spread()
    core._zoom_view(10)
    direction = 10 if spread() < before else -10
    zoom_steps = 1
    while not inside_margin() and zoom_steps < 400:
        core._zoom_view(direction)
        zoom_steps += 1
    widget.queue_render()
    yield
    check("fixture_framed", inside_margin(), {"zoom_steps": zoom_steps, "spread": round(spread(), 3)})

    framebuffer = (int(core.width), int(core.height))
    largest = 2 * max(framebuffer)
    check("export_render_target_limits",
          caps["GL_MAX_RENDERBUFFER_SIZE"] >= largest and caps["GL_MAX_TEXTURE_SIZE"] >= largest
          and min(caps["GL_MAX_VIEWPORT_DIMS"]) >= largest,
          {"framebuffer": framebuffer, "needed": largest})
    result["framebuffer"] = framebuffer
    result["logical"] = (widget.get_width(), widget.get_height())
    result["scale_applied"] = framebuffer[1] > widget.get_height()

    def activate_only(*names):
        for key, representation in molecule.representations.items():
            if representation is not None:
                representation.active = key in names

    def capture(kind):
        state["capture"] = None
        state["pending"] = kind
        widget.queue_render()
        while state["capture"] is None:
            widget.queue_render()
            yield
        return state["capture"]

    background = [int(round(v * 255)) for v in core.bckgrnd_color]
    coverage = {}
    for name in REPRESENTATIONS:
        activate_only(name)
        shot = yield from capture(name)
        mask = foreground(shot["image"], background)
        save_image(name, shot["image"])
        coverage[name] = float(mask.mean())
        check("draw_%s" % name, shot["error"] == 0 and mask.sum() >= 20,
              {"coverage": coverage[name], "pixels": int(mask.sum()), "gl_error": shot["error"]})
    result["coverage"] = coverage

    # Impostor sprites: projected diameter, or the driver's point-size cap.
    activate_only("impostor")
    shot = yield from capture("impostor_size")
    mask = foreground(shot["image"], background)
    proj11 = float(np.asarray(core.glcamera.projection_matrix)[1][1])
    point_max = caps["GL_POINT_SIZE_RANGE"][1]
    sizes = {}
    for name in ISOLATED:
        atom = atoms[name]
        x, y, view_z = projected(core, molecule, atom)
        radius = float(molecule.cov_radii_array[atom.atom_id])
        expected = radius * proj11 * core.height / abs(view_z)
        blob = component_at(mask, x, y) if x is not None else np.zeros_like(mask)
        measured = float(2.0 * np.sqrt(blob.sum() / np.pi))
        target = min(expected, point_max)
        # +/-2 px covers sprite rasterization at the disc edge; 6% covers
        # the sprite's square-to-disc discard at small sizes.
        ok = abs(measured - target) <= max(2.0, 0.06 * target)
        sizes[name] = {"expected": round(expected, 2), "measured": round(measured, 2),
                       "clamped": expected > point_max}
        check("impostor_diameter_%s" % name, ok, sizes[name])
    result["impostor_sizes"] = sizes

    # 2x offscreen export against the on-screen frame.
    activate_only("spheres", "sticks")
    shot = yield from capture("export")
    image, export = shot["image"], shot["export"]
    height, width = image.shape[:2]
    ok_shape = export is not None and export.shape[:2] == (2 * height, 2 * width)
    detail = {"shape": None if export is None else list(export.shape),
              "framebuffer": [shot["framebuffer"], shot["framebuffer_after"]],
              "viewport": [shot["viewport"], shot["viewport_after"]],
              "gl_error": shot["export_error"]}
    if ok_shape:
        reduced = export[..., :3].astype(float).reshape(height, 2, width, 2, 3).mean((1, 3))
        difference = np.abs(reduced - image[..., :3])
        detail["mean_abs_diff"] = round(float(difference.mean()), 4)
        detail["frac_over_64"] = round(float((difference.max(-1) > 64).mean()), 6)
        # Same geometry at 4x the samples: only silhouette pixels may
        # differ. Mean <= 2/255 and <= 1% of pixels off by > 64/255.
        ok_shape = detail["mean_abs_diff"] <= 2.0 and detail["frac_over_64"] <= 0.01
    check("offscreen_export_2x", ok_shape and shot["framebuffer_after"] == shot["framebuffer"]
          and shot["viewport_after"] == shot["viewport"] and shot["export_error"] == 0, detail)

    def pick_all(label, names):
        outcomes = {}
        for name in names:
            atom = atoms[name]
            x, y, _ = projected(core, molecule, atom)
            hits = 0
            for dx, dy in PICK_OFFSETS:
                core.atom_picked = None
                pick(core, widget, x + dx, y + dy)
                while core.picking:
                    widget.queue_render()
                    yield
                hits += core.atom_picked is atom
            outcomes[name] = "%d/%d" % (hits, len(PICK_OFFSETS))
            check("%s_pick_%s" % (label, name), hits == len(PICK_OFFSETS), outcomes[name])
        return outcomes

    activate_only("spheres")
    result["pick_spheres"] = yield from pick_all("spheres", ("O", "H1", "N"))
    activate_only("impostor")
    result["pick_impostor"] = yield from pick_all("impostor", ("C", "N", "S"))

    # Resize to a different aspect ratio.
    widget.set_size_request(*RESIZED)
    state["window"].set_default_size(*RESIZED)
    for _ in range(40):
        if widget.get_width() == RESIZED[0] and widget.get_height() == RESIZED[1]:
            break
        yield
    activate_only("spheres")
    shot = yield from capture("resized")
    viewport = shot["viewport"]
    ratio = core.width / max(1.0, widget.get_width())
    aspect = float(core.glcamera.viewport_aspect_ratio)
    detail = {"logical": [widget.get_width(), widget.get_height()],
              "framebuffer": [float(core.width), float(core.height)],
              "viewport": viewport, "aspect": round(aspect, 4)}
    # The window manager decides the final size (Windows GTK 4.20+ keeps a
    # mapped toplevel's height), so require a real change and that the
    # viewport, framebuffer and projection follow whatever size resulted.
    check("resize_viewport",
          viewport[2:] == [int(core.width), int(core.height)]
          and abs(aspect - core.width / core.height) < 1e-3
          and abs(core.height / widget.get_height() - ratio) < 1e-3
          and (widget.get_width(), widget.get_height()) != WINDOW, detail)
    x, y, _ = projected(core, molecule, atoms["N"])
    ys, xs = np.nonzero(component_at(foreground(shot["image"], background), x, y))
    # np.ptp: ndarray.ptp() was removed in NumPy 2.
    blob_width, blob_height = int(np.ptp(xs)) + 1, int(np.ptp(ys)) + 1
    check("resize_sphere_aspect", 0.92 <= blob_width / blob_height <= 1.08,
          {"width": blob_width, "height": blob_height})
    result["pick_resized"] = yield from pick_all("resized", ("N",))

    state["window"].close()
    state["application"].quit()


def main():
    application = Gtk.Application(application_id="org.easyhybrid.tests.RenderValidation",
                                  flags=Gio.ApplicationFlags.NON_UNIQUE)
    state["application"] = application

    def activate(app):
        session = VismolSession("Gtk_4.0")
        # Render with EasyHybrid's shipped GL parameters (stick radius,
        # line/dot types, selection widths), not standalone VisMol's.
        # Built in memory only: the disk steps (temporary folder, per-user
        # config file, startup path) are skipped.
        from gui.config import VismolConfig as EasyHybridConfig

        class ShippedDefaults(EasyHybridConfig):
            def _check_tmp_folder(self):
                pass

            def _check_config_file(self):
                pass

            def _check_startup_path(self):
                pass

        session.vm_config.gl_parameters.update(ShippedDefaults().gl_parameters_default)
        session.vm_widget.set_size_request(*WINDOW)
        window = Gtk.ApplicationWindow(application=app)
        window.set_child(session.vm_widget)
        window.present()
        wrap_render(session.vm_widget.vm_glcore)
        state.update(session=session, window=window, steps=run_steps())

    def tick():
        steps = state.get("steps")
        if steps is None:
            return GLib.SOURCE_CONTINUE
        try:
            next(steps)
        except StopIteration:
            state["finished"] = True
            return GLib.SOURCE_REMOVE
        except Exception as error:  # report, then fail the run
            import traceback

            result["failures"].append("exception")
            result["exception"] = traceback.format_exc()
            application.quit()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def timeout():
        result["failures"].append("timeout")
        application.quit()
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(50, tick)
    # Intel macOS runners render ~2.5x slower than Apple Silicon ones.
    GLib.timeout_add_seconds(240, timeout)
    application.connect("activate", activate)
    application.hold()
    application.run(None)
    print("EASYHYBRID_RENDER_VALIDATION=" + json.dumps(result, sort_keys=True,
                                                       default=lambda value: value.tolist() if hasattr(value, "tolist") else str(value)), flush=True)
    return 0 if state.get("finished") and not result["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
