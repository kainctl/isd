# Presentation

20 min in total!

## Motivation

Thank you for joining my presentation!
I am a Hobby System-Administrator...
I would like to give you some context:

## Default Workflow:

Assume we have created a `systemd` service.


- `systemctl status dummy-server.service`
  - Not enough output
- `journalctl -xeu dummy-server.service`
  - Ah, wrong type, wanted system unit not user unit.
- `journalctl -xe dummy-server.service`
  - Scrolling through output to find relevant error.
- `systemctl edit dummy-server.service`
  - Ah, need `root` privileges to edit it.
- `sudo systemctl edit dummy-server.service`
  - Oh damn, now it opened up the wrong `$EDITOR`
  - Make clunky changes
  - Store the file
- `sudo systemctl restart dummy-server.service`
- `systemctl status dummy-server.service`
  - Still starting up...
- `systemctl status dummy-server.service`
  - Still another issue.
- Let's start again from the top!
  
## Alternative `sysz` Workflow

- Show an example output with the preview
- Mention that it is a popular `bash+fzf` script
- Show that you can select multiple
- That it auto-prefixed `sudo` if required
- But after triggering the action, `sysz` is closed as it does not "track any state"
- Makes the script nice and easy to read about and fairly easy to install (smallish dependencies)
- Shows how easy and *useful* it can be to "wrap" around `systemctl` as CLI tools!

Still, the developer experience was not on par anymore with other "modern" TUI applications,
so I started to work on a spiritual successor to `sysz`.

## Interactive `systemd` -- `isd`

- My design of a modern TUI application that wraps around `systemctl` and allows for fast interaction with `systemd`: `isd`
- First, let's understand the different layout, as it may be hard to see in this conference hall:
  - Top: Fuzzy search bar
  - Middle: Search Results, allowing multiple selections
  - Below search results: Preview pane
  - Bottom: Preview pane selection
  - Footer: Shows current available actions and their keybindings.

This is a zoomed in view for the purpose of the presentation but I do want to highlight that it does look quite a bit
better without blown out fonts :D

Let's see how the previous workflow would look like:
- Search for unit (as a normal user without knowing it)
  - No matches -> see in the top left that we are in user mode
  - Switch mode -> see new matches without any issues
- See `systemctl status` output in preview pane
- Simply toggle to `journalctl` output, click enter to open it with your pager
- Run `systemctl edit` via an action
  - See that it may also ask for the user credentials
  - See that it uses the users `EDITOR`
- After closing see the auto-updating `systemctl status` output

Argue that this is already quiet the improvement compared to before.
In the following, I would like to go into a bit more detail over a few insights, design decision and other nice features
of `isd` that I haven't shown in the previous overview.

## Insight 0: `sysz` -- Take advantage of "upstream"

Wrapping around upstream CLI tools can be a great core to develop useful and "stable" TUIs.

- Pretty sure that `systemctl` will always work with `systemd` and should not lag behind the available features of `systemd`
- `systemctl` is insanely backward compatible but otherwise, wrapping around a version specifier is not the end of the world
  - Would be the same for APIs
- CLI tools expose a cherry-picked "API" that an upstream developer "recommends" and *tests*.
- Synchronization cost: Users may expect access to the same CLI "commands" as upstream supports in a TUI.

Time spent re-creating the upstream API from an "internal" library _could_ be spent in other features.

## Reasons against Insight 0

Maybe I want to re-create the CLI API because:
- I have a better design in mind
- I want to understand the inner working better
- Because it is fun
- Because it could be faster (to be discussed...)

## Insight 1: Limit the scope

Let's take a closer look at the preview pane output:

- Supports scrolling with mouse bar
- Supports navigation with arrow keys and vi keybindings

But you CANNOT edit the output, you have limited navigation features, such as searching in the output.

Why?

Use the "correct" tool for the job!

Use your preferred editor to edit files, as this will be your most comfortable environment.
Use your preferred pager to view large outputs.

(Then show that per output type a different pager can be used, very useful for `journalctl` output)

## Reasons against Insight 1

See reasons against insight 0

## Insight 2: LSPs are great for configuration files

Nobody reads your extensive customization page!

- Have the configuration page open in the background.
- Scroll through the web page and show all the different customizations options.
- In my opinion a similarly sized "Options" page within the TUI would also not be that helpful

Show `yaml-language-server` example and how it can be used to quickly check the settings of the user and provide documentation.

## Misc.

I believe TUIs can also do quite a bit of trickery to "fake" speed. 

Wanted to complain about `polkit` and how annoying it is if the user would have to enter their credentials every time
but things are moving in the right direction!

TUIs wrapping around a CLI can also "surface" interesting or lesser known commands/options (especially true for `systemctl`)

Another "interesting application" of TUIs wrapping CLI tools is that they can easily include optional programs.
For example, `shh`.

## Closing

This is a hobby project from a hobby system administrator.
It works for me and I hope that it may be useful for others.

I am currently not in a position to spend much time 'working for free' so development may seem slow currently.
Also worked on a complex tree-sitter parser for `systemd unit files` that highlights the values based on their type
but it provides less benefit compared to an LSP.



