# EasyHybrid4 — GTK4 Cross-Platform Engineering Roadmap

> **Status:** Planning baseline; not a verified compatibility claim.  
> **Scope:** EasyHybrid4, graphics engine and submodules, pDynamo integration, installation and packaging.  
> **Targets:** Linux (X11 and Wayland where possible), Windows (native), macOS (Apple Silicon and Intel where feasible).  
> **Source of truth:** This file is the durable work queue for Codex. Update it in the same commit as implementation changes.

## 0. Instructions for Codex — read on EVERY session

1. Read **this entire file** at the beginning of each session, along with `AGENTS.md` if present, the repository README, recent changes, and related docs.
2. Inspect actual repository state before proceeding. Do **not** assume tasks marked complete still pass; verify relevant evidence and dependencies.
3. Choose the **first eligible, unchecked, highest-priority task** whose dependencies are satisfied. Work on **one bounded task at a time**; do not jump to random platform-specific fixes.
4. Before coding: locate affected code and submodules; identify baseline behavior; write down the GTK API/version and OS/backend assumptions; define tests and rollback risk.
5. Prefer **one shared code path** built on APIs in the supported GTK4 range. Put unavoidable minor-version and platform differences behind centralized, tested adapters, not dispersed `if OS == ...` or `if GTK >= ...` branches.
6. Add regression tests before or with the fix. Test the oldest supported GTK4 runtime, the newest available stable runtime and relevant intermediate versions when feasible. Never silently equate import success, headless stubs, or Linux-only passes with full cross-platform verification.
7. Test what is **actually available**. Use native Windows/macOS CI or runners for native validation; use real rendering/trackpad devices for hardware-specific checks. Mark unavailable checks `NOT TESTED` with a reason. Do not invent success.
8. Keep pDynamo calculations, input/output schemas and project files compatible unless a deliberate, documented scientific change is separately approved. Avoid changing simulation results while fixing UI behavior.
9. If updating a graphics submodule: commit and publish the submodule revision to a reachable repository **before** committing its pointer in the parent. Audit submodule URL, recursive checkout and CI reproducibility.
10. After each task: run applicable tests, update the task checkbox **only if acceptance criteria pass**, update the evidence table, list known limitations, and commit in a coherent unit. Never claim all-platform support from a single development machine.
11. If blocked, record the blocker, evidence and concrete next action; select another independent eligible task without misrepresenting completion.
12. At end of session, report: task ID, files changed, tests and environments run, GTK runtime versions, pass/fail/not-tested, commits, blockers and exact next task.

**Session command for Codex:** `Read docs/ROADMAP.md completely; verify repository status; pick the next eligible unchecked task; implement it with regression tests; execute available checks; update docs/ROADMAP.md and evidence; commit the bounded change; report verified vs untested OS/GTK combinations. Do not bypass phase gates.`

## 1. Non-negotiable compatibility contract

- **GTK4 range:** The runtime floor is GTK 4.8; GTK 4.6 and older are unsupported. `Gtk 4.0` is the PyGObject introspection namespace, not the runtime minimum. Compatibility evidence must cover **each released GTK 4.x minor series from 4.8 through the latest stable minor included in the declared support range**, on each OS claimed supported. This means one explicitly recorded patch runtime per minor series, not an unsupported inference across minor versions. Record the exact patch runtime, OS, architecture, Python, PyGObject, GLib and backend per run. An unexecuted minor/platform pair is `NOT TESTED`, never inferred from another version. Add newly released minors to the matrix before claiming them supported. Do not claim future GTK releases before testing.
- **Version flexibility:** Build for an agreed interval `[GTK_MIN, GTK_LATEST_VERIFIED]`. When functionality requires a newer API, use an older supported equivalent, or a centralized feature check and fallback; otherwise revise the support contract explicitly with justification.
- **Portability:** Share application logic; isolate file dialogs, menu/shortcut conventions, paths, native packaging and GL setup only where platforms differ. Detect **capabilities**, not device names or hardcoded driver strings.
- **Scientific integrity:** GTK migration must not alter pDynamo input parameters, QM/MM definitions, trajectory processing, numerical computation, or persistent project data. Use comparison fixtures and document expected numerical tolerances.
- **Graphics:** `Gtk.GLArea` and the graphics engine must be tested with actual contexts. Linux X11/Wayland, Windows and macOS graphics drivers can differ; macOS OpenGL has limitations. An explicit unsupported feature and graceful error are better than a fabricated fallback.
- **Testing claims:** `PASS`, `FAIL`, `NOT TESTED`, or `BLOCKED`, with OS, CPU architecture, GTK/GLib/PyGObject/Python and OpenGL renderer/driver when relevant. A CI green status means only the checks that were run passed.
- **Dependencies:** Declare a supported Python matrix; pin or constrain runtime/build dependencies reproducibly. Validate pDynamo and other binary/scientific dependencies on each target rather than assuming availability.
- **Upstream:** Preserve attribution/license requirements and EasyHybrid3 as the reference behavior, while keeping EasyHybrid4 migration changes isolated and reviewable.

### Proposed test matrix (final selections require Phase 0 evidence)

