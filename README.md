[![Actions Status](https://github.com/webbbn/Open.HD-NG/workflows/build-debs/badge.svg)

# Open.HD-NG
Refactor and update of OpenHD

## Installation

### Update the submodules

~~~
git submodule update --init
~~~

### Configure the software

This defaults to installing in the system directories. Add -DCMAKE_INSTALL_PREFIX=<dir> to install in a different directory.

~~~
mkdir build
cd build
cmake ..
~~~

### Install the software

Add `sudo` if you're installing in the system directories and not already running as root.

~~~
make install
~~~

### Create a debian package

~~~
cpack
~~~

This can be installed with:

~~~
sudo dpkg -i *.deb
~~~

## Configuration

Prior to installation various configuration values can be changed in the conf/openhd file. This file gets intalled into /etc/default/openhd during installation.

## Starting

The installation includes a standard systemd service file. The following commands will start the service and enable it to automatically start on boot.

~~~
sudo systemctl enable openhd
sudo systemctl start openhd
~~~
