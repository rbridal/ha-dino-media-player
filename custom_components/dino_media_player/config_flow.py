"""Config flow for Dino Media Player."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ALERT_ENABLED,
    CONF_ALERT_MINUTES,
    CONF_NOTIFY_SERVICE,
    CONF_TOPIC_PREFIX,
    DEFAULT_ALERT_MINUTES,
    DEFAULT_NAME,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)


def _notify_choices(hass: HomeAssistant) -> list[str]:
    services = hass.services.async_services().get("notify", {})
    names = sorted(name for name in services if name != "send_message")
    return [f"notify.{name}" for name in names]


def _user_schema(name: str, prefix: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=name): str,
            vol.Required(CONF_TOPIC_PREFIX, default=prefix): str,
        }
    )


def _options_schema(
    hass: HomeAssistant,
    name: str,
    prefix: str,
    alert_enabled: bool,
    alert_minutes: int,
    notify_service: str,
) -> vol.Schema:
    choices = _notify_choices(hass)
    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=name): str,
        vol.Required(CONF_TOPIC_PREFIX, default=prefix): str,
        vol.Required(CONF_ALERT_ENABLED, default=alert_enabled): BooleanSelector(),
        vol.Required(CONF_ALERT_MINUTES, default=alert_minutes): NumberSelector(
            NumberSelectorConfig(
                min=1, max=120, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min"
            )
        ),
    }
    if choices:
        default_notify = notify_service if notify_service in choices else choices[0]
        schema[vol.Optional(CONF_NOTIFY_SERVICE, default=default_notify)] = SelectSelector(
            SelectSelectorConfig(options=choices, mode=SelectSelectorMode.DROPDOWN)
        )
    else:
        schema[vol.Optional(CONF_NOTIFY_SERVICE, default=notify_service)] = str
    return vol.Schema(schema)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dino Media Player."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(DEFAULT_NAME, DEFAULT_TOPIC_PREFIX),
            )

        await self.async_set_unique_id(user_input[CONF_TOPIC_PREFIX])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change device name, MQTT prefix, and offline alerts."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input[CONF_ALERT_MINUTES] = int(user_input[CONF_ALERT_MINUTES])
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                self.hass,
                opts.get(CONF_NAME, data.get(CONF_NAME, DEFAULT_NAME)),
                opts.get(CONF_TOPIC_PREFIX, data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)),
                bool(opts.get(CONF_ALERT_ENABLED, False)),
                int(opts.get(CONF_ALERT_MINUTES, DEFAULT_ALERT_MINUTES)),
                str(opts.get(CONF_NOTIFY_SERVICE, "")),
            ),
        )
