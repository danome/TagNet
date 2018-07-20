# Introduction

The Linux Operating System environment for the Basestation is based on an image provided by comitup. This image includes support for easy attachment to Wifi networks as well as provides a standalone Wifi Access Point if no others are available (a second Wifi interface allows for both to coexist and forward packets between them). Information on ComitUp can be found at their github site [here](https://github.com/davesteele/comitup) and at Debian Package for Stretch [here](https://manpages.debian.org/stretch/comitup/index.html).

The software required for the Basestation is then loaded on top of the ComitUp image. In the future, a snapshot of this combined image could be used for distribution.

# Using Disk Images
The fastest way to build a new Raspberry Pi is to use a disk image that has been created from by cloining a work RPi. You can prepare a new SD disk by copying a previously created image. A disk image can be created from a working SD disk as well.

### Load SD from image
```
sudo gunzip -c backup.img.gz | dd of=/dev/sdX status=progress
```

### Create disk image
Follow the steps below below to build a new SD Boot Disk with all required software loaded. Once this is complete, run the ``compact.sh``` script in the ```ubuntu_dev/common``` directory to clean up all unnecessary files from the disk (makes the image as small as possible).
Now umount the SD disk from the RPi and using another system (MAC, PC), issue the following command, where ```/dev/disk3``` is the source SD disk with the working version of software.
```
sudo diskutil umountDisk /dev/disk3
sudo dd if=/dev/disk3 conv=sync,noerror bs=64k status=progress | gzip -c  > backup.img.gz
```
Now remove the SD disk from the host maching and insert in PI. You will still need to personalize and localize the RPi which can be accomplished by running ```raspi-config``` again on the RPi (see instructions below for low level Raspbian Configuration).

### monitor progress
```
sudo kill -INFO 49719       # linux uses -USR1 signal, MacOS and BSD use -INFO
sudo pv gunzip -c backup.img.gz | dd of=/dev/sdX
sudo pv /dev/disk3 | dd conv=sync,noerror bs=64k status=progress | gzip -c  > backup.img.gz
```

# Build BOOT DISK
Follow the instructions on the ComitUp site for OS image retrieval and installation [here](https://github.com/davesteele/comitup/wiki/Tutorial#copy-the-image-to-a-microsd-card). The image is 1.4GB so it is recommended to use BitTorrent to download it.

(Commands used, modify for your use)
1. Determine SD Card device name
```
diskutil list
```
2.Format SD Card
```
sudo diskutil eraseDisk FAT32 TAGPIZ MBRFormat /dev/diskXXX
```
3. Copy Image
```
sudo diskutil umount /Volumes/TAGPIZ/
sudo dd bs=1m if=~/Downloads/2018-05-24-Comitup.img of=/dev/rdiskXXX conv=sync status=progress
```

# Start RPi with new SD card

1. Eject SD card from workstation
```
sudo diskutil eject /Volumes/boot/
```
2. Install SD card into RPi SD card slot
3. Power on the RPi
4. Wait until red light is solid on and green light stops flashing

Can now talk to RPi from any network device using raspberrypi.local or see below for more choices

### Connect to the Comitup Hotspot
Using a Wifi-enabled computer, smart phone, or tablet, view a list of available Wifi Access Points. You should see one named 'comitup-' followed by 4 digits (remember this number). Connect to this Hotspot.

If all you want to do is connect with the Pi, you are done at this point. Connect via ssh to pi@raspberrypi.local or pi@comitup-<nnnn>.local, or to pi@10.42.0.1. If you want your Pi and workstation to also have connectivity to the Internet, continue to the next step.

### Connect the Raspberry Pi to your Wifi Access Point
While connected to the Comitup Access Point, browse to http://comitup-nnnn.local (using the 4 digits from earlier) or to 'http://raspberrypi.local'. If you are using an operating system that does not understand these ',local' addresses, you can cheat and use http://10.42.0.1.

You should see a list of available Access Points. Select one, enter a password if necessary, and click on 'Connect'.



# Low Level Raspian Configuration

The Linux installation requires some configuration for localiziation of Operating System. Raspian provides a program to perform the configuration which uses an ascii character based GUI. Alternatively, there are command line tools for setting most of the parameters we are interested in for our Basestation (but alas not all). See Notes below for details on these methods.

* RUN raspi-config
    * Interfacing Options
        * enable SPI
        * enable SSH
    * hostname
    * password
    * localization
        * change locale
            * unselect:  en_GB.UTF-8 UTF-8
            * select:    en_US.UTF-8 UTF-8
            * set it as system default
        * change wifi country
        * change timezone
    * advanced, expand file system to fill SD card


# Software Installation

## RPi Basic Package Installation

1. use ssh to connect to pi@raspberrypi.local
2. check to see if 32 or 64 bit (COMITUP is 32b)
```
getconf LONG_BIT
```
3. Verify Java version 1.8 is installed
```
java -version
javac -version
```
Example output
```
pi@dvt6:~ $ java -version
java version "1.8.0_65"
Java(TM) SE Runtime Environment (build 1.8.0_65-b17)
Java HotSpot(TM) Client VM (build 25.65-b01, mixed mode)
pi@dvt6:~ $ javac -version
javac 1.8.0_65
```
4. load basic packages
```
sudo apt-get update
sudo apt-get install -qy \
git gitk ntp \
python-twisted \
libusb-dev libreadline-dev \
emacs25 emacs25-el
sudo apt-get install -qy \
python-dev python-rpi.gpio
sudo apt-get install -qy \
fuse libfuse2 libfuse-dev \
python2.7-llfuse python3-llfuse
```

## Install dot-files
These files provide a 'standard' configuration for tool related environment setup.

1. copy files, including .* files with this command:
```
git clone https://github.com/cire831/dot-files.git
SRC_DIR=./dot-files/
DST_DIR=~/
FILES=".bash_aliases .bash_functions .bash_login .bash_logout .bashrc .emacs.d \
.environment_bash .gdbinit .gitconfig .gitignore .mspdebug"
echo -e "\n*** dots from $SRC_DIR -> $DST_DIR ***"
(for i in $FILES; do echo $i; done) | rsync -aiuWr --files-from=- $SRC_DIR $DST_DIR
```

## Install Python related Packages
These are packages required by TagNet BaseStation applications.
```
git clone https://github.com/doceme/py-spidev.git
cd py-spidev/
sudo python setup.py install
sudo usermod -a -G spi pi
groups
# used by jupyter for google maps
sudo pip install pyproj
sudo pip install gmaps
# the following can also be installed when installing basestation software
sudo pip install future
sudo pip install construct==2.5.2
sudo pip install machinist
sudo pip install fusepy
sudo pip install twisted==13.1.0
sudo pip install txdbus==1.1.0
sudo pip install chest
# sudo pip install RPi.GPIO      # already installed by comitup
```

## Install TagNet BaseStation Software
```
cd ~/
git clone https://github.com/MamMark/TagNet.git
cd TagNet/si446x
sudo python setup.py install
cd ../tagnet
sudo python setup.py install
cd ../tagfuse
sudo python setup.py install
```

## Install Tag Tools
```
cd ~/
git clone https://github.com/MamMark/mm.git
cd mm
git branch checkout integration
cd tools/utils/tagcore
sudo python setup.py install
cd ../tagdump
sudo python setup.py install
```

## Install Jupyter (Optional)
##### Install Jupyter Software
This application is used for development and testing purposes. Currently there are notebooks for low level radio device testing and TagFuse related testing.
```
sudo pip install jupyter
sudo apt-get install -y python-seaborn python-pandas
sudo apt-get install -y ttf-bitstream-vera
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
```
##### Generate Jupter Password

```
$ python
> from IPython.lib import passwd
> password = passwd(“dogbreath")
> password
u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
> CTL-D
'sha1:1991fa41bea2:3c719e82a4e784e2affb6fb3b25b81d17e317bc0'
```

##### Build Jupyter Configuration
Build the default Jupyter configuration settings (should be in your home directory. (Outputs ```/home/pi/.jupyter/jupyter_notebook_config.py```)

```
jupyter notebook --generate-config
```

Edit these three lines in jupyter_notebook_config.py (produced in previous step)
```
c.NotebookApp.password = u'sha1:d5d44468f96e:86888342f48852feeaf0a07f1e55d6cd3d5876dd'
c.NotebookApp.ip = '*'
c.NotebookApp.port = 9000
```

##### Run Jupter as Background Task
To start Jupyter on the RPi, use these commands
```
sudo jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py gmaps
#nohup jupyter notebook --no-browser --port=8999 &
su pi -c "nohup nice --adjustment=-20 jupyter notebook --browser=false --allow-root --port=9000 --notebook-dir /home/pi/Desktop/TagNet&"
```

## Shared Development Folder (Optional)
Mount a Network Shared Folder for Source Code access on user workstation.

##### First Time
Add usergroup required to share files
```
sudo groupadd -g 504 devgrp
sudo usermod -a -G devgrp pi
```
Need to set the umask to allow sharing with Mac user. This is done by editting the ```.bash_login``` script to change.
```
umask 2
```

##### Permanent Mount
```
sudo mkdir /mnt/neptune
sudo mkdir /mnt/tag_integration
```
Add the following line to /etc/mount
```
//neptune.local/tag_integration /mnt/neptune cifs exec,noperm,_netdev,nosetuids,sec=ntlmssp,file_mode=0777,dir_mode=0777,user=pi,pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw  0 0
```

##### One-time Mount
```
sudo mount -t cifs //neptune.local/tag_integration /mnt/neptune -o exec,noperm,_netdev,nosetuids,sec=ntlmssp,file_mode=0777,dir_mode=0777,user=pi,pass=dogbreath,iocharset=utf8,uid=pi,gid=devgrp,rw
```

##### MOUNT SHARED FILE SYSTEM ON MAC

create a group named devgrp with number 504.
```
dscl . list /Groups PrimaryGroupID
```

ON MAC, see [this link](https://support.apple.com/en-us/HT204445) for more details.
* add user ```pi``` and group ```devgrp```
* use finder to connect to server
* use finder to Go/Connect_to_Server with ```smb://solar.local```
* specify ‘Open’ as folder to be mounted
* find the newly mounted folder at ```/Volumes/Open```

# Notes, Issues, and Ideas

## Some steps to automating Rasbian Configuration

1. enable SPI
    1. Run this command: sudo nano /boot/config.txt
    2. Add this at the end of the file: dtparam=spi=on
    3. Save file pressing: CTRL+X, Y and Enter
    4. Reboot your system: sudo reboot
2. set hostname
```
* hostnamectl set-hostname
or
* sudo nano /etc/hostname
* sudo /etc/init.d/hostname.sh
* sudo reboot
```
3. country
4. timezone
    * timedatectl set-timezone America/Los_Angeles
5. set locale
    * one way
        * sudo nano /etc/default/locale
        * sudo locale-gen --purge it_IT.UTF-8 en_US.UTF-8 && echo "Success"
        * sudo locale-gen en_US.UTF-8
        * sudo dpkg-reconfigure locales
    * another
```
$ sudo locale-gen en_US.UTF-8 # Or whatever language you want to use
$ sudo dpkg-reconfigure locales
$ sudo nano /etc/default/locale
LANG="en_US.UTF-8"
LANGUAGE=“en_US”
```

## WPA_SUPPLICANT.CONF

For WiFi access, add access point information to /boot/wpa_supplicant. (comitup does
handles this differently, so don't mix the two).
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

## USING JUPTER

In browser window enter:

```
http://<device>.local:9000
```

Update Java first
```
* Visit http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html, click the download button of Java Platform (JDK) 8. Click to Accept License Agreement, download jdk-8-linux-arm-vfp-hflt.tar.gz for Linux ARM v6/v7 Hard Float ABI.  Java SE Development Kit 8u172, Linux ARM 64 Hard Float ABI
    * Log-in Raspberry Pi, enter the command to extract jdk-8-linux-arm-vfp-hflt.tar.gz to /opt directory.
sudo tar zxvf  jdk-8u172-linux-arm64-vfp-hflt.tar.gz -C /opt
    * Set default java and javac to the new installed jdk8.
sudo update-alternatives --install /usr/bin/javac javac /opt/jdk1.8.0_172/bin/javac 1
sudo update-alternatives --install /usr/bin/java java /opt/jdk1.8.0_172/bin/java 1
sudo update-alternatives --config javac
sudo update-alternatives --config java
    * After all, verify with the commands with -verion option.
java -version
javac -version
```
