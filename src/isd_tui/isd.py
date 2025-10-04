"""
isd: interactive systemd
---

The following code is a probably the messiest code I have ever written.
However, I am trying to first get the application/features correct instead of
spending way too much time at organizing and optimizing code that
would probably be deleted.

It is easy to clean up the code and just requires some dedicated time.
But until I have my desired minimal feature list completed, I will not
refactor the code. This may seem unreasonable, but it helps me
tremendously while drafting different applications.
I do not hesitate deleting large parts of the code, since "it is ugly anyway".
When I was writing code with many refactor cycles, I was way more hesitent
to removing/restructuring large parts of the code base, as it was "looking good".
"""

from __future__ import annotations

from . import __version__

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from collections import deque
from copy import deepcopy
from enum import Enum, StrEnum, auto
from functools import partial
from itertools import chain, repeat
from importlib.resources import as_file, files
from pathlib import Path
from textwrap import dedent, indent
from typing import (
    Any,
    Self,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    cast,
    Annotated,
)

from pfzy.match import fuzzy_match
from pydantic import BaseModel, Field, model_validator, PositiveInt
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
import rich.markup
from rich.style import Style
from rich.text import Text
from textual import on, work, events, log
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    VerticalGroup,
)

from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.keys import format_key

# FUTURE: Fix the settings for the default themes!
# Issue is that the default green/yellow/red colors may not
# work well with the selection color
from textual.theme import BUILTIN_THEMES

# from textual.scrollbar import ScrollBarRender
from textual.widget import Widget
from textual.widgets import (
    Footer,
    Header,
    Input,
    RichLog,
    Button,
    SelectionList,
    TabbedContent,
    TabPane,
    Tabs,
    OptionList,
    Markdown,
)
from textual.widgets._toggle_button import ToggleButton
from xdg_base_dirs import (
    xdg_cache_home,
    xdg_config_home,
    xdg_data_home,
    xdg_config_dirs,
)
from textual.widgets.selection_list import Selection
from textual.widgets.option_list import Option


# make type checker happy.
assert __package__ is not None
CSS_RESOURCE = files(__package__).joinpath("dom.tcss")

with as_file(CSS_RESOURCE) as f:
    _CSS_RESOURCE_PATH = f

if _CSS_RESOURCE_PATH.exists():
    # package resources are persisted on the file system
    CSS_RESOURCE_PATH = _CSS_RESOURCE_PATH
else:
    # this means that the resource is dynamically extracted
    # and not read as-is from the unpacked wheel.
    # So extract it again, copy its contents
    _tmp_file = tempfile.NamedTemporaryFile(
        "w", prefix="isd_", suffix=".tcss", delete=False
    )
    _tmp_file.write(CSS_RESOURCE.read_text())
    CSS_RESOURCE_PATH = Path(_tmp_file.name)
    del _tmp_file

ToggleButton.BUTTON_LEFT = ""
ToggleButton.BUTTON_INNER = "▐"  # "▌" # "█"
ToggleButton.BUTTON_RIGHT = ""

UNIT_PRIORITY_ORDER = [
    "service",
    "timer",
    "socket",
    "network",
    "netdev",
    "link",
    "mount",
    "automount",
    "path",
    "swap",
    "scope",
    "device",
    "target",
    "hostname",
    "cgroup",
    "dnssec",
    "resolved",
    "busname",
]

# HERE: Consider if these options even have a reason to exist.
AUTHENTICATION_MODE = "sudo"
# AUTHENTICATION_MODE = "polkit"

# HERE: Remove this from the global scope for testing!
Theme = StrEnum("Theme", [key for key in BUILTIN_THEMES.keys()])  # type: ignore
StartupMode = StrEnum("StartupMode", ["user", "system", "auto"])

SETTINGS_YAML_HEADER = dedent("""\
        # yaml-language-server: $schema=schema.json
        # ^ This links to the JSON Schema that provides auto-completion support
        #   and dynamically checks the input. For this to work, your editor must have
        #   support for the `yaml-language-server`
        #   - <https://github.com/redhat-developer/yaml-language-server>
        #
        #   Check the `Clients` section for more information:
        #   - <https://github.com/redhat-developer/yaml-language-server?tab=readme-ov-file#clients>
        #
        # To create a fresh `config.yaml` file with the defaults,
        # simply delete this file. It will be re-created when `isd` starts.

    """)

RESERVED_KEYBINDINGS: Dict[str, str] = {
    "ctrl+q": "Close App",
    "ctrl+c": "Close App",
    "ctrl+z": "Suspend App",
    "ctrl+p": "Open Command Palette",
    "ctrl+minus": "Reduce Size",
    "ctrl+plus": "Increase Size",
    "escape": "Close modal",
    "tab": "Focus next",
    "shift+tab": "Focus previous",
    "space": "Select",
}


def smart_dedent(inp: Optional[str]) -> str:
    if inp is None:
        return ""
    else:
        return dedent(inp).strip()


def ensure_reserved(inp_keys: str) -> str:
    """
    Assert that the given keybinding(s)
    is inside of the global `RESERVED_KEYBDINDINGS`.

    Returns the inp as is.
    """
    for key in inp_keys.split(","):
        assert key.strip() in RESERVED_KEYBINDINGS
    return inp_keys


def get_env_systemd_less_args() -> Optional[list[str]]:
    env_systemd_less = os.getenv("SYSTEMD_LESS")
    if env_systemd_less is not None and env_systemd_less.strip() != "":
        return env_systemd_less.split(sep=" ")
    return None


PRESET_LESS_DEFAULT_ARGS: list[str] = get_env_systemd_less_args() or [
    # "--quit-if-one-screen",  # -F
    "--RAW-CONTROL-CHARS",  # -R
    "--chop-long-lines",  # -S
    "--no-init",  # -X
    "--LONG-PROMPT",  # -M
    "--quit-on-intr",  # -K
    "-+F",  # long version reset was broken in older versions
    # "--+quit-if-one-screen",  # never quit if it fits on one screen
]
# requires POSIXLY_CORRECT to be set.
PRESET_MORE_DEFAULT_ARGS: list[str] = []
PRESET_MOAR_DEFAULT_ARGS: list[str] = []
PRESET_LNAV_DEFAULT_ARGS: list[str] = [
    # "-q",  # Do not print informational message.
    #   ^ quits if outputs fits onto single screen!
    "-t",  # Treat data piped into standard in as log file
]


PRESET_LESS_JOURNAL_ARGS = PRESET_LESS_DEFAULT_ARGS + [
    "+G"  # jump to end
]
PRESET_MORE_JOURNAL_ARGS: list[str] = PRESET_MORE_DEFAULT_ARGS + []
PRESET_MOAR_JOURNAL_ARGS: list[str] = PRESET_MOAR_DEFAULT_ARGS + [
    "--follow"  # Follow input and jump to end.
]
PRESET_LNAV_JOURNAL_ARGS: list[str] = PRESET_LNAV_DEFAULT_ARGS + [
    # "-q",  # Do not print informational message.
    #   ^ quits if outputs fits onto single screen!
    "-t",  # Treat data piped into standard in as log file
]

assert PRESET_LESS_DEFAULT_ARGS is not PRESET_LESS_JOURNAL_ARGS


