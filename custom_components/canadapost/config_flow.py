import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import CanadaPostAPI
from .const import DOMAIN, CONF_INCLUDE_ADS

_LOGGER = logging.getLogger(__name__)

class CanadaPostConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                api = CanadaPostAPI(
                    self.hass, 
                    user_input["username"], 
                    user_input["password"]
                )
                
                tokens = await api.get_tokens()
                access_token = tokens["access_token"]
                id_token = tokens["id_token"]

                topic_id = await api.discover_topic_id(id_token)

                if topic_id:
                    return self.async_create_entry(
                        title=user_input["username"],
                        data={
                            "username": user_input["username"],
                            "password": user_input["password"],
                            "topic_id": topic_id
                        },
                        options={
                            CONF_INCLUDE_ADS: user_input.get(CONF_INCLUDE_ADS, True)
                        }
                    )
                
                errors["base"] = "cannot_discover_id"

            except Exception as err:
                _LOGGER.error("Error while login : %s", err)
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional(CONF_INCLUDE_ADS, default=True): bool,
            }),
            errors=errors,
        )
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CanadaPostOptionsFlowHandler(config_entry)

class CanadaPostOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        super().__init__(config_entry)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_val = self.config_entry.options.get(
            CONF_INCLUDE_ADS, 
            self.config_entry.data.get(CONF_INCLUDE_ADS, True)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_INCLUDE_ADS, default=current_val): bool,
            }),
        )