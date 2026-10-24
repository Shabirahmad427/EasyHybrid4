"""Focused tests for the process manager's nonblocking cancellation path."""
from types import SimpleNamespace

from gui.windows.setup import process_manager_window as process_manager


def test_terminate_process_tree_signals_worker_and_descendants(monkeypatch):
    signalled = []
    monkeypatch.setattr(process_manager, "_get_descendant_pids", lambda _pid: [202, 203])
    monkeypatch.setattr(process_manager.os, "kill", lambda pid, sig: signalled.append((pid, sig)))

    assert process_manager._terminate_process_tree(101) == [202, 203, 101]
    assert signalled == [
        (202, process_manager.signal.SIGTERM),
        (203, process_manager.signal.SIGTERM),
        (101, process_manager.signal.SIGTERM),
    ]


def test_abort_poll_returns_to_glib_while_worker_is_alive():
    class Worker:
        def is_alive(self):
            return True

    # A future start time keeps the poll in its wait branch. It must simply
    # ask GLib to schedule another poll, without join/sleep or UI mutation.
    result = process_manager.ProcessManagerWindow._check_abort_progress(
        object(), SimpleNamespace(status="Aborting..."), Worker(), [101],
        "system-1", 0, 10**12,
    )
    assert result is True
