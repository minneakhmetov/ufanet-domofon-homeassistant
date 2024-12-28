"""Platform for lock integration."""
from homeassistant.components.lock import LockEntity
from . import UfanetAPI

class UfanetLock(LockEntity):
    """Representation of a Ufanet Doorphone as a Lock."""
    # Lock platform implementation (from the canvas code)
