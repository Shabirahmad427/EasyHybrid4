#!/usr/bin/env bash

source "$HOME/software/pdynamo3.sh"

# Avoid loading a GTK3-only desktop module into the GTK4 process.
unset GTK3_MODULES

# Select X11 explicitly on X11 desktops when GTK has no backend preference.
# This avoids GTK initialization failures when Wayland is unavailable.
if [[ -n "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" && -z "${GDK_BACKEND:-}" ]]; then
    export GDK_BACKEND=x11
fi

EASYHYBRID4_HOME="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export EASYHYBRID_HOME="$EASYHYBRID4_HOME"
export PYTHONPATH="$EASYHYBRID4_HOME${PYTHONPATH:+:$PYTHONPATH}"

cd "$EASYHYBRID4_HOME"
exec "$PDYNAMO3_PYTHONCOMMAND" easyhybrid.py "$@"
