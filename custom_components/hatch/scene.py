"""Support for Hatch scene entities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_MODE,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
)
from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_SOUND_MODE,
)
from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchEntity
from .api.device import Device as HatchDevice
from .api.rest_plus import Preset as HatchPreset
from .const import DOMAIN, DEVICES, EFFECT_RAINBOW, ENTITIES

@dataclass
class HatchSceneEntityDescription(EntityDescription):
    """Class to describe a Hatch scene entity."""

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch scene entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchSceneEntity] = []

    for device in devices:
        if hasattr(device, "presets"):
            for preset in device.presets:
                if preset.is_favorite:
                    _LOGGER.debug(
                        f"[{device.info.name}] Found preset scene entity: {preset.index}",
                    )
                    entities.append(
                        HatchSceneEntity(
                            device=device,
                            entity_description=HatchSceneEntityDescription(
                                key=None,
                                name=None,
                                entity_category=EntityCategory.CONFIG,
                            ),
                            preset=preset,
                        )
                    )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchSceneEntity(HatchEntity, Scene):
    """Representation of a Hatch scene entity."""

    entity_description: HatchSceneEntityDescription

    def __init__(
        self,
        device: HatchDevice,
        entity_description: HatchSceneEntityDescription=None,
        preset: HatchPreset=None,
    ) -> None:
        """Initialize device."""
        super().__init__(device, entity_description)
        self.preset = preset

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{super().name} Preset {self.preset.index}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{super().unique_id}-preset-{self.preset.index}"

    def activate(self, **kwargs: Any) -> None:
        """Activate scene. Try to get entities into requested state."""
        self.device.set_preset(self.preset)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        attrs = {
            "index": self.preset.index
        }
        if self.preset.audio.name is not None:
            attrs[ATTR_SOUND_MODE] = self.preset.audio.name
        if self.preset.audio.volume is not None:
            attrs[ATTR_MEDIA_VOLUME_LEVEL] = self.preset.audio.volume
        if all(
            [
                self.preset.color.red is not None,
                self.preset.color.green is not None,
                self.preset.color.blue is not None,
            ]
        ):
            attrs[ATTR_RGB_COLOR] = (
                self.preset.color.red,
                self.preset.color.green,
                self.preset.color.blue,
            )
        if self.preset.color.intensity is not None:
            attrs[ATTR_BRIGHTNESS_PCT] = int(self.preset.color.intensity * 100 / 255)
        if self.preset.color.white:
            attrs[ATTR_COLOR_MODE] = ColorMode.WHITE
        if self.preset.color.rainbow:
            attrs[ATTR_EFFECT] = EFFECT_RAINBOW
        return attrs
