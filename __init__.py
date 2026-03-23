import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import CanadaPostAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'entrée via l'UI."""
    username = entry.data.get("username")
    password = entry.data.get("password")
    topic_id = entry.data.get("topic_id")

    api = CanadaPostAPI(hass, username, password)

    # 2. On importe et on initialise TON Coordinator (celui de sensor.py)
    # On fait l'import ici pour éviter les imports circulaires
    from .sensor import CanadaPostUpdateCoordinator
    
    coordinator = CanadaPostUpdateCoordinator(hass, api, topic_id)

    # 3. Premier rafraîchissement au démarrage
    # Si l'API est down ou le token échoue, on lève ConfigEntryNotReady
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Erreur lors du premier rafraîchissement : %s", err)
        raise ConfigEntryNotReady(f"Connexion à Postes Canada impossible : {err}")

    # 4. On stocke le coordinator pour que sensor.py puisse le récupérer
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 5. On lance les capteurs
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Suppression de l'intégration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok