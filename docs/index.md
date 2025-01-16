# Getting Started

--8<-- "README.md:tagline"

## Short Motivation

!!! note

    If you prefer an example terminal recording over text,
    [jump to the next section](#working-with-isd).

If you ever became frustrated while typing:

- `systemctl start --user unit-A.service` (manually starting a unit ⬆️)
- `systemctl status --user unit-A.service` (seeing that it failed ❌)
- `journalctl -xe --user -u unit-A.service` (checking the logs 🔬)
- `systemctl edit --user unit-A.service` (updating the unit 🧑‍🔬)
- `systemctl start --user unit-A.service` (starting it again ⬆️)
- `systemctl status --user unit-A.service` (checking the logs _again_ 🔬)
- And repeat 🔁

This tool is for you!

But `isd` is not only designed for `systemd` power-users!
`isd` lowers the bar to interact with `systemd` units and provides a unified
interface that only shows _relevant_ information and commands.
If you only ever run `systemctl status <unit>`, then `isd` is _might still_ be for you,
since `isd` will auto-refresh the output.

If you are interested, read on and take a look at the [recorded terminal session](#working-with-isd).

## Installation

`isd` can currently be installed in three different ways:

- As an [AppImage], via
- [nix], or via
- [uv].

=== "AppImage"

    An [AppImage] is a single self-containing _executable_, similar to a Windows
    `.exe` and MacOS `.dmg` file. This should make it easy to run `isd`
    on _any_ Linux distribution and on remote servers where you do
    not have elevated privileges.

    _Manual installation_:

    First, download the `.AppImage` file from:

    - <{{config['repo_url']}}/releases/latest>
    
    Then make the file executable as
    mentioned in the [AppImage documentation](https://docs.appimage.org/introduction/quickstart.html#ref-quickstart)
    and run the application.

    _Managed installation_:

    Or manage the `.AppImage` via [AppImageLauncher](https://assassinate-you.net/tags/appimagelauncher/)
    for better desktop integration support (application icon & entry) and in-app
    update functionality.

    !!! warning

        If you have `nix` installed, this `AppImage` will _not_ work!
        Either use the `nix` or `uv` installation instructions!

=== "nix"

    `isd` is developed with a reproducible [nix] environment and build as a [nix] package.
    This is my personal preference to install `isd` but it is a higher barrier compared to the `.AppImage`.
    To install [nix] with sensible default options, use the [`nix-installer`](https://github.com/DeterminateSystems/nix-installer)
    from [determinate.systems](https://determinate.systems/).

    Then, to _try out_ `isd`, simply run `nix run {{config['repo_url']}}`.

    To install `isd`, add it to your packages list:

    ```nix
    # flake.nix
    {

        # [...]
        inputs.isd.url = "{{config['repo_url']}}"
        # [...]

        outputs = {self, ...}@inputs: {
          # [...]
          # inside nixosConfigurations.<system>.modules or
          # {
          #     environment.systemPackages = [ inputs.isd.default ];
          # };
          # homeConfigurations.<name>.modules =
          # {
          #   home.packages = [ inputs.isd.default ];
          # };
        };
    }

        
    ```

=== "uv"

    [uv] is a Python package manager.
    To install [uv] have a look at the [official uv installation documentation](https://docs.astral.sh/uv/).

    After installing [uv], you can _try_ `isd` by running:
    `uvx {{config['repo_url']}}`

    To install and manage `isd` via [uv], run:
    `uv tool install {{config['repo_url']}}/isd@latest`

    For more details regarding the tool management, see the upstream
    [uv] tool documentation:

    - <https://docs.astral.sh/uv/guides/tools/#installing-tools>

## Working with `isd`

The following recorded terminal session shows how `isd`
can be used to:

- Search through `systemd` units with _fuzzy_ search,
- View the current state of all matched units,
- See more detailed status information about _multiple_ units in the preview,
- Send `systemctl` commands to the selected units with auto-refreshing status outputs,
- Open the full status output in a dedicated `pager` _without_ leaving `isd`,
- Open a _different_ `pager` for the `Journal` output, and
- Customize the _theme_.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[0], marker_names=[
    'Overview',
    'Fuzzy Search',
    'Select Multiple Units',
    'Command Palette',
    'Auto-Refreshing Preview Windows',
    'Default Pager',
    'Journal Preview',
    'Custom Journal Pager',
    'Different theme',
    'Cat Preview',
    'Dependencies Preview',
    'Show Preview',
    'Help Preview',
], pauseOnMarkers=False) }}

### User/System `mode`

The top row shows in which `mode` `isd` is running.
The `mode` can either be `user` or `system` and configures
which types of units are shown and searched in the widgets below.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[0]) }}

### Fuzzy search

The top widget is the _fuzzy_ search bar.
`isd` will load all units and unit files that match the input[^1]
and highlight them according to their current state in the _search result_ widget
below.
To switch from the current search widget to the next widget either
press ++tab++ or ++enter++.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[1], startAt=timestamps[1]) }}

[^1]: If the input is empty, then all units and unit-files are shown.

### Selecting multiple units

The _search result_ widget can be navigated with the arrow keys (++up++, ++down++)
or the vim keys (++j++, ++k++).
Multiple units can be selected with ++space++.
Selected widgets are highlighted on the left side by an additional bar in an accent color,
where the currently highlighted unit is always considered selected.

Depending on the currently selected units, the _preview widget_
will show a preview of the selected units for a given output (`Status` by default).

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[2], startAt=timestamps[2]) }}

### Command Palette

The toolbar at the bottom shows the most important keybindings for the currently focused
widget, where the `^` symbol means ++ctrl++.
To open the command palette, press ++ctrl+p++.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[3], startAt=timestamps[3]) }}

The command palette will show all available commands and their respective
keybindings if available.

### Commands

For example, press ++ctrl+o++ to stop the selected units.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[4], startAt=timestamps[4]) }}

After running a `systemctl` command, a notification is shown about the
executed command and if necessary, error messages.
The selection and preview widget will automatically update to show
the new state of the selected units.

### Pager support

To view the entire preview output, a `pager` can be opened _while_
running `isd`/_without_ closing the application.
The `pager` can be opened via the `command palette` or simply
by pressing ++enter++ while focusing the _search result_ widget.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[5], startAt=timestamps[5]) }}

To switch to a different _tab_ of the _preview widget_ the
arrow keys (++left++, ++right++) or the vim keys (++h++, ++l++)
can be pressed. The next image shows the preview for the
`Journal` output of the selected units:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[6], startAt=timestamps[6]) }}

Similarly to the `Status` output, the output of the `Journal` preview
window can be opened in a `pager`. To provide more flexibility, `isd`
allows to configure a special `pager` for the `Journal` output.
In this example, [`lnav`](https://lnav.org/) is used to view the `Journal` output.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[7], startAt=timestamps[7]) }}

### Customizeability

One core feature of `isd` is it customizability and configurability.
_You_ decide which keybindings work best for you and maximize your productivity 🚀.
It also comes with a couple of different _themes_. For example, the
`dracula` theme:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[8], startAt=timestamps[8]) }}

### Summary

I hope that this short overview has helped you to get a feeling for what `isd`
_is_ and if it can be useful for you. If you are still unsure, try it out!
It is a lot easier to get feeling for the tool when you try it on your own :)

!!! tip "Support"

    If you like `isd`, please give it a :star: on GitHub!


## Next steps

Checkout the other sections as well:

- [Customization](customization.md)
- [Security](./security.md)

