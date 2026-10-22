# EasyHybrid4 Codex instructions

Before **every** coding session, read `docs/ROADMAP.md` in full. Treat it as the authoritative task queue. Read `docs/EASYHYBRID4_REPORT.md` for consolidated repository, compatibility, test, and limitation status. Select the next eligible unchecked task, work incrementally, add tests, run only tests you can actually execute, and record OS/architecture and exact GTK runtime versions in the roadmap evidence log. Never claim Linux tests prove macOS/Windows support. Do not mark a task complete unless its acceptance criteria pass. Preserve scientific calculations, project compatibility and published graphics submodule reachability. Update the roadmap and consolidated report before ending.

**Native GTK acceptance:** before merging an implementation to `main`, run the full `.github/workflows/native-gtk-matrix.yml`: Linux x86_64, Windows x86_64 and macOS arm64 for every released GTK4 minor from 4.8 through the supported latest; also Intel macOS cells where provisioned. The GTK component matrix must run the production menu/VisMol renderer smoke through at least 5 open/callback-pick/render/close cycles per cell (reduced from 20 on 2026-10-20 at the maintainer's request: 20 cycles cost about 4 minutes per macOS job and macOS runners queue in waves). The component harness calls GTK gesture callbacks with test coordinates; it does not inject an OS pointer event, and its isolated host is not the EasyHybrid4 interface. The separate full-app harness launches `EasyHybridApplication` and production `MainWindow` with real pDynamo3, loads a generated fixture, injects native OS pointer events through the production GTK pick path, and checks clean close. Keep component and full-app results separate. Read the uploaded runtime artifact and confirm the actual GTK patch version, OS/architecture, Python, PyGObject and GL backend; a green job or requested matrix label alone is not version evidence. Physical GPU, Retina, trackpad and Wayland results remain separate claims.

**Failure protocol:** inspect the first failing assertion/native stack and the affected job's uploaded runtime log before starting another run. Identify whether it is application code, GTK/backend behavior, test setup or missing dependency; make one focused correction, run the smallest relevant check once, then run the full matrix once. Do not launch overlapping or repeated matrices, rerun passing cells, or push a test-only retry before understanding the failure. If CI fails, fix that failure and rerun the failed coverage in the same work sequence before adding more checks.

**Known GTK CI traps (verified 2026-10-19):** GTK 4.16/4.18 Linux distro builds use EGL on X11 even when `GDK_DEBUG=gl-glx` is requested; do not force PyOpenGL GLX for the EasyHybrid scene. Fedora's optional `OpenGL_accelerate` may have a NumPy ABI mismatch; its scene smoke uses PyOpenGL's ctypes path. Windows async native COM file-dialog cancellation can disconnect GTK's callback apartment and crash GLib iteration; keep the tested in-process chooser policy and fatal-exception log guard. GTK 4.8/4.10 Windows needs the legacy WGL pixel-format adapter. GTK event positions are logical widget coordinates, while VisMol picking/drag math uses GL framebuffer pixels; route all press/release/motion coordinates through `src.gtk4_compat.widget_to_framebuffer_coordinates()` using measured widget and framebuffer dimensions. HiDPI oxygen picking passed 20 independent open/pick/render/close cycles locally at GTK 4.14.5 on native Linux X11/NVIDIA with `GDK_SCALE=2`. Expanded matrix run `39307131433` passed all 19 Linux/Windows cells, but all 11 macOS Apple Software Renderer cells returned no atom ID from the exact RGB picking pass. Disabling dithering alone failed in `39309838872`; disabling blend, dither, sRGB and multisample state in `_pick()` still fails on native macOS: run `39311621966` GTK 4.12.1 artifact reads white clear color/background ID at the valid projected coordinate with GL error 0. GTK GLArea source binds its own FBO before render; do not rebind framebuffer zero without contrary evidence. Local native Linux GTK 4.14.5/NVIDIA passed 20/20 picks, which does not validate macOS. Next diagnose selection draw execution and framebuffer/readback on native macOS, make one evidence-based correction, run affected macOS cells, then the full 30-cell matrix with 20 successful open/pick/render/close cycles per cell. Run `39311621966` completed with 19/30 passing; all 11 macOS cells fail picking. `setup-micromamba@v3.2.1` using unpinned latest micromamba lookup transiently failed; pin `2.9.0-0`, since 2.8.x rejects the Windows GTK 4.8/4.10 `--skip-run-link-scripts` flag. The latest prior full exact-version matrix `39292753361` passed all 30 cells but did not test this coordinate-picking change. pDynamo3 scientific tests are separate and must run against the pDynamo3 environment.

**EH4-202 picking memory (resolved 2026-10-19):** macOS core-profile OpenGL reports `GL_LINE_WIDTH_RANGE` (0.1, 1.0): `glLineWidth()` above 1 px is ignored. VisMol's colour-ID pick pass widened the lines/nonbonded/dashed selection geometry with `glLineWidth`, so on every macOS cell the ID line was 1 px and a click at an atom's projected centre read the background. Disabling blend/dither/sRGB/multisample was not the cause. The selection geometry shaders now emit fixed-pixel-width quads with square caps at atom ends (`vismol/libgl/shaders/pick_lines.py`); never reintroduce `glLineWidth`-based hit regions. Hidden per-atom picking spheres were rejected: they make hidden atoms (for example solvent) pickable. Run `39317377076` passed 30/30 with 20 cycles x 9 click points per cell.

**macOS shader-compiler trap (verified 2026-10-20):** after a GL step that builds many new shader programs (the render validation), Apple's `CVMCompiler` service runs at 80-100% CPU for tens of seconds after the test process exits. A GTK startup in that window takes 21-44 s instead of 2-6 s and stalls in `window.present()`; it is not an EasyHybrid hang and leaves no process behind. Run timed suites before render validation (the workflow does), and do not chase it with display-sleep/App Nap changes: `pmset` already shows sleep prevented on hosted runners (disproved in `39342373577`). Windows GTK 4.20+ and macOS ignore `GDK_SCALE`; HiDPI evidence there is NOT TESTED. NumPy 2 removed `ndarray.ptp()`; use `np.ptp`.

**macOS GTK 4.24 full-app centering test (verified 2026-10-20):** the macOS arm64 full-app harness previously timed out waiting for three (then two) repeated GLib timer samples, even though its one-step test centering animation had reached the target (`centering_residual=0`, `transform_delta=0`). macOS polling cadence produced only one repeated sample in that interval. This was a test synchronization assumption, not a GTK 4.24 or renderer failure. The harness now gates on the actual centered residual and transform delta, and focused run `39476612300` passed the full app and all five-cycle scene checks at GTK 4.24.1 / Apple Software Renderer. Keep the test-only one-step centering setup; do not restore a fixed count of timer samples.

**macOS GTK 4.24 native-pick poll delay (diagnosed 2026-10-22):** matrix run
[`39713404036`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39713404036)
passed 29/30 cells; macOS arm64 GTK 4.24.1's failed full-app cycle had a
completed Quartz HID click and a GL pick render that read oxygen (`O`), while
the lifecycle poll did not advance to close before its watchdog. Focused run
[`39714957617`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39714957617)
confirmed the completed readback and clean close in all five cycles using a
watchdog fallback, but showed that fallback could cost 45 seconds per cycle.
The follow-up [`39715844952`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39715844952)
had two cycles close through the verified pick path and one later subprocess
hit its 60-second limit. The harness now schedules a default-priority 1 ms
GLib callback immediately after the real GL pick render records oxygen, with
the verified-readback watchdog fallback retained. Focused run
[`39716542528`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39716542528)
passed all five native macOS arm64 GTK 4.24.1 Quartz click/pick/render/close
cycles; three completed through the render callback and two required the
watchdog path. Its artifact reports Python 3.12.15, PyGObject 3.58.1, GLib
2.90.0 and Apple Software Renderer/OpenGL 4.1. Keep the fallback: macOS may
delay the periodic poll after a completed GL readback. The full matrix must be
rerun on the latest fix before merge.

**macOS Quartz native pointer (verified 2026-10-22):** focused run
[`39707517301`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39707517301)
passed five fresh real-app cycles on macOS 14.8.9 arm64, Python 3.12.15,
PyGObject 3.58.1, GTK 4.24.1 and GLib 2.90.0. Every cycle records
`EASYHYBRID_FULL_APP_POINTER=macos-quartz-hid`, picks `O:0`, renders with
Apple Software Renderer/OpenGL 4.1, and closes cleanly. Keep AppKit-to-Quartz
screen conversion and the common GTK gesture feedback calibration. The
separate scale-1/2 render check reported `scale_applied=false` and widget scale
factor 1; this is not Retina/HiDPI evidence. Other macOS GTK minors and Intel
macOS native pointer injection remain untested.

**Windows pDynamo3 build trap (2026-10-20):** pinned pDynamo3 `6b28dd8958e1a705fcdca130f4ab862a8af8de82` uses an empty zero-length `SNEGATIVE[0]` C array. MSVC rejects it with C2466 during the full-app CI build, after GTK/GL scene checks pass. The Windows-only `.github/scripts/patch_pdynamo3_windows.py` represents the table with a single zero sentinel in both declaration and definition. `NNEGATIVE[iam][0]` is always zero and the only access is in a loop bounded by that count, so the sentinel is never read and scientific term counts remain unchanged. Validate the patched build on the Windows runner; do not mark full-app acceptance from GTK smoke alone.

**Windows native full-app pointer calibration (verified 2026-10-22):** in the
Win32 input test, `ClientToScreen` coordinates can be displaced from the
logical coordinates received by the production GTK gesture because of window
insets. Do not replace the learned offset with the residual from the most
recent click: once a click is aligned, that residual is near zero and resetting
the offset makes retries alternate between the missed base point and corrected
point. Keep a cumulative per-app-cycle offset, and derive each attempt from the
mapped GTK point plus that offset. Restore the test window before coordinate
conversion, temporarily raise it topmost during injection when an overlay
intercepts clicks, and require `WindowFromPoint` to identify the target HWND or
one of its child windows. Foreground activation is best-effort because hosted
Windows runners can refuse `SetForegroundWindow`; actual GTK pick success is
the acceptance check. Focused native run
[`39706994456`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39706994456)
passed five real-app pointer-pick/render/close cycles at Windows GTK 4.8.2 and
4.10.1. Keep a regression test for cumulative offset and inspect press/release
coordinates plus the final picked atom if this failure returns.

**Windows GTK 4.20 repeated-launch overlay (diagnosed 2026-10-22):** the
all-scope matrix run [`39708415015`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39708415015)
and focused runs [`39711834067`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39711834067),
[`39712180632`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712180632),
and [`39712548364`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712548364)
diagnosed a foreground GitHub HostedComputeAgent console (`ConsoleWindowClass`)
covering the mapped click point. Foreground activation and `AttachThreadInput`
were refused. `GetConsoleWindow` was null because the console belongs to the
HostedComputeAgent process, not the child Python process. The helper now
recognizes that exact console title, minimizes it only when hit-testing
confirms that it blocks the GTK window, and restores it after the click.
Focused run [`39712852467`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39712852467)
passed five fresh Windows Server 2022 x86_64 app cycles at Python 3.12.15,
PyGObject 3.58.1, GTK 4.20.3, GLib 2.90.1, and Mesa 26.2.4 llvmpipe WGL.
Every cycle picked `O:0`, rendered and closed cleanly; the component scene
passed five cycles and render validation passed. Keep the blocker identity
check specific to the hosted agent console. The full platform/minor matrix is
still required.

**Full-interface test boundary (updated 2026-10-22):** `test_easyhybrid_menu_vismol_components_open_and_close_cleanly` builds a standalone GTK host around production EasyHybrid menu and VisMol components; its CI results are component evidence only. The separate opt-in `tests/test_easyhybrid_full_app_smoke.py` launches `EasyHybridApplication`, production `MainWindow`, and real pDynamo3 PDB load/render/pick/close. See the all-cell native full-app results in run `39717469974` below; never infer full-app behavior from component-smoke results alone.

**EH4-202 full native pointer matrix passed (2026-10-22):** run
[`39717469974`](https://github.com/Shabirahmad427/EasyHybrid4/actions/runs/39717469974)
passed all **30/30** configured native platform/GTK cells on branch
`eh4-202-cross-platform-pointer-injection`. Every cell completed five real
`EasyHybridApplication`/`MainWindow` fixture-load, OS-pointer pick, render and
clean-close cycles, plus five production menu/VisMol cycles. All nine Windows
GTK 4.8–4.24 cells passed Win32 input; all nine macOS arm64 cells passed
Quartz HID; Linux cells passed XTest. The earlier Windows error with cursor
`(613,444)` and client coordinate `(613,345)` is consistent with the target's
99-pixel client-to-screen origin, but `WindowFromPoint` returned a different
HWND. It did not recur in the full matrix. Keep rejecting clicks unless the
hit-tested HWND is the target or its child, and only minimize the exact
HostedComputeAgent console after confirming it is the blocker. If this happens
again, inspect the complete appended hit window title/class/PID/rectangle and
attempt trace before changing z-order or blocker handling; an abbreviated
message ending at `scale=1` is insufficient to identify the HWND. Exact GTK
patch versions and OS runtime details are tabulated in
`docs/GTK4_COMPATIBILITY.md`; full per-cell runtime evidence is in the run
artifacts. EH4-202's configured native-context acceptance is complete. Linux
Wayland, physical GPUs, physical Retina/HiDPI and trackpads remain separately
**NOT TESTED**.
