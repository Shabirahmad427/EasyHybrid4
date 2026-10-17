# GTK4 and Python Compatibility Contract

Status: evidence-based target selected; lower/upper GTK runtime validation is
still pending. This document distinguishes the intended range from versions
actually tested.

## Selected target and verified versions

| Contract item | Selection | Evidence / status |
|---|---|---|
| GTK API namespace | `Gtk 4.0` | `gi.require_version("Gtk", "4.0")` and GtkBuilder resources target 4.0. This names GTK's API namespace, not a 4.0 runtime. |
| `GTK_MIN` target | GTK `4.0` | The installer currently rejects versions below `(4, 0)`; source requests no GTK3 namespace. Optional APIs found in this audit are guarded. GTK 4.0 runtime **NOT TESTED**. |
| Local GTK runtime verified | GTK `4.14.5` / GLib `2.80.0` | The Linux development environment. Existing unit tests pass; this is not a live window/GL verification. |
| Current upstream stable target | GTK `4.22.5` (as checked 2026-10-17) | [GTK project release status](https://www.gtk.org/). GTK 4.22.5 **NOT TESTED** in this project. |
| `GTK_LATEST_VERIFIED` | `4.14.5` | Highest project runtime actually exercised so far; it is not the current upstream stable release. |
| Python target | Python `>=3.10` candidate | Source contains evaluated PEP 604 annotations such as `Gtk.Window | None`, which require Python 3.10+. Only Python 3.12.3 was executed. pDynamo/native dependency support on other Python versions is **NOT TESTED**; no upper bound is approved yet. |

The intended compatibility target is GTK 4.0 through current GTK4 stable, with
the explicit qualification that only GTK 4.14.5 has been exercised in this
checkout. This is not a blanket pass for every GTK4 minor, every platform, or
future releases. GTK 4.0 and GTK 4.22.5 need real CI jobs before the range can
be described as verified.

## Dependency resolution strategy

- GTK4, GLib and their introspection typelibs are native platform dependencies;
  do not try to version them through `pip`. Provision GTK natively on each CI
  OS and report the version loaded at runtime.
- `requirements.txt` currently provides lower bounds for Python packages but
  no lock/constraints set. Keep those minimum declarations, and add platform
  and Python-specific constraints only when CI proves an incompatibility or a
  reproducibility need. CI should install from the same declared requirements
  used by contributors, then publish the resolved package versions.
- pDynamo3 and optional QC engines remain external binary/scientific
  dependencies. The only verified pDynamo environment is the configured
  Python 3.12.3 Linux environment. Do not claim other Python/platform
  combinations based on graphics-only builds.
- A release support claim requires tests for the lowest GTK/Python targets and
  a current stable GTK runtime. Raise `GTK_MIN` only when a required API or
  dependency cannot be kept compatible, document the exact blocker, and
  provide a tested migration/fallback plan.

## Source audit: minor-version APIs

- GTK 4.8's `Gtk.Picture.set_content_fit()` is feature-detected in
  `easyhybrid.py`; the fallback uses `set_can_shrink()` and
  `set_keep_aspect_ratio()`. GTK documents `set_content_fit` as available since
  4.8 and the aspect-ratio API as deprecated since 4.8. See the [GTK
  `Gtk.Picture` API](https://docs.gtk.org/gtk4/method.Picture.set_content_fit.html).
- GTK 4.8's scroll-unit API is feature-detected in
  `src/graphics_engine/src/vismol/gui/vismol_gtkwidget.py` using
  `hasattr(Gtk.EventControllerScroll, "get_unit")`; earlier runtimes request
  discrete wheel steps. See the [GTK scroll-controller API](https://docs.gtk.org/gtk4/method.EventControllerScroll.get_unit.html).
- No `Gtk.FileDialog` or `Gtk.AlertDialog` usage was found in the source scan;
  both APIs were introduced in GTK 4.10. The application uses its existing
  async chooser and message-window helpers instead. See GTK's
  [`Gtk.FileDialog` API](https://docs.gtk.org/gtk4/class.FileDialog.html).
- The installer checks the loaded GTK version at runtime, but it does not
  validate every API referenced by Python or GtkBuilder resources. The broad
  removed/deprecated API audit and minimum-runtime builder/UI tests remain
  follow-up items.

## Validation matrix

| Version/platform | Status |
|---|---|
| Linux x86_64, GTK 4.14.5 / GLib 2.80.0 / Python 3.12.3 | Existing non-GUI suite: 23 passed. Builder resources were validated against the installed GTK 4.14 runtime in the earlier inventory. Real window and GL smoke: NOT TESTED. |
| GTK 4.0, Linux | NOT TESTED; target minimum is selected but no runtime/build is available locally. |
| GTK 4.22.5, Linux | NOT TESTED; current stable target is unavailable in the local runtime. |
| Intermediate GTK4 minors | NOT TESTED except for the single 4.14.5 runtime above. |
| Windows native GTK4 / Python | NOT TESTED; no native runner was executed. |
| macOS arm64/x86_64 GTK4 / Python | NOT TESTED; no native runner was executed. |

No runtime code changed in this contract decision. Existing behavior tests were
rerun; GTK_MIN and current stable runtime acceptance still requires the
versioned CI tasks in Phase 5.
