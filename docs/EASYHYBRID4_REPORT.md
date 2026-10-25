# EasyHybrid4 Development and Compatibility Report

**Report date:** 2026-10-25

**Project persistence (partial, EH4-404):** EasyHybrid `.easy` payloads now
write format version 1; payloads without a version key are treated as legacy
version 0. The loader validates the deserialized mapping, systems list and
system entries, and rejects unsupported future versions before restarting
the active application. Linux Xvfb/pDynamo tests pass 7 cases for legacy and
current payloads, malformed schemas and truncated pickle files. This does not
yet verify a full UI session round-trip, older historical project fixtures,
autosave recovery or Windows/macOS/other GTK runtimes. Python pickle files
remain trusted local project data; schema checks do not make untrusted pickle
loading safe.

**Simulation worker errors (partial, EH4-405):** an unsupported simulation
type previously put `RUNNING` on the multiprocessing queue and returned without
an error, leaving the process-manager row active indefinitely. The child now
reports it through the normal `ERROR` message path. Exception details are
serialized as strings so exceptions that cannot be pickled do not silently
break queue delivery. A direct worker queue regression passes locally under
Linux Xvfb with Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0.
Cancellation, progress reporting, GUI responsiveness, and unexpected worker
crash detection remain unverified.

**EH4-303 reproducible installation: PASS for clean-runner provisioning (2026-10-25).** PR #19 matrix run [40196735291](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40196735291) passed 31/31 jobs. I audited all 30 runtime artifacts: exact OS/architecture, Python, PyGObject, GTK patch, GLib and renderer are recorded; each has five full-app native pointer/pick/render/close cycles, five molecular scene cycles, render validation at scales 1 and 2, and 31 scientific tests passed. The workflow created clean Linux, Windows and macOS environments; GTK 4.16/4.18 use Linux distro packages, Windows MSYS2 builds and macOS source builds. README now covers the Linux x86_64 exact lock, Windows PowerShell and macOS arm64 GTK 4.24.1 baselines, Micromamba shell hooks, compilers and separate pDynamo3 setup. **NOT TESTED:** independent manual Windows/macOS installs following README and complete transitive locks for those platforms. EH4-304 separately tracks distribution packages.

**Current roadmap pointer:** EH4-301 and EH4-302 are complete for their
hosted-runner acceptance. PR #17 (window-minimum fix) merged as 770e666 after
native matrix 40161896666 passed 31/31. Codex audited all 30 artifacts. EH4-602 partial merged in PR #18 (`bd6e846`), and EH4-303 passed in PR #19 (matrix `40196735291`, 31/31); Codex next handles EH4-304. Claude is handling EH4-505. EH4-000/200
provenance and licensing, EH4-203 physical trackpad
review, and EH4-506 branch protection remain open pending upstream or user
evidence.

**Latest native GTK matrix (2026-10-25): PASS, 30/30 cells.** PR #17 run
[40161896666](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40161896666)
passed all 30 runtime cells (31/31 jobs including the plan). All 30 uploaded
runtime artifacts were inspected for exact OS/architecture, Python,
PyGObject, GTK patch, GLib and renderer. Each records five full-app display,
native pointer/pick/render/close cycles and five production scene cycles.
Across 150 display records, all report fits_monitor=True; hosted scale is 1.
A separate local Linux GTK 4.8.2/4.24.1 scale-2 check fits a 912x444 window
on a 960x540 logical monitor. Hosted Windows GTK 4.20+ and macOS ignore
GDK_SCALE; physical Retina/HiDPI, multi-monitor, Wayland and live display
scale changes remain NOT TESTED. Three Linux GTK 4.10/4.12/4.14 artifacts
contain a g_error_free chooser-test warning, but their test suites passed
with no failures.

**EH4-405 batch PR #6 matrix status:** corrected head `341a7cc`, merged as
`b676d00`, passed full matrix
[`40102390980`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40102390980)
**30/30**. All 30 runtime artifacts confirm five full-app native pick,
`.easy` session save/reopen, render and clean-close cycles and five production
scene cycles; widget-pattern and renderer validation also passed. The GTK
4.24 full regression suite passed 165 tests (16 skipped) on Linux, 163 (18
skipped) on Windows, and 163 (18 skipped) on macOS arm64. Exact versions and
platform coverage are in [`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md).
Earlier fail-fast runs `40052058048` and `40101418631` exposed two harness
defects: an oversized Windows inline command (`WinError 206`) and then a
working-directory import loss from direct temp-script execution. The final
short `runpy` bootstrap fixes both; focused regression: **1 passed**. The
failed runs are not acceptance evidence.

**EH4-400–405 batch full-matrix status (2026-10-24): PASS, 30/30 cells.** Run
[`40102390980`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40102390980)
passed the Linux x86_64, Windows x86_64 and macOS arm64 GTK 4.8–4.24 cells,
plus Intel macOS GTK 4.8/4.10. Runtime artifacts confirm exact GTK, GLib,
Python, PyGObject, OS/architecture and renderer versions. Each cell passed
five full `EasyHybridApplication`/`MainWindow` cycles with generated pDynamo3
fixture loading, native OS pointer input (Linux XTest, Windows Win32, macOS
Quartz), oxygen `O:0` picked, render and clean close. Each also passed five
production menu/VisMol scene cycles, the complete regression suite and
render validation. The matrix uses hosted software renderers. Cross-process
Windows/macOS clipboard, physical GPUs, Wayland, Retina/HiDPI and trackpad
behavior remain separately **NOT TESTED**. See the matrix evidence entry in
[`ROADMAP.md`](ROADMAP.md) and detailed versions in
[`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md).

Real trackpad behavior remains assigned to EH4-203; display scaling remains
under EH4-302.

**Windows GTK 4.20 repeated-launch pointer failure (2026-10-22):** full
matrix run [`39708415015`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39708415015)
revealed a failure on Windows Server 2022 x86_64, Python 3.12.15, PyGObject
3.58.1, GTK 4.20.3, GLib 2.90.1 and Mesa 26.2.4 llvmpipe WGL. The first
full-app process completed its native Win32 click/pick/close. A later process
found the previous HWND foreground and under the correct screen point, so the
helper withheld the click. Initial correction `553adf3` activated first,
raised the window, and retried pointer placement and `WindowFromPoint`
verification up to five times. Follow-up native diagnostics identified the
cover as GitHub HostedComputeAgent's console (`ConsoleWindowClass`, PID 4920);
`SetForegroundWindow` returned false while the target's raise/topmost calls
returned true. The focused run
[`39711834067`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39711834067)
failed safely without sending a click through the console. The helper now
temporarily attaches the GTK thread's input queue to the foreground console's
queue while activating and raising the target. Run
[`39712180632`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712180632)
showed Windows refuses that attachment (`false`) too. The next focused run
[`39712548364`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712548364)
showed `GetConsoleWindow` is null because the console belongs to HostedComputeAgent,
not the child Python process. The helper now recognizes the exact hosted
console title and minimizes it only when it is the actual hit-tested blocker,
then restores it after the click. Focused Windows GTK 4.20.3 run
[`39712852467`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712852467)
passed five fresh app cycles; each native click picked `O:0`, rendered and
closed. The widget suite passed 65 tests and skipped 3; five production scene
cycles and render validation also passed. Local helper/workflow/full-app
regressions pass (**22 passed, 1 skipped**); `py_compile` and `git diff --check`
pass. The follow-up matrix `39717469974` subsequently passed all configured
Windows GTK cells, five native app cycles each; this historical issue is
resolved in the current matrix.

**Latest native Windows pointer result (2026-10-22):** focused run
[`39706994456`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39706994456)
passed Windows x86_64 GTK 4.8.2 and 4.10.1. In each cell the real
`EasyHybridApplication`/`MainWindow` loaded the generated water fixture,
received OS-injected Win32 clicks through the production GTK pick path, picked
oxygen, rendered, and closed through five fresh-app cycles. The production
menu/VisMol scene also passed five open/pick/render/close cycles and render
validation succeeded. The failure was test coordinate calibration: the first
Win32 point differed from GTK's received logical point by about `(14.3, 11.8)`;
each retry then reset its learned offset to the latest, nearly-zero residual.
The test now accumulates the measured offset for the app cycle. The same
commit's local helper/workflow/full-app checks passed (**18 passed, 1 skipped**)
and `py_compile`/`git diff --check` passed. This is focused Windows evidence;
That focused run was followed by matrix run `39717469974`, which passed all
configured Windows, macOS arm64 and Linux GTK cells with native pointer
injection; see the current result at the top of this report.

**Native macOS pointer result (2026-10-22):** focused run
[`39707517301`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39707517301)
passed on macOS 14.8.9 arm64 with Python 3.12.15, PyGObject 3.58.1, GTK
4.24.1, GLib 2.90.0, and Apple Software Renderer/OpenGL 4.1. The production
`EasyHybridApplication`/`MainWindow` loaded the generated water fixture and
completed five fresh-app cycles using `macos-quartz-hid`; all five native
pointer picks selected `O:0`, rendered, and closed cleanly. Production
menu/VisMol passed another five pick/render/close cycles; the complete suite
reported 114 passed and 6 skipped; render validation passed at both requested
scales. The scale test reported `scale_applied=false` and widget scale factor
1, so this does not establish Retina/HiDPI support. This focused result was
superseded by matrix `39717469974`, which passed native pointer cycles in all
configured macOS arm64 GTK minors and Intel macOS GTK 4.8/4.10.

**Purpose:** One consolidated source for repository, architecture, dependency,
GTK/Python compatibility, parity, platform, testing, and known-limitation
status. The permanent task queue remains [`ROADMAP.md`](ROADMAP.md).

**EH4-203 scroll semantics (2026-10-22; full native matrix passed, trackpad review pending):** GTK's
`EventControllerScroll.get_unit()`/`Gdk.ScrollUnit` capability is detected on
GTK 4.8.2, 4.14.5 and 4.24.1. VisMol requests continuous deltas wherever that
capability exists, normalizes wheel detents and surface logical pixels to a
positive-down convention, and accumulates fractional deltas. Both units read
Ctrl/Shift from the current event and apply them only while dispatching the
normalized action, preserving the previous GL-core modifier state. Incomplete
typelibs keep the discrete fallback. The focused delta, event-unit, direction
and modifier tests passed **3/3** on each of three local Linux GTK runtimes
(GTK 4.8.2, 4.14.5 and 4.24.1). This was native Linux Mint 22.3 x86_64 with
Python 3.12.15/PyGObject 3.58.1/GLib 2.90.0 for GTK 4.8.2 and 4.24.1, and
Python 3.12.3/PyGObject 3.48.2/GLib 2.80.0 for GTK 4.14.5. The tests exercised
the production scroll callback with deterministic event-unit inputs; they did
not create a GL context or use a physical input device. Corrected full native
matrix run
[`39801594903`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39801594903)
completed successfully across 30 cells: Linux x86_64, Windows x86_64 and
macOS arm64 for GTK 4.8–4.24, plus Intel macOS GTK 4.8/4.10. All 30 runtime
artifacts confirm exact OS/architecture, Python, PyGObject, GTK patch, GLib
and GL backend. Each reports passing widget-pattern tests, five full-app
native pointer pick/render/close cycles and five production menu/VisMol
cycles. The first attempt `39799035762` exposed workflow test ordering:
widget-pattern tests imported `vismol.utils.matrix_operations` before Cython
extensions were built, so no scroll assertion was reached in those jobs.
Commit `f57cf86` builds graphics extensions before widget-pattern tests in all
four workflow configurations; its static ordering guard passes locally.
EH4-203 remains unchecked pending physical macOS trackpad review, which is
**NOT TESTED** by the hosted synthetic-event tests.

**EH4-204 selection-state correction (2026-10-22; partial):** viewing
selection clear now resets `Atom.selected`, `selected_objects`, and the
per-object ID buffer. Programmatic index selection and invert-selection now
rebuild the atom set, object set, flags and ID buffers consistently. Focused
production selection regressions cover atom-only selection, whole-residue
select/toggle, clear, index selection, invert, and atom label text. Six
focused tests pass on Linux GTK 4.8.2 and GTK 4.24.1. The opt-in real-app
water fixture test verifies a native Linux XTest oxygen click selects all
three water atoms in default residue mode, then clears and checks oxygen-only
atom mode. It also uses production session controls to hide/show the oxygen
nonbonded representation and show/draw/hide its `O` text through the atom label
representation. The full-app cycle passed at GTK 4.24.1, Python 3.12.15, PyGObject
3.58.1 and GLib 2.90.0, using pDynamo3
`6b28dd8958e1a705fcdca130f4ab862a8af8de82` compiled in a disposable Python
3.12 tree. X11/Xvfb used EGL/PyOpenGL and Mesa 25.2.8 llvmpipe (LLVM 20.1.2),
OpenGL 4.5 Core; fixture load, pick, selection assertions, render and close
passed. The session serializer now delegates camera capture/restore to a
separately tested helper. Camera helper tests cover pickle round-trip, viewport
and matrix restoration, old payloads without viewport dimensions, absent
camera state, and best-effort GTK size-request failure. The combined camera and
selection tests pass on local Linux GTK 4.8.2 and 4.24.1. A subsequent one-cycle
full-app check at GTK 4.24.1 also passes after the serializer refactor, confirming
the production module import and water load/native pick/render/close path. That
same real-app fixture now exercises the production pk1/pk2/pk3 measurement
workflow and checks both water O–H distances and the H–O–H angle against the
known fixture coordinates; it passes locally at GTK 4.24.1.
The user's Python 3.10 pDynamo3 environment/source was not modified. This is
local Linux evidence only; full `.easy` save/reopen integration, multi-cycle
full-app coverage on this branch, and the all-platform/all-version matrix
remain pending.
EH4-204 remains unchecked. Index-selection and invert changes pass focused
unit coverage but are not yet exercised by the full-app scenario.

**EH4-204 `.easy` round trip (2026-10-23; partial):** commit `aeeb4e7` makes
the real-app fixture save a `.easy` session, corrupt the live camera, reopen
it and require restored camera matrices plus a rendered scene. This passed
5/5 native-pointer cycles on Linux X11 GTK 4.24.1 (NVIDIA, EGL). GTK 4.24.1
rejects `GDK_DEBUG=gl-glx` and selects EGL or GLX per X11 system (EGL on
native NVIDIA, GLX in the CI conda Xvfb cell); a PyOpenGL mismatch leaves no
current context. Commit `611eac0` pins GLX with `GDK_DISABLE=egl` and passed
5/5 locally on native NVIDIA X11 and Xvfb llvmpipe. All-platform/all-minor
matrix run `40043447733` is pending.

**EH4-204 native acceptance (2026-10-24; complete):** final-head matrix
[`40045300452`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40045300452)
passed **30/30** cells, and focused macOS GTK 4.24 artifact run
`40045322982` passed. Every cell completed five full-app cycles with native
OS-pointer selection, atom/residue behavior, labels, measurements,
representation changes, `.easy` camera save/reopen, render and clean close;
each passed five production menu/VisMol cycles and rendering/export/picking
validation. All 30 artifacts record `EASYHYBRID_FULL_APP_CAMERA_SESSION_ROUND_TRIP=True`.
GTK patches covered Linux 4.8.2–4.24.1 (including Ubuntu 4.16.3, Fedora
4.16.13, Debian 4.18.6), Windows 4.8.2–4.24.1, macOS arm64 4.8.3–4.24.1,
and Intel macOS 4.8.2/4.10.1. Hosted GL used Linux llvmpipe/X11, Windows
llvmpipe/WGL and macOS Apple Software Renderer. Physical GPUs, Retina/HiDPI
and trackpad behavior remain separate **NOT TESTED** claims.

**EH4-205 focused implementation (2026-10-21):** the production VisMol
`Gtk.GLArea` now checks the realized OpenGL version before initializing its
shaders, requires OpenGL 3.3+, and shows a portable GTK4 error window for
context, capability, initialization, or render failures. Repeated GL callbacks
are suppressed after a failure; the application remains open so the user can
read the reason and close it normally. Local Linux x86_64/X11 testing used
Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0. A real Gtk.GLArea
with an injected OpenGL 2.1 version presented the fallback dialog and skipped
VisMol initialization; an injected render exception produced one dialog and
prevented further scene renders. All six diagnostics tests passed. The full
Linux Xvfb regression suite passed (168 passed, 14 skipped, one existing GLib
warning). A separate GTK GL smoke used Mesa 25.2.8 llvmpipe (OpenGL 4.5 Core)
and passed three window lifecycle cycles. All other GTK/platform cells are
**NOT TESTED** for this change; EH4-205 remains unchecked until the required
full native matrix runs.

Native X11 recheck on 2026-10-21 passed `tests/test_graphics_diagnostics.py`
**6/6** on local Linux x86_64 at GTK 4.14.5 (Python 3.12.3 / PyGObject
3.48.2 / GLib 2.80.0) and GTK 4.24.1 (Python 3.12.15 / PyGObject 3.58.1 /
GLib 2.90.0), with `G_DEBUG=fatal-criticals`. It covers visible error windows,
the realized GLArea unsupported-version path, and one-time render failure
handling. The mocked 2.1 OpenGL version tests graceful fallback; it does not
simulate a physical unsupported GPU. The first native attempt failed because
the test had not applied the application's GL startup policy; the test module
now applies `configure_gl_context_environment()` before any test opens a
display. GTK 4.24.1 printed `Unrecognized value "gl-glx"` and a missing IBus
module warning in this local direct-runtime setup, but all six tests passed.
Other GTK minors, Windows/macOS, and real unsupported hardware remain
**NOT TESTED**; EH4-205 is still open pending the native matrix.

**EH4-205 native acceptance (2026-10-24; complete):** matrix run
[`40050468870`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40050468870)
passed **30/30** cells on the final batch head. All artifacts include a
passing regression suite, five full-app native pointer pick/render/close
cycles, five production menu/VisMol cycles and renderer validation. The
artifacts record exact OS/architecture, Python, PyGObject, GTK patch, GLib and
backend; GTK coverage includes Linux 4.8.2, 4.10.1, 4.12.1, 4.14.1, 4.16.3,
4.16.13, 4.18.6, 4.20.3, 4.22.5 and 4.24.1; Windows 4.8.2–4.24.1; macOS
arm64 4.8.3–4.24.1; and Intel macOS 4.8.2/4.10.1. Software renderers were
Mesa llvmpipe on Linux and Windows and Apple Software Renderer on macOS. The
earlier fail-fast runs `40049339951` and `40049843306` exposed two test-scope
defects; both corrections are documented in `AGENTS.md` and the roadmap, and
the corrected matrix passed. EH4-205 is complete for configured matrix
acceptance; physical unsupported GPUs remain **NOT TESTED**.

Rechecked on the implementation branch on 2026-10-21: the diagnostics module
passed **6/6**, the startup/GL smoke passed with three clean window lifecycle
cycles, and the complete suite passed **168 tests** with 14 skips and one
pre-existing GTK 4.8 chooser GLib warning. Runtime was Linux 6.8.0-147-generic
x86_64, Python 3.12.3, PyGObject 3.48.2, GTK 4.14.5, GLib 2.80.0, Mesa
25.2.8 llvmpipe, OpenGL 4.5 Core. `py_compile` and `git diff --check` passed.
**EH4-301 local GTK interaction checks (2026-10-20; partial):** under Linux
Mint 22.3 x86_64 with Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib
2.80.0, native Xvfb checks for GTK event-controller mouse/keyboard dispatch,
context-menu placement and response-window behavior passed (3 passed). The
GTK 4.14 file-dialog adapter checks passed 2 tests; 9 GTK 4.8/conditional
chooser cases were skipped. Clipboard behavior, screen-reader/accessibility
checks, native platform chooser interaction, and Windows/macOS runtimes remain
**NOT TESTED**. A full widget-module attempt inside the restricted sandbox
failed its display precondition and then segfaulted in a Gtk.Builder color
button test; it is not counted as a native result. EH4-301 stays unchecked.

The focused subset was rerun with a usable Xvfb display on 2026-10-21 using
the same Linux GTK runtime: controller dispatch, context-menu placement,
response-window actions and file-dialog adapter behavior returned **7 passed,
1 skipped**, with 61 unrelated tests deselected. This confirms the selected
GTK 4.14.5 interactions; platform-specific chooser and accessibility gaps
remain open.

**EH4-301 Linux GTK integration recheck (2026-10-21; partial):** under
Linux Mint 22.3 x86_64 / Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 /
GLib 2.80.0, native Xvfb/X11 widget tests for chooser lifecycles, response
dialogs, context-menu placement, event-controller payloads, and clipboard
passed **20** with **5 skipped** on the latest run. GDK clipboard tests verified Unicode
round-trips both in-process and from a separate GTK reader process while the
owner serviced its GLib context. The X11 cross-process result does not verify
Windows/macOS clipboard behavior, native chooser selection, hardware keyboard
conventions, accessibility/screen-reader behavior, or other GTK minors;
EH4-301 remains unchecked.

The same focused X11/Xvfb GTK interaction slice passed on 2026-10-21 under
both local Linux GTK runtimes: GTK 4.14.5 / Python 3.12.3 / PyGObject 3.48.2 /
GLib 2.80.0 and GTK 4.24.1 / Python 3.12.15 / PyGObject 3.58.1 / GLib
2.90.0. Each run reports **20 passed, 5 skipped, 45 deselected**, covering
event-controller payloads, popovers, response/chooser windows and same-process
and cross-process Unicode clipboard transfers. Xvfb kept the tests from
changing the host desktop clipboard. GTK 4.24.1 printed an unrecognized
`gl-glx` debug-flag warning, a Mesa DRI3 warning, and an unavailable IBus
module warning; the tests passed. This remains Linux-only test coverage; all
other GTK minors and Windows/macOS native integration are **NOT TESTED**.
**EH4-301 hosted Windows clipboard boundary (2026-10-24):** PR #5's
fail-fast matrix run [`40049339951`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40049339951)
failed the cross-process clipboard assertion on Windows Server 2022 x86_64,
Python 3.12.15 / PyGObject 3.46.0 / GTK 4.8.2 / GLib 2.78.0. The artifact
records WinSta0 and Mesa 26.2.4 llvmpipe WGL. In-process Unicode clipboard
read/write passed, but a separate GTK reader timed out after four seconds
while the owner serviced its GLib context. The test now skips only that
cross-process assertion on GitHub-hosted Windows; the same-process Windows
test remains enabled. This evidence does not distinguish a GTK/Win32 issue
from the hosted runner session. Cross-process Windows clipboard and macOS
clipboard behavior remain **NOT TESTED**, and EH4-301 remains unchecked. After
narrowing the assertion, the two focused clipboard tests pass on Linux Mint
22.3 x86_64 under Xvfb/X11 with Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5
/ GLib 2.80.0 (**2 passed, 70 deselected**); this does not change the
Windows/macOS limitation.
**EH4-302 local X11 scale/resize check (2026-10-20; partial):** the real
Gtk.GLArea renderer validation passed at `GDK_SCALE=1` and `2` on Linux Mint
22.3 x86_64, Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0,
Mesa 25.2.8 llvmpipe OpenGL 4.5. At scale 2, the widget scale factor was 2
and framebuffer dimensions doubled from 420x300 to 840x600; representation
coverage, projected sizes, picking, viewport resize and export checks passed.
This is Xvfb/X11 evidence only. Native Wayland, physical HiDPI displays,
Retina, multi-monitor transitions, Windows/macOS and other GTK runtimes remain
**NOT TESTED**. EH4-302 stays unchecked.

The renderer check was rerun on 2026-10-21 on the same GTK 4.14.5 environment:
**1 passed**. With `GDK_SCALE=2`, GTK applied widget scale 2 and doubled the
GLArea framebuffer to 840x600 from 420x300. All representation, projected
size, selection, resize, export-difference and GL checks passed at scale 1 and
2. This remains virtual X11 evidence; physical displays, Wayland, Retina,
multi-monitor transitions and non-Linux platforms are still **NOT TESTED**.

The main window now bounds restored/default logical dimensions against GDK's
connected-monitor geometries, with margins for decorations and panels. It
uses the smallest connected dimensions so a window opened on a secondary
monitor remains reachable. The compatibility tests passed **9/9**, and a
display-backed Xvfb monitor-geometry check passed **1/1** on 2026-10-21.
Restoring an oversized window on physical displays, monitor hot-plug or scale
transitions, Wayland, Retina, Windows/macOS and other GTK runtimes remain
**NOT TESTED**; EH4-302 stays unchecked.
**EH4-303 installation instructions (2026-10-21; partial):** the root README
documents a conda-forge GTK 4.24.1 baseline environment, native compiler
prerequisites, the graphics-extension build, separate pDynamo3 setup, and
Linux/macOS plus PowerShell launch environment variables. A fresh conda-forge
environment on Linux x86_64 installed Python 3.12.15, GTK 4.24.1, PyGObject
3.58.1, GLib 2.90.0, and NumPy 2.5.4. With user-site packages disabled, all
seven Cython extensions built using that environment's NumPy headers and
imported successfully; the native GTK startup/icon smoke passed three window
cycles under Xvfb/X11 and Mesa 25.2.8 llvmpipe (OpenGL 4.5 Core). An initial
build exposed contamination by the host's user-site NumPy 1.x headers, so the
README now advises disabling user-site packages during builds.

An explicit package-URL lock for Linux x86_64 was exported from that verified
runtime. On Linux Mint 22.3 x86_64, the lock recreated a fresh conda prefix;
all seven extensions built from a clean source copy and imported, and the GTK
startup/icon smoke again passed three open/close cycles. The replay used
Python 3.12.15 / PyGObject 3.58.1 / GTK 4.24.1 / GLib 2.90.0 / NumPy 2.5.4
and the NVIDIA GeForce RTX 4060 Ti OpenGL 4.6.0 backend. This is Linux GTK
4.24.1 developer-install evidence only: Windows/macOS and other GTK minor
locks, packaged launchers, and full pDynamo3 installation remain **NOT
TESTED**. EH4-303 remains unchecked.

