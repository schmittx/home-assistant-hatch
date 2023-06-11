"""Adds config flow for Hatch integration."""
import logging

import voluptuous as vol
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
)
import homeassistant.helpers.config_validation as cv

from . import _setup_requirements
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HatchConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def __init__(self):
        """Initialize."""
        _setup_requirements()
        self.api = None
        self.user_input = {}

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:

            self.user_input[CONF_EMAIL] = user_input[CONF_EMAIL]
            self.user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]

            try:
                from .api import Hatch
                self.api = Hatch()
                token = await self.api.login(email=user_input[CONF_EMAIL], password=user_input[CONF_PASSWORD])
                response = await self.api.member(auth_token=token)

                await self.async_set_unique_id(response["member"]["id"])
                self._abort_if_unique_id_configured()

            except ConfigEntryAuthFailed:
                errors["base"] = "auth"

            finally:
                if self.api is not None:
                    await self.api.cleanup_client_session()

            return self.async_create_entry(
                title=f'{response["member"]["firstName"]} {response["member"]["lastName"]}',
                data=self.user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )
