"""Regression tests for the GTK-independent molecular analysis services."""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from util import md_analysis


def test_rmsf_is_per_atom_displacement_from_mean_position():
    coordinates = np.array(
        [
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
            [[2.0, 0.0, 0.0], [2.0, 2.0, 0.0]],
        ]
    )

    np.testing.assert_allclose(md_analysis.compute_rmsf(coordinates), [1.0, 1.0])


def test_rdf_uses_orthorhombic_minimum_image_distances():
    group_a = np.array([[[0.2, 0.0, 0.0]]])
    group_b = np.array([[[9.8, 0.0, 0.0]]])

    radii, rdf, coordination = md_analysis.compute_rdf(
        group_a,
        group_b,
        [[10.0, 10.0, 10.0]],
        same_selection=False,
        r_max=2.0,
        bin_width=0.5,
    )

    np.testing.assert_allclose(radii, [0.25, 0.75, 1.25, 1.75])
    assert rdf[0] > 0.0
    assert coordination[0] == pytest.approx(1.0)


def test_self_rdf_excludes_each_atom_as_its_own_neighbor():
    coordinates = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]])

    _, _, coordination = md_analysis.compute_rdf(
        coordinates,
        coordinates,
        [[10.0, 10.0, 10.0]],
        same_selection=True,
        r_max=2.0,
        bin_width=1.0,
    )

    np.testing.assert_allclose(coordination, [0.0, 1.0])


def test_box_density_supports_a_translated_periodic_cell():
    vertices = np.array(
        [
            [5.0, 6.0, 7.0],
            [7.0, 6.0, 7.0],
            [5.0, 9.0, 7.0],
            [7.0, 9.0, 7.0],
            [5.0, 6.0, 11.0],
            [7.0, 6.0, 11.0],
            [5.0, 9.0, 11.0],
            [7.0, 9.0, 11.0],
        ]
    )

    volumes, densities = md_analysis.compute_box_density(24.0, [vertices])

    np.testing.assert_allclose(volumes, [24.0])
    np.testing.assert_allclose(densities, [md_analysis.AMU_PER_A3_TO_G_PER_CM3])


def test_box_density_rejects_a_zero_volume_cell():
    flat_cell = np.zeros((8, 3))

    with pytest.raises(ValueError, match="zero volume"):
        md_analysis.compute_box_density(1.0, [flat_cell])


def test_md_analysis_import_does_not_require_gtk():
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
            raise AssertionError('scientific analysis imported GTK')

sys.meta_path.insert(0, RejectGtkImports())
from util import md_analysis
assert callable(md_analysis.compute_rmsf)
"""

    subprocess.run([sys.executable, "-c", code], cwd=repo_root, env=env, check=True)
