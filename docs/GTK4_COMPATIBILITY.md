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

Linux Wayland, Windows, and macOS remain **NOT TESTED**. A GitHub Actions
workflow now provisions GTK/PyGObject on native Linux, Windows, and Apple
Silicon macOS runners for every GTK minor series from 4.8 through 4.24. It
records the exact runtime, constructs a real GTK window and Gio menu actions,
and requires a real Gtk.GLArea OpenGL 3.3 context before running the suite.
The workflow has not yet been pushed or executed, so its platform results are
still **NOT TESTED**. The supplied private GitHub repository is configured as
`origin` and authentication succeeds; GitHub reports that repository is
currently empty. Native CI evidence will be added only after actual runs
finish. Linux X11 evidence cannot substitute for another OS or backend.

## Compatibility matrix

| GTK runtime / target | Result |
|---|---|
| GTK 4.8.2, Linux x86_64 / X11, Python 3.12.15, PyGObject 3.58.1, GLib 2.90.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 3.3.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL; orderly close **PASS**. Bare `Gtk.AboutDialog` has a reproducible GTK 4.8 upstream finalization critical. |
| GTK 4.8.2, Linux x86_64 / X11, Python 3.10.22, PyGObject 3.42.2, GLib 2.78.0 | Full suite: **54 passed, 5 skipped** (Cython graphics extensions built in a temporary copy). Native real-display UI/menu action smoke: **PASS**. Full app/pDynamo lifecycle **NOT TESTED** because available pDynamo binary extensions target Python 3.12. Bare `Gtk.AboutDialog` has the same GTK 4.8 upstream finalization critical. |
| GTK 4.14.5, Linux x86_64 / X11, Python 3.12.3, PyGObject 3.48.2, GLib 2.80.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL and `gl-prefer-gl`; orderly close **PASS**. GtkBuilder loads 53/53 resources without GTK criticals. |
| GTK 4.24.1, Linux x86_64 / X11, Python 3.12.15, PyGObject 3.58.1, GLib 2.90.0 | Full suite: **54 passed, 5 skipped**. Native real-display UI/menu action smoke: **PASS**. Full application lifecycle: **PASS**, fatal GTK criticals enabled, actual GL context OpenGL 4.6.0, NVIDIA GeForce RTX 4060 Ti; application-selected EGL and `gl-prefer-gl`; orderly close **PASS**. GtkBuilder loads 53/53 resources without GTK criticals; GTK emits a nonfatal missing-ibus-module warning in this shell. |
| GTK 4.8.2, Xvfb default renderer | **EGL WARNING REPRODUCED**: Mesa reports `DRI3 error: Could not get DRI3 device`; this Xvfb server does not provide a DRI3 device. Mesa EGL and DRI packages were already installed. Re-running with `LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe` created the real GL context and emitted no EGL warning. This validates the virtual-display software path only; hardware acceleration and a native desktop display are **NOT TESTED**. For widget-only smoke tests, `GSK_RENDERER=cairo` also avoids the GL probe, but it must not be used for GL tests. |
| GTK 4.8 / 4.10 | Linux x86_64 and macOS arm64 GTK smoke jobs passed for available conda artifacts; GTK 4.8/4.10 Windows jobs are still running in workflow `39063905270`. macOS arm64 4.8/4.10 are provider-excluded and **NOT TESTED**. |
| GTK 4.12, 4.14, 4.20, 4.22, 4.24 | Native GTK window/Gio action/GLArea smoke jobs passed on Linux x86_64, Windows x86_64, and macOS arm64 in workflow `39063905270`. The run remains in progress pending GTK 4.8/4.10 Windows. |
| GTK 4.16 and 4.18 | **NOT TESTED** on every OS in the current conda matrix because conda-forge publishes no artifacts for these versions. Linux distro packages exist; add a separate pinned-provider job. Windows/macOS alternative providers remain to be investigated. |
| Linux Wayland | **NOT TESTED**. |
| Windows native GTK4 | **NOT TESTED**. |
| macOS arm64/x86_64 native GTK4 | **NOT TESTED**. |

## Native platform CI (2026-10-17)

`.github/workflows/native-gtk-matrix.yml` currently defines 19 conda-provisioned
native runner combinations after excluding unavailable artifact/platform pairs.
Linux uses Xvfb and llvmpipe; Windows x86_64 and Apple Silicon macOS run the
same UI/GL checks on native runners. Workflow `39063905270` has 17 completed
successful jobs (Linux 4.8/4.10/4.12/4.14/4.20/4.22/4.24; Windows
4.12/4.14/4.20/4.22/4.24; macOS arm64 4.12/4.14/4.20/4.22/4.24), with
Windows 4.8 and 4.10 still in progress at last check. These are real GTK
window/Gio action/GLArea smoke results; only GTK 4.24 runs the full test suite
and graphics-extension build. Hardware GPU, physical trackpad, Retina, Linux
Wayland, excluded cells, and real Linux desktop behavior require separate
testing. The exclusions are package-provider gaps rather than support-policy
decisions; see the availability audit below.

## Verification requirements

For every claimed OS and GTK4 minor, record the exact GTK patch version,
GLib, PyGObject, Python, architecture, display backend, and OpenGL renderer
when applicable. Test real GtkBuilder/window lifecycle at the minimum and
latest verified runtime. A test not executed is **NOT TESTED**, not passed by
inference. Add new released GTK4 minors to the matrix before expanding the
compatibility claim. See `ROADMAP.md` for task ownership and acceptance gates.

## GTK binary availability audit (2026-10-17)

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
(`39065269579`). The 1.17 `libiconv` pin did not resolve the hang, and the
`libglib=2.82.2=h7025463_0` build did not resolve the DLL import error
(`39065624007`). A combined GLib/iconv pin also failed on Windows GTK 4.8
(`39065795981`).

Comparing the solver's package records identified a useful difference:
failing Windows GTK 4.8 and 4.10 cells resolved `gdk-pixbuf 2.42.10` with
`libglib 2.82.2`; passing Windows GTK 4.12 resolved `gdk-pixbuf 2.44.8` with
`libglib 2.90.1`, and its GdkPixbuf import and real GTK/GL smoke passed.
This points to the old GdkPixbuf build/dependency combination. The workflow
now pins only Windows GTK 4.8/4.10 to `gdk-pixbuf=2.44.8` and removes the
GLib/iconv pins and link-script bypass. This targeted combination has not yet
run successfully; the two cells remain **NOT TESTED** until the import and
native smoke pass. A separate instrumentation regression in run
`39065500734` queried a nonexistent `GdkPixbuf.MAJOR_VERSION`; it is fixed by
reporting the typelib namespace (`2.0`) and did not indicate GTK runtime
failures on Linux or macOS.
