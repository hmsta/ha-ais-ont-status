"""Coordinator for AIS ONT Status."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import AisOntStatus, AisOntTelnetClient, InvalidAuth
from .const import (
    CONF_MODEM_REACHABILITY_PORT,
    CONF_RX_POWER_MIN_DBM,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_MODEM_REACHABILITY_PORT,
    DEFAULT_RX_POWER_MIN_DBM,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class AisOntStatusCoordinator(DataUpdateCoordinator[AisOntStatus]):
    """Data update coordinator for AIS ONT optical status."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AisOntTelnetClient,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> AisOntStatus:
        """Fetch optical status from the ONT."""
        try:
            return await self.client.async_get_status()
        except InvalidAuth as err:
            _LOGGER.error("AIS ONT rejected the configured Telnet credentials")
            raise ConfigEntryAuthFailed from err


def build_client(entry: ConfigEntry) -> AisOntTelnetClient:
    """Build a Telnet client from a config entry."""
    return AisOntTelnetClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        timeout=entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        rx_power_min_dbm=entry.data.get(
            CONF_RX_POWER_MIN_DBM, DEFAULT_RX_POWER_MIN_DBM
        ),
        modem_reachability_port=entry.data.get(
            CONF_MODEM_REACHABILITY_PORT, DEFAULT_MODEM_REACHABILITY_PORT
        ),
    )