The lock replay's GTK window smoke must be launched with `conda run` (or an
activated environment) so the prefix's GTK runtime variables and libraries
are present. Calling the prefix `python` directly bypassed these and could
not open the Xvfb display. The installer-manifest test passed separately with
`pytest --noconftest` (2 passed); the default repository `conftest.py` imports
existing source-tree binary extensions built against NumPy 1.x, which cannot
load in the locked NumPy 2.5.4 environment. This test invocation adjustment
does not change the recorded clean-copy build/import evidence.
**EH4-304 Linux launcher prototype (2026-10-21; partial):** added
`packaging/linux/run-easyhybrid4.sh` for a bundle containing `app/` and a
relocated conda runtime under `runtime/`, while using an external compiled
pDynamo3 checkout. It initializes a conda-packed runtime once, sets the
application and pDynamo search paths, and chooses a user-cache scratch path.
It sources the relocated runtime's conda activation hooks and selects EGL for
PyOpenGL. Two shell-wrapper tests pass on Linux Mint 22.3 x86_64 (Python 3.12.3).
A temporary conda-pack archive was extracted at a different prefix; after
rebuilding the seven VisMol Cython extensions against that environment's
NumPy, the full-app test passed one real pDynamo3 load/render/XTest oxygen-pick
and close cycle under X11/Xvfb with Python 3.12.15, PyGObject 3.58.1, GTK
4.24.1, GLib 2.90.0 and Mesa llvmpipe OpenGL 4.5/EGL. However, directly
starting the application through the shell launcher still fails before
`MainWindow`: `Gdk.Display.get_default()` is `None` and GTK rejects the splash
window. The same Xvfb display works in a minimal GTK probe and in the full-app
harness, which initializes the display before importing EasyHybrid. The startup
adapter now preserves an explicitly selected EGL backend rather than forcing
GDK's rejected `gl-glx` flag; its focused regression and related launcher tests
pass (7 passed, 12 deselected), and the full-app harness passes one native
XTest load/render/pick/close cycle. An early display-open attempt in
`easyhybrid.py` did not resolve the wrapper failure and was reverted. The
packaged direct-launch acceptance therefore remains **FAIL / unresolved**.
No desktop installer was built; Windows and macOS packaging and GTK versions
other than 4.24.1 remain **NOT TESTED**. EH4-304 stays unchecked.
**EH4-400 frozen water-fixture check (2026-10-21; partial):** the real app
smoke loads the checked-in `tests/fixtures/water.pdb` and compares all three
VisMol coordinates against independent expected values with 0.0005 Å
tolerance. Five fresh production MainWindow cycles on Linux x86_64 preserved
the coordinates, loaded three atoms, rendered, picked oxygen (`O:0`), and
closed cleanly. Runtime: Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 /
GLib 2.80.0, pDynamo3 revision `09e583049de5d1cdca6c9b4009c7c75e451a5ae0`
rebuilt for Python 3.12.3, Mesa 25.2.8 llvmpipe OpenGL 4.5 Core. Pointer
input in this test is a synthetic GTK callback. Windows/macOS, other GTK
runtimes, additional fixture types and broader molecular invariants remain
**NOT TESTED**; EH4-400 stays unchecked.

The VisMol scale/resize test now reads its six-atom input from the checked-in
`tests/fixtures/render_validation.pdb`; a fixture test locks the atom names,
elements, residue identities and coordinates for both PDB inputs. On Linux
Mint 22.3 x86_64, the GTK 4.14.5/Xvfb renderer test passed at scale 1 and 2
(Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0): all eight representations,
resize, export, and 9/9 sphere-pick samples passed with llvmpipe OpenGL 4.5
Core. Additional OS/GTK runtimes, other structure formats and wider scientific
invariants remain **NOT TESTED**.

**EH4-304 test scope correction (2026-10-24):** PR #5 matrix run
[`40049843306`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/40049843306)
ran the full regression suite on Windows Server 2022 x86_64 with Python
3.12.15 / PyGObject 3.58.1 / GTK 4.24.1 / GLib 2.90.1 and Mesa 26.2.4
llvmpipe WGL. The suite had 145 passes and 8 skips, but two tests in
`tests/test_linux_bundle_launcher.py` failed with `WinError 193` because they
execute a Linux `.sh` launcher as a Win32 program. This test module is now
scoped to Linux only; its fake executable tests remain active on Linux.
Windows/macOS skips do not verify those platforms' packaging, and EH4-304
remains unchecked.

**Current focused result (2026-10-20): GTK 4.24/macOS full-app centering test
passes.** Run [`39476612300`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39476612300)
used GTK 4.24.1 / GLib 2.90.0 / PyGObject 3.58.1 / Python 3.12.15 on
macOS 14.8.9 arm64 with Apple's OpenGL 4.1 Software Renderer. It passed the
native GTK/GL smoke, 62 widget-pattern tests (6 skipped), five real
`EasyHybridApplication`/`MainWindow` cycles loading the generated water PDB,
picking oxygen (`O:0`), and closing cleanly, five production menu/VisMol scene
cycles, and the 101-passed/6-skipped complete regression suite. Render
validation passed at requested scales 1 and 2; GTK reported widget scale factor
1 and `scale_applied=false` for both, so Retina/HiDPI scaling is not verified.
The test pick invokes GTK callbacks with synthetic coordinates and does not
inject an OS pointer event.

The repeated failure was in the test's centering wait: it required multiple
unchanged GLib timer samples after the center residual had reached zero and
the transform delta was zero. macOS serviced too few timer polls before the
test deadline. The harness now waits on the actual centering residual and
transform delta. This is a test synchronization correction, not a GTK 4.24
runtime or application renderer defect. Local Linux GTK 4.14.5/NVIDIA also
passed five full-app cycles with the updated harness. Other platform/version
cells were not rerun for this test-only correction; previous component-matrix
evidence remains separate.

**EH4-202 native pointer branch recheck (2026-10-21):** branch
`eh4-202-cross-platform-pointer-injection` at `68a7dd3` passed the local
pointer-helper, workflow-order, and real full-app smoke tests (**12 passed**)
on Linux Mint 22.3 x86_64 with Python 3.12.3, PyGObject 3.48.2, GTK 4.14.5,
GLib 2.80.0, X11/Xvfb, and Mesa 25.2.8 llvmpipe/OpenGL 4.5 Core. The real
EasyHybridApplication loaded its generated water fixture, received an XTest
pointer click, picked oxygen (`O:0`), rendered, and closed cleanly. The pDynamo3
runtime was a disposable Python 3.12 build at `/tmp/eh4-401-pdynamo3`, not the
user's installed pDynamo environment. Win32 and Quartz injection code has not
been run natively here; all other GTK/platform cells, Wayland, and physical
hardware remain **NOT TESTED**. EH4-202 remains unchecked pending its required
matrix and native Windows/macOS pointer validation.

The same Linux XTest full-app check also passes locally at GTK 4.8.2 and
4.24.1. These are isolated conda-forge GTK runtimes, not the shared launcher
environment; both ran Python 3.12.15, PyGObject 3.58.1 and GLib 2.90.0, with
pDynamo3 loaded from `/home/shabir/software/pDynamo3-py312`. GTK 4.8.2 passed
five fresh production `EasyHybridApplication`/`MainWindow` cycles. GTK 4.24.1
passed one cycle. Each loaded the generated water PDB, received a real XTest
click, picked `O:0`, rendered with Mesa 25.2.8 llvmpipe (OpenGL 4.5 Core), and
closed cleanly. GTK 4.24.1 required
`GDK_DEBUG=gl-prefer-gl` with `PYOPENGL_PLATFORM=egl`: its older `gl-glx` hint
is unrecognized by GTK 4.24, and leaving PyOpenGL on GLX caused a context
lookup failure before the pointer test. This is local Linux evidence only;
other Linux GTK minors and all native Windows/macOS injection combinations
remain **NOT TESTED**.

The shared launcher (`activate_easyhybrid4.sh` → `pdynamo3.sh`) uses Python
3.12.3, pDynamo3 from `/home/shabir/software/pDynamo3-py312`, and system GTK
4.14.5 / PyGObject 3.48.2 / GLib 2.80.0. On that actual shared runtime, **5/5**
fresh app launches loaded the water fixture, picked `O:0` using XTest, rendered,
and closed cleanly. All three tested GTK runtimes used the same pDynamo3 source
tree; only GTK 4.14.5 is the user's shared EasyHybrid launcher environment.
This evidence is Linux-only, and every other GTK/OS combination remains
unverified for native pointer injection.

**EH4-202 cross-platform native-pointer matrix diagnosis (2026-10-21):** the
first all-scope run [`39703837396`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39703837396)
passed GTK window/GLArea smoke, widget tests and pDynamo3 build/import before
the full-app pointer step failed in Windows GTK 4.8.2/4.10.1 and macOS arm64
GTK 4.10.5 with `NameError: Graphene is not defined`. The test harness imported
`Graphene` only in its Linux-specific `GdkX11` import branch, while Windows and
macOS use it to map the projected GLArea coordinate into the top-level window
before Win32/Quartz event injection. Earlier Windows/macOS full-app passes
used synthetic GTK callback coordinates and therefore did not cover this
native-input branch. Moved the Graphene import into the shared import path and
added a regression assertion. The first matrix was canceled after confirming
the same shared failure and before spending runner time on the remaining
cells. The regression assertion passes locally; corrected native Windows and
macOS runs and the full all-platform/all-minor matrix are pending. EH4-202
remains unchecked. The artifact runtimes were Windows GTK 4.8.2 (Python
3.12.15, PyGObject 3.46.0, GLib 2.78.0), Windows GTK 4.10.1 (Python 3.12.15,
PyGObject 3.48.1, GLib 2.78.0), and macOS GTK 4.10.5 (Python 3.12.15,
PyGObject 3.58.1, GLib 2.90.0); renderers were Mesa 26.2.4 llvmpipe WGL and
Apple Software Renderer OpenGL 4.1.

**EH4-202 Win32 native click failure (2026-10-21):** focused run
[`39704362525`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39704362525)
confirmed GTK 4.8.2 and 4.10.1 on Windows Server 2022 x86_64 reach the
`windows-win32-user32` path, but production MainWindow does not pick the water
oxygen. The artifact lacks event and sampled-coordinate traces, so this is not
yet attributable to GTK, coordinate conversion, Win32 activation, or the
renderer. The harness now checks foreground activation, client bounds and
pointer hit target, and records coordinates delivered to the production GTK
gesture and the last render-thread pick. Local focused helper/workflow tests
pass (12 passed). The instrumented real full-app test also passed one Linux
X11/XTest cycle on Linux Mint 22.3 x86_64 (Python 3.12.3, PyGObject 3.48.2,
GTK 4.14.5, GLib 2.80.0, Mesa 25.2.8 llvmpipe/OpenGL 4.5 Core), picking
`O:0`, rendering and closing cleanly. This Linux result does not exercise
Win32. The next focused run subsequently exposed the coordinate-origin offset
and is documented below; the native correction is now implemented but still
needs a passing Windows runner result. EH4-202 stays open.

Follow-up run [`39704981928`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39704981928)
captured both Win32 GTK gesture callbacks and the actual pick coordinates on
Windows Server 2022 x86_64 (GTK 4.8.2 and 4.10.1, Mesa 26.2.4 llvmpipe WGL).
The foreground window and hit-test were correct; the coordinate received by
GTK was displaced about 14.3 x 11.8 logical pixels from the projected oxygen
coordinate. The harness now feeds the measured discrepancy back into the next
native click, and the full-app test uses one shared `inject_native_pointer()`
call on Linux/X11, Windows/Win32, and macOS/Quartz. The lifecycle and pass
assertions remain common across platforms; only event injection is adapted.
Focused local checks pass (**17 passed, 1 skipped**), as do Python compilation
and `git diff --check`. This correction has not yet been verified on a native
display or runner; corrected Windows and full-matrix runs remain pending.
EH4-202 remains unchecked.

Focused rerun [`39705506718`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39705506718)
verified the coordinate correction in the first launch on both Windows GTK
4.8.2 and 4.10.1: GTK picked `O:0` after the feedback-adjusted second click.
Both jobs then failed at the next fresh launch because Windows refused
`SetForegroundWindow` for the new process. The pointer already targets the
verified EasyHybrid HWND; the actual click activates it. Foreground activation
is now best-effort, while window-under-pointer verification and successful
production GTK pick remain required. This second correction needs a new
focused native Windows result. Exact runtimes: Windows Server 2022 x86_64,
Python 3.12.15, PyGObject 3.46.0 / GTK 4.8.2 and PyGObject 3.48.1 / GTK 4.10.1,
GLib 2.78.0, Mesa 26.2.4 llvmpipe WGL.

Run `39705953113` showed the first launch passed on both GTK versions after
coordinate calibration, then the second launch failed because the pointer hit
another HWND. Its screen Y coordinate was 443 for a requested client Y of 344.
The helper now restores the window before `ClientToScreen`; that alone did not
clear the overlay. It temporarily raises the disposable test window to
`HWND_TOPMOST` for the verified real click, then returns it to normal z-order.
It still requires `WindowFromPoint` to identify the EasyHybrid window. Focused
rerun is pending.

Run `39706561091` confirmed the raised window receives the actual pointer
events, but its GTK 4.8.2 pick trace alternated between the uncorrected
`(347,199)` and corrected `(361,211)` positions. The harness was deriving each
attempt from the original GTK point and replacing the learned offset with the
latest residual; a nearly zero residual therefore erased the Windows inset
correction. It now accumulates corrections across attempts in the same app
cycle, with a local regression for retaining the learned offset. The initial
GTK 4.8 pick failed in that run. Focused run
[`39706994456`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39706994456)
then passed both Windows cells: GTK 4.8.2 and 4.10.1 each completed five
full-app cycles with successful native pointer pick, render and clean close,
five production scene cycles, and render validation. The native issue is
resolved for these two Windows GTK runtimes; all other native platform/minor
combinations still require the full matrix. See the permanent Win32 notes in
[`AGENTS.md`](../AGENTS.md).

