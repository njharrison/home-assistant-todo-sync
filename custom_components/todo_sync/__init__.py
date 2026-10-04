from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import CONF_INTERVAL, CONF_LIST_A, CONF_LIST_B, DEFAULT_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


def _key(summary: str) -> str:
    return " ".join(summary.casefold().split())


def _state(item: dict[str, Any] | None) -> str | None:
    return None if item is None else item.get("status", "needs_action")


class TodoSync:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.entities = [
            entry.data[CONF_LIST_A],
            entry.data[CONF_LIST_B],
        ]
        self.interval = int(entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self.store: Store = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.baseline: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.unsubs: list = []
        self._debounce_task: asyncio.Task | None = None

    async def async_start(self) -> None:
        saved = await self.store.async_load()
        self.baseline = (saved or {}).get("baseline", {})

        @callback
        def changed(_event) -> None:
            # CalDAV and other external todo providers may update the entity state
            # before their item payload is readable. Debounce so we reconcile the
            # settled list rather than immediately reading stale item data.
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()
            self._debounce_task = self.hass.async_create_task(
                self._async_debounced_reconcile()
            )

        self.unsubs.append(async_track_state_change_event(self.hass, self.entities, changed))
        self.unsubs.append(
            async_track_time_interval(
                self.hass,
                lambda _now: self.hass.async_create_task(self.async_reconcile()),
                timedelta(seconds=self.interval),
            )
        )
        await self.async_reconcile()

    async def _async_debounced_reconcile(self) -> None:
        try:
            await asyncio.sleep(2)
            await self.async_reconcile()
        except asyncio.CancelledError:
            pass

    async def async_stop(self) -> None:
        for unsub in self.unsubs:
            unsub()
        self.unsubs.clear()
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

    async def _read(self, entity_id: str) -> dict[str, dict[str, Any]]:
        response = await self.hass.services.async_call(
            "todo",
            "get_items",
            {
                "entity_id": entity_id,
                "status": ["needs_action", "completed"],
            },
            blocking=True,
            return_response=True,
        )
        items = (response or {}).get(entity_id, {}).get("items", [])
        result: dict[str, dict[str, Any]] = {}
        for item in items:
            summary = (item.get("summary") or "").strip()
            if not summary:
                continue
            key = _key(summary)
            if key in result:
                _LOGGER.warning(
                    "Duplicate to-do summary %r in %s; To-do Sync uses summaries as identity",
                    summary,
                    entity_id,
                )
                continue
            result[key] = item
        return result

    async def _apply(
        self,
        entity_id: str,
        current: dict[str, Any] | None,
        desired: dict[str, Any] | None,
    ) -> None:
        if desired is None:
            if current is not None:
                await self.hass.services.async_call(
                    "todo",
                    "remove_item",
                    {"entity_id": entity_id, "item": current["uid"]},
                    blocking=True,
                )
            return

        if current is None:
            await self.hass.services.async_call(
                "todo",
                "add_item",
                {"entity_id": entity_id, "item": desired["summary"]},
                blocking=True,
            )
            # add_item creates needs_action. Set completed afterwards when required.
            if desired.get("status") == "completed":
                refreshed = await self._read(entity_id)
                created = refreshed.get(_key(desired["summary"]))
                if created:
                    await self.hass.services.async_call(
                        "todo",
                        "update_item",
                        {
                            "entity_id": entity_id,
                            "item": created["uid"],
                            "status": "completed",
                        },
                        blocking=True,
                    )
            return

        changes: dict[str, Any] = {"entity_id": entity_id, "item": current["uid"]}
        dirty = False
        if current.get("status") != desired.get("status"):
            changes["status"] = desired.get("status", "needs_action")
            dirty = True
        if current.get("summary") != desired.get("summary"):
            changes["rename"] = desired["summary"]
            dirty = True
        if dirty:
            await self.hass.services.async_call("todo", "update_item", changes, blocking=True)

    def _winner(
        self,
        key: str,
        snapshots: list[dict[str, dict[str, Any]]],
    ) -> dict[str, Any] | None:
        previous = self.baseline.get(key)
        previous_state = _state(previous)
        current = [snap.get(key) for snap in snapshots]
        states = [_state(item) for item in current]

        if not self.baseline:
            # First run: merge everything. If the same summary exists in both
            # places, prefer List A.
            return current[0] or current[1]

        changed = [i for i, state in enumerate(states) if state != previous_state]
        if not changed:
            return previous

        # If exactly one endpoint changed from the last agreed state, it wins.
        if len(changed) == 1:
            return current[changed[0]]

        # If changed endpoints agree, use their value.
        changed_states = {states[i] for i in changed}
        if len(changed_states) == 1:
            return current[changed[0]]

        # Concurrent conflict: List A wins.
        winner = 0
        _LOGGER.warning(
            "Conflicting changes for %r; choosing %s",
            (previous or current[winner] or {}).get("summary", key),
            self.entities[winner],
        )
        return current[winner]

    async def async_reconcile(self) -> None:
        if self.lock.locked():
            return
        async with self.lock:
            try:
                snapshots = [await self._read(entity) for entity in self.entities]
                keys = set(self.baseline)
                for snap in snapshots:
                    keys.update(snap)

                desired: dict[str, dict[str, Any]] = {}
                decisions: dict[str, dict[str, Any] | None] = {}
                for key in keys:
                    winner = self._winner(key, snapshots)
                    decisions[key] = winner
                    if winner is not None:
                        desired[key] = {
                            "summary": winner["summary"],
                            "status": winner.get("status", "needs_action"),
                        }

                for idx, entity in enumerate(self.entities):
                    for key in keys:
                        await self._apply(entity, snapshots[idx].get(key), decisions[key])

                self.baseline = desired
                await self.store.async_save({"baseline": self.baseline})
                _LOGGER.debug("To-do Sync reconciliation complete: %d items", len(desired))
            except Exception:
                _LOGGER.exception("To-do Sync reconciliation failed")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    sync = TodoSync(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sync

    if hass.is_running:
        await sync.async_start()
    else:
        async def started(_event) -> None:
            await sync.async_start()
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    sync: TodoSync = hass.data[DOMAIN].pop(entry.entry_id)
    await sync.async_stop()
    return True
