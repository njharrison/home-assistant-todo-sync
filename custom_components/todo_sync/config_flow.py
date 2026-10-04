from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import CONF_INTERVAL, CONF_LIST_A, CONF_LIST_B, DEFAULT_INTERVAL, DOMAIN


class TodoSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            entities = [user_input[CONF_LIST_A], user_input[CONF_LIST_B]]
            if len(set(entities)) != 2:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._schema(user_input),
                    errors={"base": "lists_must_differ"},
                )

            await self.async_set_unique_id("|".join(sorted(entities)))
            self._abort_if_unique_id_configured()
            a_name = self.hass.states.get(entities[0])
            b_name = self.hass.states.get(entities[1])
            a_title = a_name.name if a_name else entities[0]
            b_title = b_name.name if b_name else entities[1]
            return self.async_create_entry(
                title=f"{a_title} ↔ {b_title}", data=user_input
            )

        return self.async_show_form(step_id="user", data_schema=self._schema())

    @staticmethod
    def _schema(defaults=None):
        defaults = defaults or {}
        todo_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="todo")
        )
        return vol.Schema(
            {
                vol.Required(CONF_LIST_A, default=defaults.get(CONF_LIST_A)): todo_selector,
                vol.Required(CONF_LIST_B, default=defaults.get(CONF_LIST_B)): todo_selector,
                vol.Optional(
                    CONF_INTERVAL,
                    default=defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=300,
                        step=5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )
