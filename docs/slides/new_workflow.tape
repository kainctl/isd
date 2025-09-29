Set TypingSpeed 100ms

Set Shell "fish"
# Set PlaybackSpeed 0.4
Set Padding 1
Set Margin 1
Set FontSize 16
# Set Width 850
# Set Height 200

Hide

Type@10ms `ISD_CACHE_INPUT=false ISD_STARTUP_MODE=system ISD_JOURNAL_PAGER=moar ISD_DEFAULT_PAGER=moar ISD_FULL_REFRESH_INTERVAL_SEC=1 my_asciinema rec --overwrite --quiet --window-size 85x27 --command 'fish --private --init-command="set -g fish_autosuggestion_enabled 0"' new_workflow.cast`
Enter

Sleep 0.5s
Show

Sleep 1s 
Type "curl localhost:8181" Sleep 0.5s Enter
Sleep 1s
Ctrl+N

Sleep 1s
Type "isd" Sleep 200ms Enter
Sleep 2s
Ctrl+N

# shows the fuzzy search
Type "awesome-"
Sleep 1s
Ctrl+N

# show that switching to user mode
# is possible without any issues
Ctrl+T
Sleep 1s
Ctrl+N
Sleep 1s
Ctrl+T
Sleep 1s
Ctrl+N

# Jump to `status` output
Sleep 1s
Tab Tab Sleep 2s
Down@50ms 10
Right@50ms 20
Sleep 2s
Ctrl+N

# move from status to journal preview
Tab Sleep 500ms
Right
Sleep 1s
Ctrl+N
# open in pager
Enter
Sleep 1s
Ctrl+N
Sleep 1s
Right 2
Up@50ms 20
Sleep 1s
Right 3
Sleep 2s
Ctrl+N

# Go back to `isd` application
Type "q"
Sleep 2s
Ctrl+N

# open options
Ctrl+O
Sleep 1s
Ctrl+N
# select edit --runtime
Down@100ms 5
Sleep 1s
Enter

# `hx` magic
Sleep 500ms
Ctrl+N
Down@100ms 14
Type "x"
Type "y"
Type "g" Sleep 500ms Type "g"
Down@100ms 3
Type "o[Service]" Escape
Type "p"
Type "I" Escape
Type "v" Right Type "d"
Type "A AF_INET" Escape
Sleep 1s
Ctrl+N
Type ":wq" Enter

# show the previous ran command
Sleep 1s
Ctrl+N Enter
Sleep 1s

# show systemctl actions
Ctrl+O
Sleep 1.5s
Ctrl+N
Sleep 1.5s
Type "s"
Sleep 1.5s
Ctrl+N

# Close `isd`
Ctrl+Q

Hide
Sleep 200ms
Type@5ms "clear" Enter
Show

Sleep 1s
Type "curl localhost:8181" Enter
Sleep 1s

Ctrl+D

