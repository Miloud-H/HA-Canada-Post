import logging

from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from .const import DOMAIN, CONF_INCLUDE_ADS


_LOGGER = logging.getLogger(__name__)


# On rafraîchit les données toutes les heures
SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(hass, entry, async_add_entities):
    """Configuration des capteurs à partir du coordinator déjà créé."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    topic_id = entry.data.get("topic_id")

    async_add_entities([
        CanadaPostMailSensor(coordinator, topic_id, "transit"),
        CanadaPostMailSensor(coordinator, topic_id, "delivered")
    ])

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def update_listener(hass, entry):
    """Recharge l'intégration quand les options changent."""
    await hass.config_entries.async_reload(entry.entry_id)

class CanadaPostUpdateCoordinator(DataUpdateCoordinator):
    """Gère le polling de l'API Postes Canada."""
    def __init__(self, hass, api, topic_id):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

        self.api = api
        self.topic_id = topic_id

    async def _async_update_data(self):
        """Récupère les dernières données de courrier."""
        try:
            tokens = await self.api.get_tokens()
            acc = tokens.get("access_token")
            idt = tokens.get("id_token")

            if not acc or not idt:
                raise UpdateFailed("Tokens manquants")

            full_token = f"{acc}.{idt}"
            return await self.api.get_mail(full_token, self.topic_id)

        except Exception as err:
            _LOGGER.error("Erreur dans le coordinator : %s", err)
            raise UpdateFailed(f"Erreur communication: {err}")

class CanadaPostMailSensor(CoordinatorEntity, SensorEntity):
    """Représentation du courrier avec logique de basculement J+3."""

    def __init__(self, coordinator, topic_id, sensor_type):
        super().__init__(coordinator)
        self._topic_id = topic_id
        self._type = sensor_type # "transit" ou "delivered"
        
        type_label = "En chemin" if sensor_type == "transit" else "Livré"
        self._attr_name = f"Postes Canada {type_label}"
        self._attr_unique_id = f"cp_mymail_{topic_id}_{sensor_type}"

    def _process_mail(self):
        """Trie les courriers selon la règle métier déduite de l'APK."""
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
            for piece in result.get("Mailpieces", []):
                is_ad = piece.get("ServiceType") == 25
                start_date_str = piece.get("ActualStartDate") # Format YYYY-MM-DD

                if is_ad and not include_ads:
                    continue
                
                clean_date = start_date_str[:10] if start_date_str else ""
                
                try:
                    mail_date = datetime.strptime(clean_date, "%Y-%m-%d").date()
                    days_diff = (today - mail_date).days
                except Exception as e:
                    _LOGGER.warning("Erreur date sur un item: %s", start_date_str)
                    days_diff = 0

                # An ad sended more than 3 days -> Delivered
                # An ad sended less than 3 days -> Transit
                if is_ad:
                    if days_diff >= 3:
                        delivered_items.append(piece)
                    else:
                        transit_items.append(piece)
                else:
                    # Regular mail, 1 day to be delivered
                    if days_diff >= 1:
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
        items = []
        for piece in pieces:
            mailer = piece.get("Mailer", {})
            items.append({
                "expediteur": mailer.get("Name", {}).get("Fr", "Inconnu"),
                "logo": mailer.get("Logo", {}).get("Fr"),
                "date": piece.get("ActualStartDate"),
                "type": "Publicité" if piece.get("ServiceType") == 25 else "Lettre"
            })

        include_ads = self.coordinator.config_entry.options.get(
            CONF_INCLUDE_ADS, 
            self.coordinator.config_entry.data.get(CONF_INCLUDE_ADS, True)
        )

        return {
            "items": items,
            "count": len(items),
            "ads_included": include_ads,
            "last_check": datetime.now().isoformat()
        }