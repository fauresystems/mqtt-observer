


# MQTT Observer

Observer app to watch messages exchanged on MQTT server.

## Features

 - To start, set MQTT server host, port and root topic to subscribe.
 - Create new observations:
	 - to filter out some topics
	 - to filter out some messages starting with specific strings
	 - to display fool topic or extracted correspondent
- Modify topic syntax regex to extract which correspondent send or receive messages.
- Clean wills: identify forgotten topics with remaining wills, and select wills to reset.
- Save server and observation settings as sessions, to retrieve further. 

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Development is done on Windows 10 x64 computer under Visual Studio Community with Python 3.6.1 (32-bit) and PyQt5. It should run on Linux and Mac as well.

### Installing

Python 3, SIP, PyQt5 and paho-mqtt packages are required:

```
PyQt5 and paho-mqtt installation
================================

$ pip3 install SIP
$ pip3 install PyQt5
$ pip3 install paho-mqtt

May upgrade if already installed:

$ pip3 install SIP --upgrade
$ pip3 install PyQt5 --upgrade 
$ pip3 install paho-mqtt --upgrade
```

## Deployment

### Building

You can use `lupdate.bat` to update `Observer.fr_FR.ts` french localization file, you may create other localization files (please share them around here).

Edit and publish `Observer.fr_FR.qm` from QtLinguist.

We choose `pyinstaller` as an easy and working deployment solution:

```
Install pyinstaller and build
=============================

$ pip3 install pyinstaller

$ pyrcc5 src/observer.qrc -o src/observer_rc.py
$ pyinstaller -F -n mqtt-observer -i src/observer.ico -w src/main.py
```
You can run `build.bat` to automatize creation of `mqtt-observer.exe` file.

### Running

Run `python main.py` or  `mqtt-observer.exe` (see usage below for command line options).

### Usage

Command line options are possible for `main.py` and `mqtt-observer.exe`

```
usage: mqtt-observer.exe [-h] [-f] [-d] [-l LOGGER]

optional arguments:
  -h, --help            show this help message and exit
  -f, --french          run in French
  -d, --debug           set DEBUG log level
  -l LOGGER, --logger LOGGER
                        use logging config file
```

## Author

* **Marie Faure** - *Initial work* - [<dev@fauresystems.com>](mailto:dev@fauresystems.com)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

This software was created for Escape Room 2.0 project at [Live Escape Grenoble, France](https://www.live-escape.net/).

## Screenshot

![My image](https://raw.githubusercontent.com/fauresystems/mqtt-observer/master/screenshots/mqtt-observer-screenshot.png)

