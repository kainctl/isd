# Getting Started

--8<-- "README.md:tagline"

<center>
    <img src="./assets/images/isd.png" alt="isd logo" style="max-width: 50vh;">
</center>

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

- via [uv], or via
- [nix], or 
- as an [AppImage].

=== "uv"

    [uv] is a Python package manager.
    To install [uv] have a look at the [official uv installation documentation](https://docs.astral.sh/uv/).

    After installing [uv], you can _try_ `isd` by running:
    `uvx --python=3.12 isd-tui`

    To install and manage `isd` via [uv], run:
    `uv tool install --python=3.12 isd-tui`

    After installing the tool, the program `isd` and its alias[^alias] `isd-tui`
    will be available.

    `isd` requires `--python` to be set `>=3.12` and would fail
    if the default Python version is older.
    For more details regarding the tool management, see the upstream
    [uv] tool documentation:

    - <https://docs.astral.sh/uv/guides/tools/#installing-tools>


=== "nix"

    `isd` is developed with a reproducible [nix] environment and build as a [nix] package.
    This is my personal preference to install `isd` but it is a higher barrier compared to the `.AppImage`.
    To install [nix] with sensible default options, use the [`nix-installer`](https://github.com/DeterminateSystems/nix-installer)
    from [determinate.systems](https://determinate.systems/).

    Then, to _try out_ `isd`, simply run `nix run {{config['repo_url'] | replace('https://github.com/', 'github:')}}`.

    To install `isd`, add it to your packages list:

    ```nix
    # flake.nix
    {

        # [...]
        inputs.isd.url = "{{config['repo_url'] | replace('https://github.com/', 'github:')}}";
        # [...]

        outputs = {self, ...}@inputs: {
          # [...]
          # inside nixosConfigurations.<system>.modules or
          # {
          #     environment.systemPackages = [ inputs.isd.packages.<system>.default ];
          # };
          # homeConfigurations.<name>.modules =
          # {
          #   home.packages = [ inputs.isd.packages.<system>.default ];
          # };
        };
    }

        
    ```

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

        If you are using Ubuntu 24.04, extra installation steps are required.
        Please see the [open issue #10](https://github.com/isd-project/isd/issues/10).

    !!! warning

        If you have `nix` installed, this `AppImage` will _not_ work!
        Either use the `nix` or `uv` installation instructions!

??? warning "Warning for Windows WSL users"

    The `systemd` support of WSL seems to be quite buggy (also for WSL 2).
    See these GitHub issues for more details

    - <https://github.com/microsoft/WSL/issues/8842>
    - <https://github.com/microsoft/WSL/issues/10205>
    - <https://github.com/nix-community/NixOS-WSL/issues/375>


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
    'Systemctl Action',
    'Auto-Refreshing Preview Windows',
    'Command Palette',
    'Fuzzy Matching Commands',
    'Open Pager',
    'Preview Journal',
    'Custom Journal Pager',
    'Different theme',
    'Cat Preview',
    'Dependencies Preview',
    'Show Preview',
    'Help Preview',
    'Quit',
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

### `systemctl action`

The toolbar at the bottom shows the most important keybindings for the currently focused
widget, where the `^` symbol means ++ctrl++.
To open the `systemctl action` modal, press ++ctrl+o++.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[3], startAt=timestamps[3]) }}

This modal will show a list of possible actions that can be applied to the
currently selected/highlighted units. To select the desired action
navigate the list with the same keys as for the _search result_ widget and
then press ++enter++ to select the unit. Or type any of the colored _shortcut_ keys
to directly execute the action.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[4], startAt=timestamps[4]) }}

After running a `systemctl` command, a notification is shown about the
executed command and if necessary, error messages.
The selection and preview widget will automatically update to show
the new state of the selected units.

### Command Palette

To open the command palette, press ++ctrl+p++.
The command palette will show all currently available commands and their
respective keybindings if available.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[5], startAt=timestamps[5]) }}

!!! note

    The command palette also includes the same actions as the `systemctl actions`
    modal. However, the `systemctl actions` modal provides a _cleaner_ interface
    and is generally recommended over running these actions via the command palette.
    Though, you can use whatever you prefer 👍

The command palette also uses fuzzy searching to make it easier to find the command you are
interested in.


### Pager support

To view the entire preview output, a `pager` can be opened _while_
running `isd` and _without_ closing the application.
The `pager` can be opened
by pressing ++enter++ while focusing the _search result_ widget or
via the `command palette`:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[6], startAt=timestamps[6]) }}

Then you can efficiently navigate the text with the [`pager` of your choice](./customization.md#default-pager).
By deeply integrating with `pager`s `isd` avoids the need to re-invent the wheel
for code navigation and gives you full control over how you would like to navigate
the text. Here, for example, showing the output in `moar`.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[7], startAt=timestamps[7]) }}

### Journal Support

To switch to a different _tab_ of the _preview widget_ the
arrow keys (++left++, ++right++) or the vim keys (++h++, ++l++)
can be pressed while focusing the tab header or globally by triggering the
[`Next/Previous Preview Tab` actions](./customization.md#main-keybindings).

The next image shows the preview for the
`Journal` output of the selected units:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[8], startAt=timestamps[8]) }}

Similarly to the `Status` output, the output of the `Journal` preview
window can be opened in a `pager`. To provide more flexibility, `isd`
allows you [to configure a special `pager` for the `Journal` output](./customization.md#journal-pager).
In this example, [`lnav`](https://lnav.org/) is used to view the `Journal` output.

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[9], startAt=timestamps[9]) }}

### Customizeability

One core feature of `isd` is it customizability and configurability.
_You_ decide which keybindings work best for you and maximize your productivity 🚀.
It also comes with a couple of different _themes_. For example, the
`dracula` theme:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[10], startAt=timestamps[10]) }}

### Quitting

To quit the application you can either press ++ctrl+q++ or stop it via the command palette:

{{ asciinema("./assets/images/isd.cast", poster=poster_markers[15], startAt=timestamps[15]) }}

### Summary

I hope that this short overview has helped you to get a feeling for what `isd`
_is_ and if it can be useful for you. If you are still unsure, try it out!
It is a lot easier to get feeling for the tool when you try it on your own :)

!!! tip "Support"

    If you like `isd`, please give it a :star: on GitHub!

    And if you _really_ like it and can afford it, consider
    buying me a coffee via [ko-fi](https://ko-fi.com/isdproject).


## Next steps

Checkout the other sections as well:

- [Customization](./customization.md)
- [FAQ](./faq.md)
- [Security](./security.md)

[^alias]: The reason why the `isd-tui` alias exists is due to a naming conflict
on PyPI with a different package called `isd`. Providing the alias `isd-tui`
allows `uv` users to try it without having to write `uvx --from isd-tui isd`.

