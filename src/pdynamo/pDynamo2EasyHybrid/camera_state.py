"""Capture and restore the VisMol camera portion of an EasyHybrid session."""

import numpy as np

from util.debug import dprint


def capture_camera_state(vm_glcore):
    """Return a detached, pickle-friendly snapshot of the current camera."""
    camera = vm_glcore.glcamera
    return {
        "model_mat": np.copy(vm_glcore.model_mat),
        "zero_reference_point": np.copy(vm_glcore.zero_reference_point),
        "dist_cam_zrp": float(vm_glcore.dist_cam_zrp),
        "view_matrix": np.copy(camera.view_matrix),
        "projection_matrix": np.copy(camera.projection_matrix),
        "z_near": float(camera.z_near),
        "z_far": float(camera.z_far),
        "glarea_width": float(vm_glcore.width),
        "glarea_height": float(vm_glcore.height),
    }


def restore_camera_state(camera_data, vm_glcore, vm_widget=None):
    """Restore a saved camera state, accepting older payloads without size.

    Returns whether a camera state was present. The size fields are optional
    for compatibility with sessions written before viewport dimensions were
    included.
    """
    if camera_data is None:
        return False

    camera = vm_glcore.glcamera
    vm_glcore.model_mat = np.copy(camera_data["model_mat"])
    vm_glcore.zero_reference_point = np.copy(camera_data["zero_reference_point"])
    vm_glcore.dist_cam_zrp = camera_data["dist_cam_zrp"]
    camera.set_view_matrix(np.copy(camera_data["view_matrix"]))
    camera.set_projection_matrix(np.copy(camera_data["projection_matrix"]))
    camera.z_near = camera_data["z_near"]
    camera.z_far = camera_data["z_far"]
    camera.update_fog()

    width = camera_data.get("glarea_width")
    height = camera_data.get("glarea_height")
    if width and height:
        if vm_widget is not None:
            try:
                vm_widget.set_size_request(int(width), int(height))
            except Exception as error:
                # GTK containers may reject best-effort size requests; the
                # camera and projection are still restored below.
                dprint("Could not resize GLArea on session load:", error)
        vm_glcore.resize_window(width, height)

    vm_glcore.queue_draw()
    return True