class CustomOptionList(OptionList, inherit_bindings=False):
    # init should receive a custom type as input.
    # that has a list of key triggers and
    # associated "actions"
    # These keys from the init, initialize the
    # "bindings" that trigger a 'quick-select' action
    # it should also receive a list of options for navigation keys
    # (this should be a list).
    # Since this is the third place, the configuration file
    # should be updated to reflect this change and share the navigation
    # keybindings across _all_ elements.
    # This should avoid clashing configurations for up/down
    # and modal shortcuts -> Avoiding unexpected behavior.
    # Although the direct triggers should _still_ be supported!
    def __init__(self, navigation_keybindings: NavigationKeybindings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for keys, action, description in [
            (navigation_keybindings.down, "cursor_down", "Down"),
            (navigation_keybindings.up, "cursor_up", "Up"),
            (navigation_keybindings.page_up, "page_up", "Page Up"),
            (navigation_keybindings.page_down, "page_down", "Page Down"),
            (navigation_keybindings.top, "first", "First"),
            (navigation_keybindings.bottom, "last", "Last"),
        ]:
            self._bindings.bind(
                keys=keys,
                action=action,
                description=description,
                show=False,
            )


def rich_underline_key(inp_str: str, key: str) -> Text:
    txt = inp_str.replace(key, f"[u]{key}[/u]", 1)
    return Text.from_markup(txt)


def render_keybinding(inp_str: str) -> str:
    *modifiers, key = inp_str.split("+")
    key = format_key(key)

    # Convert ctrl modifier to caret
    if "ctrl" in modifiers:
        modifiers.pop(modifiers.index("ctrl"))
        key = f"^{key}"
    # Join everything with +
    key_tokens = modifiers + [key]
    return "+".join(key_tokens)


class SystemctlActionScreen(ModalScreen[Optional[str]]):
    """
    Present a screen with the configured systemctl actions.
    Uses the common navigation style with enter and uses the modal specific
    shortcuts.

    Assumes that the keybindings aren't conflicting.
    """

    BINDINGS = [Binding("enter", "select", "Select", show=True)]
    AUTO_FOCUS = "CustomOptionList"

    def __init__(
        self,
        close_modal_key: str,
        navigation_keybindings: NavigationKeybindings,
        systemctl_commands: List[SystemctlCommand],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.navigation_keybindings = navigation_keybindings
        self.systemctl_commands = systemctl_commands
        # only the first keybinding will be shown!
        self._bindings.bind(
            ensure_reserved("escape") + "," + close_modal_key, "close", "Close"
        )

    def build_options(self) -> List[Option]:
        rendered_keys_map = {
            cmd.modal_keybinding: render_keybinding(cmd.modal_keybinding)
            for cmd in self.systemctl_commands
        }
        longest_rendered_keybinding = max(
            len(key) for key in rendered_keys_map.values()
        )

        accent = self.app.theme_variables.get("accent")

        opts = []
        for cmd in self.systemctl_commands:
            k = Text.from_markup(
                f"[b]{rendered_keys_map[cmd.modal_keybinding]:>{longest_rendered_keybinding}}[/b]",
            )
            if accent is not None:
                k.stylize(accent, start=0)
            opts.append(
                Option(
                    k
                    + " systemctl "
                    + rich_underline_key(cmd.command, cmd.modal_keybinding),
                    id=cmd.command,
                )
            )
            # Add the quick_select bindings
            self._bindings.bind(
                cmd.modal_keybinding,
                f"quick_select('{cmd.command}')",
                description=f"Quick select {cmd.description}",
                show=False,
            )
        return opts

    def compose(self) -> ComposeResult:
        opts = self.build_options()
        yield CustomOptionList(self.navigation_keybindings, *opts)
        yield Footer()

    def action_select(self) -> None:
        opt_list = cast(CustomOptionList, self.query_one(CustomOptionList))
        opt_list.action_select()

    def action_quick_select(self, id: str) -> None:
        opt_list = cast(CustomOptionList, self.query_one(CustomOptionList))
        opt_idx = opt_list.get_option_index(id)
        opt_list.highlighted = opt_idx
        opt_list.action_select()
        # -> could be simplified to the following since `id` == selected option
        # self.dismiss(id); but leave for now, to keep it consistent with enter

    def action_close(self) -> None:
        self.dismiss(None)

    @on(CustomOptionList.OptionSelected)
    def command_selected(self, event: CustomOptionList.OptionSelected):
        self.dismiss(event.option_id)


class DonationScreen(ModalScreen[Optional[None]]):
    """
    Present a screen with the donation information.
    """

    BINDINGS = [Binding("enter", "select", "Select", show=True)]

    def __init__(
        self,
        startup_count: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._bindings.bind(ensure_reserved("escape"), "close", "Close")
        self.startup_count = startup_count

    def compose(self) -> ComposeResult:
        with VerticalGroup():
            yield Markdown(
                f"# 🎉🎉🎉 You have opened isd more than {self.startup_count} times! 🎉🎉🎉\n"
                + "We are proud this tool is useful to you! "
                + "We build this app with love (and a lot of caffeine). "
                + "If our work adds value to your day, consider supporting us to keep the project sustainable. "
                + "Every contribution, big or small, powers future updates! \n"
                + "- [ko-fi.com/isdproject](https://ko-fi.com/isdproject)\n\n"
                + "# 💙 Thank you 💙"
            )
            yield Button(
                label="Close",
            )
        yield Footer()

    def on_button_pressed(self) -> None:
        self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)


def get_default_pager_args_presets(pager: str) -> list[str]:
    pager_bin = pager.split("/")[-1]
    if pager_bin == "less":
        return PRESET_LESS_DEFAULT_ARGS
    elif pager_bin == "more":
        return PRESET_MORE_DEFAULT_ARGS
    elif pager_bin == "moar":
        return PRESET_MOAR_DEFAULT_ARGS
    elif pager_bin == "lnav":
        return PRESET_LNAV_DEFAULT_ARGS
    return []


def get_journal_pager_args_presets(pager: str) -> list[str]:
    pager_bin = pager.split("/")[-1]
    if pager_bin == "less":
        return PRESET_LESS_JOURNAL_ARGS
    elif pager_bin == "more":
        return PRESET_MORE_JOURNAL_ARGS
    elif pager_bin == "moar":
        return PRESET_MOAR_JOURNAL_ARGS
    elif pager_bin == "lnav":
        return PRESET_LNAV_JOURNAL_ARGS
    return []


# The systemctl direct_keybindings should be unique!
# They should never allow accidental triggers!
# By default, there aren't any direct keybindings
# Only modal keybindings.
# These modal keybindings should also only map to a single key, ideally ascii.
# The modal keybindings aren't allowed to overlap with the navigation keybindings.
class SystemctlCommand(BaseModel):
    """SystemctlCommand documentation"""

    modal_keybinding: str = Field(description="Associated key to use in the modal")
    direct_keybinding: Optional[str] = Field(
        default=None, description="Direct Keybinding"
    )
    command: str = Field(description="systemctl subcommand (may include arguments)")
    description: str = Field(description="Additional command information.")

    @model_validator(mode="after")
    def check_overlaps_with_reserved(self) -> Self:
        for attr in ["modal_keybinding", "direct_keybinding"]:
            complex_key = getattr(self, attr)
            if complex_key is None:
                continue
            for unformatted_key in complex_key.split(","):
                key = unformatted_key.lower().strip()
                if key in RESERVED_KEYBINDINGS.keys():
                    raise ValueError(
                        f"The reserved keybinding: `{key}` for `{RESERVED_KEYBINDINGS[key]}` was used in {self.__class__}.{attr} for `{self.command}`"
                    )
        return self


class KeybindingModel(BaseModel):
    @model_validator(mode="after")
    def check_overlaps(self) -> Self:
        # normalized_key_map would raise an error
        # if there would be a conflict
        key_map = self.normalized_key_map()
        # check if any of these keys are from the reserved keybindings
        conflicting_keys = key_map.keys() & RESERVED_KEYBINDINGS.keys()
        if len(conflicting_keys) != 0:
            error_message = "\n".join(
                f"The reserved keybinding: `{key}` for `{RESERVED_KEYBINDINGS[key]}` was used in {self.__class__}.{key_map[key]}"
                for key in conflicting_keys
            )
            raise ValueError(error_message)

        return self

    def normalized_key_map(self) -> Dict[str, str]:
        """
        Returns a normalized keymap.
        Raises a ValueError if there conflicts
        """
        d: Dict[str, str] = {}
        for attr, keys in self.model_dump().items():
            for unformatted_key in keys.split(","):
                key = unformatted_key.strip().lower()
                if key in d:
                    raise ValueError(
                        f"{self.__class__} has conflicting definitions for the key `{key}`"
                        + f" between the attributes `{d[key]}` and `{attr}`."
                    )
                else:
                    d[key] = attr

        return d


class GenericKeybinding(KeybindingModel):
    """
    Uncategorized generic keybindings for
    toggling screens/modals and opening settings.
    """

    toggle_systemctl_modal: str = Field(
        default="ctrl+o", description="Systemctl action"
    )
    open_config: str = Field(
        # confi*g*ure; there are just too few safe keybindings :(
        default="ctrl+g",
        description="Open config in editor",
    )


class MainKeybindings(KeybindingModel):
    """
    Configurable keybindings for common actions on the main screen.
    These keybindings must be unique across the entire application.
    """

    next_preview_tab: str = Field(
        default="full_stop",
        description="Next preview tab",
    )
    previous_preview_tab: str = Field(
        default="comma",
        description="Previous preview tab",
    )
    clear_input: str = Field(
        default="backspace,ctrl+backspace", description="Clear search input"
    )
    jump_to_input: str = Field(default="slash", description="Jump to search input")
    copy_unit_path: str = Field(
        default="ctrl+x",
        description="Copy highlighted unit path to clipboard",
    )
    open_preview_in_pager: str = Field(
        default="enter",
        description="Open in pager",
    )
    open_preview_in_editor: str = Field(
        default="ctrl+v",  # Ctrl-V is Visual Mode so I find opening in EDITOR fitting
        description="Open in editor",
    )
    toggle_mode: str = Field(default="ctrl+t", description="Toggle mode")
    increase_widget_height: str = Field(
        default="plus", description="Increase height of currently focused widget"
    )
    decrease_widget_height: str = Field(
        default="minus", description="Decrease height of currently focused widget"
    )


class NavigationKeybindings(KeybindingModel):
    """
    Keybindings specific to navigation.
    These will be applied to _all_ widgets that
    have any navigational component.
    To avoid confusion, these must be unique across the entire application;
    even if a given widget does not have horizontal navigation.
    """

    down: str = Field(default="down,j", description="Down")
    up: str = Field(default="up,k", description="Up")
    page_down: str = Field(default="ctrl+down,ctrl+f,pagedown", description="Page down")
    page_up: str = Field(default="ctrl+up,ctrl+b,pageup", description="Page up")
    top: str = Field(default="home", description="Goto top")
    bottom: str = Field(default="end", description="Goto bottom")
    # These are probably only needed for the preview output!
    left: str = Field(default="left,h", description="Left")
    right: str = Field(default="right,l", description="Right")
    page_left: str = Field(default="ctrl+left", description="Page left")
    page_right: str = Field(default="ctrl+right", description="Page right")


DEFAULT_COMMANDS = [
    SystemctlCommand(
        modal_keybinding="a",
        command="start",
        description="Start unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="o",
        command="stop",
        direct_keybinding="ctrl+s",
        description="Stop unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="s",
        command="restart",
        description="Restart unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="e",
        command="edit",
        description="Edit highlighted unit via drop-in with configured editor",
    ),
    SystemctlCommand(
        modal_keybinding="f",
        command="edit --full",
        description="Edit highlighted unit source with configured editor",
    ),
    SystemctlCommand(
        modal_keybinding="r",
        command="edit --runtime",
        description="Edit highlighted unit only for current runtime",
    ),
    SystemctlCommand(
        modal_keybinding="d",
        command="reload",
        description="Reload unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="n",
        command="enable",
        description="Enable unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="i",
        command="disable",
        description="Disable unit(s).",
    ),
    SystemctlCommand(
        modal_keybinding="m",
        command="mask",
        description="Mask/Disable starting unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="u",
        command="unmask",
        description="Undo masking of unit(s)",
    ),
    SystemctlCommand(
        modal_keybinding="-",
        command="reset-failed",
        description="Reset failed state of unit(s), including the restart counter.",
    ),
]

SYSTEMD_EDITOR_ENVS = {
    env: os.getenv(env) for env in ["SYSTEMD_EDITOR", "EDITOR", "VISUAL"]
}


# mainly for further work in the future.
# Now, I simply assume that it is in the PATH
def get_systemctl_bin() -> str:
    return "systemctl"


def get_systemd_editor() -> str:
    """
    See systemd editor resolution.
    """
    env_editors = [
        editor
        for env_var, editor in SYSTEMD_EDITOR_ENVS.items()
        if (editor is not None) and (shutil.which(editor) is not None)
    ]
    default_editors = [
        editor
        for cmd in ["editor", "nano", "vim", "vi"]
        if (editor := shutil.which(cmd)) is not None
    ]
    available_editors = env_editors + default_editors
    if len(available_editors) == 0:
        raise OSError("Could not find editor according to systemd resolution rules!")
    return available_editors[0]


def get_systemd_pager() -> str:
    """
    See SYSTEMD_PAGER resolution.

    Ignoring the SYSTEMD_PAGERSECURE option:
    <https://www.freedesktop.org/software/systemd/man/latest/systemd.html#%24SYSTEMD_PAGERSECURE>
    """
    env_pagers = [
        pager
        for env in ["SYSTEMD_PAGER", "PAGER"]
        if (pager := os.getenv(env)) is not None and (shutil.which(pager) is not None)
    ]
    default_pagers = [
        pager for cmd in ["less", "more"] if (pager := shutil.which(cmd)) is not None
    ]
    available_pagers = env_pagers + default_pagers
    if len(available_pagers) == 0:
        raise OSError("Could not find pager according to systemd resolution rules!")
    return available_pagers[0]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="isd_",
        env_ignore_empty=True,
        cli_parse_args=False,
        env_file_encoding="utf-8",
    )

    startup_mode: StartupMode = Field(
        default=StartupMode("auto"),
        description=dedent("""\
            The systemctl startup mode (`user`/`system`).
            By default loads the mode from the last session (`auto`)."""),
    )

    preview_and_selection_refresh_interval_sec: float = Field(
        default=1,
        description=dedent("""\
            Auto refresh the preview unit _and_ unit states of selected units.
            Example: When a selected unit changes from running to failed
            the unit state color and preview window will be updated after this
            time has passed, even if _nothing_ is pressed.
            """),
    )

    full_refresh_interval_sec: float = Field(
        default=10,
        description=dedent("""\
            Auto refresh all unit states.
            This is important to find new units that have been added
            since the start of `isd`.
            Please note that low values will cause many and large systemctl calls."""),
    )

    cache_input: bool = Field(
        default=True,
        description=dedent("""\
            Cache the unit search text input across restarts.
            Enabled by default."""),
    )

    updates_throttle_sec: float = Field(
        default=0.05,
        description=dedent("""\
            Seconds to wait before computing state updates (default 0.05s).
            For example, time after input has changed before updating the selection.
            Or time to wait to update preview window after highlighting new value.
            The idea is to minimize the number of 'irrelevant' updated during fast
            scrolling through the unit list or quick typing."""),
    )

    editor: str = Field(
        default="auto",
        description=dedent("""\
            Editor to use; Default = `auto`
            Defaults to the first editor defined in one of the environment variables:
            - $SYSTEMD_EDITOR, $EDITOR, $VISUAL
            and then falls back to the first available editor:
            - `editor`, `nano`, `vim`, `vi`."""),
    )

    default_pager: str = Field(
        default="auto",
        description=dedent("""\
            Default pager to open preview tabs in (except for `Journal`). Default = `auto`
            Defaults to the first pager defined in one of the environment variables:
            - `SYSTEMD_PAGER`, `PAGER`
            and then falls back to the first available pager:
            - `less`, `more`.

            Note: Input is always provided via STDIN to the pager!"""),
    )

    journal_pager: str = Field(
        default="auto",
        description=dedent("""\
            Default pager to open preview for `Journal` tab. Default = `auto`
            Defaults to the first pager defined in one of the environment variables:
            - `SYSTEMD_PAGER`, `PAGER`
            and then falls back to the first available pager:
            - `less`, `more`.

            Note: Input is always provided via STDIN to the pager!"""),
    )

    journalctl_args: list[str] = Field(
        default=["--catalog", "--lines=1000"],
        description=dedent("""\
            Default arguments for `journalctl` to generate the
            output of the `Journal` preview window."""),
    )

    theme: Theme = Field(
        default=Theme("textual-dark"), description="The theme of the application."
    )

    search_results_height_fraction: PositiveInt = Field(
        default=1, description="Relative height compared to preview height."
    )
    preview_height_fraction: PositiveInt = Field(
        default=2, description="Relative height compared to search result height."
    )

    # FUTURE: Allow option to select if multi-select is allowed or not.
    generic_keybindings: GenericKeybinding = Field(
        default=GenericKeybinding(),
        description=smart_dedent(GenericKeybinding.__doc__),
    )

    main_keybindings: MainKeybindings = Field(
        default=MainKeybindings(),
        description=smart_dedent(MainKeybindings.__doc__),
    )

    navigation_keybindings: NavigationKeybindings = Field(
        default=NavigationKeybindings(),
        description=smart_dedent(NavigationKeybindings.__doc__),
    )

    systemctl_commands: list[SystemctlCommand] = Field(
        default=DEFAULT_COMMANDS,
        description=smart_dedent(
            """
            List of configurable systemctl subcommand keybindings.
            The exact subcommand (including arguments) can be defined by setting `command`.
            The `modal_keybinding`s provide the shortcut key(s)
            for the modal action window.
            Optionally, `direct_keybinding`s can be configured to
            immediately trigger the systemctl action from the main screen
            without having to open the modal first.

            The description is used to describe the subcommand
            in the `CommandPalette`
            """
        ),
    )

    default_pager_args: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description=dedent("""\
        Arguments passed to the configured `default_pager`.
        Should NOT be required most of the time.
        As for most pagers, the correct arguments/environment variables are set by default
        if this value is unset (`null`)."""),
        ),
    ] = None

    journal_pager_args: Annotated[
        Optional[list[str]],
        Field(
            default=None,
            description=dedent("""\
        Arguments passed to the configured `journal_pager`.
        Should NOT be required most of the time.
        As for most pagers, the correct arguments/environment variables are set by default
        if this value is unset (`null`)."""),
        ),
    ] = None

    preview_max_lines: int = Field(
        default=500,
        description=dedent("""\
            How many lines to show in the preview windows.
            Setting this value too large, especially with long journal entries
            will considerably slow down the application.
            Usually the default should be left as is.

            Note: The output is not trimmed when a pager or editor is opened!"""),
    )

    # https://github.com/tinted-theming/home?tab=readme-ov-file
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_file = get_config_file_path()
        global_config_file = get_global_config_file_path()
        settings = [init_settings]
        # The environment variables should have preference over global configuration.
        settings.append(env_settings)
        if config_file is not None and config_file.exists():
            settings.append(YamlConfigSettingsSource(settings_cls, config_file))
        if global_config_file.exists():
            settings.append(YamlConfigSettingsSource(settings_cls, global_config_file))
        return tuple(settings)

    @model_validator(mode="after")
    def check_keybinding_overlaps(self) -> Self:
        """
        Check whether or not the provided keybindings overlap
        with reserved keybindings or with each other.
        """

        direct_keys = {
            unformatted_key.lower().strip()
            for sys_cmd in self.systemctl_commands
            if sys_cmd.direct_keybinding is not None
            for unformatted_key in sys_cmd.direct_keybinding.split(",")
        }
        modal_keys = {
            unformatted_key.lower().strip()
            for sys_cmd in self.systemctl_commands
            if sys_cmd.modal_keybinding is not None
            for unformatted_key in sys_cmd.modal_keybinding.split(",")
        }
        generic_keys = self.generic_keybindings.normalized_key_map().keys()
        main_keys = self.main_keybindings.normalized_key_map().keys()
        navigation_keys = self.navigation_keybindings.normalized_key_map().keys()

        named_keybindings = {
            "navigation_keybindings": navigation_keys,
            "systemctl.direct_keybinding": direct_keys,
            "generic_keybindings": generic_keys,
            "systemctl.modal_keybinding": modal_keys,
            "main_keybindings": main_keys,
        }

        # What combinations are not allowed?
        # `navigation` with ANY.
        # `direct_keybinding` with ANY
        # global with ANY
        # atm only modal_keybinding and main_keybindings may overlap
        # Remember: The reason why modal_keybindings should be unique
        # is to ensure that nobody _accidentally_ triggers something
        # out of habit, even if the modal "catches" all keybindings.
        for strict_keybinding_name in [
            "navigation_keybindings",
            "systemctl.direct_keybinding",
            "generic_keybindings",
        ]:
            for name, keybindings in named_keybindings.items():
                if strict_keybinding_name == name:
                    continue
                overlapping_keys = (
                    keybindings & named_keybindings[strict_keybinding_name]
                )
                if len(overlapping_keys) != 0:
                    error_message = "\n".join(
                        f"The key `{key}` overlaps between `{name}` and `{strict_keybinding_name}`"
                        for key in overlapping_keys
                    )
                    raise ValueError(error_message)

        return self


def get_default_settings() -> Settings:
    return Settings.model_construct()


def get_default_settings_yaml(as_comments: bool) -> str:
    text = render_model_as_yaml(get_default_settings())

    def comment_line(line: str) -> str:
        """
        Leave empty lines as they are.
        If line is already a comment make it `##`.
        Otherwise, prefix it with `# `
        """
        if line.strip() == "":
            prefix = ""
        elif line.startswith("#"):
            prefix = "#"
        else:
            prefix = "# "
        return prefix + line

    if as_comments:
        text = "\n".join(comment_line(line) for line in text.splitlines())
    return SETTINGS_YAML_HEADER + text


def is_root() -> bool:
    # assuming root == 0
    return os.getuid() == 0


# Structure from:
# https://github.com/darrenburns/posting/blob/main/src/posting/locations.py
def isd_cache_dir() -> Path:
    """
    Return the path to the isd version-specific cache directory.
    The function will try to create the directory if it doesn't exist
    but will skip any errors.
    """
    assert __package__ is not None
    cache_dir = Path(xdg_cache_home()) / __package__ / __version__
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Exception: {e} while creating directory: {cache_dir}")
    return cache_dir


def isd_data_dir() -> Path:
    """
    Return the path to persistent isd data directory.
    The function will try to create the directory if it doesn't exist
    but will skip any errors.
    """
    assert __package__ is not None
    isd_data_dir = xdg_data_home() / __package__
    try:
        isd_data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Exception: {e} while creating directory: {isd_data_dir}")
    return isd_data_dir


def isd_config_dir() -> Path:
    """
    Return the path to the isd config directory.
    The function will try to create the directory if it doesn't exist
    but will skip any errors.
    """
    assert __package__ is not None
    config_dir: Path = xdg_config_home() / __package__
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Exception: {e} while creating directory: {config_dir}")
    return config_dir


def isd_global_config_dir() -> Path:
    """
    Return the path to the global isd config directory.
    It will return the first matching directory within XDG_CONFIG_DIRS
    and return `/etc/xdg/<pkg>` otherwise.
    The function will NOT try to create the directory if it doesn't exist.
    """
    assert __package__ is not None
    matched_config_dirs = [
        p / __package__ for p in xdg_config_dirs() if (p / __package__).exists()
    ]
    config_dir: Path = (
        matched_config_dirs[0]
        if len(matched_config_dirs) > 0
        else (Path("/etc/xdg/") / __package__)
    )
    return config_dir


def get_isd_cached_state_json_file_path() -> Path:
    cache_dir = isd_cache_dir()
    return cache_dir / "state.json"


def get_isd_persistent_json_file_path() -> Path:
    data_dir = isd_data_dir()
    return data_dir / "persistent_state.json"


def get_config_file_path() -> Path:
    config_dir = isd_config_dir()
    return config_dir / "config.yaml"


def get_global_config_file_path() -> Path:
    config_dir = isd_global_config_dir()
    return config_dir / "config.yaml"


class Fluid(Horizontal):
    """
    A simple Container that switches it's layout from `Horizontal`
    to `Vertical` if the width falls below the `min_width`.
    """

    is_horizontal: reactive[bool] = reactive(True)

    def __init__(self, min_width=120, **kwargs) -> None:
        self.min_width = min_width
        super().__init__(**kwargs)

    def on_resize(self, event: events.Resize) -> None:
        """Adjust layout based on terminal width."""
        self.is_horizontal = event.size.width >= self.min_width
        self.update_layout()

    def update_layout(self) -> None:
        """Update the layout direction based on current width."""
        self.styles.layout = "horizontal" if self.is_horizontal else "vertical"


class CustomInput(Input):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CustomSelectionList(SelectionList, inherit_bindings=False):
    def __init__(
        self,
        navigation_keybindings: NavigationKeybindings,
        **kwargs,
    ):
        super().__init__(**kwargs)
        for keys, action, description in [
            (navigation_keybindings.down, "cursor_down", "Down"),
            (navigation_keybindings.up, "cursor_up", "Up"),
            (navigation_keybindings.page_up, "page_up", "Page Up"),
            (navigation_keybindings.page_down, "page_down", "Page Down"),
            (navigation_keybindings.top, "first", "First"),
            (navigation_keybindings.bottom, "last", "Last"),
        ]:
            self._bindings.bind(
                keys=keys,
                action=action,
                description=description,
                show=False,
            )

        self._bindings.bind(
            keys="space",
            action="select",
            description="Select",
            show=True,
        )

    async def on_click(self, event: events.Click) -> None:
        """React to the mouse being clicked on an item.

        Args:
            event: The click event.

        Copied logic from `_option_list.py` file `_on_click`.
        """
        clicked_option: int | None = event.style.meta.get("option")
        if (
            clicked_option is not None
            and clicked_option >= 0
            and not self._options[clicked_option].disabled
        ):
            self.highlighted = clicked_option

        if event.ctrl or event.meta or event.shift:
            # Only actually select the unit if it was
            self.action_select()
        else:
            # if no modifier is pressed, deselect the other ones!
            self.deselect_all()

        await super()._on_click(event)

        event.stop()


def unit_sort_priority(unit: str) -> int:
    suffix = unit.rsplit(".", maxsplit=1)[-1]
    try:
        prio = UNIT_PRIORITY_ORDER.index(suffix)
    except ValueError:
        prio = 100
    return prio


