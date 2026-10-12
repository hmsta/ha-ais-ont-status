"""Binary sensors for AIS ONT Status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import AisOntStatus
from .const import DOMAIN
from .coordinator import AisOntStatusCoordinator
from .entity import AisOntEntity


@dataclass(frozen=True)
class AisOntBinarySensorDescription(BinarySensorEntityDescription):
    """Description for an AIS ONT binary sensor."""

    value_fn: Callable[[AisOntStatus], bool | None] | None = None


BINARY_SENSORS = (
    AisOntBinarySensorDescription(
        key="modem_reachable",
        translation_key="modem_reachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda status: status.modem_reachable,
    ),
    AisOntBinarySensorDescription(
        key="fiber_link",
        translation_key="fiber_link",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda status: (
            status.optical_signal_ok if status.rx_power_dbm is not None else None
        ),
    ),
    AisOntBinarySensorDescription(
        key="telnet",
        translation_key="telnet",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: status.telnet_ok,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AIS ONT binary sensors."""
    coordinator: AisOntStatusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AisOntBinarySensor(entry, coordinator, description)
        for description in BINARY_SENSORS
    )


class AisOntBinarySensor(AisOntEntity, BinarySensorEntity):
    """AIS ONT binary sensor."""

    entity_description: AisOntBinarySensorDescription

    @property
    def available(self) -> bool:
        """Return whether this sensor has a known state."""
        if not super().available:
            return False
        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return False
        return self.entity_description.value_fn(self.coordinator.data) is not None

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return error attributes for diagnostics."""
        if self.entity_description.key != "telnet":
            return None
        if self.coordinator.data is None or self.coordinator.data.error is None:
            return None
        return {"last_error": self.coordinator.data.error}
