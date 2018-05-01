# Build BOOT DISK

1. Format SD Card
```
sudo diskutil eraseDisk FAT32 TAGPI2 MBRFormat /dev/disk2
```
Get OS Image to load
```
https://www.raspberrypi.org/downloads/raspbian/
```
Unzip file and write image to SD Card
```
https://etcher.io/
```

## WPA_SUPPLICANT.CONF

For WiFi access, add access point information to /boot/wpa_supplicant.
```
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
    ssid="teahouse"
    psk=""
    key_mgmt=WPA-PSK
}
```
```
cp ~/Downloads/wpa_supplicant.conf /Volumes/boot/

SSH

/boot/ssh

touch /Volumes/boot/ssh
```

## EJECT MEDIA AND INSERT INTO RASPBERRY PI

1. can now talk to mac using raspberrypi.local


BASIC RPi CONFIG

* RUN raspi-config
    * Interfacing Options
        * enable SPI
        * enable SSH
    * hostname
    * localization
        * change locale
        * change wifi country
        * change timezone

or

1. enable SPI
    1. Run this command: sudo nano /boot/config.txt
    2. Add this at the end of the file: dtparam=spi=on
    3. Save file pressing: CTRL+X, Y and Enter
    4. Reboot your system: sudo reboot
2. set hostname
    * hostnamectl set-hostname
                or
    * sudo nano /etc/hostname
    * sudo /etc/init.d/hostname.sh
    * sudo reboot
1. country
2. timezone
    * timedatectl set-timezone America/Los_Angeles
3. set locale
    * one way
        * sudo nano /etc/default/locale
        * sudo locale-gen --purge it_IT.UTF-8 en_US.UTF-8 && echo "Success"
        * sudo locale-gen en_US.UTF-8
        * sudo dpkg-reconfigure locales
    * another
$ sudo locale-gen en_US.UTF-8 # Or whatever language you want to use
$ sudo dpkg-reconfigure locales
$ sudo nano /etc/default/locale
LANG="en_US.UTF-8"
LANGUAGE=“en_US”


## RPi Package Installation

Use ssh to connect to pi@raspberrypi.local

```
ssh -AXY pi@device.local
```

Run these commands

```
sudo apt-get remove --purge oracle-java8-jdk
sudo apt-get install dirmngr
echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | sudo tee /etc/apt/sources.list.d/webupd8team-java.list
echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | sudo tee -a /etc/apt/sources.list.d/webupd8team-java.list
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886
sudo apt-get update
sudo apt-get install oracle-java8-jdk
java -version
```

## load application related packages
```
sudo apt-get update
sudo apt-get install -qy \
    git gitk ntp \
    python-twisted \
    libusb-dev libreadline-dev \
    emacs emacs24-el
sudo apt-get install -qy \
    fuse libfuse2 libfuse-dev \
    python2.7-llfuse python3-llfuse
```

## INSTALL ENVIRONMENT dot-files

Set up shell and emacs related files, with this command:
```
git clone https://github.com/cire831/dot-files.git
SRC_DIR=./dot-files/
DST_DIR=~/
FILES=".bash_aliases .bash_functions .bash_login .bash_logout .bashrc .emacs.d \
.environment_bash .gdbinit .gitconfig .gitignore .mspdebug"
echo -e "\n*** dots from $SRC_DIR -> $DST_DIR ***"
(for i in $FILES; do echo $i; done) | rsync -aiuWr --files-from=- $SRC_DIR $DST_DIR
```

## INSTALL PYTHON SOFTWARE
```
git clone https://github.com/doceme/py-spidev.git
cd py-spidev/
sudo python setup.py install
sudo usermod -a -G spi pi
groups
#check to see if this will be done when tagnet python module is installed
sudo pip install future
sudo pip install construct==2.5.2
sudo pip install temporenc
sudo pip install machinist
sudo pip install pyproj
sudo pip install gmaps
sudo pip install fusepy
```

# OPTIONAL DEVELOPMENT CONFIGURATION

## MOUNT SHARED FILE SYSTEM ON MAC

* ON MAC, see https://support.apple.com/en-us/HT204445
    * use finder to connect to server
    * use finder to Go/Connect_to_Server with smb://solar.local
    * specify ‘Open’ as folder to be mounted
    * find the newly mounted folder at /Volumes/Open

## MOUNT SHARED FOLDER WITH SOURCE CODE

### PERMANENT:
* mkdir /mnt/Open
* add to /etc/fstab
    * //solar.local/Open /mnt/Open cifs exec,user=pi,pass=raspberry,iocharset=utf8,uid=pi,gid=pi,rw  0 0
* sudo mount -a

### ONE-TIME:
```
sudo mount -t cifs //solar.local/Open /mnt/Open -o user=pi,pass=raspberry,iocharset=utf8,uid=pi,gid=pi,rw
```

## ADD JUPYTER
Get Jupyter running on RPi using the following commands.

This installs packages Jupyter requires. Console shows the
URL needed to access the Jupyter web server from user's system.
```
sudo pip install jupyter
sudo apt-get install -y python-seaborn python-pandas
sudo apt-get install -y ttf-bitstream-vera
sudo python /usr/local/lib/python2.7/dist-packages/pip install jupyter
```

## START JUPYTER
```
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py gmaps
nohup jupyter notebook --browser=false --allow-root --port=9000 &> /dev/null &
```

## CONNECTION

Requires establishing an ssh tunnel from user system

```
ssh -N -f -L localhost:8889:localhost:8889 pi@P222.local -o ServerAliveInterval=30
```


## GENERATE JUPYTER PASSWORD

```
$ python
> from IPython.lib import passwd
> password = passwd(“dogbreath")
> password
u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
> CTL-D
```

Build the default Jupyter configuration settings (should be in your home directory

```
jupyter notebook --generate-config
```

Edit these three lines in jupyter_notebook_config.py (produced in previous step)
```
c.NotebookApp.password = u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
c.NotebookApp.ip = '*'
c.NotebookApp.port = 9000
```

USING JUPTER

In browser window enter:

```
http://<device>.local:9000
```
