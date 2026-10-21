"""Regression coverage for the camera state stored in .easy sessions."""

from types import SimpleNamespace

import numpy as np
import pytest

def test_camera_state_round_trips_through_easy_session_file(tmp_path):
    import os

    if not os.environ.get("PDYNAMO3_PARAMETERS"):
        pytest.skip("camera session persistence requires the configured pDynamo3 runtime")
    pytest.importorskip("pCore", reason="pDynamo3 source/runtime is not on PYTHONPATH")
    from pdynamo.pDynamo2EasyHybrid.io_data import LoadAndSaveData

    class FakeCamera:
        def __init__(self):
            self.view_matrix = np.eye(4, dtype=np.float32) * 2
            self.projection_matrix = np.eye(4, dtype=np.float32) * 3
            self.z_near = 0.25
            self.z_far = 750.0

        def set_view_matrix(self, matrix):
            self.view_matrix = matrix

        def set_projection_matrix(self, matrix):
            self.projection_matrix = matrix

        def update_fog(self):
            self.fog_updated = True

    camera = FakeCamera()
    original_core = SimpleNamespace(
        model_mat=np.arange(16, dtype=np.float32).reshape(4, 4),
        zero_reference_point=np.array([1.5, -2.0, 3.5], dtype=np.float32),
        dist_cam_zrp=12.25,
        glcamera=camera,
        width=960,
        height=540,
        resize_calls=[],
        queue_draw=lambda: None,
    )
    original_core.resize_window = lambda width, height: original_core.resize_calls.append(
        (width, height)
    )
    original_vm_session = SimpleNamespace(
        vm_glcore=original_core,
        vm_objects_dic={},
        vm_widget=SimpleNamespace(set_size_request=lambda width, height: None),
    )
    save_io = object.__new__(LoadAndSaveData)
    save_io.main = SimpleNamespace(
        bottom_notebook=SimpleNamespace(
            get_active_system_text_from_textbuffer=lambda: None
        ),
        session_filename=None,
    )
    save_io.vm_session = original_vm_session
    save_io.psystem = {}

    filename = tmp_path / "camera-state.easy"
    save_io.save_easyhybrid_session(str(filename), tmp=True)

    restored_camera = FakeCamera()
    restored_core = SimpleNamespace(
        model_mat=np.zeros((4, 4), dtype=np.float32),
        zero_reference_point=np.zeros(3, dtype=np.float32),
        dist_cam_zrp=0.0,
        glcamera=restored_camera,
        resize_calls=[],
        queue_draw=lambda: None,
    )
    restored_core.resize_window = lambda width, height: restored_core.resize_calls.append(
        (width, height)
    )
    size_requests = []
    restored_vm_session = SimpleNamespace(
        vm_glcore=restored_core,
        vm_widget=SimpleNamespace(
            set_size_request=lambda width, height: size_requests.append((width, height))
        ),
    )
    load_io = object.__new__(LoadAndSaveData)
    load_io.main = SimpleNamespace(
        restart=lambda: None,
        bottom_notebook=SimpleNamespace(status_teeview_add_new_item=lambda **_kwargs: None),
        process_manager_window=SimpleNamespace(
            build_liststore_from_job_history=lambda **_kwargs: None
        ),
        session_filename=None,
    )
    load_io.vm_session = restored_vm_session

    load_io.load_easyhybrid_serialization_file(str(filename) + "~", tmp=True)

    np.testing.assert_array_equal(restored_core.model_mat, original_core.model_mat)
    np.testing.assert_array_equal(
        restored_core.zero_reference_point, original_core.zero_reference_point
    )
    assert restored_core.dist_cam_zrp == original_core.dist_cam_zrp
    np.testing.assert_array_equal(
        restored_camera.view_matrix, camera.view_matrix
    )
    np.testing.assert_array_equal(
        restored_camera.projection_matrix, camera.projection_matrix
    )
    assert (restored_camera.z_near, restored_camera.z_far) == (0.25, 750.0)
    assert restored_camera.fog_updated is True
    assert size_requests == [(960, 540)]
    assert restored_core.resize_calls == [(960.0, 540.0)]
    assert load_io.main.session_filename == str(filename)
