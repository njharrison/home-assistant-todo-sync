# Home Assistant To-do Sync

A custom Home Assistant integration that performs a two-way merge between pairs of `todo` entities.

Each config entry synchronises one pair. Add the integration repeatedly to sync as many Alexa, CalDAV, Local To-do or other Home Assistant to-do lists as you want.

## Example

- **List A:** Alexa Shopping
- **List B:** Radicale / Apple Reminders Shopping

The integration keeps a small persisted **last agreed state** internally. That lets it distinguish a real change on one endpoint from stale state on the other without requiring a third "master" list.

## What v0.2.0 syncs

- New items in either list
- Completed / reopened status in either direction
- Deletion/removal in either direction
- Periodic reconciliation (default 10 seconds)
- Debounced reconciliation after entity changes
- Persistent last-agreed state across Home Assistant restarts
- Multiple independent list pairs

Items are currently matched by a case-insensitive, whitespace-normalised summary. Avoid duplicate items with the same name. Rename handling is limited because external systems use different UIDs.

## Installation

### HACS custom repository

1. In HACS, add `https://github.com/njharrison/home-assistant-todo-sync` as a **Custom repository** of type **Integration**.
2. Install **To-do Sync**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration → To-do Sync**.
5. Choose List A and List B.
6. Repeat step 4 for every additional pair.

## Safety

The first reconciliation is deliberately additive: existing items from both lists are merged rather than treating absence as deletion.

## Conflict handling

Normally only one endpoint differs from the last agreed state, so that endpoint wins and its change is copied to the other. If both endpoints independently change the same item in incompatible ways before reconciliation, List A wins and a warning is logged.
