from homeassistant.components.lock import LockEntity


class MyLock(LockEntity):

    def unlock(self, **kwargs):
        """Unlock all or specified locks. A code to unlock the lock with may optionally be specified."""