"""Hatch integration."""
from __future__ import annotations

from homeassistant.util.color import COLORS, RGBColor


def rgb_distance_between(color_1: RGBColor, color_2: RGBColor) -> float:
    return ((color_1.r-color_2.r)**2) + ((color_1.g-color_2.g)**2) + ((color_1.b-color_2.b)**2)


def rgb_to_name(value: RGBColor) -> str | None:
    closest_distance: float | None  = None
    closest_name: str | None = None

    for color_name, color_rgb in COLORS.items():
        distance = rgb_distance_between(color_rgb, value)
        if closest_distance is None or distance < closest_distance:
            closest_distance = distance
            closest_name = color_name
    return closest_name
