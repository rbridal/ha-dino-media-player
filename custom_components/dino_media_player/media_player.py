"""Media Player platform for Dino Media Player."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_DINO = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media player from a config entry."""
    name = entry.data[CONF_NAME]
    topic_prefix = entry.data[CONF_TOPIC_PREFIX]

    async_add_entities([DinoMediaPlayer(hass, name, topic_prefix, entry.entry_id)])


class DinoMediaPlayer(MediaPlayerEntity):
    """Representation of the Dino Media Player."""

    _attr_supported_features = SUPPORT_DINO
    _attr_media_content_type = MediaType.MUSIC

    def __init__(self, hass: HomeAssistant, name: str, topic_prefix: str, unique_id: str):
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._topic_prefix = topic_prefix

        self._attr_state = MediaPlayerState.IDLE
        self._attr_source = None
        self._attr_source_list = []
        self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when entity is added."""

        @callback
        def message_received(msg):
            topic = msg.topic
            payload = msg.payload

            if topic.endswith("/state"):
                state_map = {
                    "playing": MediaPlayerState.PLAYING,
                    "paused": MediaPlayerState.PAUSED,
                    "stopped": MediaPlayerState.IDLE,
                    "idle": MediaPlayerState.IDLE,
                }
                self._attr_state = state_map.get(payload, MediaPlayerState.IDLE)
                self.async_write_ha_state()

            elif topic.endswith("/source"):
                self._attr_source = payload or None
                self.async_write_ha_state()

            elif topic.endswith("/sources"):
                try:
                    self._attr_source_list = json.loads(payload)
                except Exception:
                    self._attr_source_list = []
                self.async_write_ha_state()

            elif topic.endswith("/available"):
                self._attr_available = payload == "online"
                self.async_write_ha_state()

        topics = [
            f"{self._topic_prefix}/state",
            f"{self._topic_prefix}/source",
            f"{self._topic_prefix}/sources",
            f"{self._topic_prefix}/available",
        ]

        for t in topics:
            await mqtt.async_subscribe(self.hass, t, message_received, 1)

    async def _publish_command(self, action: str, source: str | None = None) -> None:
        payload = {"action": action}
        if source:
            payload["source"] = source
        await mqtt.async_publish(
            self.hass,
            f"{self._topic_prefix}/command",
            json.dumps(payload),
            1,
        )

    async def async_media_play(self) -> None:
        await self._publish_command("play", self._attr_source)

    async def async_media_pause(self) -> None:
        await self._publish_command("pause")

    async def async_media_stop(self) -> None:
        await self._publish_command("stop")

    async def async_select_source(self, source: str) -> None:
        self._attr_source = source
        await self._publish_command("set_source", source)
        self.async_write_ha_state()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a specific media file by filename."""
        self._attr_source = media_id
        await self._publish_command("play", media_id)
        self.async_write_ha_state()
