# Build BOOT DISK

1. Format SD Card
    1. sudo diskutil eraseDisk FAT32 TAGPI2 MBRFormat /dev/disk2
2. Get OS Image to load
    1. https://www.raspberrypi.org/downloads/raspbian/
    2. unzip file
3. Write image to SD Card
    1. https://etcher.io/


# BASIC RPi CONFIG

1. connect keyboard, mouse, and monitor to RPi
2. set hostname, country, locale, timezone
3. enable ssh and SPI
4. edit to enable connection to wifi
    * /etc/wpa_supplicant/wpa_supplicant.conf
    * add:
        * network={
ssid=“”
psk=“”
key_mgmt=WPA-PSK
}
5. can now talk to mac using <hostname>.local

more /etc/wpa_supplicant/wpa_supplicant.conf
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
ssid="BC HOUSE AC"
psk="nonenone"
key_mgmt=WPA-PSK
}

# RPi Package Installation

1. use ssh to connect to pi@P211.local
2. load normal packages
```
sudo add-apt-repository ppa:openjdk-r/ppa

sudo apt-get update
sudo apt-get install -qy --force-yes \
    git gitk \
    python-twisted \
    openjdk-8-jre openjdk-8-jdk \
    libusb-dev libreadline-dev \
    emacs emacs24-el
```

# INSTALL ENVIRONMENT dot-files
copy files, including .* files with this command:
```
git clone https://github.com/cire831/dot-files.git
SRC_DIR=./dot-files/
DST_DIR=~/
FILES=".bash_aliases .bash_functions .bash_login .bash_logout .bashrc .emacs.d \
.environment_bash .gdbinit .gitconfig .gitignore .mspdebug"
echo -e "\n*** dots from $SRC_DIR -> $DST_DIR ***"
(for i in $FILES; do echo $i; done) | rsync -aiuWr --files-from=- $SRC_DIR $DST_DIR
```
# INSTALL PYTHON SOFTWARE

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
```
# SSH CONNECTION TO RPI
```
ssh -AXY pi@P211
```
or
```
ssh -AXY pi@P222
```

# MOUNT SHARED FILE SYSTEM ON MAC

* ON MAC, see https://support.apple.com/en-us/HT204445
    * use finder to connect to server
    * use finder to Go/Connect_to_Server with smb://solar.local
    * specify ‘Open’ as folder to be mounted
    * find the newly mounted folder at /Volumes/Open

# MOUNT SHARED FOLDER WITH SOURCE CODE

## PERMANENT:
* mkdir /mnt/Open
* add to /etc/fstab
    * //solar.local/Open /mnt/Open cifs exec,user=pi,pass=raspberry,iocharset=utf8,uid=pi,gid=pi,rw  0 0

## ONE-TIME:
```
sudo mount -t cifs //solar.local/Open /mnt/Open -o user=pi,pass=raspberry,iocharset=utf8,uid=pi,gid=pi,rw
```

# ADD JUPYTER
Get Jupyter running on RPi using the following commands.

This installs packages Jupyter requires. Console shows the
URL needed to access the Jupyter web server from user's system.
```
sudo pip install jupyter
sudo apt-get install -y python-seaborn python-pandas
sudo apt-get install -y ttf-bitstream-vera
sudo python /usr/local/lib/python2.7/dist-packages/pip install jupyter
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
```

Also, requires establishing an ssh tunnel from user system

```
ssh -N -f -L localhost:8889:localhost:8889 pi@P222.local -o ServerAliveInterval=30
```
