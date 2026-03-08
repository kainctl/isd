set -exu

mv ./docs/assets/images/isd.cast ./docs/assets/images/isd.bak.cast

systemctl --user cat 0-isd-example-unit-01.service 2&> /dev/null || \
  nix run ./nix/systemd-units#generate-doc-test-data

systemctl start --user \
  '0-isd-example-unit-01.service' \
  '0-isd-example-unit-05.service'

nix build .#isd

PATH="$PWD/result/bin/:$PATH" vhs demo.tape

# Check that it is > 0
file ./docs/assets/images/isd.cast 

