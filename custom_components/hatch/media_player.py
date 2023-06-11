"""Support for Hatch media player entities."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityDescription,
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchEntity
from .const import DOMAIN, DEVICES, ENTITIES, MEDIA_IMAGE_DIRECTORY

@dataclass
class HatchMediaPlayerEntityDescription(MediaPlayerEntityDescription):
    """Class to describe a Hatch media player entity."""


MEDIA_PLAYER_DESCRIPTIONS: list[HatchMediaPlayerEntityDescription] = [
    HatchMediaPlayerEntityDescription(
        key="sound_machine",
        name="Sound Machine",
        device_class=MediaPlayerDeviceClass.SPEAKER,
    ),
]


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hatch media player entity based on a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    devices = entry[DEVICES]
    entities: list[HatchMediaPlayerEntity] = []

    for device in devices:
        for description in MEDIA_PLAYER_DESCRIPTIONS:
            if hasattr(device, description.key):
                entities.append(
                    HatchMediaPlayerEntity(
                        device=device,
                        entity_description=description,
                    )
                )
    entry[ENTITIES].extend(entities)

    async_add_entities(entities)


class HatchMediaPlayerEntity(HatchEntity, MediaPlayerEntity):
    """Representation of a Hatch media player entity."""

    entity_description: HatchMediaPlayerEntityDescription

    @property
    def state(self) -> str | None:
        """State of the player."""
        if self.device.is_audio_on:
            return STATE_ON
        return STATE_OFF

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        return self.device.audio.volume / 100

    @property
    def media_content_id(self) -> str | None:
        """Content ID of current playing media."""
        return self.device.audio.track

    @property
    def media_content_type(self) -> str | None:
        """Content type of current playing media."""
        return MediaType.MUSIC

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        return self.device.audio.name

    @property
    def sound_mode(self) -> str | None:
        """Name of the current sound mode."""
        return self.device.audio.name

    @property
    def sound_mode_list(self) -> list[str] | None:
        """List of available sound modes."""
        return sorted(self.device.audio.list)

    @property
    def supported_features(self) -> int:
        """Flag media player features that are supported."""
        return (
            MediaPlayerEntityFeature.SELECT_SOUND_MODE |
            MediaPlayerEntityFeature.TURN_OFF |
            MediaPlayerEntityFeature.TURN_ON |
            MediaPlayerEntityFeature.VOLUME_SET |
            MediaPlayerEntityFeature.VOLUME_STEP
        )

    def turn_on(self):
        """Turn the media player on."""
        self.device.turn_on_audio()

    def turn_off(self):
        """Turn the media player off."""
        self.device.turn_off_audio()

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self.device.set_audio_volume(int(volume * 100))

    def select_sound_mode(self, sound_mode):
        """Select sound mode."""
        self.device.set_audio_track(sound_mode)

    @property
    def media_image_hash(self):
        """Hash value for media image."""
        if self.state == STATE_ON:
            return self.device.audio.image
        return None

    async def async_get_media_image(self):
        """Fetch media image of current playing image."""
        if self.media_image_hash:
            path =f"{MEDIA_IMAGE_DIRECTORY}/{self.media_image_hash}.png"
            artwork = open(path, "rb").read()
            return artwork, "image/png"
        return None, None
