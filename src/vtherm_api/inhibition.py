"""Inhibition facade types (issue #2087)."""

from homeassistant.exceptions import HomeAssistantError


class InhibitionNotStartedError(HomeAssistantError):
    """The targeted VTherm has not restored its inhibition state at startup yet.

    Raised by ``set_inhibition`` / ``unset_inhibition`` before the VTherm
    startup restore. Nothing was changed: call again once
    ``VThermAPI.is_inhibition_started`` returns True.
    """
