"""Pure validation helpers for reaction-coordinate scan inputs."""


def has_positive_step_counts(*values) -> bool:
    """Return whether every supplied scan step count is a positive integer."""
    if not values:
        return False
    for value in values:
        if isinstance(value, str):
            try:
                count = int(value.strip())
            except ValueError:
                return False
        elif type(value) is int:
            count = value
        else:
            return False
        if count <= 0:
            return False
    return True
