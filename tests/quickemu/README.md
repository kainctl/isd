# VM Notes

Installed each `ubuntu-server` VM with `OpenSSH` via `quickemu`.
Downloaded the images with `quickemu --download ubuntu-server XX.YY`.
Then, connect to it via `ssh kai@<server-name>.localhost -p 22220`.
Note that an address ending in `.localhost` will be bound to `.localhost`
if `systemd-resolved` is used. This avoids having to fight with conflicting
key pairs for the "same" destination `localhost`.
To generate the test data:

1. Copy the `test_data_generator.sh` script
2. Execute it via `bash test_data_generator.sh generate_list_data && bash test_data_generator.sh generate_unit_data systemd-timesyncd.service`
3. Copy the resulting directory `test-systemd-<VERSION>` back to the host.

The following configurations have been tested:

- Ubuntu-Server 16.04: v229
- Ubuntu-Server 18.04: v237
- Ubuntu-Server 20.04: v245
- Ubuntu-Server 22.04: v249

To test `isd` within the VM, run the `uv` installation script:
- `curl -LsSf https://astral.sh/uv/install.sh | sh`

And then install the `wheel` with `uv --python=312 pip install *.wheel`.

## Why `quickemu`?

I have tried several different strategies in the hopes of streamlining the test data generation with more `systemctl` versions
but running older versions is just infeasible.
First, I tried running older `systemctl` version directly from `nixpkgs`.
I have tried running older versions by checking out old revisions from [`lazamar.co.uk`](https://lazamar.co.uk/nix-versions/?channel=nixpkgs-unstable&package=systemd) website.
But the older versions (for example, v238) of `systemctl` crash when calling `systemctl list-unit-files`.
This is probably due to the large mismatch between the `systemctl` package version and the `systemd` version running on the host.

Then I have tried to create old NixOS tests that are based on old `systemd` versions.
However, NixOS is not written in a way that allow to still boot very old `systemd` versions.
Changes to the structure of the package derivations make it infeasible to run very old `systemd` versions.
Checking out old versions of `nixpkgs` and trying to create "old" NixOS tests also introduces differences
in the way how the NixOS tests are written.

Since the main purpose is to generate test data and I am content with non-deterministic
outputs, it is just a lot easier to utilize full blown VMs.
I still have to manually run bash scripts that generate the test data and
copy the data around but further optimizing this is just not worth the time.
Especially since supporting >5 year old software in this FOSS project is done best-effort
and not something that is even tangible useful for myself.

