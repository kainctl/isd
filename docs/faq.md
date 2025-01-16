# FAQ

## How does it differ from `sysz`?

[`sysz`](https://github.com/joehillen/sysz) is a beautiful, light-weight
TUI for `systemctl` based on [`fzf`](https://github.com/junegunn/fzf) and `bash`.
[`sysz`](https://github.com/joehillen/sysz) was the inspiration for
`isd` and has proven to be great reference material.

The main difference is that `isd` is _stateful_ and allows to quickly chain
multiple action together. For example, within one `isd` session one can
search for the desired unit, edit it with the favorite editor, restart the unit,
and view the journal output.
`sysz` closes after every action. Plus, `isd` allows for more [customization](./customization.md).

## Why is `isd` so big?

At its core, `isd` is a Python application.
As such, it requires a Python interpreter to run and this alone contributes
to around 40 MB of the total installation size.

For the self-contained [AppImage][] installation, there is no way to minimize the size.
For the [nix][] and [uv][] installations, the same Python interpreter may be re-used
by other applications, which may amortize the size across multiple installations.

If you are looking for a more light-weight solution, albeit with fewer features,
have a look at [`sysz`](#how-does-it-differ-from-sysz).

## How do I copy text?

Running `isd` puts the terminal into the application mode
which disables clicking and dragging to select text.
Most terminal emulators offer a modifier key which you can hold while you
click and drag to restore the behavior you may expect from the command line.
The exact modifier key depends on the terminal and platform you are running on.

- Ghostty: Hold the ++shift++ key.
- iTerm: Hold the ++option++ key.
- Gnome Terminal: Hold the ++shift++ key.
- Windows Terminal: Hold the ++shift++ key.

Refer to the documentation for your terminal emulator, if it is not listed above.

> Documentation snippet from the upstream documentation:
> <https://textual.textualize.io/FAQ/#how-can-i-select-and-copy-text-in-a-textual-app>

### Copying more than a single line

One current limitation is that all rendered items are included in the
text selection and copy buffer.
Currently, the recommendation is to open the preview in the pager or editor
and to copy the text from there.
Usability enhancements for interacting with the preview window do not have a high
priority at the moment, since a pager/editor can be launched with a single key press.

## What are the security implications?

For a detailed description of possible security implications,
take a look at the [Security page](./security.md).

## Why can't I interact with the preview window?

At the time of writing, I believe that by limiting the possible _interactions_ with
the preview window one is more inclined towards using the pager or editor.
These tools were purposefully build to navigate text and `isd` tries not to reinvent the wheel.
I fear that by starting to add more "interactive features" to the preview window, feature creep
would start.

Nah, I should really add support for basic scrolling.


