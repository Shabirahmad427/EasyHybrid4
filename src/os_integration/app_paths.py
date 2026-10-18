"""Portable per-user paths for EasyHybrid settings and transient files."""

import os
import sys
from pathlib import Path


APP_DIRECTORY = "EasyHybrid4"


def _absolute_env_path(environ, name):
    value = environ.get(name)
    if value:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
    return None


def user_config_dir(*, platform=None, environ=None, home=None):
    """Return the per-user configuration directory without creating it."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)

    if platform == "win32":
        base = _absolute_env_path(environ, "APPDATA") or home / "AppData" / "Roaming"
    elif platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = _absolute_env_path(environ, "XDG_CONFIG_HOME") or home / ".config"
    return base / APP_DIRECTORY


def user_cache_dir(*, platform=None, environ=None, home=None):
    """Return the per-user cache directory without creating it."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)

    if platform == "win32":
        base = _absolute_env_path(environ, "LOCALAPPDATA") or home / "AppData" / "Local"
    elif platform == "darwin":
        base = home / "Library" / "Caches"
    else:
        base = _absolute_env_path(environ, "XDG_CACHE_HOME") or home / ".cache"
    return base / APP_DIRECTORY


def ensure_user_directories(*, platform=None, environ=None, home=None):
    """Create and return the application's config and cache directories."""
    config_dir = user_config_dir(platform=platform, environ=environ, home=home)
    cache_dir = user_cache_dir(platform=platform, environ=environ, home=home)
    config_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return config_dir, cache_dir


def config_file_candidates(legacy_home=None, *, platform=None, environ=None, home=None):
    """Return the active settings file followed by the legacy source-tree file."""
    active = user_config_dir(platform=platform, environ=environ, home=home) / "config.json"
    candidates = [active]
    if legacy_home is not None:
        legacy = Path(legacy_home) / ".config.json"
        if legacy != active:
            candidates.append(legacy)
    return tuple(candidates)
