Set TypingSpeed 100ms

Set Shell "fish"
# Set PlaybackSpeed 0.4
Set Padding 1
Set Margin 1
Set FontSize 16
# Output out.gif
# Set Width 850
# Set Height 200

Hide

Type@10ms `rm ~/.config/isd_tui/config.yaml` Enter
Type "clear" Enter
Type@10ms `ISD_CACHE_INPUT=false ISD_STARTUP_MODE=system ISD_FULL_REFRESH_INTERVAL_SEC=1 my_asciinema rec --overwrite --quiet --window-size 85x27 --command 'fish --private --init-command="set -g fish_autosuggestion_enabled 0"' custom.cast` Enter
Show

Sleep 1s
Type "isd" Sleep 0.5s Enter
Sleep 2s
Ctrl+N
Ctrl+P
Sleep 1s
Type "config"
Sleep 1s
Ctrl+N
Enter
Sleep 1s
Ctrl+N
Down@50ms 11
Type "i"
Type "journal_p" Sleep 1s Tab
Sleep 3s Enter
Type "0" Escape
Sleep 1s
Ctrl+N
Sleep 1s
Type "i" Backspace
Type "lnav" Enter
Sleep 1s
Type "navigation_keybindings: " Tab
Sleep 2s
Sleep 1s Escape
Ctrl+N
Type ":wq" Enter

Sleep 1s
Ctrl+N
Sleep 1s
Ctrl+Q
Sleep 1s
Type "isd" Enter
Sleep 2s
Ctrl+N
Type "awesome-"
Sleep 1s
Tab@500ms 3
Sleep 1s Right Sleep 1s
Enter
Sleep 1s
Ctrl+N
Sleep 1s
Type ":filter-in DEBUG"
Sleep 2s
Enter
Sleep 1s
Right 1
Ctrl+N
Sleep 1s
Type "q"

Ctrl+D

