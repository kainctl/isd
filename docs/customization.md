# Customization

As eluded to in the [Getting Started section](./index.md),
`isd` is _very_ configurable.
Almost _all_ keybindings and commands are configurable!
During start-up `isd` will read a configuration file and load those settings.

By default, the configuration is read from `~/.config/isd/config.yaml`[^1].
Though you can also simply open the file from _within_ `isd` by running the
`Open Config` command (++alt+o++ by default).
However, you will _have_ to restart `isd` for the changes to take effect!

[^1]: More precisely from `$XDG_CONFIG_DIR/isd` but for most users, it will
default to the path above.

## Configuration Options

!!! warning

    Do _not_ manually create the file!
    Open `isd` and run the `Open Config` command.
    It will create a default configuration file and open it with
    your configured editor.

The following collapsed document shows the _entire_ default configuration:

??? "Default `config.yaml`"

    ```yaml

    --8<-- "docs/config/isd/config.yaml"

    ```

To not get too bored by the wall 🧱 of text, let's have a look
at the different options individually.
As smaller walls 🧱 of text... Though, I don't know how exciting
these section will be 😅.
Some section will contain more context or additional information.

Just jump to the sections that sound interesting:

<!--toc:start-->
- [Editing The Configuration With Editor Support](#editing-the-configuration-with-editor-support)
- [Startup Mode](#startup-mode)
- [Preview And Selection Refresh Interval](#preview-and-selection-refresh-interval)
- [Full Refresh Interval](#full-refresh-interval)
- [Input Caching](#input-caching)
- [Update Throttling](#update-throttling)
- [Editor](#editor)
- [Default Pager](#default-pager)
- [Journal Pager](#journal-pager)
- [Journal Pager Arguments](#journal-pager-arguments)
- [Theme](#theme)
- [Generic Keybindings](#generic-keybindings)
- [Selection Keybindings](#selection-keybindings)
- [Preview Keybindings](#preview-keybindings)
- [`systemctl` Commands](#systemctl-commands)
- [Pager Arguments](#pager-arguments)
- [Journal Pager Arguments](#journal-pager-arguments)
- [Maximum Preview Lines](#maximum-preview-lines)
<!--toc:end-->



### Editing The Configuration With Editor Support

{{ config_block(0) }}

As the [YAML] comments indicate, the `isd` configuration file supports
auto-completion and input validation from _within_ the editor
_without_ having to start `isd`
or reading error 🐛 messages! If this does not work in your editor out-of-the-box,
checkout the
[yaml-language-server documentation](https://github.com/redhat-developer/yaml-language-server).

### Startup Mode

{{ config_block(1) }}

⬆️

### Preview And Selection Refresh Interval

{{ config_block(2) }}

This options is mainly relevant for the _auto-refresh_
feature from `isd`.
With these fixed interval updates, the unit state (`○`) and output of the `Status` preview
is kept in sync with the system state _without_ any user input.
The value should not be set too low, in order to avoid spamming too many[^2]
sub-processes.

[^2]: Although, the code only applies partial updates to the selected units.
So even fairly low values should not cause too many issues.

### Full Refresh Interval

{{ config_block(3) }}

Similar to [Preview And Selection Refresh Interval](#preview-and-selection-refresh-interval) but more
_aggressive_ as it updates all and previously untracked units.

### Input Caching

{{ config_block(4) }}

Having caching enabled by default might be the most _controversial_ 💣 preset.
The idea is that if you have opened `isd` to search for a specific unit,
you are likely to search for the same unit again when you re-open `isd`.
And, if not, then you can quickly clear the search input with ++ctrl+backspace++
or disable this option.

### Update Throttling

{{ config_block(5) }}

The preset is fairly low for the most responsive experience.
Though, it can be increased to improve performance.
Please raise an issue and let me know your specs/number of units
to improve on it!

### Editor

{{ config_block(6) }}

The `auto` logic, searches for an editor exactly like `systemctl`:

- <https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#%24SYSTEMD_EDITOR> 

It is highly recommended to either set the environment
variables `$EDITOR` or `$VISUAL` for a more consistent
Linux Terminal experience across different applications.

For the security implications of setting this variable see
the [systemctl edit security discussion](security.md/#issues-with-systemctl-edit).

### Default Pager

{{ config_block(7) }}

The `auto` logic, searches for and editor exactly like `systemctl` 
_WITH_ `SYSTEMD_PAGERSECURE=0`:

- <https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#%24SYSTEMD_PAGER>

For the security implications of setting this variable see
the [pagers discussion](security.md/#pagers).

### Journal Pager

{{ config_block(8) }}

`auto` behaves _exactly_ like [Default Pager](#default-pager).
Though, it is more common to set this value to a different pager
like [lnav](https://lnav.org/).

### Journal Pager Arguments

{{ config_block(9) }}

These values can be adjusted according to personal preference.

### Theme

{{ config_block(10) }}

`isd` comes with a few default themes.
You can _temporarily_ view the themes via the `Change theme` command.
But to persist the changes you _must_ update the configuration file.

<!-- If you are familiar with theming your terminal via -->
<!-- [ansi escape codes](https://github.com/tinted-theming/home) -->
<!-- you --> 

### Generic Keybindings

{{ config_block(11) }}

Generic keybindings are enabled _globally_ and are not limited to a specific widget.
For example, `"ctrl+backspace"` will clear the search input and focus the search input
widget, even if the selection or preview window is currently focused.

If a focused widget already defines the same keybinding, the generic keybinding
will have a lower priority. For example, `right` would switch to the next preview window
when the selection window is focused but it would move the cursor to the right if the
preview log output is focused.

For the key format, see: <https://posting.sh/guide/keymap/#key-format>

### Selection Keybindings

{{ config_block(12) }}

Keybindings specific to the selection widget.

### Preview Keybindings

{{ config_block(13) }}

Keybindings specific for the preview _log_ window.
Note that the preview tab header is _different_ to the preview _log_ window.

### `systemctl` Commands

{{ config_block(14) }}

This allows you to configure the `systemctl` commands and keybindings.
It is important to note that the `command` key may contain spaces (like `edit --runtime`)
but _does not_ include the prefix `systemctl`, since this will always be inserted.
The full command name (for example `systemctl start`) is used for the `description` which
will be shown in the command palette.

For the security implications of setting these variables see
the [shell injection section](security.md/#shell-injection).

### Pager Arguments

{{ config_block(15) }}

If you have to customize the pager arguments for a common pager,
please open an issue!

### Journal Pager Arguments

{{ config_block(16) }}

If you have to customize the pager arguments for a common pager,
please open an issue!

### Maximum Preview Lines

{{ config_block(17) }}

This value can mainly be configured if opening the journal preview
window takes too long. Though, it should usually not be required
to lower this value.

To view the entire output, open the output in the pager.

