#!/usr/bin/env python


###############################################################################
##
## Observer app to watch messages on MQTT server.
##
## Copyright (C) 2017 Faure Systems <dev@fauresystems.com>
##
## Permission is hereby granted, free of charge, to any person obtaining a 
## copy of this software and associated documentation files (the "Software"), 
## to deal in the Software without restriction, including without limitation 
## the rights to use, copy, modify, merge, publish, distribute, sublicense, 
## and/or sell copies of the Software, and to permit persons to whom the 
## Software is furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
## THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
## DEALINGS IN THE SOFTWARE.
##
###############################################################################


from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtCore import QSysInfo, Qt, QUuid, QTranslator, QLocale, QDir

from ObserverWindow import ObserverWindow

import paho.mqtt.client as mqtt
import sys, os, platform
import logging, logging.config
import argparse

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"  # for 4k display

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--french", help="run in French", action='store_true')
parser.add_argument("-d", "--debug", help="set DEBUG log level", action='store_true')
parser.add_argument("-l", "--logger", help="use logging config file", nargs=1)
args = vars(parser.parse_args())

if args['logger'] and os.path.isfile(args['logger']):
	logging.config.fileConfig(args['logger'])
	if args['debug']:
		logger = logging.getLogger('debug')
		logger.setLevel(logging.DEBUG)
	else:
		logger = logging.getLogger('production')
		logger.setLevel(logging.INFO)
elif os.path.isfile('logging.ini'):
	logging.config.fileConfig('logging.ini')
	if args['debug']:
		logger = logging.getLogger('debug')
		logger.setLevel(logging.DEBUG)
	else:
		logger = logging.getLogger('production')
		logger.setLevel(logging.INFO)
else:
	if args['debug']:
		logger = logging.getLogger('debug')
		logger.setLevel(logging.DEBUG)
	else:
		logger = logging.getLogger('production')
		logger.setLevel(logging.INFO)
	ch = logging.FileHandler('observer.log', 'w')
	ch.setLevel(logging.INFO)
	logger.addHandler(ch)

app = QApplication(sys.argv)

if platform.system() == 'Windows':
	if QSysInfo.windowsVersion() > QSysInfo.WV_WINDOWS7:
		QApplication.setStyle(QStyleFactory.create("Fusion"))
	else:
		QApplication.setStyle(QStyleFactory.create("Windows"))
else:
	QApplication.setStyle(QStyleFactory.create("Windows"))

app.setApplicationDisplayName("MQTT Observer")
app.setApplicationName("MQTT Observer")
app.setOrganizationDomain("xcape.io")
app.setOrganizationName("xcape.io")

if platform.system() == 'Windows':
	app.setAttribute(Qt.AA_EnableHighDpiScaling) # for 4K display

translator = QTranslator()
if args['french']:
	if translator.load(":/Observer.fr_FR.qm", QDir.currentPath()):
		app.installTranslator(translator)

clientid = "Observer/" + QUuid.createUuid().toString()
logger.debug("MQTT clientid %s", clientid)

mqtt_client = mqtt.Client(clientid, clean_session=True, userdata=None)

dlg = ObserverWindow(mqtt_client, logger)
dlg.show()

mqtt_client.loop_start()

rc = app.exec_()

try:
	mqtt_client.disconnect()
	mqtt_client.loop_stop()
except:
	pass

sys.exit(rc)