| Target | Required checks | Status |
|---|---|---|
| Linux x86_64 / X11 | Import, UI, GL, scientific regression, package | PARTIAL: full suite and native GTK/OpenGL lifecycle pass on GTK 4.8.2, 4.14.5, 4.24.1; packaging and all GTK minors remain unverified |
| Linux x86_64 / Wayland | Import, UI, GL, input, scaling | NOT TESTED |
| Linux second distribution / native GTK | Startup, integration, package | NOT TESTED |
| Windows x64 / native GTK4 | Import, UI, GL, dialogs, package | NOT TESTED |
| macOS arm64 / native GTK4 | Import, UI, GL, Retina, trackpad, package | NOT TESTED |
| macOS x86_64 (if available) | Import, UI, GL, package | NOT TESTED |
| Every GTK 4.x minor >= 4.8 in declared support range (4.8, 4.10, 4.12, ... through latest stable) | API/feature and UI smoke tests on each claimed OS; record exact runtime patch version | Linux X11 evidence for GTK 4.8.2, 4.14.5, and 4.24.1; GTK 4.10/4.12/4.16/4.18/4.20/4.22 and all non-Linux results NOT TESTED |

Use a **pairwise smoke matrix on pull requests** and more extensive native/version runs before releases; report missing combinations. CI images alone cannot prove real GPU or real trackpad behavior.

## 2. Required structure and permanent documents

- `docs/ROADMAP.md` — this file: task inventory, phase gates, completion evidence.
- `docs/EASYHYBRID4_REPORT.md` — the consolidated repository, compatibility, parity, platform, test, contributor, fixture-policy, and limitation report.
- `AGENTS.md` (if absent) — short permanent agent instruction: always read this roadmap and do not overstate tests.

The consolidated report is the only project status and technical report.
Keep source/data `README.md` files with their code. The root `README.md` and
`AGENTS.md` remain entry-point documents; avoid creating additional report
files.

## 3. Work queue: execute IN ORDER; one checkbox per independently verifiable task

### Phase 0 — Inventory and reproducible baseline (provenance-dependent work gated)

- [ ] **EH4-000** Record remote URLs, current branches, commit IDs, dirty tree, tags, licenses, and recursively resolved submodule SHAs. Identify EasyHybrid3 reference and EasyHybrid4 fork roots. **Accept:** baseline recorded in architecture docs; no uncommitted user changes overwritten.
- [x] **EH4-001** Map package/module layout and entry points, GTK3 vs GTK4 usage, `.ui` resources, PyGObject, GLib, pDynamo, graphics module, optional libraries, scripts and installers. **Accept:** annotated dependency and API inventory with file references.
- [x] **EH4-002** Build/install and run existing tests on available Linux environment without editing runtime behavior; capture exact package/runtime versions and failures. **Accept:** reproducible setup commands plus baseline logs in test documentation.
- [x] **EH4-003** Compare EasyHybrid3 workflows to current EasyHybrid4; tag `WORKING`, `BROKEN`, `UNIMPLEMENTED`, `UNTESTED`. **Accept:** feature parity checklist including molecular interaction and scientific exports.
- [x] **EH4-004** Select `GTK_MIN`, supported Python versions and dependency resolution strategy based on accessible CI/runtime builds and APIs in source. **Accept:** documented supported interval and criteria for raising minimum; no unsupported universal GTK4 claim.
- [x] **EH4-005** Add initial repo docs listed in Section 2; create focused regression fixtures and a safe test-data policy. **Accept:** a new contributor or Codex session can reproduce baseline and resume work.

**Phase 0 gate:** Implementation and test prerequisites are documented. EH4-000 remains incomplete until authoritative parent-remote and graphics-source provenance are available. Those provenance gaps do not block independent architecture work; tasks that publish graphics changes or require reachable upstreams remain gated. Do not claim Phase 0 complete.

### Phase 1 — Architecture and GTK4 adaptation

- [x] **EH4-100** Separate GUI/presentation, domain/scientific services, graphics abstraction and OS integration. **Accept:** testable science modules without requiring GTK display.
- [x] **EH4-101** Centralize GTK feature detection in one compatibility module; avoid hardcoding specific distributions or GTK patches. **Accept:** unit tests for supported branches and fallback behavior.
- [x] **EH4-102** Review Gtk.Application lifecycle, Gio actions, UI templates/resources and GtkBuilder definitions for supported GTK4 APIs. **Accept:** open/close smoke checks without critical warnings at GTK_MIN and GTK_LATEST where testable. Full EasyHybrid open/GL/close and real Gio action tests pass at GTK 4.8.2 and GTK 4.24.1 on native Linux X11; one GTK 4.8 `Gtk.AboutDialog` finalization critical is independently reproduced in GTK itself and documented as upstream behavior.
- [ ] **EH4-103** Migrate removed GTK3 widgets/layout and model patterns to shared GTK4 patterns. **Accept:** dialogs, windows, data views and selections pass deterministic UI tests.
- [ ] **EH4-104** Migrate event controllers, gestures, drag/drop, shortcuts and menus, including touchpad precision and delta handling. **Accept:** mouse and keyboard automated tests; actual trackpad validation marked separately.
- [ ] **EH4-105** Review async dialogs, GLib scheduling, thread boundaries, cancellation and error paths. **Accept:** tests for nonblocking UI, clean shutdown and no callbacks on destroyed widgets.
- [ ] **EH4-106** Audit deprecations using supported version targets and prefer stable APIs with tested older fallbacks. **Accept:** no unexplained version-specific imports in core modules.

