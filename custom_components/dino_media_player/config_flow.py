"""Config flow for Dino Media Player."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TOPIC_PREFIX, DEFAULT_NAME, DEFAULT_TOPIC_PREFIX, DOMAIN


def _schema(name: str, prefix: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=name): str,
            vol.Required(CONF_TOPIC_PREFIX, default=prefix): str,
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dino Media Player."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_schema(DEFAULT_NAME, DEFAULT_TOPIC_PREFIX),
            )

        await self.async_set_unique_id(user_input[CONF_TOPIC_PREFIX])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change device name and MQTT prefix."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        name = self.config_entry.options.get(
            CONF_NAME, self.config_entry.data.get(CONF_NAME, DEFAULT_NAME)
        )
        prefix = self.config_entry.options.get(
            CONF_TOPIC_PREFIX,
            self.config_entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX),
        )
        return self.async_show_form(step_id="init", data_schema=_schema(name, prefix))
