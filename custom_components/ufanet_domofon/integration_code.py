import logging
import requests
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.components.lock import LockEntity

DOMAIN = "ufanet_domofon"
_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://dom.ufanet.ru"
LOGIN_ENDPOINT = f"{API_BASE_URL}/login/"
GET_DOORPHONES_ENDPOINT = f"{API_BASE_URL}/api/v0/skud/shared"
OPEN_DOORPHONE_ENDPOINT = f"{API_BASE_URL}/api/v0/skud/shared/{{id}}/open/"

class UfanetAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.cookie = None

    def authenticate(self):
        """Authenticates with the API and retrieves the cookie."""
        data = {
            "next": "/office/skud/",
            "contract": self.username,
            "password": self.password
        }
        response = self.session.post(LOGIN_ENDPOINT, data=data)
        if response.status_code == 200:
            self.cookie = self.session.cookies.get_dict()
            _LOGGER.debug("Authentication successful, cookies saved.")
        else:
            _LOGGER.error("Authentication failed. Status code: %s", response.status_code)
            raise Exception("Authentication failed")

    def get_doorphones(self):
        """Gets the list of doorphones."""
        if not self.cookie:
            self.authenticate()
        response = self.session.get(GET_DOORPHONES_ENDPOINT, cookies=self.cookie)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            _LOGGER.warning("Cookie expired, re-authenticating.")
            self.authenticate()
            return self.get_doorphones()
        else:
            _LOGGER.error("Failed to fetch doorphones. Status code: %s", response.status_code)
            raise Exception("Failed to fetch doorphones")

    def open_doorphone(self, doorphone_id):
        """Opens a specific doorphone."""
        if not self.cookie:
            self.authenticate()
        url = OPEN_DOORPHONE_ENDPOINT.format(id=doorphone_id)
        response = self.session.get(url, cookies=self.cookie)
        if response.status_code == 200:
            return response.json().get("result", False)
        elif response.status_code == 401:
            _LOGGER.warning("Cookie expired, re-authenticating.")
            self.authenticate()
            return self.open_doorphone(doorphone_id)
        else:
            _LOGGER.error("Failed to open doorphone. Status code: %s", response.status_code)
            raise Exception("Failed to open doorphone")

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration using YAML (if applicable)."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    api = UfanetAPI(username, password)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=api.get_doorphones,
        update_interval=timedelta(minutes=10),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator
    }

    await coordinator.async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, ["lock"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, ["lock"])

class UfanetLock(LockEntity):
    """Representation of a Ufanet Doorphone as a Lock."""

    def __init__(self, api, doorphone):
        self._api = api
        self._doorphone = doorphone
        self._name = doorphone.get("string_view", "Unknown Doorphone")
        self._id = doorphone["id"]

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"ufanet_doorphone_{self._id}"

    @property
    def is_locked(self):
        """Doorphones are stateless, always return False."""
        return False

    def unlock(self, **kwargs):
        """Handle the unlock action to open the doorphone."""
        success = self._api.open_doorphone(self._id)
        if success:
            _LOGGER.info("Doorphone %s opened successfully.", self._name)
        else:
            _LOGGER.error("Failed to open doorphone %s.", self._name)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the lock platform."""
    entry_id = discovery_info["entry_id"]
    api = hass.data[DOMAIN][entry_id]["api"]
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]

    doorphones = coordinator.data
    locks = [UfanetLock(api, doorphone) for doorphone in doorphones]
    async_add_entities(locks)
