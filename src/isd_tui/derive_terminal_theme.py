import re
import sys
import tty
import termios
import select
from typing import Optional
from textual.theme import Theme

# OSC Codes:
# https://chromium.googlesource.com/apps/libapps/+/a5fb83c190aa9d74f4a9bca233dac6be2664e9e9/hterm/doc/ControlSequences.md#OSC


def send_osc_query(seq) -> str:
    """
    Send an OSC query. To avoid locking up when something
    unexpected happens, the terminal has 1 second to respond
    and cannot write more than 1024 characters.
    If there is any issue, an empty string is returned.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    response = ""
    try:
        tty.setcbreak(fd)

        # tty.setraw(fd)
        sys.stdout.write(seq)
        sys.stdout.flush()
        timeout_s = 1
        # I am using a timeout when reading from `stdin`
        # to ensure that this won't block forever if the terminal
        # behaves oddly. This may only work on `UNIX` but
        # that should be fine for now.
        ready, _, _ = select.select([fd], [], [], timeout_s)
        last_char_was_esc = False
        if ready:
            for _ in range(1024):
                c = sys.stdin.read(1)
                if c == "\a" or (c == "\x5c" and last_char_was_esc):
                    break

                if c == "\x1b":
                    last_char_was_esc = True
                    continue
                else:
                    last_char_was_esc = False
                response += c
            else:
                response = ""

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return response


def parse_rgb(resp: str) -> Optional[str]:
    match = re.search(r"rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)", resp)
    if match:
        # TODO: At some point figure out why ghostty return RR
        # -> Seems to be the spec
        rgb = "".join(m[:2] for m in match.groups())
        return "#" + rgb
    else:
        return None


def query_palette_color(index: int) -> Optional[str]:
    """Send OSC 4 query and parse reply."""
    seq = f"\033]4;{index};?\a"
    response = send_osc_query(seq)
    return parse_rgb(response)


def query_background_color() -> Optional[str]:
    seq = "\033]11;?\a"
    response = send_osc_query(seq)
    return parse_rgb(response)


def query_foreground_color() -> Optional[str]:
    seq = "\033]10;?\a"
    response = send_osc_query(seq)
    return parse_rgb(response)


def derive_textual_theme() -> Optional[Theme]:
    """
    Derive a textual theme by quering the current terminal
    via OSC escape codes.

    Here, we assume that an iTerm2 color scheme (https://github.com/mbadolato/iTerm2-Color-Schemes) is used.
    This function may return `None` if the theme could not be derived.
    This may happen if the terminal emulator does not support the `OSC 4` query extension
    to retrieve the current palette.
    If this is the case, use a modern terminal emulator such as `ghostty` or `kitty`.

    This function REQUIRES textual to suspend the current application!
    """
    fg = query_foreground_color()
    if fg is None:
        return None
    bg = query_background_color()

    if bg is None:
        return None

    iterm_colors = []
    for i in range(15):
        iterm_color = query_palette_color(i)
        if iterm_color is None:
            return None
        iterm_colors.append(iterm_color)

    return Theme(
        name="terminal-derived-theme",
        primary=iterm_colors[4],
        secondary=iterm_colors[2],
        accent=iterm_colors[3],
        foreground=fg,
        background=bg,
        success=iterm_colors[10],
        warning=iterm_colors[11],
        error=iterm_colors[9],
        surface=bg,
        panel=iterm_colors[8],
        boost=iterm_colors[0],
    )
