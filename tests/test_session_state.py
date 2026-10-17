"""Regression tests for GTK-independent EasyHybrid session state."""

import os
import subprocess
import sys
from pathlib import Path


def test_session_state_lifecycle_does_not_import_gtk():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source_path = str(repo_root / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, env.get("PYTHONPATH")))
    )
    code = """
import importlib.abc
import sys

class RejectGtkImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'gi' or fullname.startswith('gi.'):
            raise AssertionError('session state imported GTK')

sys.meta_path.insert(0, RejectGtkImports())
from pdynamo.pDynamo2EasyHybrid.state import SessionState

first = SessionState(random_code='session-a')
second = SessionState(random_code='session-b')
assert 'gi' not in sys.modules
assert first.systems == {0: None}
assert first.get_system() is None

first.systems[1] = {'name': 'water'}
first.set_active(1)
assert first.get_system() == {'name': 'water'}
assert second.systems == {0: None}

first.changed = True
first.autosave_change_counter = 3
first.process_pool[1] = 'worker'
first.reset_systems()
assert first.systems == {0: None}
assert first.active_id == 0
assert first.psystem_name_list == []
assert first.psystem_name_counter == 1
assert first.counter == 0
assert first.color_palette_counter == 0
# Match the legacy pDynamoSession.restart() contract: restart only clears
# the loaded-system catalog and preserves session/job metadata.
assert first.changed is True
assert first.autosave_change_counter == 3
assert first.process_pool == {1: 'worker'}
assert first.random_code == 'session-a'
"""

    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)