**Phase 1 gate:** Core GUI startup/navigation and controls work at GTK_MIN and GTK_LATEST on at least one real environment, with untested OS explicitly logged.

### Phase 2 — Molecular graphics engine and input semantics

- [ ] **EH4-200** Audit graphics engine fork/submodule architecture, OpenGL requirements, native libraries, build, CI and published revisions. **Accept:** reproducible recursive clone + build and clear ownership of graphics fixes.
- [ ] **EH4-201** Implement GTK4 Gtk.GLArea setup, lifecycle, realized context, render callback, error diagnostics and resource cleanup. **Accept:** real-context smoke rendering and teardown checks.
- [ ] **EH4-202** Inspect GL capabilities; validate shaders/VBO/VAO/FBO/picking/selection paths, scaling and resize. **Accept:** visual or image-difference evidence with justified thresholds on available real graphics contexts.
- [ ] **EH4-203** Normalize mouse-wheel, smooth scroll, trackpad, zoom, rotate and pan behavior **by input semantics**, not tuned per named hardware. **Accept:** logged delta/steps tests plus actual macOS trackpad review.
- [ ] **EH4-204** Verify picking, atom/residue selection, labels, measurements, representations and camera persistence. **Accept:** end-to-end 3D sample fixture tests.
- [ ] **EH4-205** Implement error/fallback messaging for unsupported graphics capabilities and context failure. **Accept:** useful diagnostics, no silent blank view or crash.

**Phase 2 gate:** Real molecular display works in tested contexts; missing Windows/macOS hardware evidence remains explicitly open.

### Phase 3 — OS and packaging boundaries

- [ ] **EH4-300** Centralize paths, encoding, config/cache/log directories and Unicode/special-character handling. **Accept:** portable path tests on all CI operating systems.
- [ ] **EH4-301** Verify native file dialogs, clipboard, window lifetime, menu/keyboard conventions and accessibility. **Accept:** OS-specific GUI smoke scripts with native results recorded.
- [ ] **EH4-302** Audit font, window sizing, HiDPI, Retina, multi-monitor, Wayland/X11 handling and display scale changes. **Accept:** screen/capability test evidence, known limitations documented.
- [ ] **EH4-303** Add platform dependency provisioning and reproducible installation instructions; identify native build/runtime requirements. **Accept:** clean runner installation works or precise blocker captured.
- [ ] **EH4-304** Produce Linux, Windows and macOS candidate distribution paths without assuming identical native bundling strategy. **Accept:** independently installed and launched packages for every platform labeled supported.

**Phase 3 gate:** Native integrations and packaging tested on real OS runners; no Linux commands embedded into common application logic.

### Phase 4 — Scientific parity and data integrity

- [ ] **EH4-400** Freeze representative fixtures for system loading, coordinates and visualization. **Accept:** input-to-display checks with no unintended molecule changes.
- [ ] **EH4-401** Verify atom/residue selection, measurements, editing, undo/project persistence (where implemented). **Accept:** repeatable round-trip tests.
- [ ] **EH4-402** Validate MM, QC/MM, energy and minimization workflows against EasyHybrid3/reference pDynamo APIs. **Accept:** input settings preserved; numerical deviations bounded and explained.
- [ ] **EH4-403** Validate reaction coordinate scans, pathways, umbrella sampling and other supported simulation setup/export. **Accept:** exported scripts/parameters and sample calculations checked.
- [ ] **EH4-404** Verify project save/load, versioning, migration and failure recovery. **Accept:** no silent corruption; backwards compatibility policy documented.
- [ ] **EH4-405** Validate logs/errors/progress, cancel/interrupt and background scientific computations without blocking GUI. **Accept:** cancellation and exception regression tests.

**Phase 4 gate:** Every core EasyHybrid3 feature explicitly marked parity PASS, known difference, incomplete or untested, backed by fixtures where possible.

### Phase 5 — CI, native testing, and reproducibility

- [ ] **EH4-500** Add GitHub Actions lint, tests, type/build/import checks on Linux, Windows and macOS. **Accept:** runners actually provision dependencies and publish logs.
- [ ] **EH4-501** Build compatibility checks for every released GTK 4.x minor in the declared range (starting at 4.8 through latest stable), on each OS claimed supported. **Accept:** each OS/minor combination has a native runtime result with actual GTK/GLib/PyGObject versions; unavailable combinations are `NOT TESTED` and excluded from support claims. Add each new GTK4 minor before claiming support for it.
- [ ] **EH4-502** Add UI tests under appropriate native display servers; do not substitute mocks for GUI acceptance. **Accept:** startup/window/action/dialog results documented per OS.
- [ ] **EH4-503** Add real GL context smoke tests, artifacts and driver metadata; isolate environment-dependent skips. **Accept:** failures are visible, skips explain exact reason.
- [ ] **EH4-504** Add non-GUI scientific regression and project/export fixture tests in cross-platform CI. **Accept:** scientific tests run even where graphics unavailable.
- [ ] **EH4-505** Define manual native validation for Windows UI, Linux Wayland/X11, macOS M4 trackpad/Retina/OpenGL and Intel Mac where available. **Accept:** signed/date-stamped reports, no inferred passes.
- [ ] **EH4-506** Protect release branch with supported gating tests and immutable evidence artifacts. **Accept:** CI failure blocks release; platform gaps visible.

