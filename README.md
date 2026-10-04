# Home Assistant To-do Sync

A custom Home Assistant integration that keeps three `todo` entities synchronised.

It is designed for setups where Home Assistant is the bridge between two external task systems. The middle/master list remains a normal editable Home Assistant to-do list, while a small persisted snapshot records the last agreed state so changes can be reconciled in either direction.

## Nick's setup

- **Master:** `todo.shopping_list` (Home Assistant Shopping List)
- **List A:** `todo.njharrison_gmail_com_shopping_list` (Alexa)
- **List B:** `todo.shopping_2` (Radicale / Apple Reminders)

## What v0.1.0 syncs

- New items in any list
- Completed / reopened status in either direction
- Deletion/removal in either direction
- Changes made directly to the master list
- Periodic reconciliation (default 10 seconds)
- Persistent last-agreed state across Home Assistant restarts

Items are matched by a case-insensitive, whitespace-normalised summary. Avoid duplicate items with the same name. Rename handling is limited in v0.1 because external systems use different UIDs.

## Installation

### HACS custom repository

1. In HACS, add `https://github.com/njharrison/home-assistant-todo-sync` as a **Custom repository** of type **Integration**.
2. Install **To-do Sync**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → To-do Sync**.
5. Choose the three to-do entities.

### Manual

Copy `custom_components/todo_sync` into your Home Assistant `config/custom_components` directory and restart Home Assistant.

## Conflict handling

The integration stores the last agreed state. If one list changes, that change is propagated to the other two. If two lists independently make conflicting changes before a reconciliation, the master list wins when it is one of the changed lists; otherwise List A wins.

## Safety

The first reconciliation is deliberately additive: existing items from all three lists are merged rather than treating absence as deletion.
