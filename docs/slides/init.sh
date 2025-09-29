umask 0122

sudo mkdir -p /opt/hello/
sudo chmod -R o+r /opt/hello
cp ./awesome-hello-world.py /opt/hello/awesome-hello-world.py

sudo systemctl stop awesome-hello-world.service
sudo rm -r /run/systemd/system/awesome-hello-world.service.d/override.conf
sudo cp ./awesome-hello-world.service /run/systemd/system/awesome-hello-world.service

sudo systemctl daemon-reload
sudo systemctl start awesome-hello-world.service

