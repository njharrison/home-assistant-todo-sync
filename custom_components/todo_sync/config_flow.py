from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import CONF_INTERVAL, CONF_LIST_A, CONF_LIST_B, DEFAULT_INTERVAL, DOMAIN


class TodoSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
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

            return self.async_create_entry(
                title=self._title(entities[0], entities[1]),
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=self._schema())

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ):
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            entities = [user_input[CONF_LIST_A], user_input[CONF_LIST_B]]
            if len(set(entities)) != 2:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._schema(user_input),
                    errors={"base": "lists_must_differ"},
                )

            new_unique_id = "|".join(sorted(entities))
            # Allow the pair itself to be changed while preventing collision with
            # another existing To-do Sync entry.
            for other in self.hass.config_entries.async_entries(DOMAIN):
                if other.entry_id != entry.entry_id and other.unique_id == new_unique_id:
                    return self.async_show_form(
                        step_id="reconfigure",
                        data_schema=self._schema(user_input),
                        errors={"base": "already_configured"},
                    )

            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=new_unique_id,
                title=self._title(entities[0], entities[1]),
            )
            return self.async_update_reload_and_abort(
                entry,
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(dict(entry.data)),
        )

    def _title(self, list_a: str, list_b: str) -> str:
        a_state = self.hass.states.get(list_a)
        b_state = self.hass.states.get(list_b)
        a_title = a_state.name if a_state else list_a
        b_title = b_state.name if b_state else list_b
        return f"{a_title} ↔ {b_title}"

    @staticmethod
    def _schema(defaults: dict[str, Any] | None = None):
        defaults = defaults or {}
        todo_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="todo")
        )

        schema: dict[Any, Any] = {}
        if defaults.get(CONF_LIST_A):
            schema[vol.Required(CONF_LIST_A, default=defaults[CONF_LIST_A])] = todo_selector
        else:
            schema[vol.Required(CONF_LIST_A)] = todo_selector

        if defaults.get(CONF_LIST_B):
            schema[vol.Required(CONF_LIST_B, default=defaults[CONF_LIST_B])] = todo_selector
        else:
            schema[vol.Required(CONF_LIST_B)] = todo_selector

        schema[
            vol.Optional(
                CONF_INTERVAL,
                default=defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5,
                max=300,
                step=5,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        )
        return vol.Schema(schema)
