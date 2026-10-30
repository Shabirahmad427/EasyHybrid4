# EasyHybrid4 vX.Y.Z

> Source-only release. GitHub's automatically generated source archive for the
> tag is the release artifact. This release does not provide app bundles,
> installers, or a bundled Python/GTK/pDynamo runtime.

## Source

- Tag:
- Commit:
- GitHub source archive URL:
- Release date (UTC):

## Compatibility and validation

- Tested combinations: see [`SUPPORT_TABLE.md`](SUPPORT_TABLE.md) (identify the
  exact support-table revision and matrix run).
- Native matrix run and gate:
- Fresh source checkout, install, launch, and close result:
- Manual report links: Windows; Linux X11; Linux Wayland; macOS Apple Silicon;
  Intel macOS (if available).
- macOS trackpad review report:
- Untested hardware, operating systems, GTK versions, or workflows:

## Installation

Follow the source-checkout instructions in the [README](../README.md). Install
GTK 4 and pDynamo3 separately using their platform-specific instructions;
EasyHybrid4 does not bundle those runtimes or scientific libraries.

## Changes

-

## Known limitations

- Include the current support-table restrictions and relevant **NOT TESTED**
  items. Do not infer physical-device or hardware support from hosted CI.

## Licenses and third-party components

EasyHybrid4 application code is GPL-3.0. Preserve and review all notices in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), including the
CC BY-NC 4.0 VisMol graphics engine. Do not describe the combined source tree
as GPL-only.

## Release gate checklist

- [ ] The release tag points to the reviewed commit and all referenced commits
      are reachable.
- [ ] EH4-200 graphics authorship, ownership, and permission facts are recorded.
- [ ] EH4-203 has a dated physical macOS trackpad report.
- [ ] EH4-505 required manual reports are signed and dated.
- [ ] The exact tagged commit passes the required full native matrix and
      source-checkout install/launch/close checks.
- [ ] `SUPPORT_TABLE.md`, license notices, installation instructions, and
      known limitations match the tagged commit.
- [ ] The generated source archive has been downloaded and inspected; no
      credentials, local data, or build artifacts are included.
- [ ] Release notes identify the exact tag/commit and link to the evidence.