class UnitReprState(Enum):
    # derived from the value of the "active" column
    active = auto()
    reloading = auto()
    refreshing = auto()
    deactivating = auto()
    activating = auto()
    maintenance = auto()
    failed = auto()
    # These are custom values that try to be more
    # specific than simply returning "inactive".
    not_found = auto()
    bad_setting = auto()
    masked = auto()
    error = auto()
    inactive = auto()
    # state for unit files that are only listed in
    # the output of `list-unit-files`
    file = auto()

    def render_state(
        self, unit: str, highlight_indices: Optional[List[int]] = None
    ) -> Text:
        """
        Given a `unit` and an optional list of indices, highlight them depending
        on the state.
        Return a rich `Text` object with the correct styling.

        Use mapping from upstream:
        https://github.com/systemd/systemd/blob/78056ba850fbe0606c3e264f5af68ac3eb52c9e7/src/basic/unit-def.c#L361-L378
        """
        if self == UnitReprState.active:
            prefix = "●"
            style = "green"
        elif self == UnitReprState.reloading or self == UnitReprState.refreshing:
            prefix = "↻"
            style = "green"
        elif self == UnitReprState.failed:
            prefix = "×"
            style = "red"
        elif self == UnitReprState.activating or self == UnitReprState.deactivating:
            prefix = "●"
            style = "yellow"  # This is custom
        elif self == UnitReprState.inactive or self == UnitReprState.maintenance:
            prefix = "○"
            style = ""
        # until here, I am following the settings from upstream:
        # https://github.com/systemd/systemd/blob/78056ba850fbe0606c3e264f5af68ac3eb52c9e7/src/basic/unit-def.c#L361-L378
        # The following a more custom visualization that I provide for "more detailed"
        # `inactive` units. The parser needs to take care of mapping those to the more specialized cases.
        # To link the meaning closer to the `inactive` state, the following should re-use the same
        # symbol as `inactive`.
        elif self == UnitReprState.not_found or self == UnitReprState.masked:
            prefix = "○"
            style = "yellow"
        elif self == UnitReprState.error or self == UnitReprState.bad_setting:
            prefix = "○"
            style = "red"
        elif auto:
            # -> this is a visual indication that it is "different"
            prefix = "○"
            style = "#878787"  # gray
        else:
            raise NotImplementedError("Unknown render state")

        text = Text(unit)
        if highlight_indices is not None and len(highlight_indices) > 0:
            text.stylize("dim")
            for idx in highlight_indices:
                text.stylize(Style(dim=False, bold=True), start=idx, end=idx + 1)

        # FUTURE: Could implement overflow method
        return Text.assemble(prefix, " ", text, style=style)


def parse_list_unit_files_lines(lines: str) -> dict[str, UnitReprState]:
    """
    This output seems to be quite a bit less stable over different
    `systemd` versions.
    From what I can tell, the unit-files can be one of
    (v229) static, enabled, disabled, masked, or
    (v233) enabled, generated, linked, alias, masked, enabled-runtime.
    -> I will simply map those to a special `UnitReprState` and use
    that as a fall back if the actual `list-units` call does not
    provide any actual info.
    """
    d = {}
    for i, line in enumerate(lines.splitlines()):
        # if i == 0:
        #     columns = line.split()
        #     # May receive an empty input if no user units exist!
        #     if columns == "":
        #         return {}
        #     # strictly speaking it should be "UNIT FILE"
        #     assert columns[0] == "UNIT"
        #     assert columns[1] == "FILE"
        #     continue
        if line == "":
            # End of structured output.
            # The remaining lines contain the legend description.
            break
        #
        fields = line.split(maxsplit=1)
        unit_file_name = fields[0]
        d[unit_file_name] = UnitReprState.file
    return d


def parse_list_units_lines(lines: str) -> dict[str, UnitReprState]:
    """
    Parses data that was generated with `systemctl list-units --full --all --plain`.
    Skips the first row and stop after seeing the first empty line.

    Throughput notes:
    Generating the mappings for a file that is over
    100'000 lines long with > 21MB of data, the runtime
    is about 170 ms. I won't optimize this further.
    If necessary, optimize reading the data from the pipe
    to process the data in chunks. Using `re` was slower.
    """
    d = {}
    for i, line in enumerate(lines.splitlines()):
        if line == "":
            # End of structured output.
            break

        fields = line.split()
        unit = fields[0]
        load_value = fields[1]
        active_value = fields[2]

        if active_value in (
            "active",
            "reloading",
            "refreshing",
            "deactivating",
            "activating",
            "maintenance",
            "failed",
        ):
            d[unit] = UnitReprState[active_value]
        elif active_value == "inactive":
            if load_value == "loaded":
                # If the value is `loaded` fall back to the
                # default `invalid` state.
                # For example, a crashed unit falls into `invalid`
                # with `loaded` and has the sub state failed.
                d[unit] = UnitReprState["inactive"]
            else:
                # Try to derive custom, more concrete value from `load_value`
                # If it is something different than 'loaded' I can
                # provide more information.
                # This should be one of `masked`, `bad-setting`, `not-found`, `error`
                d[unit] = UnitReprState[load_value.replace("-", "_")]
        else:
            raise NotImplementedError("Reached an unknown unit state.")
    return d


