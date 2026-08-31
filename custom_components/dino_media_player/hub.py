"""Shared MQTT state for a Dino player device."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_TOPIC_PREFIX, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)
HEARTBEAT_STALE = timedelta(seconds=45)


class DinoHub:
    """Holds live MQTT state and notifies entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.mqtt_online = False
        self.state = "stopped"
        self.source = ""
        self.sources: list[str] = []
        self.output = "3.5mm jack"
        self.outputs: list[str] = ["3.5mm jack", "BT-WUZHI"]
        self.position = 0.0
        self.duration = 0.0
        self.volume = 80
        self.bluetooth_status = "unknown"
        self.last_heartbeat: datetime | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsub_interval: Callable[[], None] | None = None

    @property
    def name(self) -> str:
        return self.entry.options.get(CONF_NAME, self.entry.data[CONF_NAME])

    @property
    def topic_prefix(self) -> str:
        return self.entry.options.get(
            CONF_TOPIC_PREFIX, self.entry.data[CONF_TOPIC_PREFIX]
        )

    @property
    def heartbeat_fresh(self) -> bool:
        if self.last_heartbeat is None:
            return False
        return dt_util.utcnow() - self.last_heartbeat <= HEARTBEAT_STALE

    @property
    def available(self) -> bool:
        return self.mqtt_online and self.heartbeat_fresh

    @property
    def bluetooth_connected(self) -> bool:
        return self.bluetooth_status == "connected"

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

    def async_unload(self) -> None:
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None

    async def async_publish_command(
        self,
        action: str,
        source: str | None = None,
        volume: int | None = None,
        output: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"action": action}
        if source:
            payload["source"] = source
        if volume is not None:
            payload["volume"] = volume
        if output:
            payload["output"] = output
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
                self.mqtt_online = payload == "online"
            elif topic.endswith("/heartbeat"):
                parsed = dt_util.parse_datetime(payload) if payload else None
                if parsed is not None:
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=dt_util.UTC)
                    self.last_heartbeat = dt_util.as_utc(parsed)
                    self.mqtt_online = True
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
            elif topic.endswith("/outputs"):
                try:
                    data = json.loads(payload) if payload else []
                    if isinstance(data, list) and data:
                        self.outputs = [str(x) for x in data]
                except json.JSONDecodeError:
                    _LOGGER.warning("Invalid outputs payload: %s", payload)
            elif topic.endswith("/output"):
                if payload:
                    self.output = payload
            elif topic.endswith("/bluetooth"):
                self.bluetooth_status = payload or "unknown"
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
            f"{self.topic_prefix}/heartbeat",
            f"{self.topic_prefix}/state",
            f"{self.topic_prefix}/source",
            f"{self.topic_prefix}/sources",
            f"{self.topic_prefix}/output",
            f"{self.topic_prefix}/outputs",
            f"{self.topic_prefix}/bluetooth",
            f"{self.topic_prefix}/position",
            f"{self.topic_prefix}/duration",
            f"{self.topic_prefix}/volume",
        ]
        for topic in topics:
            await mqtt.async_subscribe(self.hass, topic, _msg, 1)

        @callback
        def _tick(_now) -> None:
            self.notify()

        self._unsub_interval = async_track_time_interval(
            self.hass, _tick, timedelta(seconds=15)
        )
