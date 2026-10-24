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


def test_graphics_extensions_build_before_widget_patterns_import_vismol():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    build = "- name: Build graphics engine extensions"
    widget_tests = "- name: Run GTK4 widget-pattern tests"

    build_positions = [index for index in range(len(workflow)) if workflow.startswith(build, index)]
    widget_positions = [index for index in range(len(workflow)) if workflow.startswith(widget_tests, index)]

    assert len(build_positions) == len(widget_positions) == 4
    assert all(compiled < tests for compiled, tests in zip(build_positions, widget_positions))


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


def test_failed_windows_gtk420_cell_can_be_dispatched_alone():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()

    assert "- windows-gtk420" in workflow
    assert "inputs.scope == 'windows-gtk420') && '[\"windows-x86_64\"]'" in workflow
    assert "inputs.scope == 'windows-gtk420' && '[\"4.20\"]'" in workflow
    assert workflow.count("inputs.scope == 'windows-gtk420'") == 3
    assert workflow.count("inputs.scope != 'windows-gtk420'") == 3


def test_full_app_timeout_reports_gtk_scene_progress():
    smoke = (ROOT / "tests" / "test_easyhybrid_full_app_smoke.py").read_text()

    assert 'state["phase"] = "waiting_for_scene_render"' in smoke
    assert 'core_renders=%s scene_draws=%s active=%s picking=%s' in smoke
    assert 'widget.get_realized(), widget.get_mapped()' in smoke
    assert 'state["phase"] = "waiting_for_gl_area_allocation"' in smoke
    assert 'state["pick_dimensions"] = (' in smoke
    assert 'pick_attempts=%s' in smoke
    assert 'state["pick_attempts"] = state.get("pick_attempts", 0) + 1' in smoke


def test_native_matrix_lists_every_supported_gtk_minor_and_records_runtime():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    supported_minors = ("4.8", "4.10", "4.12", "4.14", "4.16", "4.18", "4.20", "4.22", "4.24")

    matrix_line = next(line for line in workflow.splitlines() if line.lstrip().startswith("gtk:"))
    for minor in supported_minors:
        assert f'"{minor}"' in matrix_line

    # GTK 4.16/4.18 lack conda-forge packages and must remain covered by
    # native distro/source builds, including Windows and Apple Silicon.
    assert 'gtk: "4.16"' in workflow
    assert 'gtk: "4.18"' in workflow
    assert "gtk-windows-msys2:" in workflow
    assert "gtk-macos-source:" in workflow

    # Every provider must record the loaded runtime before its smoke/tests.
    assert workflow.count(".github/scripts/record_runtime.py") >= 4
    assert "Record actual runtime and host" in workflow
    assert "record_runtime.py conda-forge" in workflow
    assert "record_runtime.py 'msys2-source-${{ matrix.version }}'" in workflow
    assert "record_runtime.py 'source-${{ matrix.version }}'" in workflow


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
    assert 'if foreground != hwnd' not in pointer
    assert 'win32_hit_belongs_to_target(' in pointer
    assert 'root_owner=lambda candidate: user32.GetAncestor(candidate, 3)' in pointer
    assert 'topmost = ctypes.c_void_p(-1)  # HWND_TOPMOST' in pointer
    assert 'user32.SetWindowPos(hwnd, not_topmost' in pointer
    assert 'confirmed_attempt = retry_until_native_hit_target(' in pointer
    assert '"hit": hit_description' in pointer
    assert '"class": class_buffer.value' in pointer
    assert 'minimize_hosted_runner_console_blocker(' in pointer
    assert '"hosted_runner_console_minimized": console_minimized' in pointer
    assert pointer.index('user32.SetForegroundWindow(hwnd)', pointer.index('def prepare_target')) < pointer.index(
        'user32.SetWindowPos(hwnd, topmost', pointer.index('def prepare_target')
    )


