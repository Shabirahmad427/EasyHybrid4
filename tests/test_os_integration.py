"""Regression coverage for display-independent startup OS integration."""

import json
import pytest

from src.os_integration.gtk_startup import (
    configure_vblank_mode,
    configure_gl_context_environment,
)
from src.os_integration.app_paths import (
    config_file_candidates,
    ensure_user_directories,
    user_cache_dir,
    user_config_dir,
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


def test_malformed_gpu_vendor_path_is_ignored(tmp_path):
    environment = {}

    configure_vblank_mode(
        config_path=tmp_path / "missing.json",
        platform="linux",
        environ=environment,
        vendor_paths=["vendor"],
    )

    assert environment == {}


def test_linux_x11_gtk_gl_environment_aligns_glx_and_desktop_gl():
    environment = {"DISPLAY": ":99", "GDK_DEBUG": "portals"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=(4, 14),
    )

    assert environment["GDK_DEBUG"] == "portals:gl-prefer-gl:gl-glx"
    assert environment["PYOPENGL_PLATFORM"] == "glx"


def test_gtk48_uses_the_default_desktop_gl_backend_on_linux_x11():
    environment = {"DISPLAY": ":99"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=(4, 8),
    )

    assert environment == {
        "DISPLAY": ":99",
        "PYOPENGL_PLATFORM": "glx",
        "GDK_DEBUG": "gl-glx",
    }


@pytest.mark.parametrize("runtime_version", [(4, 16), (4, 18)])
def test_gtk416_and_418_use_egl_on_linux_x11(runtime_version):
    environment = {"DISPLAY": ":99"}

    configure_gl_context_environment(
        platform="linux",
        environ=environment,
        runtime_version=runtime_version,
    )

    assert environment["PYOPENGL_PLATFORM"] == "egl"
    assert "gl-glx" not in environment.get("GDK_DEBUG", "").split(":")


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
    assert environment["GDK_DEBUG"] == "gl-prefer-gl"


def test_gtk424_x11_pins_glx_with_gdk_disable_instead_of_removed_debug_flag():
    # GTK 4.24.1 reports 'Unrecognized value "gl-glx"' for GDK_DEBUG and
    # otherwise chooses EGL or GLX depending on the X11 system.
    environment = {"DISPLAY": ":99", "GDK_DISABLE": "vulkan"}

    configure_gl_context_environment(
        platform="linux", environ=environment, runtime_version=(4, 24)
    )

    assert environment["PYOPENGL_PLATFORM"] == "glx"
    assert environment["GDK_DISABLE"] == "vulkan:egl"
    assert "gl-glx" not in environment.get("GDK_DEBUG", "").split(":")


def test_gtk424_x11_keeps_user_selected_egl_enabled():
    environment = {"DISPLAY": ":99", "PYOPENGL_PLATFORM": "egl"}

    configure_gl_context_environment(
        platform="linux", environ=environment, runtime_version=(4, 24)
    )

    assert environment["PYOPENGL_PLATFORM"] == "egl"
    assert "GDK_DISABLE" not in environment


def test_user_selected_egl_platform_does_not_force_gdk_glx():
    environment = {"DISPLAY": ":99", "PYOPENGL_PLATFORM": "egl"}

    configure_gl_context_environment(
        platform="linux", environ=environment, runtime_version=(4, 24)
    )

    assert environment["PYOPENGL_PLATFORM"] == "egl"
    assert environment["GDK_DEBUG"] == "gl-prefer-gl"

def test_user_paths_follow_platform_conventions_and_unicode(tmp_path):
    home = tmp_path / "Usuário Ω"
    linux_env = {"XDG_CONFIG_HOME": str(tmp_path / "configé"),
                 "XDG_CACHE_HOME": str(tmp_path / "cacheé")}
    assert user_config_dir(platform="linux", environ=linux_env, home=home) == (
        tmp_path / "configé" / "EasyHybrid4"
    )
    assert user_cache_dir(platform="linux", environ=linux_env, home=home) == (
        tmp_path / "cacheé" / "EasyHybrid4"
    )
    assert user_config_dir(
        platform="win32", environ={"APPDATA": str(tmp_path / "Roaming")}, home=home
    ) == tmp_path / "Roaming" / "EasyHybrid4"
    assert user_cache_dir(
        platform="win32", environ={"LOCALAPPDATA": str(tmp_path / "Local")}, home=home
    ) == tmp_path / "Local" / "EasyHybrid4"
    assert user_config_dir(platform="darwin", environ={}, home=home) == (
        home / "Library" / "Application Support" / "EasyHybrid4"
    )

    config_dir, cache_dir = ensure_user_directories(
        platform="linux", environ=linux_env, home=home
    )
    (config_dir / "config.json").write_text('{"startup_path": "Moléculas"}', encoding="utf-8")
    assert (config_dir / "config.json").read_text(encoding="utf-8") == (
        '{"startup_path": "Moléculas"}'
    )
    assert config_dir.is_dir() and cache_dir.is_dir()


def test_config_path_candidates_keep_legacy_settings_readable(tmp_path):
    legacy_home = tmp_path / "installed app"
    candidates = config_file_candidates(
        legacy_home,
        platform="linux",
        environ={"XDG_CONFIG_HOME": str(tmp_path / "user config")},
        home=tmp_path / "home",
    )

    assert candidates == (
        tmp_path / "user config" / "EasyHybrid4" / "config.json",
        legacy_home / ".config.json",
    )


def test_legacy_preferences_migrate_without_modifying_source_tree(tmp_path, monkeypatch):
    import json
    from gui.config import VismolConfig
    from src.os_integration.app_paths import user_cache_dir, user_config_dir

    legacy_home = tmp_path / "readonly-install"
    legacy_home.mkdir()
    legacy_file = legacy_home / ".config.json"
    legacy_file.write_text(
        json.dumps({"startup_path": "Moléculas", "vblank_mode": "off"}),
        encoding="utf-8",
    )
    profile = tmp_path / "user profile"
    monkeypatch.setenv("HOME", str(profile))
    monkeypatch.setenv("USERPROFILE", str(profile))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "user config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "user cache"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming config"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local cache"))

    config = VismolConfig(home=str(legacy_home))

    migrated = user_config_dir() / "config.json"
    saved = json.loads(migrated.read_text(encoding="utf-8"))
    assert saved["startup_path"] == "Moléculas"
    assert saved["vblank_mode"] == "off"
    assert config.easyhybrid_tmp == str(user_cache_dir())
    assert legacy_file.exists()
