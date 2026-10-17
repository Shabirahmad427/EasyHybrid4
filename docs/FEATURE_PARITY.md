# EasyHybrid3 to EasyHybrid4 Feature Parity Audit

Date: 2026-10-17. This is a source and test inventory, not a claim that the
complete applications have been exercised. EasyHybrid3 was inspected
read-only at `$HOME/software/EasyHybrid3`; its implementation summary is
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
| Interactive Builder: create/edit loaded molecules, undo, hydrogen/charge handling, fragments, structures, solvation, DYFF/OPLS tools | `src/gui/windows/builder/`; detailed scope in EH3 implementation report §§3.1 and Part II | GTK4 counterparts under `src/gui/windows/builder/`; GTK4 migration described in `GTK4_PORT.md` | **UNTESTED** — component source exists; existing regression suite covers bond operations/perception only. No live Builder interaction, full undo/persistence round trip, or real pDynamo-backed editing run was recorded. |
| Molecular viewer, picking, selection, representations, camera and trajectory playback | `src/graphics_engine/src/vismol/` and EH3 report §§2–3 | `src/graphics_engine/src/vismol/`, GTK4 integration in `src/gui/main/main_window.py` | **UNTESTED** — no real `Gtk.GLArea` context/render test or end-to-end mouse/picking validation in this baseline. |
| GTK widget lifecycle / window startup | GTK3 main window and auxiliary Glade windows | `easyhybrid.py`, `src/gui/main/`, GTK4 GtkBuilder resources | **BROKEN (diagnostic observed)** — user-provided launch output contains two `gtk_box_remove` GTK critical assertions. Whether these affect visible behavior is unknown; the responsible widget-removal path has not yet been isolated. |
| System import, force-field assignment, merge/prune, trajectory import and `.easy` project save/load | EH3 `import_system.py`, session methods, `io_data.py`; report §3.6 | `src/gui/windows/setup/windows_and_dialogs/system_windows/`, `src/pdynamo/pDynamo2EasyHybrid/{session,io_data,import_trajectory}.py` | **UNTESTED** — parallel code paths are present; no representative file-import or project round-trip fixture has been run as part of this audit. |
| MM/QC/QC-MM model setup and calculations | EH3 QC setup modules and pDynamo session integration; report §3.5 | `src/gui/windows/setup/windows_and_dialogs/qc_setup/`, `src/pdynamo/pDynamo2EasyHybrid/session.py` | **UNTESTED** — code and engine setup modules exist, but no calculation-level pDynamo result comparison was run. |
| Single point, geometry optimization, MD, normal modes and transition-state search | EH3 `src/gui/windows/simulation/` | Same named GTK4 window family under `src/gui/windows/simulation/`; dispatch in `src/pdynamo/pDynamo2EasyHybrid/simulations_mixin.py` | **UNTESTED** — windows and dispatch exist; no sample scientific run or output comparison was performed. |
| 1D/2D PES scans, umbrella sampling, WHAM, reaction paths/NEB and CPR | EH3 report §3.3; `PES_scan_window.py`, `umbrella_sampling_window.py`, `WHAM_analysis_window.py`, path/CPR tools | Corresponding GTK4 modules and pDynamo methods are present; see `GTK4_PORT.md` | **UNTESTED** — UI/resources and dispatch are present; no generated-input or numerical-output comparison was run. |
| Analysis: RDF, density, RMSD/RMSF, Ramachandran, surfaces, WHAM and trajectory tools | EH3 report §3.4 and `src/gui/windows/analysis/` | Corresponding modules exist under `src/gui/windows/analysis/`; GTK4_PORT documents RDF, density, RMSF and Ramachandran migration | **UNTESTED** — source presence is verified, but no analysis fixture/result comparisons were run for this audit. |
| Infrared spectrum workflow | EH3 report §3.4 and infrared changelog in §7 | No EasyHybrid4 infrared/spectrum window or menu handler was found by filename or source-symbol search; current `src/util/extras/` has QC model adapters but no corresponding GUI workflow | **UNIMPLEMENTED** — restore or explicitly retire with a documented feature decision; do not treat generic dipole/QC support as parity. |
| AutoDock Vina and AutoDock-GPU setup/run/import | EH3 report §3.2 and `setup/windows_and_dialogs/system_windows/prepare_vina_docking.py`, `prepare_autodock_gpu.py` | No corresponding docking modules or menu/action handlers found under `src/` | **UNIMPLEMENTED** — both EH3 docking front ends are absent from the audited EasyHybrid4 source. |
| NAMD/SMD, AMBER `tleap`, Packmol and Antechamber preparation front ends | EH3 report §3.5 and `prepare_namd_run.py`, `prepare_smd_run.py`, `prepare_amber_system.py`, `prepare_packmol_run.py`, `prepare_ligand_antechamber.py` | No matching setup windows/front ends found. The bundled solvent builder's Packmol-style placement is not the same as those preparation workflows. | **UNIMPLEMENTED** — the EH3 external preparation dialogs are not present. |
| Scientific system/script exports and simulation output files | EH3 export dialogs and report §3.6 | `src/gui/windows/setup/windows_and_dialogs/dialogs/export_dialogs.py`, `pDynamo2EasyHybrid/session.py::export_system`, pDynamo scan/sampling methods | **UNTESTED** — export code exists; no exported-file schema, restart, or numerical output fixture comparison was done. |
| Process manager, jobs, recent files, and project/session management | EH3 report §3.6 | `src/gui/windows/setup/process_manager_window.py`, session/serialization modules, main-window actions | **UNTESTED** — source paths are present; lifecycle and restart behavior were not exercised. |

## Test evidence and limits

On Linux x86_64 with Python 3.12.3, PyGObject 3.48.2, GTK 4.14.5 and GLib
2.80.0:

- EasyHybrid4: `$HOME/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider tests/` — **23 passed**.
- EasyHybrid3 reference: `$HOME/software/envs/easyhybrid312/bin/python -m pytest -q -p no:cacheprovider $HOME/software/EasyHybrid3/tests/` — **23 passed, 4 skipped**.
- Both suites are primarily GTK/display-free atom/bond and chemistry logic tests. They do not test the GUI, pDynamo calculations, exports, real OpenGL, Windows, or macOS.
- Linux Wayland/X11 live GUI, GTK 4.0, other GTK minors, Windows, and macOS are **NOT TESTED**. See `TEST_MATRIX.md`.

This audit changes documentation only. No new executable behavior was added,
so no new behavioral regression test was appropriate. The identified parity
gaps and the observed GTK critical warning become follow-up work; this checklist
does not authorize removing or changing scientific behavior.
