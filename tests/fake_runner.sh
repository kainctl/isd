#!/usr/bin/env bash

script_dir="$(dirname "${BASH_SOURCE[0]}")"

function get_first_arg {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --*) shift ;; # ignore options with long arguments
      -*) shift ;;  # ignore short options
      *) first_arg="$1"; break ;;
    esac
  done
  echo "$first_arg"
}

function systemctl {
  # echo "systemctl"
  # get the unit (=last argument)
  unit="${!#}"
  sub_command="$(get_first_arg "$@")"

  if [[ "$sub_command" == "list-units" ]]; then
    cat "$script_dir/integration-test/list-units.txt"
  elif [[ "$sub_command" == "list-unit-files" ]]; then
    cat "$script_dir/integration-test/list-unit-files.txt"
  else
    cat "$script_dir/integration-test/$unit.$sub_command.txt"
  fi
}

function journalctl {
  unit="${!#}"
  cat "$script_dir/integration-test/$unit.journalctl.txt"
}

script_name="$(basename "$0")"

if [[ "$script_name" == "systemctl" ]]; then
  systemctl "$@"
elif [[ "$script_name" == "journalctl" ]]; then
  journalctl "$@"
else
  echo "Unknown execution pattern; link it either with the name 'systemctl' or 'journalctl'."
  exit 1
fi
