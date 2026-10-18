# GTK4 compatibility policy and evidence

## Runtime contract

- The application runtime floor is **GTK 4.8**. GTK 4.6 and older are not
  supported. `gi.require_version("Gtk", "4.0")` selects the introspection
  namespace; it does not assert GTK runtime 4.0.
- The compatibility target must track the latest stable GTK4 release, but a
  support claim requires an explicit result for each supported minor and OS.
  The GTK documentation currently identifies GTK 4.24.1 as the library
  version ([GTK API reference](https://docs.gtk.org/gtk4/)). Native Linux
  X11 checks have run on GTK 4.8.2, 4.14.5, and 4.24.1. This samples the
  minimum, an intermediate release, and current stable; it does not validate
  every GTK 4.x minor series.
- Linux X11/Wayland, Windows, and macOS results are tracked separately. A
  successful unit test on Linux does not establish a native OS or runtime
  result. See the matrix below and `ROADMAP.md` EH4-501/502.

## Capability handling

`src/gtk4_compat.py` is the shared location for runtime API checks and
fallbacks. It checks callable APIs and exposed enum namespaces instead of
parsing patch-version strings.

| Feature | Shared handling | Runtime evidence |
|---|---|---|
| `Gtk.Picture.set_content_fit()` | `set_picture_contain()` uses `ContentFit.CONTAIN` when both API pieces are exposed; otherwise it uses the older shrink/aspect-ratio pair. The fallback is defensive for runtimes below the supported floor. | Capability branches unit-tested; real window/widget smoke passed on GTK 4.8.2, 4.14.5, and 4.24.1. |
| `Gtk.EventControllerScroll.get_unit()` | `supports_scroll_unit()`, `scroll_controller_flags()`, and `get_scroll_unit()` select discrete wheel events unless the caller handles surface deltas and the runtime exposes the unit API. | Both API shapes unit-tested; native widget smoke passed on GTK 4.8.2, 4.14.5, and 4.24.1. macOS trackpad is **NOT TESTED**. |
| `Gtk.GLArea.set_allowed_apis()` | `set_gl_area_allowed_apis()` selects desktop GL through `set_allowed_apis(Gdk.GLAPI.GL)` where exposed (GTK 4.12+) and uses `set_use_es(False)` on GTK 4.8. | Unit-tested both branches; full EasyHybrid native X11 GL context passed on GTK 4.8.2, 4.14.5, and 4.24.1. |
| `Gtk.Popover` pointer placement | `src/gui/gtk4_context_menu.py` anchors a `Gdk.Rectangle` through `set_pointing_to()` and opens it with `popup()`. It does not use GTK3's `popup_at_pointer()`. | Source inspection only; interactive popover UI on GTK 4.8/current stable is **NOT TESTED**. |

The capability tests exercise decision logic. They are not substitutes for
loading each GTK runtime or constructing UI widgets under that runtime.

## Icon-theme critical investigation (2026-10-17)

### Reproduction and root cause

The exact critical is:

```text
Gtk-CRITICAL: gtk_icon_theme_get_for_display: assertion 'GDK_IS_DISPLAY (display)' failed
Gtk-CRITICAL: gtk_icon_theme_add_resource_path: assertion 'GTK_IS_ICON_THEME (self)' failed
RuntimeError: Gtk couldn't be initialized. Use Gtk.init_check() if you want to handle this case.
```

It reproduces in a minimal standalone `Gtk.Application` with no EasyHybrid
imports, GtkBuilder files, icon assets, or graphics engine when the process
has no usable display (`Gdk.Display.get_default()` is `None`) and then runs
`Gtk.Application.run()`. It was reproduced with `G_DEBUG=fatal-criticals` on
Linux x86_64 for both GTK 4.8.2 and 4.14.5. The application-window traceback
ends in PyGObject's `Gtk.py` constructor (`Gtk.py:519` on GTK 4.8.2 and
`Gtk.py:508` on GTK 4.14.5). The underlying GTK call is earlier, during
application registration/startup, before EasyHybrid's activation handler.

GDB breakpoints at `gtk_icon_theme_get_for_display` showed these native call
paths:

- GTK 4.8.2: `gtk_icon_theme_get_for_display` → `gtk_application_startup` →
  GObject signal emission → `g_application_register` →
  `g_application_real_local_command_line` → `g_application_run` →
  PyGObject/libffi → Python.
- GTK 4.14.5: `gtk_icon_theme_get_for_display` → GTK internal startup frame →
  GObject signal emission → `g_application_register` → `g_application_run` →
  PyGObject/libffi → Python.

This identifies a missing GDK display in the test process, not a missing icon
or a renderer fault. With an available Xvfb display and the smoke harness
checking `Gdk.Display.get_default()` before constructing/registering the
application, a real `Gtk.ApplicationWindow` opens and closes under
`G_DEBUG=fatal-criticals` on both runtimes. The Xvfb theme is Adwaita. The
native Linux X11 display (`:0`) reports Mint-Y-Sand. `GTK_THEME` is unset in
both cases. When there is no display, no active GTK icon theme can be queried.

### Application resource audit

- No application source calls `Gtk.IconTheme`, adds icon-theme resource
  paths, or registers a `GResource`.
- GtkBuilder uses explicit file-backed `GtkImage.file` values; all referenced
  files exist. There are 51 files under `src/gui/icons/`.
- All 53 `.glade` resources load through the application's
  `src/gui/gtk4_builder.py:load_builder_file()` on GTK 4.8.2, 4.14.5, and
  4.24.1. With fatal criticals enabled on GTK 4.8.2, `about_dialog.glade`
  emits a GtkImage finalization critical. A minimal bare `Gtk.AboutDialog`
  reproduces it without EasyHybrid; GTK 4.14.5 and 4.24.1 load the same
  resource cleanly. Debian tracked this GTK 4.8/GLib behavior and notes that
  upstream fixed it in GTK 4.10 ([bug #1041599](https://bugs.debian.org/1041599)).
  GTK 4.14.5 `gtk4-builder-tool validate` also accepts all 53. The GTK 4.8.2
  standalone builder tool accepts 19 and reports 34 unresolved Glade signal
  handler names because it does not know the application's Python callbacks;
  the application's GTK4 loader removes those XML signal nodes, retains their
  metadata, and the real runtime loader successfully builds all 53 files.
  This validator result is distinct from a file-path or icon-theme failure.
- `tests/test_gtk_icon_theme_smoke.py` now rejects a GUI test with no GDK
  display before registering `Gtk.Application`, so an inaccessible runner
  cannot turn a test-setup error into GTK's misleading icon-theme critical.
  Its opt-in tests verify both successful real-display startup and the clear
  missing-display diagnostic.

No icon-theme workaround or renderer change was needed. The initial critical
was caused by running GTK application registration without an initialized
display in the isolated test environment. The guarded real-display smoke
passes on the native Linux X11 desktop (`:0`) under GTK 4.8.2, 4.14.5, and
4.24.1. This is an actual desktop session, distinct from Xvfb.

### Native Linux desktop graphics check (2026-10-17)

The display is X11 (`:0`) on Linux x86_64, with NVIDIA GeForce RTX 4060 Ti,
driver 595.99.02, and GLX OpenGL 4.6.0 available (`glxinfo -B`). A minimal
real Gtk.GLArea requesting OpenGL 3.3 core, with `G_DEBUG=fatal-criticals`,
reported:

- GTK 4.8.2: **PASS**, renderer `NVIDIA GeForce RTX 4060 Ti/PCIe/SSE2`.
- GTK 4.14.5 default X11 GL backend: **FAIL**,
  `gdk-gl-error-quark: Unable to create a GL context` (error code 0). The same
  occurred in a full EasyHybrid startup attempt. Setting
  `LIBGL_ALWAYS_SOFTWARE=1` and `GALLIUM_DRIVER=llvmpipe` did not help. With
  `GDK_DEBUG=gl-glx`, GTK's documented GLX selection diagnostic, the same
  Gtk.GLArea succeeds and reports the NVIDIA renderer. This flag is test-only
  evidence; no app-side Linux override has been added. Explicit
  `GDK_DEBUG=gl-egl` reproduces the context failure, isolating this result to
  GTK's EGL path on this specific GTK 4.14.5/X11/NVIDIA combination.

The lifecycle harness imports `easyhybrid` before PyGObject, leaving both
`GDK_DEBUG` and `PYOPENGL_PLATFORM` unset in the parent environment. The
application startup adapter configured EGL for PyOpenGL on Linux and added
`gl-prefer-gl` on GTK 4.14+; GTK 4.8 retained its desktop-GL default. Under
`G_DEBUG=fatal-criticals`, the complete EasyHybrid application opened and
closed cleanly and its actual `Gtk.GLArea` returned a current OpenGL context:

- GTK 4.8.2: OpenGL 3.3.0, NVIDIA GeForce RTX 4060 Ti; configured
  `PYOPENGL_PLATFORM=egl`, no GDK debug override.
- GTK 4.14.5: OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; configured
  `PYOPENGL_PLATFORM=egl`, `GDK_DEBUG=gl-prefer-gl`.
- GTK 4.24.1: OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; configured
  `PYOPENGL_PLATFORM=egl`, `GDK_DEBUG=gl-prefer-gl`.

GTK 4.8.2 full-app verification used Python 3.12.15 and a matching pDynamo3
build. A separate Python 3.10.22 GTK 4.8.2 environment ran the complete suite
and a native GTK widget smoke, but its pDynamo extension is Python 3.12-built;
full-app startup under that Python combination remains **NOT TESTED**. All
three full-app runs used the real native X11 display, NVIDIA hardware, and
fatal criticals; they were not Xvfb/software-renderer substitutions.

Native GitHub Actions jobs now provision GTK/PyGObject on Linux, Windows, and
Apple Silicon macOS runners where the selected conda-forge provider has
matching artifacts. They construct real GTK windows, activate Gio menu
actions, and require a real Gtk.GLArea OpenGL 3.3 context. Results are listed
below by exact runtime and platform. Linux X11 evidence does not substitute
for another OS or backend.

## Compatibility matrix

| GTK runtime / target | Result |
|---|---|
| GTK 4.8.2, Linux x86_64 / X11, Python 3.12.15, PyGObject 3.58.1, GLib 2.90.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 3.3.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL; orderly close **PASS**. Bare `Gtk.AboutDialog` has a reproducible GTK 4.8 upstream finalization critical. |
| GTK 4.8.2, Linux x86_64 / X11, Python 3.10.22, PyGObject 3.42.2, GLib 2.78.0 | Full suite: **54 passed, 5 skipped** (Cython graphics extensions built in a temporary copy). Native real-display UI/menu action smoke: **PASS**. Full app/pDynamo lifecycle **NOT TESTED** because available pDynamo binary extensions target Python 3.12. Bare `Gtk.AboutDialog` has the same GTK 4.8 upstream finalization critical. |
| GTK 4.14.5, Linux x86_64 / X11, Python 3.12.3, PyGObject 3.48.2, GLib 2.80.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL and `gl-prefer-gl`; orderly close **PASS**. GtkBuilder loads 53/53 resources without GTK criticals. |
| GTK 4.24.1, Linux x86_64 / X11, Python 3.12.15, PyGObject 3.58.1, GLib 2.90.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL and `gl-prefer-gl`; orderly close **PASS**. GtkBuilder loads 53/53 resources without GTK criticals; GTK emits a nonfatal missing-ibus-module warning in this shell. |
| GTK 4.8.2, Xvfb default renderer | **EGL WARNING REPRODUCED**: Mesa reports `DRI3 error: Could not get DRI3 device`; this Xvfb server does not provide a DRI3 device. Mesa EGL and DRI packages were already installed. Re-running with `LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe` created the real GL context and emitted no EGL warning. This validates the virtual-display software path only; hardware acceleration and a native desktop display are **NOT TESTED**. For widget-only smoke tests, `GSK_RENDERER=cairo` also avoids the GL probe, but it must not be used for GL tests. |
| GTK 4.8 through 4.24, Linux x86_64 / Windows x86_64 / macOS arm64 (+ macOS x86_64 for 4.8/4.10) | Native GTK window, Gio action, and real `Gtk.GLArea` render smoke: **PASS, 30/30 cells** in workflow `39071376507` at `38f2b6c`. Exact runtimes per cell are in [Full GTK4 minor matrix](#full-gtk4-minor-matrix-2026-10-17). Earlier Windows GTK 4.8/4.10 GL failures were fixed by the WGL pixel-format workaround; see the investigation below. |
| Linux Wayland | **NOT TESTED**. |
| Windows GTK4 native runner smoke | **PASS** for GTK 4.8–4.24 on hosted Windows Server 2022 with pinned Mesa 26.2.4 llvmpipe. Physical Windows GPUs remain **NOT TESTED**. |
| macOS arm64 native GTK4 runner smoke | **PASS** for GTK 4.8–4.24 (4.8/4.10/4.16/4.18 built from GNOME source). Physical GPU behavior beyond the hosted runner, Retina, and trackpad remain **NOT TESTED**. |
| macOS x86_64 native GTK4 | **PASS** for GTK 4.8.2 and 4.10.1 (conda-forge `osx-64`, `macos-15-intel`). Other minors on Intel macOS are **NOT TESTED**. |

## Native platform CI (2026-10-17)

`.github/workflows/native-gtk-matrix.yml` covers every released GTK4 minor
from 4.8 to 4.24 on Linux x86_64, Windows x86_64 and Apple Silicon macOS, plus
Intel macOS for GTK 4.8/4.10 (30 cells). conda-forge provides most cells.
Where it has no build, the workflow uses another native provider (see the
matrix below). Linux uses Xvfb and llvmpipe; Windows uses a pinned Mesa
26.2.4 llvmpipe WGL runtime; macOS uses the runner's native Apple OpenGL.
Every job fails if the loaded GTK minor differs from the requested one.
Only GTK 4.24 runs the full test suite and graphics-extension build.
Hardware GPUs, physical trackpad, Retina, Linux Wayland and real Linux
desktop behavior require separate testing.

## Full GTK4 minor matrix (2026-10-17)

Workflow `39071376507`, commit `38f2b6c`: **30/30 PASS**. Each cell opened a
real GTK4 window, dispatched Gio menu actions, rendered a `Gtk.GLArea` with
an OpenGL 3.3+ context, and closed with `G_DEBUG=fatal-criticals`.

| GTK | Linux x86_64 | Windows x86_64 | macOS arm64 | macOS x86_64 |
|---|---|---|---|---|
| 4.8 | 4.8.2 conda-forge | 4.8.2 conda-forge | 4.8.3 GNOME source | 4.8.2 conda-forge |
| 4.10 | 4.10.1 conda-forge | 4.10.1 conda-forge | 4.10.5 GNOME source | 4.10.1 conda-forge |
| 4.12 | 4.12.1 conda-forge | 4.12.1 conda-forge | 4.12.1 conda-forge | NOT TESTED |
| 4.14 | 4.14.1 conda-forge | 4.14.1 conda-forge | 4.14.1 conda-forge | NOT TESTED |
| 4.16 | 4.16.3 Ubuntu 24.10; 4.16.13 Fedora 41 | 4.16.13 MSYS2 UCRT64 source | 4.16.13 GNOME source | NOT TESTED |
| 4.18 | 4.18.6 Debian 13 | 4.18.6 MSYS2 UCRT64 source | 4.18.6 GNOME source | NOT TESTED |
| 4.20 | 4.20.3 conda-forge | 4.20.3 conda-forge | 4.20.3 conda-forge | NOT TESTED |
| 4.22 | 4.22.5 conda-forge | 4.22.5 conda-forge | 4.22.5 conda-forge | NOT TESTED |
| 4.24 | 4.24.1 conda-forge | 4.24.1 conda-forge | 4.24.1 conda-forge | NOT TESTED |

Runtimes: conda-forge cells use Python 3.12.15 with PyGObject 3.46.0 (GTK
4.8), 3.48.1/3.50.0 (GTK 4.10) or 3.58.1 and GLib 2.78–2.90. Ubuntu: Python
3.12.7, PyGObject 3.48.2, GLib 2.82.1. Fedora: Python 3.13.9, PyGObject
3.48.2, GLib 2.82.5. Debian: Python 3.13.5, PyGObject 3.50.0, GLib 2.84.4.
MSYS2: Python 3.14.8, PyGObject 3.58.1, GLib 2.90.1. macOS source builds:
Python 3.12.15, PyGObject 3.58.1, GLib 2.90.0. Source builds use
SHA-256-pinned `download.gnome.org` tarballs. All Linux and Windows results
use software OpenGL; all macOS results use hosted-runner Apple OpenGL.

### GTK defects found and handled

| GTK range / platform | Defect (upstream) | EasyHybrid handling |
|---|---|---|
| 4.8–4.11, Windows | Bootstrap HDC uses a GDI pixel format but surfaces use an ARB format; `wglMakeCurrent` fails with error 2000 when they differ. | `src/os_integration/win32_wgl.py` presets GDK's GDI format on the GLArea window; `GSK_RENDERER=cairo` default. |
| 4.8–4.11, macOS | Only exact GL 3.2/4.1 requests map to Core profiles; 3.3 yields a Legacy context that cannot share with GDK's Core context ("invalid share context"). | `gl_area_required_version()` requests 3.2 there; macOS returns its highest Core version (4.1). The smoke asserts the real context is ≥ 3.3. |
| 4.16, all platforms | With the previous `gl` renderer, closing a window with a `Gtk.GLArea` aborts: `gsk_renderer_unrealize` drops the GLArea texture and `release_gl_texture` calls `glDeleteSync` with no current context (debug-symbol backtrace, Fedora 4.16.13). | `GSK_RENDERER=ngl` default on GTK 4.16; per-renderer runs showed `gl` aborts and `ngl`/`cairo` pass. |

User-set `GSK_RENDERER` values are always kept.

## GTK4 widget-pattern portability (EH4-103, 2026-10-18)

Probed locally on every conda-forge GTK minor with a real display (GTK
4.8.2/PyGObject 3.46.0, 4.10.1/3.50.0, 4.12.1, 4.14.1, 4.20.3, 4.22.5,
4.24.1/3.58.1, plus 4.14.5/3.48.2 and 4.8.2/3.42.2):

| Finding | Range | Handling |
|---|---|---|
| `Gtk.PropertyExpression.new` raises `TypeError: No means to translate argument or return value for 'GtkPropertyExpression'` | GTK 4.8 with every PyGObject conda pairs with it (3.42.2, 3.44.1, 3.46.0); works on 4.10+ | Removed all 43 uses. `Gtk.StringList` dropdowns need no expression (GTK displays `Gtk.StringObject` itself on every minor). Custom rows use `gtk4_compat.bind_dropdown_label_property` (a list-item factory). ColumnView sorting uses `gtk4_compat.property_sorter` (`Gtk.CustomSorter`). |
| Empty `Gtk.DropDown` selection | Kept on 4.8–4.14; GTK 4.20+ auto-selects item 0 | Code never relies on an empty selection; the OPLS filter tracks its pending default in Python. |
| `Gtk.ComboBoxText` | Deprecated since 4.10 | Five uses moved to `gui.choice_dropdown` value-keyed dropdowns with identical IDs (`PRP/FR/HS`, `BOFILL/BFGS/MS/POWELL`, xTB `2/1`, `none/water/methanol`, OPLS filters). |
| `popup_at_widget` (GTK3 `Gtk.Menu`) | Absent in all GTK4 | PES Actions button raised `AttributeError`; now `ContextMenu.present_at_widget` via `Gtk.Widget.compute_bounds`. |

`tests/test_gtk4_widget_patterns.py` checks these with real widgets and a
static guard against reintroducing the patterns; CI runs it in every matrix
cell with `EASYHYBRID_REQUIRE_GTK_DISPLAY=1` so it cannot silently skip.
Message dialogs (2026-10-18): `Gtk.MessageDialog` is deprecated since GTK
4.10 and `Gtk.AlertDialog`/`Gtk.FileDialog` are absent on GTK 4.8 (probed on
every conda minor). `src/gui/message_dialogs.py` builds message, question and
multi-button dialogs from a plain `Gtk.Window` using only GTK 4.0 widgets,
so one code path serves GTK 4.8–4.24. All 20 live `Gtk.MessageDialog` uses
and `SimpleDialog` (81 call sites) now use it. The removed
`SimpleDialog.finished()` called `Gdk.cairo_surface_create_from_pixbuf`,
which no GTK4 release provides. Dialog tests passed 10 consecutive runs on
each local minor after replacing fixed sleeps with condition waits.
Native matrix run `39083365433` (commit `07585a1`): **14/14 passed in all 30 cells**.

Custom dialogs (2026-10-18): `Gtk.Dialog` is deprecated since GTK 4.10.
`src/gui/response_dialog.py` provides `ResponseDialog`, a `Gtk.Window` with
the `Gtk.Dialog` API EasyHybrid uses (content area, response buttons,
default response, `response` signal; closing emits `DELETE_EVENT`). All 10
Python `Gtk.Dialog` uses (incl. two subclasses and the VisMol preset dialog)
now use it. Five Builder `GtkDialog`s, used only as windows, became
`GtkWindow`; their action row, which `GtkDialog` placed at the bottom, was
moved to the end of the content box so the layout is unchanged.
Native matrix run `39084141877` (commit `cf8d16b`): **22/22 passed in all 30 cells**.

GTK 4.8 upstream defect: freeing any `Gtk.DropDown` emits
`GLib-GObject-CRITICAL ... GtkImage ... during instance finalization` (a bare
GTK script reproduces it on 4.8.2; clean on 4.10.1). It is the same
finalization bug recorded above for `Gtk.AboutDialog`. Widget tests do not use
`G_DEBUG=fatal-criticals` on GTK 4.8.

Correction (2026-10-18, file-chooser step): this critical was **not**
harmless. PyGObject turns `GLib-GObject` criticals into Python warnings, so
Python code runs inside the GLib log handler. If Python's cyclic garbage
collector runs there and frees another widget holding a `GtkImage`, the
nested critical is a *recursive* log message, which GLib always aborts on.
Reproduced deterministically on GTK 4.8.2 with PyGObject 3.42.2 and 3.46.0
(a file chooser held in a Python reference cycle aborts within 1–4 dialogs;
`faulthandler` shows `Garbage-collecting` inside `warnings._formatwarnmsg`).
GTK 4.10 fixed the critical. Fix: on GTK < 4.10 only,
`gtk_startup.install_native_glib_log_handler()` (run by
`configure_startup_environment`) installs GLib's own C
`g_log_default_handler` for `GLib-GObject`, so these messages print from C
and no Python runs inside the handler. The same reproducer survives with it
(test `test_widget_cycles_freed_by_garbage_collection_do_not_abort`, run on
every minor). `G_DEBUG=fatal-criticals` still applies.

### File, folder and colour choosers

`Gtk.FileChooserDialog`/`Gtk.ColorChooserDialog` are deprecated since GTK
4.10 and `Gtk.FileDialog`/`Gtk.ColorDialog` do not exist on GTK 4.8.
`src/gui/file_dialogs.py` (`choose_file`, `choose_color`, `file_filter`)
detects the new API by feature and otherwise uses the old dialogs, which are
not deprecated on 4.8. Both paths give the same callback result (local path,
list of paths for multi-selection, `Gdk.RGBA`, or `None`/`[]` on cancel). All
call sites (about 20, including VisMol's open/export dialogs) use it. GTK4
always confirms overwrites, so the GTK3-only
`set_do_overwrite_confirmation` calls (an `AttributeError` on every GTK4,
which broke four save dialogs) are gone. The selection-colour menu also no
longer calls a nonexistent `SimpleDialog.destroy()`, which had stopped the
"make permanent?" question from appearing.

Each real file chooser is tested where the app uses it: the GTK 4.8
`Gtk.FileChooserDialog` path on GTK 4.8 (cancel for every mode, selected
real paths for open/save/folder), and `Gtk.FileDialog` on GTK 4.10+ (cancel
for every mode; the dialog carries the requested title, accept label,
folder, name and filters). On Windows/macOS 4.10+ that is the native
dialog; on Linux runners without a portal it is GTK's own handling. The
colour paths (both) run on every minor. Adapter logic, the schema guard and
the cycle regression (GTK < 4.10) also have tests.

Upstream defects in the deprecated `Gtk.FileChooserDialog` on GTK 4.10+,
which the app does not use there: destroying it while its path bar is
still looking up a folder crashes in `gtk_path_bar_set_file_finish` (gdb
backtrace, GTK 4.24.1 Linux; also crashed macOS arm64 4.14/4.22 and MSYS2
Windows 4.16/4.18 runners); a Windows 4.12 runner crashed in `present()`;
and on a loaded macOS 4.24 runner it ignored a programmatic accept. Run
`39137929806` exposed these when the GTK 4.8 path was forced on 4.10+.
The adapter still hides the chooser on response and destroys it five
seconds later, which also protects GTK 4.8 on slow machines (macOS x86_64
GTK 4.8/4.10 runners crashed the same way before that change).

Native matrix run `39140683707` (commit `01ea9a5`): **30/30 cells PASS** — GTK 4.8: 36 passed, 3 skipped (Linux, Windows, macOS arm64/x86_64); GTK 4.10–4.24: 33 passed, 6 skipped. One intermittent access violation on MSYS2 Windows GTK 4.18.6 in run `39139961309` (after a native `Gtk.FileDialog` cancel) did not recur; a gdb backtrace step captures it if it does.

### Colour buttons

`Gtk.ColorButton` is deprecated since GTK 4.10 and `Gtk.ColorDialogButton`
does not exist on GTK 4.8. `src/gui/color_button.py` provides `ColorButton`
(GType `EasyHybridColorButton`, used directly by Builder files): a
`Gtk.Button` with a colour swatch keeping the `rgba`, `use-alpha` and
`title` properties, `get_rgba`/`set_rgba`, `new_with_rgba` and the
`color-set` signal (emitted only for a user's choice). It opens
`gui.file_dialogs.choose_color`, so it uses `Gtk.ColorDialog` on 4.10+.
All 26 uses moved (21 in 8 UI definitions, 5 in Python); Builder's
string-to-`Gdk.RGBA` conversion for the Python property was verified on
GTK 4.8, 4.10 and 4.24. PyGObject note: `Gdk.RGBA` is iterable only from
PyGObject 3.58, so `list(rgba)` raised `TypeError` in 17 setup-preference
handlers on PyGObject 3.42–3.50 (typical with GTK 4.8–4.14); they now use
`gtk4_compat.rgba_components`, and the guard rejects the old pattern.

### Deprecation sweep

Remaining APIs deprecated inside the supported range were replaced with
ones present since GTK 4.0: `widget.show()`/`hide()` (deprecated 4.10; 361
calls, token-based codemod skipping comments, strings and matplotlib's
`plt.show()`) became `set_visible()`; `get_allocated_width/height()`
(deprecated 4.12) became `get_width()/get_height()` (identical values with
margins, padding and border on GTK 4.8, 4.12 and 4.24); pixbuf image calls
(`Gtk.Image.set_from_pixbuf`/`new_from_pixbuf`, `Gtk.Picture.set_pixbuf`,
deprecated 4.12, and `Gdk.Texture.new_for_pixbuf`, deprecated 4.20) use
`gtk4_compat.texture_from_pixbuf` (a `Gdk.MemoryTexture`); the main window's
`GtkStatusbar` (deprecated 4.10) is `gui.status_label.StatusLabel`
(`EasyHybridStatusLabel`, same push/pop message stack). Kept on purpose:
`Gtk.StyleContext.add_provider_for_display` (not deprecated), the
`set_keep_aspect_ratio` fallback in `gtk4_compat.set_picture_contain` (only
reachable below the GTK 4.8 floor), and the GTK 4.8-only dialogs inside
`gui.file_dialogs`. The static guard rejects every replaced pattern.

Native matrix run `39082144669` (commit `9373956`): **10/10 passed in all 30 cells** — every GTK4 minor 4.8–4.24 on Linux, Windows and macOS arm64, plus GTK 4.8/4.10 on macOS x86_64.

## Verification requirements

For every claimed OS and GTK4 minor, record the exact GTK patch version,
GLib, PyGObject, Python, architecture, display backend, and OpenGL renderer
when applicable. Test real GtkBuilder/window lifecycle at the minimum and
latest verified runtime. A test not executed is **NOT TESTED**, not passed by
inference. Add new released GTK4 minors to the matrix before expanding the
compatibility claim. See `ROADMAP.md` for task ownership and acceptance gates.

## GTK binary availability audit (2026-10-17)

Superseded for coverage: the gaps below are now filled by the distro, MSYS2
source, GNOME source and Intel macOS jobs in the [full
matrix](#full-gtk4-minor-matrix-2026-10-17). The conda-forge findings
themselves remain accurate.

The setup failures were checked against conda-forge's package metadata API,
including each artifact's platform subdirectory:

| Failed runner cell | Exact conda-forge artifact finding | Interpretation |
|---|---|---|
| Linux x86_64 / GTK 4.16 and 4.18 | Neither release appears in the package version list; no Linux artifacts exist. | The solver failure is real for this provider. GTK 4.16.x and 4.18.x Linux distribution packages do exist, so these GTK series must not be dropped from Linux testing. Provision them through a pinned system-package or source-build job. |
| Windows x86_64 / GTK 4.16 and 4.18 | Neither release appears in the package version list; no Windows artifacts exist. | These versions cannot be provisioned by this workflow's current conda-forge method. Windows GTK support is not disproved; exact native tests remain **NOT TESTED** pending another provider. |
| macOS arm64 / GTK 4.8 and 4.10 | GTK 4.8.2 and 4.10.1 exist for `osx-64`; no `osx-arm64` artifacts exist. | The exact packages are unavailable for this Apple Silicon runner architecture through conda-forge. Intel macOS artifacts do not count as arm64 test evidence. |
| macOS arm64 / GTK 4.16 and 4.18 | Neither release appears in the package version list; no macOS artifacts exist. | These versions cannot be provisioned by this workflow's current provider. macOS support is not disproved; exact native tests remain **NOT TESTED** pending another provider. |

Thus `.github/workflows/native-gtk-matrix.yml` excludes unavailable
conda-forge artifacts, not GTK/OS combinations from the product support
contract. The Linux 4.16/4.18 omissions specifically need an alternate
provider. GTK's upstream [source archive](https://download.gnome.org/sources/gtk/)
and the [Ubuntu GTK package archive](https://mirrors.edge.kernel.org/ubuntu/pool/main/g/gtk4/)
show released source and Linux distribution builds. No Windows/macOS source
build is claimed or inferred here.

### Windows GTK 4.8/4.10 GdkPixbuf runtime

The initial GTK 4.8/4.10 Windows setup stalled in the `gdk-pixbuf` post-link
loader-cache script (`39063905270`). Skipping link scripts and running the
cache helper directly let setup finish, but PyGObject then failed importing
GdkPixbuf with `gdk_pixbuf-2.0-0.dll: The specified procedure could not be
found`, followed by `AssertionError` in `gi.overrides.GdkPixbuf`
(`39065269579`). The 1.17 `libiconv` pin did not resolve the hang, and
`libglib=2.82.2=h7025463_0`, alone or combined with that iconv pin, did not
resolve the import (`39065624007`, `39065795981`).

Package comparison showed Windows GTK 4.8/4.10 are constrained to GdkPixbuf
2.42.10 because their `jpeg`/`libtiff` ABI requirements cannot resolve with
the newer 2.44.8 build used by passing GTK 4.12. The older GdkPixbuf permits
GLib 2.78.4 but the environment had selected GLib 2.82.2. The upstream
[conda-forge GLib issue](https://github.com/conda-forge/glib-feedstock/issues/162)
identifies the `libglib 2.78.4 h55e6270_1` build as faulty and recommends
the `_0` build. CI pins the matching good pair
`libglib=2.78.4=h16e383f_0` and
`glib-tools=2.78.4=h12be248_0`, plus `libiconv=1.17`, only on Windows GTK
4.8/4.10; it keeps the link-script bypass and explicit cache generation for
those cells. Both cells now import GdkPixbuf successfully. A separate
instrumentation regression in run `39065500734` queried nonexistent
`GdkPixbuf.MAJOR_VERSION`; it is fixed by reporting the typelib namespace
(`2.0`) and did not indicate GTK runtime failures on Linux or macOS.

### Windows GTK 4.8/4.10 WGL smoke failure

The targeted CI probe uses the same pinned Mesa 26.2.4 build as the GTK smoke
and independently creates a basic native WGL context with Tk's window. The
latest GTK 4.10.1 log reports OpenGL 4.6 Compatibility Profile and
`llvmpipe (LLVM 23.1.2, 256 bits)`. GTK 4.10.1, GdkPixbuf imports, and
app-local Mesa DLL loads also pass. In the same job, EasyHybrid's minimal GTK smoke fails with
`Gsk-Message: Failed to realize renderer ... No GL implementation is available`
and Gtk.GLArea reports the same GDK error. The basic context proves that Mesa
WGL can create a compatibility-profile context; it does not exercise GTK's
dummy-window HDC or pixel-format setup. GTK 4.10's upstream
[`gdk_win32_display_init_wgl()`](https://github.com/GNOME/gtk/blob/4.10.0/gdk/win32/gdkglcontext-win32-wgl.c#L251-L296)
uses the generic `No GL implementation is available` message if its dummy
pixel-format/context setup returns no format or the initial `wglMakeCurrent`
fails. A separate branch uses the same message if the resulting GL version
is below 2 and `GL_ARB_shader_objects` is absent. The current CI output does
not distinguish those branches. The failure occurs before EasyHybrid's
scientific graphics code runs; the exact failing GDK WGL operation has not
been captured.

An upstream source comparison supports this classification. GTK 4.8's
`gdk_win32_display_init_gl()` obtains the bootstrap HDC from
`GetDC(display_win32->hwnd)` in
[`gdkdisplay-win32.c` at GTK 4.8](https://github.com/GNOME/gtk/blob/4.8.0/gdk/win32/gdkdisplay-win32.c).
GTK 4.12 creates a dedicated hidden `GdkGLDummyWindow` with `CS_OWNDC` and
uses its own HDC in
[`gdkglcontext-win32-wgl.c` at GTK 4.12](https://github.com/GNOME/gtk/blob/4.12.0/gdk/win32/gdkglcontext-win32-wgl.c).
GTK 4.12.1 passes the Windows smoke with the same Mesa 26.2.4 llvmpipe
renderer (OpenGL 4.6). This evidence is consistent with an older GTK Win32
bootstrap incompatibility in this hosted software-WGL setup, but does not
identify the precise failed WGL call or prove that all physical Windows
drivers fail on GTK 4.8/4.10. Native hardware Windows results remain
**NOT TESTED**; the hosted GTK 4.8/4.10 GL smoke result is **FAIL**. The
unsupported `GDK_DEBUG=opengl` diagnostic was removed because
the conda GTK release binaries were built without `G_ENABLE_DEBUG`.

Trace result at `1529bf5` (GTK 4.10.1, Windows Server 2022 x86_64, Mesa
26.2.4 llvmpipe; run `39067856957`): retaining the Mesa
DLL fixed the earlier lost-format symptom. GDK WGL init now succeeds and
creates a 4.6 core shared context. The new failure is `wglMakeCurrent`
returning Windows error 2000 (`ERROR_INVALID_PIXEL_FORMAT`). GTK sets the
display-HWND bootstrap HDC through legacy `ChoosePixelFormat` (format 75)
and the surface HDC through `wglChoosePixelFormatARB` (format 1). A surface
context created for format 1 is then made current surfaceless on the
bootstrap HDC (format 75), which WGL rejects. The GLArea gets no context and
reports `render signal not emitted`. Upstream source at GTK 4.8.3 and 4.10.1
shows the same design: `GetDC(display_win32->hwnd)` serves as the dummy HDC,
and surfaceless `make_current` binds to it. GTK 4.12 discards the initial
dummy and sets the ARB-chosen format on the display HDC
(`set_wgl_pixformat_for_hdc`), which explains why 4.12+ passes. This is a
GTK 4.8/4.10 Win32 defect that is exposed when GDI and ARB choose different
format indices, as Mesa does. It is not an EasyHybrid defect. The GTK 4.8.2 job in
the same run traced the identical sequence (bootstrap HDC format 75,
surface format 1, `wglMakeCurrent` error 2000). Whether physical Windows
drivers pick matching indices is **NOT TESTED**. No supported
application-side workaround exists, because both pixel formats are chosen
inside GDK. Hosted Windows GTK 4.8/4.10 GL remains **FAIL**. The decision
on whether to declare GTK 4.12 as the Windows floor is left to the user.

Fix (branch `fix/win32-legacy-wgl-pixel-format`, merged to `main`):
`src/os_integration/win32_wgl.py` applies only on Windows with GTK earlier
than 4.12. Startup defaults `GSK_RENDERER=cairo`, so GSK does not claim the
toplevel with the ARB-chosen format. A `Gtk.GLArea` `create-context`
handler sets GDK's own legacy GDI pixel format on the window and then defers
to GTK's default context creation, so both HDCs share one format. The
helper keeps `opengl32` loaded for the process lifetime. GTK version lookup
now also finds the Windows `gtk-4-1.dll`. As a result, Windows GTK 4.14+ now
receives `GDK_DEBUG=gl-prefer-gl`, as the startup policy already intended.
Run `39068617718` passed the real GLArea render on both cells. Windows GTK
4.8.2 and GTK 4.10.1 each produced OpenGL 4.6 Core Profile with Mesa 26.2.4
llvmpipe; output showed `legacy-wgl=True GSK_RENDERER=cairo`. The CI
investigation scaffolding was then removed: the Frida trace, the DLL
diagnosis step, and `EASYHYBRID_TEST_OPENGL_DLL`. Clean full-matrix run `39068863706` (push to `main` at `308c2d8`): **PASS, 19/19 cells**: Linux GTK 4.8/4.10/4.12/4.14/4.20/4.22/4.24; Windows GTK 4.8/4.10/4.12/4.14/4.20/4.22/4.24; macOS arm64 GTK 4.12/4.14/4.20/4.22/4.24. GTK 4.16/4.18 on all OSes and macOS arm64 GTK 4.8/4.10 remain **NOT TESTED** (no conda-forge artifacts). Physical Windows GPUs remain **NOT TESTED**.
Unit coverage is in `tests/test_win32_wgl.py`, using a fake Win32 API; it
does not prove native behavior.
