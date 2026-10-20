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


def test_macos_gtk424_full_app_smoke_enables_hang_stack_diagnostics():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    smoke = (ROOT / "tests" / "test_easyhybrid_full_app_smoke.py").read_text()

    assert "EASYHYBRID_FULL_APP_TRACE: ${{ runner.os == 'macOS' && matrix.gtk == '4.24'" in workflow
    assert 'faulthandler.dump_traceback_later(20, repeat=True)' in smoke
