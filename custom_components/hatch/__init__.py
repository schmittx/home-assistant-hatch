"""The Hatch integration."""
from __future__ import annotations

import datetime
import logging
from subprocess import PIPE

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_point_in_utc_time

from .api.const import DEFAULT_SAVE_ENABLED
from .const import (
    DEVICES,
    DOMAIN,
    ENTITIES,
    EXPIRATION_LISTENER,
    MANUFACTURER,
    MQTT_CONNECTION,
)

PLATFORMS = [
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SCENE,
    Platform.SENSOR,
    Platform.SWITCH,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    data = {}
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    async def setup_connection(arg):
        from awscrt.mqtt import Connection
        from .api import get_devices

        _LOGGER.debug(f"[{config_entry.title}] Updating credentials: {arg}")
        client_session = async_get_clientsession(hass)

        def disconnect():
            _LOGGER.debug(f"[{config_entry.title}] Disconnected")

        def resumed():
            _LOGGER.debug(f"[{config_entry.title}] Resumed")

        if MQTT_CONNECTION in data.keys():
            mqtt_connection: Connection = data[MQTT_CONNECTION]
            try:
                mqtt_connection.disconnect().result()
            except Exception as error:
                _LOGGER.debug(
                    f"[{config_entry.title}] mqtt_connection disconnect failed during reconnect: {error}"
                )

        _, mqtt_connection, devices, expiration_time = await get_devices(
            email=email,
            password=password,
            client_session=client_session,
            on_connection_interrupted=disconnect,
            on_connection_resumed=resumed,
            save_response_enabled=DEFAULT_SAVE_ENABLED,
        )
        _LOGGER.debug(
            f"[{config_entry.title}] Credentials expire at: {datetime.datetime.fromtimestamp(expiration_time)}"
        )
        data[MQTT_CONNECTION] = mqtt_connection

        if ENTITIES in list(data.keys()):
            _LOGGER.debug(
                f"[{config_entry.title}] Updating existing entities: {data[ENTITIES]}"
            )
            for device in devices:
                _LOGGER.debug(
                    f"[{config_entry.title}] Looping new devices: {device.info.thing_name}, {device.info.name}"
                )
                for entity in data[ENTITIES]:
                    _LOGGER.debug(
                        f"[{config_entry.title}] Looping existing entities: {entity.unique_id}, {entity.name}"
                    )
                    if device.info.mac_address in entity.unique_id:
                        _LOGGER.debug(f"[{config_entry.title}] Matched and replacing entity's device")
                        entity.replace_device(device)
        else:
            data[DEVICES] = devices
            data[ENTITIES] = []

        data[EXPIRATION_LISTENER] = async_track_point_in_utc_time(
            hass,
            setup_connection,
            datetime.datetime.fromtimestamp(expiration_time - 60),
        )

    await setup_connection("Initial setup")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = data

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"[{config_entry.title}] Unload entry")
    from awscrt.mqtt import Connection

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        mqtt_connection: Connection = hass.data[DOMAIN][config_entry.entry_id][MQTT_CONNECTION]
        try:
            mqtt_connection.disconnect().result()
        except Exception as error:
            _LOGGER.debug(f"[{config_entry.title}] mqtt_connection disconnect failed during unload: {error}")
        hass.data[DOMAIN][config_entry.entry_id][EXPIRATION_LISTENER]()
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


class HatchEntity(Entity):
    """Representation of a Hatch entity."""

    from .api.device import Device as HatchDevice

    translation_key: str | None = "all"

    def __init__(
        self,
        device: HatchDevice,
        entity_description: EntityDescription=None,
    ) -> None:
        """Initialize device."""
        self.device = device
        self.device.register_callback(self._update_local_state)
        self.entity_description = entity_description

    def replace_device(self, device) -> None:
        self.device.remove_callback(self._update_local_state)
        self.device = device
        self.device.register_callback(self._update_local_state)

    async def async_added_to_hass(self) -> None:
        if self.device.is_connected:
            self._update_local_state()

    def _update_local_state(self) -> None:
        if self.platform is None:
            return
        _LOGGER.debug(f"[{self.entity_id}] Updating Home Assistant state")
        self.schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.device.is_connected

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes.

        Implemented by platform classes.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.info.mac_address)},
            manufacturer=MANUFACTURER,
            model=self.device.info.model,
            name=self.device.info.name,
            sw_version=self.device.firmware_version,
            hw_version=self.device.info.hardware_version,
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        name = self.device.info.name
        if description := self.entity_description.name:
            return f"{name} {description}"
        return name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        unique_id = self.device.info.mac_address
        if key := self.entity_description.key:
            return f"{unique_id}-{key}"
        return unique_id
