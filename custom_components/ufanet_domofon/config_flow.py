"""Config flow for Ufanet Doorphone."""
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ufanet Doorphone."""
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Ufanet Doorphone", data=user_input)
        return self.async_show_form(step_id="user")
