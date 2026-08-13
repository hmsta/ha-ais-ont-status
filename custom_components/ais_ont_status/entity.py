"""Base entity for AIS ONT Status."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AisOntStatusCoordinator


@dataclass(frozen=True)
class AisOntEntityDescription(EntityDescription):
    """AIS ONT entity description."""


class AisOntEntity(CoordinatorEntity[AisOntStatusCoordinator]):
    """Base class for AIS ONT entities."""

    entity_description: AisOntEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: AisOntStatusCoordinator,
        description: AisOntEntityDescription,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self.config_entry = entry
        self.entity_description = description
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Huawei / AIS",
            model="HG8045B7N-52",
            name=f"AIS ONT {host}",
            configuration_url=f"http://{host}/",
        )
