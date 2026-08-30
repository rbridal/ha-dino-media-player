"""Shared MQTT state for a Dino player device."""
from __future__ import annotations

from collections.abc import Callable
import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_TOPIC_PREFIX, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class DinoHub:
    """Holds live MQTT state and notifies entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.available = False
        self.state = "stopped"
        self.source = ""
        self.sources: list[str] = []
        self.position = 0.0
        self.duration = 0.0
        self.volume = 80
        self._listeners: list[Callable[[], None]] = []

    @property
    def name(self) -> str:
        return self.entry.options.get(CONF_NAME, self.entry.data[CONF_NAME])

    @property
    def topic_prefix(self) -> str:
        return self.entry.options.get(
            CONF_TOPIC_PREFIX, self.entry.data[CONF_TOPIC_PREFIX]
        )

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url="https://github.com/rbridal/dino-media-player",
        )

    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    def notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_publish_command(
        self,
        action: str,
        source: str | None = None,
        volume: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {"action": action}
        if source:
            payload["source"] = source
        if volume is not None:
            payload["volume"] = volume
        await mqtt.async_publish(
            self.hass,
            f"{self.topic_prefix}/command",
            json.dumps(payload),
            1,
        )

    async def async_subscribe(self) -> None:
        @callback
        def _msg(msg: mqtt.ReceiveMessage) -> None:
            topic = msg.topic
            payload = msg.payload
            if isinstance(payload, bytes):
                payload = payload.decode()

            if topic.endswith("/available"):
                self.available = payload == "online"
            elif topic.endswith("/state"):
                self.state = payload or "stopped"
            elif topic.endswith("/source"):
                self.source = payload or ""
            elif topic.endswith("/sources"):
                try:
                    data = json.loads(payload) if payload else []
                    self.sources = data if isinstance(data, list) else []
                except json.JSONDecodeError:
                    _LOGGER.warning("Invalid sources payload: %s", payload)
            elif topic.endswith("/position"):
                try:
                    self.position = float(payload or 0)
                except ValueError:
                    self.position = 0.0
            elif topic.endswith("/duration"):
                try:
                    self.duration = float(payload or 0)
                except ValueError:
                    self.duration = 0.0
            elif topic.endswith("/volume"):
                try:
                    self.volume = max(0, min(100, int(round(float(payload or 0)))))
                except ValueError:
                    pass
            self.notify()

        topics = [
            f"{self.topic_prefix}/available",
            f"{self.topic_prefix}/state",
            f"{self.topic_prefix}/source",
            f"{self.topic_prefix}/sources",
            f"{self.topic_prefix}/position",
            f"{self.topic_prefix}/duration",
            f"{self.topic_prefix}/volume",
        ]
        for topic in topics:
            await mqtt.async_subscribe(self.hass, topic, _msg, 1)
