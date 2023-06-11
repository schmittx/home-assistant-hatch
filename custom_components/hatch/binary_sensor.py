"""Support for Hatch binary sensor entities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchEntity
from .const import DOMAIN, DEVICES, ENTITIES

@dataclass
class HatchBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a Hatch binary sensor entity."""


BINARY_SENSOR_DESCRIPTIONS: list[HatchBinarySensorEntityDescription] = [
    HatchBinarySensorEntityDescription(
        key="is_light_on",
        name="Color Status",
        device_class=BinarySensorDeviceClass.LIGHT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch binary sensor entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchBinarySensorEntity] = []

    for device in devices:
        for description in BINARY_SENSOR_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchBinarySensorEntity(
                        device=device,
                        entity_description=description,
                    )
                )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchBinarySensorEntity(BinarySensorEntity, HatchEntity):
    """Representation of a Hatch binary sensor entity."""

    entity_description: HatchBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return getattr(self.device, self.entity_description.key)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        attrs = {}
        if self.variable == "is_light_on":
            for attr in [
                "current_color_r",
                "current_color_g",
                "current_color_b",
                "current_color_i",
                "current_color_rainbow",
                "current_color_w",
            ]:
                attrs[attr] = getattr(self.device, attr)
        return attrs
