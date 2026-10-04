from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class TodoSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_abort(reason="test_complete")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional("test"): str,
                }
            ),
        )
