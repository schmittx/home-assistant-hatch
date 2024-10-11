"""Support for Hatch number entities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import final

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchEntity
from .const import DOMAIN, DEVICES, ENTITIES

@dataclass
class HatchNumberEntityDescription(NumberEntityDescription):
    """Class to describe a Hatch number."""

NUMBER_DESCRIPTIONS: list[HatchNumberEntityDescription] = [
    HatchNumberEntityDescription(
        key="clock_brightness",
        name="Clock Brightness",
        entity_category=EntityCategory.CONFIG,
        native_max_value=100,
        native_min_value=0,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:brightness-6",
    ),
]


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch number entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchNumberEntity] = []

    for device in devices:
        for description in NUMBER_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchNumberEntity(
                        device=device,
                        entity_description=description,
                    )
                )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchNumberEntity(HatchEntity, NumberEntity):
    """Representation of a Hatch number entity."""

    entity_description: HatchNumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return getattr(self.device, self.entity_description.key)

    @final
    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        setattr(self.device, self.entity_description.key, value)
