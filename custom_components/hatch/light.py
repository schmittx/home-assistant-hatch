"""Support for Hatch light entities."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ColorMode,
    LightEntity,
    LightEntityDescription,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.color as color_util

from . import HatchEntity
from .const import DOMAIN, DEVICES, EFFECT_RAINBOW, ENTITIES

@dataclass
class HatchLightEntityDescription(LightEntityDescription):
    """Class to describe a Hatch light entity."""

LIGHT_DESCRIPTIONS: list[HatchLightEntityDescription] = [
    HatchLightEntityDescription(
        key="nightlight",
        name="Nightlight",
    ),
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch light entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchLightEntity] = []

    for device in devices:
        for description in LIGHT_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchLightEntity(
                        device=device,
                        entity_description=description,
                    )
                )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchLightEntity(HatchEntity, LightEntity):
    """Representation of a Hatch light entity."""

    entity_description: HatchLightEntityDescription

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return bool(self.device.is_device_on and self.device.is_light_on)

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return self.device.color.intensity

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        return color_util.color_RGB_to_hs(
            self.device.color.red,
            self.device.color.green,
            self.device.color.blue,
        )

    @property
    def color_mode(self) -> str:
        """Return the color mode of the light."""
        if self.device.color.rainbow:
            return ColorMode.BRIGHTNESS
        elif self.device.color.white:
            return ColorMode.WHITE
        return ColorMode.HS

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        return [EFFECT_RAINBOW]

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if self.device.color.rainbow:
            return EFFECT_RAINBOW
        return None

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return LightEntityFeature.EFFECT

    @property
    def supported_color_modes(self) -> set[str]:
        """Flag supported color modes."""
        return set([ColorMode.HS, ColorMode.WHITE])

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        r, g, b, i, white, rainbow = None, None, None, None, None, None

        if ATTR_BRIGHTNESS in kwargs:
            i = kwargs[ATTR_BRIGHTNESS]
            _LOGGER.debug(f"Found ATTR_BRIGHTNESS in kwargs, got i: {i}")

        if ATTR_HS_COLOR in kwargs:
            h, s = kwargs[ATTR_HS_COLOR]
            r, g, b = color_util.color_hs_to_RGB(h, s)
            rainbow = False
            white = False
            _LOGGER.debug(f"Found ATTR_HS_COLOR in kwargs, got r: {r}, g: {g}, b: {b} from h: {h}, s: {s}")

        if ATTR_WHITE in kwargs:
            i = kwargs[ATTR_WHITE]
            rainbow = False
            white = True
            _LOGGER.debug(f"Found ATTR_WHITE in kwargs, got i: {i}")

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            if effect == EFFECT_RAINBOW:
                r, g, b = 0, 0, 0
                rainbow = True
                white = False
                _LOGGER.debug(f"Found ATTR_EFFECT in kwargs, got effect: {effect}")

        self.device.turn_on_light(
            red=r,
            green=g,
            blue=b,
            intensity=i,
            white=white,
            rainbow=rainbow,
        )

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self.device.turn_off_light()
