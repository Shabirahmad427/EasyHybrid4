"""pDynamo GTK row references must survive project serialization failures."""

import os
import pickle

import pytest


def test_session_pickle_restores_live_tree_rows_when_write_fails(tmp_path, monkeypatch):
    if not os.environ.get("PDYNAMO3_PARAMETERS"):
        pytest.skip("session serialization requires the configured pDynamo3 runtime")
    pytest.importorskip("pCore", reason="pDynamo3 source/runtime is not on PYTHONPATH")

    from pdynamo.pDynamo2EasyHybrid.io_data import LoadAndSaveData

    class System:
        pass

    system = System()
    system.tree_row = object()
    system.system_choice_row = object()
    rows = (system.tree_row, system.system_choice_row)
    session_data = {"systems": [{"system": system}]}

    def fail_dump(_data, _stream):
        assert system.tree_row is None
        assert system.system_choice_row is None
        raise OSError("simulated disk-full failure")

    monkeypatch.setattr(pickle, "dump", fail_dump)
    writer = object.__new__(LoadAndSaveData)

    with pytest.raises(OSError, match="simulated disk-full failure"):
        writer._write_session_pickle(str(tmp_path / "session.easy"), session_data)

    assert (system.tree_row, system.system_choice_row) == rows
