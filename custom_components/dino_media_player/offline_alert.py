"""Notify when the Pi player stays offline."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_ALERT_ENABLED,
    CONF_ALERT_MINUTES,
    CONF_NOTIFY_SERVICE,
    DEFAULT_ALERT_MINUTES,
)
from .hub import DinoHub

_LOGGER = logging.getLogger(__name__)
REPEAT_SECONDS = 30 * 60
TAG = "dino-player-unavailable"


class OfflineAlert:
    """Send a notify service after the player is offline long enough."""

    def __init__(self, hass: HomeAssistant, hub: DinoHub) -> None:
        self.hass = hass
        self.hub = hub
        self._unsub_timer: Callable[[], None] | None = None
        self._unsub_listener: Callable[[], None] | None = None
        self._notified = False

    def async_start(self) -> None:
        self._unsub_listener = self.hub.async_add_listener(self._on_update)
        self._on_update()

    def async_stop(self) -> None:
        self._cancel_timer()
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None

    def _enabled(self) -> bool:
        return bool(self.hub.entry.options.get(CONF_ALERT_ENABLED, False))

    def _minutes(self) -> int:
        try:
            return max(1, int(self.hub.entry.options.get(CONF_ALERT_MINUTES, DEFAULT_ALERT_MINUTES)))
        except (TypeError, ValueError):
            return DEFAULT_ALERT_MINUTES

    def _notify_service(self) -> str | None:
        raw = str(self.hub.entry.options.get(CONF_NOTIFY_SERVICE, "")).strip()
        if not raw:
            return None
        if raw.startswith("notify."):
            raw = raw[7:]
        return raw or None

    def _cancel_timer(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _on_update(self) -> None:
        if not self._enabled() or not self._notify_service():
            if self._notified and self.hub.available:
                self.hass.async_create_task(self._async_send(recovered=True))
                self._notified = False
            self._cancel_timer()
            return

        if self.hub.available:
            self._cancel_timer()
            if self._notified:
                self.hass.async_create_task(self._async_send(recovered=True))
                self._notified = False
            return

        if self._unsub_timer is None and not self._notified:
            self._unsub_timer = async_call_later(
                self.hass, timedelta(minutes=self._minutes()), self._timer_fired
            )
        elif self._unsub_timer is None and self._notified:
            self._unsub_timer = async_call_later(
                self.hass, timedelta(seconds=REPEAT_SECONDS), self._timer_fired
            )

    @callback
    def _timer_fired(self, _now) -> None:
        self._unsub_timer = None
        if self.hub.available or not self._enabled():
            return
        self.hass.async_create_task(self._async_send(recovered=False))

    async def _async_send(self, recovered: bool) -> None:
        service = self._notify_service()
        if not service:
            return
        if recovered:
            title = "Dino yard"
            message = f"{self.hub.name} is back online."
        else:
            title = "Dino yard"
            message = (
                f"{self.hub.name} has been unavailable for {self._minutes()} minutes or more."
            )
            self._notified = True
            if not self.hub.available and self._unsub_timer is None:
                self._unsub_timer = async_call_later(
                    self.hass, timedelta(seconds=REPEAT_SECONDS), self._timer_fired
                )
        payload = {
            "title": title,
            "message": message,
            "data": {
                "tag": TAG,
                "push": {"sound": {"name": "default"}},
            },
        }
        if recovered:
            payload["message"] = message
        try:
            await self.hass.services.async_call("notify", service, payload, blocking=False)
        except Exception:
            _LOGGER.exception("Offline notify failed via notify.%s", service)
