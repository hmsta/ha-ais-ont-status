"""Sensors for AIS ONT Status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import AisOntStatus
from .const import DOMAIN
from .coordinator import AisOntStatusCoordinator
from .entity import AisOntEntity


@dataclass(frozen=True)
class AisOntSensorDescription(SensorEntityDescription):
    """Description for an AIS ONT sensor."""

    value_fn: Callable[[AisOntStatus], float | int | str | None] | None = None


SENSORS = (
    AisOntSensorDescription(
        key="rx_power",
        translation_key="rx_power",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda status: status.rx_power_dbm,
    ),
    AisOntSensorDescription(
        key="tx_power",
        translation_key="tx_power",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda status: status.tx_power_dbm,
    ),
    AisOntSensorDescription(
        key="poll_duration",
        translation_key="poll_duration",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: status.poll_duration_ms,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AIS ONT sensors."""
    coordinator: AisOntStatusCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AisOntSensor(entry, coordinator, description) for description in SENSORS
    )


class AisOntSensor(AisOntEntity, SensorEntity):
    """AIS ONT sensor."""

    entity_description: AisOntSensorDescription

    @property
    def available(self) -> bool:
        """Return whether this sensor has a known value."""
        if not super().available:
            return False
        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return False
        return self.entity_description.value_fn(self.coordinator.data) is not None

    @property
    def native_value(self) -> float | int | str | None:
        """Return sensor value."""
        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
