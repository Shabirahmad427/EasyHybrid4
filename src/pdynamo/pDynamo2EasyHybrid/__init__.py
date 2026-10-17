"""pDynamo integration package with lazy compatibility exports.

Importing standalone session-state models does not load the GTK application.
The established package-level names remain available on first access for
existing GUI callers.
"""

from importlib import import_module


_EXPORTS = {
    "pDynamoSession": ("pdynamo.pDynamo2EasyHybrid.session", "pDynamoSession"),
    "pSimulations": ("pdynamo.pDynamo2EasyHybrid.simulations_mixin", "pSimulations"),
    "pAnalysis": ("pdynamo.pDynamo2EasyHybrid.analysis_mixin", "pAnalysis"),
    "ModifyRepInVismol": (
        "pdynamo.pDynamo2EasyHybrid.representation",
        "ModifyRepInVismol",
    ),
    "LoadAndSaveData": ("pdynamo.pDynamo2EasyHybrid.io_data", "LoadAndSaveData"),
    "EasyHybridImportTrajectory": (
        "pdynamo.pDynamo2EasyHybrid.import_trajectory",
        "EasyHybridImportTrajectory",
    ),
    "Restraints": ("pdynamo.pDynamo2EasyHybrid.restraints", "Restraints"),
    "Atom": ("pdynamo.pDynamo2EasyHybrid.helpers", "Atom"),
    "generate_random_code": (
        "pdynamo.pDynamo2EasyHybrid.helpers",
        "generate_random_code",
    ),
    "export_special_PDB": (
        "pdynamo.pDynamo2EasyHybrid.helpers",
        "export_special_PDB",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    """Import and cache a legacy package-level export on first access."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
