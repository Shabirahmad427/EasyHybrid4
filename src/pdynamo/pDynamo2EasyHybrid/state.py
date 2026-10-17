"""GTK-independent in-memory state for an EasyHybrid pDynamo session.

The pDynamo session facade historically exposed these values as direct
attributes. ``pDynamoSession`` keeps those public attributes as delegating
properties while this model owns their defaults and reset behavior.
"""

from dataclasses import dataclass, field


@dataclass
class SessionState:
    """Mutable project/session bookkeeping independent of GTK and VisMol."""

    systems: dict = field(default_factory=lambda: {0: None})
    active_id: int = 0
    psystem_name_list: list = field(default_factory=list)
    psystem_name_counter: int = 1
    counter: int = 0
    color_palette_counter: int = 0
    random_code: str = ""
    changed: bool = False
    autosave_change_counter: int = 0
    process_pool: dict = field(default_factory=dict)

    def set_active(self, system_id=None):
        """Set the active system ID, preserving the legacy None behavior."""
        if system_id is not None:
            self.active_id = system_id

    def get_system(self, system_id=None):
        """Return a selected system, defaulting to the active system."""
        if system_id is None:
            system_id = self.active_id
        return self.systems[system_id]

    def reset_systems(self):
        """Clear loaded-system bookkeeping as ``pDynamoSession.restart`` did."""
        self.active_id = 0
        self.systems = {0: None}
        self.psystem_name_list = []
        self.psystem_name_counter = 1
        self.counter = 0
        self.color_palette_counter = 0
