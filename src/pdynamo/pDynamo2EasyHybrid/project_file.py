"""Safe file-level operations for EasyHybrid ``.easy`` session pickles.

The payload remains a pickle for compatibility with existing project files.
Writes are atomic; readers accept the legacy unversioned payload as version 0.
"""
import os
import pickle
import tempfile


CURRENT_PROJECT_FORMAT = 1


def write_project_file(filename, payload):
    """Atomically replace *filename* with a versioned project payload."""
    if not isinstance(payload, dict) or not isinstance(payload.get("systems"), list):
        raise ValueError("EasyHybrid project payload must contain a systems list")
    payload = dict(payload)
    payload["format_version"] = CURRENT_PROJECT_FORMAT
    path = os.path.abspath(os.fspath(filename))
    parent = os.path.dirname(path) or "."
    fd, temporary = tempfile.mkstemp(prefix=".easyhybrid-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            pickle.dump(payload, stream, protocol=pickle.HIGHEST_PROTOCOL)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def read_project_file(filename):
    """Read a project without changing application state and validate its format."""
    with open(filename, "rb") as stream:
        payload = pickle.load(stream)
    if not isinstance(payload, dict) or not isinstance(payload.get("systems"), list):
        raise ValueError("File is not a valid EasyHybrid project (missing systems list)")
    version = payload.get("format_version", 0)
    if not isinstance(version, int) or version < 0 or version > CURRENT_PROJECT_FORMAT:
        raise ValueError(f"Unsupported EasyHybrid project format version: {version!r}")
    return payload
