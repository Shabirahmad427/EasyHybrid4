import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from native_pointer_input import appkit_to_quartz_point, logical_to_device_point


@pytest.mark.parametrize(
    ("point", "scale", "expected"),
    [((12.2, 4.6), 1, (12, 5)), ((12.2, 4.6), 2, (24, 9)), ((-1.5, 2.5), 2, (-3, 5))],
)
def test_logical_coordinates_map_to_device_pixels(point, scale, expected):
    assert logical_to_device_point(*point, scale) == expected


def test_logical_to_device_point_rejects_invalid_scale():
    with pytest.raises(ValueError, match="positive"):
        logical_to_device_point(1, 2, 0)


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
