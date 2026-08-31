"""Availability and Bluetooth binary sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    async_add_entities(
        [DinoAvailabilitySensor(hub), DinoBluetoothConnectedSensor(hub)]
    )


class DinoAvailabilitySensor(DinoEntity, BinarySensorEntity):
    """Online / offline for the Pi player."""

    _attr_name = "Availability"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "availability")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.hub.available


class DinoBluetoothConnectedSensor(DinoEntity, BinarySensorEntity):
    _attr_name = "Bluetooth connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "bluetooth_connected")

    @property
    def is_on(self) -> bool:
        return self.hub.bluetooth_connected
