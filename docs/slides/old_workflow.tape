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

Set TypingSpeed 50ms

Set Shell "fish"
# Set PlaybackSpeed 0.4
Set Padding 1
Set Margin 1
Set FontSize 16
Set Width 1280
Set Height 720

Hide

Type@25ms "sudo bash init.sh" Enter
Sleep 0.5s
Type "clear" Enter
Sleep 0.5s

Type@25ms `my_asciinema rec --overwrite --quiet old_workflow.cast --window-size 85x27 --command 'fish --private --init-command="set -g fish_autosuggestion_enabled 0"'` Enter
Sleep 0.5s

Show

Sleep 1s 
Type "curl localhost:8181" Sleep 0.5s Enter
Sleep 1s
Ctrl+N

Sleep 1s
Type "systemctl status" Type@20ms " awesome-hello-world.service" Sleep 0.5s Enter
Sleep 1s
Ctrl+N
Right 1
Sleep 1s
Ctrl+N
 
Sleep 1s
Type "q" Enter
Type "journalctl --user -xeu"  Type@20ms " awesome-hello-world.service" Sleep 0.5s Enter
Sleep 1s
Ctrl+N

Sleep 1s
Type "journalctl -xeu " Type@20ms "awesome-hello-world.service" Sleep 0.5s Enter
Sleep 1s
Right
Sleep 1s
Up@50ms 20
Sleep 1s
Right
Sleep 2s
Ctrl+N

Sleep 1s
Type "q" Enter
Sleep 1s
Type "systemctl edit --runtime"  Type@20ms " awesome-hello-world.service" Enter
Sleep 1s
Ctrl+N

# # ah yeah, requires sudo
Sleep 1s
Type "sudo systemctl edit --runtime" Type@20ms " awesome-hello-world.service"
Sleep 1s Enter Sleep 1s
Ctrl+N

Sleep 1s
Type "[Service]" Enter
Sleep 1s
Type "RestrictAddressFamilies=AF_UNIX AF_INET6 AF_INET"
Sleep 1s
Ctrl+N
Ctrl+X
Type "Y" Enter
Sleep 1s
Ctrl+N

Sleep 1s
Type "curl localhost:8181" Enter
Sleep 1s
Ctrl+N

# ah yeah, forgot to restart the service
Sleep 1s
Type "sudo systemctl restart" Type@20ms " awesome-hello-world.service" Enter
Sleep 1s
Ctrl+N

Type "curl localhost:8181" Enter
Sleep 1s

Ctrl+D

