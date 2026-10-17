# PySCF as a QC Engine in EasyHybrid3

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
