"""Formatting helpers for user-facing OpenGL startup diagnostics."""

import re
from logging import getLogger

logger = getLogger(__name__)


def parse_gl_version(value):
    """Return ``(major, minor)`` from a GL_VERSION string, or ``None``."""
    if isinstance(value, bytes):
        value = value.decode("ascii", "replace")
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)(?:\.|\s|$)", str(value or ""))
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def graphics_failure_message(phase, *, gl_version=None, context_error=None, exception=None):
    """Build concise primary and detailed diagnostics for graphics failure."""
    primary = "EasyHybrid could not start its molecular graphics view."
    reasons = ["Failure during %s." % phase]
    if gl_version:
        reasons.append("Detected OpenGL version: %s." % gl_version)
    else:
        reasons.append("No usable OpenGL version was reported.")
    if context_error:
        reasons.append("GTK context error: %s" % context_error)
    if exception:
        reasons.append("Graphics error: %s" % exception)
    reasons.append(
        "EasyHybrid requires an OpenGL 3.3 core context. Check that the graphics "
        "driver is installed and supports OpenGL 3.3 or newer."
    )
    return primary, " ".join(reasons)


def report_graphics_failure(widget, phase, *, gl_version=None, context_error=None, exception=None):
    """Disable repeated GL failure handling and present the portable GTK dialog."""
    if getattr(widget, "_graphics_failed", False):
        return None
    widget._graphics_failed = True
    primary, details = graphics_failure_message(
        phase,
        gl_version=gl_version,
        context_error=context_error,
        exception=exception,
    )
    logger.error("%s %s", primary, details)
    try:
        from gui.message_dialogs import show_message

        return show_message(
            widget,
            primary,
            "The rest of the application remains available, but molecular rendering is disabled.",
            kind="error",
            title="Graphics unavailable",
            details=details,
        )
    except Exception:
        # The GLArea can fail before it has a usable toplevel. Preserve the
        # diagnostic in the log even if GTK cannot present the fallback.
        logger.exception("Could not present the graphics failure dialog")
        return None