**Phase 5 gate:** Automated and manual results cover promised supported targets or support statement narrowed accordingly.

### Phase 6 — Release qualification and maintenance

- [ ] **EH4-600** Run fresh-install checks on each supported platform and architecture, including linked native libraries and sample data. **Accept:** clean-install reproduction instructions and logs.
- [ ] **EH4-601** Add About/diagnostic report of OS/architecture, Python, PyGObject, GTK, GLib, GL backend/renderer, pDynamo and graphics submodule version. **Accept:** diagnostics do not crash if optional GL context unavailable.
- [ ] **EH4-602** Audit legal notices, licenses, dependency attribution, security and unsupported GTK/OS assumptions. **Accept:** tracked findings addressed or accepted with rationale.
- [ ] **EH4-603** Finalize release support table listing **exact tested combinations**, restrictions and known issues. **Accept:** no unverified compatibility claims.
- [ ] **EH4-604** Tag and package release only after gates satisfied and parent/submodule commits are reachable. **Accept:** tested installable artifacts and published reproducible release notes.

## 4. Definition of done for EVERY task

Mark a checkbox `[x]` **only** when all relevant items are satisfied:

- Behavior and compatibility contract explicitly stated.
- Tests added or reason documented why not possible.
- Tests executed on available environments; raw outcomes preserved, including failures/skips.
- GTK runtime/API availability considered at `GTK_MIN` and `GTK_LATEST_VERIFIED` (or `NOT TESTED` accurately recorded).
- Cross-platform risk considered, with platform-specific code isolated and justified.
- No unintended change to scientific calculations or project data; regression checked where relevant.
- Docs and test matrix updated in same commit; applicable code/submodules pushed to reachable refs.
- No unrelated scope changes; code reviewable and rollback possible.

A task may be **implemented but NOT VERIFIED**; in that case leave unchecked and record the actual progress in the task log. A phase gate is not satisfied merely because all code has been written.

## 5. Evidence log — append after every task

