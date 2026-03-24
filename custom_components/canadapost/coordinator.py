import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

class CanadaPostUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, topic_id, config_entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.topic_id = topic_id
        self.config_entry = config_entry

    async def _async_update_data(self):
        try:
            tokens = await self.api.get_tokens()
            acc = tokens.get("access_token")
            idt = tokens.get("id_token")

            if not acc or not idt:
                raise UpdateFailed("Missing token")

            full_token = f"{acc}.{idt}"
            return await self.api.get_mail(full_token, self.topic_id)

        except Exception as err:
            _LOGGER.error("Error in coordinator: %s", err)
            raise UpdateFailed(f"Communication error: {err}")
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "Canada Post",
            "manufacturer": "Canada Post",
            "model": "My Mail",
        }