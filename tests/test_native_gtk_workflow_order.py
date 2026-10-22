"""Guard GTK CI ordering against macOS shader compiler contention."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_full_application_smoke_runs_before_component_shader_cycles():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    full_app = "- name: Run the full EasyHybrid application with pDynamo3"
    component = "- name: Run 5 EasyHybrid molecular scene pick and close cycles"

    full_app_positions = [index for index in range(len(workflow)) if workflow.startswith(full_app, index)]
    component_positions = [index for index in range(len(workflow)) if workflow.startswith(component, index)]

    assert len(full_app_positions) == len(component_positions) == 4
    assert all(full < scene for full, scene in zip(full_app_positions, component_positions))


def test_failed_macos_gtk424_cell_can_be_dispatched_alone():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()

    assert "- macos-gtk424" in workflow
    assert "inputs.scope == 'macos-diagnostic' || inputs.scope == 'macos-gtk424') && '[\"macos-arm64\"]'" in workflow
    assert "inputs.scope == 'macos-gtk424' && '[\"4.24\"]'" in workflow
    assert workflow.count("inputs.scope != 'macos-gtk424'") == 3


def test_failed_linux_gtk48_cell_can_be_dispatched_alone():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()

    assert "- linux-gtk48" in workflow
    assert "inputs.scope == 'linux-gtk48' && '[\"linux-x86_64\"]'" in workflow
    assert "inputs.scope == 'linux-gtk48' && '[\"4.8\"]'" in workflow
    assert workflow.count("inputs.scope != 'linux-gtk48'") == 3


def test_full_app_timeout_reports_gtk_scene_progress():
    smoke = (ROOT / "tests" / "test_easyhybrid_full_app_smoke.py").read_text()

    assert 'state["phase"] = "waiting_for_scene_render"' in smoke
    assert 'core_renders=%s scene_draws=%s active=%s picking=%s' in smoke
    assert 'widget.get_realized(), widget.get_mapped()' in smoke
    assert 'state["phase"] = "waiting_for_gl_area_allocation"' in smoke
    assert 'state["pick_dimensions"] = (' in smoke
    assert 'pick_attempts=%s' in smoke
    assert 'state["pick_attempts"] = state.get("pick_attempts", 0) + 1' in smoke


def test_full_app_matrix_injects_native_pointer_on_all_desktop_oses():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    smoke = (ROOT / "tests" / "test_easyhybrid_full_app_smoke.py").read_text()
    pointer = (ROOT / "tests" / "native_pointer_input.py").read_text()

    assert workflow.count('EASYHYBRID_FULL_APP_NATIVE_POINTER: "1"') == 4
    assert workflow.count("pyobjc-framework-Cocoa pyobjc-framework-Quartz") == 2
    assert '"linux": "linux-x11-xtest"' in smoke
    assert '"win32": "windows-win32-user32"' in smoke
    assert '"darwin": "macos-quartz-hid"' in smoke
    assert 'return _click_linux_x11(window, x, y)' in pointer
    assert 'return _click_windows(window, x, y)' in pointer
    assert 'return _click_macos(window, x, y)' in pointer
