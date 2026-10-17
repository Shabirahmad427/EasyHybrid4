# GPU-accelerated PySCF on `[remote Linux host]`

This is a follow-up to `PYSCF_INTEGRATION.md` (the CPU-only PySCF QC engine,
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
| `$HOME/software/envs/pdynamo3` (Python 3.10.20) | 2.14.0 | `gpu4pyscf-cuda12x` 1.8.1 | 1.26.4 | 13.6.0 | `activate_pdynamo3` for scripting or `easyhybrid` for the GUI |

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
- `_unpicklable` (the pickling-safety mechanism from `PYSCF_INTEGRATION.md`)
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

Same pattern as every other PySCF field in `PYSCF_INTEGRATION.md`. Confirmed
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
Environment: $HOME/software/envs/pdynamo3
pDynamo:     $HOME/software/pDynamo3
EasyHybrid:  $HOME/software/EasyHybrid3
Graphics:    $HOME/software/EasyHybrid3/src/graphics_engine
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
