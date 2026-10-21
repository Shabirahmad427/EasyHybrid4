import pickle

import pytest

from pdynamo.pDynamo2EasyHybrid import project_file


def test_project_file_round_trip_adds_format_version(tmp_path):
    target = tmp_path / "sample.easy"
    project_file.write_project_file(target, {"systems": [{"name": "water"}]})

    restored = project_file.read_project_file(target)
    assert restored["format_version"] == project_file.CURRENT_PROJECT_FORMAT
    assert restored["systems"] == [{"name": "water"}]


def test_project_file_reader_accepts_legacy_unversioned_payload(tmp_path):
    target = tmp_path / "legacy.easy"
    target.write_bytes(pickle.dumps({"systems": [{"name": "legacy"}]}))

    assert project_file.read_project_file(target) == {"systems": [{"name": "legacy"}]}


def test_corrupt_project_is_rejected_without_touching_existing_file(tmp_path):
    target = tmp_path / "project.easy"
    target.write_bytes(b"previous valid project")
    original = target.read_bytes()
    with pytest.raises(pickle.UnpicklingError):
        project_file.read_project_file(target)
    assert target.read_bytes() == original


def test_failed_write_keeps_existing_project_intact(tmp_path, monkeypatch):
    target = tmp_path / "project.easy"
    target.write_bytes(b"previous valid project")
    original = target.read_bytes()

    def fail_dump(*_args, **_kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(project_file.pickle, "dump", fail_dump)
    with pytest.raises(OSError, match="simulated disk failure"):
        project_file.write_project_file(target, {"systems": []})
    assert target.read_bytes() == original
    assert list(tmp_path.glob(".easyhybrid-*.tmp")) == []


def test_project_file_rejects_unknown_future_version(tmp_path):
    target = tmp_path / "future.easy"
    target.write_bytes(pickle.dumps({"format_version": 999, "systems": []}))
    with pytest.raises(ValueError, match="Unsupported EasyHybrid project format"):
        project_file.read_project_file(target)
