import logging

from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_INCLUDE_ADS
from .coordinator import CanadaPostUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    topic_id = entry.data.get("topic_id")

    async_add_entities([
        CanadaPostMailSensor(coordinator, topic_id, "transit"),
        CanadaPostMailSensor(coordinator, topic_id, "delivered"),
        CanadaPostUpdatedSensor(coordinator, topic_id)
    ])

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def update_listener(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

class CanadaPostMailSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, topic_id, sensor_type):
        super().__init__(coordinator)
        self._topic_id = topic_id
        self._type = sensor_type

        self._attr_device_info = coordinator.device_info
        
        self._attr_translation_key = sensor_type
        self._attr_unique_id = f"cp_v2_{topic_id}_{sensor_type}"
        
        if sensor_type == "transit":
            self._attr_icon = "mdi:truck-delivery-outline"
        elif sensor_type == "delivered":
            self._attr_icon = "mdi:package-variant-closed-check"
        else:
            self._attr_icon = "mdi:mailbox-outline"

    def _process_mail(self):
        data = self.coordinator.data
        if not data or "Results" not in data:
            return []

        transit_items = []
        delivered_items = []
        today = datetime.now().date()

        include_ads = self.coordinator.config_entry.options.get(
            CONF_INCLUDE_ADS, 
            self.coordinator.config_entry.data.get(CONF_INCLUDE_ADS, True)
        )

        for result in data.get("Results", []):
            date_str = result.get("Date", "")
            try:
                delivery_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                delivery_date = today

            for piece in result.get("Mailpieces", []):
                piece["_calculated_delivery_date"] = date_str

                is_ad = piece.get("ServiceType") == 25
                if is_ad and not include_ads:
                    continue

                if delivery_date <= today:
                    delivered_items.append(piece)
                else:
                    transit_items.append(piece)

        return transit_items if self._type == "transit" else delivered_items

    @property
    def native_value(self):
        return len(self._process_mail())

    @property
    def extra_state_attributes(self):
        pieces = self._process_mail()
        
        packages = []
        for piece in pieces:
            mailer = piece.get("Mailer", {})
            d_date = piece.get("_calculated_delivery_date", "Unknown")
            is_ad = piece.get("ServiceType") == 25
            
            packages.append({
                "sender": mailer.get("Name", {}).get("En", "Unknown"),
                "image_url": mailer.get("Logo", {}).get("En"),
                "estimated_delivery": d_date,
                "tracking_number": piece.get("SOMIdentifier", "N/A"),
                "tracking_description": "Advertisement" if is_ad else "Letter",
                "tracking_status": "Delivered" if self._type == "delivered" else "In transit"
            })

        include_ads = self.coordinator.config_entry.options.get(
            CONF_INCLUDE_ADS, 
            self.coordinator.config_entry.data.get(CONF_INCLUDE_ADS, True)
        )

        attributes = {
            "packages": packages,
            "count": len(packages),
            "ads_included": include_ads,
            "integration_id": DOMAIN,
            "last_check": dt_util.now().isoformat(),
        }

        if packages and packages[0].get("image_url"):
            attributes["image_url"] = packages[0]["image_url"]

        return attributes
    
class CanadaPostUpdatedSensor(CanadaPostMailSensor):    
    def __init__(self, coordinator, topic_id):
        super().__init__(coordinator, topic_id, "mail_updated")        
        self._type = "delivered"        
        self._attr_unique_id = f"cp_mail_updated_compat_{topic_id}"

    @property
    def native_value(self):
        return len(self._process_mail())

    @property
    def extra_state_attributes(self):
        return super().extra_state_attributes