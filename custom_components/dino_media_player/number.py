"""Volume control."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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
    async_add_entities([DinoVolumeNumber(hub)])


class DinoVolumeNumber(DinoEntity, NumberEntity):
    _attr_name = "Volume"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "volume")

    @property
    def native_value(self) -> float:
        return self.hub.volume

    async def async_set_native_value(self, value: float) -> None:
        volume = max(0, min(100, int(round(value))))
        self.hub.volume = volume
        self.async_write_ha_state()
        await self.hub.async_publish_command("set_volume", volume=volume)
