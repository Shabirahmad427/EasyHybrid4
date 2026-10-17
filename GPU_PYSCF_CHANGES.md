# PySCF and GPU4PySCF integration in EasyHybrid3

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

- `$HOME/.local/bin/easyhybrid`
- Stable Conda environment `$HOME/software/envs/pdynamo3`
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
in `pDynamo3/GPU_PYSCF_CHANGES.md`.

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
- `$HOME/software/envs/pdynamo3`
- `$HOME/software/pDynamo3`
- `$HOME/software/EasyHybrid3`
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
