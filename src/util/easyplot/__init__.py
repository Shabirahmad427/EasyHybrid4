"""EasyHybrid plotting API with lazy GTK widget exports.

Pure plotting calculations can be imported from this package without loading
PyGObject. GTK-backed widgets are imported only when their public names are
requested, preserving the historical ``from util.easyplot import XYPlot``
interface for GUI callers.
"""

from importlib import import_module


_EXPORTS = {
    "interpolate_color": ("util.easyplot.color_math", "interpolate_color"),
    "get_color": ("util.easyplot.color_math", "get_color"),
    "bilinear_interpolation": ("util.easyplot.color_math", "bilinear_interpolation"),
    "expand_array_size": ("util.easyplot.color_math", "expand_array_size"),
    "ColorSquareBilinearInterpolation": (
        "util.easyplot.color_utils",
        "ColorSquareBilinearInterpolation",
    ),
    "Canvas": ("util.easyplot.canvas", "Canvas"),
    "ImagePlot": ("util.easyplot.image_plot", "ImagePlot"),
    "XYPlot": ("util.easyplot.xy_plots", "XYPlot"),
    "XYScatterPlot": ("util.easyplot.xy_plots", "XYScatterPlot"),
    "export_plot_to_png": ("util.easyplot.export_utils", "export_plot_to_png"),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    """Load a public plotting class/function on first access."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
