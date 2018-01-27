#!/usr/bin/env python


###############################################################################
##
## Observer main window.
##
## Copyright (C) 2017 Marie Faure <dev@fauresystems.com>
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


from PyQt5.QtCore import (QCoreApplication, Qt, pyqtSignal, pyqtSlot, QSettings, QUuid,
	QPoint, QSize, QFile, QVariant)
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QHBoxLayout, QVBoxLayout,
	QPushButton, QFrame, QSizePolicy, QLabel, QMainWindow, QWidget, QTabWidget, QMessageBox)
from PyQt5.QtGui import QIcon, QImage

from ObserverDisplayWidget import ObserverDisplayWidget
from ObserverSettingsDialog import ObserverSettingsDialog
from ObserverRegexDialog import ObserverRegexDialog
from ObserverFilterDialog import TopicDisplay

import paho.mqtt.client as mqtt
import re, sys, time
from threading import Timer
from enum import Enum
from datetime import datetime
import logging
import observer_rc

MQTT_KEEPALIVE = 15 # 15 seconds is default MQTT_KEEPALIVE in Arduino PubSubClient.h


class ConnectionState(Enum):
	CONNECTED = 1
	CONNECTING = 2
	DISCONNECTED = 3


class ObserverWindow(QMainWindow):

	messageReceived = pyqtSignal(str, str, str, str, str)
	newFilterSettingsApplied = pyqtSignal(str)
	resetDisplays = pyqtSignal()

	#__________________________________________________________________
	def __init__(self, client, logger):

		super(ObserverWindow, self).__init__()

		self._connectionState = None

		self._countUntitledDisplay = 0
		self._displays = []
		self._session = 'Default session'
		self._host = 'localhost'
		self._port = 1883
		self._rootTopic = ''
		self._logger = logger

		self._logger.info(self.tr("Started"))

		reg = QSettings()
		
		if "current session" in reg.childKeys() and reg.value("current session", '').strip() and reg.value("current session", '').strip() in reg.childGroups():
			self._session = reg.value("current session")
		
		self._logger.info(self.tr("Current session : ") + self._session)

		if self._session not in reg.childGroups():
			reg.beginGroup(self._session)
			reg.setValue("host", self._host)
			reg.setValue("port", self._port)
			reg.setValue("root topic", self._rootTopic)
			reg.endGroup()
		else:
			reg.beginGroup(self._session)
			self._host = reg.value("host", 'localhost')
			try:
				self._port = reg.value("port", 1883, type=int)
			except:
				pass
			self._rootTopic = reg.value("root topic", '')
			reg.endGroup()

		if "current session" in reg.childKeys() and not reg.value("current session", '') in reg.childGroups():
			reg.remove("current session")

		self._mqttSwitchingConnection = False

		self._mqttClient = client
		self._mqttServerHost = self._host
		self._mqttServerPort = self._port
		self._mqttRootTopic = self._rootTopic
		self._mqttSubTopic = '#'

		if self._rootTopic:
			self._mqttSubTopic = self._rootTopic + '/#'

		QApplication.desktop().screenCountChanged.connect(self.restoreWindow)
		QApplication.desktop().resized.connect(self.restoreWindow)
		
		self.setWindowTitle(self._session)
		self.setWindowIcon(QIcon(':/view-eye.svg'))

		self._tabWidget = QTabWidget()
		self._cloudLabel = QLabel()
		self._connectionStateLabel = QLabel()
		
		self.builUi()

		reg.beginGroup(self._session)
		inbox = reg.value("param inbox", 'inbox')	
		outbox = reg.value("param outbox", 'outbox')	
		regexInbox = reg.value("regex inbox", r'^%ROOT%/(?P<correspondent>.+)/%INBOX%$')
		regexOutbox = reg.value("regex outbox", r'^%ROOT%/(?P<correspondent>.+)/%OUTBOX%$')
		regexDefault = reg.value("regex default", r'.*/(?P<correspondent>[^/]+)/[^/]+$')
		reg.endGroup()

		regexInbox = regexInbox.replace("%ROOT%", self._rootTopic).replace("%INBOX%", inbox)
		regexOutbox = regexOutbox.replace("%ROOT%", self._rootTopic).replace("%OUTBOX%", outbox)

		self._topicRegexInbox = None
		try:
			self._topicRegexInbox = re.compile(regexInbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile inbox regex"))
			self._logger.debug(e)
		
		self._topicRegexOutbox = None
		try:
			self._topicRegexOutbox = re.compile(regexOutbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile outbox regex"))
			self._logger.debug(e)
		
		self._topicRegexDefault = None
		try:
			self._topicRegexDefault = re.compile(regexDefault)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile topic default regex"))
			self._logger.debug(e)

		self.addDisplay(self.tr("All messsages"))

		reg.beginGroup(self._session)
		for i in reg.childGroups():
			self.addDisplay(i)
		reg.endGroup()
	
		self.changeConnectionState(ConnectionState.DISCONNECTED)

		self._logger.info("{0} : {1}".format(self.tr("MQTT server host"), self._mqttServerHost))
		self._logger.info("{0} : {1}".format(self.tr("MQTT server port"), self._mqttServerPort))
		self._logger.info("{0} : {1}".format(self.tr("MQTT clientid"), self._mqttClient._client_id.decode("latin1")))

		Timer(0, self.layoutLoadSettings).start()
		Timer(0, self.start).start()

	#__________________________________________________________________
	@pyqtSlot()
	def addDisplay(self, title=None):	
		
		if not title:
			if self._countUntitledDisplay:
				title = "{0} ({1})".format(self.tr("New observation"), self._countUntitledDisplay)
			else:
				title = self.tr("New observation")
			self._countUntitledDisplay = self._countUntitledDisplay + 1
			reg = QSettings()
			reg.beginGroup(self._session)
			if title not in reg.childGroups():
				reg.beginGroup(title)
				reg.setValue("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT))
				reg.endGroup()
			reg.endGroup()
			reg.sync()

		root_observation = not len(self._displays)

		new_display = ObserverDisplayWidget(title, self._logger, self._session, self._mqttServerHost, self._mqttServerPort, self._mqttRootTopic, remove = not root_observation, filter = not root_observation)

		new_display.addObservation.connect(self.addDisplay)
		new_display.delObservation.connect(self.removeCurrentDisplay)
		self.newFilterSettingsApplied.connect(new_display.applyFilterSettings)

		self._displays.append(new_display)
		self._tabWidget.addTab(new_display, title)

		self.resetDisplays.connect(new_display.reset)
		self.messageReceived.connect(new_display.processMessage)
		new_display.newFilterSettings.connect(self.applyFilterSettings)
		new_display.resetWills.connect(self.applyResetWills)

		self._tabWidget.setCurrentWidget(new_display)

		self._logger.info("{0} : {1}".format(self.tr("Added observation"), title))

		dspmsg = ''
		for d in self._displays:
			if dspmsg:
				dspmsg += ' | '
			else:
				dspmsg = 'Displays : '
			dspmsg += d.title()
		self._logger.debug(dspmsg)

	#__________________________________________________________________
	@pyqtSlot(dict)
	def applyFilterSettings(self, filter):

		try:
			display = None
			for d in self._displays:
				if d.title() == filter["observation"]:
					display = d

			if not display:
				self._logger.error(self.tr("Observation not found in displays : ") + filter["observation"])
			else:
			
				if filter["name"] != filter["observation"]:
					for d in self._displays:
						if d.title() == filter["name"]:
							self._logger.warning(self.tr("Can't rename observation '") +  filter["observation"] + self.tr("' : '") + filter["name"] + self.tr("' already exists"))
							msgbox = QMessageBox()
							msgbox.setWindowTitle(self.tr("Observer"))
							msgbox.setWindowIcon(QIcon(':/magnifier-black.svg'))        
							msgbox.setText(self.tr("Ignore apply filter !") + "<br><br><i>" + self.tr("Can't rename observation (name already in use).") + "</i><br>")
							msgbox.setStandardButtons(QMessageBox.Close)
							msgbox.setAttribute(Qt.WA_DeleteOnClose)
							msgbox.setWindowFlags(msgbox.windowFlags() & ~Qt.WindowContextHelpButtonHint)		
							msgbox.button(QMessageBox.Close).setText(self.tr("Close"))
							msgbox.move(self.pos() + QPoint(40, 40))
							msgbox.exec()
							return
					display.setTitle(filter["name"])
					self._tabWidget.setTabText(self._tabWidget.currentIndex(), filter["name"])
					reg = QSettings()
					reg.beginGroup(self._session)
					reg.remove(filter["observation"])
					reg.endGroup()

				reg = QSettings()
				reg.beginGroup(self._session)
				reg.beginGroup(filter["name"])
				reg.setValue("display", int(filter["display"]))
				reg.setValue("filter 1", filter["filter 1"])
				reg.setValue("filter 2", filter["filter 2"])
				reg.setValue("filter 3", filter["filter 3"])
				reg.setValue("filter 4", filter["filter 4"])
				reg.setValue("buffer size", filter["buffer size"])
				reg.remove("Hidden correspondents")
				reg.beginGroup("Hidden correspondents")
				for p in filter["hidden correspondents"]:
					reg.setValue(p.replace('/', '\\'), '')
				reg.endGroup()
				reg.remove("Hidden topics")
				reg.beginGroup("Hidden topics")
				for t in filter["hidden topics"]:
					reg.setValue(t.replace('/', '\\'), '')		
				reg.endGroup()
				reg.endGroup()
				reg.endGroup()
				reg.sync()

				self.newFilterSettingsApplied.emit(filter["name"])

		except Exception as e:
			self._logger.error("Failed to apply filter settings")
			self._logger.debug(e)

	#__________________________________________________________________
	@pyqtSlot(list)
	def applyResetWills(self, topics):

		for topic in topics:
			if self._connectionState == ConnectionState.CONNECTED:
				try:
					(result, mid) = self._mqttClient.publish(topic, '', qos=0, retain=True)
					self._logger.info("{0} {1} (mid={2})".format(self.tr("MQTT sending '' to clear will for "), topic, mid))
				except Exception as e:
					self._logger.info("{0} {1} (mid={2})".format(self.tr("MQTT failed to send '' to clear will for "), topic, mid))
					self._logger.debug(e)
			else:
				self._logger.info("{0} {1}".format(self.tr("MQTT failed to reset will (disconnected) for "), topic))

	#__________________________________________________________________
	def builUi(self):	
		
		mw = QWidget()
		self.setCentralWidget(mw)

		main_layout = QVBoxLayout(mw)
		main_layout.setSpacing(12)

		cloud_image = QLabel()
		cloud_image.setPixmap(QIcon(":/cloud-data.svg").pixmap(QSize(36, 36)))
		cloud_image.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		cloud = self._mqttServerHost + ':' + str(self._mqttServerPort)

		if self._mqttRootTopic:
			cloud += '/' + self._mqttRootTopic + '/#'
		else:
			cloud += '/#'

		self._cloudLabel.setText(cloud)
		font = self._cloudLabel.font()
		font.setPixelSize(12)
		font.setBold(True)
		self._cloudLabel.setFont(font)
			
		settings_button = QPushButton()
		settings_button.setIcon(QIcon(":/settings.svg"))
		settings_button.setFlat(True)
		settings_button.setToolTip(self.tr("Settings"))
		settings_button.setIconSize(QSize(16, 16))
		settings_button.setFixedSize(QSize(24, 24))
		settings_button.setStyleSheet("QPushButton { padding-bottom: 4px }")

		self._connectionStateLabel = QLabel()
		self._connectionStateLabel.setPixmap(QIcon(":/led-circle-grey.svg").pixmap(QSize(24, 24)))
		self._connectionStateLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

		header_layout = QHBoxLayout()
		header_layout.addWidget(cloud_image)
		header_layout.addWidget(self._cloudLabel)
		header_layout.addStretch()
		header_layout.addWidget(settings_button)
		header_layout.addWidget(self._connectionStateLabel)
		main_layout.addLayout(header_layout)

		main_layout.addWidget(self._tabWidget)

		settings_button.pressed.connect(self.settings)

	#__________________________________________________________________
	def changeConnectionState(self, state):

		self._connectionState = state

		if state == ConnectionState.CONNECTED:
			self._connectionStateLabel.setPixmap(QIcon(":/led-circle-green.svg").pixmap(QSize(24, 24)))
			self._connectionStateLabel.setToolTip(self.tr("Connected"))
		elif state == ConnectionState.CONNECTING:
			self._connectionStateLabel.setPixmap(QIcon(":/led-circle-yellow.svg").pixmap(QSize(24, 24)))
			self._connectionStateLabel.setToolTip(self.tr("Connecting"))
		elif state == ConnectionState.DISCONNECTED:
			self._connectionStateLabel.setPixmap(QIcon(":/led-circle-red.svg").pixmap(QSize(24, 24)))
			self._connectionStateLabel.setToolTip(self.tr("Disconnected"))
		else:
			self._connectionStateLabel.setPixmap(QIcon(":/led-circle-grey.svg").pixmap(QSize(24, 24)))
			self._connectionStateLabel.setToolTip("")

	#__________________________________________________________________
	def closeEvent(self, event):

		self._logger.info(self.tr("Done"))

	#__________________________________________________________________
	def layoutLoadSettings(self):

		reg = QSettings()
		pos = reg.value("position", QPoint(200, 200))
		size = reg.value("size", QSize(400, 400))

		self.move(pos)
		self.resize(size)

	#__________________________________________________________________
	def layoutSaveSettings(self):

		reg = QSettings()
		reg.setValue("position", self.pos())
		reg.setValue("size", self.size())
		reg.sync()

	#__________________________________________________________________
	def moveEvent(self, event):

		if self.isVisible():
			Timer(0, self.layoutSaveSettings).start()

	#__________________________________________________________________
	def mqttConnect(self):

		self._logger.info(self.tr("May connect to MQTT server..."))

		if self._mqttSwitchingConnection and self._connectionState == ConnectionState.DISCONNECTED:
			self._mqttServerHost = self._host
			self._mqttServerPort = self._port
			self._mqttRootTopic = self._rootTopic
		
			if self._rootTopic:
				self._mqttSubTopic = self._rootTopic + '/#'
			else:
				self._mqttSubTopic = '#'
			
			cloud = self._mqttServerHost + ':' + str(self._mqttServerPort)

			if self._mqttRootTopic:
				cloud += '/' + self._mqttRootTopic + '/#'
			else:
				cloud += '/#'

			self._cloudLabel.setText(cloud)

			clientid = "Observer/" + QUuid.createUuid().toString()
			self._logger.debug("MQTT clientid %s", clientid)

			self._mqttClient.reinitialise(client_id=clientid, clean_session=True, userdata=None)

			self._logger.info(self.tr("MQTT client reinitialised"))
			self._logger.info("{0} : {1}".format(self.tr("MQTT server host"), self._mqttServerHost))
			self._logger.info("{0} : {1}".format(self.tr("MQTT server port"), self._mqttServerPort))
			self._logger.info("{0} : {1}".format(self.tr("MQTT clientid"), self._mqttClient._client_id.decode("latin1")))
			self._mqttClient.on_connect = self.mqttOnConnect
			self._mqttClient.on_disconnect = self.mqttOnDisconnect
			self._mqttClient.on_log = self.mqttOnLog
			self._mqttClient.on_message = self.mqttOnMessage
			self._mqttClient.on_publish = self.mqttOnPublish
			self._mqttClient.on_subscribe = self.mqttOnSubscribe
			self._mqttClient.on_unsubscribe = self.mqttOnUnsubscribe

			self._mqttSwitchingConnection = False
			self._mqttClient.loop_start()


		if self._connectionState == ConnectionState.CONNECTED or self._connectionState == ConnectionState.CONNECTING:
			self._logger.info(self.tr("MQTT connect ignored (already ongoing)"))
		else:
			self._logger.info(self.tr("Connect to MQTT server"))
			try:
				self._mqttClient.connect(self._mqttServerHost, port = self._mqttServerPort, keepalive = MQTT_KEEPALIVE)
				self.changeConnectionState(ConnectionState.CONNECTING)
				self._logger.info(self.tr("MQTT connecting"))
			except Exception as e:
				self.changeConnectionState(ConnectionState.DISCONNECTED)
				self._logger.warning(self.tr("Failed to connect to MQTT server"))
				self._logger.debug(e)
				Timer(15.000, self.mqttConnect).start()

		self._logger.debug("Connection state = " + str(self._connectionState))

	#__________________________________________________________________
	def mqttDisconnect(self):

		try:
			self._mqttClient.disconnect()
		except Exception as e:
			self._logger.error(self.tr("MQTT disconnection call failed"))
			self._logger.debug(e)
		
	#__________________________________________________________________
	def mqttOnConnect(self, client, userdata, flags, rc):

		self._logger.debug("Connected to MQTT server with result code: " + str(rc) + " and flags: ", flags) # flags is dict

		if rc == 0:
			self._logger.info(self.tr("MQTT connected"))
			self.changeConnectionState(ConnectionState.CONNECTED)
			mydata = { 'host': self._mqttServerHost, 'port': self._mqttServerPort }
			self._mqttClient.user_data_set(str(mydata))
			try:
				(result, mid) = self._mqttClient.subscribe(self._mqttSubTopic)
				self._logger.info("{0} {1} : {2}".format(self.tr("MQTT subscribing to"), mid, self._mqttSubTopic))
			except Exception as e:
				self._logger.error(self.tr("MQTT subscribe call failed"))
				self._logger.debug(e)
		elif rc == 1:
			self._logger.warning(self.tr("MQTT failed to connect : connection refused - incorrect protocol version"))
		elif rc == 2:
			self._logger.warning(self.tr("MQTT failed to connect : connection refused - invalid client identifier"))
		elif rc == 3:
			self._logger.warning(self.tr("MQTT failed to connect : connection refused - server unavailable"))
		elif rc == 4:
			self._logger.warning(self.tr("MQTT failed to connect : connection refused - bad username or password"))
		elif rc == 5:
			self._logger.warning(self.tr("MQTT failed to connect : connection refused - not authorised"))
		else:
			self._logger.warning("{0} : {1}".format(self.tr("MQTT failed to connect : return code"), rc))

		self._logger.debug("Connection state = " + str(self._connectionState))

	#__________________________________________________________________
	def mqttOnDisconnect(self, client, userdata, rc):

		self.changeConnectionState(ConnectionState.DISCONNECTED)

		if self._mqttSwitchingConnection:
			self._logger.info(self.tr("Disconnected from MQTT server (switching connection)"))
			Timer(0, self.mqttConnect).start()
			return
		else:
			self._logger.info(self.tr("Disconnected from MQTT server"))

		serv = ''
		if isinstance(userdata, str):
			try:
				mydata = eval(userdata)
				if isinstance(mydata, dict) and 'host' in mydata and 'port' in mydata:
					serv = mydata['host'] + ':' + str(mydata['port'])
			except Exception as e:
				self._logger.info(self.tr("MQTT client userdata not as expected"))
				self._logger.debug(e)

		if rc == 0:
			if serv:
				self._logger.info("{0} {1}".format(self.tr("MQTT disconnected on request from"), serv))
			else:
				self._logger.info(self.tr("MQTT disconnected on request"))
					
		else:
			Timer(15.000, self.mqttConnect).start()
			if serv:
				self._logger.warning("{0}{1} {2} {3}".format(self.tr("MQTT disconnected with rc="), rc, self.tr("from"), serv))
			else:
				self._logger.warning("{0}{1}".format(self.tr("MQTT disconnected with rc="), rc))

		self._logger.debug("Connection state = " + str(self._connectionState))
		
	#__________________________________________________________________
	def mqttOnLog(self, client, userdata, level, buf):

		self._logger.debug("MQTT log level {0} : {1}".format(level, buf))

	#__________________________________________________________________
	def mqttOnMessage(self, client, userdata, msg):

		if self._mqttSwitchingConnection:
			self._logger.info(self.tr("Ignore MQTT message (switching connection)"))
			return

		message = None
		try:
			message = msg.payload.decode(encoding="utf-8", errors="strict")
		except:
			pass

		if not message:
			self._logger.warning("{0} {1}".format(self.tr("MQTT message decoding failed on"), msg.topic))
			return
			
		self._logger.debug('Message: ' + message + ' in ' + msg.topic)

		direction = "&mdash;"
		correspondent = None

		if self._topicRegexInbox:
			if "correspondent" in self._topicRegexInbox.pattern:
				try:
					m = re.match(self._topicRegexInbox, msg.topic)
					if m:
						match = m.groupdict()
						if match["correspondent"]:
							correspondent = match["correspondent"]
							direction = "&rarr;"
				except Exception as e:
					self._logger.debug(e)
			else:
				self._logger.warning(self.tr("No 'correspondent' field in inbox regex : ") + self._topicRegexInbox.pattern)

		if not correspondent and self._topicRegexOutbox:
			if "correspondent" in self._topicRegexOutbox.pattern:
				try:
					m = re.match(self._topicRegexOutbox, msg.topic)
					if m:
						match = m.groupdict()
						if match["correspondent"]:
							correspondent = match["correspondent"]
							direction = "&larr;"
				except Exception as e:
					self._logger.debug(e)
			else:
				self._logger.warning(self.tr("No 'correspondent' field in outbox regex : ") + self._topicRegexInbox.pattern)

		if not correspondent and self._topicRegexDefault:
			if "correspondent" in self._topicRegexDefault.pattern:
				try:
					m = re.match(self._topicRegexDefault, msg.topic)
					if m:
						match = m.groupdict()
						if match["correspondent"]:
							correspondent = match["correspondent"]
				except Exception as e:
					self._logger.debug(e)
			else:
				self._logger.warning(self.tr("No 'correspondent' field in default regex : ") + self._topicRegexInbox.pattern)

		if not correspondent:
			self._logger.warning(self.tr("No correspondent defined for topic : ") + msg.topic)
			
		now = time.time()
		msec = repr(now).split('.')[1][:3]	
		timestamp = time.strftime("[%d/%m/%Y %H:%M:%S.{}]".format(msec), time.localtime(now))
		self.messageReceived.emit(correspondent, msg.topic, message, timestamp, direction)

		
	#__________________________________________________________________
	def mqttOnPublish(self, client, userdata, mid):

		self._logger.debug("userdata=%s mid=%s", userdata, mid)
		self._logger.info("{0} : mid={1}".format(self.tr("MQTT published"), mid)) # mid is a number (message id)

	#__________________________________________________________________
	def mqttOnSubscribe(self, client, userdata, mid, granted_qos):

		self._logger.debug("mid=%s granted_qos=%s", mid, granted_qos) # granted_qos is (2,)
		self._logger.info("{0} : {1} {2} {3}".format(self.tr("MQTT susbcribed to"), mid, self.tr("with QoS"), granted_qos))  # mid is a number (count)

	#__________________________________________________________________
	def mqttOnUnsubscribe(self, client, userdata, mid):

		self._logger.debug("mid=%s", mid)
		self._logger.info("{0} : {1}".format(self.tr("MQTT unsusbcribed from"), mid)) # mid is a number (message id)

		if self._mqttSwitchingConnection:
			Timer(0, self.mqttDisconnect).start()

	#__________________________________________________________________
	def mqttReconnect(self):

		self._logger.info(self.tr("MQTT reconnecting"))

		if self._mqttSwitchingConnection:
			self._logger.info(self.tr("Ignore MQTT reconnecting (switching connection)"))
			return

		try:
			self._mqttClient.reconnect()
		except Exception as e:
			self._logger.error(self.tr("MQTT reconnection call failed"))
			Timer(15.000, self.mqttConnect).start()
			self._logger.debug(e)

	#__________________________________________________________________
	@pyqtSlot()
	def reload(self):

		reg = QSettings()
		
		if "current session" in reg.childKeys() and reg.value("current session", '').strip() and reg.value("current session", '').strip() in reg.childGroups():
			self._session = reg.value("current session")
		
		self._logger.info(self.tr("Current session : ") + self._session)

		self.setWindowTitle(self._session)

		if self._session not in reg.childGroups():
			reg.beginGroup(self._session)
			reg.setValue("host", self._host)
			reg.setValue("port", self._port)
			reg.setValue("root topic", self._rootTopic)
			reg.endGroup()
		else:
			reg.beginGroup(self._session)
			self._host = reg.value("host", 'localhost')
			try:
				self._port = reg.value("port", 1883, type=int)
			except:
				pass
			self._rootTopic = reg.value("root topic", '')
			reg.endGroup()

		if "current session" in reg.childKeys() and not reg.value("current session", '') in reg.childGroups():
			reg.remove("current session")

		self._mqttSwitchingConnection = False
		self._mqttSwitchingSubscription = False

		if self._host != self._mqttServerHost or self._port != self._mqttServerPort:
			self._mqttSwitchingConnection = True
		elif self._rootTopic != self._mqttRootTopic:
			self._mqttSwitchingSubscription = True

		self._mqttServerHost = self._host
		self._mqttServerPort = self._port
		self._mqttRootTopic = self._rootTopic
		self._mqttSubTopic = '#'

		if self._rootTopic:
			self._mqttSubTopic = self._rootTopic + '/#'

		reg.beginGroup(self._session)
		inbox = reg.value("param inbox", 'inbox')	
		outbox = reg.value("param outbox", 'outbox')	
		regexInbox = reg.value("regex inbox", r'^%ROOT%/(?P<correspondent>.+)/%INBOX%$')
		regexOutbox = reg.value("regex outbox", r'^%ROOT%/(?P<correspondent>.+)/%OUTBOX%$')
		regexDefault = reg.value("regex default", r'.*/(?P<correspondent>[^/]+)/[^/]+$')
		reg.endGroup()

		regexInbox = regexInbox.replace("%ROOT%", self._rootTopic).replace("%INBOX%", inbox)
		regexOutbox = regexOutbox.replace("%ROOT%", self._rootTopic).replace("%OUTBOX%", outbox)

		self._topicRegexInbox = None
		try:
			self._topicRegexInbox = re.compile(regexInbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile inbox regex"))
			self._logger.debug(e)
		
		self._topicRegexOutbox = None
		try:
			self._topicRegexOutbox = re.compile(regexOutbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile outbox regex"))
			self._logger.debug(e)
		
		self._topicRegexDefault = None
		try:
			self._topicRegexDefault = re.compile(regexDefault)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile topic default regex"))
			self._logger.debug(e)

		index = self._tabWidget.currentIndex()
		current = self._tabWidget.currentWidget()
		
		for index in (1, self._tabWidget.count()):
			try:
				self._displays.remove(self._tabWidget.widget(index))
				self._tabWidget.widget(index).deleteLater()
				self._tabWidget.removeTab(index)
			except Exception as e:
				self._logger.error(self.tr("Failed to remove observation : not in display list (index=") + str(index) +  self.tr(")"))
				self._logger.debug(e)

		dspmsg = ''
		for d in self._displays:
			if dspmsg:
				dspmsg += ' | '
			else:
				dspmsg = 'Displays : '
			dspmsg += d.title()
		self._logger.debug(dspmsg)

		reg.beginGroup(self._session)
		for i in reg.childGroups():
			self.addDisplay(i)
		reg.endGroup()
	
		QCoreApplication.processEvents()

		if self._mqttSwitchingConnection:
			self.switchConnection()
		elif self._mqttSwitchingSubscription:
			self.switchSubscription()

	#__________________________________________________________________
	@pyqtSlot()
	def removeCurrentDisplay(self):

		index = self._tabWidget.currentIndex()
		current = self._tabWidget.currentWidget()
		
		if index > 0 and current == self.sender():
			try:
				title = self._tabWidget.tabText(index)
				self._tabWidget.removeTab(index)
				if current in self._displays:
					self._displays.remove(self.sender())
					self.sender().deleteLater()
					self._logger.info("{0} : {1}".format(self.tr("Remove observation"), title))
					reg = QSettings()
					reg.beginGroup(self._session)
					reg.remove(title)
					reg.endGroup()
					reg.sync()
				else:
					self._logger.warning(self.tr("Failed to remove observation : not in display list (index=") + str(index) +  self.tr(")"))
			except Exception as e:
				self._logger.error(self.tr("Failed to remove observation : not in display list (index=") + str(index) +  self.tr(")"))
				self._logger.debug(e)

		dspmsg = ''
		for d in self._displays:
			if dspmsg:
				dspmsg += ' | '
			else:
				dspmsg = 'Displays : '
			dspmsg += d.title()
		self._logger.debug(dspmsg)

	#__________________________________________________________________
	@pyqtSlot()
	def restoreWindow(self):

		self.resize(QSize(400, 400))
		self.move(QPoint(200, 200))

	#__________________________________________________________________
	def resizeEvent(self, event):

		if self.isVisible():
			Timer(0, self.layoutSaveSettings).start()
	
	#__________________________________________________________________
	@pyqtSlot()
	def settings(self):
		
		dlg = ObserverSettingsDialog(self._logger, self._session)
		dlg.move(self.pos() + QPoint(20, 20))

		dlg.correspondentRegex.connect(self.settingsRegex)
		dlg.reloadSession.connect(self.reload)
		dlg.exec()

		reg = QSettings()

		reg.beginGroup(self._session)
		self._host = reg.value("host", 'localhost')
		try:
			self._port = reg.value("port", 1883, type=int)
		except:
			self._port = 1883
		self._rootTopic = reg.value("root topic", '')
		reg.endGroup()
		
		if self._host != self._mqttServerHost or self._port != self._mqttServerPort:
			self.switchConnection()
		elif self._rootTopic != self._mqttRootTopic:
			self.switchSubscription()

	#__________________________________________________________________
	@pyqtSlot()
	def settingsRegex(self):

		dlg = ObserverRegexDialog(self._logger, self._session)
		dlg.move(self.pos() + QPoint(20, 20))
		dlg.exec()

		reg = QSettings()
		reg.beginGroup(self._session)
		inbox = reg.value("param inbox", 'inbox')	
		outbox = reg.value("param outbox", 'outbox')	
		regexInbox = reg.value("regex inbox", r'^%ROOT%/(?P<correspondent>.+)/%INBOX%$')
		regexOutbox = reg.value("regex outbox", r'^%ROOT%/(?P<correspondent>.+)/%OUTBOX%$')
		regexDefault = reg.value("regex default", r'.*/(?P<correspondent>[^/]+)/[^/]+$')
		reg.endGroup()

		regexInbox = regexInbox.replace("%ROOT%", self._rootTopic).replace("%INBOX%", inbox)
		regexOutbox = regexOutbox.replace("%ROOT%", self._rootTopic).replace("%OUTBOX%", outbox)

		self._topicRegexInbox = None
		try:
			self._topicRegexInbox = re.compile(regexInbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile inbox regex :") + regexInbox)
			self._logger.debug(e)
		
		self._topicRegexOutbox = None
		try:
			self._topicRegexOutbox = re.compile(regexOutbox)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile outbox regex :") + regexOutbox)
			self._logger.debug(e)
		
		self._topicRegexDefault = None
		try:
			self._topicRegexDefault = re.compile(regexDefault)
		except Exception as e:
			self._logger.error(self.tr("Failed to compile topic default regex :") + regexDefault)
			self._logger.debug(e)
		
	#__________________________________________________________________
	def start(self):	

		try:
			self._mqttClient.on_connect = self.mqttOnConnect
			self._mqttClient.on_disconnect = self.mqttOnDisconnect
			self._mqttClient.on_log = self.mqttOnLog
			self._mqttClient.on_message = self.mqttOnMessage
			self._mqttClient.on_publish = self.mqttOnPublish
			self._mqttClient.on_subscribe = self.mqttOnSubscribe
			self._mqttClient.on_unsubscribe = self.mqttOnUnsubscribe
			Timer(0, self.mqttConnect).start()
		except:
			self._logger.error(self.tr("Can't start MQTT (check definitions in .INI)"))
			msgbox = QMessageBox()
			msgbox.setWindowTitle(self.tr("Observer"))
			msgbox.setWindowIcon(QIcon(':/view-eye.svg'))        
			msgbox.setText(self.tr("Failed to set MQTT client !") + "<br><br><i>" + self.tr("Application will be closed.") + "</i><br>")
			msgbox.setStandardButtons(QMessageBox.Close)
			msgbox.setAttribute(Qt.WA_DeleteOnClose)
			msgbox.setWindowFlags(msgbox.windowFlags() & ~Qt.WindowContextHelpButtonHint)		
			msgbox.button(QMessageBox.Close).setText(self.tr("Close"))
			msgbox.resize(QSize(400, 300))
			msgbox.exec()
			self._logger.info(self.tr("Done"))
			Timer(0, QCoreApplication.quit).start()

		self._logger.debug("Connection state = " + str(self._connectionState))

	#__________________________________________________________________
	def switchConnection(self):

		self._mqttSwitchingConnection = True
		
		self.resetDisplays.emit()

		current_topic = self._mqttSubTopic

		if self._connectionState == ConnectionState.CONNECTED or self._connectionState == ConnectionState.CONNECTING:
			try:
				(result, mid) = self._mqttClient.unsubscribe(current_topic)
				self._logger.info("{0} {1} : {2}".format(self.tr("MQTT unsubscribing from"), mid, current_topic))
			except Exception as e:
				self._logger.debug(e)
				Timer(0, self.mqttDisconnect).start()
		else:
			Timer(0, self.mqttConnect).start()

		self._logger.debug("Connection state = " + str(self._connectionState))

	#__________________________________________________________________
	def switchSubscription(self):

		self.resetDisplays.emit()

		current_topic = self._mqttSubTopic
		self._mqttRootTopic = self._rootTopic
		
		if self._rootTopic:
			self._mqttSubTopic = self._rootTopic + '/#'
		else:
			self._mqttSubTopic = '#'

		cloud = self._mqttServerHost + ':' + str(self._mqttServerPort)

		if self._mqttRootTopic:
			cloud += '/' + self._mqttRootTopic + '/#'
		else:
			cloud += '/#'

		self._cloudLabel.setText(cloud)
		self.resetDisplays.emit()

		if self._connectionState == ConnectionState.CONNECTED:
			try:
				(result, mid) = self._mqttClient.unsubscribe(current_topic)
				self._logger.info("{0} {1} : {2}".format(self.tr("MQTT unsubscribing from"), mid, current_topic))
				(result, mid) = self._mqttClient.subscribe(self._mqttSubTopic)
				self._logger.info("{0} {1} : {2}".format(self.tr("MQTT subscribing to"), mid, self._mqttSubTopic))
			except Exception as e:
				self._logger.debug(e)
		else:
			Timer(0, self.mqttReconnect).start()

		self._logger.debug("Connection state = " + str(self._connectionState))

