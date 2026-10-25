# Manual native validation (EH4-505)

The native GitHub matrix runs every supported GTK 4 minor on Linux, Windows
and macOS, but only on hosted runners: software renderers, one virtual or
small monitor, scale factor 1, synthetic OS input, no screen reader. This
procedure covers what those runners **cannot** show. It is run by a person on
real hardware and recorded in a signed, dated report.

## Rules

1. **No inferred passes.** Mark a check PASS only if you performed it on this
   machine and saw the expected result. Otherwise write FAIL (with what you
   saw) or NOT TESTED (with the reason). Never copy a result from another
   machine, another GTK version or the CI matrix.
2. **Record exact versions** from *Help → About → System* (EH4-601) and paste
   that block into the report unchanged. A report without it is invalid.
3. **One report per machine and EasyHybrid commit.** Name it
   `docs/manual-validation/YYYY-MM-DD-<os>-<arch>-<short-commit>.md`, start
   from [`manual-validation/TEMPLATE.md`](manual-validation/TEMPLATE.md), and
   sign and date it at the end.
4. Attach screenshots or a short screen recording for every FAIL, and for
   visual checks (HiDPI, multi-monitor) even when they pass.

## Fixtures

Use the repository's frozen fixtures so results are comparable:
`tests/fixtures/water.pdb` (3 atoms) for interaction checks, and a protein you
normally work with for performance and appearance.

## Checks by platform

Run the **common** checks everywhere, then the section for your platform.

### Common (all platforms)

| ID | Check | Expected |
|---|---|---|
| C1 | Launch EasyHybrid, open `water.pdb` with *File → Open* | molecule renders; no error dialog |
| C2 | Click the oxygen | it is picked/selected; selection changes visibly |
| C3 | Rotate (drag), pan, zoom with the **physical mouse wheel** | smooth, correct direction, no jumps |
| C4 | Measure H1–O–H2 with pk1/pk2/pk3 picking | distances ≈ 0.957 Å, angle ≈ 104.5° |
| C5 | *File → Save*, close, reopen the `.easy` file | camera and molecule restored |
| C6 | Shortcuts on the **physical keyboard**: New/Open/Save/Save As/Quit (Ctrl, or ⌘ on macOS) | each opens the matching action |
| C7 | Copy a file path from EasyHybrid, paste into another application, and back | text arrives intact (including non-ASCII) |
| C8 | Native file dialog: open, cancel, save to a folder with spaces and non-ASCII characters | correct path used; cancel does nothing |
| C9 | About → System tab | lists OS, GTK, GL renderer of the **real GPU**, pDynamo3 version |
| C10 | Screen reader (Narrator/Orca/VoiceOver): move through toolbar buttons | each button is announced with a name, not just "button" |

### Windows (x86_64, real GPU)

| ID | Check | Expected |
|---|---|---|
| W1 | Display scaling 100 %, 150 %, 200 % (Settings → Display) | window fits; text and icons sharp; picking hits the atom under the pointer |
| W2 | Two monitors with different scaling; drag the window between them | re-renders sharp on each; picking still accurate |
| W3 | Change scaling **while EasyHybrid is running** | view re-renders; no crash or blank view |
| W4 | Install path and user name containing spaces/non-ASCII | starts, opens and saves files |

### Linux (X11 and Wayland, real GPU)

| ID | Check | Expected |
|---|---|---|
| L1 | Run under **Wayland** and under **X11** sessions (record `GDK backend` from About) | C1–C9 pass on both, or record which fail |
| L2 | Fractional scaling 125 %/150 %/200 % (Wayland) and `GDK_SCALE=2` (X11) | window fits (its minimum width is about 390–560 logical px, depending on the UI font); picking accurate |
| L3 | Two monitors, different scaling | as W2 |
| L4 | Proprietary vs Mesa driver if available | record renderer; C1–C3 pass |

### macOS (Apple Silicon M-series, and Intel where available)

| ID | Check | Expected |
|---|---|---|
| M1 | Built-in **Retina** display | sharp rendering; framebuffer = 2× logical; picking accurate |
| M2 | **Trackpad**: two-finger scroll to zoom, pinch, drag to rotate, with and without ⌥/⇧ modifiers (EH4-203) | smooth, natural direction, no runaway zoom |
| M3 | Magic Mouse / external mouse wheel | as C3 |
| M4 | External non-Retina monitor; drag the window across | re-renders correctly on both |
| M5 | ⌘N/⌘O/⌘S/⇧⌘S/⌘Q on the built-in keyboard | as C6 (Ctrl must **not** be required) |
| M6 | Intel Mac (if available) | repeat C1–C9 and M1 |

## What results feed back into

- A PASS on real hardware can close the matching **NOT TESTED** item in
  `docs/ROADMAP.md` (e.g. EH4-203 trackpad, EH4-302 Retina/multi-monitor/
  Wayland, EH4-301 screen readers), citing the report file.
- A FAIL becomes a new roadmap issue with the report attached.
- EH4-505 itself is complete only when reports exist for Windows, Linux
  (X11 and Wayland) and macOS Apple Silicon.
