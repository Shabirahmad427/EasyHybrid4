import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from native_pointer_input import (
    activate_target_with_foreground_input,
    add_window_point_offset,
    adjust_window_point_from_gesture_feedback,
    appkit_to_quartz_point,
    logical_to_device_point,
    retry_until_native_hit_target,
)


@pytest.mark.parametrize(
    ("point", "scale", "expected"),
    [((12.2, 4.6), 1, (12, 5)), ((12.2, 4.6), 2, (24, 9)), ((-1.5, 2.5), 2, (-3, 5))],
)
def test_logical_coordinates_map_to_device_pixels(point, scale, expected):
    assert logical_to_device_point(*point, scale) == expected


def test_logical_to_device_point_rejects_invalid_scale():
    with pytest.raises(ValueError, match="positive"):
        logical_to_device_point(1, 2, 0)


def test_native_click_feedback_corrects_toplevel_client_offset():
    assert adjust_window_point_from_gesture_feedback(
        613.3,
        343.8,
        target_framebuffer_point=(361.3, 209.8),
        observed_framebuffer_point=(347.0, 198.0),
        widget_size=(771, 357),
        framebuffer_size=(771, 357),
    ) == pytest.approx((627.6, 355.6))


def test_native_click_feedback_offset_accumulates_after_calibration():
    base = (613.3, 343.8)
    offset = (0.0, 0.0)
    corrected = adjust_window_point_from_gesture_feedback(
        base[0] + offset[0],
        base[1] + offset[1],
        target_framebuffer_point=(361.3, 209.8),
        observed_framebuffer_point=(347.0, 198.0),
        widget_size=(771, 357),
        framebuffer_size=(771, 357),
    )
    offset = add_window_point_offset(
        offset, (corrected[0] - base[0], corrected[1] - base[1])
    )
    # A second click is already aligned. Its small residual must refine the
    # learned offset instead of resetting the next click to the base point.
    next_corrected = adjust_window_point_from_gesture_feedback(
        base[0] + offset[0],
        base[1] + offset[1],
        target_framebuffer_point=(361.3, 209.8),
        observed_framebuffer_point=(361.0, 210.0),
        widget_size=(771, 357),
        framebuffer_size=(771, 357),
    )
    offset = add_window_point_offset(
        offset,
        (next_corrected[0] - (base[0] + offset[0]),
         next_corrected[1] - (base[1] + offset[1])),
    )
    assert (base[0] + offset[0], base[1] + offset[1]) == pytest.approx(
        next_corrected
    )
    assert offset[0] > 14 and offset[1] > 9


def test_native_click_feedback_accounts_for_hidpi_widget_ratio():
    assert adjust_window_point_from_gesture_feedback(
        100,
        80,
        target_framebuffer_point=(400, 240),
        observed_framebuffer_point=(380, 220),
        widget_size=(400, 240),
        framebuffer_size=(800, 480),
    ) == pytest.approx((110, 90))


def test_native_click_feedback_rejects_invalid_dimensions():
    with pytest.raises(ValueError, match="dimensions"):
        adjust_window_point_from_gesture_feedback(
            10,
            20,
            target_framebuffer_point=(1, 2),
            observed_framebuffer_point=(3, 4),
            widget_size=(0, 20),
            framebuffer_size=(10, 20),
        )


def test_native_windows_hit_target_is_restacked_after_previous_window_covers_it():
    events = []
    hit_results = iter((False, True))

    def prepare_target():
        events.append("raise_target")

    def move_pointer():
        events.append("move_pointer")

    def is_target_under_pointer():
        events.append("hit_test")
        return next(hit_results)

    assert retry_until_native_hit_target(
        prepare_target,
        move_pointer,
        is_target_under_pointer,
    ) == 2
    assert events == [
        "raise_target", "move_pointer", "hit_test",
        "raise_target", "move_pointer", "hit_test",
    ]


def test_native_windows_hit_target_retry_has_a_bounded_failure():
    assert retry_until_native_hit_target(
        lambda: None,
        lambda: None,
        lambda: False,
        attempts=3,
    ) is None
    with pytest.raises(ValueError, match="positive"):
        retry_until_native_hit_target(lambda: None, lambda: None, lambda: True, attempts=0)


def test_win32_activation_temporarily_attaches_foreground_input_queue():
    events = []

    def attach(source, target, attached):
        events.append(("attach" if attached else "detach", source, target))
        return True

    def set_foreground():
        events.append(("foreground",))
        return True

    def bring_to_top():
        events.append(("top",))
        return True

    result = activate_target_with_foreground_input(
        attach, set_foreground, bring_to_top, attach,
        current_thread_id=11, foreground_thread_id=22,
    )
    assert result == {
        "input_queues_attached": True,
        "foreground_activation_result": True,
        "bring_to_top_result": True,
    }
    assert events == [
        ("attach", 11, 22), ("foreground",), ("top",), ("detach", 11, 22),
    ]


def test_appkit_point_maps_to_quartz_on_secondary_display():
    # AppKit uses a bottom-left origin; this display is left and above the
    # primary Quartz display, so both desktop origins must be preserved.
    assert appkit_to_quartz_point(
        100, 250, -1280, 0, 1280, 800, -1280, -800
    ) == (100, -250)


def test_appkit_point_maps_vertical_axis_on_primary_display():
    assert appkit_to_quartz_point(
        400, 600, 0, 0, 1440, 900, 0, 0
    ) == (400, 300)
