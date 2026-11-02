# EasyHybrid4 v4.0.0

> Source-only release. GitHub's automatically generated source archive for the
> tag is the release artifact. This release does not provide app bundles,
> installers (MSI, DMG, AppImage, etc.), or a bundled Python/GTK/pDynamo runtime.

## Source

- Tag: `v4.0.0`
- Commit: the commit the `v4.0.0` tag points to (also given on the GitHub
  release page). It is the merge of the release PR into `main`.
- GitHub source archive URL:
  `https://github.com/Shabirahmad427/EasyHybrid4/archive/refs/tags/v4.0.0.tar.gz`
  (and `.zip`)
- Release date (UTC): 2026-11-02

## Compatibility and validation

- Tested combinations: [`SUPPORT_TABLE.md`](SUPPORT_TABLE.md), generated from
  native matrix run `41340875386`: 30/30 PASS across Linux x86_64, Windows
  x86_64, macOS arm64 (macOS 15.8.2) and Intel macOS for every GTK minor
  4.8–4.24. Every cell builds pDynamo3 `Shabirahmad427/pDynamo3@08f73f5`.
- Native matrix run and gate: the tagged commit's own full matrix run is
  linked on the GitHub release page.
- Fresh source checkout, install, launch and close: every matrix cell runs
  `git clone --recurse-submodules`, `python install.py --ci`, launches
  `easyhybrid.py` and closes it natively (`SOURCE_CHECKOUT_NATIVE_CLOSE=PASS`).
- Manual report links:
  - macOS Apple Silicon (MacBook Air M4, macOS 27.2, GTK 4.24.1):
    [`manual-validation/2026-11-02-macos-arm64-4804f27.md`](manual-validation/2026-11-02-macos-arm64-4804f27.md)
  - Windows: **NOT TESTED** manually (waived by the maintainer for this release).
  - Linux X11 and Wayland: **NOT TESTED** manually (waived by the maintainer
    for this release).
  - Intel macOS: **NOT TESTED** manually (no hardware).
- macOS trackpad review report: the macOS report above, check M2 (PASS,
  recorded as an overall result without a per-gesture breakdown).
- Untested: see Known limitations.

## Installation

Follow the source-checkout instructions in the [README](../README.md). Install
GTK 4 and pDynamo3 separately using their platform-specific instructions;
EasyHybrid4 does not bundle those runtimes or scientific libraries. CI builds
the maintainer's pDynamo3 fork at `08f73f5`, which carries the GPU4PySCF/PySCF
adapter and the xTB empty-input fix on top of upstream `6b28dd8`.

## Changes

First EasyHybrid4 release: a GTK4 port of EasyHybrid3 on pDynamo3. The
roadmap in [`ROADMAP.md`](ROADMAP.md) lists each task and its evidence.
Highlights:

- GTK 4.8–4.24 support on Linux, Windows and macOS (native Quartz), verified in
  a 30-cell native matrix with real-app open/pick/render/close cycles.
- Portable colour-ID picking (fixed on macOS core-profile OpenGL), HiDPI-aware
  pointer mapping, and Retina backing-framebuffer detection.
- Trackpad and smooth-scroll normalisation with bounded camera clipping (EH4-203).
- Spawn-safe simulation workers for macOS (EH4-408) and scan step-count
  validation before launch (EH4-409).
- Help → About works on GTK4 and includes a System report (EH4-510).
- GPU4PySCF/PySCF adapter guards (EH4-407) and the xTB empty-input fix, via the
  pDynamo3 fork.

## Known limitations

- **NOT TESTED:** Linux Wayland; physical GPUs other than the maintainer's
  Apple M4 and NVIDIA RTX 4060 Ti; physical Retina/HiDPI scaling checks;
  multi-monitor; screen readers; physical mouse-wheel behaviour on macOS.
- **NOT TESTED:** manual validation on Windows and Linux (CI coverage only).
- **NOT TESTED:** cross-process clipboard on Windows and macOS; the native
  Windows COM file chooser (the tested in-process chooser is used).
- GPU4PySCF guards are verified only locally on an NVIDIA RTX 4060 Ti; hosted
  runners have no PySCF or GPU.
- Hosted CI uses software renderers (llvmpipe, Apple Software Renderer); do
  not infer physical hardware support from it.

## Licenses and third-party components

EasyHybrid4 application code is GPL-3.0. Preserve and review all notices in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), including the
CC BY-NC 4.0 VisMol graphics engine. The combined source tree is therefore
**not** GPL-only, and as distributed it is for non-commercial use.

## Release gate checklist

- [x] The release tag points to the reviewed commit and all referenced commits
      are reachable.
- [x] EH4-200 graphics authorship, ownership, and permission facts are recorded.
- [x] EH4-203 has a dated physical macOS trackpad report.
- [ ] EH4-505 required manual reports are signed and dated. **Waived for
      v4.0.0 by the maintainer (2026-11-02):** only the macOS Apple Silicon
      report exists; Windows and Linux X11/Wayland are NOT TESTED manually.
      EH4-505 stays open.
- [x] The exact tagged commit passes the required full native matrix and
      source-checkout install/launch/close checks.
- [x] `SUPPORT_TABLE.md`, license notices, installation instructions, and
      known limitations match the tagged commit.
- [x] The generated source archive has been downloaded and inspected; no
      credentials, local data, or build artifacts are included.
- [x] Release notes identify the exact tag/commit and link to the evidence.
