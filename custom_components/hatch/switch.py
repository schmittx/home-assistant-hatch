"""Support for Hatch switch entities."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchEntity
from .api.device import Device as HatchDevice
from .api.rest_plus import Preset as HatchPreset
from .const import DOMAIN, DEVICES, ENTITIES

@dataclass
class HatchSwitchEntityDescription(SwitchEntityDescription):
    """Class to describe a Hatch switch entity."""

    extra_attrs: dict[str, Callable] | None = None

SWITCH_DESCRIPTIONS: list[HatchSwitchEntityDescription] = [
    HatchSwitchEntityDescription(
        key="is_device_on",
        name="Power",
        entity_category=None,
        extra_attrs={
            "active_preset_index": lambda device: getattr(device, "active_preset_index"),
            "active_program_name": lambda device: getattr(device, "active_program_name"),
        },
    ),
    HatchSwitchEntityDescription(
        key="clock_enabled",
        name="Show Clock",
        entity_category=EntityCategory.CONFIG,
    ),
    HatchSwitchEntityDescription(
        key="clock_24hr_time",
        name="24-Hour Time",
        entity_category=EntityCategory.CONFIG,
    ),
]


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch switch entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchSwitchEntity] = []

    for device in devices:
        for description in SWITCH_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchSwitchEntity(
                        device=device,
                        entity_description=description,
                    )
                )
        if hasattr(device, "presets"):
            for preset in device.presets:
                if preset.is_favorite:
                    _LOGGER.debug(
                        f"[{device.info.name}] Found preset switch entity: {preset.index}",
                    )
                    entities.append(
                        HatchSwitchEntity(
                            device=device,
                            entity_description=HatchSwitchEntityDescription(
                                key=None,
                                name=None,
                                entity_category=EntityCategory.CONFIG,
                            ),
                            preset=preset,
                        )
                    )

    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchSwitchEntity(HatchEntity, SwitchEntity):
    """Representation of a Hatch switch entity."""

    entity_description: HatchSwitchEntityDescription

    def __init__(
        self,
        device: HatchDevice,
        entity_description: HatchSwitchEntityDescription=None,
        preset: HatchPreset=None,
    ) -> None:
        """Initialize device."""
        super().__init__(device, entity_description)
        self.preset = preset

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        name = super().name
        if self.preset:
            return f"{name} Preset {self.preset.index} Enabled"
        return name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        unique_id = super().unique_id
        if self.preset:
            return f"{unique_id}-preset-{self.preset.index}-enabled"
        return unique_id

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        if self.preset:
            return getattr(self.preset, "is_enabled")
        return getattr(self.device, self.entity_description.key)

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if self.preset:
            self.device.enable_preset(self.preset, True)
        else:
            setattr(self.device, self.entity_description.key, True)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if self.preset:
            self.device.enable_preset(self.preset, False)
        else:
            setattr(self.device, self.entity_description.key, False)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        attrs = {}
        if self.entity_description.extra_attrs and self.is_on:
            for key, func in self.entity_description.extra_attrs.items():
                if value := func(self.device):
                    attrs[key] = value
        return attrs
