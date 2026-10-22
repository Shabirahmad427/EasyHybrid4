"""Camera state round-trip coverage for EasyHybrid session files."""

import pickle
from types import SimpleNamespace

import numpy as np

from pdynamo.pDynamo2EasyHybrid.camera_state import (
    capture_camera_state,
    restore_camera_state,
)


class _Camera:
    def __init__(self, seed):
        self.view_matrix = np.eye(4, dtype=np.float32) * seed
        self.projection_matrix = np.eye(4, dtype=np.float32) * (seed + 1)
        self.z_near = 0.1 * seed
        self.z_far = 100.0 * seed
        self.fog_updates = 0

    def set_view_matrix(self, value):
        self.view_matrix = value

    def set_projection_matrix(self, value):
        self.projection_matrix = value

    def update_fog(self):
        self.fog_updates += 1


class _GLCore:
    def __init__(self, seed):
        self.glcamera = _Camera(seed)
        self.model_mat = np.eye(4, dtype=np.float32) * (seed + 2)
        self.zero_reference_point = np.array([seed, seed + 1, seed + 2], dtype=np.float32)
        self.dist_cam_zrp = float(seed + 3)
        self.width = 800
        self.height = 600
        self.resize_calls = []
        self.draw_requests = 0

    def resize_window(self, width, height):
        self.resize_calls.append((width, height))

    def queue_draw(self):
        self.draw_requests += 1


def test_camera_state_pickle_round_trip_restores_viewport_and_matrices():
    saved_core = _GLCore(2)
    state = pickle.loads(pickle.dumps(capture_camera_state(saved_core)))
    loaded_core = _GLCore(9)
    widget = SimpleNamespace(size_request=None)
    widget.set_size_request = lambda width, height: setattr(
        widget, "size_request", (width, height)
    )

    assert restore_camera_state(state, loaded_core, widget) is True

    np.testing.assert_array_equal(loaded_core.model_mat, saved_core.model_mat)
    np.testing.assert_array_equal(
        loaded_core.zero_reference_point, saved_core.zero_reference_point
    )
    np.testing.assert_array_equal(
        loaded_core.glcamera.view_matrix, saved_core.glcamera.view_matrix
    )
    np.testing.assert_array_equal(
        loaded_core.glcamera.projection_matrix,
        saved_core.glcamera.projection_matrix,
    )
    assert loaded_core.dist_cam_zrp == saved_core.dist_cam_zrp
    assert loaded_core.glcamera.z_near == saved_core.glcamera.z_near
    assert loaded_core.glcamera.z_far == saved_core.glcamera.z_far
    assert loaded_core.glcamera.fog_updates == 1
    assert loaded_core.resize_calls == [(800.0, 600.0)]
    assert widget.size_request == (800, 600)
    assert loaded_core.draw_requests == 1


def test_camera_restore_accepts_legacy_payload_without_viewport_dimensions():
    saved_core = _GLCore(3)
    state = capture_camera_state(saved_core)
    state.pop("glarea_width")
    state.pop("glarea_height")
    loaded_core = _GLCore(8)

    assert restore_camera_state(state, loaded_core) is True

    np.testing.assert_array_equal(loaded_core.model_mat, saved_core.model_mat)
    np.testing.assert_array_equal(
        loaded_core.glcamera.view_matrix, saved_core.glcamera.view_matrix
    )
    assert loaded_core.resize_calls == []
    assert loaded_core.draw_requests == 1


def test_restore_without_camera_state_leaves_current_view_untouched():
    gl_core = _GLCore(4)
    original_view = gl_core.glcamera.view_matrix.copy()

    assert restore_camera_state(None, gl_core) is False

    np.testing.assert_array_equal(gl_core.glcamera.view_matrix, original_view)
    assert gl_core.draw_requests == 0


def test_camera_restore_continues_if_widget_rejects_size_request():
    saved_core = _GLCore(5)
    state = capture_camera_state(saved_core)
    loaded_core = _GLCore(7)

    class _RejectingWidget:
        def set_size_request(self, _width, _height):
            raise RuntimeError("widget is already attached to a constrained layout")

    assert restore_camera_state(state, loaded_core, _RejectingWidget()) is True

    np.testing.assert_array_equal(loaded_core.model_mat, saved_core.model_mat)
    np.testing.assert_array_equal(
        loaded_core.glcamera.view_matrix, saved_core.glcamera.view_matrix
    )
    assert loaded_core.resize_calls == [(800.0, 600.0)]
    assert loaded_core.draw_requests == 1
