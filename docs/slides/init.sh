umask 0122

sudo mkdir -p /opt/hello/
sudo echo "hello world" > /opt/hello/hello.txt

cp ./awesome-hello-world.py /opt/hello/awesome-hello-world.py
sudo cp ./awesome-hello-world.service /run/systemd/system/hello.service

