"""pDynamo GTK row references must survive project serialization failures."""

import os
import pickle

import pytest


def _session_writer():
    if not os.environ.get("PDYNAMO3_PARAMETERS"):
        pytest.skip("session serialization requires the configured pDynamo3 runtime")
    pytest.importorskip("pCore", reason="pDynamo3 source/runtime is not on PYTHONPATH")

    from pdynamo.pDynamo2EasyHybrid.io_data import LoadAndSaveData

    return object.__new__(LoadAndSaveData)


class System:
    pass


def test_session_pickle_restores_live_tree_rows_when_write_fails(tmp_path, monkeypatch):
    writer = _session_writer()
    system = System()
    system.tree_row = object()
    system.system_choice_row = object()
    rows = (system.tree_row, system.system_choice_row)
    session_data = {"systems": [{"system": system}]}

    def fail_dump(_data, _stream, **_kwargs):
        assert system.tree_row is None
        assert system.system_choice_row is None
        raise OSError("simulated disk-full failure")

    monkeypatch.setattr(pickle, "dump", fail_dump)

    with pytest.raises(OSError, match="simulated disk-full failure"):
        writer._write_session_pickle(str(tmp_path / "session.easy"), session_data)

    assert (system.tree_row, system.system_choice_row) == rows


def test_session_pickle_omits_rows_and_leaves_rowless_systems_unchanged(tmp_path):
    writer = _session_writer()
    with_rows = System()
    with_rows.tree_row = "live tree row"
    with_rows.system_choice_row = "live choice row"
    rowless = System()
    filename = tmp_path / "session.easy"

    writer._write_session_pickle(
        str(filename), {"systems": [{"system": with_rows}, {"system": rowless}]}
    )

    with open(filename, "rb") as session_file:
        saved = pickle.load(session_file)
    saved_with_rows, saved_rowless = (data["system"] for data in saved["systems"])
    assert saved_with_rows.tree_row is None
    assert saved_with_rows.system_choice_row is None
    assert not hasattr(saved_rowless, "tree_row")
    assert not hasattr(saved_rowless, "system_choice_row")
    assert with_rows.tree_row == "live tree row"
    assert with_rows.system_choice_row == "live choice row"
    assert not hasattr(rowless, "tree_row")
