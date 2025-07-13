# VHS documentation
#
# Output:
#   Output <path>.gif               Create a GIF output at the given <path>
#   Output <path>.mp4               Create an MP4 output at the given <path>
#   Output <path>.webm              Create a WebM output at the given <path>
#
# Require:
#   Require <string>                Ensure a program is on the $PATH to proceed
#
# Settings:
#   Set FontSize <number>           Set the font size of the terminal
#   Set FontFamily <string>         Set the font family of the terminal
#   Set Height <number>             Set the height of the terminal
#   Set Width <number>              Set the width of the terminal
#   Set LetterSpacing <float>       Set the font letter spacing (tracking)
#   Set LineHeight <float>          Set the font line height
#   Set LoopOffset <float>%         Set the starting frame offset for the GIF loop
#   Set Theme <json|string>         Set the theme of the terminal
#   Set Padding <number>            Set the padding of the terminal
#   Set Framerate <number>          Set the framerate of the recording
#   Set PlaybackSpeed <float>       Set the playback speed of the recording
#   Set MarginFill <file|#000000>   Set the file or color the margin will be filled with.
#   Set Margin <number>             Set the size of the margin. Has no effect if MarginFill isn't set.
#   Set BorderRadius <number>       Set terminal border radius, in pixels.
#   Set WindowBar <string>          Set window bar type. (one of: Rings, RingsRight, Colorful, ColorfulRight)
#   Set WindowBarSize <number>      Set window bar size, in pixels. Default is 40.
#   Set TypingSpeed <time>          Set the typing speed of the terminal. Default is 50ms.
#
# Sleep:
#   Sleep <time>                    Sleep for a set amount of <time> in seconds
#
# Type:
#   Type[@<time>] "<characters>"    Type <characters> into the terminal with a
#                                   <time> delay between each character
#
# Keys:
#   Escape[@<time>] [number]        Press the Escape key
#   Backspace[@<time>] [number]     Press the Backspace key
#   Delete[@<time>] [number]        Press the Delete key
#   Insert[@<time>] [number]        Press the Insert key
#   Down[@<time>] [number]          Press the Down key
#   Enter[@<time>] [number]         Press the Enter key
#   Space[@<time>] [number]         Press the Space key
#   Tab[@<time>] [number]           Press the Tab key
#   Left[@<time>] [number]          Press the Left Arrow key
#   Right[@<time>] [number]         Press the Right Arrow key
#   Up[@<time>] [number]            Press the Up Arrow key
#   Down[@<time>] [number]          Press the Down Arrow key
#   PageUp[@<time>] [number]        Press the Page Up key
#   PageDown[@<time>] [number]      Press the Page Down key
#   Ctrl+<key>                      Press the Control key + <key> (e.g. Ctrl+C)
#
# Display:
#   Hide                            Hide the subsequent commands from the output
#   Show                            Show the subsequent commands in the output
# 
# FUTURE: Maybe try out the new "wait" feature.
# 

# Output demo.gif
# Output demo.webm

Require echo
Require isd
Require asciinema
Require lnav
Require moar

Set TypingSpeed 100ms

Set Shell "fish"
Set PlaybackSpeed 0.4
Set Padding 1
Set Margin 1
Set FontSize 16
Set Width 1280
Set Height 720

# Should first run  `nix run ./result/bin/generate-doc-test-data`.
Type@10ms "systemctl start --user '0-isd-example-unit-01.service' '0-isd-example-unit-05.service'" Enter
# do not full refresh during recording -> Set it to a very large value
# normal refresh should use the default value!
# `my_asciinema` is simply `asciinema_3` wrapped in a bash script, where a custom `config.toml` is utilized.
Type@10ms "ISD_CACHE_INPUT=false ISD_STARTUP_MODE=user ISD_JOURNAL_PAGER=lnav ISD_DEFAULT_PAGER=moar ISD_PREVIEW_AND_SELECTION_REFRESH_INTERVAL_SEC=2.5 ISD_FULL_REFRESH_INTERVAL_SEC=1000 my_asciinema rec --overwrite --quiet --command isd ./docs/assets/images/isd.cast"
Enter

# # Sleep 2s
# Type "isd"
# Enter

# ISD Overview marker
Sleep 2s Type "]" Sleep 1s

Type "0-isd exmpl u 0"
# Fuzzy search marker
Sleep 2s Type "]"

Tab
Sleep 2s Space Down@750ms 4
# Multi-selection marker
Sleep 1s Type "]" Sleep 1s

# systemctl action marker
Sleep 1s Ctrl+o Sleep 2s Type "]" Sleep 1s
Down Sleep 2s Enter

# Auto-refresh marker
Sleep 0.5s Type "]"

# Wait until stop notification has cleared and the
# units have stopped and updated their preview
Sleep 4s

# Command palette marker
Ctrl+p Sleep 1s Type "]" Sleep 1s

# Command palette search marker
Type "open pager" Sleep 1s Type "]" Sleep 1s
Enter Sleep 0.5s
# set marker to opened pager
Type "]"
Sleep 2s
Right Right Right
Sleep 2s
Type "q"

Sleep 2s

# show journal preview marker
Tab Sleep 0.5s Tab Sleep 0.5s Right
Sleep 3s Type "]"
Sleep 1s Ctrl+p Type "open pag" Sleep 1.5s
Enter

# set marker to journal pager
Sleep 2s Type "]" Sleep 2s

Type "/unit-" Sleep 0.5s Enter
Type "NNN"
Sleep 1s PageDown Sleep 1s PageDown

Sleep 2s Type "q" Sleep 1s

# Theme changer marker
Ctrl+p Sleep 1s Type "theme" Sleep 0.5s Enter Sleep 0.5s
Type "dracula" Sleep 1s Enter Sleep 0.5s Type "]" Sleep 2s

Right Sleep 1s
# marker for Cat 
Type "]"
Sleep 1s

# marker for Dependencies 
Right Sleep 1s 
Type "]"
Sleep 1s

# marker for Show
Right Sleep 2s
Type "]"
Sleep 1s

# marker for Help 
Right Sleep 2s
Type "]"
Sleep 1s

# show status again
Right Sleep 2s

# quit marker
Ctrl+p Type "quit" Sleep 0.5s Type "]" Sleep 0.5s Enter
