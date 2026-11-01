"""Regression for child simulation dispatch failures reaching the process UI."""
import os
import sys
import multiprocessing
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class _UnpickleableRow:
    def __reduce__(self):
        raise TypeError("GUI model rows cannot be pickled")


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires pDynamo3 imports used by the simulation process manager",
)
def test_unknown_simulation_type_emits_error_instead_of_staying_running():
    pytest.importorskip("pBabel")
    from pdynamo.pDynamo2EasyHybrid.simulations_mixin import pSimulations

    class Queue:
        def __init__(self):
            self.messages = []

        def put(self, message):
            self.messages.append(message)

    class System:
        e_id = "test-system"
        e_step_counter = 3

    queue = Queue()
    simulation = pSimulations()
    simulation._target_process(
        {
            "queue": queue,
            "simulation_type": "not-a-real-simulation",
            "system": System(),
            "logfile": "test.log",
        }
    )

    assert queue.messages[0] == "RUNNING"
    assert queue.messages[1][0] == "ERROR"
    error = queue.messages[1][1]
    assert error["error"] == "ValueError: Unknown simulation type: not-a-real-simulation"
    assert error["e_id"] == "test-system"
    assert not any(message == "DONE" for message in queue.messages)


@pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires pDynamo3 imports used by the simulation process manager",
)
def test_spawn_worker_serializes_without_gui_rows_and_restores_them():
    pytest.importorskip("pBabel")
    from pdynamo.pDynamo2EasyHybrid.simulations_mixin import (
        _start_process_without_gui_rows,
        pSimulations,
    )

    system = SimpleNamespace(
        e_id="test-system",
        e_step_counter=3,
        tree_row=_UnpickleableRow(),
        system_choice_row=_UnpickleableRow(),
    )
    rows = system.tree_row, system.system_choice_row
    queue = multiprocessing.get_context("spawn").Queue()
    parameters = {
        "system": system,
        "queue": queue,
        "simulation_type": "not-a-real-simulation",
        "logfile": "test.log",
    }
    process = multiprocessing.get_context("spawn").Process(
        target=pSimulations._target_process, args=(parameters,)
    )

    # Exercise the real spawn pickling path, not just a serialization mock.
    _start_process_without_gui_rows(process, system)

    assert (system.tree_row, system.system_choice_row) == rows
    messages = [queue.get(timeout=30), queue.get(timeout=30)]
    process.join(timeout=30)
    if process.is_alive():
        process.terminate()
        process.join()
        pytest.fail("spawned simulation worker did not exit")
    assert process.exitcode == 0
    assert messages[0] == "RUNNING"
    assert messages[1][0] == "ERROR"
    assert messages[1][1]["e_id"] == "test-system"
    queue.close()
