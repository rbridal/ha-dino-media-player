"""Base entity tied to the Dino device availability."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .hub import DinoHub


class DinoEntity(Entity):
    """Entity that goes unavailable when the Pi is offline."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: DinoHub, key: str) -> None:
        self.hub = hub
        self._attr_unique_id = f"{hub.entry.entry_id}_{key}"
        self._attr_device_info = hub.device_info

    @property
    def available(self) -> bool:
        return self.hub.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.async_add_listener(self.async_write_ha_state))
