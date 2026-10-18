"""GTK-main-loop helpers for trajectory playback."""

import math

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402


def timer_interval_ms(fps):
    """Return a safe GLib timeout interval for a requested playback rate."""
    try:
        fps = float(fps)
    except (TypeError, ValueError):
        fps = 1.0
    if not math.isfinite(fps) or fps < 1.0:
        fps = 1.0
    return max(1, int(round(1000.0 / fps)))


def start_playback_timer(callback, fps, *, glib=GLib):
    """Schedule one playback tick on the GTK main loop."""
    return glib.timeout_add(timer_interval_ms(fps), callback)


def stop_playback_timer(source_id, *, glib=GLib):
    """Remove a scheduled playback tick, if one is active."""
    if source_id is not None:
        glib.source_remove(source_id)


def ping_pong_playback_tick(player, *, glib=GLib):
    """Advance one step and reverse direction at either trajectory end."""
    if not player.running:
        player._playback_source_id = None
        return glib.SOURCE_REMOVE

    step = max(1, int(player.entry_step.get_value()))
    if player.frame_forward:
        value = player.forward(step=step)
        if value >= player.upper - 1:
            player.frame_forward = False
    else:
        value = player.reverse(step=step)
        if value <= 0:
            player.frame_forward = True
    return glib.SOURCE_CONTINUE


def looping_playback_tick(player, *, glib=GLib):
    """Advance one frame and wrap to the first frame at the end."""
    if not player.running:
        player._playback_source_id = None
        return glib.SOURCE_REMOVE

    player.vm_session.set_frame(int(player.value))
    player.value += 1
    if player.value >= player.upper:
        player.value = player.lower
    return glib.SOURCE_CONTINUE
