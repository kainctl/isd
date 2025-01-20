"""
isd: Interactive Systemd
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
from pathlib import Path
from textwrap import dedent, indent
from typing import (
    Any,
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
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from rich.style import Style
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Resize
from textual.reactive import reactive
from textual.screen import Screen

# FUTURE: Fix the settings for the default themes!
# Issue is that the default green/yellow/red colors may not
# work well with the selection color
from textual.theme import BUILTIN_THEMES

# from textual.scrollbar import ScrollBarRender
from textual.widgets import (
    Footer,
    Header,
    Input,
    RichLog,
    SelectionList,
    TabbedContent,
    TabPane,
    Tabs,
)
from textual.widgets._toggle_button import ToggleButton
from xdg_base_dirs import xdg_cache_home, xdg_config_home
from textual.widgets.selection_list import Selection

from . import __version__

ToggleButton.BUTTON_LEFT = ""
ToggleButton.BUTTON_INNER = "▐"  # "▌"  # "█"
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

_CACHE_DIR = xdg_cache_home() / __package__ / __version__
_CONFIG_DIR = xdg_config_home() / __package__
KEYBINDING_HELP_TEXT = dedent("""\
    Note about keybindings:
    Multiple keys can be defined by separating them with a comma `,`.
    Please note that depending on the terminal, terminal multiplexer, and
    operating system supported keys will vary and may require trial and error.
    See: <https://posting.sh/guide/keymap/#key-format>
   """)
Theme = StrEnum("Theme", [key for key in BUILTIN_THEMES.keys()])  # type: ignore
StartupMode = StrEnum("StartupMode", ["user", "system", "auto"])


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
    "--+quit-if-one-screen",  # never quit if it fits on one screen
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


class SystemctlCommand(BaseModel):
    """SystemctlCommand documentation"""

    keybinding: str = Field(description="Link to keybinding documentation from textual")
    command: str = Field(description="systemctl subcommand (may include arguments)")
    description: str = Field(description="A short description of the command.")


class GenericKeyBindings(BaseModel):
    """Defines the keybinding(s) for the given actions"""

    next_preview_tab: str = Field(
        default="l,right",
        description="Next preview tab",
    )
    previous_preview_tab: str = Field(
        default="h,left",
        description="Previous preview tab",
    )
    clear_input: str = Field(
        default="ctrl+backspace", description="Clear search input."
    )
    jump_to_input: str = Field(default="slash", description="Jump to the search input.")
    copy_unit_path: str = Field(
        default="ctrl+y",
        description="Copy highlighted unit path to the clipboard",
    )
    open_preview_in_pager: str = Field(
        default="enter",
        description="Open in pager",
    )
    open_preview_in_editor: str = Field(
        default="alt+enter",
        description="Open in editor",
    )
    toggle_mode: str = Field(default="ctrl+t", description="Toggle mode")
    open_config: str = Field(
        default="alt+o",
        description=dedent("""\
            Open `config.yaml` file with `editor`.
            Creates `config.yaml` if it doesn't exist."""),
    )


class SelectionKeyBindings(BaseModel):
    down: str = Field(default="down,j", description="Down")
    up: str = Field(default="up,k", description="Up")
    toggle_selection: str = Field(default="space", description="Toggle selection.")
    page_down: str = Field(default="ctrl+down,pagedown", description="Page down")
    page_up: str = Field(default="ctrl+up,pageup", description="Page up")
    first: str = Field(default="home", description="First Element")
    last: str = Field(default="end", description="Last Element")


class PreviewKeyBindings(BaseModel):
    scroll_down: str = Field(default="down,j", description="Scroll down")
    scroll_up: str = Field(default="up,k", description="Scroll up")
    scroll_right: str = Field(default="right,l", description="Scroll right")
    scroll_left: str = Field(default="left,h", description="Scroll left")
    scroll_page_down: str = Field(default="ctrl+down,pagedown", description="Page down")
    scroll_page_up: str = Field(default="ctrl+up,pageup", description="Page up")
    # Not quite sure why but ctrl+pageup/down doesn't seem to work for me.
    scroll_page_left: str = Field(default="ctrl+left", description="Page left")
    scroll_page_right: str = Field(default="ctrl+right", description="Page right")
    scroll_top: str = Field(default="home", description="First Page")
    scroll_end: str = Field(default="end", description="Last Page")


