"""Notify when the Pi player stays offline or Bluetooth stays down."""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_ALERT_ENABLED,
    CONF_ALERT_MINUTES,
    CONF_NOTIFY_SERVICE,
    CONF_PERSISTENT_NOTIFICATION,
    DEFAULT_ALERT_MINUTES,
)
from .hub import DinoHub

_LOGGER = logging.getLogger(__name__)
REPEAT_SECONDS = 30 * 60
BT_STABLE_SECONDS = 30
TAG_OFFLINE = "dino-player-unavailable"
TAG_BLUETOOTH = "dino-player-bluetooth"


def _is_bluetooth_output(label: str) -> bool:
    text = (label or "").lower()
    return "bt" in text or "blue" in text or "wuzhi" in text


class OfflineAlert:
    """Send a notify service after a problem lasts long enough."""

    def __init__(self, hass: HomeAssistant, hub: DinoHub) -> None:
        self.hass = hass
        self.hub = hub
        self._unsub_listener: Callable[[], None] | None = None
        self._offline_timer: Callable[[], None] | None = None
        self._bt_timer: Callable[[], None] | None = None
        self._offline_notified = False
        self._bt_notified = False
        self._bt_connected_since: float | None = None

    def async_start(self) -> None:
        self._unsub_listener = self.hub.async_add_listener(self._on_hub_update)
        self._on_hub_update()

    def async_stop(self) -> None:
        self._cancel(self._offline_timer)
        self._cancel(self._bt_timer)
        self._offline_timer = None
        self._bt_timer = None
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None

    def _enabled(self) -> bool:
        return bool(self.hub.entry.options.get(CONF_ALERT_ENABLED, False))

    def _persistent(self) -> bool:
        return bool(self.hub.entry.options.get(CONF_PERSISTENT_NOTIFICATION, False))

    def _minutes(self) -> int:
        try:
            return max(1, int(self.hub.entry.options.get(CONF_ALERT_MINUTES, DEFAULT_ALERT_MINUTES)))
        except (TypeError, ValueError):
            return DEFAULT_ALERT_MINUTES

    def _notify_target(self) -> str | None:
        raw = str(self.hub.entry.options.get(CONF_NOTIFY_SERVICE, "")).strip()
        if not raw:
            return None
        if not raw.startswith("notify."):
            raw = f"notify.{raw}"
        if raw in {"notify.notify", "notify.persistent_notification", "notify.send_message"}:
            return None
        return raw

    def _cancel(self, unsub: Callable[[], None] | None) -> None:
        if unsub:
            unsub()

    def _schedule_send(self, kind: str, recovered: bool) -> None:
        self.hass.add_job(self._async_send(kind, recovered))

    def _bluetooth_healthy(self) -> bool:
        if not self.hub.bluetooth_connected:
            self._bt_connected_since = None
            return False
        now = time.monotonic()
        if self._bt_connected_since is None:
            self._bt_connected_since = now
            return False
        return (now - self._bt_connected_since) >= BT_STABLE_SECONDS

    def _bluetooth_problem(self) -> bool:
        if not self.hub.available or not _is_bluetooth_output(self.hub.output):
            self._bt_connected_since = None
            return False
        return not self._bluetooth_healthy()

    def _on_hub_update(self) -> None:
        self.hass.loop.call_soon_threadsafe(self._on_update)

    @callback
    def _on_update(self) -> None:
        enabled = self._enabled() and (bool(self._notify_target()) or self._persistent())
        self._track(
            problem=enabled and not self.hub.available,
            notified_attr="_offline_notified",
            timer_attr="_offline_timer",
            kind="offline",
        )
        self._track(
            problem=enabled and self._bluetooth_problem(),
            notified_attr="_bt_notified",
            timer_attr="_bt_timer",
            kind="bluetooth",
        )

    @callback
    def _track(self, problem: bool, notified_attr: str, timer_attr: str, kind: str) -> None:
        notified = getattr(self, notified_attr)
        timer = getattr(self, timer_attr)
        if not problem:
            if timer:
                self._cancel(timer)
                setattr(self, timer_attr, None)
            if notified:
                setattr(self, notified_attr, False)
                self._schedule_send(kind, True)
            return
        if timer is None:
            delay = (
                timedelta(seconds=REPEAT_SECONDS)
                if notified
                else timedelta(minutes=self._minutes())
            )
            setattr(
                self,
                timer_attr,
                async_call_later(self.hass, delay, lambda _now, k=kind: self._timer_fired(k)),
            )

    @callback
    def _timer_fired(self, kind: str) -> None:
        if kind == "offline":
            self._offline_timer = None
            if self.hub.available or not self._enabled():
                return
        else:
            self._bt_timer = None
            if not self._bluetooth_problem() or not self._enabled():
                return
        self._schedule_send(kind, False)

    async def _async_notify_target(self, title: str, message: str, tag: str) -> None:
        target = self._notify_target()
        if not target:
            return
        try:
            if self.hass.states.get(target) is not None:
                await self.hass.services.async_call(
                    "notify",
                    "send_message",
                    {
                        "title": title,
                        "message": message,
                        "entity_id": target,
                    },
                    blocking=False,
                )
            else:
                await self.hass.services.async_call(
                    "notify",
                    target.removeprefix("notify."),
                    {
                        "title": title,
                        "message": message,
                        "data": {
                            "tag": tag,
                            "push": {"sound": {"name": "default"}},
                        },
                    },
                    blocking=False,
                )
            _LOGGER.info("Sent alert to %s", target)
        except Exception:
            _LOGGER.exception("Dino notify failed via %s", target)

    async def _async_send(self, kind: str, recovered: bool) -> None:
        title = self.hub.name
        minutes = self._minutes()
        if kind == "offline":
            tag = TAG_OFFLINE
            if recovered:
                message = f"{title} is back online."
            else:
                message = f"{title} has been unavailable for {minutes} minutes or more."
                self._offline_notified = True
        else:
            tag = TAG_BLUETOOTH
            output = self.hub.output or "Bluetooth"
            if recovered:
                message = f"{title} Bluetooth ({output}) is connected again."
            else:
                message = (
                    f"{title} output is {output}, but Bluetooth has been disconnected "
                    f"for {minutes} minutes or more."
                )
                self._bt_notified = True

        await self._async_notify_target(title, message, tag)

        if self._persistent():
            try:
                if recovered:
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "dismiss",
                        {"notification_id": tag},
                        blocking=False,
                    )
                else:
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": title,
                            "message": message,
                            "notification_id": tag,
                        },
                        blocking=False,
                    )
            except Exception:
                _LOGGER.exception("Persistent notification failed for %s", kind)
