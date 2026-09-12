"""Config flow for AIS ONT Status."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .client import AisOntTelnetClient, CannotConnect, InvalidAuth, WebSessionError
from .const import (
    CONF_MODEM_REACHABILITY_PORT,
    CONF_RX_POWER_MIN_DBM,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_WEB_SESSION_COOKIE,
    DEFAULT_HOST,
    DEFAULT_MODEM_REACHABILITY_PORT,
    DEFAULT_PORT,
    DEFAULT_RX_POWER_MIN_DBM,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_USERNAME,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
)


def _schema(
    defaults: dict[str, Any] | None = None, *, include_web_session_cookie: bool = False
) -> vol.Schema:
    """Build the config form schema."""
    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST)): str,
        vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(
            CONF_USERNAME, default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME)
        ): str,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
        vol.Optional(
            CONF_TIMEOUT,
            default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_TIMEOUT)),
        vol.Optional(
            CONF_RX_POWER_MIN_DBM,
            default=defaults.get(CONF_RX_POWER_MIN_DBM, DEFAULT_RX_POWER_MIN_DBM),
        ): vol.Coerce(float),
        vol.Optional(
            CONF_MODEM_REACHABILITY_PORT,
            default=defaults.get(
                CONF_MODEM_REACHABILITY_PORT, DEFAULT_MODEM_REACHABILITY_PORT
            ),
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }

    password_selector = selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )
    if CONF_PASSWORD in defaults:
        schema[vol.Optional(CONF_PASSWORD)] = password_selector
    else:
        schema[vol.Required(CONF_PASSWORD)] = password_selector

    if include_web_session_cookie:
        schema[vol.Optional(CONF_WEB_SESSION_COOKIE)] = password_selector

    return vol.Schema(schema)


def _client_from_input(user_input: dict[str, Any]) -> AisOntTelnetClient:
    """Build the ONT client from config flow input."""
    return AisOntTelnetClient(
        host=user_input[CONF_HOST],
        port=user_input[CONF_PORT],
        username=user_input[CONF_USERNAME],
        password=user_input[CONF_PASSWORD],
        timeout=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        rx_power_min_dbm=user_input.get(CONF_RX_POWER_MIN_DBM, DEFAULT_RX_POWER_MIN_DBM),
        modem_reachability_port=user_input.get(
            CONF_MODEM_REACHABILITY_PORT, DEFAULT_MODEM_REACHABILITY_PORT
        ),
    )


async def _validate_input(user_input: dict[str, Any]) -> None:
    """Validate that the ONT can be reached and read."""
    client = _client_from_input(user_input)
    await client.async_test_auth()


class AisOntStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle AIS ONT Status config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"AIS ONT {user_input[CONF_HOST]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None

        errors: dict[str, str] = {}
        defaults = {**entry.data}

        if user_input is not None:
            web_session_cookie = (
                user_input.pop(CONF_WEB_SESSION_COOKIE, "") or ""
            ).strip()
            if not user_input.get(CONF_PASSWORD):
                user_input = {
                    key: value
                    for key, value in user_input.items()
                    if key != CONF_PASSWORD
                }
            data = {**entry.data, **user_input}
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            if unique_id != entry.unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            try:
                if web_session_cookie:
                    await _client_from_input(data).async_enable_telnet_lan(
                        web_session_cookie
                    )
                await _validate_input(data)
            except WebSessionError:
                errors["base"] = "web_session_invalid"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = (
                    "enable_telnet_failed" if web_session_cookie else "cannot_connect"
                )
            except Exception:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    unique_id=unique_id,
                    title=f"AIS ONT {data[CONF_HOST]}",
                    data=data,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(defaults, include_web_session_cookie=True),
            errors=errors,
        )
