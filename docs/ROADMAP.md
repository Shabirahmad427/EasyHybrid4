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

- **GTK4 range:** First measure the actual GTK version and APIs used; then pin a documented **minimum supported GTK4 minor release** (`GTK_MIN`) and continuously validate against the **latest stable GTK4 available** (`GTK_LATEST`). Do not promise every past or future GTK4 minor release. GTK 4.0 is the API major version, not the current runtime minor release.
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
| Linux x86_64 / X11 | Import, UI, GL, scientific regression, package | NOT TESTED |
| Linux x86_64 / Wayland | Import, UI, GL, input, scaling | NOT TESTED |
| Linux second distribution / native GTK | Startup, integration, package | NOT TESTED |
| Windows x64 / native GTK4 | Import, UI, GL, dialogs, package | NOT TESTED |
| macOS arm64 / native GTK4 | Import, UI, GL, Retina, trackpad, package | NOT TESTED |
| macOS x86_64 (if available) | Import, UI, GL, package | NOT TESTED |
| GTK_MIN | API/feature and UI smoke tests | NOT TESTED |
| Intermediate GTK4 version(s) | API/feature and UI smoke tests | NOT TESTED |
| GTK_LATEST | API/feature and UI smoke tests | NOT TESTED |

Use a **pairwise smoke matrix on pull requests** and more extensive native/version runs before releases; report missing combinations. CI images alone cannot prove real GPU or real trackpad behavior.

## 2. Required structure and permanent documents

- `docs/ROADMAP.md` — this file: task inventory, phase gates, completion evidence.
- `docs/ARCHITECTURE.md` — GUI / science / graphics / platform module boundaries, architecture decisions.
- `docs/GTK4_COMPATIBILITY.md` — GTK_MIN, GTK_LATEST_VERIFIED, forbidden APIs, compatibility helpers and fallbacks.
- `docs/PLATFORM_SUPPORT.md` — target architectures/backends, runtime prerequisites and native caveats.
- `docs/FEATURE_PARITY.md` — EasyHybrid3-to-EasyHybrid4 feature-by-feature comparison.
- `docs/TEST_MATRIX.md` — exact runner, installed versions, tests, status and logs/artifacts.
- `docs/KNOWN_LIMITATIONS.md` — incomplete functionality with reproducible issue links.
- `AGENTS.md` (if absent) — short permanent agent instruction: always read this roadmap and do not overstate tests.

## 3. Work queue: execute IN ORDER; one checkbox per independently verifiable task

### Phase 0 — Inventory and reproducible baseline (BLOCKS all other phases)

- [ ] **EH4-000** Record remote URLs, current branches, commit IDs, dirty tree, tags, licenses, and recursively resolved submodule SHAs. Identify EasyHybrid3 reference and EasyHybrid4 fork roots. **Accept:** baseline recorded in architecture docs; no uncommitted user changes overwritten.
- [x] **EH4-001** Map package/module layout and entry points, GTK3 vs GTK4 usage, `.ui` resources, PyGObject, GLib, pDynamo, graphics module, optional libraries, scripts and installers. **Accept:** annotated dependency and API inventory with file references.
- [ ] **EH4-002** Build/install and run existing tests on available Linux environment without editing runtime behavior; capture exact package/runtime versions and failures. **Accept:** reproducible setup commands plus baseline logs in test documentation.
- [ ] **EH4-003** Compare EasyHybrid3 workflows to current EasyHybrid4; tag `WORKING`, `BROKEN`, `UNIMPLEMENTED`, `UNTESTED`. **Accept:** feature parity checklist including molecular interaction and scientific exports.
- [ ] **EH4-004** Select `GTK_MIN`, supported Python versions and dependency resolution strategy based on accessible CI/runtime builds and APIs in source. **Accept:** documented supported interval and criteria for raising minimum; no unsupported universal GTK4 claim.
- [ ] **EH4-005** Add initial repo docs listed in Section 2; create focused regression fixtures and a safe test-data policy. **Accept:** a new contributor or Codex session can reproduce baseline and resume work.

