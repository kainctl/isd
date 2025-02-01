# Architecture

`InteractiveSystemd` is the main application.
It handles the synchronization among the child widgets, all global
keybindings and configuration loading.

The selection window is refreshed through `refresh_selection` calls:
- The `search_term` changes
- The `unit_to_state_dict` changes

The `unit_to_state_dict` is refreshed when:
- It is completely new initialized if the `mode` changes!
- When the `preview_and_selection_refresh_interval_sec` timer has passed
  - This will trigger a partial update to the current `relevant_units`.
    The option contains the prefix `selection` as this is what the _user_ sees.
    Internally, this refers to the `relevant_units` (selected + highlighted units).
- When the `full_refresh_interval_sec` timer has passed
  - This will add new units from the system to the `unit_to_state_dict` variable.
    But it will _not_ trigger a new search!
- Highlighted changes

The `preview_window` is refreshed when the `mode` or `units` variables of the
`PreviewArea` widget or the currently active tab changes!

A refresh is triggered from the main application through `refresh_preview`.
This function will enforce a refresh even if the `units` haven't changed.
This happens when one of the following states changes:
- Highlight
- Selection
- `unit_to_state_dict`

Or when the interval `preview_and_selection_refresh_interval_sec` is up.

Todo:
- Wrap all `systemctl` actions with a partial update to the `unit_to_state_dict`!