def test_every_provider_runs_pdynamo_scientific_tests_without_a_display():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    runner = (ROOT / ".github" / "scripts" / "run_scientific_tests.py").read_text()

    # One step per provider job (conda, Linux distro, MSYS2, macOS source),
    # each after its pDynamo3 build and before the full-app step.
    assert workflow.count(".github/scripts/run_scientific_tests.py") == 4
    for job in ("gtk-runtime:", "gtk-linux-distro:", "gtk-windows-msys2:", "gtk-macos-source:"):
        start = workflow.index(job)
        build = workflow.index("- name: Build pDynamo3", start)
        science = workflow.index("run_scientific_tests.py", start)
        full_app = workflow.index("- name: Run the full EasyHybrid application", start)
        assert build < science < full_app
    assert 'for name in ("DISPLAY", "WAYLAND_DISPLAY")' in runner
    assert '"skipped" in summary' in runner


def test_main_push_skips_matrix_only_for_tested_merges_or_markdown():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()

    assert "  plan:\n" in workflow
    assert "git diff --quiet HEAD^2 HEAD" in workflow
    assert "git diff --name-only HEAD^ HEAD | grep -qv '\\.md$'" in workflow
    assert 'if [[ "${{ github.event_name }}" == "push" ]]' in workflow
    for job in ("gtk-runtime:", "gtk-linux-distro:", "gtk-windows-msys2:", "gtk-macos-source:"):
        start = workflow.index("\n  " + job)
        header = workflow[start:workflow.index("runs-on:", start)]
        assert "needs: plan" in header
        assert "needs.plan.outputs.run == 'true'" in header
    # GitHub's own runner limits schedule the cells; no extra serial waves.
    assert "max-parallel" not in workflow


def test_compiler_cache_scope_runs_only_native_source_builders():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    assert "- compiler-cache" in workflow

    runtime = workflow.split("  gtk-runtime:", 1)[1].split("  gtk-linux-distro:", 1)[0]
    distro = workflow.split("  gtk-linux-distro:", 1)[1].split("  gtk-windows-msys2:", 1)[0]
    windows_source = workflow.split("  gtk-windows-msys2:", 1)[1].split("  gtk-macos-source:", 1)[0]
    macos_source = workflow.split("  gtk-macos-source:", 1)[1]

    assert "inputs.scope != 'compiler-cache'" in runtime.split("steps:", 1)[0]
    assert "inputs.scope != 'compiler-cache'" in distro.split("steps:", 1)[0]
    assert "inputs.scope != 'compiler-cache'" not in windows_source.split("steps:", 1)[0]
    assert "inputs.scope != 'compiler-cache'" not in macos_source.split("steps:", 1)[0]


def test_native_gtk_source_builders_cache_only_compiler_outputs():
    workflow = (ROOT / ".github" / "workflows" / "native-gtk-matrix.yml").read_text()
    windows_source = workflow.split("  gtk-windows-msys2:", 1)[1].split("  gtk-macos-source:", 1)[0]
    macos_source = workflow.split("  gtk-macos-source:", 1)[1]

    for section in (windows_source, macos_source):
        assert "uses: actions/cache@v4" in section
        assert "path: ${{ runner.temp }}/gtk-ccache" in section
        assert "matrix.sha256" in section
        assert "CCACHE_COMPILERCHECK: content" in section
        assert "CCACHE_MAXSIZE: 1G" in section
        assert "ccache --zero-stats" in section
        assert "ccache --show-stats --verbose" in section
        assert "GTK_CCACHE_RESTORED" in section
        assert "meson setup gtk-build" in section
        assert "meson compile -C gtk-build" in section
        assert "meson install -C gtk-build" in section
        assert "CC: ccache" not in section
        assert "CXX: ccache" not in section
        job_env = section.split("    env:\n", 1)[1].split("    timeout-minutes:", 1)[0]
        assert "runner.temp" not in job_env

    assert 'export CCACHE_DIR="$(cygpath -u "$RUNNER_TEMP")/gtk-ccache"' in windows_source
    assert 'export CCACHE_DIR="$RUNNER_TEMP/gtk-ccache"' in macos_source

    assert "mingw-w64-ucrt-x86_64-ccache" in windows_source
    assert "ccache=4.13.6" in macos_source
    assert "pacman -Q mingw-w64-ucrt-x86_64-gcc" in windows_source
    assert "xcrun clang --version" in macos_source
