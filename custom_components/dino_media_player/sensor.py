"""Status sensors for the Dino player."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
        [
            DinoStateSensor(hub),
            DinoMediaNameSensor(hub),
            DinoPositionSensor(hub),
            DinoDurationSensor(hub),
            DinoBluetoothStatusSensor(hub),
            DinoHeartbeatSensor(hub),
        ]
    )


class DinoStateSensor(DinoEntity, SensorEntity):
    _attr_name = "Playback state"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "state")

    @property
    def native_value(self) -> str:
        return self.hub.state


class DinoMediaNameSensor(DinoEntity, SensorEntity):
    _attr_name = "Current media"
    _attr_icon = "mdi:music-box-outline"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "media_name")

    @property
    def native_value(self) -> str | None:
        return self.hub.source or None


class DinoPositionSensor(DinoEntity, SensorEntity):
    _attr_name = "Position"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:timer-outline"
    _attr_suggested_display_precision = 0

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "position")

    @property
    def native_value(self) -> float:
        return round(self.hub.position, 1)


class DinoDurationSensor(DinoEntity, SensorEntity):
    _attr_name = "Duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-sand"
    _attr_suggested_display_precision = 0

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "duration")

    @property
    def native_value(self) -> float:
        return round(self.hub.duration, 1)


class DinoBluetoothStatusSensor(DinoEntity, SensorEntity):
    _attr_name = "Bluetooth status"
    _attr_icon = "mdi:bluetooth"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "bluetooth_status")

    @property
    def native_value(self) -> str:
        return self.hub.bluetooth_status


class DinoHeartbeatSensor(DinoEntity, SensorEntity):
    _attr_name = "Last heartbeat"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, hub: DinoHub) -> None:
        super().__init__(hub, "heartbeat")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> datetime | None:
        return self.hub.last_heartbeat