**Phase 0 gate:** Source dependencies known, runtime/versions captured, proposed compatibility contract justified, parity baseline written and CI strategy realistic.

### Phase 1 — Architecture and GTK4 adaptation

- [ ] **EH4-100** Separate GUI/presentation, domain/scientific services, graphics abstraction and OS integration. **Accept:** testable science modules without requiring GTK display.
- [ ] **EH4-101** Centralize GTK feature detection in one compatibility module; avoid hardcoding specific distributions or GTK patches. **Accept:** unit tests for supported branches and fallback behavior.
- [ ] **EH4-102** Review Gtk.Application lifecycle, Gio actions, UI templates/resources and GtkBuilder definitions for supported GTK4 APIs. **Accept:** open/close smoke checks without critical warnings at GTK_MIN and GTK_LATEST where testable.
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
- [ ] **EH4-501** Build GTK_MIN and GTK_LATEST compatibility checks; intermediate matrix where practical. **Accept:** version detection reports actual loaded GTK/GLib runtime, not requested version.
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
| 2026-10-17 | EH4-000 | None; EasyHybrid4 `.git` metadata unavailable | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | `git -C . status/rev-parse` and branch/remotes/tags: BLOCKED (`.git/` empty, read-only); read `.gitmodules`, both license files, and EasyHybrid3 Git/submodule metadata. No runtime tests for this inventory task. | NOT TESTED | PARTIAL; EH4 remote, branch, commit, tags, dirty state, and local graphics SHA are unknown. See `docs/ARCHITECTURE.md`. |
| 2026-10-17 | EH4-000 | `843c82a` (blocker record) | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Verified `main`, HEAD `bea94210ed7c23f71d2241f8abe3c849ade18561`, clean tree, no configured remotes, and no tags. `.gitmodules` declares graphics submodule, but `git ls-tree` gives mode `040000`, `git submodule status --recursive` is empty, and files are tracked individually. EasyHybrid3 reference and both licenses recorded in `docs/ARCHITECTURE.md`. | NOT TESTED | INCOMPLETE: no EasyHybrid4 remote/fork URL and no graphics upstream SHA/submodule metadata. Missing information recorded; no inference made. |
| 2026-10-17 | EH4-001 | `f69e4c4` | Linux x86_64, kernel 6.8.0-147-generic | Python 3.12.3 / PyGObject 3.48.2 / GTK 4.14.5 / GLib 2.80.0 | Source inventory in `docs/DEPENDENCY_INVENTORY.md`; parsed all 53 `.glade` resources and confirmed each declares Gtk 4.0; scanned Python imports and found GTK 4 requests with no GTK 3 namespace requests. `$HOME/software/envs/easyhybrid312/bin/python -m pytest -q tests/`: **23 passed**, one pytest cache warning because `$HOME/software/.pytest_cache` is read-only. No runtime code changed, so no regression test was added. | NOT TESTED (real Gtk.GLArea context/renderer) | COMPLETE for the documentation inventory only. Native Windows/macOS, Wayland, and non-installed GTK minors remain NOT TESTED. EH4-000 remote/submodule blockers remain open. |

### Active task and blockers

- **Next task:** `EH4-000` — resolve the EasyHybrid4 remote/fork root and graphics-engine upstream revision; this remains the first unchecked task. EH4-001's independent inventory is complete and documented.
- **Current blocker:** EasyHybrid4 has no configured remote and its declared graphics submodule is an ordinary tracked directory without an upstream SHA. Keep both unresolved; do not infer the source revision from EasyHybrid3 or `.gitmodules`.
- **Compatibility policy:** `GTK_MIN = TBD`, `GTK_LATEST_VERIFIED = TBD`, Python support = TBD. Codex must fill these from evidence during Phase 0.
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
