"""Coverage for the CI helper that selects GTK source-build Meson options."""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "gtk_meson_options",
    Path(__file__).resolve().parents[1] / ".github" / "scripts" / "gtk_meson_options.py",
)
gtk_meson_options = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gtk_meson_options)

# Excerpts in the formats used by GTK 4.8 (meson_options.txt) and 4.18.
GTK_48 = """
option('macos-backend',
       type: 'boolean',
       value: true)
option('vulkan',
       type: 'feature',
       value: 'enabled')
option('demos',
       type: 'boolean',
       value: true)
option('gtk_doc', type: 'boolean', value: false)
"""
GTK_418 = """
option('build-demos', type: 'boolean', value: true)
option('documentation', type: 'boolean', value: false)
option('accesskit', type: 'feature', value: 'auto')
option('introspection', type: 'feature', value: 'auto')
"""


def test_old_option_names_are_typed_and_selected():
    arguments = gtk_meson_options.meson_arguments(gtk_meson_options.parse_option_types(GTK_48))

    assert arguments == [
        "-Dmacos-backend=true", "-Dvulkan=disabled", "-Dgtk_doc=false", "-Ddemos=false",
    ]


def test_renamed_options_are_used_only_where_defined():
    arguments = gtk_meson_options.meson_arguments(gtk_meson_options.parse_option_types(GTK_418))

    assert "-Dbuild-demos=false" in arguments
    assert "-Ddocumentation=false" in arguments
    assert "-Daccesskit=disabled" in arguments
    assert "-Dintrospection=enabled" in arguments
    assert not any(argument.startswith(("-Ddemos=", "-Dgtk_doc=")) for argument in arguments)


def test_main_reads_either_options_file_name(tmp_path, capsys):
    (tmp_path / "meson_options.txt").write_text(GTK_48)

    assert gtk_meson_options.main(["prog", str(tmp_path)]) == 0
    assert "-Ddemos=false" in capsys.readouterr().out
