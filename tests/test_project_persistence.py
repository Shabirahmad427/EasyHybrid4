"""Project format compatibility and corruption guard regressions."""
import os
import pickle
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


pytestmark = pytest.mark.skipif(
    not os.environ.get("PDYNAMO3_HOME"),
    reason="requires the pDynamo3 runtime used by project persistence",
)


def _project_io():
    pytest.importorskip("pBabel")
    from pdynamo.pDynamo2EasyHybrid.io_data import (
        PROJECT_FORMAT_VERSION,
        _read_project_payload,
    )

    return PROJECT_FORMAT_VERSION, _read_project_payload


def test_project_payload_round_trip_and_legacy_version(tmp_path):
    version, read_payload = _project_io()
    current = {"format_version": version, "systems": []}
    path = tmp_path / "current.easy"
    path.write_bytes(pickle.dumps(current))
    assert read_payload(path) == current

    # Projects from before the explicit version key are treated as v0.
    legacy = {"systems": []}
    path.write_bytes(pickle.dumps(legacy))
    assert read_payload(path) == legacy


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"format_version": 999, "systems": []},
        {"format_version": "1", "systems": []},
        {"systems": {}},
        {"systems": [{"system": object(), "vobjects": None}]},
    ],
)
def test_invalid_project_payload_is_rejected(tmp_path, payload):
    _, read_payload = _project_io()
    path = tmp_path / "invalid.easy"
    path.write_bytes(pickle.dumps(payload))
    with pytest.raises(ValueError):
        read_payload(path)


def test_truncated_project_pickle_raises_without_returning_payload(tmp_path):
    _, read_payload = _project_io()
    path = tmp_path / "truncated.easy"
    path.write_bytes(b"\x80\x04broken")
    with pytest.raises((pickle.UnpicklingError, EOFError, ValueError)):
        read_payload(path)
