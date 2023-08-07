"""Support for Hatch sensor entities."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HatchEntity
from .const import DOMAIN, DEVICES, ENTITIES

@dataclass
class HatchSensorEntityDescription(SensorEntityDescription):
    """Class to describe a Hatch sensor entity."""

SENSOR_DESCRIPTIONS: list[HatchSensorEntityDescription] = [
    HatchSensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
    ),
]


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch sensor entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchSensorEntity] = []

    for device in devices:
        for description in SENSOR_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchSensorEntity(
                        device=device,
                        entity_description=description,
                    )
                )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchSensorEntity(HatchEntity, SensorEntity):
    """Representation of a Hatch sensor entity."""

    entity_description: HatchSensorEntityDescription

    @property
    def native_value(self) -> StateType | date | datetime:
        return getattr(self.device, self.entity_description.key)
