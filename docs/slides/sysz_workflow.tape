Set TypingSpeed 100ms

Set Shell "fish"
# Set PlaybackSpeed 0.4
Set Padding 1
Set Margin 1
Set FontSize 16
# Set Width 850
# Set Height 200

Hide

Type@25ms "sudo bash init.sh" Enter
Sleep 0.5s
Type "clear" Enter
Sleep 0.5s

Type@25ms `my_asciinema rec --overwrite --quiet sysz_workflow.cast --window-size 85x27 --command 'fish --private --init-command="set -g fish_autosuggestion_enabled 0"'` Enter
Sleep 0.5s

Show

Type "sysz" Sleep 500ms Enter Sleep 2s
Ctrl+N
Type "awesome-" Sleep 1s 
Ctrl+N
Sleep 1s

Enter
Sleep 1s
Ctrl+N
# Up
# Sleep 1s
# Enter
# Sleep 2s
# Ctrl+N

# Type "sysz" Sleep 500ms Enter Sleep 1.5s
# Type "awesome-" Sleep 1s Enter
# Sleep 1s
# Ctrl+N
Up@100ms 4
Sleep 1s
Enter

Sleep 1s
Right
Sleep 1s
Up@50ms 20
Sleep 1s
Right
Sleep 2s
Ctrl+N

Sleep 500ms
Type "q" Enter
Sleep 500ms

Ctrl+N
Type "sysz"

Sleep 1s
Ctrl+D


