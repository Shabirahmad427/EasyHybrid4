"""Regression coverage for display-independent startup OS integration."""

import json

from src.os_integration.gtk_startup import (
    configure_vblank_mode,
    configure_gl_context_environment,
)


def test_saved_vblank_preference_overrides_platform_default(tmp_path):
    config_path = tmp_path / ".config.json"
    config_path.write_text(json.dumps({"vblank_mode": "on"}), encoding="utf-8")
    environment = {}

    configure_vblank_mode(
        config_path=config_path,
        platform="darwin",
        environ=environment,
    )

    assert environment == {"vblank_mode": "1"}


def test_explicit_environment_preference_is_preserved(tmp_path):
    environment = {"vblank_mode": "custom"}

    configure_vblank_mode(
        config_path=tmp_path / "missing.json",
        platform="linux",
        environ=environment,
        vendor_paths=[],
    )

    assert environment == {"vblank_mode": "custom"}


def test_automatic_driver_detection_is_limited_to_linux(tmp_path):
    environment = {}
    vendor_path = tmp_path / "card0" / "device" / "vendor"
    vendor_path.parent.mkdir(parents=True)
    vendor_path.write_text("0x8086", encoding="ascii")

    configure_vblank_mode(
        config_path=tmp_path / "missing.json",
        platform="win32",
        environ=environment,
        vendor_paths=[str(vendor_path)],
    )

    assert environment == {}


def test_linux_intel_default_can_be_overridden_by_saved_preference(tmp_path):
    environment = {}
    vendor_path = tmp_path / "card0" / "device" / "vendor"
    vendor_path.parent.mkdir(parents=True)
    vendor_path.write_text("0x8086", encoding="ascii")

    configure_vblank_mode(
        config_path=tmp_path / "missing.json",
        platform="linux",
        environ=environment,
        vendor_paths=[str(vendor_path)],
    )

    assert environment == {"vblank_mode": "0"}


def test_unknown_saved_preference_falls_back_to_automatic_detection(tmp_path):
    config_path = tmp_path / ".config.json"
    config_path.write_text(json.dumps({"vblank_mode": "unknown"}), encoding="utf-8")
    environment = {}
    vendor_path = tmp_path / "card0" / "device" / "vendor"
    vendor_path.parent.mkdir(parents=True)
    vendor_path.write_text("0x8086", encoding="ascii")

    configure_vblank_mode(
        config_path=config_path,
        platform="linux",
        environ=environment,
        vendor_paths=[str(vendor_path)],
    )

    assert environment == {"vblank_mode": "0"}


def test_linux_gtk_gl_environment_aligns_egl_and_desktop_gl():
    environment = {"DISPLAY": ":99", "GDK_DEBUG": "portals"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=(4, 14),
    )

    assert environment["GDK_DEBUG"] == "portals:gl-prefer-gl"
    assert environment["PYOPENGL_PLATFORM"] == "egl"


def test_gtk48_keeps_its_desktop_gl_default_but_selects_egl_on_linux():
    environment = {"DISPLAY": ":99"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=(4, 8),
    )

    assert environment == {"DISPLAY": ":99", "PYOPENGL_PLATFORM": "egl"}


def test_wayland_uses_egl_and_newer_gtk_prefers_desktop_gl():
    environment = {"WAYLAND_DISPLAY": "wayland-0"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=(4, 24),
    )

    assert environment["PYOPENGL_PLATFORM"] == "egl"
    assert environment["GDK_DEBUG"] == "gl-prefer-gl"


def test_native_windows_and_macos_keep_pyopengl_platform_autodetection():
    windows_environment = {}
    macos_environment = {}

    configure_gl_context_environment(
        platform="win32", environ=windows_environment, runtime_version=(4, 24)
    )
    configure_gl_context_environment(
        platform="darwin", environ=macos_environment, runtime_version=(4, 24)
    )

    assert windows_environment == {"GDK_DEBUG": "gl-prefer-gl"}
    assert macos_environment == {"GDK_DEBUG": "gl-prefer-gl"}


def test_user_selected_opengl_platform_is_preserved():
    environment = {"DISPLAY": ":99", "PYOPENGL_PLATFORM": "glx"}

    configure_gl_context_environment(
        platform="linux", environ=environment, runtime_version=(4, 24)
    )

    assert environment["PYOPENGL_PLATFORM"] == "glx"