async def load_unit_to_state_dict(mode: str, *pattern: str) -> Dict[str, UnitReprState]:
    """
    Calls `list-unit-files` and `list-units` command and parses the output.
    Returns mapping from the unit name to its `UnitReprState` to allow
    customized coloring.

    The output of `list-unit-files` contains ALL units but not with the most specific information.
    The output of `list-units` only contains those in memory but contains relevant
    information for coloring.

    The mode defines which types of units should be loaded.

    By default, it will load ALL units of the configured `mode`
    but if `patterns` is given, those will be forwarded to the
    `list-unit-files` and `list-units` calls!
    """
    list_units = [
        get_systemctl_bin(),
        "list-units",
    ]
    list_unit_files = [
        get_systemctl_bin(),
        "list-unit-files",
    ]
    if mode == "user":
        mode_arg = ["--user"]
    else:
        mode_arg = []

    args = mode_arg + [
        "--all",
        "--full",
        "--plain",
        "--no-legend",
        "--",
        *pattern,
    ]
    proc = await asyncio.create_subprocess_exec(
        *list_units,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    # proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parsed_units = parse_list_units_lines(stdout.decode())

    proc = await asyncio.create_subprocess_exec(
        *list_unit_files,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()

    # If there are no matches for the selected pattern,
    # `systemctl list-unit-files` returns a non-zero exit code!
    # Better to check `stderr`.
    if stderr.decode() != "":
        raise Exception(proc.stderr)

    parsed_unit_files = parse_list_unit_files_lines(stdout.decode())
    return {**parsed_unit_files, **parsed_units}


def show_command(*args: str) -> None:
    # clean up terminal
    subprocess.call("clear")
    # show current command
    print(f"\n$ {' '.join(args)}")


async def systemctl_async(
    *cmd: str,
    mode: str,
    units: Iterable[str],
    sudo: bool = False,
    foreground: bool = False,
    head: Optional[int] = None,
    ask_password: bool = False,
) -> Tuple[int, str, str]:
    sys_cmd = systemctl_args_builder(
        *cmd, mode=mode, units=units, sudo=sudo, ask_password=ask_password
    )
    if foreground:
        show_command(*sys_cmd)
    proc = await asyncio.create_subprocess_exec(
        *sys_cmd,
        stdout=None if foreground else asyncio.subprocess.PIPE,
        stderr=None if foreground else asyncio.subprocess.PIPE,
        env=env_with_color(),
        stdin=None if foreground else subprocess.DEVNULL,
    )
    # maxlen appending works as a fifo.
    stdout_deque: Deque[bytes] = Deque(maxlen=head)
    if proc.stdout is not None:
        i = 0
        async for line in proc.stdout:
            stdout_deque.append(line.rstrip())
            i += 1
            if i == head:
                break
    stderr_deque: Deque[bytes] = Deque(maxlen=head)
    if proc.stderr is not None:
        i = 0
        async for line in proc.stderr:
            stderr_deque.append(line.rstrip())
            i += 1
            if i == head:
                break

    # I believe that will read everything until EOF
    stdout = "\n".join(byte_line.decode() for byte_line in stdout_deque)
    stderr = "\n".join(byte_line.decode() for byte_line in stderr_deque)
    return_code = await proc.wait()
    return return_code, stdout, stderr


def systemctl_args_builder(
    *cmd: str,
    mode: str,
    units: Iterable[str],
    sudo: bool = False,
    ask_password: bool = True,
) -> List[str]:
    sys_cmd: List[str] = list()
    if sudo and not is_root():
        # if `sudo = True` only prefix if process isn't running as `root` user.
        #
        # -> -E/--preserve-env/--preserve-env=[...] may be disallowed for a given user.
        # it is more "robust" to inject the environment variables to the command line.
        # No! There are _many_ VSCode extensions that shouldn't be trusted.
        # FUTURE: Implement a _custom_ `systemd edit` wrapper that opens an
        # override file from USER space and then only copies the file with elevated
        # privileges. This avoids _all_ of the environment forwarding and editor trust issues.
        sys_cmd.extend(["sudo", "--stdin", "-E"])
    sys_cmd.append(get_systemctl_bin())
    if not ask_password:
        # TODO: Ensure that this works with older versions.
        sys_cmd.append("--no-ask-password")
    if mode == "user":
        # `root` user _may_ have user services (https://github.com/kainctl/isd/issues/30)
        # if sudo or is_root():
        #     raise ValueError("user mode is not allowed when running as root!")
        sys_cmd.extend(
            [
                "--user",
                *cmd,
                "--",
            ]
        )
    else:
        sys_cmd.extend(
            [
                *cmd,
                "--",
            ]
        )
    sys_cmd.extend(units)
    return sys_cmd


def journalctl_args_builder(
    *args: str, mode: str, units: Iterable[str], sudo: bool = False
) -> List[str]:
    sys_cmd = []
    if sudo and not is_root():
        # if `sudo = True` only prefix if process isn't running as `root` user.
        #
        # -> -E/--preserve-env/--preserve-env=[...] may be disallowed for a given user.
        # it is more "robust" to inject the environment variables to the command line.
        # No! There are _many_ VSCode extensions that shouldn't be trusted.
        # FUTURE: Implement a _custom_ `systemd edit` wrapper that opens an
        # override file from USER space and then only copies the file with elevated
        # privileges. This avoids _all_ of the environment forwarding and editor trust issues.
        sys_cmd.extend(["sudo", "--stdin", "-E"])
    if mode == "user":
        sys_cmd.extend(["journalctl", "--user"])
    else:
        sys_cmd.extend(["journalctl"])

    return list(
        chain(
            sys_cmd,
            args,
            *zip(repeat("--unit"), units),
        )
    )


def env_with_color() -> Dict[str, str]:
    env = os.environ.copy()
    # systemd_colors = "1" if colors else "0"
    env.update(SYSTEMD_COLORS="1")
    return env


# may have additional opts in the future
# In the future, I need to potentially figure out how to handle async piping
async def journalctl_async(
    *args: str,
    mode: str,
    units: Iterable[str],
    sudo: bool = False,
    tail: Optional[int] = None,
) -> Tuple[int, str, str]:
    journalctl_cmd = journalctl_args_builder(*args, mode=mode, units=units, sudo=sudo)
    env = env_with_color()
    # env = os.environ.copy()
    # env.update(SYSTEMD_COLORS="1")
    proc = await asyncio.create_subprocess_exec(
        *journalctl_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    stdout_deque: Deque[bytes] = Deque(maxlen=tail)
    if proc.stdout is not None:
        async for line in proc.stdout:
            stdout_deque.append(line.rstrip())
        # I believe that will read everything until EOF
    stderr_deque: Deque[bytes] = Deque(maxlen=tail)
    if proc.stdout is not None:
        async for line in proc.stdout:
            stderr_deque.append(line.rstrip())

    stdout = "\n".join(byte_line.decode() for byte_line in stdout_deque)
    stderr = "\n".join(byte_line.decode() for byte_line in stderr_deque)
    return_code = await proc.wait()

    # this shouldn't error
    return (return_code, stdout, stderr)


class Preview(RichLog, inherit_bindings=False):
    """
    `RichLog` with custom bindings and 'captive' scrolling.
    If the output fits onto the presented screen, scrolling does _not_
    bubble to the parent.
    """

    def __init__(self, navigation_keybindings: NavigationKeybindings, **kwargs):
        super().__init__(**kwargs)
        for keys, action, description in [
            (navigation_keybindings.down, "scroll_down", "Down"),
            (navigation_keybindings.up, "scroll_up", "Up"),
            (navigation_keybindings.left, "scroll_left", "Left"),
            (navigation_keybindings.right, "scroll_right", "Right"),
            (navigation_keybindings.page_up, "page_up", "Page Up"),
            (navigation_keybindings.page_down, "page_down", "Page Down"),
            (navigation_keybindings.top, "scroll_home", "First"),
            (navigation_keybindings.bottom, "scroll_end", "Last"),
            (navigation_keybindings.page_left, "page_left", "Page Left"),
            (navigation_keybindings.page_right, "page_right", "Page Right"),
        ]:
            self._bindings.bind(
                keys=keys,
                action=action,
                description=description,
                show=False,
            )

    @property
    def allow_vertical_scroll(self) -> bool:
        if self._check_disabled():
            return False
        return True

    @property
    def allow_horizontal_scroll(self) -> bool:
        if self._check_disabled():
            return False
        return True


class PreviewArea(Container):
    """
    The preview area.
    If the active tab changes, a `TabActivated` message is sent
    with a id/name of the new tab.
    """

    # FUTURE: Implement a 'smart' line-wrap for systemctl status/cat output
    # track the leading chars and auto-indent with the journalctl indent characters

    units: reactive[List[str]] = reactive(list())
    mode: reactive[str] = reactive("system")

    def __init__(
        self,
        *args,
        max_lines: int,
        navigation_keybindings: NavigationKeybindings,
        journalctl_args: list[str],
        **kwargs,
    ) -> None:
        self.max_lines = max_lines
        self.journalctl_args = journalctl_args
        self.navigation_keybindings = navigation_keybindings
        super().__init__(*args, **kwargs)
        self._bindings.bind(navigation_keybindings.right, "next_tab")
        self._bindings.bind(navigation_keybindings.left, "previous_tab")

    def on_mount(self) -> None:
        self.last_output = Text("")
        # Could disable `can_focus` on `ContentTabs` or to avoid loading
        # from a private module `Tabs`
        # (though it is `ContentTabs` if one looks at the `console log` output).
        # This ensure that the header itself cannot be focused.
        # This also implies that the first child widget of the
        # `TabbedContent` is focused!
        # Requires `on_click` to forward the focus to the preview.
        # self.query_one(Tabs).can_focus = False

    def watch_mode(self, mode: str) -> None:
        self.update_preview_window()

    def watch_units(self, units: List[str]) -> None:
        self.update_preview_window()

    def on_tabbed_content_tab_activated(self, _tab) -> None:
        self.update_preview_window()

    def focus_preview(self) -> None:
        """
        Focuses the current `Preview` output.

        Note: If `action_next_tab` is called within the same
        update cycle, calling this function will see the _old_
        pane. In this instance, you probably want to call it via
        `call_after_refresh`.
        """
        tabbed_content: TabbedContent = self.query_one(TabbedContent)
        cur_pane = tabbed_content.active_pane

        if cur_pane:
            cur_pane.query_one(Preview).focus()

    def action_next_tab(self) -> None:
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_next_tab()

    def action_previous_tab(self) -> None:
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()

    @work(exclusive=True, group="preview_area_preview_window")
    async def update_preview_window(self) -> None:
        """
        Update the current preview window.
        It only updates the currently selected preview window/tab
        to avoid spamming subprocesses.
        """
        if len(self.units) == 0:
            return

        # FUTURE:
        # This smart refresh is an okay-ish solution.
        # The better solution would be to implement a textarea that
        # can allow basic highlighting/copy pasting and searching.
        # Then I would only update the lines that have changed, which would make the updates
        # much less aggressive.
        tabbed_content = cast(TabbedContent, self.query_one(TabbedContent))
        match tabbed_content.active:
            case "status":
                preview = tabbed_content.query_one("#status_log", RichLog)
                # preview = cast(RichLog, self.query_one(PreviewStatus))
                # FUTURE: Expand on the functionality from _from_ansi
                # to open URLs or man pages, maybe skip if unknown
                return_code, stdout, stderr = await systemctl_async(
                    "status",
                    mode=self.mode,
                    units=self.units,
                    head=self.max_lines,
                )
            case "dependencies":
                preview = tabbed_content.query_one("#dependencies_log", RichLog)
                # FUTURE: Expand on the functionality from _from_ansi
                # to open URLs or man pages, maybe skip if unknown
                return_code, stdout, stderr = await systemctl_async(
                    "list-dependencies",
                    mode=self.mode,
                    units=self.units,
                    head=self.max_lines,
                )
            case "help":
                preview = tabbed_content.query_one("#help_log", RichLog)
                # FUTURE: Expand on the functionality from _from_ansi
                # to open URLs or man pages, maybe skip if unknown
                return_code, stdout, stderr = await systemctl_async(
                    "help", mode=self.mode, units=self.units, head=self.max_lines
                )
            case "show":
                preview = tabbed_content.query_one("#show_log", RichLog)
                return_code, stdout, stderr = await systemctl_async(
                    "show", mode=self.mode, units=self.units, head=self.max_lines
                )
            case "cat":
                preview = tabbed_content.query_one("#cat_log", RichLog)
                return_code, stdout, stderr = await systemctl_async(
                    "cat", mode=self.mode, units=self.units, head=self.max_lines
                )
            case "journal":
                preview = tabbed_content.query_one("#journal_log", RichLog)
                return_code, stdout, stderr = await journalctl_async(
                    *self.journalctl_args,
                    mode=self.mode,
                    units=self.units,
                    tail=self.max_lines,
                )
            case other:
                self.notify(f"Unknown state {other}", severity="error")
                return
        # style it like systemctl from CLI
        # For example, previewing a template file with `status` raises
        # an error but it shouldn't "cover" stdout.
        output = Text.from_ansi(stdout if stderr == "" else stderr + "\n" + stdout)
        # Not sure if this comparison makes it slower or faster
        if output != self.last_output:
            preview.clear()
            preview.write(output)
            self.last_output = output

    def compose(self) -> ComposeResult:
        # FUTURE: Use custom enum classes for the preview id and tab-pane
        # id mapping
        with TabbedContent():
            with TabPane("Status", id="status"):
                yield Preview(
                    id="status_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Journal", id="journal"):
                yield Preview(
                    id="journal_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=True,
                )

            with TabPane("Cat", id="cat"):
                yield Preview(
                    id="cat_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Dependencies", id="dependencies"):
                yield Preview(
                    id="dependencies_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Show", id="show"):
                yield Preview(
                    id="show_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Help", id="help"):
                yield Preview(
                    id="help_log",
                    navigation_keybindings=self.navigation_keybindings,
                    auto_scroll=False,
                )


def derive_startup_mode(startup_mode: StartupMode) -> str:
    mode: str
    if startup_mode == StartupMode("auto"):
        fallback: StartupMode = StartupMode("user")
        fp = get_isd_cached_state_json_file_path()
        if fp.exists():
            mode = json.loads(fp.read_text()).get("mode", fallback)
        else:
            mode = fallback
    else:
        mode = startup_mode
    if mode == "user" and is_root():
        if systemctl_is_system_running(mode="user").returncode == 0:
            return "user"
        else:
            # If it is not possible to connect to the `root` users `--user` bus,
            # fallback to system
            return "system"
    return mode


def cached_search_term() -> str:
    fp = get_isd_cached_state_json_file_path()
    if fp.exists():
        return json.loads(fp.read_text()).get("search_term", "")
    return ""


def systemctl_is_system_running(*, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        systemctl_args_builder("is-system-running", mode=mode, units=[]),
        capture_output=True,
        text=True,
    )


# class SettingsError(ModalScreen):
#     def __init__(
#         self, settings: Settings, exception: Exception, *args, **kwargs
#     ) -> None:
#         self.settings = settings
#         self.exception = exception
#         super().__init__(*args, **kwargs)

#     def compose(self):
#         tb = Traceback.from_exception(Exception, self.exception)
#         yield RichLog().write(tb)
#         yield CustomOptionList(
#             self.settings.navigation_keybindings,
#             "option1",
#             "option2",
#             # continue with default settings
#             # copy error message to clipboard
#         )


class MainScreen(Screen):
    # Zellij writes some weird output to the input otherwise.
    # If this is `None` it may lead to weird flashes in the footer.
    # Zellij users have to live with it until the bug is
    # fixed: https://github.com/zellij-org/zellij/issues/3959
    AUTO_FOCUS = "CustomInput" if os.getenv("ZELLIJ") is None else None

    unit_to_state_dict: reactive[Dict[str, UnitReprState]] = reactive(dict())
    # Relevant = Union(ordered selected units & highlighted unit)
    relevant_units: Deque[str] = deque()
    search_term: str = ""
    search_results: list[Dict[str, Any]] = list()
    status_text: reactive[str] = reactive("")
    # `mode` is immediately overwritten. It simply acts a sensible default
    # to make type-checkers happy.
    mode: reactive[str] = reactive("system")
    ordered_selection: Deque[str] = deque()
    highlighted_unit: Optional[str] = None
    _tracked_keybinds: Dict[str, str] = dict()

    def __init__(self, settings, *args, **kwargs) -> None:
        self.settings = settings
        super().__init__(*args, **kwargs)
        self.update_keybindings()

    def update_keybindings(self) -> None:
        # update keybindings
        for command in self.settings.systemctl_commands:
            action = f"systemctl_command('{command.command}')"
            direct_keybind = command.direct_keybinding
            if direct_keybind is not None:
                self._bindings.bind(
                    keys=direct_keybind,
                    action=action,
                    description=command.description,
                    show=False,
                )
        main_keybindings = self.settings.main_keybindings
        show_fields = [
            "open_preview_in_pager",
            "open_preview_in_editor",
            "toggle_mode",
        ]
        model_fields = MainKeybindings.model_fields
        assert all([show_field in model_fields for show_field in show_fields]), (
            "Forgot to update show_field"
        )
        for action, field in model_fields.items():
            # name of keybinding == action name and
            # description is used for binding description
            keys = getattr(main_keybindings, action)

            self._bindings.bind(
                keys,
                action,
                description=getattr(field, "description", ""),
                # yeah, this is kinda hacky, but I only want a few items
                # to be shown in the footer. Adding it to the configuration
                # is too verbose and complicates the design
                show=action in show_fields,
            )

    def system_commands(self):
        """
        Yields `SystemCommand`s that are specific for this screen.
        """
        for systemctl_command in self.settings.systemctl_commands:
            shortcut_txt = (
                ""
                if systemctl_command.direct_keybinding is None
                else f" (Shortcut: {systemctl_command.direct_keybinding})"
            )
            yield SystemCommand(
                "systemctl " + systemctl_command.command,
                systemctl_command.description + f"{shortcut_txt}",
                # partial(self.exec_systemctl_command, systemctl_command.command),
                partial(self.action_systemctl_command, systemctl_command.command),
            )

        for action in self.settings.main_keybindings.model_fields.keys():
            keys = getattr(self.settings.main_keybindings, action)
            yield SystemCommand(
                action.replace("_", " ").title(),
                f"Shortcut: {keys}",
                eval(f"self.action_{action}"),
            )

    # FUTURE:
    # Add a 'systemd' page/screen that shows the overall status of the system
    # and potentially also the environment variables.
    # Take a look at the environment commands, as they might be helpful
    # FUTURE: Figure out how to work with/handle --global
    # FUTURE: Add option to list the most recently failed units.
    #         -> This should be a global option, as this is a frequent use-case.

    def _step_preview_tab(self, *, next: bool):
        prev_focus = self.focused
        preview_area = self.query_one(PreviewArea)
        if next:
            preview_area.action_next_tab()
        else:
            preview_area.action_previous_tab()
        if prev_focus and isinstance(prev_focus, Preview):
            self.call_after_refresh(preview_area.focus_preview)

    def action_next_preview_tab(self) -> None:
        self._step_preview_tab(next=True)

    def action_previous_preview_tab(self) -> None:
        self._step_preview_tab(next=False)

    def action_clear_input(self) -> None:
        """
        Clear the input from the input widget
        and switch focus to it.
        """
        inp = cast(CustomInput, self.query_one(CustomInput))
        inp.clear()
        inp.focus()

    def action_jump_to_input(self) -> None:
        """
        Switch focus to the search input.
        """
        inp = cast(CustomInput, self.query_one(CustomInput))
        inp.focus()

    def _change_widget_height_fraction(self, value: int):
        """
        Change the height fraction of the widget if possible.
        Will increase/decrease the fraction by the given value.
        This function ensures that the mininum value is 1.
        """

        def __change_widget_height_fraction(widget: Widget, value: int):
            if widget.styles.height is not None:
                if widget.styles.height.is_fraction is not None:
                    height = widget.styles.height
                    new_value = max(height.value + value, 1)
                    widget.styles.height = height.copy_with(value=new_value)

        search_results = self.query_one(CustomSelectionList)
        preview_area = self.query_one(PreviewArea)

        if preview_area.has_focus or preview_area.has_focus_within:
            __change_widget_height_fraction(preview_area, value)
        if search_results.has_focus or search_results.has_focus_within:
            __change_widget_height_fraction(search_results, value)

    def action_increase_widget_height(self) -> None:
        """
        Increase the height of the search results or preview
        widget. Depending if one of them is focused or not.
        """
        self._change_widget_height_fraction(+1)

    def action_decrease_widget_height(self) -> None:
        """
        Decrease the height of the search results or preview
        widget. Depending if one of them is focused or not.
        """
        self._change_widget_height_fraction(-1)

    def store_state(self) -> None:
        """
        Store the current application state.
        """
        json_state = json.dumps({"mode": self.mode, "search_term": self.search_term})

        if not is_root():
            fp_cache_state = get_isd_cached_state_json_file_path()
            # directory may not exist if there was a previous issue while creating them
            if fp_cache_state.parent.exists():
                try:
                    fp_cache_state.write_text(json_state)
                except Exception as e:
                    print(f"Exception: {e} while writing state to: {fp_cache_state}")

    # There isn't really any additional foreground commands apart from
    # edit that are useful. All the other ones are encoded as preview windows.
    # The other inspection tools such as systemd-analyze derivatives should be
    # their own application. Or could be a future extension that could be
    # out-sourced.
    # https://github.com/systemd/systemd/pull/30302
    # https://github.com/systemd/systemd/issues/21862
    # pseudopty cannot really split out the stdout/stderr streams
    # and that would produce a mess for my output.
    # No, I think I need to be a bit more creative.
    # systemd edit seems to be "smart" an only raise the TTY error message
    # _after_ all the other checks have passed!
    # As such, I can run a quick 'test' and check the output and only foreground
    # the application if the error message contains the 'magic' tty error.
    # Nah, too complicated.
    #
    # 1. Allow two different authentication modes: sudo OR polkit (config)
    # 2. Read from config which commands require "root" (yes, this may be different for each environment)
    #    If no  -> run with as is -> if this is wrong, the output will complain about missing polkit authentication
    #           -> inform the user about mistake & suggest to fix config.
    #           -> Continue with 'yes' logic
    #    If yes -> run with sudo and no foreground & see if caching is required
    #             -> if it fails, then run it in the foreground
    #           -> in polkit mode, run it directly in the foreground
    # Somebody _could_ run the entire authentication as _root_. Then it should
    # skip over asking for a password. To provide good support for "old fashioned"
    # users. Though I would like to give users a warning that are running this program as root,
    # as it is scary.
    # -> Running as root should _imply_ polkit mode as there is no need to prefix anything with sudo!
    #
    # The asking should ONLY happen here! In the other functions, the error text should be reported
    # in the preview. Again, if the command requires additional authentication, is something
    # that needs to be defined by the user.
    async def action_systemctl_command(self, unsplit_command: str) -> None:
        """
        Split the given `systemctl` subcommand (`unsplit_command`) by whitespaces and
        execute the command in the background.

        By enforcing `systemctl` as the prefix and making sure that no shell
        injection can be done, it should be fairly secure/safe.
        """
        command = unsplit_command.split()
        # first I need to check if this is systemctl edit
        # if it is edit then I need to change the async commands to foreground
        # commands with a foreground TTY!
        if "edit" in unsplit_command:
            # since this MUST run in the foreground and I CANNOT capture stderr
            # I am calling it directly with sudo if the current mode is `system`:
            # In polkit mode, it will probably fail due to filesystem permissions errors,
            # even if the unit could be "modified" by the current user.
            # Since `edit` is such an weird outlier, enforcing `sudo` in this instance
            # is probably the most straight-forward solution IF the mode is `system`!
            # In `user` mode, there should never be a reason to prefix it with sudo!
            with self.app.suspend():
                args = systemctl_args_builder(
                    *command,
                    mode=self.mode,
                    units=self.relevant_units,
                    sudo=self.mode == "system",
                )
                show_command(*args)
                subprocess.call(args)
                input("Print any button to continue")
        else:
            # Try to run command as-is.
            return_code, stdout, stderr = await systemctl_async(
                *command,
                mode=self.mode,
                units=self.relevant_units,
                sudo=False,
            )
            # if it fails, check if there was an authentication issue
            # and prefix it with sudo or explicitly wait for polkit authentication.
            if return_code != 0:
                if "auth" in stderr:
                    if AUTHENTICATION_MODE == "sudo":
                        # first try again with sudo and see
                        # if previous cached password works
                        # invalidate with sudo --reset-timestamp
                        return_code, stdout, stderr = await systemctl_async(
                            *command,
                            mode=self.mode,
                            units=self.relevant_units,
                            sudo=True,
                            foreground=False,
                        )
                        if return_code == 1:
                            with self.app.suspend():
                                return_code, stdout, stderr = await systemctl_async(
                                    *command,
                                    mode=self.mode,
                                    units=self.relevant_units,
                                    sudo=True,
                                    foreground=True,
                                )
                    else:
                        with self.app.suspend():
                            return_code, stdout, stderr = await systemctl_async(
                                *command,
                                mode=self.mode,
                                units=self.relevant_units,
                                sudo=False,
                                foreground=True,
                                ask_password=True,
                            )
                else:
                    self.notify(
                        f"Unexpected error:\n{Text.from_ansi(stderr)}",
                        severity="error",
                        timeout=30,
                    )
        # FUTURE: Provide different colored outputs depending on the exit code.
        # Potentially also include the error output.
        self.notify(f"Executed `systemctl {unsplit_command}`")
        self.partial_refresh_unit_to_state_dict()
        self.refresh()

    async def watch_mode(self, mode: str) -> None:
        self.query_one(PreviewArea).mode = mode
        # clear current selection
        sel = cast(SelectionList, self.query_one(SelectionList))
        sel.deselect_all()
        self.query_one(Fluid).border_title = " " + mode + " "
        await self.new_unit_to_state_dict()
        # self.query_one(Vertical).border_title = self.mode
        # await self.update_unit_to_state_dict()

    def action_copy_unit_path(self) -> None:
        # load the fragment path from the `systemctl cat output`
        # FUTURE: Fix to currently highlighted one!
        if self.highlighted_unit is None:
            return
        # Copying multiple ones doesn't make much sense!
        args = systemctl_args_builder(
            "show", mode=self.mode, units=[self.highlighted_unit]
        )
        p1 = subprocess.run(args, capture_output=True, text=True)
        path = next(
            line.split("=", 1)[1]
            for line in p1.stdout.splitlines()
            if line.startswith("FragmentPath=")
        )
        self.app.copy_to_clipboard(path)
        self.notify(f"Copied '{path}' to the clipboard.")

    def action_toggle_mode(self) -> None:
        """
        Toggle the current `bus`.
        Try to protect the user from accidentally crashing the program by trying
        to access the `--user` bus from the `root` user. But I still have to
        allow access, as some have user services configured for the `root` user:

        - <https://github.com/kainctl/isd/issues/30>
        """
        if is_root() and self.mode == "system":
            # Test if `root` user can actually connect to a `--user` bus.
            proc = systemctl_is_system_running(mode="user")
            if proc.returncode != 0:
                self.notify(
                    "Could not connect to `root` users `--user` bus.\n"
                    + "Usually, this does not work, as the `root` user does not have any `user` services.\n"
                    + "The connection was tested via `systemctl --user is-system-running` as `root` user with the full error message below:\n\n"
                    + proc.stderr,
                    severity="error",
                    timeout=60,
                )
                return

        self.mode = "system" if self.mode == "user" else "user"

    # FUTURE: Maybe split out this logic and make it easier to retrieve the output
    # directly from the tabbed output. Though pay attention that the preview window
    # might generate different output in the future with smart wrapping or truncating.
    # I should just switch the logic associated to it.
    def preview_output_command_builder(self, cur_tab: str) -> List[str]:
        if cur_tab == "status":
            # FUTURE: Consider allowing tuning `--lines` or using `--full`
            # but remember that this is only relevant for current in-memory or last
            # invocation. Otherwise one should always use journalctl
            args = systemctl_args_builder(
                "status", mode=self.mode, units=self.relevant_units
            )
        elif cur_tab == "show":
            args = systemctl_args_builder(
                "show", mode=self.mode, units=self.relevant_units
            )
        elif cur_tab == "cat":
            # note that cat refers to the content on disk.
            # if there is a missing daemon-reload then there will be a difference!
            args = systemctl_args_builder(
                "cat", mode=self.mode, units=self.relevant_units
            )
        elif cur_tab == "dependencies":
            args = systemctl_args_builder(
                "list-dependencies", mode=self.mode, units=self.relevant_units
            )
        elif cur_tab == "help":
            args = systemctl_args_builder(
                "help", mode=self.mode, units=self.relevant_units
            )
        else:  # journal
            journalctl_args = self.settings.journalctl_args
            # FUTURE:
            # journalctl --follow _should_ be a valid option!
            # But currently it freezes the window after the journal preview
            # was opened.
            # if this is opened in the preview, it should run
            # with follow!
            # if "--follow" not in journalctl_args:
            #     journalctl_args.append("--follow")

            args = journalctl_args_builder(
                *journalctl_args,
                mode=self.mode,
                units=self.relevant_units,
            )
        return args

    # TODO: Does it make sense to load preview_output_command_builder ?
    # Yes, it does since it loads it from the TabbedContent, but it should
    # then derive the required sudo state again.
    # -> Maybe it would be smarter to forward this logic to the main loop?
    def action_open_preview_in_pager(self) -> None:
        cur_tab = cast(TabbedContent, self.query_one(TabbedContent)).active

        if cur_tab == "journal":
            pager = (
                get_systemd_pager()
                if self.settings.journal_pager == "auto"
                else self.settings.journal_pager
            )
            pager_args = get_journal_pager_args_presets(pager)
        else:
            pager = (
                get_systemd_pager()
                if self.settings.default_pager == "auto"
                else self.settings.default_pager
            )
            pager_args = get_default_pager_args_presets(pager)

        with self.app.suspend():
            cmd_args = self.preview_output_command_builder(cur_tab)
            env = env_with_color()
            p1 = subprocess.Popen(
                cmd_args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            if p1.stdout is not None:
                # for true `more` support I must inject the following
                # environment variable but make sure to not bleed it here!
                # os.environ["POSIXLY_CORRECT"] = "NOT_EMPTY"
                subprocess.call([pager, *pager_args], stdin=p1.stdout)
                subprocess.call("clear")
            else:
                self.notify("Preview was empty.", severity="information")
        self.refresh()

    def action_open_preview_in_editor(self) -> None:
        cur_tab = cast(TabbedContent, self.query_one(TabbedContent)).active
        editor = cast(InteractiveSystemd, self.app).editor
        with self.app.suspend():
            args = self.preview_output_command_builder(cur_tab)
            p1 = subprocess.run(
                args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            with tempfile.NamedTemporaryFile() as tmp_file:
                p = Path(tmp_file.name)
                p.write_text(
                    # capture_output appends a newline to non-empty stderr!
                    p1.stdout
                )
                subprocess.call([editor, p.absolute()])
        self.refresh()

    async def on_mount(self) -> None:
        self.set_interval(
            self.settings.preview_and_selection_refresh_interval_sec,
            self.partial_refresh_unit_to_state_dict,
        )
        self.set_interval(
            self.settings.preview_and_selection_refresh_interval_sec,
            self.refresh_preview,
        )
        self.set_interval(
            self.settings.full_refresh_interval_sec,
            self.full_refresh_unit_to_state_dict,
        )
        self.mode = derive_startup_mode(self.settings.startup_mode)
        await self.new_unit_to_state_dict()
        self.search_results = await self.search_units(self.search_term)
        self.query_one(
            CustomSelectionList
        ).styles.height = f"{self.settings.search_results_height_fraction}fr"
        self.query_one(
            PreviewArea
        ).styles.height = f"{self.settings.preview_height_fraction}fr"

    def on_input_changed(self, event: CustomInput.Changed) -> None:
        self.search_term = event.value
        self.debounced_search_units(self.search_term)

    def on_input_submitted(self, _: CustomInput.Submitted) -> None:
        sel = self.query_one(CustomSelectionList)
        sel.focus()

    def update_relevant_units(self) -> None:
        # With exclusive=True, I should make sure to NOT use parameters!
        # Since the provided parameters could become out-dated.
        # Future: Make this the preview settings!
        units = deque(self.ordered_selection)
        # this check is only for the first iteration
        # where the highlight is None
        if self.highlighted_unit is not None:
            if self.highlighted_unit in units:
                units.remove(self.highlighted_unit)
            units.appendleft(self.highlighted_unit)
        assert len(units) == len(set(units))
        self.relevant_units = units

    @work(exclusive=True, group="main_preview_window")
    async def refresh_preview(self) -> None:
        await asyncio.sleep(self.settings.updates_throttle_sec)
        if len(self.relevant_units) > 0:
            preview_area = self.query_one(PreviewArea)
            preview_area.units = list(self.relevant_units)
            preview_area.mutate_reactive(PreviewArea.units)

    async def watch_unit_to_state_dict(
        self, unit_to_state_dict: Dict[str, UnitReprState]
    ) -> None:
        # if it has been correctly initialized
        if len(unit_to_state_dict) != 0:
            await self.refresh_selection()
        self.refresh_preview()

    @on(CustomSelectionList.SelectedChanged)
    async def process_selection(
        self, event: CustomSelectionList.SelectedChanged
    ) -> None:
        prev_sel = self.ordered_selection
        selected = event.selection_list.selected
        assert len(set(prev_sel)) == len(prev_sel)
        assert len(set(selected)) == len(selected)

        # Keep the original selection ordering
        ordered_selection = deque(item for item in prev_sel if item in selected)
        # Add new selection to the front of the list
        ordered_selection.extendleft(item for item in selected if item not in prev_sel)
        assert set(ordered_selection) == set(selected)
        self.ordered_selection = ordered_selection
        # Technically, the following is _not_ required.
        # Even if the selection is updated, it can only be selected by being
        # highlighted first. In this case, the `relevant_units` does not change!
        self.update_relevant_units()
        self.refresh_preview()

    @on(CustomSelectionList.SelectionHighlighted)
    def process_highlight(
        self, event: CustomSelectionList.SelectionHighlighted
    ) -> None:
        self.highlighted_unit = event.selection.value
        self.update_relevant_units()

        if self.highlighted_unit is not None:
            # throttle since highlighted unit can change quite quickly
            # updating it since the current highlighted value should _always_
            # show the _current_ state of the unit!
            self.throttled_refresh_unit_to_state_dict_worker()

        self.refresh_preview()

    async def search_units(self, search_term: str) -> list[Dict[str, Any]]:
        # haystack MUST be a local copy as it mutates the data in-place!
        haystack = [u for u in self.unit_to_state_dict.keys()]
        # self.search_results = await fuzzy_match(search_term.replace(" ", ""), haystack)
        return await fuzzy_match(search_term.replace(" ", ""), haystack)

    @work(exclusive=True, group="search_units")
    async def debounced_search_units(self, search_term: str) -> None:
        await asyncio.sleep(self.settings.updates_throttle_sec)
        self.search_results = await self.search_units(search_term)
        # Should the selection be always refreshed? I would argue yes.
        # The computation is fairly cheap and caching costs probably more.
        await self.refresh_selection()

    # let's assume that we have the search results stored in a reactive variable
    # then update_selection does NOT require a search_term variable
    # it _could_ cache the pre-build matches list, but I think that it something
    # for later
    #
    async def refresh_selection(self) -> None:
        """
        Clears the current selection and
        finds the units from the `unit_to_state_dict` that
        are given in the `matches` list.
        These matches are then added to the selection.
        Previous selected units are kept as is and those that
        were selected but aren't part of the selection anymore are
        _prepended_ as a user is most likely interested in interacting
        with them.

        This _may_ trigger a new highlighted value to be set!

        Call this function within a function that has a debounce set!
        """
        # Maybe: Rewrite the function to only use parameters for clarity!
        sel = cast(SelectionList, self.query_one(SelectionList))
        prev_selected = sel.selected
        prev_highlighted = (
            sel.get_option_at_index(sel.highlighted)
            if sel.highlighted is not None
            else None
        )

        sel.clear_options()
        match_dicts = self.search_results
        matches = [
            Selection(
                prompt=self.unit_to_state_dict[d["value"]].render_state(
                    d["value"], d["indices"]
                ),
                value=d["value"],
                initial_state=d["value"] in prev_selected,
                id=d["value"],
            )
            for d in match_dicts
        ]
        matched_units = [d["value"] for d in match_dicts]
        # first show the now "unmatched" selected units,
        # otherwise they might be hidden by the scrollbar
        prev_selected_unmatched_units = [
            Selection(
                prompt=self.unit_to_state_dict[unit].render_state(unit),
                value=unit,
                initial_state=True,
                id=unit,
            )
            for unit in prev_selected
            if unit not in matched_units
        ]
        sel.add_options(prev_selected_unmatched_units)
        sel.add_options(matches)

        # FUTURE: Improve the following code snippet

        # If a previous unit was highlighted, get its ID
        # and check if it is part of the previous selected units OR
        # in the matched units. In this case, keep highlighting the
        # _same_ unit even if the position changes!
        if (
            prev_highlighted is not None
            and prev_highlighted.id is not None
            and (
                prev_highlighted.id in prev_selected_unmatched_units
                or prev_highlighted.id in matched_units
            )
        ):
            new_highlight_position = sel.get_option_index(prev_highlighted.id)
            # FUTURE: Maybe even jump to the highlight if required?
        else:
            # Apply the following logic to find the new highlight:
            # Since the previous selected units that aren't part of the
            # current search are prepended to the list, jump with the
            # highlighting to the best "matching" unit!
            # The following seems to work, even if the search is empty.
            new_highlight_position = len(prev_selected_unmatched_units)

        sel.highlighted = new_highlight_position

    def partial_refresh_unit_to_state_dict(self) -> None:
        self.refresh_unit_to_state_dict_worker(*self.relevant_units)

    def full_refresh_unit_to_state_dict(self) -> None:
        self.refresh_unit_to_state_dict_worker()

    async def new_unit_to_state_dict(self) -> None:
        self.unit_to_state_dict = await load_unit_to_state_dict(self.mode)
        # also needs to update the search_results, since we may now have
        # _more_ results _or_ completely different results if the mode was switched!
        self.search_results = await self.search_units(self.search_term)
        self.mutate_reactive(MainScreen.unit_to_state_dict)

    @work(exclusive=True, group="refresh_unit_to_state_dict")
    async def throttled_refresh_unit_to_state_dict_worker(self) -> None:
        """
        Will throttle the calls to `refresh_unit_to_state_dict_worker`.
        This should be done whenever many partial updates are expected.
        """
        await asyncio.sleep(self.settings.updates_throttle_sec)
        self.refresh_unit_to_state_dict_worker(*self.relevant_units)

    @work()
    async def refresh_unit_to_state_dict_worker(self, *units: str) -> None:
        """
        Refreshes the `unit_to_state_dict` by reloading the states of the
        given `units`. If some of the provided `units` cannot be found, set those
        `units` in the `unit_to_state_dict` as `not_found`.

        If no units are given, then it will refresh ALL units.

        This is a worker since it might take a long time until
        `load_unit_to_state_dict` has returned.
        But it should NOT be exclusive! If there is one full refresh queued
        and after it a partial update, then the full refresh might be interrupted!
        """
        local_unit_to_state_dict = deepcopy(self.unit_to_state_dict)
        partial_unit_to_state_dict = await load_unit_to_state_dict(self.mode, *units)
        for unit in partial_unit_to_state_dict:
            local_unit_to_state_dict[unit] = partial_unit_to_state_dict[unit]

        for unit in set(units) - partial_unit_to_state_dict.keys():
            local_unit_to_state_dict[unit] = UnitReprState.not_found

        if local_unit_to_state_dict != self.unit_to_state_dict:
            # Using `update` and not simple `=` as multiple accesses could
            # happen at the same time! I do not want to loose updates to
            # new keys!
            self.unit_to_state_dict.update(local_unit_to_state_dict)
            self.mutate_reactive(MainScreen.unit_to_state_dict)
            # unit_to_state_dict watcher calls update_selection!

    # FUTURE: Evaluate if updating the self values in compose makes sense.
    def compose(self) -> ComposeResult:
        # search_term is used in the following input function
        if self.settings.cache_input:
            self.search_term = cached_search_term()

        yield Header()
        with Fluid():
            with Vertical():
                yield CustomInput(
                    value=self.search_term,
                    placeholder="Type to search...",
                    id="search_input",
                )
                yield CustomSelectionList(
                    navigation_keybindings=self.settings.navigation_keybindings,
                    id="unit-selection",
                )
                yield PreviewArea(
                    max_lines=self.settings.preview_max_lines,
                    journalctl_args=self.settings.journalctl_args,
                    navigation_keybindings=self.settings.navigation_keybindings,
                )
        yield Footer()


class InteractiveSystemd(App, inherit_bindings=False):
    """
    The textual `App` that loads the settings and controls the screens.

    The bindings are controlled by the dedicated screens!
    """

    TITLE = "isd"
    # CSS_PATH = "dom.tcss"
    CSS_PATH = CSS_RESOURCE_PATH
    COMMAND_PALETTE_BINDING = ensure_reserved("ctrl+p")
    NOTIFICATION_TIMEOUT = 5
    # If the modal is dismissed, this App would be focused by default
    # for a split second.
    # Causing the footer to flash the `App`s footer before updating
    # itself to the focused widget.
    # Disabling auto-focus solves this issue.
    AUTO_FOCUS = None

    # posting defines the `Binding`s manually here via `BINDINGS`
    # and then runs self.set_keymap(self.settings.keymap) to
    # update the Bindings via an explicit `id`!
    # -> This is done globally and doesn't really work for me.
    # I will continue to use my "illegal" methods.
    BINDINGS = [
        Binding(
            ensure_reserved("ctrl+q,ctrl+c"),
            "stop",
            description="Close",
            show=False,
            priority=True,
        ),
        Binding(
            ensure_reserved("ctrl+z"), "suspend_process", show=False, priority=True
        ),
    ]

    def __init__(
        self,
        *args,
        fake_startup_count: Optional[int] = 1,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        try:
            self.settings = Settings()
            self.settings_error = None
        except Exception as e:
            self.settings = Settings.model_construct()
            self.settings_error = e
        _persistent_json_fp = get_isd_persistent_json_file_path()

        try:
            _persistent_data = (
                json.loads(_persistent_json_fp.read_text())
                if _persistent_json_fp.exists()
                else {}
            )
        except Exception as e:
            # if there are any other issues, log it and assume that we are
            # creating a new file
            log.error(
                f"Exception while trying to read persistent data from: {_persistent_json_fp}",
                e,
            )
            _persistent_data = {}

        if fake_startup_count is None:
            _startup_count = _persistent_data.get("startup_count")
            self.startup_count = 1 if _startup_count is None else _startup_count + 1
            try:
                _persistent_data["startup_count"] = self.startup_count
                _persistent_json_fp.write_text(json.dumps(_persistent_data))
            except Exception as e:
                log.error(
                    f"Exception while trying to write persistent data to: {_persistent_json_fp}",
                    e,
                )
        else:
            self.startup_count = fake_startup_count

        # Only show the following bindings in the footer
        show_bindings = ["toggle_systemctl_modal"]
        for action, field in GenericKeybinding.model_fields.items():
            keys = getattr(self.settings.generic_keybindings, action)
            self.bind(
                keys,
                action,
                description=getattr(field, "description"),
                show=action in show_bindings,
            )

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from self.get_default_system_commands_subset(screen)

        for action, field in GenericKeybinding.model_fields.items():
            keys = getattr(self.settings.generic_keybindings, action)
            description = getattr(field, "description")
            yield SystemCommand(
                description,
                f"Shortcut: {keys}",
                eval(f"self.action_{action}"),
            )

        if isinstance(screen, MainScreen):
            yield from screen.system_commands()

    def action_suspend_process(self) -> None:
        super().action_suspend_process()
        # enforce a full refresh to not have broken layout
        self.refresh()

    def update_schema(self) -> None:
        schema = json.dumps(Settings.model_json_schema())
        fp = isd_config_dir() / "schema.json"
        if fp.exists() and fp.read_text() == schema:
            # self.notify("Schema is already up-to-date.")
            return
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(schema)
        except Exception as e:
            self.notify(f"Error while creating/updating {fp}: {e}", severity="error")

    # FUTURE: Also add the pager as property here
    @property
    def editor(self) -> str:
        return (
            get_systemd_editor()
            if self.settings.editor == "auto"
            else self.settings.editor
        )

    def action_open_config(self) -> None:
        fp = get_config_file_path()
        if not fp.exists():
            prev = ""
            try:
                # in theory `get_config_file_path` should already try to create
                # the parent directories. But doing it again here to potentially
                # propagate the exception to the app.
                fp.parent.mkdir(parents=True, exist_ok=True)
                self.update_schema()
                fp.write_text(get_default_settings_yaml(as_comments=True))
            except Exception as e:
                self.notify(f"Error while creating default config.yaml: {e}")
        else:
            prev = fp.read_text()
        with self.app.suspend():
            subprocess.call([self.editor, fp.absolute()])
        if prev != fp.read_text():
            self.notify(
                dedent("""\
                    Changes to configuration detected!
                    Please restart application for them to take effect."""),
                severity="warning",
            )
        self.refresh()

    def get_default_system_commands_subset(
        self, screen: Screen
    ) -> Iterable[SystemCommand]:
        """
        Only show a subset of the default system commands
        https://github.com/Textualize/textual/blob/d34f4a4bcf683144bc3b45ded331f297012c8d40/src/textual/app.py#L1096
        """
        # Always allow changing the theme:
        # if not self.ansi_color:
        yield SystemCommand(
            "Preview theme",
            "Preview the current theme",
            self.action_change_theme,
        )
        yield SystemCommand(
            "Quit application",
            "Quit the application as soon as possible (Shortcut: ctrl+q,ctrl+c)",
            self.action_stop,
        )
        yield SystemCommand(
            "Show version", "Show the isd version", self.action_show_version
        )

        if screen.query("HelpPanel"):
            yield SystemCommand(
                "Hide keys and help panel",
                "Hide the keys and widget help panel",
                self.action_hide_help_panel,
            )
        else:
            yield SystemCommand(
                "Show keys and help panel",
                "Show help for the focused widget and a summary of available keys",
                self.action_show_help_panel,
            )

    def action_stop(self) -> None:
        """
        Calls the `stop` function of the `MainScreen` and exists.
        """
        self.get_screen("main", MainScreen).store_state()
        self.exit()

    def action_show_version(self) -> None:
        self.notify(f"isd version: {__version__}", timeout=30)

    def on_mount(self) -> None:
        # The theme should be loaded very early,
        # as the theme change can be quite jarring.
        self.theme = self.settings.theme
        # Always make sure to use the latest schema
        self.update_schema()
        self.install_screen(MainScreen(self.settings), "main")
        if self.settings_error is not None:
            error_text = str(self.settings_error)
            self.notify(
                "Error encountered while loading settings; falling back to defaults.",
                severity="error",
                timeout=90,
            )
            error_log_file = Path(tempfile.gettempdir()) / "isd_startup_error.log"
            escaped_error_text = rich.markup.escape(error_text)
            self.notify(
                f"Error while loading settings:\nLog stored under: {error_log_file})\n\n{escaped_error_text}",
                severity="error",
                timeout=90,
            )
            error_log_file.write_text(error_text)
        self.push_screen("main")

        if self.startup_count % 100 == 0:
            self.call_after_refresh(self.show_donation_screen)

    @work
    async def show_donation_screen(self) -> None:
        prev_focus = self.focused
        self.set_focus(None)
        await self.push_screen_wait(DonationScreen(startup_count=self.startup_count))
        self.set_focus(prev_focus)

    @work
    async def action_toggle_systemctl_modal(self) -> None:
        prev_focus = self.focused
        self.set_focus(None)
        cmd = await self.push_screen_wait(
            SystemctlActionScreen(
                self.settings.generic_keybindings.toggle_systemctl_modal,
                self.settings.navigation_keybindings,
                self.settings.systemctl_commands,
            )
        )
        self.set_focus(prev_focus)
        if cmd is not None:
            screen = self.get_screen("main", MainScreen)
            await screen.action_systemctl_command(cmd)


def render_field(key, field, level: int = 0) -> str:
    text = ""
    default_value = field.default
    if hasattr(field, "description"):
        text += "# " + "\n# ".join(field.description.splitlines()) + "\n"
    if isinstance(default_value, (str, StrEnum)):
        text += f'{key}: "{field.default}"'
    elif isinstance(default_value, (int, float)):
        text += f"{key}: {default_value}"
    elif default_value is None:
        text += f"{key}: null"
    elif isinstance(
        default_value,
        (
            GenericKeybinding,
            MainKeybindings,
            NavigationKeybindings,
        ),
    ):
        text += f"{key}:\n"
        for key, value in type(default_value).model_fields.items():
            text += render_field(key, value, level=level + 1)
    elif isinstance(default_value, list):
        if len(default_value) == 0:
            text += f"{key}: []"
        else:
            text += f"{key}: \n"
            for el in default_value:
                # Get the indentation right
                indentation = "  " * (level + 1)
                if isinstance(el, SystemctlCommand):
                    text += indentation + "- " + f'command: "{el.command}"' + "\n"
                    text += (
                        indentation
                        + "  "
                        + f'modal_keybinding: "{el.modal_keybinding}"'
                        + "\n"
                    )
                    text += (
                        indentation
                        + "  "
                        + "direct_keybinding: "
                        + (
                            "null"
                            if el.direct_keybinding is None
                            else f'"{el.direct_keybinding}"'
                        )
                        + "\n"
                    )
                    text += (
                        indentation + "  " + f'description: "{el.description}"' + "\n"
                    )
                else:
                    text += indentation + "- " + f'"{el}"' + "\n"

    # add newline for next item
    # but do not add two empty lines if nested types already added
    # a new line at the end.
    if not text.endswith("\n"):
        text += "\n"

    # add empty line between top-level keys
    if level == 0:
        text += "\n"
    return indent(text, "  " * level)


def render_model_as_yaml(model: Settings) -> str:
    """
    My custom pydantic Settings yaml renderer.
    I had a very bloated implementation with `PyYAML`
    with a custom `Dumper` and with `ruamel.yaml` to inject comments
    but it was unnecessarily complex and hard to configure.

    Instead, I wrote a simple, custom renderer for my `pydantic.Settings`.
    It will only work for this code-base but it gives me full control over the
    rendering process without having code with so much hidden functionality.
    """
    text = ""
    model_fields = type(model).model_fields
    for key in model.model_dump().keys():
        field = model_fields[key]
        text += render_field(key, field)
    return text


def main():
    app = InteractiveSystemd(fake_startup_count=None)
    # In theory, I could trigger a custom exit code for the application
    # if a change is detected and then restart the application here.
    # But let's keep it simple for now. If somebody actually asks for this
    # feature, I might take a closer look at it.
    app.run()


if __name__ == "__main__":
    main()
