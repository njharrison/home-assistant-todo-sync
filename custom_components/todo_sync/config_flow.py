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
                return self.async_show_form(step_id="user", data_schema=self._schema(user_input), errors={"base": "lists_must_differ"})
            await self.async_set_unique_id("|".join(sorted(entities)))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=self._title(*entities), data=user_input)
        return self.async_show_form(step_id="user", data_schema=self._schema())

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            entities = [user_input[CONF_LIST_A], user_input[CONF_LIST_B]]
            if len(set(entities)) != 2:
                return self.async_show_form(step_id="reconfigure", data_schema=self._schema(user_input), errors={"base": "lists_must_differ"})
            return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(step_id="reconfigure", data_schema=self._schema(dict(entry.data)))

    def _title(self, a: str, b: str) -> str:
        sa, sb = self.hass.states.get(a), self.hass.states.get(b)
        return f"{sa.name if sa else a} ↔ {sb.name if sb else b}"

    @staticmethod
    def _schema(defaults=None):
        defaults = defaults or {}
        todo = selector.EntitySelector(selector.EntitySelectorConfig(domain="todo"))
        fields = {}
        key_a = vol.Required(CONF_LIST_A, default=defaults[CONF_LIST_A]) if CONF_LIST_A in defaults else vol.Required(CONF_LIST_A)
        key_b = vol.Required(CONF_LIST_B, default=defaults[CONF_LIST_B]) if CONF_LIST_B in defaults else vol.Required(CONF_LIST_B)
        fields[key_a] = todo
        fields[key_b] = todo
        fields[vol.Optional(CONF_INTERVAL, default=defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL))] = selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=300, step=5, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"))
        return vol.Schema(fields)
