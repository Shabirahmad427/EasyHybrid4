"""Regression for child simulation dispatch failures reaching the process UI."""
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


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
    simulation.MSG_RUNNING = "RUNNING"
    simulation.MSG_ERROR = "ERROR"
    simulation.MSG_RESULT = "RESULT"
    simulation.MSG_DONE = "DONE"
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
