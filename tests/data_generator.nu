use std assert

def "main" [] {
  # nix run ".#isd-example-units"
  # FUTURE: This should become part of the flake script.
  # Then it should be fairly easy to customize it for different systemctl versions.
  # TODO:
  # Add unit-files examples
  # -> Would also correctly render 03 in the output!
  # -> Add templates!
  ^systemctl --user stop 0-isd-example-unit-02.service
  do --ignore-errors {
    ^systemctl --user stop 0-isd-example-unit-03.service
  }
  ^systemctl --user disable 0-isd-example-unit-03.service
  ln -s /tmp/__wrong_path_that_does_not_exist --force ($"($env.HOME)/.config/systemd/user/0-isd-example-unit-03.service")
  # 4 is broken by default.

  let example_units = ^systemctl list-units --user --output=json --all -- | from json | where unit =~ "0-isd-example" | sort-by unit
  assert equal ($example_units | where unit == "0-isd-example-unit-01.service" | get "active" | get 0) "active"
  assert equal ($example_units | where unit == "0-isd-example-unit-02.service" | get "active" | get 0) "inactive"
  # assert equal ($example_units | get "load" | get 2) "not-found"
  assert equal ($example_units | | where unit == "0-isd-example-unit-04.service" | get "active" | get 0) "failed"
  $example_units | save --force fake_list_units.json

  with-env {"SYSTEMD_COLORS": 1} {
      ["01" "02" "03" "04"] | each {
      |unit_suffix|
      let service_name = $"0-isd-example-unit-($unit_suffix).service"
      ^systemctl --user status $service_name o+e>| save -f $"($service_name).status.txt"
      ^journalctl -x --invocation=-1 --user --unit $service_name o+e>| save -f $"($service_name).journal.txt"
      ^systemctl --user cat $service_name o+e>| save -f $"($service_name).cat.txt"
      ^systemctl --user show $service_name o+e>| save -f $"($service_name).show.txt"
      ^systemctl --user help $service_name o+e>| save -f $"($service_name).help.txt"
      # super dependent on the system. Just store the first line.
      ^systemctl --user list-dependencies $service_name | lines | first | save -f $"($service_name).list-dependencies.txt"
    }
  }
}


