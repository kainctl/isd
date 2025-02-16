#!/bin/usr/env bash
set -ex

VERSION=$(systemctl --version | awk 'NR==1 {print $2}')
DIR=${OUT_DIR:-"test-systemd-$VERSION"}

# Function to show usage information
usage() {
  echo "Usage: $0 {generate_list_data [pattern] |generate_unit_data [unit]}"
  echo "To check the output of the user dbus set _SYSTEMD_USER_MODE"
  exit 1
}

# Ensure at least one argument is provided
if [ $# -lt 1 ]; then
  usage
fi

mkdir -p "$DIR"
pushd "$DIR"
trap "popd" EXIT

# Handle subcommands
case "$1" in
  generate_list_data)
    echo "Generating list data..."
    systemctl ${_SYSTEMD_USER_MODE:+--user} list-units --full --all --plain --no-legend ${2:+"$2"} > "list-units.txt"
    systemctl ${_SYSTEMD_USER_MODE:+--user} list-unit-files --full --all --plain --no-legend ${2:+"$2"} > "list-unit-files.txt"
    ;;

  generate_unit_data)
    # Ensure command2 has an additional argument
    if [ -z "$2" ]; then
      echo "Error: generate_unit_data requires an additional argument."
      usage
    fi
    echo "Executing generate_unit_data with argument: $2"
    UNIT="$2"
    export SYSTEMD_COLORS=1

    # Allow errors in these branches
    set +e
    systemctl ${_SYSTEMD_USER_MODE:+"--user"} status "$UNIT" > "$UNIT.status.txt" 2>&1
    systemctl ${_SYSTEMD_USER_MODE:+"--user"} cat "$UNIT" > "$UNIT.cat.txt" 2>&1
    systemctl ${_SYSTEMD_USER_MODE:+"--user"} show "$UNIT" > "$UNIT.show.txt" 2>&1
    systemctl ${_SYSTEMD_USER_MODE:+"--user"} help "$UNIT" > "$UNIT.help.txt" 2>&1
    systemctl ${_SYSTEMD_USER_MODE:+"--user"} list-dependencies "$UNIT" > "$UNIT.list-dependencies.txt" 2>&1
    journalctl ${_SYSTEMD_USER_MODE:+"--user"} -x --invocation=-1 --unit "$UNIT" > "$UNIT.journalctl.txt" 2>&1
    set -e
    ;;
  *)
    echo "Error: Unknown command '$1'"
    usage
    ;;
esac