**Current native matrix (2026-10-20):** run
[`39485989866`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39485989866)
completed successfully at main commit `e096a024bb2ccc0755b5ba632f1d5aa5a74a3b13`.
Every workflow cell built the seven graphics Cython extensions and passed its
native GTK/GL checks; component cells completed five production menu/VisMol
open/pick/render/close cycles. The focused full-app smoke also passed wherever
enabled by the workflow, but its pick invokes GTK callbacks with synthetic
coordinates rather than injecting an OS pointer event. Exact patch versions
and host/runtime details are in the uploaded artifacts and
[`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md). This is matrix-backed hosted
software-renderer evidence; it does not establish physical-GPU, Retina,
trackpad, Wayland, or native OS input behavior.

The native workflow regression suite now checks that all nine supported GTK
minor series remain declared and that GTK 4.16/4.18 retain Windows and macOS
source-build providers with runtime recording. Its focused local result is
5 passed; this guard does not substitute for rerunning the native matrix.
**EH4-202 local graphics follow-up (2026-10-21):** Linux x86_64 under
Xvfb/X11, Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0,
Mesa llvmpipe OpenGL 4.5 Core Profile. The real-context render validation
passed at `GDK_SCALE=1` and `2`; GTK applied scale 2 and doubled the
framebuffer. The live `Gtk.GLArea` rendered with its nonzero GTK-owned
framebuffer (ID 1). All eight representations rendered without GL errors;
sphere picks (O/H1/N), impostor picks (C/N/S), and the resized sphere pick
all hit 9/9 points. The 2x export mean absolute difference was 0.0145/255 at
scale 1 and 0.0085/255 at scale 2; no pixels differed by more than 64/255.
The resized sphere was 32x31 px. This run verifies the new framebuffer
assertion only on the local GTK runtime; the cross-platform/minor matrix has
not been rerun for it. PNG captures were written under
`/tmp/eh4-202-render-evidence` for local inspection.

The same Linux x86_64 host also passed five fresh full-app cycles under
Xvfb/X11 using the real EasyHybridApplication/MainWindow, pDynamo3-backed
water fixture loading and an XTest-injected pointer click that selected
`O:0`; each cycle rendered and closed cleanly. Runtime: Python 3.12.3 /
PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 / Mesa 25.2.8 llvmpipe,
OpenGL 4.5 Core. The pDynamo3 source/build revision
`09e583049de5d1cdca6c9b4009c7c75e451a5ae0` was supplied on `PYTHONPATH`,
not installed in the GTK environment. This is Linux GTK 4.14.5 evidence only;
Windows/macOS native pointer injection and full-app tests on other GTK/platform
cells remain **NOT TESTED**.
**CI quality gate update (2026-10-20):** the native matrix now runs Python
`compileall` across `src/` and `tests/`, then repo-wide Ruff critical checks
(`E9,F63,F7`) in every GTK runtime job. Local Linux validation passed. The
updated hosted jobs have not yet run. Existing matrix steps already build
graphics extensions and pDynamo3, perform pDynamo imports, run tests, and
upload per-cell logs.

**EH4-500 strict typing follow-up (2026-10-25):** added mypy 1.20-compatible
strict checking for `src/os_integration/app_paths.py`, with explicit path and
environment mapping types. `mypy.ini` pins the syntax target to Python 3.10,
the project floor. The native conda-backed GTK jobs now install the dev
requirements and run this check on Linux, Windows and macOS. Local mypy passed
on Linux x86_64 with Python 3.13.9; the focused path/workflow tests passed
32/32 on Linux Mint 22.3 x86_64, Python 3.12.3 / PyGObject 3.48.2 / GTK
4.14.5 / GLib 2.80.0. The hosted matrix for this new gate is pending, and the
check currently covers the path adapter rather than claiming whole-repository
type safety.
**Native UI acceptance (EH4-502):** matrix run
[`39526661552`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39526661552)
completed successfully across all 30 provisioned OS/GTK cells. Native GTK
window, Gio action, real GLArea, and widget-pattern/dialog steps succeeded in
the cells. Local GTK 4.14.5/Xvfb widget tests passed 62 with 6 skips; the
startup/window smoke passed. Wayland, physical GPU, Retina, and trackpad
coverage remain separate and untested.

**EH4-202 input-picking history and current acceptance state.** GTK
pointer events arrive in widget-local logical units, while VisMol pick reads
use framebuffer pixels. `widget_to_framebuffer_coordinates()` now converts
press/release/motion input using the live widget and GL framebuffer dimensions.
Native Linux X11/NVIDIA testing at GTK 4.14.5, Python 3.12.3, PyGObject 3.48.2,
GLib 2.80.0 and `GDK_SCALE=2` picked the projected oxygen atom in **20/20**
fresh test-host open/callback-pick/render/close cycles using EasyHybrid menu/VisMol components. The pick is triggered by calling the GTK gesture handlers with synthetic coordinates, not by injecting an OS pointer event; the harness does not launch EasyHybridApplication/MainWindow. The focused GTK compatibility
tests pass **7/7**. The matrix workflow now exercises the same projected-oxygen
GTK event in **5 isolated component-harness cycles per cell** (20 until
2026-10-20; reduced at the maintainer's request). These are not full
EasyHybrid interface launches or OS-injected pointer events. First expanded run
[`39307131433`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39307131433)
completed **19/30 PASS**: every Linux and Windows cell passed; all 11 macOS
cells rendered the scene but returned no atom ID through Apple Software
Renderer. A focused dither-only correction did not resolve it: expanded run
[`39309838872`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39309838872)
again passed all 19 Linux/Windows cells and failed all 11 macOS cells, despite
matching click and framebuffer coordinates. The pick pass now disables
blending, dithering, framebuffer sRGB conversion and multisampling for exact
RGB ID rendering, then restores all four GL states. This did not fix native
macOS. Matrix run
[`39311621966`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39311621966)
still fails Apple Software Renderer picking in 11 completed macOS cells,
including Apple Silicon GTK 4.8.3–4.24.1 and Intel macOS GTK 4.8.2/4.10.1. The GTK 4.12.1
artifact shows the correct in-bounds projected oxygen coordinate and viewport,
but `glReadPixels` returns white `(255,255,255,255)` (background ID
`16777215`), with GL error 0 and the four states disabled. GTK's GLArea source
binds its own framebuffer as read/draw target before render callbacks; there is
no evidence for rebinding framebuffer 0. The failure is narrowed to selection
geometry not writing the sampled pixel, but its cause is still unknown. Local
Linux X11/NVIDIA GTK 4.14.5 `GDK_SCALE=2` validation after state isolation
passed **20/20** fresh scene cycles; each picked `O:0`, confirmed GL state
restoration, rendered and closed cleanly. The failure harness now records
selection draw calls, active representation shader/VAO state, framebuffer and
viewport bindings, raw target and nearby pixels, and GL state/error. That
instrumentation passed 20/20 local Linux component cycles. The macOS cause was
later identified as its one-pixel line-width limit and fixed with shader-built
hit geometry; full-matrix acceptance is recorded below. The preceding failures
are retained here as diagnosis history, not current blockers.
Earlier matrix run
[`39305083176`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39305083176)
passed **30/30** after the coordinate conversion was first added, confirming
exact GTK patch runtimes and two scene render/close cycles per cell. Artifact
review found that the old smoke did not invoke picking on hosted platforms.
**Render validation (2026-10-20):** a real-context validation at display
scale 1 and 2 now runs in every matrix cell and passed 30/30 in run
[`39355045155`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39355045155). It fixed impostor sphere sizing (a fixed
256-pixel scale ignored window size and display scale), the impostor picking
attribute binding, and invisible dots on Mesa. The 2x offscreen export matches
the screen (mean difference 0.0145/255). macOS CI note: Apple's `CVMCompiler`
keeps a core busy for tens of seconds after many new shader programs, so the
workflow runs the validation after the timed suite.

**Resolved (2026-10-19):** the macOS picking failure was the platform's
1-pixel line-width limit (`GL_LINE_WIDTH_RANGE` 0.1–1.0), not colour processing
or framebuffer binding. Selection lines are now fixed-pixel-width quads with
atom-end caps (`vismol/libgl/shaders/pick_lines.py`). Full matrix
[`39317377076`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39317377076)
passed **30/30**: every cell ran 20 open/render/pick/close cycles, hit the
oxygen at its centre and at 8 points 3 framebuffer pixels away (9/9), and
loaded exactly its pinned GTK patch. The HiDPI coordinate conversion is
accepted by the same run and both are merged to `main`. The `spheres`
selection VAO now binds its radius/instance attributes to the selection
program (fix from the Codex session); run `39321285586` passed **30/30**
with it. At the time of that run, only a static test covered sphere selection;
the real-context spheres pick was added to the renderer validation later and
passed in the 2026-10-21 local run recorded above.
The image-difference, resize and capability checks are now present and pass in
the native matrix (see run `39485989866`). That run's separate full-app picks
used synthetic coordinates; newer native OS pointer evidence and the latest
full-matrix status are recorded at the beginning of this report.

**Full-interface coverage:** the opt-in `tests/test_easyhybrid_full_app_smoke.py`
launches `EasyHybridApplication`, constructs the production `MainWindow`, loads
a generated molecular fixture through EasyHybrid's real pDynamo3-backed
session, renders, picks oxygen through the production GTK gesture callback,
and closes. Linux X11/GTK 4.14.5/Python 3.12.3/PyGObject 3.48.2/GLib 2.80.0/
NVIDIA passed 20/20 cycles in the earlier local run and five cycles with the
current centering gate. Windows GTK 4.8.2 and 4.10.1 passed five cycles each in
focused run `39450153293`. macOS arm64 GTK 4.24.1/Python 3.12.15/PyGObject
3.58.1/GLib 2.90.0/Apple Software Renderer passed five synthetic-coordinate
cycles in focused run `39476612300`. Those earlier cycles did not inject OS
events. Newer native XTest/Win32/Quartz evidence is summarized at the beginning
of this report; matrix `39717469974` subsequently passed full-app coverage in
every configured GTK/platform cell. A pDynamo import without a system label also exposed and fixed a
production display-name fallback to the loaded coordinate file's basename.

The full-app harness has an opt-in native pointer path. On Linux/X11 it uses
`xdotool`/XTest; five local fresh-app cycles under Xvfb/X11 passed: the real
pDynamo3-backed MainWindow loaded water, the XTest click picked `O:0`, the GL
scene rendered, and each window closed cleanly (Python 3.12.3, PyGObject
3.48.2, GTK 4.14.5, GLib 2.80.0, Mesa 25.2.8 llvmpipe/OpenGL 4.5). The
Windows implementation uses Win32 client-to-screen conversion and mouse
events. The macOS implementation maps the GTK widget point through AppKit and
posts Quartz HID events; its CI environment installs PyObjC Cocoa/Quartz.
Workflow checks now request the native path on all desktop OSes. Windows and
macOS native injection passed in all configured GTK/platform cells in matrix
`39717469974`; physical GPU, Retina/HiDPI, Wayland and trackpad claims remain
separately **NOT TESTED**.
Focused helper/workflow tests validate coordinate conversion but do not
substitute for native OS injection.
The full matrix for the initial Linux harness change failed GTK 4.8.2/Linux: the real
XTest click reached the release handler, where `GestureClick.get_current_event()`
raised `TypeError: No means to translate argument or return value for
'GdkButtonEvent'`. Since this event is optional context-menu metadata and the
release coordinates are already saved for menu placement, the handler now
omits that API call completely; regression fakes fail if it is invoked. The
GTK 4.14.5 Linux Xvfb/XTest full-app smoke passed five fresh launches, each with
an actual XTest click and `O:0` pick, rendering and clean close. This does not
validate GTK 4.8. Focused workflow run
[`39526363320`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39526363320)
passed the exact GTK 4.8.2/Linux cell (Python 3.12.15, PyGObject 3.46.0,
GLib 2.78.0, Mesa 25.2.8 llvmpipe/OpenGL 4.5): five XTest-injected clicks
picked `O:0` through five fresh production full-app launches, each rendered
and closed; GTK widget tests passed 64 with 4 skipped. Full native matrix run
[`39526661552`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39526661552)
passed **30/30 jobs** across Linux, Windows, macOS arm64, and provisioned Intel
macOS for GTK 4.8–4.24. Each cell's artifact records the actual runtime and
backend. Linux full-app paths use XTest; Windows/macOS full-app paths still use
synthetic GTK callbacks, so native OS pointer injection on those platforms is
**NOT TESTED**. EH4-202 remains unchecked for that limitation and broader
real-device acceptance.

**Windows full-app CI blocker (2026-10-20):** diagnostic run `39368203653`
(its Actions record was deleted at the maintainer's request after inspection)
passed native GTK/window/Gio/GLArea and five-cycle production menu/VisMol
checks on Windows GTK 4.8.2 and 4.10.1 (Python 3.12.15, PyGObject 3.46.0 and
3.48.1 respectively, Mesa 26.2.4 llvmpipe WGL). It then failed to build the
pinned pDynamo3 revision `6b28dd8958e1a705fcdca130f4ab862a8af8de82`:
MSVC C2466 rejects its empty `SNEGATIVE[0]` array. This table is selected
when `jam == 0`; every `NNEGATIVE[iam][0]` count is zero, and its only reads
are bounded by that count. The Windows-only CI patch now changes the array
declaration and definition to one zero sentinel without changing the count or
calculation loop. The local patch regression passes; native pDynamo3 rebuild
and full-app smoke are pending in verification run
`39448296274` (the run's Actions record will be removed after artifacts are
inspected, per maintainer request).
Windows conda GTK 4.8–4.24 jobs showed the
same build failure; Windows source GTK 4.16/4.18 jobs were cancelled before
the build step. Linux/macOS were skipped in this Windows-scoped run. This is a
Windows pDynamo3 compiler-portability issue, separate from GTK compatibility.

The zero-sentinel patch passed its MSVC compile stage in verification run
`39448296274` (run record deleted after the artifacts and job logs were
inspected and summarized here, per maintainer request), but both Windows GTK
4.8.2 and 4.10.1 then failed linking
`DFTFunctionalModel` with unresolved `xc_mgga_exc_vxc`, `xc_lda_exc_vxc`,
`xc_gga_exc_vxc`, `xc_lda_exc`, and `xc_gga_exc`. Inspection of pinned
pDynamo3 source `6b28dd8958e1a705fcdca130f4ab862a8af8de82` found these wrappers
declared as external in `xc.h` but defined using C `inline` in the bundled XC
translation units. The Windows-only compatibility patch removes `inline`
only from those five wrapper definitions; function bodies and calculations
are unchanged.

Focused verification run `39450153293` passed both Windows cells: GTK 4.8.2
(Python 3.12.15, PyGObject 3.46.0, GLib 2.78.0) and GTK 4.10.1 (Python
3.12.15, PyGObject 3.48.1, GLib 2.78.0). Each built and imported pinned
pDynamo3 `6b28dd8958e1a705fcdca130f4ab862a8af8de82`, then passed the complete
`EasyHybridApplication`/`MainWindow` smoke for five fresh cycles: generated
water PDB load, 3-atom system verification, oxygen pick (`O:0`), render and
clean close. GTK widget tests were 64 passed/4 skipped on 4.8 and 65 passed/3
skipped on 4.10; five-cycle production menu/VisMol scene tests passed. The
real-window rendering and scale-1/2 scene validations used Mesa 26.2.4
llvmpipe WGL (OpenGL 4.6 Core). Full suite results are not implied by this
focused run. The pick invokes GTK gesture callbacks with test coordinates;
it does not inject an OS pointer event. Physical Windows GPUs remain
**NOT TESTED**. The full Linux/Windows/macOS GTK matrix is still required
before merge.

The accidental Intel macOS 4.8/4.10 cells built pDynamo3 and passed GTK and
component tests, then failed during the import preflight because
`PDYNAMO3_SCRATCH` was not set (`TypeError` while joining the unset value to
the MNDO test path). The workflow supplies the runner temporary directory for
this variable in each pDynamo preflight variant; this correction passed on
Windows, while the Intel macOS case remains **NOT TESTED** after the update.
`windows-legacy` now excludes unintended Intel macOS include cells. The
workflow regression tests pass locally.

**EH4-201 component-smoke evidence:** The GTK smoke creates a test-owned
GTK window with EasyHybrid's production menu and bundled VisMol widget. It
does not instantiate `EasyHybridApplication` or `MainWindow`. It
loads a generated three-atom water PDB, verifies two bonds, active
representations and actual draw calls, checks the GL error state, then closes
and reopens the window. On this Linux host (GTK 4.14.5, native X11, NVIDIA RTX
4060 Ti), both cycles passed three times with 22–24 representation draws each
and OpenGL 4.6.0. The synthetic fixture enters VisMol's base session insertion path
because it intentionally has no pDynamo system record. The first full matrix
passed generic GTK/widget checks in 30/30 cells; its added full-app scene step
failed on Linux, Windows and macOS GTK 4.24 because hosted runners do not have
pDynamo3 (`ModuleNotFoundError: pBabel`). The workflow now builds the graphics
extensions and runs a pDynamo-independent EasyHybrid menu/VisMol scene smoke
in every GTK/OS cell. Corrected matrix run
[`39264038822`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39264038822)
completed **FAILED** on commit `1100afa`: generic GTK/widget checks passed in
30/30 cells, while the added scene/build checks exposed missing setuptools,
GTK runtime drift and a Linux GL backend mismatch. The follow-up run
[`39265658429`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39265658429)
on `3ece343` completed **17/30 PASS, 13/30 FAIL**. Every non-Linux GTK scene
and widget job passed, including GTK 4.16/4.18 Windows source builds and
macOS arm64 GTK 4.8–4.24. Eight Linux X11 scene jobs failed because startup
selected EGL while the VisMol renderer's PyOpenGL context lookup could not see
GTK's context on hosted runners. Five GTK 4.8/4.10 jobs failed environment
solving because adding Pillow to the conda solve conflicted with the legacy
`jpeg=9e` GTK pin. The 3ece343 attempt moved graphics-only Python dependencies
out of the pinned GTK solve and selected GLX for X11. Locally,
the production menu/VisMol smoke passed twice with GTK 4.14.5, Python 3.12.3,
PyGObject 3.48.2, GLib 2.80.0 and NVIDIA RTX 4060 Ti (22 representation
draws per cycle; clean close); startup/platform regression tests passed **33**.
The next matrix, [`39267210110`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39267210110)
on `0ebd3ef`, completed **27/30 PASS**. All 30 GTK/widget suites and all
Windows/macOS scene runs passed. Three Linux distro GTK 4.16/4.18 scene runs
failed: those builds reject `GDK_DEBUG=gl-glx` and fall back to EGL. On Debian
and Ubuntu, forcing PyOpenGL to GLX then failed to find GTK's current context;
Fedora also exposed an ABI mismatch between its optional
`OpenGL_accelerate` extension and user-site NumPy. Startup now selects EGL for
Linux X11 GTK 4.16/4.18; the distro scene step uses PyOpenGL's supported
ctypes path to avoid the incompatible optional extension. Startup regressions pass **35 tests**. The
native Linux X11/NVIDIA scene test passed both open/render/close cycles with
22 draws per cycle on GTK 4.14.5. Corrected matrix
[`39272229764`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39272229764)
on `467e620` passed **30/30 cells** across Linux, Windows, macOS arm64 and
provisioned Intel macOS for the workflow's GTK 4.8–4.24 coverage. Every cell
passed its GTK/widget smoke and two-cycle EasyHybrid/VisMol scene render and
close checks. EH4-201 is complete for its stated acceptance. The merged `main`
commit `88b5eb5` was revalidated by run
[`39275185493`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39275185493),
which also passed **30/30 cells**; exact per-cell runtime versions are in the
uploaded artifacts. The exact runtime guard follow-up run
[`39292753361`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39292753361)
also passed **30/30**, including the GTK 4.8/4.10 Windows environment creates.
pDynamo3
scientific/runtime tests remain separate and must run in pDynamo3 itself.

**CI provisioning follow-up:** Exact GTK patch pinning and validation are being
added on branch `ci/gtk-exact-runtime-guard`. Its first workflow run
(`39277240441`) failed one GTK 4.24 Linux cell before environment creation:
`setup-micromamba@v3.2.1` could not find the unpinned latest micromamba
`2.9.0-0` Linux binary. The subsequent “Unexpected end of JSON input” was a
cleanup error. This cell did not run GTK tests; the release asset exists, so
the lookup failure was transient. The next run
[`39278528559`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39278528559)
pinned micromamba `2.8.1-1` and passed 28/30 cells. GTK 4.8 and 4.10 Windows
failed before GTK installation: micromamba 2.8.1 rejects the
`--skip-run-link-scripts` flag those cells need (exit 109). `main` passed only
because its environment caches were restored without running `create`; the
exact-version pins changed `create-args` and forced a fresh create. The
workflow now pins micromamba `2.9.0-0`, which accepts the flag; a local
`--platform win-64 --dry-run` solve of both cells succeeds with it. Full run
[`39292753361`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39292753361)
passed **30/30**. Every artifact reports exactly its pinned GTK patch, and
every cell completed two scene open/render/close cycles. The macOS arm64
source cells print their scene evidence only to the job log. The guard is
merged to `main`.

EH4-200's clean-clone audit confirmed that the declared
`casebor/graphics_engine` URL resolves to public `casebor/Vismol`, whose
`vismol_easyhybrid` branch head is `2df3cd96f0b4970d62bd2c4e652faded411549a2`.
This is not established as the vendored tree's base revision. Comparison found
28 differing files among 88 common tracked files, four vendored-only files,
and eight upstream-only files. The project clone reproduced the vendored tree
because Git tracks it as ordinary files (tree mode `040000`), not a gitlink;
`git submodule status --recursive` is empty. A fresh recursive clone built and
imported all seven graphics extensions on Linux x86_64 (Python 3.12.3,
NumPy 1.26.4, Cython 3.0.8). Native matrix run `39485989866` also built the
extensions in all OS/version cells and passed five renderer/pick cycles per
cell. The graphics `LICENSE` says CC BY-NC 4.0 while package metadata carries
an MIT classifier; the root project is GPLv3. EH4-200 remains unchecked pending
authoritative source ancestry and license/ownership review. No graphics source
or submodule pointer was changed, and no conclusion about distribution rights
is made here.

The 2026-10-21 public-history follow-up found candidate commit
[`2827f069`](https://github.com/casebor/Vismol/commit/2827f069355f990e3022fba41aac23239e0cda2e)
with four exact top-level file blob matches. Its source subtree does not match
the original vendored baseline, so the candidate cannot establish the base
revision or authorship. EH4-200 stays partial; see the roadmap evidence log.

EH4-300 moved preferences and transient autosaves out of the installed source
tree into platform-standard per-user config/cache directories. Existing
`.config.json` settings migrate to the user config while the source file stays
intact; calculation logs remain beside project outputs. Focused Linux tests:
**14 passed**; full non-widget suite: **82 passed, 5 skipped**. Native matrix
run [`39176735398`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39176735398)
passed **30/30** on Linux, Windows, macOS arm64 and provisioned Intel macOS
across GTK 4.8–4.24. The path/migration regressions passed in the Linux,
Windows and macOS GTK 4.24 full-suite jobs.

The first full native matrix run
[`39176069763`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39176069763)
passed 28/30 cells. Windows GTK 4.24 and macOS GTK 4.24 each failed only in
the new migration-test assertion: it hard-coded Linux XDG locations instead
of deriving the expected native path. The GTK widget and GL smoke steps passed
in both cells. The assertion now uses the path adapter with each native
platform's temporary user directories; focused and non-widget suites passed
after that correction. The full rerun and Windows GTK 4.16 failed-cell retry
then passed.

A combined local suite run terminated in
a native segmentation fault inside the existing
`test_color_button_keeps_the_gtk_color_button_api` at
`Gtk.Builder.add_from_string`; GTK widget tests are run as a separate,
display-backed workflow step. That crash is not counted as a passing GTK
result or as a path-test failure. After correcting the platform-specific
assertion, native matrix run
[`39176735398`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39176735398)
passed **30/30 jobs** across Linux, Windows, macOS arm64 and provisioned Intel
macOS for GTK 4.8–4.24. The application’s native GTK widget and GL smoke
steps passed throughout; full regression jobs, including path migration,
passed on Linux, Windows and macOS GTK 4.24. Windows GTK 4.16 source-build
provisioning failed once due a GObject Introspection cache permission error
and GCC 16 header parsing; rerunning only that failed cell passed the build,
GTK widget tests and GL smoke. EH4-300 is complete. This does not prove a
VisMol molecular scene render; the next graphics task will exercise the
bundled viewer directly. EH4-200’s upstream ancestry and license mismatch
still block submodule conversion or publishing graphics changes, not local
use of the bundled engine.

**Security cleanup (2026-10-18):** Removed personal host/network identifiers,
user-specific home-directory paths, and literal IP addresses from tracked
files and rewritten branch history. A repository scan found no private key
blocks or credential-bearing URLs. GitHub secret-scanning alerts are not
available for this repository. History rewriting removes these strings from
the reachable refs, but GitHub may retain unreachable cached objects.

**Windows GTK test stability (2026-10-18):** The matrix had executed the
real-display GTK chooser/widget tests twice in one Windows GTK 4.24 job: once
in their dedicated step and again as part of the full suite. Repeated native
`Gtk.FileDialog` cancellation intermittently produced COM-disconnected errors
and a process access violation on the second pass. The workflow now runs the
GTK widget/chooser module once in every OS/GTK cell, then runs the remaining
full regression suite separately. Matrix run `39151909478` passed **30/30**;
Windows GTK 4.24 reported **50 passed, 6 skipped** in the GTK module and
**80 passed, 4 skipped** in the remaining suite.

**EH4-103 acceptance review (2026-10-18):** Added a deterministic native
`Gtk.ColumnView` regression that checks `Gtk.SingleSelection` and
`Gtk.MultiSelection` selection, clearing, and selected row identity. On Linux
x86_64 under Xvfb with GTK 4.14.5, Python 3.12.3, PyGObject 3.48.2, and GLib
2.80.0, the focused test passed and the complete widget-pattern module passed
(50 passed, 7 skipped). Native matrix run `39153435108` passed **30/30** cells
on Linux, Windows, and macOS across GTK 4.8–4.24, including this widget test in
every cell. EH4-103 acceptance is complete; EH4-104 is now complete for
automated/native-matrix acceptance. The next roadmap item is EH4-105.

**EH4-104 input-event regression (2026-10-18):** Centralized GTK scroll-delta
conversion in `src/gtk4_compat.py` and wired the VisMol GL widget to it. The
adapter retains fractional surface deltas until they make a full zoom step,
keeps discrete wheel direction, and ignores non-finite deltas safely. Further
review found that wheel-unit handlers discarded fractional deltas on
non-surface paths. They now accumulate those fractions to whole zoom steps and
reset the accumulator when switching between surface and wheel units. Added
real-widget synthetic `Gtk.GestureClick` and `Gtk.EventControllerKey` signal
coverage and tests for smooth surface and partial wheel deltas. Linux
x86_64/Xvfb, GTK 4.14.5, Python 3.12.3, PyGObject 3.48.2, GLib 2.80.0:
focused scroll tests **2 passed**; prior widget-pattern module **52 passed, 7
skipped**. Native matrix run
[`39170488393`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39170488393)
passed **30/30** across Linux x86_64, Windows x86_64, macOS arm64, and
provisioned Intel macOS for GTK 4.8–4.24. EH4-104 automated/native-matrix
acceptance is complete. Physical macOS trackpad behavior remains **NOT
TESTED** and is recorded separately.

**EH4-105 async lifecycle and playback thread-boundary work (2026-10-18):**
The xTB fragment-charge worker posted progress and completion callbacks that
could still touch a closed window's widgets. Added a per-window generation
guard, suppressed stale progress callbacks, made stale completion release the
running state without touching a closed window, and guarded fragment
build/import while the worker uses the fragment list. The Close button now
uses `Gtk.Window.close()` so cleanup follows `close-request`. The broader
thread audit found both trajectory playback loops read GTK controls and
updated the viewer from Python worker threads. Replaced them with removable
GLib timer callbacks on the main loop. The first matrix playback-test run
failed because importing the GUI packages pulled in NumPy, which is absent
from the GTK-only test environment. Extracted the shared timer/tick logic to
`src/gui/playback.py` and changed the focused tests to avoid those heavyweight
imports. On Linux x86_64/Xvfb, Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 /
GLib 2.80.0, the two focused playback tests now pass (**2 passed**). Initial
playback matrix run [`39172212413`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39172212413)
failed in 28 cells because those tests imported GUI packages that transitively
require NumPy; two Windows crash-diagnostic jobs were canceled after the fix
was verified. The xTB-only commit's matrix passed **30/30**. Expanded the
native GTK smoke to open, render and close
three fresh windows per run; the first attempt exposed automatic application
deregistration between cycles, fixed by holding the application until the
third window closes. Final Linux x86_64/Xvfb smoke: **3/3 lifecycle cycles
passed**, GTK 4.14.5 / GLib 2.80.0 / PyGObject 3.48.2, OpenGL 4.5 Core Profile
on Mesa llvmpipe. The repeated-cycle code was tested in native matrix run
[`39173458935`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39173458935):
**30/30 PASS** across Linux x86_64, Windows x86_64, macOS arm64, and provisioned
Intel macOS, GTK 4.8–4.24. The two focused playback tests and actual GUI module
imports passed locally. EH4-105 automated acceptance is complete. No xTB or
trajectory scientific calculation was run or changed; real trajectory-data
playback was **NOT TESTED**.

**Windows chooser cancellation harness diagnosis (2026-10-18):** The initial
UI Automation attempt in commit `1a88c31` did not operate the Cancel button:
the PowerShell `AutomationElement.FindFirst` query hung and Python raised
`subprocess.TimeoutExpired` after 15 seconds. Available Windows artifacts
from matrix `39158650884` show this same helper timeout on multiple GTK 4.10+
cells; they do not demonstrate an application-side failure. Removed the UIA
helper. The regression now cancels the real `Gtk.FileDialog` through the
application's `ChooserHandle.cancel()` / `Gio.Cancellable` path. Matrix
`39160656186` exposed a stale helper call in Linux chooser configuration
(`TypeError: _dismiss() takes 1 positional argument but 2 were given`) and
the existing COM disconnection in Windows GTK 4.10. A five-second wrapper
lifetime delay did not fix it: matrix `39161457858` still logged
`0x80010108` during the color cancellation test, and GTK 4.14/4.24 Windows
failed the fatal-log guard. Reverted the unproven lifetime workaround.
Application policy now uses GTK's in-process file and color chooser widgets
by default on Windows, avoiding the unstable async COM dialog path; Linux and
macOS continue to use `Gtk.FileDialog`/`Gtk.ColorDialog` when available. The
Windows widget path passed every supported GTK minor in matrix
`39161921877`: **30/30 OS/GTK cells passed**, including Windows GTK 4.8–4.24
widget tests and fatal-exception guards. The hosted native Windows OS COM
dialog path is no longer used by default and is not claimed as supported.

**Recurring Windows chooser crash (2026-10-18):** Matrix `39154336539`
reproduced `0x80010108` in `test_file_chooser_cancel_reports_nothing_once` on
Windows GTK 4.24 while `_wait_for()` ran the GLib main loop after native
`Gtk.FileDialog` cancellation. The earlier CI change prevented a second run
of the widget module but left this test opening five native COM dialogs in a
loop plus a separate configuration-test dialog. Limiting Windows to one real
native cancel and testing the other modes with a fake removed the hard process
failure, but matrix `39155304114` still logged the COM exception on that one
cancel while returning exit code 0. Replacing the posted `WM_COMMAND` with
`BM_CLICK` did not resolve it: matrix `39156076019` also logged the same
exception on GTK 4.24 Windows, despite the job passing. A real Escape key via
`SendInput` made GTK 4.24 pass cleanly, but foreground activation failed on
GTK 4.10/4.12/4.22. Posting Escape keydown/up messages did not activate the
dialog on those runners, leaving its callback empty. `WM_CLOSE` made GTK 4.10
report cancellation but reproduced `0x80010108`, so that route is unsafe.
Attaching to foreground and dialog threads also did not overcome the runner's
activation restriction: failed-job-only retry of run `39157728494` reproduced
the same focus assertion on GTK 4.12 and 4.22. A later UI Automation attempt
timed out while querying the native dialog (`39158650884`); it was removed.
The verified fix is the Windows GTK widget-chooser default described above,
validated in run `39161921877`.
The Windows matrix has a post-test log guard that fails if
`Windows fatal exception` or the corresponding access-violation exit code is
logged, even if pytest itself returned zero. Matrix `39156544333` tested the
Escape approach: Windows GTK 4.24 widget tests passed, but GTK 4.20 and 4.22
failed before sending input because `SetForegroundWindow` was denied. The
helper temporarily attached the test and dialog input threads while focusing
the dialog. The post-test guard covers both conda and MSYS2 Windows jobs. In
matrix `39156735470`, GTK 4.24 Windows completed with
`54 passed, 6 skipped` plus `80 passed, 4 skipped`; its uploaded log has no
`Windows fatal exception`, and the guard passed. GTK 4.20 also passed with the
guard. GTK 4.10, 4.12 and 4.22 still fail only because Windows refuses to
activate the native dialog, even while the input threads are attached; their
fatal-log guards pass. Thus the recurring 4.24 COM exception is resolved by
real Escape input on that tested cell, but the complete Windows GTK matrix is
not green. Run `39157728494` completed with **28/30 pass**; its only failures,
Windows GTK 4.12 and 4.22, recurred on failed-job-only retry. All Linux and
macOS cells passed. Run `39157332484` confirmed that posting Escape key
messages left GTK 4.10/4.12/4.22 native dialogs open and raised an empty-result
assertion; it did not log a fatal exception. Run `39157594361` confirmed
`WM_CLOSE` reports cancellation but logs `0x80010108` on GTK 4.10; the guard
failed the job as intended.

The Windows-only test double initially lacked `Gtk.FileFilter`, so the
mitigation matrix `39155132412` failed on GTK 4.10, 4.12, 4.20 and 4.22 before
any native chooser was opened. That test-only `AttributeError` is fixed. The
corrected matrix `39155304114` passed 30/30 jobs, but its Windows GTK 4.24
artifact still contained the `0x80010108` trace after the single native
cancellation, although pytest completed (54 passed, 6 skipped) and the
workflow exited successfully. Matrix `39156076019` showed the same exception
after changing the dialog action from posted `WM_COMMAND` to `BM_CLICK`; both
approaches leave the native GLib callback failure unresolved. The next test
uses foreground keyboard Escape through `SendInput`. Its result is pending.
Do not regard a green pytest/job status as a fix while the artifact contains
the fatal exception trace.
The first full clean-history GTK matrix log showed an access violation when
the `Gtk.ColorChooserDialog` response handler destroyed its dialog inline on
Windows. The fallback now hides the dialog and defers destruction; targeted
chooser tests pass on Linux GTK 4.14.5. The follow-up full matrix run
`39150184361` on commit `5d3a9db` passed all 30/30 jobs across GTK 4.8–4.24
on Linux, Windows and macOS, including the macOS GTK 4.24 full regression
suite. The merged `main` run `39150864061` completed 30/30 jobs successfully
after rerunning its initially aborted Windows GTK 4.24 full-suite job.

## Topics

1. [Current status and repository provenance](#1-current-status)
2. [Architecture and dependencies](#2-architecture-and-dependencies)
3. [GTK4, Python, and dependency compatibility](#3-gtk4-python-and-dependency-compatibility)
4. [EasyHybrid3 feature parity](#4-easyhybrid3-feature-parity)
5. [Platform and graphics requirements](#5-platform-and-graphics-requirements)
6. [Reproducible test baseline](#6-reproducible-test-baseline)
7. [Contributor workflow](#7-contributor-workflow)
8. [Safe test-data policy](#8-safe-test-data-policy)
9. [Known limitations](#9-known-limitations-and-follow-up)
10. [Platform/version evidence](#10-evidence-and-limitations-by-platformversion)
11. [Preserved detailed topic reports](#11-preserved-topic-reports-and-detailed-evidence)
12. [Graphics engine patch status](#1116-graphics-engine-fixes-patch)

## 1. Current status

- EH4-001 through EH4-005 are complete for their documented inventory,
  baseline, parity, compatibility, and contributor/report deliverables.
  EH4-000 remains incomplete because vendored graphics ancestry and
  contributor/license ownership remain unresolved; the parent remote and
  current repository state are now verified. EH4-100 is complete for its defined
  architecture/import-boundary acceptance: scientific workflows, session
  state, plotting math, and startup OS policy have tested separations; remaining
  pDynamo/GTK and graphics coupling is documented. EH4-101 is complete:
  capability helpers and GTK 4.8/4.12+ Gtk.GLArea fallbacks pass tests. The
  GTK no-display icon-theme critical is classified as GTK/GIO registration
  without a usable Gdk display. EH4-102 is complete: full EasyHybrid
  open/close tests with `G_DEBUG=fatal-criticals` and an actual NVIDIA GL
  context pass on native Linux X11 for GTK 4.8.2, 4.14.5, and 4.24.1; real
  GIO main-menu actions also pass at GTK 4.8.2, 4.14.5, and 4.24.1. Full
  suites pass **54 tests, 5 skipped** in four local environments. The GTK
  4.8.2/Python 3.10 full suite and widget smoke pass, but full pDynamo app
  startup with that Python remains **NOT TESTED** because its available
  pDynamo extensions target Python 3.12. GTK 4.8 `Gtk.AboutDialog` teardown
  separately reproduces an upstream GtkImage finalization critical; see the
  compatibility report and [Debian bug #1041599](https://bugs.debian.org/1041599).
  EH4-103 is complete: dialog, window, chooser, data-view, and selection tests
  pass in native matrix run `39153435108` (30/30). Latest main-branch matrix
  run `39275185493` passes every GTK minor 4.8–4.24 on Linux x86_64, Windows
  x86_64 and macOS arm64, plus GTK 4.8/4.10 on macOS x86_64 (30/30), including
  two real EasyHybrid/VisMol scene cycles per cell. Three GTK defects needed app-side
  handling (Windows 4.8/4.10 WGL pixel format, macOS 4.8/4.10 GL profile,
  GTK 4.16 GLArea teardown). Wayland and physical hardware graphics remain
  **NOT TESTED**. Exact results are recorded in `GTK4_COMPATIBILITY.md`.
- This file is the single consolidated project status and technical report.
  GTK/API/platform validations remain limited to the evidence actually run.
- Recent commits: `8fb0bd6`, `cb5ca10`, `21e49db` (focused Windows WGL
  diagnosis), `ecb93b2` (matched GLib runtime), `b181a50` (architecture/GTK compatibility and native smoke),
  `f69e4c4` (EH4-001), `d8fc403` (EH4-001 evidence),
  `b15fa22` (EH4-002 baseline), `01a8f21` (EH4-003 parity), and `27a25b9`
  (EH4-004 compatibility target). This report is part of the EH4-005 commit.
- The initial verified clean baseline was branch `main`, commit
  `bea94210ed7c23f71d2241f8abe3c849ade18561`.

### 1.1 Provenance and repository record

| Item | Verified information |
|---|---|
| EasyHybrid4 baseline | Historical EH4-000 baseline: `main`, HEAD `bea94210ed7c23f71d2241f8abe3c849ade18561`, clean at that verification. Re-audited 2026-10-20: branch `eh4-000-repository-provenance`, HEAD `0f21022a345e1fda80b2cc18b048e9ed91c1b867` (same as `main` and `origin/main`), clean before this documentation update. Remote `origin`: `https://github.com/Shabirahmad427/EasyHybrid4.git`; 26 local branches, only remote ref `origin/main`, and no tags. The upstream graphics branch head is known, but its relationship to the vendored tree is not. |
| Graphics engine in EasyHybrid4 | `.gitmodules` declares `src/graphics_engine` at `https://github.com/casebor/graphics_engine`, branch `vismol_easyhybrid`; the current index/tree tracks ordinary files, `git submodule status --recursive` is empty, and there is no nested Git metadata. The URL resolves to public `casebor/Vismol`; its branch head is `2df3cd96f0b4970d62bd2c4e652faded411549a2`, but comparison does not establish this as the vendored base revision. |
| EasyHybrid3 comparison checkout | `~/software/EasyHybrid3`, branch `dev`, commit `b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098`; origin is `git@github.com:Shabirahmad427/EasyHybrid3.git`, tracking `origin/dev`, 18 commits ahead at inspection. Its working tree had pre-existing user changes and was not modified. |
| EasyHybrid3 graphics submodule | Declared at `https://github.com/Shabirahmad427/Vismol`, branch `vismol_easyhybrid`; checked-out SHA `6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`. This is comparison evidence only, not the missing EasyHybrid4 revision. |
| Licenses | Root application `LICENSE`: GNU GPL v3. Vendored graphics `src/graphics_engine/LICENSE`: CC BY-NC 4.0. Graphics metadata is inconsistent: `pyproject.toml` includes an MIT classifier, `setup.py` includes a CC BY-NC classifier, and some source files carry GPL notices. Preserve all notices; ownership, file-level licensing, and distribution compatibility require authoritative reconciliation and legal review before packaging. |

**Repository state re-audit (2026-10-21):** the current provenance task
branch was clean at `12ec192857a0d765149c9671f57bf5685b09efef` before this
documentation update. The configured parent remote is `origin` at
`https://github.com/Shabirahmad427/EasyHybrid4.git`; `main` and `origin/main`
are synchronized at `0f21022a345e1fda80b2cc18b048e9ed91c1b867`. The local
repository has 32 task/main branches, only the `origin/main` remote-tracking
ref and no tags. Full branch-name/object-ID inventory is in
[`ARCHITECTURE.md`](ARCHITECTURE.md#repository-state-re-audit-2026-10-21).
The current graphics tree object is `e2dd787a9b1f20d1e47ccba3bd484c45573bef73`
but still does not identify its source commit. `git submodule status --recursive`
is empty in EasyHybrid4. EasyHybrid3 remains at its previously recorded dirty
`dev` checkout; no files there were modified. Parent/reference identities,
licenses and Git state are recorded; exact graphics ancestry and contributor
ownership remain unavailable, so EH4-000 stays unchecked.

The public upstream audit found a historical candidate commit
`2827f069355f990e3022fba41aac23239e0cda2e` in `casebor/Vismol`. Four top-level
blob IDs match exactly (`.gitignore`, `LICENSE`, `README.md`, and
`build_vismol_BCK.py`), but the setup/manifest and source tree differ, and the
vendored tree contains additional files. This narrows a possible historical
relationship but does not establish ancestry or contributor ownership; it is
not acceptable as a source-base SHA claim.

The EasyHybrid4 parent remote and EasyHybrid3 comparison root were reverified
on 2026-10-20. The local EasyHybrid3 checkout is on `dev` at
`b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098`, tracks `origin/dev` and is 18
commits ahead; pre-existing changes to seven tracked paths plus untracked
`bin/` were left untouched. Its graphics submodule resolves to
`6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`. EasyHybrid4 itself has no graphics
gitlink, so that SHA is comparison evidence only. Do not equate the parent
URL, EasyHybrid3 submodule SHA, or declared graphics branch head with proof of
the vendored EasyHybrid4 graphics base revision. The unresolved graphics
ancestry and license/ownership questions still gate graphics publication or
submodule conversion; independent local validation can continue.

## 2. Architecture and dependencies

### 2.1 Application boundaries

- `easyhybrid.py` is the GTK4 application entrypoint. It creates a
  `Gtk.Application`, configures startup, and creates the main window.
- `activate_easyhybrid4.sh` selects the configured Python/pDynamo environment
  and sets the application home. `install.py` checks prerequisites and builds
  the graphics extensions; it may update an active pDynamo environment.
- `src/gui/` contains the main window, GTK widgets, menus, builder, analysis,
  import/setup, and simulation dialogs. The repository has 53 `.glade`
  GtkBuilder resources and no `.ui` resources.
- `src/pdynamo/pDynamo2EasyHybrid/` adapts GUI actions to pDynamo systems,
  simulation, analysis, restraints, and I/O. `src/pdynamo/p_methods/` holds
  numerical workflow implementations. Keep scientific computation separate
  from GTK and operating-system integration. The GTK-free
  `pDynamo2EasyHybrid/state.py` now owns selected session bookkeeping; see
  [`ARCHITECTURE.md`](ARCHITECTURE.md).
- `src/util/`, `src/pdynamo/opls/`, and `src/util/extras/` provide analysis,
  force-field, and external QC adapters.
- `src/graphics_engine/src/vismol/` contains molecular data/models/parsers,
  GTK4 widget integration, OpenGL renderer/shaders, and seven Cython extension
  sources. The graphics directory is vendored source, not a working Git
  submodule in this checkout.
- The plot package retains its existing public widget exports lazily, while
  color interpolation lives in GTK-free `src/util/easyplot/color_math.py`.
  Module responsibilities and remaining couplings are mapped in
  [`ARCHITECTURE.md`](ARCHITECTURE.md).

### 2.2 Runtime dependencies

The root `requirements.txt` lists NumPy, SciPy, PyOpenGL, Cython, freetype-py,
pycairo, PyGObject, and psutil with lower bounds. It has no lock/constraints
file. GTK4, GLib, typelibs, compiler toolchains, pDynamo3, and optional QC
engines are native/external requirements and are not reproducibly installed by
pip alone. The graphics package metadata separately declares NumPy, Cython,
PyOpenGL and Cython build extensions; its Python/platform classifiers do not
establish compatibility of the complete application.

The configured launcher environment provides `pCore`, `pMolecule`,
`pSimulation`, and `pScientific`. These resolve after sourcing the pDynamo
environment script. Other pDynamo versions, Python versions, and native
platforms have not been validated. Optional interfaces include ORCA, xTB,
MOPAC, Sparrow, DFTB+, PySCF/GPU4PySCF and external simulation tools; each has
its own binary and platform constraints.

## 3. GTK4, Python, and dependency compatibility

### Icon-theme critical: diagnosis and evidence (2026-10-17)

The reproduced messages are:

```text
Gtk-CRITICAL: gtk_icon_theme_get_for_display: assertion 'GDK_IS_DISPLAY (display)' failed
Gtk-CRITICAL: gtk_icon_theme_add_resource_path: assertion 'GTK_IS_ICON_THEME (self)' failed
RuntimeError: Gtk couldn't be initialized. Use Gtk.init_check() if you want to handle this case.
```

Both criticals occur in a minimal standalone `Gtk.Application` when
`Gdk.Display.get_default()` is `None` and the process calls
`Gtk.Application.run()`. The stack trace enters `gtk_icon_theme_get_for_display`
from GTK application startup/registration (`gtk_application_startup` on GTK
4.8.2; GTK startup signal and `g_application_register` on 4.14.5), then returns
through PyGObject/libffi. Constructing a `Gtk.ApplicationWindow` in the
activation handler raises the quoted PyGObject `Gtk.py` RuntimeError (line 519
with GTK 4.8.2, line 508 with GTK 4.14.5). `G_DEBUG=fatal-criticals` aborts at
the first critical. This minimal reproducer has no EasyHybrid code, resources,
or icon files, so those are not the source.

On Linux x86_64, GTK 4.8.2 used Python 3.10.22 / PyGObject 3.42.2 / GLib
2.78.0; GTK 4.14.5 used Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0.
When a display is present and queried before application registration, the
real Xvfb smoke opens and closes a Gtk.ApplicationWindow without criticals
under `G_DEBUG=fatal-criticals`; it reports the Adwaita icon theme. The native
X11 display reports Mint-Y-Sand. `GTK_THEME` is unset. A process with no
display has no active icon-theme setting. Thus this is a headless/display
initialization problem in the test environment, not a renderer or missing
runtime-asset problem. The opt-in smoke now checks for a Gdk display before
creating/registering an application and has a no-display regression probe.

The repository scan finds no themed icon names, calls to `Gtk.IconTheme`,
icon-theme resource-path registration, or GResource registration. The 53
Glade files contain 21 explicit `GtkImage.file` references; all paths resolve.
There are 51 custom icon files in `src/gui/icons/`. GTK 4.14.5's Builder tool
validates all 53 Glades. GTK 4.8.2's tool accepts 19 and reports 34 unresolved
signal handler names because the standalone tool has no Python callbacks;
EasyHybrid's GTK4 loader strips these XML signal nodes and installs callbacks
separately. In actual runtime parsing, `load_builder_file()` loads all 53
files successfully on both GTK runtimes.

### 3.1 Selected target

| Item | Target / evidence |
|---|---|
| GTK introspection namespace | `Gtk 4.0`; this is GTK's API namespace, not the installed runtime minor. |
| `GTK_MIN` target | GTK 4.8 runtime. `Gtk 4.0` remains the introspection namespace. GTK 4.8.2 was tested on Linux x86_64 in an isolated environment; other platforms and patches remain **NOT TESTED**. |
| Highest project runtime verified | GTK 4.24.1 with GLib 2.90.0, on Linux x86_64 / native X11. Full application lifecycle and real NVIDIA GL context pass. |
| Current upstream stable | GTK 4.24.1, listed by the [GTK API reference](https://docs.gtk.org/gtk4/) on 2026-10-17. Native Linux X11 tests pass; other OSes and GTK minor series remain **NOT TESTED**. |
| Python target | Python >=3.10 candidate, because source uses evaluated PEP 604 annotations such as `Gtk.Window | None`. Python 3.10.22, 3.12.3, and 3.12.15 have Linux test evidence; native OS/pDynamo compatibility on other versions is **NOT TESTED** and no maximum is approved. |

The intended target is GTK 4.8 through current GTK4 stable, but it is not a
verified interval or a claim for every future GTK4 release. GTK 4.6 and older
are unsupported. Compatibility must be tested for every released GTK 4.x
minor series from 4.8 through the latest stable minor included in the support
claim, on each claimed OS, using an explicitly tested patch runtime for each
series. This does not imply every patch-level build was tested. Record the
exact patch runtime. Every unexecuted
minor/platform pair remains **NOT TESTED** and cannot be inferred from another
minor or OS. GTK 4.8.2, 4.14.5, and 4.24.1 have native Linux X11 evidence as
recorded in [`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md). Every
intermediate minor series and all non-Linux combinations remain **NOT
TESTED**. `Gtk 4.0` remains the introspection namespace used by PyGObject.

### 3.2 Version-sensitive API evidence

- `src/gtk4_compat.py` centralizes capability checks for
  `Gtk.Picture.set_content_fit()` and
  `Gtk.EventControllerScroll.get_unit()`. It selects the picture aspect-ratio
  fallback or discrete scroll behavior when the loaded API shape lacks those
  methods. See [`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md) for branch
  tests, GTK4 `Gtk.Popover` usage, and exact runtime results.
- The pre-4.8 branches above are defensive code only. GTK 4.0 through 4.6
  remain outside the supported runtime range and the installer rejects them;
  retaining a fallback does not make those versions supported.
- The source scan found no `Gtk.FileDialog` or `Gtk.AlertDialog` usage. Both
  arrived in GTK 4.10; the application uses existing asynchronous chooser and
  message-window helpers. See [`Gtk.FileDialog`](https://docs.gtk.org/gtk4/class.FileDialog.html).
- The installer checks the loaded GTK version, but it does not statically
  validate every Python symbol or GtkBuilder property. An exhaustive,
  version-aware deprecation audit remains EH4-106.

### 3.3 Dependency-resolution policy

- GTK, GLib and typelibs are native OS dependencies, not pip packages. Install
  them natively on each test runner and record loaded runtime versions.
- Retain explicit lower bounds in `requirements.txt` and publish resolved
  versions from CI. Add Python/platform constraints when a reproducible
  incompatibility or dependency conflict is demonstrated.
- Validate pDynamo and optional scientific binaries per OS/Python combination;
  do not infer them from a successful graphics extension build.

## 4. EasyHybrid3 feature parity

Statuses apply to the named scope only: **WORKING** means a narrow
non-GUI behavior has regression-test evidence; **BROKEN** means a known
diagnostic/failure exists; **UNIMPLEMENTED** means no corresponding
EasyHybrid4 implementation was found; **UNTESTED** means source is present or
migration is claimed but end-to-end behavior is not demonstrated.

| Workflow | EasyHybrid4 status | Evidence / remaining work |
|---|---|---|
| Atom/bond mutation and bond-order perception logic | **WORKING (logic slice only)** | 23 tests cover bond edits, valence/order handling, representations' bookkeeping, and frame-specific dynamic bonds. No GTK UI, GL rendering, or pDynamo sync claim. |
| Interactive Builder (create/edit, undo, charges/hydrogens, fragments, structures, solvation, DYFF/OPLS) | **PARTIAL** | `tests/test_atom_ops_bonds.py` exercises coordinate/add-bonded-atom/undo restoration plus atom multi-select/toggle/clear and numeric distance/angle measurements (15 tests pass). Selection-clear now resets atom selection flags. The opt-in full-app smoke now passes one native Linux X11/XTest `.easy` save/reload cycle with real pDynamo3 and checks the restored system and VisMol object; it also verifies GTK row references are restored after successful and injected-failure writes. Builder UI workflows, persistence of edited structures, Windows/macOS and other GTK minors remain untested. |
| VisMol viewer, picking, selection, representations, camera and playback | **PARTIAL** | Real GTK GLArea, production renderer, picking, representation/export/resize checks pass in native matrix run `39485989866`; component matrix picking calls GTK handlers with synthetic coordinates. Full app passed focused native Linux, Windows GTK 4.8/4.10, and macOS GTK 4.24.1 checks. Local Linux X11/XTest full-app picking passes five cycles; hosted full-matrix confirmation is pending. Windows/macOS native OS input, physical GPU, Retina/trackpad, Wayland, and real trajectory playback remain **NOT TESTED**. |
| GTK widget startup/lifecycle | **BROKEN (diagnostic observed)** | User-provided launch output showed two `gtk_box_remove` parent assertion critical messages. Visible impact and responsible removal path are unknown. |
| System import, force-field assignment, merge/prune, trajectory import, `.easy` save/load | **PARTIAL** | Project writes now use atomic replacement and a versioned payload; readers accept legacy unversioned files and reject unsupported future versions before application restart. Five file-level regressions pass, including corrupt-read and simulated-write failure preservation. Full session/system/camera/vobject round trips and historical project migrations remain untested. |
| System import, force-field assignment, merge/prune, trajectory import, `.easy` save/load | **PARTIAL** | The opt-in full-app regression imports a generated three-atom water system and now saves/reloads it through the production `.easy` serializer and loader on Linux X11 (GTK 4.14.5), verifying one pDynamo system and one 3-atom VisMol object. Other project contents, trajectory import, edited-structure persistence, Windows/macOS and other GTK minors remain **NOT TESTED**. |
| MM/QC/QC-MM setup and calculations | **PARTIAL** | The opt-in scientific suite now checks DYFF energy/minimization, AM1 single-point energy and the production EasyHybrid MNDO/QC-MM setup against pDynamo's water-dimer reference. Cross-platform numerical comparison and broader systems/engines remain untested. |
| System import, force-field assignment, merge/prune, trajectory import, `.easy` save/load | **UNTESTED** | Matching dialogs/session/serialization code exists; no representative import or project round-trip fixture was run. |
| MM/QC/QC-MM setup and calculations | **PARTIAL** | `tests/test_pdynamo_mm_workflow.py` covers the 3-atom water DYFF energy/minimization reference (initial `5.104425761412759`, minimized `0.0010421253750697622`), AM1/MNDO single-point reference (`-247.65607705020375`, coordinates unchanged within `1e-12 Å`), and EasyHybrid's production MNDO/QC-MM setup on a water dimer (energy `-258.5075262422 kJ/mol`, 3 selected QC atoms, neutral singlet, `NBModelCutOff`, gradient deviation <=`1e-3`). The local headless scientific runner passed **26 tests** with pDynamo3. Cross-platform numerical comparison and broader systems/engines remain **NOT TESTED**. |
| Single point, optimization, MD, normal modes, transition-state search | **UNTESTED** | GTK4 windows and dispatch are present; no sample scientific output comparison. |
| PES scans, umbrella sampling, WHAM, NEB/reaction paths, CPR | **PARTIAL** | Opt-in `tests/test_reaction_coordinate_workflow.py` verifies simple/chained/paired distances with fake and compiled pDynamo3 coordinates, and compiles generated script text/checks class dispatch for relaxed/advanced scans, umbrella sampling and NEB (**4 passed**). NEB generated scripts now load exported coordinate pickle files. Actual scan/path/umbrella/WHAM calculations, exported script execution, and native GTK export UI remain untested. |
| RDF, density, RMSD/RMSF, Ramachandran, surfaces, trajectory analysis | **UNTESTED** | Modules exist; no representative analysis-result fixtures were run. |
| Infrared spectrum GUI | **UNIMPLEMENTED** | No matching EasyHybrid4 spectrum window/menu workflow was found. |
| AutoDock Vina / AutoDock-GPU setup-run-import | **UNIMPLEMENTED** | EasyHybrid3 report and dialogs identify both; no EasyHybrid4 front ends/actions were found. |
| NAMD/SMD, AMBER `tleap`, Packmol, Antechamber preparation dialogs | **UNIMPLEMENTED** | EasyHybrid3 front ends are absent. Packmol-style solvent placement is not a replacement for these dialogs. |
| Scientific system/script exports and simulation output files | **UNTESTED** | Export code exists, but schemas/restarts/numerical outputs lack fixture comparisons. |
| Process manager, job lifecycle, recent files, project/session management | **PARTIAL** | Two helper regressions verify process-tree SIGTERM dispatch and nonblocking GLib abort polling. Live job execution/cancellation, exception propagation, restart lifecycle and cross-platform behavior remain untested. |

EasyHybrid3's detailed implementation report was inspected read-only at
`~/software/EasyHybrid3/docs/EASYHYBRID3_IMPLEMENTATION_REPORT.md`.
The comparison suite result is recorded below. Preserve all scientific
workflows; this status report does not authorize dropping an incomplete
feature.

## 5. Platform and graphics requirements

### 5.1 Platform matrix

| Platform/backend | Intended target | Verified status |
|---|---|---|
| Linux x86_64, GTK 4.14.5 | GTK4/PyGObject, Python, pDynamo3, OpenGL 3.3+ | 23 non-GUI tests passed and the graphics extensions built/imported. Live UI, X11 window construction, and real GL: **NOT TESTED**. |
| Linux Wayland | Shared GTK4 application | **NOT TESTED**. |
| Other Linux architectures/distributions | Native GTK/pDynamo dependencies | **NOT TESTED**. |
| Windows x64 | Native GTK4, pDynamo3, compiler and OpenGL 3.3+ context | **NOT TESTED**; Bash launcher/build path needs native Windows handling. |
| macOS arm64/x86_64 | Native GTK4, pDynamo3, compiler and OpenGL 3.3+ core context | **NOT TESTED**; no native runner/device used. |

The VisMol widget explicitly requests OpenGL 3.3+ and exits with diagnostics
if Gtk.GLArea cannot create the context. No renderer/vendor was captured. GTK
and GL context negotiation, dialogs, fonts, scaling, and input semantics must
be checked on every native OS. The macOS trackpad scroll-unit path has a
GTK 4.8 feature check; real trackpad behavior is untested.

### 5.2 Native CI architecture

`.github/workflows/native-gtk-matrix.yml` uses native Linux, Windows and macOS
GitHub-hosted runners for dependency provisioning, extension builds, display-
free scientific tests, real GTK/GL checks and uploaded runtime evidence. PRs
run the full supported GTK-version matrix. The plan job skips a `main` push
when its tree is already covered by the merged PR, or when only Markdown
changed; it does not skip code pushes. EH4-500 compiler-output caching for
macOS GTK source builds and Windows MSYS2 GTK 4.16/4.18 builds is merged in
PR #13. Focused cold/warm runs `40126461301` and `40127443099` passed all six
source-build cells; warm artifacts show 99.46–99.62% ccache hits and GTK
build-step reductions of 78–91%. The full 30-cell PR matrix passed in
`40129629714`; all six compiler caches are now available in main scope. The
cache excludes installed GTK prefixes.

The workflow does not replace dated manual checks for macOS Retina/trackpad or
physical GPUs; those remain separate native-hardware evidence.

## 6. Reproducible test baseline

### 6.1 Environment

| Item | Observed |
|---|---|
| OS/kernel/architecture | Linux x86_64, kernel `6.8.0-147-generic`, Ubuntu userspace/glibc 2.39 |
| Python | 3.12.3 |
| PyGObject / GTK / GLib | 3.48.2 / 4.14.5 / 2.80.0 |
| pytest | 9.1.1 |
| NumPy / SciPy | 1.26.4 / 1.11.4 |
| Cython / PyOpenGL / psutil | 3.0.8 / 3.1.7 / 5.9.8 |
| Compiler | GCC 12.4.0 |
| Display / renderer | **NOT TESTED** for the baseline |

The launcher-sourced pDynamo environment resolves `pCore`, `pMolecule`,
`pSimulation`, and `pScientific`.

### 6.2 Commands and outcomes

Existing EasyHybrid4 tests:

```sh
~/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/
```

Result: **PASS**, 23 passed in 0.02 seconds.

EasyHybrid3 reference suite:

```sh
~/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider ~/software/EasyHybrid3/tests/
```

Result: **PASS**, 23 passed, 4 skipped in 0.08 seconds.

Graphics extension build (isolated source copy, no repository mutation):

```sh
tmpdir=$(mktemp -d)
cp -a src/graphics_engine "$tmpdir/graphics_engine"
cd "$tmpdir/graphics_engine"
~/software/envs/easyhybrid312/bin/python setup.py build_ext --inplace
PYTHONPATH="$tmpdir/graphics_engine/src" \
  ~/software/envs/easyhybrid312/bin/python -c 'import vismol.utils.matrix_operations, vismol.utils.PDBFiles, vismol.utils.GROFiles, vismol.utils.c_distances, vismol.utils.selectors, vismol.utils.mesh_decimation, vismol.utils.mesh_smoothing; print("7 graphics extension imports: PASS")'
```

Result: **PASS**, seven compiled modules and seven imports. GCC emitted NumPy
deprecated C API and setuptools license/metadata warnings.

An isolated `pip install --target` probe **FAILED** during PEP 517 metadata
generation with `ModuleNotFoundError: No module named 'src'`. The documented
`build_ext --inplace` route succeeds. The full interactive `install.py` was
**NOT RUN** because it can install packages or modify the configured pDynamo
environment.

### 6.3 Coverage boundaries

Tests use `tests/conftest.py` to create generated in-memory atoms, bonds, and
zero-coordinate frames. They do not validate OpenGL rendering, pDynamo
synchronization, scientific calculations, project/export round trips, or
cross-platform behavior. EH4-100 added
`tests/test_md_analysis.py` for RMSF, RDF minimum-image and self-selection,
periodic-box density, zero-volume failure, and GTK-free import, plus
`tests/test_gtk_version.py` for rejecting GTK 4.6 and accepting GTK 4.8+.
EH4-100 implementation adds import-boundary, pDynamo workflow, session-state,
Cairo drawing, startup OS-policy, and GTK capability-branch regression tests.
The standard test environment reports **47 passed, 2 skipped** (the two
pDynamo integration checks are skipped because that Python process has no
configured pDynamo). With the configured pDynamo3 environment loaded, the complete suite
reports **49 passed**. On Linux x86_64 with Python 3.12.3 / PyGObject 3.48.2 /
GTK 4.14.5 / GLib 2.80.0, under Xvfb/X11 a real GTK `Window`, `Picture`, EasyPlot
`Canvas`, and `Gtk.Popover` were constructed, presented, and closed. All 53
Glade resources passed `gtk4-builder-tool validate` under the same virtual
display. An initial full launcher run failed before splash construction with
GTK display/icon-theme criticals. A later run under Xvfb/X11 produced a visible
application window and remained free of GTK critical warnings with
`G_DEBUG=fatal-criticals`; KL-012 records both results. No GL
renderer/context was verified in that earlier EH4-100 coverage run. Current
native GTK4 window/GL smoke results from GitHub Actions are listed below;
Wayland remains **NOT TESTED**; all GTK 4.8–4.24 matrix cells now run.

Compatibility planning update, 2026-10-17: GTK's current API reference reports
GTK 4.24.1 ([GTK API reference](https://docs.gtk.org/gtk4/)), replacing the
older 4.22.5 latest-stable target recorded in earlier evidence. The
[conda-forge GTK package](https://anaconda.org/conda-forge/gtk4) lists Linux,
Windows x64, macOS Intel, and macOS arm64 support in aggregate. This does not
establish that every historical GTK minor is published for each platform.
Native CI must install an exact patch release and assert the loaded GTK major,
minor, and micro versions; package resolution alone is not evidence that the
requested runtime was used. Wordcraft's separation of headless checks, Linux
virtual-display UI jobs, and native Windows/macOS UI jobs is a useful CI design
reference. At the time of this initial CI-planning note, EasyHybrid4 had no
native runner results; see the current run and exact package-availability
audit below.

### GTK 4.16/4.18 package-resolution failures (2026-10-17)

The failed setup cells were audited against conda-forge's GTK4 package API,
including exact artifact platform tags. GTK 4.16 and 4.18 do not appear in its
published version list, so the Linux and Windows solver failures and macOS
4.16/4.18 failures indicate a provider gap, not that GTK itself is absent on
those operating systems. Linux distribution packages for GTK 4.16.x and
4.18.x exist. Add Linux checks through an exact system runtime or another
pinned provider instead of dropping those GTK series from Linux testing.

The macOS arm64 GTK 4.8/4.10 failures have a different cause: conda-forge has
GTK 4.8.2 and 4.10.1 artifacts for Intel `osx-64`, but no corresponding
`osx-arm64` artifacts. This does not establish that those series cannot run
on Apple Silicon; they remain **NOT TESTED** there. Windows/macOS 4.16/4.18
exact native runtime tests likewise remain **NOT TESTED**. No source build or
alternate package-manager result is inferred. The workflow exclusions mean
“no exact artifact from the current conda-forge provider,” not “GTK
unavailable on this platform.” See
[`GTK4_COMPATIBILITY.md`](GTK4_COMPATIBILITY.md#gtk-binary-availability-audit-2026-10-17).

The GTK 4.8/4.10 Windows setup stall was isolated in run `39065269579` by
skipping conda link scripts only in those cells and invoking the pixbuf cache
helper with a 60-second timeout. The helper exited successfully, but
GdkPixbuf import failed with `gdk_pixbuf-2.0-0.dll: The specified procedure
could not be found`, followed by a PyGObject assertion. Pinning GLib build
`2.82.2=h7025463_0`, alone or with `libiconv=1.17`, did not fix the import
(`39065624007`, `39065795981`). A GdkPixbuf 2.44.8 override was unsatisfiable
because of GTK 4.8's JPEG and GTK 4.10's libtiff constraints
(`39065992963`). The upstream conda-forge GLib issue identifies the bad
`2.78.4 h55e6270_1` build; metadata confirms matching `libglib 2.78.4
h16e383f_0` and `glib-tools 2.78.4 h12be248_0` builds. The workflow now
tests those exact builds plus iconv 1.17 only for Windows GTK 4.8/4.10,
keeping the cache-script workaround. GdkPixbuf import now passes in both
cells, but their GTK GLArea smoke fails; see the focused WGL results in
`GTK4_COMPATIBILITY.md`. A separate diagnostic bug in `39065500734` queried nonexistent
`GdkPixbuf.MAJOR_VERSION` and caused Linux/macOS jobs to fail before smoke;
reporting now uses the typelib namespace (`2.0`), and later Linux matrix
smoke jobs passed again.

Run `39066895345` completed with 17 successes and only two failures: GTK
4.8/4.10 on Windows. Both import GTK/GdkPixbuf and load the app-local Mesa
26.2.4 DLLs. The latest GTK 4.10.1 job also creates a basic Tk-window WGL
context reporting OpenGL 4.6 Compatibility Profile and
`llvmpipe (LLVM 23.1.2, 256 bits)`, but the GTK window/Gio/GLArea smoke still
fails with `No GL implementation is available`. A basic compatibility
context does not verify GTK's requested profile, pixel format, or sharing
behavior. GTK 4.10's source emits this generic error when dummy pixel-format
or context setup fails, when initial `wglMakeCurrent` fails, or when GL is
below 2 without `GL_ARB_shader_objects`; CI has not distinguished those
branches. GTK 4.12.1 passes the smoke on the same runner and Mesa driver. Upstream sources show a
different WGL bootstrap-window strategy in GTK 4.12, making an older GDK
Win32 bootstrap incompatibility plausible, but not proven. The failure is
before EasyHybrid's molecular graphics code; physical Windows hardware
remains **NOT TESTED**. The `GDK_DEBUG=opengl` diagnostic was removed because
conda GTK release builds omit `G_ENABLE_DEBUG`.

### GTK4 widget-pattern portability (EH4-103, 2026-10-18)

A GTK 4.8 floor probe found that `Gtk.PropertyExpression.new` cannot be
called from Python on GTK 4.8 (PyGObject 3.42–3.46), which broke 43
dropdown/sorter call sites in about 25 windows on the declared minimum. All
were replaced with expression-free adapters in `src/gtk4_compat.py`;
`Gtk.ComboBoxText` uses moved to `src/gui/choice_dropdown.py` with identical
scientific option IDs; and the PES Actions button's GTK3 `popup_at_widget`
crash was fixed. GTK 4.20+ also auto-selects empty dropdowns, so no code
relies on an empty selection. Details and the per-minor probe are in
`GTK4_COMPATIBILITY.md`. Native matrix run `39082144669` passed the new
widget tests in all 30 cells (Linux, Windows, macOS; GTK 4.8–4.24).
Message and question dialogs then moved to the portable
`src/gui/message_dialogs.py` (plain `Gtk.Window`; `Gtk.AlertDialog` is absent
on GTK 4.8). Custom `Gtk.Dialog` windows then moved to the portable
`src/gui/response_dialog.py`, and Builder `GtkDialog`s became `GtkWindow`s.
File, folder and colour choosers then moved to `src/gui/file_dialogs.py`
(`Gtk.FileDialog`/`Gtk.ColorDialog` on GTK 4.10+, the GTK 4.8 dialogs
otherwise). This fixed four save dialogs that raised `AttributeError`
(`set_do_overwrite_confirmation`, absent in GTK4) and an app-wide GTK 4.8
abort: a GtkImage finalization critical raised during Python garbage
collection inside PyGObject's warning handler is a recursive, always-fatal
GLib message. On GTK < 4.10 the app now prints those messages from GLib's C
handler. `Gtk.ColorButton` (a widget, mostly in Builder files) remains.

## 7. Contributor workflow

Windows follow-up: `39067404621` reproduced the GTK 4.8/4.10 failures.
The focused native trace in `39067671751` found identical pixel-format state
loss in both runtimes: format 75 was set successfully, then read as 0 on the
same HDC across repeated Mesa DLL loads. The real GTK smoke now optionally
retains the CI-provided Mesa library before GTK import. The option is set
only on Windows 4.8/4.10 CI cells; native rerun results are pending.
`tests/diagnostics/trace_windows_wgl.py` (since removed) traced the actual GTK process's
pixel-format and WGL calls using an optional, pinned Frida CI dependency.
It logs native return values, error codes, and DLL paths without changing
them. The separate uninstrumented smoke remains required; diagnostic failure
cannot turn a failing GTK smoke green. Native trace results are pending;
local Python compilation and `git diff --check` passed.

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

1. Read root `AGENTS.md` and [`ROADMAP.md`](ROADMAP.md) completely before a
   coding session. Work the first eligible task and do not bypass phase gates.
2. Use an isolated Python environment with root `requirements.txt`, native
   GTK4/PyGObject, and a separately configured pDynamo3 environment. There is
   no universal installer for all operating systems.
3. Run `python -m pytest -q -p no:cacheprovider tests/` in the configured
   environment. These tests do not need a display or actual GL context.
4. The normal VisMol build is `cd src/graphics_engine && bash install.sh`;
   it writes generated C/native binaries into the source tree. For a clean
   baseline, build a temporary copy using the command above.
5. Avoid running the interactive installer as a test; inspect its package and
   pDynamo modifications first.
6. Record OS/architecture, Python/PyGObject/GTK/GLib, test commands/raw
   outcomes, graphics metadata when tested, and every unavailable platform.

## 8. Safe test-data policy

- Prefer the smallest synthetic molecular graph and in-memory coordinates.
- Use `tmp_path`/temporary directories for projects, scripts, trajectories,
  logs and exports; tests must not write to a user's project, home directory,
  or pDynamo data tree.
- Keep fixtures deterministic; record atom ordering, units, random seeds, and
  scientific tolerances. Avoid large trajectories and production databases.
- If a real structure is necessary, use a small redistributable public example
  with source URL, license, attribution and date. Remove confidential/project
  metadata. If rights are unclear, do not add the file.
- Never commit research data, private structures, serialized projects without
  provenance review, credentials, or machine-specific configuration.
- Check `git status` after tests and keep generated data in temporary/ignored
  locations.

## 9. Known limitations and follow-up

| ID | Limitation | Evidence | Follow-up |
|---|---|---|---|
| KL-001 | The vendored graphics source SHA and contributor/license ownership are unknown. | EasyHybrid4 `origin` is verified as `https://github.com/Shabirahmad427/EasyHybrid4.git`; graphics directory is ordinary tracked files despite stale `.gitmodules` metadata. The EasyHybrid3 reference and its graphics SHA are recorded but do not prove EasyHybrid4 ancestry. Graphics license/metadata notices conflict. | EH4-000/EH4-200 and EH4-602 after authoritative source/ownership reconciliation. |
| KL-002 | GTK range target is not fully validated. | GTK 4.8 minimum and stable GTK 4.22.5 **NOT TESTED**; local GTK 4.14.5 only. GTK 4.6 is unsupported. | EH4-501/502/503. |
| KL-003 | Native cross-platform support unknown. | Windows, macOS, Wayland and other distributions **NOT TESTED**; launcher/build use Bash. | EH4-300–304 and EH4-500 onward. |
| KL-004 | Native graphics path differs by GTK runtime; GTK 4.8 full-app close still unverified. | Native X11/NVIDIA Gtk.GLArea passes on GTK 4.8.2 and GTK 4.14.5 with `GDK_DEBUG=gl-glx`; GTK 4.14.5's default/EGL path fails to create a context. Full GTK 4.14.5 app opens/closes under explicit GLX selection. GTK 4.8 full app is blocked by the Python/pDynamo extension ABI mismatch. Xvfb/llvmpipe passes separately. | EH4-102 and EH4-201–205/EH4-502/503. |
| KL-005 | GTK critical removal warning during startup. | User provided two `gtk_box_remove` parent assertion messages; impact/path unknown. | Reproduce and isolate; EH4-102/105. |
| KL-006 | Generic graphics-engine pip installation fails. | Isolated PEP 517 metadata failed `ModuleNotFoundError: No module named 'src'`; direct Cython build/import passes. | EH4-200 or EH4-303. |
| KL-007 | pDynamo validated in one environment only. | Linux Python 3.12.3 resolves core packages. | EH4-004/500/504. |
| KL-008 | Feature parity is incomplete/unverified. | See Section 4: docking, several external setup dialogs, and IR GUI are absent; others untested. | Separate parity tasks with scientific regression evidence. |
| KL-009 | Builder-tool validation behavior differs across GTK minors. | GTK 4.14.5 tool validates 53/53 Glades; GTK 4.8.2 tool validates 19/53 and reports 34 unresolved signal names. EasyHybrid's loader successfully parses 53/53 using both runtimes. | EH4-102/501/502; retain the callback-aware loader validation. |
| KL-010 | Removed/deprecated API inventory incomplete. | A targeted scan found guarded GTK 4.8 APIs; no exhaustive audit. | EH4-106. |
| KL-012 | Icon-theme critical appears if GTK application registration occurs with no Gdk display. | Minimal app reproduces both icon-theme criticals and Gtk.py initialization exception with `Gdk.Display.get_default() is None` under GTK 4.8.2 and 4.14.5. GDB traces the call to GTK/GIO application startup. Guarded real-display `Gtk.ApplicationWindow` smoke passes on both versions. No EasyHybrid icon/resource defect found. | Keep GTK GUI test setup display-aware; EH4-102 orderly full-app startup/close remains in progress. |

## 10. Evidence and limitations by platform/version

| Target | Result |
|---|---|
| Linux x86_64, GTK 4.8.2 / GLib 2.90.0 / PyGObject 3.58.1 / Python 3.12.15 | Full suite **54 passed, 5 skipped**. Updated standalone GTK window/menu-action/GLArea smoke: **PASS** with `G_DEBUG=fatal-criticals`, OpenGL 3.3.0 on NVIDIA RTX 4060 Ti. Full EasyHybrid open/close **PASS** with fatal criticals. Startup selected EGL for PyOpenGL; no external backend overrides. GTK 4.8 AboutDialog finalization critical is a separate upstream behavior (see compatibility report). |
| Linux x86_64, GTK 4.8.2 / GLib 2.78.0 / PyGObject 3.42.2 / Python 3.10.22 | Full suite **54 passed, 5 skipped** after the seven graphics extensions were built in a temporary source copy. Native window/menu-action smoke **PASS**. Full application/pDynamo lifecycle **NOT TESTED** because the available pDynamo binary extensions target Python 3.12. |
| Linux x86_64, GTK 4.14.5 / GLib 2.80.0 / PyGObject 3.48.2 / Python 3.12.3 | Latest full suite with real-display GTK/OpenGL smoke enabled: **55 passed, 4 skipped**. Standalone window/menu-action/GLArea smoke: **PASS** with fatal criticals; actual GL context OpenGL 4.6.0 on NVIDIA RTX 4060 Ti. Full EasyHybrid open/close **PASS** in the prior complete lifecycle run. Startup selected EGL and `gl-prefer-gl`; no external backend overrides. GTK 4.14's default standalone X11/EGL context failure from earlier tests is historical; application startup setup resolves the current full-app path. |
| Linux x86_64, GTK 4.24.1 / GLib 2.90.0 / PyGObject 3.58.1 / Python 3.12.15 | Full suite **54 passed, 5 skipped**. Updated standalone window/menu-action/GLArea smoke: **PASS** with fatal criticals, OpenGL 4.6.0 on NVIDIA RTX 4060 Ti. Full EasyHybrid open/close **PASS** with fatal criticals. Startup selected EGL and `gl-prefer-gl`; no external overrides. |
| Linux GTK no-display diagnostic | **REPRODUCED / CLASSIFIED** on GTK 4.8.2 and 4.14.5 with `G_DEBUG=fatal-criticals`; standalone GTK app and GDB stack identify missing display at GTK/GIO registration. Not an EasyHybrid icon/resource defect. |
| GTK 4.24.1 current stable | **PASS** on native Linux X11 as listed above |
| GTK 4.8–4.24 native GTK/widget and EasyHybrid scene matrix | **PASS, 30/30 cells** in main run `39275185493`, including Windows GTK 4.8/4.10 WGL fix and two molecular-scene render/close cycles per cell. Exact runtimes are listed in `docs/GTK4_COMPATIBILITY.md`. |
| GTK 4.16 and 4.18 | **PASS** on Linux (Ubuntu 24.10, Fedora 41, Debian 13), Windows (MSYS2 source) and macOS arm64 (GNOME source), run `39275185493`. Linux distro scene uses EGL; Fedora uses PyOpenGL ctypes due optional accelerator ABI mismatch. |
| Linux x86_64 / X11 live UI and GL | Local NVIDIA scene lifecycle **PASS** at GTK 4.8.2, 4.14.5, and 4.24.1; all GTK 4.8–4.24 minors also pass hosted Xvfb/llvmpipe scene and widget coverage in the native matrix. |
| EH4-302 hosted display evidence (PR #16/#17; runs 40156091773/40161896666) | **PASS:** both native matrices 31/31; PR #17 artifacts audited 30/30, with five display/native-pointer cycles and five scene cycles per cell. All hosted monitor-fit checks pass at scale 1. Local Linux scale-2 fit passes at GTK 4.8.2 and 4.24.1. Physical Retina/multi-monitor and Wayland remain **NOT TESTED**. |
| Linux Wayland UI/GL/input/scaling | **NOT TESTED** |
| Windows GTK4/Python/GL and EasyHybrid scene | **PASS** for GTK 4.8–4.24 on hosted software WGL (run `39275185493`). Physical GPUs and packaging **NOT TESTED**. |
| macOS arm64 GTK4/Python/GL and EasyHybrid scene | **PASS** for GTK 4.8–4.24 (4.8/4.10/4.16/4.18 built from GNOME source), run `39275185493`. Trackpad/Retina/hardware-driver coverage **NOT TESTED**. |
| macOS x86_64 GTK4/Python/GL | **PASS** for GTK 4.8.2/4.10.1 (run `39275185493`); other minors **NOT TESTED** |

No Linux pass is evidence of Windows/macOS or GTK-minimum compatibility.
Update this consolidated report and the task evidence in `ROADMAP.md` as new
results become available.


# 11. Preserved topic reports and detailed evidence

The sections below retain the prior topic reports in one place. Their original scope and dates remain in their text; dated machine-specific and EasyHybrid3-only results are historical evidence, not claims about current EasyHybrid4 support. Sections 1–10 above are the consolidated current status.


## 11.1 Repository architecture and baseline

## Baseline record

Recorded 2026-10-17 UTC while starting EH4-000. The checked-out EasyHybrid4
directory is `~/software/EasyHybrid4`.

| Item | Evidence |
|---|---|
| EasyHybrid4 Git metadata | Reverified directly: repository root `~/software/EasyHybrid4`, branch `main`, HEAD `bea94210ed7c23f71d2241f8abe3c849ade18561`, clean working tree, no tags, and **no remotes configured**. The canonical EasyHybrid4 fork URL cannot be identified from this clone. |
| EasyHybrid4 declared graphics submodule | `.gitmodules` declares `src/graphics_engine`, URL `https://github.com/casebor/graphics_engine`, branch `vismol_easyhybrid`. However, `git ls-tree HEAD src/graphics_engine` reports mode `040000` (ordinary tree), the index lists files individually, `git submodule status --recursive` is empty, and there is no nested `.git` or `.gitmodules`. The entry is stale: the source is vendored, not a resolvable submodule. No upstream graphics revision is present in Git metadata. |
| EasyHybrid3 reference checkout | `~/software/EasyHybrid3`, branch `dev`, commit `b2113b8c11ba3dff51b93fd2f52fc1a7dc9d1098` (2026-10-16). Tracking `origin/dev`, 18 commits ahead. Remote `origin`: `git@github.com:Shabirahmad427/EasyHybrid3.git`. No tags were listed. Working tree is dirty: modified `docs/GPU4PySCF.md`, six source files, and untracked `bin/`. These user changes were left untouched. |
| EasyHybrid3 declared graphics submodule | `.gitmodules` names `src/graphics_engine`, URL `https://github.com/Shabirahmad427/Vismol`, branch `vismol_easyhybrid`. Resolved SHA `6a25a2eaf27c7627dba171104fc7fc8a4c9295fd`; the submodule checkout is detached. Its `origin` is the same HTTPS URL. No submodule tags were listed. |
| Nested graphics submodules | No nested `.gitmodules` or `.git` entries were found under the vendored graphics-engine directory. |
| Licenses | EasyHybrid4 root `LICENSE` is GNU GPL version 3. `src/graphics_engine/LICENSE` is Creative Commons Attribution-NonCommercial 4.0 International. Preserve both notices; distribution compatibility needs a deliberate legal review before packaging. |
| Runtime observed | Linux x86_64, kernel `6.8.0-147-generic`; EasyHybrid Python `3.12.3`, PyGObject `3.48.2`, GTK `4.14.5`, GLib `2.80.0`. Display backend and OpenGL renderer were not measured for this baseline. |
| Existing test/CI inventory | `tests/` contains `test_bond_order_perception.py` and `test_atom_ops_bonds.py`; these avoid GTK/display/OpenGL. No CI workflow directory was present in this checkout. The GUI has 53 `.glade` files and no `.ui` files. |

The first inspection in the prior session saw an empty `.git/` placeholder.
That observation was superseded when the repository metadata became available;
the direct Git results above are the current baseline.

## Layout and boundaries observed

- `easyhybrid.py` is the GTK4 application entry point; `activate_easyhybrid4.sh`
  selects the configured pDynamo Python environment and sets the application
  home.
- `install.py`, `requirements.txt`, and `requirements-dev.txt` manage
  prerequisites and Python packages. The current installer checks for GTK
  4.0+, but that is not yet a justified compatibility interval.
- `src/gui/` contains the main window, GTK widgets, workflow dialogs, and
  GtkBuilder `.glade` resources. `src/gtk4_compat.py` centralizes a fallback
  value for GTK builds that omit `Gtk.INVALID_LIST_POSITION` from introspection.
- `src/pdynamo/` adapts GUI actions to pDynamo systems and simulation
  workflows. Scientific regression scope is described in Sections 6 and 11.15.
- `src/graphics_engine/` contains the vendored VisMol Python package, GTK4
  widget, OpenGL implementation, shaders, molecular parsers, Cython sources,
  and its own `setup.py`, `pyproject.toml`, and license. Git tracks its files
  directly, despite the stale `.gitmodules` entry.
- Detailed package, GTK API, UI resource, dependency, and installer inventory
  is recorded in this report under Sections 2 and 11.2 (EH4-001).
- GTK4 migration, trackpad, and PySCF/GPU history reports are retained as
  topic sections in Section 11 of this report.

## EH4-000 remaining blockers

EH4-000 remains **in progress, not complete**. The current parent branch, commit,
clean state and owner-supplied `origin` are verified. The declared graphics
submodule has no gitlink or checked-out Git metadata. Its public branch head is
known, but the exact vendored source base and contributor/license ownership
remain unresolved. Do not infer the graphics base SHA from EasyHybrid3 or the
current upstream branch head.


## 11.2 Package and dependency inventory

## EH4-001 — package, dependency, and GTK API inventory

### Entrypoints and project areas

- `easyhybrid.py` is the application entrypoint. It loads pDynamo environment
  configuration, requests GTK 4, creates `Gtk.Application`, and initializes
  the GUI. The active launcher `activate_easyhybrid4.sh` sets `EASYHYBRID_HOME`
  and invokes the configured Python environment.
- `install.py` is the interactive prerequisite/build installer. `paths.py`
  optionally supplies `PDYNAMO_HOME`; `requirements.txt` lists Python runtime
  packages and `requirements-dev.txt` adds pytest. Root scientific example
  scripts live under `examples/scripts/`.
- `src/gui/` contains the main window, widgets, molecular builder, analysis,
  setup, and simulation dialogs. UI definitions are 53 `.glade` GtkBuilder
  resources; there are no `.ui` resources. Resources are loaded from GUI
  modules, including `src/gui/main/main_window.py` and
  `src/gui/windows/simulation/`.
- `src/pdynamo/pDynamo2EasyHybrid/` is the GUI-to-pDynamo session facade and
  mixins for analysis, simulation, restraints, representation, and data I/O.
  `src/pdynamo/p_methods/` implements simulation setup/workflows, while
  `src/pdynamo/opls/` and `src/util/extras/` contain force-field and QC
  integrations.
- `src/util/` provides plotting, geometry, trajectory, file, and analysis
  utilities. `tests/` has two scientific/data-logic test modules and
  fixtures; the coverage boundary is stated in Sections 6 and 11.15.
- `src/graphics_engine/src/vismol/` contains the VisMol models and parsers
  (`model/`, `utils/`), application/session logic (`core/`), GTK widgets
  (`gui/`), OpenGL context and molecular rendering (`libgl/`), and GLSL
  shaders (`libgl/shaders/`). Seven Cython extension sources are built by
  `src/graphics_engine/setup.py` through `install.sh`.

### GTK, GLib, and UI resource API baseline

- Python GTK imports request `gi.require_version("Gtk", "4.0")`; a source
  audit found no GTK 3 namespace requests. GTK3 and GTK4 are distinct API
  majors; the GTK4 import request does not establish a supported runtime
  minor interval. The runtime minimum is GTK 4.8; GTK 4.14.5 is
  the highest locally verified runtime. Current stable GTK 4.22.5 remains
  untested. See Section 3.
- The 53 `.glade` resources declare GtkBuilder library version 4.0. The
  resource/API audit is descriptive only; no blanket claim that all builders
  work at every GTK4 minor is made here.
- GTK classes are used directly throughout GUI and pDynamo adapter modules.
  GLib provides idle scheduling in `easyhybrid.py` and the pDynamo/VisMol
  adapters. GTK feature compatibility currently has a small helper in
  `src/gtk4_compat.py`; EH4-101 is the planned comprehensive adapter/test
  task.
- `Gtk.GLArea` is embedded in `src/graphics_engine/src/vismol/gui/` and
  delegates rendering to `libgl/vismol_glcore.py` and the shader/representation
  modules. A real context and renderer were not inspected during this static
  inventory.

### Declared and optional dependencies

- Root Python requirements: NumPy, SciPy, PyOpenGL, Cython, freetype-py,
  pycairo, PyGObject, and psutil (`requirements.txt`). GTK4 and its
  introspection typelib are external native dependencies. pDynamo3 is an
  independently installed binary/scientific framework, not a pip requirement.
- The graphics package metadata (`src/graphics_engine/pyproject.toml` and
  `setup.py`) additionally declares NumPy, Cython, and PyOpenGL and compiles
  Cython extensions. Its metadata advertises Python `>=3.7` and Unix only;
  this does not establish compatibility of the whole application with those
  Python versions or with Windows/macOS.
- The installer checks Python packages in `install.py:PYTHON_LIBRARIES`, the
  GTK typelib/runtime, compiler tools, and pDynamo. Optional QC interfaces
  appear in setup dialogs for ORCA, xTB, MOPAC, Sparrow, DFTB+, and
  PySCF/GPU4PySCF. Vendored adapters under `src/util/extras/` include ORCA,
  xTB, and MOPAC; `install.py` currently offers installation of the xTB
  adapter and checks the ORCA/xTB executable environment variables.
  PySCF/GPU4PySCF and the other external engines are not installed by
  `requirements.txt`.
- Build/launch scripts include `install.py`,
  `src/graphics_engine/install.sh`, `activate_easyhybrid4.sh`, and standalone
  VisMol scripts under `src/graphics_engine/scripts/`. The latter two shell
  scripts require a Bash-compatible shell, so native Windows provisioning is
  not demonstrated by this inventory.

### Known source-boundary observations (not fixes in EH4-001)

- `.gitmodules` declares a graphics submodule, but Git stores the directory
  as ordinary files. `.gitmodules` URL, `pyproject.toml` project URLs, and the
  absent parent remote do not establish which upstream revision these files
  came from; preserve that as an EH4-000/EH4-200 issue.
- The root README's clone example names EasyHybrid3, while describing
  EasyHybrid4 as a separate local port. No EasyHybrid4 remote/fork URL is
  configured in Git.
- Native Windows, macOS, Wayland, and GTK minor-version test results remain
  **NOT TESTED**. This task changed documentation only and did not alter
  scientific behavior.


## 11.3 Contributor quick start

Read [`../AGENTS.md`](../AGENTS.md) and [`ROADMAP.md`](ROADMAP.md) before
starting work. The roadmap is the task queue; update it with actual test
evidence and commit each coherent task separately.

## Environment

Use an isolated Python environment with the dependencies from
[`../requirements.txt`](../requirements.txt) and GTK4/PyGObject installed from
the native platform package source. The application also requires a separately
configured pDynamo3 environment. EasyHybrid4 does not provide one universal
dependency installer for all operating systems.

The verified local example used Python 3.12.3, PyGObject 3.48.2, GTK 4.14.5,
GLib 2.80.0 and GCC 12.4.0 on Linux x86_64. Those versions are evidence for
that environment only. Check [Section 3](#3-gtk4-python-and-dependency-compatibility)
and [Section 5](#5-platform-and-graphics-requirements) before making other
compatibility claims.

## Build and run checks

With the environment that provides GTK, pDynamo3 and the Python requirements
activated:

```sh
python -m pytest -q -p no:cacheprovider tests/
```

To compile the VisMol Cython extensions in the checkout:

```sh
cd src/graphics_engine
bash install.sh
cd ../..
```

That build writes generated C and native extension outputs under the graphics
source tree. For a non-mutating baseline, copy `src/graphics_engine` to a
temporary directory and build the copy; the complete verified example is in
[this report, Section 6](#6-reproducible-test-baseline).

The full `install.py` is interactive and may install packages or update the
configured pDynamo environment. Review its choices before running it; do not
run it as a test command in a user's active scientific environment.

## Regression tests and test data

The current pytest suite is display-free and targets molecular bond editing
and bond-order perception. `tests/conftest.py` builds a small in-memory VisMol
object with generated atoms, connectivity, and zeroed coordinates; this avoids
real research structures and does not exercise GTK, OpenGL, pDynamo
synchronization, simulations, or export round trips. Add focused tests next to
the behavior they cover and keep UI/GL acceptance separate from unit tests.

Follow [this report, Section 8](#8-safe-test-data-policy) for all fixtures and
generated scientific inputs. Never put private research files, credentials,
or unlicensed molecular data into the repository.

## Reporting

For each task record OS/architecture, Python/PyGObject/GTK/GLib versions,
commands, raw pass/fail/skip results, graphics metadata where applicable, and
all untested platforms. Update `docs/ROADMAP.md`, run applicable checks, and
commit the task without claiming unavailable CI or native hardware results.


## 11.4 EasyHybrid3 feature parity audit

Date: 2026-10-17. This is a source and test inventory, not a claim that the
complete applications have been exercised. EasyHybrid3 was inspected
read-only at `~/software/EasyHybrid3`; its implementation summary is
`docs/EASYHYBRID3_IMPLEMENTATION_REPORT.md`. EasyHybrid4 evidence is from this
checkout. Statuses mean:

- **WORKING** — the explicitly named non-GUI behavior has regression-test
  evidence; this does not certify its GUI workflow.
- **BROKEN** — a reproducible diagnostic/failure is known, but impact may need
  further investigation.
- **UNIMPLEMENTED** — the audited EasyHybrid3 capability has no corresponding
  EasyHybrid4 implementation/menu front end found in this source audit.
- **UNTESTED** — corresponding code is present or a migration is claimed, but
  end-to-end behavior has not been demonstrated.

| Workflow | EasyHybrid3 reference | EasyHybrid4 evidence | Status and evidence |
|---|---|---|---|
| Atom/bond editing primitives and bond-order perception | `src/gui/windows/builder/atom_ops.py`; `src/graphics_engine/src/vismol/core/bond_order_perception.py` | `src/gui/windows/builder/atom_ops.py`; same VisMol core modules | **WORKING (logic slice only)** — both suites exercise these non-GUI components. EH4: `python -m pytest -q -p no:cacheprovider tests/` = 23 passed. No claim for UI, pDynamo synchronization, or rendered result. |
| Interactive Builder: create/edit loaded molecules, undo, hydrogen/charge handling, fragments, structures, solvation, DYFF/OPLS tools | `src/gui/windows/builder/`; detailed scope in EH3 implementation report §§3.1 and Part II | GTK4 counterparts under `src/gui/windows/builder/`; GTK4 migration described in Section 11.10 | **UNTESTED** — component source exists; existing regression suite covers bond operations/perception only. No live Builder interaction, full undo/persistence round trip, or real pDynamo-backed editing run was recorded. |
| Molecular viewer, picking, selection, representations, camera and trajectory playback | `src/graphics_engine/src/vismol/` and EH3 report §§2–3 | `src/graphics_engine/src/vismol/`, GTK4 integration in `src/gui/main/main_window.py` | **UNTESTED** — no real `Gtk.GLArea` context/render test or end-to-end mouse/picking validation in this baseline. |
| GTK widget lifecycle / window startup | GTK3 main window and auxiliary Glade windows | `easyhybrid.py`, `src/gui/main/`, GTK4 GtkBuilder resources | **BROKEN (diagnostic observed)** — user-provided launch output contains two `gtk_box_remove` GTK critical assertions. Whether these affect visible behavior is unknown; the responsible widget-removal path has not yet been isolated. |
| System import, force-field assignment, merge/prune, trajectory import and `.easy` project save/load | EH3 `import_system.py`, session methods, `io_data.py`; report §3.6 | `src/gui/windows/setup/windows_and_dialogs/system_windows/`, `src/pdynamo/pDynamo2EasyHybrid/{session,io_data,import_trajectory}.py` | **UNTESTED** — parallel code paths are present; no representative file-import or project round-trip fixture has been run as part of this audit. |
| MM/QC/QC-MM model setup and calculations | EH3 QC setup modules and pDynamo session integration; report §3.5 | `src/gui/windows/setup/windows_and_dialogs/qc_setup/`, `src/pdynamo/pDynamo2EasyHybrid/session.py` | **UNTESTED** — code and engine setup modules exist, but no calculation-level pDynamo result comparison was run. |
| Single point, geometry optimization, MD, normal modes and transition-state search | EH3 `src/gui/windows/simulation/` | Same named GTK4 window family under `src/gui/windows/simulation/`; dispatch in `src/pdynamo/pDynamo2EasyHybrid/simulations_mixin.py` | **UNTESTED** — windows and dispatch exist; no sample scientific run or output comparison was performed. |
| 1D/2D PES scans, umbrella sampling, WHAM, reaction paths/NEB and CPR | EH3 report §3.3; `PES_scan_window.py`, `umbrella_sampling_window.py`, `WHAM_analysis_window.py`, path/CPR tools | Corresponding GTK4 modules and pDynamo methods are present; see Section 11.10 | **UNTESTED** — UI/resources and dispatch are present; no generated-input or numerical-output comparison was run. |
| Analysis: RDF, density, RMSD/RMSF, Ramachandran, surfaces, WHAM and trajectory tools | EH3 report §3.4 and `src/gui/windows/analysis/` | Corresponding modules exist under `src/gui/windows/analysis/`; Section 11.10 documents GTK4 migration | **UNTESTED** — source presence is verified, but no analysis fixture/result comparisons were run for this audit. |
| Infrared spectrum workflow | EH3 report §3.4 and infrared changelog in §7 | No EasyHybrid4 infrared/spectrum window or menu handler was found by filename or source-symbol search; current `src/util/extras/` has QC model adapters but no corresponding GUI workflow | **UNIMPLEMENTED** — restore or explicitly retire with a documented feature decision; do not treat generic dipole/QC support as parity. |
| AutoDock Vina and AutoDock-GPU setup/run/import | EH3 report §3.2 and `setup/windows_and_dialogs/system_windows/prepare_vina_docking.py`, `prepare_autodock_gpu.py` | No corresponding docking modules or menu/action handlers found under `src/` | **UNIMPLEMENTED** — both EH3 docking front ends are absent from the audited EasyHybrid4 source. |
| NAMD/SMD, AMBER `tleap`, Packmol and Antechamber preparation front ends | EH3 report §3.5 and `prepare_namd_run.py`, `prepare_smd_run.py`, `prepare_amber_system.py`, `prepare_packmol_run.py`, `prepare_ligand_antechamber.py` | No matching setup windows/front ends found. The bundled solvent builder's Packmol-style placement is not the same as those preparation workflows. | **UNIMPLEMENTED** — the EH3 external preparation dialogs are not present. |
| Scientific system/script exports and simulation output files | EH3 export dialogs and report §3.6 | `src/gui/windows/setup/windows_and_dialogs/dialogs/export_dialogs.py`, `pDynamo2EasyHybrid/session.py::export_system`, pDynamo scan/sampling methods | **UNTESTED** — export code exists; no exported-file schema, restart, or numerical output fixture comparison was done. |
| Process manager, jobs, recent files, and project/session management | EH3 report §3.6 | `src/gui/windows/setup/process_manager_window.py`, session/serialization modules, main-window actions | **UNTESTED** — source paths are present; lifecycle and restart behavior were not exercised. |

## Test evidence and limits

On Linux x86_64 with Python 3.12.3, PyGObject 3.48.2, GTK 4.14.5 and GLib
2.80.0:

- EasyHybrid4: `~/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/` — **23 passed**.
- EasyHybrid3 reference: `~/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider ~/software/EasyHybrid3/tests/` — **23 passed, 4 skipped**.
- Both suites are primarily GTK/display-free atom/bond and chemistry logic tests. They do not test the GUI, pDynamo calculations, exports, real OpenGL, Windows, or macOS.
- Linux Wayland/X11 live GUI, GTK 4.0, other GTK minors, Windows, and macOS are **NOT TESTED**. See Section 6 of this report.

This audit changes documentation only. No new executable behavior was added,
so no new behavioral regression test was appropriate. The identified parity
gaps and the observed GTK critical warning become follow-up work; this checklist
does not authorize removing or changing scientific behavior.


## 11.5 GTK4 and Python compatibility contract

Status: evidence-based target selected; lower/upper GTK runtime validation is
still pending. This document distinguishes the intended range from versions
actually tested.

## Selected target and verified versions

| Contract item | Selection | Evidence / status |
|---|---|---|
| GTK API namespace | `Gtk 4.0` | `gi.require_version("Gtk", "4.0")` and GtkBuilder resources target 4.0. This names GTK's API namespace, not a 4.0 runtime. |
| `GTK_MIN` target | GTK `4.8` | The installer rejects versions below `(4, 8)`; source requests the `Gtk 4.0` namespace. GTK 4.8 runtime **NOT TESTED**. |
| Local GTK runtime verified | GTK `4.14.5` / GLib `2.80.0` | The Linux development environment. Existing unit tests pass; this is not a live window/GL verification. |
| Current upstream stable target | GTK `4.22.5` (as checked 2026-10-17) | [GTK project release status](https://www.gtk.org/). GTK 4.22.5 **NOT TESTED** in this project. |
| `GTK_LATEST_VERIFIED` | `4.14.5` | Highest project runtime actually exercised so far; it is not the current upstream stable release. |
| Python target | Python `>=3.10` candidate | Source contains evaluated PEP 604 annotations such as `Gtk.Window | None`, which require Python 3.10+. Only Python 3.12.3 was executed. pDynamo/native dependency support on other Python versions is **NOT TESTED**; no upper bound is approved yet. |

The intended compatibility target is GTK 4.8 through current GTK4 stable, with
the explicit qualification that only GTK 4.14.5 has been exercised in this
checkout. This is not a blanket pass for every GTK4 minor, every platform, or
future releases. Every GTK 4.x minor from 4.8 through the latest included
stable release needs an actual run on each claimed OS before the range can be
described as verified. GTK 4.8 and GTK 4.22.5 need real CI jobs. GTK 4.6 and
older are unsupported.

## Dependency resolution strategy

- GTK4, GLib and their introspection typelibs are native platform dependencies;
  do not try to version them through `pip`. Provision GTK natively on each CI
  OS and report the version loaded at runtime.
- `requirements.txt` currently provides lower bounds for Python packages but
  no lock/constraints set. Keep those minimum declarations, and add platform
  and Python-specific constraints only when CI proves an incompatibility or a
  reproducibility need. CI should install from the same declared requirements
  used by contributors, then publish the resolved package versions.
- pDynamo3 and optional QC engines remain external binary/scientific
  dependencies. The only verified pDynamo environment is the configured
  Python 3.12.3 Linux environment. Do not claim other Python/platform
  combinations based on graphics-only builds.
- A release support claim requires tests for the lowest GTK/Python targets and
  a current stable GTK runtime. Raise `GTK_MIN` only when a required API or
  dependency cannot be kept compatible, document the exact blocker, and
  provide a tested migration/fallback plan.

## Source audit: minor-version APIs

- GTK 4.8's `Gtk.Picture.set_content_fit()` is feature-detected in
  `easyhybrid.py`; the fallback uses `set_can_shrink()` and
  `set_keep_aspect_ratio()`. GTK documents `set_content_fit` as available since
  4.8 and the aspect-ratio API as deprecated since 4.8. See the [GTK
  `Gtk.Picture` API](https://docs.gtk.org/gtk4/method.Picture.set_content_fit.html).
- GTK 4.8's scroll-unit API is feature-detected in
  `src/graphics_engine/src/vismol/gui/vismol_gtkwidget.py` using
  `hasattr(Gtk.EventControllerScroll, "get_unit")`; earlier runtimes request
  discrete wheel steps. See the [GTK scroll-controller API](https://docs.gtk.org/gtk4/method.EventControllerScroll.get_unit.html).
- No `Gtk.FileDialog` or `Gtk.AlertDialog` usage was found in the source scan;
  both APIs were introduced in GTK 4.10. The application uses its existing
  async chooser and message-window helpers instead. See GTK's
  [`Gtk.FileDialog` API](https://docs.gtk.org/gtk4/class.FileDialog.html).
- GTK deprecation cleanup for the supported chooser paths is complete as
  EH4-106. The file/color chooser
  adapter must retain `Gtk.FileChooserDialog` and `Gtk.ColorChooserDialog` for
  GTK 4.8, and currently uses the GTK widget fallback on Windows after native
  async dialog cancellation disconnected COM on multiple GTK releases. Those
  chooser-class references are therefore deliberate compatibility exceptions.
  `ChooserHandle.cancel()` now emits the existing `response` signal instead of
  calling the deprecated `Gtk.Dialog.response()` convenience method. The
  fallback color chooser now reads/writes its `rgba` property instead of the
  deprecated `Gtk.ColorChooser.get_rgba()`/`set_rgba()` methods. On local GTK
  4.14.5, focused chooser tests passed (6 passed, 1 skipped), three repeated
  display-backed cancellation/open-close runs passed (3/3 each), and the full
  widget-pattern module passed (60 passed, 7 skipped). Native matrix run
  [`39174543987`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39174543987)
  passed **30/30** for Linux, Windows and macOS across GTK 4.8–4.24; every
  matrix widget-pattern step passed. The static regression scan exempts only
  the legacy chooser class references in the adapter, not unrelated deprecated
  calls in that module. Two complete local GTK 4.14 module runs reported a
  GLib `g_error_free` assertion during the color-cancel test sequence; an
  isolated warning-as-error rerun passed, and the warning did not fail any
  native matrix cell.
- The installer checks the loaded GTK version at runtime, but it does not
  validate every API referenced by Python or GtkBuilder resources. The GTK
  import scan found the `Gtk 4.0` introspection namespace used consistently;
  platform/minor API differences are routed through the documented adapters.

## Validation matrix

| Version/platform | Status |
|---|---|
| Linux x86_64, GTK 4.14.5 / GLib 2.80.0 / Python 3.12.3 | Current suite: 48 passed, 4 skipped; Gtk application/widget, builder loader and GLArea software-renderer smoke passed under Xvfb. GTK 4.14.5 is the latest runtime currently verified, not a claim for later minors. |
| GTK 4.8.2 minimum, Linux x86_64 | Current suite: 48 passed, 4 skipped; GTK application/widget, app Builder loader and GLArea software-renderer smoke passed under Xvfb. Full EasyHybrid import is blocked by a Python-3.12-built pDynamo binary extension when using Python 3.10. |
| GTK 4.10, 4.12, 4.16, 4.18, 4.20, and subsequent GTK 4.x minors through 4.22, Linux | NOT TESTED; GTK 4.14.5 is the only runtime present. Exact runtime patch versions must be recorded separately for every minor. |
| GTK 4.22.5, Linux | NOT TESTED; current stable target is unavailable in the local runtime. |
| Windows native GTK4 / Python | NOT TESTED; no native runner was executed. |
| macOS arm64/x86_64 GTK4 / Python | NOT TESTED; no native runner was executed. |

No runtime code changed in this contract decision. Existing behavior tests were
rerun; GTK_MIN and current stable runtime acceptance still requires the
versioned CI tasks in Phase 5.


## 11.6 Known limitations register

This list records current evidence and does not make an implementation issue a
reason to change scientific behavior without regression evidence.

| ID | Limitation | Evidence / impact | Next work |
|---|---|---|---|
| KL-001 | The vendored graphics-engine source revision and contributor/license ownership are not established. `.gitmodules` lists the path, but Git tracks ordinary files. | Parent remote and EasyHybrid3 comparison root are verified. EasyHybrid4 has no Git submodule pointer; EasyHybrid3's graphics SHA and the public branch head do not prove the vendored base revision. Conflicting license notices remain. This is a provenance/publishing gap, not a current Linux test blocker. Do not guess URLs or revisions. | EH4-000 / EH4-200 / EH4-602 when authoritative ancestry and ownership evidence is available. |
| KL-002 | GTK minor range is selected but not fully validated. | GTK 4.8 target and upstream stable GTK 4.22.5 have not been run; local evidence is GTK 4.14.5 only. GTK 4.6 is unsupported. | Native GTK_MIN and current-stable CI jobs in EH4-501; UI/GL in EH4-502/503. |
| KL-003 | Cross-platform support is unverified. | Windows, macOS, Linux Wayland, and alternate Linux distributions were not tested. Bash launch/build scripts and native pDynamo dependencies need platform-specific validation. | EH4-300 through EH4-304 and EH4-500 onward. |
| KL-004 | Graphics fallback coverage is only locally verified on one GTK runtime. | Linux X11/Xvfb GTK 4.14.5 confirms actual GL rendering and an injected unsupported-version diagnostic; native unsupported-driver failures and cross-platform/minor behavior remain unverified. | EH4-205 native matrix; real unsupported drivers where available. |
| KL-005 | EasyHybrid startup emitted two GTK critical messages. | User-provided terminal output reported `gtk_box_remove: assertion 'gtk_widget_get_parent (child) == (GtkWidget *)box' failed` twice. Visible impact and responsible removal path are unknown. | Reproduce under GTK 4.14.5, isolate the parent/child removal path, add a lifecycle regression in EH4-102/105. |
| KL-006 | Generic pip installation of the graphics package failed metadata generation. | Isolated `pip install --target` failed with `ModuleNotFoundError: No module named 'src'`; the project's `build_ext --inplace` path and all seven extension imports passed. | Packaging/build audit EH4-200 or EH4-303. |
| KL-007 | pDynamo3 is only validated in one configured environment. | Linux Python 3.12.3 environment resolves `pCore`, `pMolecule`, `pSimulation`, and `pScientific`; Windows/macOS and other Python runtimes are untested. | Python/platform integration matrix in EH4-004/500/504. |
| KL-008 | Feature parity is incomplete or unverified. | See [Section 4](#4-easyhybrid3-feature-parity): docking front ends, several external preparation dialogs, and infrared GUI are absent; many remaining paths are source-present but behavior-unverified. | Implement parity gaps as separate scoped tasks; test scientific outputs before changing workflows. |
| KL-009 | GtkBuilder validation covers only the installed GTK minor. | The 53 Glade resources and additional embedded definitions were checked against installed GTK 4.14 introspection data; GTK 4.8/current stable construction tests are absent. | EH4-102 and EH4-501/502. |
| KL-010 | GTK removed/deprecated API audit is incomplete. | A targeted audit found gated GTK 4.8 methods; there is no exhaustive, version-aware API inventory yet. | EH4-106, with compatibility tests for the selected range. |
| KL-011 | The saved graphics patch is stale and cannot be applied to the current tree. | Correctly rooted dry run fails on changed GTK/event hunks; event forwarding and selection guards are already in source. Its `popup_at_pointer` calls are not part of GTK4 `Gtk.Popover`; current GTK4 code uses `set_pointing_to()` and `popup()`. | Keep it unapplied; test the active GTK4 path in EH4-104/200. |

See [this report, Section 6](#6-reproducible-test-baseline) for precise environments and results and
[Section 5](#5-platform-and-graphics-requirements) for target platform requirements.


## 11.7 Platform support and native requirements

## Status summary

| Platform/backend | Intended target | Verified status |
|---|---|---|
| Linux x86_64, X11 | GTK 4.x, Python target >=3.10, pDynamo3, OpenGL 3.3+ core | Python 3.12.3 / GTK 4.14.5 tests and extension build passed. Live GUI, X11 window construction, and GL context: **NOT TESTED**. |
| Linux x86_64, Wayland | Same shared application code and native GTK | **NOT TESTED**; no Wayland session exercised. |
| Linux other architectures/distributions | Native GTK/PyGObject and compatible pDynamo3 | **NOT TESTED**. |
| Windows x64 | Native GTK4/PyGObject, working OpenGL 3.3+ core driver, compatible pDynamo3 and external engines | **NOT TESTED**; no Windows runner/build used. |
| macOS arm64 | Native GTK4/PyGObject, compiler tools, OpenGL 3.3+ core profile, compatible pDynamo3 | **NOT TESTED**; no macOS runner/device used. |
| macOS x86_64 | Same, if a supported native GTK/pDynamo environment is available | **NOT TESTED**. |

These are intended targets, not a declaration of supported releases. Exact GTK
and Python status is in [Section 3](#3-gtk4-python-and-dependency-compatibility); test
commands and versions are in [this report, Section 6](#6-reproducible-test-baseline).

## Shared runtime requirements

- GTK4 with the `Gtk 4.0` introspection namespace, GLib, and PyGObject.
  GTK/GLib are native dependencies supplied by the operating system or a
  platform-specific package environment, not by `pip`.
- Python dependencies listed in root `requirements.txt`.
- pDynamo3 and its compiled scientific extensions, configured independently
  from EasyHybrid4. Optional engines such as ORCA, xTB, MOPAC, DFTB+, PySCF,
  Sparrow and GPU4PySCF have their own executables/build constraints.
- A C compiler and Python development headers to compile the seven Cython
  VisMol extensions.
- A working GTK OpenGL area and a driver that provides the requested OpenGL
  3.3+ core context. The GL widget requests that version explicitly; failures
  are reported as fatal because the shaders require it.

## Platform-specific observations

- The launcher and VisMol build helper are Bash scripts. Native Windows
  launching/building therefore needs a documented Windows shell/build path or
  replacement entry point before Windows can be claimed supported.
- The installer checks Xcode Command Line Tools on macOS for native extension
  builds. It does not provision GTK, pDynamo3, or optional scientific engines.
- GTK4 and OpenGL context negotiation, file dialogs, fonts, scaling, and
  keyboard/trackpad event semantics must be checked on each native OS. Linux
  results do not validate Windows or macOS.
- The macOS scroll path has a GTK 4.8 capability check for scroll units. The
  actual trackpad behavior remains **NOT TESTED**.
- No OS-specific fallback may substitute a stub for molecular rendering or
  scientific calculations. Record an explicit unsupported capability if the
  required native feature is unavailable.

## CI design input

Use native GitHub-hosted Linux, Windows, and macOS runners for OS-level
provisioning, import, build, and regression tests. The initial workflow
`.github/workflows/native-gtk-matrix.yml` now requests all nine GTK minor
series and records exact loaded GTK/GLib/PyGObject/Python versions. Linux
native jobs use Xvfb/llvmpipe; Windows/macOS jobs call GTK directly. The
workflow has run: Windows GTK 4.8/4.10 fail during GTK GL context creation;
the other included matrix cells passed in run `39066895345`. Cell-by-cell
results and the limits of the WGL diagnostic are in
`GTK4_COMPATIBILITY.md`. Apple trackpad/Retina and physical-driver coverage
still require dated manual device reports. See EH4-500 through EH4-505 for
completion criteria.


## 11.8 Safe test data and fixture policy

## Prefer generated fixtures

- Use the smallest synthetic molecular graph that reproduces the behavior.
- Prefer in-memory atoms, bonds, and coordinates over checked-in structures.
  The existing `tests/conftest.py` factory creates generated atoms and simple
  zero-coordinate frames for connectivity/selection tests.
- Use `tmp_path` or a temporary directory for generated projects, scripts,
  trajectories, logs, and exports. Tests must not write into a user's project,
  home directory, or shared pDynamo data tree.
- Keep fixtures deterministic: document atom ordering, units, expected
  tolerances, and any random seed. Avoid large simulation trajectories and
  production-scale force-field databases.

## If real molecular data is necessary

- Use only a small, public example with a license that permits redistribution
  and record the source URL, license, attribution, and date in a fixture
  README or adjacent manifest.
- Remove personal/clinical/project metadata and verify that no confidential
  coordinates, collaborator identifiers, paths, or embedded credentials are
  included.
- Do not assume a public paper or repository makes its coordinate files
  freely redistributable. If rights are unclear, do not add the file; create a
  synthetic equivalent or obtain permission outside the repository.
- Never commit user research data, private structures, simulation outputs,
  tokens, passwords, or machine-specific configuration.

## Review and storage

- Keep committed fixtures small and purpose-specific. Add only data required
  to reproduce a regression.
- Include expected output assertions and scientific tolerances; do not compare
  full logs containing paths or machine-specific timing.
- Check `git status` after tests and ensure generated files stay in temporary
  locations or ignored build directories.
- Treat serialized pDynamo/EasyHybrid project files as potentially containing
  complete molecular data; do not add them without provenance and license
  review.


## 11.9 Detailed test matrix and baseline results

This file records checks actually run in the EasyHybrid4 checkout. A passing
Linux result does not imply support on another operating system, GTK minor, or
display backend.

## Available environment

| Item | Observed value |
|---|---|
| OS / kernel | Linux x86_64, `Linux [remote Linux host] 6.8.0-147-generic`, Ubuntu userspace with glibc 2.39 |
| Python | 3.12.3 (`~/software/envs/easyhybrid312/bin/python`) |
| PyGObject | 3.48.2 |
| GTK runtime | 4.14.5 |
| GLib runtime | 2.80.0 |
| pytest | 9.1.1 |
| NumPy / SciPy | 1.26.4 / 1.11.4 |
| Cython | 3.0.8 |
| PyOpenGL / psutil | 3.1.7 / 5.9.8 |
| Compiler | GCC 12.4.0 (Ubuntu) |
| Graphics renderer/context | NOT TESTED in this baseline |

The application launcher sources `~/software/pdynamo3.sh`. With
that environment active, `pCore`, `pMolecule`, `pSimulation`, and `pScientific`
all resolve. A direct import probe without the launcher environment does not
represent the application's configured runtime.

## EH4-002 reproducible baseline

### Existing tests

Command:

```sh
~/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/
```

Result: **PASS**, 23 passed in 0.02 seconds. Cache is disabled to avoid the
previous warning caused by a read-only shared pytest cache directory.

### Graphics engine extension build and import

The repository's graphics build command is `python3 setup.py build_ext
--inplace` (`src/graphics_engine/install.sh`). The test below runs that command
on a temporary source copy so generated C files and binaries do not modify the
checkout:

```sh
tmpdir=$(mktemp -d)
cp -a src/graphics_engine "$tmpdir/graphics_engine"
cd "$tmpdir/graphics_engine"
~/software/envs/easyhybrid312/bin/python setup.py build_ext --inplace
PYTHONPATH="$tmpdir/graphics_engine/src" \
  ~/software/envs/easyhybrid312/bin/python -c 'import vismol.utils.matrix_operations, vismol.utils.PDBFiles, vismol.utils.GROFiles, vismol.utils.c_distances, vismol.utils.selectors, vismol.utils.mesh_decimation, vismol.utils.mesh_smoothing; print("7 graphics extension imports: PASS")'
```

Result: **PASS**; all seven Cython extensions compiled with GCC and imported.
Build emitted NumPy deprecated C API and setuptools metadata/license warnings.
The source checkout was not changed by this build.

### Package installation probe

An isolated `pip install --no-deps --no-build-isolation --target <temporary-dir>
<temporary graphics-engine copy>` probe **FAILED** during PEP 517 metadata
generation: `setup.py` raised `ModuleNotFoundError: No module named 'src'`.
The project's own `install.sh` build path and compiled-extension imports pass,
but generic pip package installation is not verified. Treat wheel/package
installation as a graphics-engine packaging issue for later task EH4-200 or
EH4-303; do not infer that pip installation works from `build_ext` success.

The full interactive EasyHybrid installer was **NOT RUN**: it can install
dependencies and modify the configured pDynamo environment, which would exceed
this non-invasive baseline check.

## Platform and GTK coverage

| Target | Status | Evidence / reason |
|---|---|---|
| Linux x86_64, GTK 4.14.5 / GLib 2.80.0 | PASS for existing tests and graphics extension build/import | Commands above; no real GUI or GL context test |
| GTK 4.8 selected minimum target | NOT TESTED | No GTK 4.8 runtime/build available; GTK 4.6 is below the target |
| Each GTK 4.x minor >=4.8 except GTK 4.14.5 | NOT TESTED | Only GTK 4.14.5 is installed locally; exact patch runtime results are required for every minor in the claimed range |
| Linux Wayland | NOT TESTED | No Wayland UI/GL session exercised |
| Linux X11 GUI / real OpenGL context | NOT TESTED | No GUI/context smoke test in EH4-002 |
| Windows native GTK4 | NOT TESTED | No Windows runner available in this session |
| macOS native GTK4 (arm64 / x86_64) | NOT TESTED | No macOS runner available in this session |

The GTK project website listed GTK 4.22.5 as the latest stable release on
2026-10-17 ([release status](https://www.gtk.org/)); this runtime was not
installed or tested. GTK 4.8 is the selected minimum target, not yet a
validated minimum. See Section 3 for the API audit and target
contract.

No runtime application or scientific behavior was modified in EH4-002, so no
new behavioral regression test was needed; the existing test suite and a
compiled-extension import smoke check were run.


## 11.10 GTK4 port history

EasyHybrid4 aims to be a faithful GTK4 port of EasyHybrid3. EasyHybrid3 remains
the behavioral and visual reference. The parity audit in
[Section 4](#4-easyhybrid3-feature-parity) records workflows that are
still unimplemented or unverified. The port must not redesign workflows,
rename scientific concepts, remove features, or add placeholder features.

## Supported platforms

- Linux, Windows, and macOS are intended targets for the GTK 4.8 runtime baseline
  and PyGObject. This is not a verified platform support claim: only Linux
  GTK 4.14.5 has been exercised so far. See
  [Section 3](#3-gtk4-python-and-dependency-compatibility) for exact
  results and untested combinations.

Platform-specific code is allowed only for dependency discovery, packaging,
native file integration, and graphics behavior that cannot be implemented
portably. GTK4 `Gtk.GLArea` is the default renderer integration on every
platform. The EasyHybrid3 macOS workaround based on a hidden GLFW context must
not be copied unless native GTK4 testing demonstrates that it is still needed.

## Compatibility rules

1. Keep EasyHybrid3 unchanged. All port changes belong in `EasyHybrid4`.
2. Preserve window structure, labels, actions, defaults, shortcuts, and
   scientific behavior from EasyHybrid3.
3. Write all new source, comments, documentation, messages, and UI text in
   English.
4. Replace removed GTK3 APIs with their direct GTK4 equivalents. Do not use a
   visual redesign to avoid a difficult migration.
5. Keep pDynamo session data and EasyHybrid project formats compatible unless a
   documented format migration is unavoidable.
6. Verify each migrated window against EasyHybrid3 before marking it complete.

## Known GTK4 migrations

| EasyHybrid3 GTK3 API | Faithful GTK4 implementation |
| --- | --- |
| `Gtk.main()` / `Gtk.main_quit()` | `Gtk.Application.run()` / application quit |
| `Gtk.MenuBar`, `Gtk.Menu`, `Gtk.MenuItem` | `Gio.MenuModel`, actions, and `Gtk.PopoverMenuBar` |
| `add()` / `pack_start()` / `pack_end()` | `set_child()` / `append()` / `prepend()` |
| GTK event signals and event masks | GTK4 event controllers and gestures |
| legacy drag destination API | `Gtk.DropTarget` / `Gtk.DropTargetAsync` |
| blocking dialog `run()` | asynchronous response callbacks |
| Blocking file chooser dialogs | `gui.file_dialogs.choose_file` (`Gtk.FileDialog` on 4.10+, GTK 4.8 fallback) |
| Blocking color chooser dialogs | `gui.file_dialogs.choose_color` (`Gtk.ColorDialog` on 4.10+, GTK 4.8 fallback) |
| `show_all()` | widget visibility plus `present()` |
| GTK3 Glade packing nodes | GTK4 child properties and layouts |

## Current state — migration in progress

The application requests the GTK 4.0 introspection namespace and targets a
GTK 4.8 runtime minimum. GTK 4.14.5 is the only project runtime exercised;
GTK 4.8 and current stable GTK have not yet been validated. GTK 4.6 and older
are unsupported. Startup uses
`Gtk.Application`; VisMol renders through
`Gtk.GLArea` on every platform. GtkBuilder signal connections use explicit
GTK4 helpers. The code does not monkeypatch GTK classes with GTK3 methods.
The signal loader resolves relative image paths against the original UI file
before using its temporary XML copy. Window-local styling uses GTK4 widget CSS
classes, and the terminal removes its display CSS provider when it closes.

The splash image uses `Gtk.Picture.set_content_fit()` when the runtime has it
(GTK 4.8+), and falls back to `set_can_shrink()` plus
`set_keep_aspect_ratio()` before GTK 4.8. VisMol uses GTK 4.8's scroll-unit
API to convert macOS trackpad surface-pixel deltas to calibrated wheel steps;
on earlier GTK4 versions the scroll controller asks GTK to emit discrete
wheel steps. The GTK3 Quartz `Gtk.DrawingArea`/hidden-GLFW workaround and
GTK3-only native accessibility bridge are not used by the GTK4 build.

The main browser uses `Gtk.TreeListModel`, `Gtk.ColumnView`, typed
`Gio.ListStore` rows, and GTK4 selection models. System and coordinate
selectors use `Gtk.DropDown`; tables and editable lists use column views with
list-item factories. The same native models are used across VisMol navigation,
analysis, simulation, import, restraint, and preferences workflows. Scientific
clone paths clear and restore interface row references around pDynamo cloning.
Full browser refresh rebuilds its tree and selector models together, preserves
the active system, and refreshes open interface windows. The old duplicate
RMSD and context-menu implementations and unreferenced Glade assets have been
removed or retired.

The EasyHybrid3 installation remains separate and has not been modified. A
source scan found no GTK3 typelib requests, GTK3 tree/combo widgets, GTK3
container methods, or GTK3 dialog `run()` calls in EasyHybrid4. Python modules
that import Gtk pin the `Gtk` namespace to 4.0, and all 53 GtkBuilder files
declare GTK 4.0.

The GTK-free RDF, RMSF, density, and Ramachandran calculations are available
in EasyHybrid4. RDF, box-density, RMSF, and trajectory Ramachandran analysis
windows are wired to the native GTK4 menu. They use GTK4 `DropDown`,
`SpinButton`, `DrawingArea`, motion controllers, and asynchronous file chooser
responses.

The Builder now exposes DYFF parameter inspection and editing, model
incorporation into pDynamo, and xTB torsion fitting through native GTK4
windows. Its parameter window uses GTK4 notebook/list widgets, and the
torsion-fit window builds controls in GTK4 rather than loading a GTK3 Glade
file. Builder undo snapshots include partial charges, manual atom types,
aromatic bonds, and DYFF parameter edits. The OPLS parameter inspector is also
ported to GTK4, with per-system tables, quality filters, structure projection,
editable values, model rebuilds, and xTB torsion fitting; it is available from
the System menu.
The remaining setup module,
`info_text_window.py` is an unreferenced standalone GTK3 demo that creates a
window and starts a GTK3 event loop at import time, so it is intentionally not
copied into EasyHybrid4. The Builder includes a GTK4
periodic-table picker and solvation window backed by the solvent library and
pure NumPy solvation engine, with 13 bundled solvent templates. DYFF atom
typing, editable type and charge values, protonation controls, residue rename,
hybridization display, and 3D atom highlighting use a native GTK4 ColumnView. Live selection translation and rotation use GTK4 scales and gesture controllers, with a single undo point per gesture.
The Builder can pick four atoms and adjust a rotatable bond dihedral with a
native GTK4 scale window; cyclic bonds are rejected and the linked pDynamo
system is synchronized when the adjustment ends. Its fragment library uses a
GTK4 category selector, fragment list, and GLArea preview. Selecting a
fragment arms hydrogen replacement; the selected molecule and formal charges
are carried into the Builder graph and pDynamo system. The fragment bundle
contains 27 MOL2 definitions across functional groups and rings.
The complete-structure library uses a native GTK4 category dropdown, list,
and GLArea preview. It places complete MOL2 molecules on a Builder click and
syncs their atoms and explicit bond orders to pDynamo. EasyHybrid4 now bundles
the same 663 structure templates as EasyHybrid3 across 31 categories.
The Builder toolbar opens a native GTK4 new/edit chooser. Existing systems are
cloned for editing; same-size edits fold back into the chosen molecular object,
while atom-count changes retain the clone as a separate system.
Remaining tools are migration work, not features considered complete by
absence from the GTK3 API scan.

The pDynamo layer exposes Baker saddle optimization and reaction-path
branches through the geometry-optimization worker, and dispatches Conjugate
Peak Refinement through pDynamo's `addOns.pyCPR`. All three workflows now
have GTK4 windows, native coordinate selectors, non-blocking error windows,
and GTK4 menu actions. Their Glade files declare GTK 4.0 and pass
`gtk4-builder-tool simplify` without property or class errors. The installed
pDynamo3 APIs and the EasyHybrid4 dispatch modules import successfully.

The current Builder, preferences, and reaction-coordinate modules compile and
import under GTK 4.14. The solvation library discovers all 13 solvent
templates, and a sphere solvation calculation placed solvent molecules. Gtk
imports in all 100 Python modules request GTK 4.0. All 53 GtkBuilder XML files
declare GTK 4.0; their object classes and properties resolve against the GTK4
introspection data, and no GTK3 packing nodes remain. The embedded preference
and reaction-coordinate UI definitions also pass the GTK4 property scan. The
menu JSON parses, and the Ramachandran Cairo renderer drew categorized points
on an image surface. The pDynamo typer classified both atoms in a bonded
two-carbon fragment. Live window construction and visual comparison remain
unverified in this environment: `Gtk.init_check()` succeeds, but constructing
a GTK window fails because the available display backend is not usable here.
Static verification also confirms all 53 GtkBuilder files request GTK 4.0 and
all 20 main-window image assets resolve from the original UI directory.


## 11.11 macOS trackpad pan implementation history

## Summary

EasyHybrid's camera panning is bound to a middle-mouse-button drag
(`vismol_glcore.py`). MacBook trackpads have no middle button and no
default gesture that emulates one, so panning was effectively
unreachable for anyone driving the app from a trackpad — rotate
(left-drag) and zoom (right-drag, reachable via a two-finger
secondary-click) both worked fine, but translating the view did not.

This adds a second way to trigger the same pan action: **holding Cmd
while right-dragging** (i.e. Cmd + two-finger-tap-drag on a trackpad),
matching PyMOL's own `Cmd+Right` = translate convention on macOS, so
the muscle memory carries over. The existing plain-right-drag = zoom
and plain-middle-drag = pan bindings are untouched; this is additive
only.

Verified end-to-end on an Apple Silicon Mac (M4): launched the app,
confirmed via a temporary debug print that GTK reports the Cmd key as
keyval `Meta_L` on this platform, then confirmed Cmd+trackpad-drag
visually pans the loaded structure instead of zooming it.

## Change

`src/graphics_engine/src/vismol/libgl/vismol_glcore.py`:
- Added a `self.cmd` flag (alongside the existing `self.ctrl` /
  `self.shift` modifier flags), defaulting to `False`.
- `mouse_pressed()`: right-button-drag now resolves to **pan** instead
  of **zoom** when `self.cmd` is `True`. Plain right-drag (no Cmd) still
  zooms, unchanged.

```python
self.mouse_rotate = left   and not (middle or right)
self.mouse_zoom   = right  and not (middle or left) and not self.cmd
self.mouse_pan    = (middle and not (right or left)) \
                     or (right and self.cmd and not (middle or left))
```

`src/graphics_engine/src/vismol/gui/vismol_gtkwidget.py`:
- Added key-press/release handlers for `Meta_L`, `Meta_R`, `Super_L`,
  and `Super_R`, all toggling the same `self.vm_glcore.cmd` flag. All
  four keyval names are wired (rather than just `Meta_L`) because which
  one GTK reports for the Cmd key can vary by GTK version/backend/
  keymap; only `Meta_L` was actually observed on the tested setup, but
  binding all four is cheap insurance against a different GTK build
  reporting one of the others.

This mirrors the existing pattern already used for `Control_L` /
`Shift_L` in the same file (`self.vm_glcore.ctrl` / `self.vm_glcore.shift`).

## Files changed

Submodule (`src/graphics_engine`, Vismol):
- `src/vismol/libgl/vismol_glcore.py` — `self.cmd` flag + pan/zoom
  gating in `mouse_pressed()`.
- `src/vismol/gui/vismol_gtkwidget.py` — `Meta_L/R` and `Super_L/R`
  key handlers.

## Not changed

- Left-drag rotate, middle-drag pan, and plain right-drag zoom are all
  unchanged for every platform.
- No new dependencies.
- Scroll-wheel zoom and the existing Ctrl/Shift-gated builder and
  selection-box behavior are untouched.


## 11.12 PySCF integration history (EasyHybrid3)

## Summary

Wires PySCF into EasyHybrid3's QC-engine selector as a fifth option alongside
pDynamo (MNDO), ORCA, DFTB+ and xTB, using pDynamo3's existing
`addOns.pySCF.QCModelPySCF` / `addOns.pySCF.NBModelPySCF` classes. This is
the state currently present and working in this EasyHybrid3 checkout and the
paired `pDynamo3` checkout on this machine (macOS/Apple Silicon, CPU only).

GPU support via `gpu4pyscf` was prototyped on a separate Linux machine
(`[remote Linux host]`) but is **not** part of this checkout — that machine has its own
independent conda env and its own copy of `pDynamo3`'s
`addOns/pySCF/QCModelPySCF.py`. Nothing GPU-related is installed or wired in
here.

## Prerequisite

```
pip install pyscf
```

installed into the same Python environment EasyHybrid3/pDynamo3 run under
(the one pointed to by `EASYHYBRID3_PYTHON` / `PDYNAMO3_PYTHONCOMMAND`).

## Files changed

### 1. `src/gui/windows/setup/setup_qc_model_window.glade`

Added a new `GtkWindow id="window_setup_pyscf"` dialog (Method dropdown,
Functional dropdown, Orbital Basis dropdown, Scratch Folder entry, "Delete
job files" checkbox, OK/Cancel buttons), built by copying the structure of
the existing `window_setup_xtb` dialog. The Functional and Orbital Basis
fields are empty `GtkBox` placeholders (`box_pyscf_functional`,
`box_pyscf_basis`, same pattern as `box_pyscf_method`), each filled in at
runtime with `Gtk.DropDown` and `Gtk.Entry` controls. Each offers a curated
dropdown list and an adjacent editable text field, so users can enter any
PySCF/Libxc-recognized name directly.

### 2. `src/gui/windows/setup/windows_and_dialogs/qc_setup/setup_pyscf.py` (new file)

`SetupPySCFWindow` class that drives the new glade dialog, modeled directly
on `setup_xtb.py`.

- `parameters` dict: `method` (`RHF`/`UHF`/`RKS`/`UKS`), `functional`,
  `orbitalBasis`, `deleteJobFiles`, `scratch`.
- **Functional** combobox: 79 named PySCF/Libxc functionals (`B3LYP`, `PBE0`,
  `CAM-B3LYP`, `WB97X-D`, `HSE06`, ...), only used when Method is `RKS`/`UKS`.
  Sourced from `pyscf.dft.libxc.XC_ALIAS` plus other well-known named
  hybrids/range-separated functionals, each re-validated with
  `pyscf.dft.libxc.parse_xc(name)` on the installed pyscf (2.14.0) before
  being written into the list. Raw exchange-only/correlation-only fragments
  (e.g. `B88`, `LYP` alone) are excluded since they aren't valid standalone
  `xc=` values on their own; the field is still editable, so an explicit
  `"exchange,correlation"` string (e.g. `pbe,pbe`) can be typed in directly.
- **Basis** combobox: 18 common PySCF-recognized basis sets (`STO-3G` through
  `def2-QZVP`), also editable/free-text for anything else PySCF recognizes.
- **Method**: deliberately kept to `RHF`/`UHF`/`RKS`/`UKS` only (not widened
  to PySCF's full method zoo). pDynamo3's own `addOns/pySCF/__init__.py`
  states only these four mean-field methods are supported for QC/QM-MM
  energies and gradients, and `QCModelPySCF.Energy()` relies on
  `state.mf.nuc_grad_method()`, an analytic-gradient path only guaranteed for
  these four — post-HF methods (MP2/CCSD/...) don't expose gradients the
  same way and would silently break QM/MM forces. Widening this is a
  pDynamo3-level change, out of scope here.

### 3. `src/gui/windows/setup/windows_and_dialogs/qc_setup/qcmodel_window.py`

- Imports and instantiates `SetupPySCFWindow`.
- `qc_engine_id == 4` is now `'PySCF'` in the `QC_engines` dict (was a
  commented-out/dead `MOPAC` slot — `QCModelMOPAC` is not exported by
  `pMolecule.QCModel`, so that branch could never have worked, and
  `'MOPAC'`/`'sparrow'` were already commented out of the combobox, so index
  4 was unreachable dead code). `MOPAC` was renumbered to the next free,
  still-commented-out slot `5`; `setup_mopac_window` itself is untouched.
- The Setup button for `qc_engine_id == 4` now opens `setup_pyscf_window`
  instead of `setup_mopac_window`, and the `parameters` dict assembled for
  the energy calculation is populated from
  `setup_pyscf_window.parameters` (`method`, `functional`, `orbitalBasis`,
  `deleteJobFiles`, `scratch`) instead of the old MOPAC fields.

### 4. `src/pdynamo/pDynamo2EasyHybrid/session.py`

- `from addOns.pySCF import QCModelPySCF, NBModelPySCF` wrapped in
  `try/except ImportError` (sets both to `None` on failure), so EasyHybrid3
  still starts normally if `pyscf` isn't installed. Reachable because
  `easyhybrid.py` already does `sys.path.append(PDYNAMO3_HOME)` at startup.
- New `elif parameters['qcengine'] == 'PySCF':` branch in
  `define_a_new_QCModel`: if `QCModelPySCF is None`, shows a "PySCF not
  installed" dialog (same pattern used elsewhere in this file) and returns
  `None` instead of crashing; otherwise builds
  `QCModelPySCF.WithOptions(deleteJobFiles=..., functional=..., method=...,
  orbitalBasis=...)`.
- New `elif parameters['qcengine'] == 'PySCF':` branch wherever the NBModel
  is defined for QM/MM: `system.DefineNBModel(NBModelPySCF.WithDefaults())`.

`charge`/`multiplicity`/`isSpinRestricted` are not passed directly into
`QCModelPySCF.WithOptions` — `define_a_new_QCModel` already sets
`system.electronicState` generically before the per-engine branch runs (same
as every other engine), and `QCModelPySCF.CreateMole` reads
`target.electronicState.charge`/`.multiplicity` from there.

`scratch` is collected in the GUI dialog for consistency with the other
engines but not passed to `WithOptions` — `QCModelPySCF._CheckOptions`
unconditionally derives `pySCFscratch` from the `PYSCF_TMPDIR` /
`PDYNAMO3_SCRATCH` environment variables, so a passed-in value would be
silently overwritten anyway.

## Verification

Exercised the exact `QCModelPySCF.WithOptions(...)` / `NBModelPySCF.WithDefaults()`
call now used in `session.py`, using the same `parameters` dict shape that
`qcmodel_window.on_button_ok()` assembles for `qc_engine_id == 4`, against
pDynamo3's own `waterDimer_cs` QM/MM test system (OPLS MM model, 3 QM atoms,
RHF/3-21G and, separately, RKS/PBE0). Both matched pDynamo3's own
`examples/addOns/pySCF/PySCFExample.py` output for the same
system/method/basis, and `SystemGeometryObjectiveFunction.TestGradients()`
confirmed analytical vs. numerical gradients agree (max difference
~0.0003).

## Not covered / left for follow-up

- `mf_kwargs` / `mole_kwargs` (advanced PySCF `Mole`/`SCF` keyword overrides,
  e.g. custom DIIS) are not exposed in the GUI — `QCModelPySCF.WithOptions`
  defaults them to empty dicts.
- No dedicated NBModel choice for PySCF beyond `NBModelPySCF.WithDefaults()`
  (mirrors what ORCA/xTB do — they also just call `.WithDefaults()`).
- GPU support (`gpu4pyscf`) is not part of this checkout — see Summary above.
- Method is intentionally restricted to `RHF`/`UHF`/`RKS`/`UKS`.

## Related fixes made alongside this integration

Found while cross-checking xTB/DFTB+ against the new PySCF integration and
while actually exercising PySCF QM/MM systems. All of the below are applied
and working in this checkout (EasyHybrid3) and the paired `pDynamo3`
checkout on this machine.

### xTB: GFN-FF added as a 4th dropdown option

`setup_xtb.py`'s combobox only offered `GFN1-xTB`, `GFN2-xTB`, `g-xTB`.
`xtb 6.7.1`'s own `--help` also supports `--gfnff`/`--gff` (a separate
force-field method), which pDynamo3's `QCModelXTB.py` never emitted. Added
`GFN-FF` as a 4th combobox option; `self.parameters['gfn']` is `'ff'` for
this option (string, vs. the integer 1/2/3 used for the others), and
`QCModelXTB.Execute()`'s command-builder gained an `elif self.gfn == 'ff':
cpus = ' --gfnff '` branch alongside the existing `--gfn N` and (untested,
`g-xTB`) `--gxtb` branches. Verified `--gfnff` runs cleanly and a full
`QCModelXTB.WithOptions(gfn='ff', ...)` energy+gradient calculation
completes correctly.

### xTB: pure-QC jobs no longer hang forever

`QCModelXTB.WriteInputFile()` only ever wrote content to the `--input`
xcontrol file for QM/MM jobs (the `$embedding` block); for pure-QC jobs the
file was opened, left completely empty, and never closed. This installed
`xtb 6.7.1` hangs indefinitely when given an empty `--input` file (no `xtb`
process even appears in `ps aux`), but returns instantly given the same file
with just a minimal `$end\n` block. Fixed by adding an `else: inFile.write(
'$end\n')` branch and closing the file in both branches (`inFile.close()`
was missing from both). Affects every pure-QC xTB calculation on this xtb
version, regardless of GFN type — unrelated to the GFN-FF work, just never
previously triggered. Verified: pure-QC `gfn=2` and pure-QC `gfn='ff'` both
now complete on `waterDimer_cs`; QM/MM xTB (already unaffected) still works
identically.

### PySCF: systems with a PySCF QC model couldn't be pickled

`QCModelPySCF._CheckOptions()` sets `self.pyscf = pyscf` — a live reference
to the imported Python module — as an instance attribute, and Python modules
can't be pickled. This broke saving a system to a `.pkl`
(`TypeError: cannot pickle 'module' object`) and broke EasyHybrid3's
Advanced Relaxed Surface Scan, which pickles `parameters['system']` to hand
off to a `multiprocessing.Process` worker. ORCA/xTB/DFTB+ never hit this
because they run as external subprocess binaries; PySCF runs in-process.

Fixed in pDynamo3's `addOns/pySCF/QCModelPySCF.py` using its existing
`_unpicklable` mechanism (`pCore.AttributableObject`'s `__getstate__` skips
any attribute name listed there):

```python
_unpicklable  = set ( QCModel._unpicklable )
_unpicklable.update ( { "mf", "mole", "pyscf" } )
```

(`mf`/`mole`, the live PySCF calculation-state objects built in
`CreateMole()`, are excluded for the same reason and are already always
rebuilt fresh at the start of every `Energy()` call, so excluding them from
the pickled state changes no behavior.) `Energy()` gained a one-line
self-heal at its top so a system reloaded via `Unpickle()` (where
`self.pyscf` is now `None`) re-imports pyscf on first use:

```python
def Energy ( self, target ):
    if self.pyscf is None: self._CheckOptions ( )
    ...
```

Verified: `Pickle()`/`Unpickle()` round-trip on a `waterDimer_cs` system with
a PySCF `qcModel` attached now succeeds (previously raised `TypeError`), and
the reloaded system's `Energy(doGradients=True)` reproduces the same
QC energy as before pickling. Also reproduced the exact
`multiprocessing.reduction.ForkingPickler` path directly (what `spawn`/`Popen`
uses internally) — now succeeds where it previously raised the identical
`TypeError`.


## 11.13 GPU PySCF changes (EasyHybrid3)

## Scope and comparison baseline

This report describes the local EasyHybrid3 changes that expose pDynamo3's
PySCF QC model in the GUI and allow users to select its optional GPU4PySCF
backend.

The comparison baseline is EasyHybrid3 Git commit `d578240`, the current
`HEAD` of this checkout before the uncommitted PySCF integration changes.
Only PySCF/GPU-related files are covered here.

EasyHybrid3 does not implement a separate GPU computational kernel. It passes
the selected options to `pDynamo3/addOns/pySCF`, where CPU PySCF or GPU4PySCF
performs the calculation.

## Files changed

### `src/gui/windows/setup/setup_qc_model_window.glade`

Added the PySCF setup window with controls for:

- Method
- DFT functional
- Orbital basis
- Scratch directory
- Delete-job-files option
- `Run on GPU (gpu4pyscf)` option

The GPU option is disabled by default.

### `src/gui/windows/setup/windows_and_dialogs/qc_setup/setup_pyscf.py`

New controller for the PySCF setup window.

- Provides the methods `RHF`, `UHF`, `RKS`, and `UKS`.
- Provides editable functional and basis-set fields. The lists contain common
  values, but users may enter other values supported by PySCF.
- Stores the `useGPU` checkbox state with the other PySCF parameters.

### `src/gui/windows/setup/windows_and_dialogs/qc_setup/qcmodel_window.py`

- Added PySCF to the QC-engine list as engine ID 4.
- Opens the PySCF setup window when PySCF is selected.
- Passes `method`, `functional`, `orbitalBasis`, `deleteJobFiles`, `scratch`,
  and `useGPU` to the pDynamo session layer.

### `src/pdynamo/pDynamo2EasyHybrid/session.py`

- Imports `QCModelPySCF` and `NBModelPySCF` conditionally so EasyHybrid can
  still start when PySCF is not installed.
- Checks GPU4PySCF availability with
  `importlib.util.find_spec("gpu4pyscf")` without importing it in the parent
  GUI process.
- Creates `QCModelPySCF` with the selected method, functional, basis, file
  cleanup option, and `useGPU` value.
- Uses `NBModelPySCF` for PySCF QM/MM calculations.
- Displays an error and stops model creation when the requested PySCF or
  GPU4PySCF dependency is unavailable.

The non-importing GPU4PySCF check is required because EasyHybrid launches
calculations with `multiprocessing.Process` on Linux. Importing GPU4PySCF in
the parent process can initialize CUDA before `fork`, causing CUDA
initialization failures in the child process. The real GPU4PySCF import is
deferred to pDynamo's calculation worker.

## GPU-specific runtime files outside the EasyHybrid repository

The GPU launcher uses:

- `~/.local/bin/easyhybrid`
- Stable Conda environment `~/software/envs/pdynamo3`
- The bundled `EasyHybrid3/src/graphics_engine` source tree

The stable environment provides both CPU PySCF and GPU4PySCF. It uses Python
3.10.20, NumPy 1.26.4, CuPy 13.6.0, PySCF 2.14.0, and GPU4PySCF 1.8.1. The
bundled VisMol Cython extensions and all pDynamo CPU/GPU paths were verified
in this environment, so neither a separate graphics-engine copy, GPU Conda
environment, nor GPU-specific launcher is necessary.

## Verification

The GUI GPU path was verified with:

- System: alanine dipeptide, 22 atoms
- QC engine: PySCF
- Method: RKS
- Functional: B3LYP
- Basis: 3-21G
- GPU option: enabled
- Calculation: QM/MM single-point energy

The calculation completed through EasyHybrid's process manager after moving
the GPU4PySCF import into the worker process.

## Performance status

EasyHybrid only selects and launches the pDynamo PySCF backend, so it has no
independent GUI acceleration value. Backend benchmark results are documented
in the pDynamo3 GPU_PYSCF_CHANGES.md report.

On the saved 41,925-atom relaxed-PES system with 71 QM atoms and
RKS/PBE/3-21G, replacing the original scalar MM-center gradient loop with the
blocked PySCF/GPU4PySCF implementation reduced full GPU energy/gradient calls
from a median of 628.651 s to 41.122 s: **15.29x speedup**. Energy was
unchanged and gradients agreed to approximately `2.4e-13 kJ mol-1 A-1` RMS.

This is acceleration of the pDynamo/GPU4PySCF calculation launched by
EasyHybrid, not acceleration of the GUI itself. The saved benchmark script and
JSON results are in the calculation's `dft/benchmarks` directory.

A smaller isolated CPU test measured 2.181x speedup for 100 MM centers and
7.255x for 1,000 MM centers. These values measure the changed gradient kernel
and should not be interpreted as universal end-to-end speedups.

No controlled CPU-versus-GPU timing series is reported because none was saved and the
NVIDIA driver was unavailable during the 2026-08-22 report update. No general
GPU acceleration factor is claimed.

## How to run

Launch EasyHybrid for either CPU or GPU work:

```bash
easyhybrid
```

In the QC-model window, select PySCF and enable `Run on GPU (gpu4pyscf)` for
GPU execution. Leave it disabled for CPU execution. For scripted work, use
`activate_pdynamo3` and set `useGPU=True` or `False` on `QCModelPySCF`.

## Known limitations

- GPU execution requires a working NVIDIA driver.
- The exposed mean-field methods are `RHF`, `UHF`, `RKS`, and `UKS`.
- The scratch value is collected by the GUI, while the current pDynamo PySCF
  model obtains its scratch path from `PYSCF_TMPDIR` or `PDYNAMO3_SCRATCH`.
- GPU acceleration depends on system size and method; no universal speedup is
  implied.

## Final unified-installation validation (2026-08-31)

The final installation has one public activation command, one environment,
one pDynamo source tree, one EasyHybrid source tree, and one GUI launcher:

- `activate_pdynamo3`
- `~/software/envs/pdynamo3`
- `~/software/pDynamo3`
- `~/software/EasyHybrid3`
- `easyhybrid`

CPU/GPU selection is a model option rather than an environment choice:
`QCModelPySCF(useGPU=False)` uses CPU PySCF and `useGPU=True` uses
GPU4PySCF. The EasyHybrid checkbox exposes the same option.

Final checks:

- `pip check`: no broken requirements.
- NVIDIA GeForce RTX 4060 Ti detected (one CUDA device).
- NumPy 1.26.4, SciPy 1.15.3, PySCF 2.14.0, CuPy 13.6.0, and
  GPU4PySCF 1.8.1.
- pDynamo H2/RHF/STO-3G CPU energy: `-2932.051561066158 kJ mol-1`.
- pDynamo H2/RHF/STO-3G GPU energy: `-2932.051561066207 kJ mol-1`.
- Absolute CPU/GPU difference: `4.957e-11 kJ mol-1`.
- All seven compiled VisMol utility extensions imported from the bundled
  `EasyHybrid3/src/graphics_engine`; five bundled fonts were found.
- EasyHybrid's main window and PySCF setup controller imported successfully.
- The real `easyhybrid` GUI launcher remained alive until an intentional
  six-second timeout. Its only output was a nonfatal Fontconfig warning.

The obsolete GPU-specific environments, graphics-engine copy, launchers, and
experimental pDynamo source copies were removed after these checks passed.


## 11.14 GPU PySCF on [remote Linux host] (EasyHybrid3)

This is a follow-up to Section 11.12 (the CPU-only PySCF QC engine,
working identically on both machines). This document covers only the
GPU-specific work, which exists **exclusively on `[remote Linux host]`**
([redacted IP]), the Linux lab machine with an NVIDIA GPU (RTX 4060 Ti,
8 GB). None of it is installed, cloned, or wired in on the Mac — there is no
GPU there to use.

Verified live on `[remote Linux host]` on 2026-08-18 by re-checking the actual files,
installed packages, and env layout over SSH (not just recalled from an
earlier report).

## One stable CPU/GPU environment

| Conda env | PySCF | GPU (`gpu4pyscf`) | NumPy | CuPy | Activate with |
|---|---|---|---|---|---|
| `~/software/envs/pdynamo3` (Python 3.10.20) | 2.14.0 | `gpu4pyscf-cuda12x` 1.8.1 | 1.26.4 | 13.6.0 | `activate_pdynamo3` for scripting or `easyhybrid` for the GUI |

CuPy 13.6.0 satisfies GPU4PySCF's supported `cupy>=13` range while retaining
NumPy 1.26.4 compatibility required by existing pDynamo add-ons. The stable
environment contains all CPU and GPU packages. GPU use is selected by
`useGPU=True` in scripts or the `Run on GPU` checkbox in EasyHybrid.

Both `PDYNAMO3_HOME` and `EASYHYBRID_HOME` point at the single source
checkouts (`~/software/pDynamo3` and `~/software/EasyHybrid3`).

## Shared `vismol` graphics engine

EasyHybrid3's bundled `src/graphics_engine` is used for both CPU and GPU
calculations. Its Python 3.10 Cython extensions were verified with stable
NumPy 1.26.4, including all seven compiled `vismol.utils` modules. The
EasyHybrid activation script uses the bundled tree directly:

   ```bash
   export PYTHONPATH="$EASYHYBRID_HOME:$EASYHYBRID_HOME/src:$EASYHYBRID_HOME/src/graphics_engine/src:$PDYNAMO3_HOME${PYTHONPATH:+:$PYTHONPATH}"
   ```

The former isolated `graphics_engine_gpu_build` copy was removed because its
Python sources had become stale and caused API mismatches such as the missing
`list_available_fonts` import.

## `QCModelPySCF.py`: `useGPU` option

`~/software/pDynamo3/addOns/pySCF/QCModelPySCF.py` (this file has no version
control of its own on this machine — verified directly by reading it, not
via diff):

- `_GPU4PySCFFound = importlib.util.find_spec('gpu4pyscf') is not None` —
  availability check that does **not** execute the module (see "fork
  safety" below for why that distinction is load-bearing).
- New attributable options: `"gpu4pyscf": None`, `"useGPU": False`.
  `_CheckOptions()` raises `NotInstalledError` if `useGPU` is set but
  `_GPU4PySCFFound` is `False`.
- `CreateMole()`: when `useGPU` is set, `import gpu4pyscf` /
  `import gpu4pyscf.qmmm` happen **inside this method** (not at module
  level), and the mean-field object is built from `gpu4pyscf.scf.RHF/UHF` or
  `gpu4pyscf.dft.RKS/UKS` directly (`mf_kwargs` applied as attributes
  afterward, since `gpu4pyscf` has no `Mole.apply()`-style dispatcher the
  way plain `pyscf` does), and QM/MM point charges go through
  `gpu4pyscf.qmmm.add_mm_charges` instead of `pyscf.qmmm.add_mm_charges`.
- `_unpicklable` (the pickling-safety mechanism from Section 11.12)
  also includes `"gpu4pyscf"`, for the same live-module-reference reason as
  `"pyscf"`.

## `QCMMElectrostaticModelPySCF.py`: cupy → numpy conversion

Confirmed present at
`~/software/pDynamo3/addOns/pySCF/QCMMElectrostaticModelPySCF.py`.
`gpu4pyscf`'s mean-field objects return `cupy` (GPU-resident) arrays from
methods like `mf.mm_mol.atom_coords()` / `mf.make_rdm1()`; the rest of this
module does plain `numpy` math on them, which fails when the array is
`cupy`'s. A small `_AsNumpy()` helper (no-op when `cupy` isn't importable,
or when the array already is plain `numpy`) is applied at every point QM/MM
gradient data is pulled off `target.qcState.mf`. `target.qcState.mole` is
always a plain `pyscf.gto.Mole` regardless of `useGPU`, so it never needs
converting — only `mf`-derived quantities do.

## GUI: "Run on GPU (gpu4pyscf)" checkbox

Same pattern as every other PySCF field in Section 11.12. Confirmed
present in this EasyHybrid3 checkout (shared by both machines, only exercised
with the checkbox enabled here):

- `setup_pyscf.py`: `parameters['useGPU']` (default `False`), a checkbox
  widget wired the same way as `deleteJobFiles`.
- `session.py`: `_GPU4PySCFAvailable = importlib.util.find_spec('gpu4pyscf')
  is not None` (same non-importing check as in `QCModelPySCF.py`, for the
  same reason). In the `qcengine == 'PySCF'` branch of
  `define_a_new_QCModel`, if `useGPU` is requested but `gpu4pyscf` isn't
  available, shows a "gpu4pyscf not installed" dialog and returns `None`
  instead of crashing; otherwise `useGPU=parameters.get('useGPU', False)` is
  passed into `QCModelPySCF.WithOptions(...)`.

## The real bug: CUDA contexts are not fork-safe

Found only by running a GPU calculation through the live GUI, not scripted
tests.

**Symptom**: selecting PySCF, checking "Run on GPU", running Single Point
Energy through the GUI failed with
`cudaErrorInitializationError: initialization error` from inside
`gpu4pyscf/lib/logger.py`'s `cupy.cuda.Event()` call.

**Root cause**: EasyHybrid3 runs every simulation in a separate worker
process via `multiprocessing.Process`
(`src/pdynamo/pDynamo2EasyHybrid/simulations_mixin.py`), using the platform
default start method — **`fork`** on Linux (confirmed: no
`get_context('spawn')` or `set_start_method` calls anywhere in
`simulations_mixin.py` or `p_methods/surface_scan.py` on either machine —
both still use plain `multiprocessing.Process`, i.e. fork). `fork()`
duplicates the parent's memory, including any already-initialized CUDA/cupy
state. If `gpu4pyscf` had been imported at module level, it would run the
instant EasyHybrid3 starts, long before any user action — so by the time a
simulation forks a worker, the parent's CUDA context is already poisoned for
that worker.

**Rejected fix: force `spawn`.** The textbook fix for CUDA + fork is to
force `spawn`, which starts a genuinely fresh interpreter per worker. This
fixed the CUDA error but broke pickling of the `System` object being handed
to the worker in ways `fork` never required:
`system.tree_row`/`system_choice_row` (live GTK row objects
EasyHybrid attaches for its own interface bookkeeping — unpicklable) and
`system._energyClosures` (local closure functions built when models are
attached — unpicklable by nature). This would have meant excluding
attributes one crash at a time with no guarantee of ever reaching the end of
the list, so this approach was abandoned and `simulations_mixin.py`/
`surface_scan.py` were left on plain `fork`.

**Actual fix: lazy `gpu4pyscf` import.** Since `fork()` itself isn't the
problem — only *having already touched CUDA in the parent* is — both
formerly-eager `import gpu4pyscf` call sites (`session.py`'s and
`QCModelPySCF.py`'s) were replaced with the non-executing
`importlib.util.find_spec('gpu4pyscf') is not None` check described above.
The real `import gpu4pyscf` now only runs inside `CreateMole()`, at the
moment an energy is actually computed — which, under fork, always happens
inside the already-forked worker, never in the parent GUI process. The
parent's CUDA/cupy state is therefore never touched, so each worker
initializes its own clean CUDA context from scratch.

## Verification

Live GUI run on `[remote Linux host]` (real system, real clicks): alanine dipeptide (22
atoms), PySCF engine, Method RKS, Functional b3lyp, Orbital Basis 3-21G,
"Run on GPU" checked → Single Point Energy → Process Manager reported
**Finished**, log confirmed `Run On GPU = True` and a QM/MM energy consistent
with the CPU path on the same system. This was the first GPU-accelerated
PySCF QM/MM energy computed through EasyHybrid3's GUI, using the unmodified
fork-based worker mechanism.

## How to reproduce

```bash
# CPU or GPU GUI (choose with the Run on GPU checkbox)
easyhybrid

# CPU or GPU scripted/headless (choose with QCModelPySCF useGPU)
activate_pdynamo3
python3 your_script.py
```

In the GUI: select **PySCF** as the QC engine, open its setup dialog, check
**"Run on GPU (gpu4pyscf)"**, and set Method/Functional/Basis as usual. Leave
the checkbox disabled to use CPU PySCF in the same environment.

## Final system audit (2026-08-31)

The machine now exposes only `activate_pdynamo3` for pDynamo scripting and
`easyhybrid` for the GUI. Both CPU and GPU calculations use:

```text
Environment: ~/software/envs/pdynamo3
pDynamo:     ~/software/pDynamo3
EasyHybrid:  ~/software/EasyHybrid3
Graphics:    ~/software/EasyHybrid3/src/graphics_engine
```

There are no `*_gpu`, EasyHybrid-specific activation, batched-pDynamo, or
pairlist-fix activation commands remaining. The useful pair-list memory fix
was transferred into the main pDynamo tree before its experimental copy was
deleted.

The final audit confirmed no broken Python requirements, one visible RTX
4060 Ti, a converged GPU4PySCF calculation, CPU/GPU pDynamo H2 energies
agreeing within `4.957e-11 kJ mol-1`, successful official CPU and pair-list
examples, all bundled VisMol extensions, and successful EasyHybrid GUI
startup through the sole `easyhybrid` launcher.


## 11.15 Test suite usage notes

## Run

The current suite needs the project Python dependencies and compiled VisMol
extensions, but does not need a GTK display or OpenGL context:

```sh
python -m pytest -q -p no:cacheprovider tests/
```

If the extensions are missing, build them with
`bash src/graphics_engine/install.sh`. That command writes generated sources and
binaries into the graphics source tree. For a non-mutating build, follow the
temporary-copy command in [Section 6 of this report](#6-reproducible-test-baseline).

## Coverage

- `test_bond_order_perception.py` tests pure bond-order perception, including
  valence bounds, input-order independence, aromatic rings, and QC/MM boundary
  handling.
- `test_atom_ops_bonds.py` tests bond edits against a generated in-memory
  molecule, refresh behavior for sticks, and per-frame dynamic-bond edits.
- `test_md_analysis.py` checks GTK-independent RMSF, RDF and box-density
  calculations, plus an import guard that rejects GTK imports.
- `test_gtk_version.py` checks the installer's minimum-version predicate:
  GTK 4.6 is rejected, while GTK 4.8 and newer are accepted. This unit test
  does not run the application on those GTK versions.
- `test_gtk4_compat.py` exercises capability-driven Gtk.Picture and scroll
  behavior using both available and legacy API shapes.
- `test_gtk_builder_icon_assets.py` verifies every file-backed GtkImage path
  resolves relative to its Glade file.
- `test_gtk_icon_theme_smoke.py` is opt-in. It constructs and closes a real
  Gtk.ApplicationWindow with fatal GTK criticals on a selected display, and
  separately verifies that a no-display test process is rejected before
  GApplication registration. Run it with
  `EASYHYBRID_RUN_GTK_GUI_TESTS=1` and, for the missing-display probe,
  `EASYHYBRID_RUN_GTK_ENV_DIAGNOSTIC=1`.
- `test_easyhybrid_menu_vismol_components_open_and_close_cleanly`
  runs when `EASYHYBRID_RUN_GRAPHICS_TESTS=1`. It puts EasyHybrid's production
  GTK menu and bundled VisMol widget in a test-created GTK window, loads a
  generated three-atom water PDB, checks atoms/bonds, counts representation
  draws, checks GL errors, and opens/closes the component host. Matrix jobs set
  a 20-cycle count and call the GTK gesture callbacks with test coordinates;
  they do not inject native OS pointer events. It does **not** construct
  `EasyHybridApplication` or the real `gui.main.MainWindow`; therefore it is
  component/renderer evidence, not full-interface acceptance. A separate full-app
  regression with real pDynamo3 is still required across the supported GTK/OS
  matrix. The full-app regression performs one production `.easy` save/reload
  in each cycle; it currently passes locally on Linux X11 with GTK 4.14.5 and
  native XTest pointer injection. Other OS/minor combinations are not covered
  by that local run. pDynamo3 scientific calculations remain tested against
  pDynamo3.
- `test_dependency_boundaries.py`, `test_session_state.py`,
  `test_easyplot_boundaries.py`, and `test_os_integration.py` cover the
  EH4-100 import, state, plotting, and startup-policy boundaries.
- `conftest.py` builds a minimal fake VisMol session and deterministic atoms,
  connectivity, and zero-coordinate frames. It does not construct a GTK or GL
  session or call pDynamo calculations.
- `test_pdynamo_mm_workflow.py` is opt-in and requires a compiled pDynamo3
  checkout plus its parameter directory. It checks the bundled DYFF water
  energy/minimization and AM1 water single-point baselines, then exercises
  EasyHybrid's production MNDO QC/MM model setup on pDynamo's water dimer.
  That case checks the QC atom selection, charge/multiplicity, AM1 method,
  nonbonded model, unchanged single-point coordinates, reference energy and
  analytic/numerical gradients. Local Linux x86_64 evidence is **3 passed** at
  Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 with pDynamo3
  revision `09e583049de5d1cdca6c9b4009c7c75e451a5ae0`; Claude independently
  replayed the focused checks against CI-pinned pDynamo3
  `6b28dd8958e1a705fcdca130f4ab862a8af8de82`. The merged headless runner
  (`.github/scripts/run_scientific_tests.py`) passed **26 tests in 1.24 s**
  locally with display variables removed. This task's own 30-cell matrix is
  still pending.

The default suite skips display-dependent GTK checks. The opt-in GTK smoke
must be run with an accessible native display or virtual display. The full-app
smoke covers one generated `.easy` save/reload fixture on the tested local
Linux runtime; it does not prove persistence for other project contents,
scientific simulation results, export round trips, or cross-platform support.
Those checks are tracked in `docs/ROADMAP.md` and Section 6 of this report.
Fixture requirements are documented in [Section 8 of this report](#8-safe-test-data-policy).


## 11.16 Graphics engine fixes patch

[`GRAPHICS_ENGINE_FIXES.patch`](GRAPHICS_ENGINE_FIXES.patch) is a tracked
patch file moved here from the repository root. It proposes changes to
`vismol_gtkwidget.py` and `vismol_glcore.py` for forwarding GTK release events
to context menus, positioning popovers at the triggering pointer, and
initializing/guarding selection-box coordinates.

The patch is **not applied** to the working source. A correctly rooted dry
run from the graphics-engine directory fails:
`patch --dry-run -p1 < ../../docs/GRAPHICS_ENGINE_FIXES.patch`. The GTK widget
hunks and three graphics-core hunks fail; one legacy selection guard hunk
succeeds with fuzz. No files were modified by the check.

Hunk-by-hunk comparison against the current source:

- Event forwarding from GTK to `VismolGLCore.mouse_released()` is already
  present. The active GTK4 `Gtk.GestureClick` callback also saves its local
  pointer coordinates before dispatch.
- Selection-box initialization and the null guard are already present in the
  active motion handler; the saved patch targets an older source version.
- The patch proposes `Gtk.Popover.popup_at_pointer(event)`. The official
  [GTK4 Gtk.Popover API](https://docs.gtk.org/gtk4/class.Popover.html) lists
  `set_pointing_to()` and `popup()`, but not `popup_at_pointer()`. Current
  GTK4 code anchors a `Gdk.Rectangle` from gesture coordinates with
  `set_pointing_to()` and calls `popup()`.
- `show_gl_menu()` accepts but does not use the optional event because the
  gesture coordinates are retained directly. No behavior change is justified.

**Disposition:** event forwarding and selection guards are already implemented;
the menu hunk is obsolete and GTK4-incompatible. Do not apply this patch. Its
original date is 2026-08-31. The audit used local Linux GTK 4.14.5 source;
Windows/macOS, GTK 4.8/current stable and every other untested GTK minor,
native display backends and real GL
contexts are **NOT TESTED**.
