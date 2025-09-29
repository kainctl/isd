```sh

rm -f /run/systemd/system/awesome-hello-world.service.d/override.conf

# asciinema rec --overwrite --quiet old_workflow.cast

curl localhost:8181

systemctl status awesome-hello-world.service

journalctl -xeu awesome-hello-world.service

journalctl --user -xeu awesome-hello-world.service

journalctl -xeu awesome-hello-world.service

# UP for 10sek
# q

systemctl edit --runtime awesome-hello-world.service

# ah yeah, requires sudo

sudo systemctl edit --runtime awesome-hello-world.service
# TYPE:
# [Service] ENTER
# RestrictAddressFamilies=AF_UNIX AF_INET6 AF_INET ENTER
# Ctrl+X
# Y

curl localhost:8181

# ah yeah, forgot to restart the service

sudo systemctl restart awesome-hello-world.service

curl localhost:8181


# rm /run/systemd/system/awesome-hello-world.service.d/override.conf

```
