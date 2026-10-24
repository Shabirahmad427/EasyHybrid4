"""Guard the coordinate and identity baselines used by graphics regressions."""

from pathlib import Path


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def read_atoms(path):
    atoms = []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith(("ATOM  ", "HETATM")):
            atoms.append(
                (
                    line[12:16].strip(),
                    line[17:20].strip(),
                    int(line[22:26]),
                    tuple(float(line[start:start + 8]) for start in (30, 38, 46)),
                    line[76:78].strip(),
                )
            )
    return atoms


def test_water_full_app_fixture_has_frozen_atom_identity_and_coordinates():
    assert read_atoms(FIXTURES / "water.pdb") == [
        ("O", "HOH", 1, (0.0, 0.0, 0.0), "O"),
        ("H1", "HOH", 1, (0.957, 0.0, 0.0), "H"),
        ("H2", "HOH", 1, (-0.24, 0.927, 0.0), "H"),
    ]


def test_vismol_render_fixture_has_frozen_atom_identity_and_coordinates():
    assert read_atoms(FIXTURES / "render_validation.pdb") == [
        ("O", "HOH", 1, (0.0, 3.0, 0.0), "O"),
        ("H1", "HOH", 1, (0.957, 3.0, 0.0), "H"),
        ("H2", "HOH", 1, (-0.24, 3.927, 0.0), "H"),
        ("C", "CAA", 2, (-4.0, -2.0, 0.0), "C"),
        ("N", "NAA", 3, (0.0, -2.0, 0.0), "N"),
        ("S", "SAA", 4, (4.0, -2.0, 0.0), "S"),
    ]