# Creating a temporary configuration file conflicts with
# a relative schema definition. The user should simply delete the configuration
# file if they like to start "fresh".

DEFAULT_COMMANDS = [
    SystemctlCommand(
        keybinding="ctrl+e",
        command="edit",
        description="systemctl edit",
    ),
    SystemctlCommand(
        keybinding="alt+e",
        command="edit --runtime",
        description="systemctl edit --runtime",
    ),
    SystemctlCommand(
        keybinding="ctrl+o",
        command="stop",
        description="systemctl stop",
    ),
    SystemctlCommand(
        keybinding="ctrl+a",
        command="start",
        description="systemctl start",
    ),
    SystemctlCommand(
        keybinding="ctrl+l",
        command="reload",
        description="systemctl reload",
    ),
    SystemctlCommand(
        keybinding="ctrl+n",
        command="enable",
        description="systemctl enable",
    ),
    SystemctlCommand(
        keybinding="ctrl+r",
        command="restart",
        description="systemctl restart",
    ),
    SystemctlCommand(
        keybinding="ctrl+k",
        command="mask",
        description="systemctl mask",
    ),
    SystemctlCommand(
        keybinding="ctrl+u",
        command="unmask",
        description="systemctl unmask",
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
        cli_parse_args=True,
        env_file_encoding="utf-8",
    )

    startup_mode: StartupMode = Field(
        default=StartupMode("auto"),
        description=dedent("""\
            The systemctl startup mode (`user`/`system`).
            By default loads the mode from the last session (`auto`)."""),
    )

    preview_and_selection_refresh_interval_sec: float = Field(
        default=3,
        description=dedent("""\
            Auto refresh the preview unit _and_ unit states of selected units.
            Example: When a selected unit changes from running to failed
            the unit state color and preview window will be updated after this
            time has passed, even if _nothing_ is pressed.
            """),
    )

    full_refresh_interval_sec: float = Field(
        default=15,
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
            The idea is to minimize the number of 'irrelvant' updated during fast
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
        default=["--catalog"],
        description=dedent("""\
            Default arguments for `journalctl` to generate the
            output of the `Journal` preview window."""),
    )

    theme: Theme = Field(
        default=Theme("textual-dark"), description="The theme of the application."
    )

    # FUTURE: Add configuration for input selection keybindings
    # FUTURE: Allow option to select if multi-select is allowed or not.
    generic_keybindings: GenericKeyBindings = Field(
        default=GenericKeyBindings(),
        description=dedent("""\
            Configurable keybindings for common actions.
            The actions (keys) are predefined and the configured keybindings
            are given as values.

            """)
        + KEYBINDING_HELP_TEXT,
    )

    selection_keybindings: SelectionKeyBindings = Field(
        default=SelectionKeyBindings(),
        description="Configurable keybindings for the selection window.",
    )

    preview_keybindings: PreviewKeyBindings = Field(
        default=PreviewKeyBindings(),
        description="Configurable keybindings for preview log windows.",
    )

    systemctl_commands: list[SystemctlCommand] = Field(
        default=DEFAULT_COMMANDS,
        description=dedent(
            """\
            List of configurable systemctl subcommands.
            The exact subcommand (including arguments) can be defined
            by settings `command`. The keybinding(s) that triggers this
            systemctl subcommand is configured via the `keybinding` key.
            The description is used to describe the subcommand
            and used in the applications command palette to find
            the action.

            """
        )
        + KEYBINDING_HELP_TEXT,
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

    # FUTURE: Add in-depth documentation about possible security issues.
    # https://github.com/darrenburns/posting/blob/94feabc232da078c8cc9194e5259c3cd2206cfbb/src/posting/config.py#L113

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
        settings = [init_settings]
        settings.append(env_settings)
        if config_file is not None and config_file.exists():
            settings.append(YamlConfigSettingsSource(settings_cls, config_file))
        return tuple(settings)


def get_default_settings_yaml() -> str:
    header = dedent("""\
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
    text = render_model_as_yaml(Settings())
    return header + text


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
    cache_dir: Path = _CACHE_DIR
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Exception: {e} while creating directory: {cache_dir}")
    return cache_dir


def isd_config_dir() -> Path:
    """
    Return the path to the isd config directory.
    The function will try to create the directory if it doesn't exist
    but will skip any errors.
    """
    config_dir: Path = _CONFIG_DIR
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Exception: {e} while creating directory: {config_dir}")
    return config_dir


def get_isd_state_json_file_path() -> Path:
    cache_dir = isd_cache_dir()
    return cache_dir / "state.json"


def get_config_file_path() -> Path:
    config_dir = isd_config_dir()
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

    def on_resize(self, event: Resize) -> None:
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
    def __init__(self, selection_keybindings: SelectionKeyBindings, **kwargs):
        super().__init__(**kwargs)
        self._bindings.bind(
            keys=selection_keybindings.down,
            action="cursor_down",
            description="Down",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.up,
            action="cursor_up",
            description="Up",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.page_up,
            action="page_up",
            description="Page Up",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.page_down,
            action="page_down",
            description="Page Down",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.first,
            action="first",
            description="First",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.last,
            action="last",
            description="Last",
            show=False,
        )
        self._bindings.bind(
            keys=selection_keybindings.toggle_selection,
            action="select",
            description="Select",
            show=True,
        )
        # HERE: Add home/end!


def unit_sort_priority(unit: str) -> int:
    suffix = unit.rsplit(".", maxsplit=1)[-1]
    try:
        prio = UNIT_PRIORITY_ORDER.index(suffix)
    except ValueError:
        prio = 100
    return prio


class UnitReprState(Enum):
    active = auto()
    failed = auto()
    not_found = auto()
    dead = auto()
    other = auto()

    def render_state(
        self, unit: str, highlight_indices: Optional[List[int]] = None
    ) -> Text:
        """
        Given a `unit` and an optional list of indices, highlight them depending
        on the state.
        Return a rich `Text` object with the correct styling.
        """
        if self == UnitReprState.active:
            prefix = "●"
            style = "green"
        elif self == UnitReprState.failed:
            prefix = "×"
            style = "red"
        elif self == UnitReprState.not_found:
            prefix = "○"
            style = "yellow"
        # TODO: Implement additional ones for:
        # activating, deactivating, maintenance, reloading
        else:
            prefix = "○"
            style = ""  # plain

        text = Text(unit)
        if highlight_indices is not None and len(highlight_indices) > 0:
            text.stylize("dim")
            for idx in highlight_indices:
                text.stylize(Style(dim=False, bold=True), start=idx, end=idx + 1)

        # FUTURE: Could implement overflow method
        return Text.assemble(prefix, " ", text, style=style)


def parse_units_to_state_dict(
    dicts: List[Dict[str, str]],
) -> Dict[str, UnitReprState]:
    """
    Given a list of dictionaries that is derived by
    `systemctl list-units --output=json` extract the
    `unit` entry and map it to a `ServiceReprState`.
    The key ordering is customized to have more relevant units
    in the beginning of the list.
    """
    state_mapper: Dict[str, UnitReprState] = dict()
    # first create unit to state mapping
    for d in dicts:
        if d.get("active") == "active":
            state = UnitReprState.active
        elif d.get("active") == "failed":
            state = UnitReprState.failed
        elif d.get("load") == "not-found":
            state = UnitReprState.not_found
        else:
            state = UnitReprState.other
        state_mapper[d["unit"]] = state
    # second find desired order of dict
    sorted_units = sorted(
        state_mapper.keys(), key=lambda unit: (unit_sort_priority(unit), unit.lower())
    )
    # Generate sorted state mapping
    return {unit: state_mapper[unit] for unit in sorted_units}


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
        # "systemctl",
        "list-units",
    ]
    list_unit_files = [
        # "systemctl",
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
        "--output=json",
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
    parsed_units: List[Dict[str, str]] = json.loads(stdout)

    proc = await asyncio.create_subprocess_exec(
        *list_unit_files,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    # proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parsed_unit_files: List[Dict[str, str]] = json.loads(stdout)
    # So I am simply appending one after the other, so that the more specific color
    # information is stored. A uniqueness test would just be unnecessary
    merged_units = [{"unit": d["unit_file"]} for d in parsed_unit_files]
    merged_units.extend(parsed_units)
    return parse_units_to_state_dict(merged_units)


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
) -> Tuple[int, str, str]:
    sys_cmd = systemctl_args_builder(*cmd, mode=mode, units=units, sudo=sudo)
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
    *cmd: str, mode: str, units: Iterable[str], sudo: bool = False
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
    if mode == "user":
        if sudo or is_root():
            raise ValueError("user mode is not allowed when running as root!")
        sys_cmd.extend(
            [
                get_systemctl_bin(),
                # "systemctl",
                "--user",
                *cmd,
                "--",
            ]
        )
    else:
        sys_cmd.extend(
            [
                get_systemctl_bin(),
                # "systemctl",
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
    def __init__(self, keybindings: PreviewKeyBindings, **kwargs):
        super().__init__(**kwargs)
        self._bindings.bind(
            keys=keybindings.scroll_down,
            action="scroll_down",
            description="Down",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_up,
            action="scroll_up",
            description="Up",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_right,
            action="scroll_right",
            description="Right",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_left,
            action="scroll_left",
            description="Left",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_page_up,
            action="page_up",
            description="Page Up",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_page_down,
            action="page_down",
            description="Page Down",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_page_left,
            action="page_left",
            description="Page Left",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_page_right,
            action="page_right",
            description="Page Right",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_top,
            action="scroll_home",
            description="First Page",
            show=False,
        )
        self._bindings.bind(
            keys=keybindings.scroll_end,
            action="scroll_end",
            description="Last Page",
            show=False,
        )


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
        max_lines: int,
        preview_keybindings: PreviewKeyBindings,
        *args,
        journalctl_args: list[str],
        **kwargs,
    ) -> None:
        self.max_lines = max_lines
        self.journalctl_args = journalctl_args
        self.preview_keybindings = preview_keybindings
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        self.last_output = Text("")

    def watch_mode(self, mode: str) -> None:
        self.update_preview_window()

    def watch_units(self, units: List[str]) -> None:
        self.update_preview_window()

    def on_tabbed_content_tab_activated(self, _tab) -> None:
        self.update_preview_window()

    def action_next_tab(self) -> None:
        tabs: Tabs = self.query_one(Tabs)
        # may add tabs.has_focus():
        tabs.action_next_tab()

    def action_previous_tab(self) -> None:
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()

    @work(exclusive=True)
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
                    keybindings=self.preview_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Journal", id="journal"):
                yield Preview(
                    id="journal_log",
                    keybindings=self.preview_keybindings,
                    auto_scroll=True,
                )

            with TabPane("Cat", id="cat"):
                yield Preview(
                    id="cat_log",
                    keybindings=self.preview_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Dependencies", id="dependencies"):
                yield Preview(
                    id="dependencies_log",
                    keybindings=self.preview_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Show", id="show"):
                yield Preview(
                    id="show_log",
                    keybindings=self.preview_keybindings,
                    auto_scroll=False,
                )

            with TabPane("Help", id="help"):
                yield Preview(
                    id="help_log",
                    keybindings=self.preview_keybindings,
                    auto_scroll=False,
                )


# FUTURE: Maybe call it 'allowed' mode?
def derive_startup_mode(startup_mode: StartupMode) -> str:
    if is_root():
        # if user == `root` then only system is allowed
        return "system"
    if startup_mode == StartupMode("auto"):
        fallback: StartupMode = StartupMode("user")
        fp = get_isd_state_json_file_path()
        if fp.exists():
            return json.loads(fp.read_text()).get("mode", fallback)
        else:
            return fallback
    else:
        return startup_mode


def cached_search_term() -> str:
    fp = get_isd_state_json_file_path()
    if fp.exists():
        return json.loads(fp.read_text()).get("search_term", "")
    return ""


class InteractiveSystemd(App):
    TITLE = "isd"
    CSS_PATH = "dom.tcss"
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
    # Future: Consider not tracking all settings globally

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
            "Change theme",
            "Change the current theme",
            self.action_change_theme,
        )
        yield SystemCommand(
            "Quit the application",
            "Quit the application as soon as possible",
            self.action_quit,
        )
        yield SystemCommand(
            "Show the version", "Show the isd version", self.action_show_version
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

    def action_show_version(self) -> None:
        self.notify(f"isd version: {__version__}", timeout=30)

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from self.get_default_system_commands_subset(screen)
        # Re-reading from settings file, as I might add additional information
        # into the schema for this viewer + only finding the local bindings is
        # a pain.
        for systemctl_command in self.settings.systemctl_commands:
            yield SystemCommand(
                systemctl_command.description,
                f"Shortcut: {systemctl_command.keybinding}",
                partial(self.action_systemctl_command, systemctl_command.command),
            )
        for action, field in self.settings.generic_keybindings.model_fields.items():
            keys = getattr(self.settings.generic_keybindings, action)
            yield SystemCommand(
                action.replace("_", " ").title(),
                f"Shortcut: {keys}",
                eval(f"self.action_{action}"),
            )

    # FUTURE: Use rich text to highlight/underline the letter
    COMMAND_PALETTE_BINDING = "ctrl+p"
    NOTIFICATION_TIMEOUT = 5
    BINDINGS = [
        Binding("ctrl+c", "stop", "Quit the application", priority=True, show=False),
    ]

    def __init__(self) -> None:
        self.settings = Settings()
        super().__init__()
        for command in self.settings.systemctl_commands:
            action = f"systemctl_command('{command.command}')"
            self.update_tracked_keybindings(command.keybinding, action)
            self.bind(
                keys=command.keybinding,
                action=action,
                description=command.description,
                show=False,
            )
        generic_keybindings = self.settings.generic_keybindings
        show_fields = ["open_preview_in_pager", "open_preview_in_editor", "toggle_mode"]
        model_fields = GenericKeyBindings.model_fields
        assert all(
            [show_field in model_fields for show_field in show_fields]
        ), "Forgot to update show_field"
        for action, field in model_fields.items():
            # name of keybinding == action name and
            # description is used for binding description
            keys = getattr(generic_keybindings, action)
            self.update_tracked_keybindings(keys, action)

            self.bind(
                keys,
                action,
                description=getattr(field, "description", ""),
                # yeah, this is kinda hacky, but I only want a few items
                # to be shown in the footer. Adding it to the configuration
                # is too verbose and complicates the design
                show=action in show_fields,
            )

    def update_tracked_keybindings(self, keys: str, action: str) -> None:
        """
        Custom function that keeps track of all custom keybindings and
        raises a warning notification if there are any overlapping keybindings.
        """
        new_keybinds = {key: action for key in keys.split(",")}
        clashes = new_keybinds.keys() & self._tracked_keybinds.keys()
        if len(clashes) != 0:
            msg = "\n".join(
                f"{key}: {new_keybinds[key]} and {self._tracked_keybinds[key]}"
                for key in clashes
            )
            self.notify(
                "Keybinding clashes between: \n" + msg, severity="error", timeout=30
            )
        self._tracked_keybinds.update(new_keybinds)

    # FUTURE:
    # Add a 'systemd' page/screen that shows the overall status of the system
    # and potentially also the environment variables.
    # Take a look at the environment commands, as they might be helpful
    # FUTURE: Figure out how to work with/handle --global
    # FUTURE: Add option to list the most recently failed units.
    #         -> This should be a global option, as this is a frequent use-case.
    def action_next_preview_tab(self) -> None:
        self.query_one(PreviewArea).action_next_tab()

    def action_previous_preview_tab(self) -> None:
        self.query_one(PreviewArea).action_previous_tab()

    # Not supporting this as it leads to too many keyboard shortcuts
    # def action_jump_tab(self, tab: str) -> None:
    #     self.query_one(TabbedContent).active = tab

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

    def action_stop(self) -> None:
        """
        Stop the current application.
        """
        json_state = json.dumps({"mode": self.mode, "search_term": self.search_term})

        fp = get_isd_state_json_file_path()
        # directory may not exist if there was a previous issue while creating them
        if not is_root() and fp.parent.exists():
            try:
                fp.write_text(json_state)
            except Exception as e:
                print(f"Exception: {e} while writing state to: {fp}")
        self.exit()

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
            with self.suspend():
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
                            with self.suspend():
                                return_code, stdout, stderr = await systemctl_async(
                                    *command,
                                    mode=self.mode,
                                    units=self.relevant_units,
                                    sudo=True,
                                    foreground=True,
                                )
                    else:
                        with self.suspend():
                            return_code, stdout, stderr = await systemctl_async(
                                *command,
                                mode=self.mode,
                                units=self.relevant_units,
                                sudo=False,
                                foreground=True,
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
        self.refresh()
        self.partial_refresh_unit_to_state_dict()

    async def watch_mode(self, mode: str) -> None:
        self.query_one(PreviewArea).mode = self.mode
        # clear current selection
        sel = cast(SelectionList, self.query_one(SelectionList))
        sel.deselect_all()
        self.query_one(Fluid).border_title = " " + self.mode + " "
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
        self.copy_to_clipboard(path)
        self.notify(f"Copied '{path}' to the clipboard.")

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
                fp.write_text(get_default_settings_yaml())
            except Exception as e:
                self.notify(f"Error while creating default config.yaml: {e}")
        else:
            prev = fp.read_text()
        with self.suspend():
            subprocess.call([self.editor, fp.absolute()])
        if prev != fp.read_text():
            self.notify(
                dedent("""\
                    Changes to configuration detected!
                    Please restart application for them to take effect."""),
                severity="warning",
            )
        self.refresh()

    def action_toggle_mode(self) -> None:
        # only allow changing mode if current user isn't root user
        if is_root():
            self.notify(
                "Cannot change to `user` mode if program is running as `root` user!",
                severity="warning",
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

        with self.suspend():
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

    @property
    def editor(self) -> str:
        return (
            get_systemd_editor()
            if self.settings.editor == "auto"
            else self.settings.editor
        )

    def action_open_preview_in_editor(self) -> None:
        cur_tab = cast(TabbedContent, self.query_one(TabbedContent)).active
        with self.suspend():
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
                subprocess.call([self.editor, p.absolute()])
        self.refresh()

    async def on_mount(self) -> None:
        # always make sure to use the latest schema
        self.update_schema()
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

    def on_input_changed(self, event: CustomInput.Changed) -> None:
        self.search_term = event.value
        self.debounced_search_units(self.search_term)

    def on_input_submitted(self, value: CustomInput.Submitted) -> None:
        self.action_focus_next()

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

    @work(exclusive=True)
    async def refresh_preview(self):
        await asyncio.sleep(self.settings.updates_throttle_sec)
        if len(self.relevant_units) > 0:
            preview_area = self.query_one(PreviewArea)
            preview_area.units = list(self.relevant_units)
            preview_area.mutate_reactive(PreviewArea.units)

    async def watch_unit_to_state_dict(
        self, unit_to_state_dict: Dict[str, UnitReprState]
    ):
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
        if self.highlighted_unit is not None:
            # throttle since highlighted unit can change quite quickly
            # updating it since the current highlighted value should _always_
            # show the _current_ state of the unit!
            self.throttled_refresh_unit_to_state_dict_worker(self.highlighted_unit)

        self.update_relevant_units()
        self.refresh_preview()

    async def search_units(self, search_term: str) -> list[Dict[str, Any]]:
        # haystack MUST be a local copy as it mutates the data in-place!
        haystack = [u for u in self.unit_to_state_dict.keys()]
        # self.search_results = await fuzzy_match(search_term.replace(" ", ""), haystack)
        return await fuzzy_match(search_term.replace(" ", ""), haystack)

    @work(exclusive=True)
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
            for i, d in enumerate(match_dicts)
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
        self.mutate_reactive(InteractiveSystemd.unit_to_state_dict)

    @work(exclusive=True)
    async def throttled_refresh_unit_to_state_dict_worker(self, *units: str) -> None:
        """
        Will throttle the calls to `refresh_unit_to_state_dict_worker`.
        This should be done whenever many partial updates are expected.
        """
        await asyncio.sleep(self.settings.updates_throttle_sec)
        self.refresh_unit_to_state_dict_worker(*units)

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
        partial_unit_to_state_dict = await load_unit_to_state_dict(self.mode, *units)
        local_unit_to_state_dict = deepcopy(self.unit_to_state_dict)
        for unit in partial_unit_to_state_dict:
            local_unit_to_state_dict[unit] = partial_unit_to_state_dict[unit]

        for unit in set(units) - partial_unit_to_state_dict.keys():
            local_unit_to_state_dict[unit] = UnitReprState.not_found

        if local_unit_to_state_dict != self.unit_to_state_dict:
            # Using `update` and not simple `=` as multiple accesses could
            # happen at the same time! I do not want to loose updates to
            # new keys!
            self.unit_to_state_dict.update(local_unit_to_state_dict)
            self.mutate_reactive(InteractiveSystemd.unit_to_state_dict)
            # unit_to_state_dict watcher calls update_selection!

    # FUTURE: Evaluate if updating the self values in compose makes sense.
    def compose(self) -> ComposeResult:
        # theme should be loaded very early,
        # as the theme change can be quite jarring.
        self.theme = self.settings.theme
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
                    selection_keybindings=self.settings.selection_keybindings,
                    id="unit-selection",
                )
                # with Vertical():
                yield PreviewArea(
                    max_lines=self.settings.preview_max_lines,
                    journalctl_args=self.settings.journalctl_args,
                    preview_keybindings=self.settings.preview_keybindings,
                )
        yield Footer()


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
        (GenericKeyBindings, SelectionKeyBindings, PreviewKeyBindings),
    ):
        text += f"{key}:\n"
        for key, value in default_value.model_fields.items():
            text += render_field(key, value, level=level + 1)
    elif isinstance(default_value, list):
        if len(default_value) == 0:
            text += f"{key}: []"
        else:
            text += f"{key}: \n"
            for el in default_value:
                # remove last
                # get the indentation right
                indentation = "  " * (level + 1)
                if isinstance(el, SystemctlCommand):
                    text += indentation + "- " + f'keybinding: "{el.keybinding}"' + "\n"
                    text += indentation + "  " + f'command: "{el.command}"' + "\n"
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
    I had a very bloated implementation with PyYAML
    with custom a `Dumper` and with ruamel.yaml to inject comments
    but it was unnecessarily complex and hard to configure.

    Instead, I simply wrote a simple, custom renderer for my pydantic Settings.
    It will only work for this code-base but it gives me full control over the
    rendering process without having code with so much hidden functionality.
    """
    text = ""
    model_fields = model.model_fields
    for key, value in model.model_dump().items():
        field = model_fields[key]
        text += render_field(key, field)
    return text


def main():
    app = InteractiveSystemd()
    # In theory, I could trigger a custom exit code for the application
    # if a change is detected and then restart the application here.
    # But let's keep it simple for now. If somebody actually asks for this
    # feature, I might take a closer look at it.
    app.run()


if __name__ == "__main__":
    main()
