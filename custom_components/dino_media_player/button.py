"""Stop and reconnect buttons."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DinoEntity
from .hub import DinoHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: DinoHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DinoStopButton(hub), DinoReconnectButton(hub)])


class DinoStopButton(DinoEntity, ButtonEntity):
    _attr_name = "Stop"
    _attr_icon = "mdi:stop"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "stop")

    async def async_press(self) -> None:
        await self.hub.async_publish_command("stop")


class DinoReconnectButton(DinoEntity, ButtonEntity):
    _attr_name = "Reconnect Bluetooth"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "reconnect")

    async def async_press(self) -> None:
        await self.hub.async_publish_command("reconnect")