| Date (UTC) | Task | Commit(s) | Environment (OS/arch) | Python / PyGObject / GTK / GLib | Test commands & outcomes | Graphics context | Status / gap |
|---|---|---|---|---|---|---|---|
| 2026-10-17 | EH4-000 | None; EasyHybrid4 `.git` metadata unavailable | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | `git -C . status/rev-parse` and branch/remotes/tags: BLOCKED (`.git/` empty, read-only); read `.gitmodules`, both license files, and EasyHybrid3 Git/submodule metadata. No runtime tests for this inventory task. | NOT TESTED | PARTIAL; EH4 remote, branch, commit, tags, dirty state, and local graphics SHA are unknown. See `EASYHYBRID4_REPORT.md`. |
| 2026-10-17 | EH4-000 | `843c82a` (blocker record) | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Verified `main`, HEAD `bea94210ed7c23f71d2241f8abe3c849ade18561`, clean tree, no configured remotes, and no tags. `.gitmodules` declares graphics submodule, but `git ls-tree` gives mode `040000`, `git submodule status --recursive` is empty, and files are tracked individually. EasyHybrid3 reference and both licenses recorded in `docs/EASYHYBRID4_REPORT.md`. | NOT TESTED | INCOMPLETE: no EasyHybrid4 remote/fork URL and no graphics upstream SHA/submodule metadata. Missing information recorded; no inference made. |
| 2026-10-17 | EH4-001 | `f69e4c4` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Source inventory in `docs/EASYHYBRID4_REPORT.md`; parsed all 53 `.glade` resources and confirmed each declares Gtk 4.0; scanned Python imports and found GTK 4 requests with no GTK 3 namespace requests. `$HOME/software/envs/easyhybrid312/bin/python -m pytest -q tests/`: **23 passed**, one pytest cache warning because `$HOME/software/.pytest_cache` is read-only. No runtime code changed, so no regression test was added. | NOT TESTED (real Gtk.GLArea context/renderer) | COMPLETE for the documentation inventory only. Native Windows/macOS, Wayland, and non-installed GTK minors remain NOT TESTED. EH4-000 remote/submodule blockers remain open. |
| 2026-10-17 | EH4-002 | `b15fa22` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0; pytest 9.1.1; NumPy 1.26.4; SciPy 1.11.4; Cython 3.0.8; PyOpenGL 3.1.7; psutil 5.9.8 | `$HOME/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/`: **23 passed**. Copied graphics engine to a temporary directory; `python setup.py build_ext --inplace`: **7 extensions built**, all **7 imported**. With `$HOME/software/pdynamo3.sh` sourced, `pCore`, `pMolecule`, `pSimulation`, `pScientific` resolve. Isolated `pip install --target` probe **FAILED** in PEP 517 metadata generation (`ModuleNotFoundError: No module named 'src'`). Full interactive installer NOT RUN because it changes the configured pDynamo/dependency environment. Full commands/results in `docs/EASYHYBRID4_REPORT.md`. | NOT TESTED (real Gtk.GLArea context/renderer) | COMPLETE for reproducible Linux baseline/build and existing tests. Generic pip installation remains a packaging issue; GTK 4.8 minimum and other minors, Wayland UI/GL, Windows, and macOS are NOT TESTED. No runtime source behavior changed; no behavioral regression test was applicable. |
| 2026-10-17 | EH4-003 | `01a8f21` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Inspected the EasyHybrid3 implementation report and workflow modules read-only, then mapped present/absent EasyHybrid4 windows, dispatchers, exports, and tests in `docs/EASYHYBRID4_REPORT.md`. EH4 suite: **23 passed**. EH3 suite: **23 passed, 4 skipped**. These suites cover non-GUI atom/bond logic, not GUI, scientific runs, or exports. | NOT TESTED (real Gtk.GLArea context/renderer or interactive picking) | COMPLETE for the static/test-evidence parity inventory. Molecular interaction, simulation/export workflows, and most analysis are UNTESTED; Vina/AutoDock-GPU, external NAMD/AMBER/Packmol/Antechamber front ends, and infrared GUI workflow are UNIMPLEMENTED. User-provided launch output records two `gtk_box_remove` critical assertions; impact/source path remains unresolved. Windows/macOS, Wayland, X11 live GUI, GTK 4.8 minimum, and all untested GTK minors are NOT TESTED. |
| 2026-10-17 | EH4-004 | `27a25b9`, minimum revised in this commit | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Versioned API/source audit recorded in `docs/EASYHYBRID4_REPORT.md`. GTK official site checked 2026-10-17: stable 4.22.5; local runtime 4.14.5. Earlier suite: **23 passed**. GTK 4.8 APIs used by splash and scroll handling were identified; regression tests now cover installer rejection of 4.6 and acceptance of 4.8+. Python 3.10 syntax floor; only Python 3.12.3 run. | NOT TESTED (real UI/GL context) | Target is GTK 4.8 through current stable; GTK 4.6 is intentionally unsupported. GTK 4.14.5/Python 3.12.3 is the only runtime combination verified. GTK 4.8, GTK 4.22.5, other Python versions, Windows, macOS and Wayland are NOT TESTED. |
| 2026-10-17 | EH4-005 | `02d3db2` plus `8aa1e70` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Consolidated status and implementation reports, contributor/test guidance, and fixture policy in `docs/EASYHYBRID4_REPORT.md`; relocated the graphics patch in a follow-up. Existing suite: **23 passed**; Markdown links and whitespace checks: **PASS**. Patch applicability was not assessed for EH4-005. | NOT TESTED | Documentation-only; no scientific/runtime behavior changed. Windows, macOS, GTK 4.8/current stable and GUI/GL remain NOT TESTED. |
| 2026-10-17 | EH4-100 (in progress) | `6b6944a` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Audited `src/util/md_analysis.py` as a NumPy-only service imported by GTK analysis windows. Added tests for RMSF, RDF periodic behavior, density, invalid cells, GTK-free import, and GTK version policy (4.6 rejected; 4.8+ accepted). Correctly rooted graphics patch dry run fails as detailed in the report; patch remains unapplied. Full suite: **33 passed**. Compile check and `git diff --check`: **PASS**. | NOT TESTED (no display, GTK window, or GL context) | PARTIAL: science/presentation boundary has regression coverage; installer now enforces the declared GTK 4.8 floor. Broader architecture separation remains. Windows, macOS, GTK 4.8/4.22.5 and every other unrun GTK minor, Wayland/X11 UI, and real renderers NOT TESTED. |
| 2026-10-17 | EH4-100 | b181a50 | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Added pure `SessionState`, plotting color-math, and OS-startup boundaries with regression coverage for state behavior, GTK-free imports, legacy plotting exports, Cairo drawing, saved driver preferences, and platform guards. Standard environment: **47 passed, 2 skipped** (pDynamo not configured); pDynamo-configured environment: **49 passed**, including workflow package import with PyGObject blocked and legacy session facade without a display. Compileall: **PASS**; Ruff on added pure modules/tests: **PASS**. Wider Ruff scan across legacy app code: **FAIL**, 233 diagnostics, recorded as existing cleanup work. GTK docs identify 4.24.1 as current stable (superseding prior 4.22.5 target); matrix package availability per historical minor/platform is unverified. Reviewed Wordcraft's split headless, Linux virtual-display, and native Windows/macOS test pattern. | GTK 4.14.5/X11/Xvfb: real widget/popover smoke passed. Full launcher showed the main window with `G_DEBUG=fatal-criticals`; orderly shutdown and real GL context remain **NOT TESTED**. | COMPLETE for architecture boundaries and GTK-free scientific import acceptance. Remaining coupling is documented; untested GTK versions/platforms remain open for later tasks. |
| 2026-10-17 | EH4-101 (in progress) | b181a50 | Linux x86_64, X11/Xvfb | Python 3.10.22 / PyGObject 3.42.2 / GTK 4.8.2 / GLib 2.78.0 | Isolated `/tmp/easyhybrid4-gtk48` runtime. Full available suite with graphics built in an isolated copy: **47 passed, 2 skipped** (pDynamo environment not configured). A real `Gtk.GLArea` created an OpenGL 3.3 context and reported `llvmpipe (LLVM 20.1.2, 256 bits)`. Default Xvfb emitted Mesa `DRI3 error: Could not get DRI3 device`; Mesa EGL and DRI packages were already installed. Repeating with `LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe` retained the real GL context and removed the warning. `GSK_RENDERER=cairo` also removes GL probing for widget-only smoke, but is not a GL test. An additional run with `G_DEBUG=fatal-criticals` exposed a GTK icon-theme initialization critical, a separate unresolved issue. | Xvfb/X11 software GL via llvmpipe: **PASS** for GLArea context creation only. Hardware GL, native X11, Wayland, Windows, macOS, GTK 4.10 through 4.24.1: **NOT TESTED**. | EH4-101 remains in progress: the DRI3 message is environment/display capability related, not a missing package; no installation or application workaround is justified. Continue GTK capability audit and investigate the separate GTK icon-theme critical. |
| 2026-10-17 | EH4-101 complete; icon-theme diagnostic | b181a50 | Linux x86_64, native X11 and X11/Xvfb | GTK 4.8.2: Python 3.10.22 / PyGObject 3.42.2 / GLib 2.78.0; GTK 4.14.5: Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0 | Full suite on each runtime: **48 passed, 4 skipped**. Targeted real GTK capability/icon/resource tests: **5 passed** per runtime, including fatal-critical Gtk.ApplicationWindow open/close on Xvfb and no-display guard. The critical reproduces in a minimal app only when `Gdk.Display.get_default()` is `None`; GDB stack points to GTK/GIO application registration (`gtk_application_startup` on 4.8.2). Native `:0` theme: Mint-Y-Sand; Xvfb theme: Adwaita; `GTK_THEME` unset. All 53 Glades loaded through `load_builder_file()` on both runtimes; GTK 4.14.5 builder tool validated 53/53, GTK 4.8.2 builder tool validated 19/53 because it reports 34 unresolved external signal handler names. 21 file-backed GtkImage paths all exist; 51 custom icon files; no themed icon/GResource registration in app code. Gtk.GLArea created OpenGL 4.5 core using Mesa llvmpipe (`LLVM 20.1.2, 256 bits`) on both runtimes with `G_DEBUG=fatal-criticals`. Compileall: **PASS**. | Xvfb/X11 software rendering via llvmpipe: **PASS**. Real GPU, native GL driver, Wayland, Windows and macOS: **NOT TESTED**. | EH4-101 **COMPLETE**. Icon critical is a no-display GTK test setup failure, not an EasyHybrid asset or renderer defect. Separate test guard now checks display before GApplication registration. Full EasyHybrid orderly close remains unverified; proceed to EH4-102. |
| 2026-10-17 | EH4-102 (in progress) | b181a50 | Linux x86_64, X11/Xvfb | GTK 4.14.5 / Python 3.12.3 / PyGObject 3.48.2; GTK 4.8.2 full-app environment uses Python 3.10.22 | Began lifecycle and Builder review. App-loader test parsed 53/53 files on both runtimes. An 8-second GTK 4.14 full-app close attempt did not exit before interruption and emitted D-Bus portal/FUSE permission diagnostics; orderly close is **NOT TESTED**. Full app under GTK 4.8 is blocked by configured pDynamo3 Python 3.12 extension import failure (`undefined symbol: Py_Version`). | Gtk.GLArea software-context smoke passes on both runtimes; this does not verify full-app shutdown. | In progress: run full application lifecycle in a reproducible isolated GUI/D-Bus environment; resolve GTK 4.8 Python/pDynamo ABI setup before claiming full-app minimum-version validation. Windows, macOS, Wayland and hardware rendering remain **NOT TESTED**. |
| 2026-10-17 | EH4-102 native-display retest | b181a50 | Linux x86_64, native X11 display `:0`, NVIDIA GeForce RTX 4060 Ti / driver 595.99.02 | GTK 4.14.5 / Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0; GTK 4.8.2 / Python 3.10.22 / PyGObject 3.42.2 / GLib 2.78.0 | On native `:0`, targeted GTK widget/icon/resource suite: **5 passed** on each runtime, `G_DEBUG=fatal-criticals`; theme Mint-Y-Sand. Full suites: **48 passed, 4 skipped** on each. Minimal Gtk.GLArea OpenGL 3.3 core: GTK 4.8.2 default backend **PASS**, NVIDIA RTX 4060 Ti renderer. GTK 4.14.5 default backend **FAIL**, `Unable to create a GL context` although native GLX reports OpenGL 4.6; explicitly selecting GTK's GLX backend with `GDK_DEBUG=gl-glx` makes the Gtk.GLArea **PASS**. The full GTK 4.14.5 EasyHybrid application opened and closed with `G_DEBUG=fatal-criticals` under that explicit GLX test setting. GTK 4.8 full-app run remains blocked by Python 3.12 pDynamo extension loaded from Python 3.10 (`undefined symbol: Py_Version`). `gh auth status`: invalid token; no remote configured, so native Windows/macOS GitHub jobs cannot be launched. | Native X11 hardware GL: GTK 4.8.2 **PASS** on default selection; GTK 4.14.5 **PASS** with explicit GLX and **FAIL** on default selection. Xvfb/llvmpipe on both versions passed earlier; it is separate evidence. Linux Wayland, Windows, macOS: **NOT TESTED**. | EH4-102 remains incomplete because GTK 4.8 full-app open/close and native Windows/macOS behavior are unverified. Next action: resolve test environment's GTK 4.8/pDynamo ABI and establish authenticated native Windows/macOS CI. Do not infer other GTK minors from these two results. |
| 2026-10-17 | EH4-102 native GTK matrix and lifecycle | b181a50 | Linux x86_64, native X11 `:0`, NVIDIA GeForce RTX 4060 Ti / driver 595.99.02 | GTK 4.8.2 / Python 3.12.15 / PyGObject 3.58.1 / GLib 2.90.0; GTK 4.8.2 / Python 3.10.22 / PyGObject 3.42.2 / GLib 2.78.0; GTK 4.14.5 / Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0; GTK 4.24.1 / Python 3.12.15 / PyGObject 3.58.1 / GLib 2.90.0 | Complete suite on each of four environments: **54 passed, 5 skipped** (two pDynamo-not-configured checks, three opt-in/no-display GUI checks). Native GTK window/icon/Gio menu-action smoke with `G_DEBUG=fatal-criticals`: **1 passed** on all four combinations. Full EasyHybrid open/close with actual `Gtk.GLArea` context and fatal criticals: **1 passed** on GTK 4.8.2/Python 3.12.15, GTK 4.14.5/Python 3.12.3, and GTK 4.24.1/Python 3.12.15; GL versions 3.3.0/4.6.0/4.6.0, renderer NVIDIA RTX 4060 Ti. App auto setup selected `PYOPENGL_PLATFORM=egl` for Linux and `GDK_DEBUG=gl-prefer-gl` for GTK >=4.14; no external overrides were set. All 53 GtkBuilder files loaded on GTK 4.8.2/4.14.5/4.24.1; fatal-critical GTK 4.8 audit isolated a `GtkImage` finalization critical to bare `Gtk.AboutDialog`/`about_dialog.glade`, independently reproducible without EasyHybrid and tracked as GTK upstream (Debian bug #1041599; fixed upstream in GTK 4.10). Real native display smoke also validates actual `Gtk.PopoverMenuBar` construction and Gio action/state activation. `python3 -m compileall -q easyhybrid.py install.py src tests` and `git diff --check`: **PASS**. | Native X11 hardware OpenGL contexts **PASS** for the three full-app runtime combinations; GTK 4.8/Python 3.10 full suite and widget smoke pass, but full pDynamo app is **NOT TESTED** because binary extensions target Python 3.12. | EH4-102 **COMPLETE** for Linux lifecycle/action/resource acceptance at GTK minimum and latest verified runtime. Other GTK4 minors, Linux Wayland, Windows, macOS, Intel/Apple GPUs, native package installation and macOS trackpad remain **NOT TESTED**. GitHub native CI could not be started: no remote configured and `gh auth status` reports an invalid token. Continue to EH4-103; do not infer any untested platform or GTK minor. |
| 2026-10-17 | EH4-102 cross-platform smoke extension | b181a50 | Linux x86_64, native X11 `:0`, NVIDIA GeForce RTX 4060 Ti / driver 595.99.02 | GTK 4.8.2 / Python 3.12.15 / PyGObject 3.58.1 / GLib 2.90.0; GTK 4.14.5 / Python 3.12.3 / PyGObject 3.48.2 / GLib 2.80.0; GTK 4.24.1 / Python 3.12.15 / PyGObject 3.58.1 / GLib 2.90.0 | Updated the native-window smoke to place the actual main menu and Gtk.GLArea together, require a 3.3 context, activate real Gio actions, and report GL version/renderer. With `G_DEBUG=fatal-criticals`, each runtime: **1 passed**. GTK/GL/renderer: 4.8.2 / 3.3.0 / NVIDIA GeForce RTX 4060 Ti; 4.14.5 / 4.6.0 / NVIDIA GeForce RTX 4060 Ti; 4.24.1 / 4.6.0 / NVIDIA GeForce RTX 4060 Ti. On GTK 4.14.5/Python 3.12.3, `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 EASYHYBRID_RUN_GTK_GUI_TESTS=1 $HOME/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/`: **55 passed, 4 skipped**, with the native GTK/OpenGL smoke enabled. Test used the application's shared startup capability policy and no external backend override. Added `.github/workflows/native-gtk-matrix.yml` for all nine GTK minor series (4.8 through 4.24) on Linux x86_64, Windows x86_64, and Apple Silicon macOS. Workflow validation/build/test has **NOT RUN** yet; no remote commit has been pushed. | Native Linux X11 hardware GL: **PASS** at all three tested GTK runtimes. Native Windows/macOS and all other GTK minor combinations: **NOT TESTED** pending workflow execution. | This is additional verification tooling for EH4-103 and later; EH4-500 remains unchecked and incomplete. GitHub auth is now valid; `origin` points to the user-supplied private repo, which GitHub reports as empty. |

### CI package-provider audit (2026-10-17)

Queried `https://api.anaconda.org/package/conda-forge/gtk4` directly and
filtered all published artifacts by version and platform. GTK 4.16 and 4.18
are absent from conda-forge entirely (not only Linux), explaining solver
failures on Linux/Windows/macOS. GTK 4.8.2 and 4.10.1 have Linux, Windows,
and Intel macOS artifacts, but no Apple Silicon `osx-arm64` artifact, which
explains the 4.8/4.10 macOS arm64 failures. Ubuntu separately publishes Linux
GTK 4.16.x and 4.18.x packages, so Linux GTK compatibility must not be
dropped because the selected conda provider lacks those versions. The matrix
exclusions are provider-specific; the excluded cells remain **NOT TESTED**.
Windows/macOS builds through source or another package manager were not
verified. Workflow run `39063905270` was still running when this audit was
recorded; its in-progress status is not a final result. See
`docs/GTK4_COMPATIBILITY.md` for the cell-by-cell evidence and next provider
work. This audit does not complete EH4-103 or EH4-500.

Follow-up: Windows GTK 4.8 and 4.10 setup jobs stalled in `gdk-pixbuf`'s
post-link script after resolving `libiconv 1.18` (run `39063905270`; the same
cells were still at setup in `39064335791`). The conda-forge feedstock
documents a Windows loader-cache failure and temporary `libiconv 1.17`
workaround. The pin was applied only to Windows GTK 4.8/4.10; run
`39064516500` confirms `libiconv 1.17` was selected but still hangs in the
same post-link step. The next revision skips link scripts only in those test
environments and runs the gdk-pixbuf cache utility directly with a 60-second
timeout and captured output. Workflow YAML parses and `git diff --check`
passes; that diagnostic and native smoke are pending. Both cells stay
**NOT TESTED**.

### Active task and blockers

- **Current task:** `EH4-103` — migrate GTK3-era widgets/layout and model patterns to shared GTK4 patterns. Inspect the existing controls, add behavioral regression tests before changes, preserve scientific workflows, and retain the explicit cross-platform/GTK-minor gaps.
- **EH4-000 provenance limitations (not blockers for independent implementation):** `origin` now points to the user-supplied private EasyHybrid4 repository, and GitHub confirms that repository exists but is empty. The graphics-engine files are still ordinary tracked files rather than an active submodule, and their upstream revision remains unknown. Keep the revision unresolved; do not infer it from EasyHybrid3 or `.gitmodules`. Graphics publishing/ownership-dependent work remains gated.
- **Current implementation/testing blockers:** The GTK 4.8/Python 3.10 full application cannot use the available Python 3.12-built pDynamo binary extensions; a GTK 4.8/Python 3.12 + matching pDynamo combination passes full app/GL open-close. GTK 4.8 `Gtk.AboutDialog` produces an upstream GtkImage finalization critical (also reproduced with a bare dialog); this is not the GTK no-display icon-theme critical or the user's reported `gtk_box_remove` issue. The native GTK matrix is pushed and running as GitHub Actions run `39063905270`: 17 included jobs have passed and two Windows jobs are still in progress as last checked. Linux Wayland and all specifically excluded provider/platform/minor combinations remain **NOT TESTED**.
- **Compatibility policy:** GTK runtime minimum = 4.8; GTK 4.6 is too old and rejected by the installer. The `Gtk 4.0` namespace remains the typelib API version. Linux X11 has full-app evidence for GTK 4.8.2, 4.14.5, and 4.24.1. GitHub run `39063905270` has successful native GTK/GLArea smoke jobs for GTK 4.8/4.10/4.12/4.14/4.20/4.22/4.24 on Linux; 4.12/4.14/4.20/4.22/4.24 on Windows and macOS arm64. Windows 4.8/4.10 are still in progress; GTK 4.16/4.18 and macOS arm64 4.8/4.10 remain **NOT TESTED** due to provider artifact gaps. Linux Wayland remains **NOT TESTED**. Python 3.10.22/3.12.3/3.12.15 have Linux test evidence; no maximum is approved. See `docs/EASYHYBRID4_REPORT.md` and `docs/GTK4_COMPATIBILITY.md`.
- **Rule:** Update the active task pointer after a completed or blocked task. Do not change task ordering without recording why.

## 6. End-of-session report template

```text
Task ID:
Summary:
Changed files and submodule SHAs:
Commits pushed / pending:
OS/architecture tested:
Python / PyGObject / GTK / GLib versions observed:
Display server and OpenGL vendor/renderer (if tested):
Tests PASS:
Tests FAIL:
Tests NOT TESTED and why:
Scientific-regression impact:
Documentation and checkbox updates:
Unresolved blockers:
Next eligible task:
```

## 7. Operating rules for roadmap maintenance

- Do not erase historical failed tests or remove unfinished tasks to make progress appear better. Add dated evidence and preserve the relevant history or link to CI runs.
- New issues discovered mid-work become numbered subtasks under the relevant phase; only urgent blockers interrupt the current task.
- Any decision to raise `GTK_MIN`, remove an OS/architecture, replace the rendering backend, or change scientific outputs requires an explicit architecture decision note and an updated compatibility table.
- A large refactor must first be split into small deliverables with separate tests and rollback boundaries.
- Keep platform and GTK specifics in tests/adapters, not in feature logic.
- Never commit secrets, private credentials or large proprietary molecular inputs as test fixtures.
