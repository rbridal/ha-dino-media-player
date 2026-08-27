"""Media source select."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
    async_add_entities([DinoSourceSelect(hub)])


class DinoSourceSelect(DinoEntity, SelectEntity):
    _attr_name = "Media"
    _attr_icon = "mdi:playlist-music"
    _attr_translation_key = "media"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "media")

    @property
    def options(self) -> list[str]:
        opts = list(self.hub.sources)
        if self.hub.source and self.hub.source not in opts:
            opts.append(self.hub.source)
        return opts or ([self.hub.source] if self.hub.source else [""])

    @property
    def current_option(self) -> str | None:
        if self.hub.source and self.hub.source in self.options:
            return self.hub.source
        if self.options and self.options[0]:
            return self.options[0]
        return None

    async def async_select_option(self, option: str) -> None:
        await self.hub.async_publish_command("set_source", option)
