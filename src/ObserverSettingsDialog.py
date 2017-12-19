#!/usr/bin/env python


###############################################################################
##
## Observer settings dialog.
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


from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout,
	QLabel, QPushButton, QGroupBox, QLineEdit, QComboBox)
from PyQt5.QtGui import QIcon

from threading import Timer


class ObserverSettingsDialog(QDialog):

	correspondentRegex = pyqtSignal()
	reloadSession = pyqtSignal()

	#__________________________________________________________________
	def __init__(self, logger, session):

		super(ObserverSettingsDialog, self).__init__()

		self._logger = logger
		self._session = session
		
		self._count = QLabel()
		self._countLeftEstimated = QLabel()
		self._metersLeftEstimated = QLabel()

		self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
		self.setWindowTitle(self.tr("Observer settings"))
		self.setWindowIcon(QIcon(':/settings.svg'))        

		self._mqttServerInput = QLineEdit()
		self._mqttPortInput = QLineEdit()
		self._mqttTopicInput = QLineEdit()
		self._sessionNameInput = QLineEdit()
		self._retrieveComboBox = QComboBox()
		self._deleteComboBox = QComboBox()
		
		self.buildUi()

		reg = QSettings()

		self._sessionNameInput.setText(self._session)

		try:
			port = reg.value("port", 1883, type=int)
		except:
			port = 1883

		reg.beginGroup(self._session)
		self._mqttServerInput.setText(reg.value("host", 'localhost'))
		self._mqttPortInput.setText(str(port))
		self._mqttTopicInput.setText(reg.value("root topic", ''))
		reg.endGroup()

		retrieveable = []
		for session in reg.childGroups():
			if session != self._session:
				retrieveable.append(session)

		if retrieveable:
			self._retrieveComboBox.addItem(self.tr("Select session to retrieve..."), '')
			for i in retrieveable:
				self._retrieveComboBox.addItem(i, i)
		else:
			self._retrieveComboBox.addItem(self.tr("No session to retrieve"), '')
			self._retrieveComboBox.setDisabled(True)

		deleteable = []
		for session in reg.childGroups():
			if session != 'Default session' and session != self._session:
				deleteable.append(session)

		if deleteable:
			self._deleteComboBox.addItem(self.tr("Select session to delete..."), '')
			for i in deleteable:
				self._deleteComboBox.addItem(i, i)
		else:
			self._deleteComboBox.addItem(self.tr("No session to delete"), '')
			self._deleteComboBox.setDisabled(True)

		self._retrieveComboBox.currentIndexChanged.connect(self.retrieveSession)
		self._deleteComboBox.currentIndexChanged.connect(self.deleteSession)

	#__________________________________________________________________
	@pyqtSlot()
	def apply(self):

		reg = QSettings()

		if self._mqttPortInput.text().isdecimal():
			port = int(self._mqttPortInput.text())
		else:
			port = 1883

		try:
			port_in_reg = reg.value("port", 1883, type=int)
		except:
			port_in_reg = 1883

		reg.beginGroup(self._session)
		self._logger.info(self.tr("Current session : ") + self._session)
		self._logger.info("{0} : {1} -> {2}".format(self.tr("Apply settings for server host"), reg.value("host", 'localhost'), self._mqttServerInput.text().replace('/', '')))
		self._logger.info("{0} : {1} -> {2}".format(self.tr("Apply settings for server port"), str(port_in_reg), str(port)))
		self._logger.info("{0} : {1} -> {2}".format(self.tr("Apply settings for room topic"), reg.value("root topic", ''), self._mqttTopicInput.text()))
		reg.endGroup()

		reg.beginGroup(self._session)
		reg.setValue("host", self._mqttServerInput.text().replace('/', ''))
		reg.setValue("port", port)
		reg.setValue("root topic", self._mqttTopicInput.text())
		reg.endGroup()
		reg.sync()

		new_session = self._sessionNameInput.text().strip()
		if new_session and new_session != self._session:
			reg_from = QSettings()
			reg_from.beginGroup(self._session)
			reg_to = QSettings()
			reg_to.beginGroup(new_session)
			for k in reg_from.childKeys():
				reg_to.setValue(k, reg_from.value(k))	
			for g in reg_from.childGroups():
				reg_from.beginGroup(g)
				reg_to.beginGroup(g)
				for k in reg_from.childKeys():
					reg_to.setValue(k, reg_from.value(k))	
				reg_from.endGroup()
				reg_to.endGroup()
			reg_from.endGroup()
			reg_to.endGroup()
			reg.setValue("current session", new_session)
			Timer(0, self.reloadSession.emit).start()

		self.accept()

	#__________________________________________________________________
	def buildUi(self):	
	
		main_layout = QVBoxLayout()
		main_layout.setSpacing(12)

		mqtt_box = QGroupBox(self.tr("MQTT"))
		mqtt_box_layout = QGridLayout(mqtt_box)
		main_layout.addWidget(mqtt_box)

		mqtt_box_layout.addWidget(QLabel(self.tr("MQTT server :")), 0, 0)
		mqtt_box_layout.addWidget(self._mqttServerInput, 0, 1)

		mqtt_box_layout.addWidget(QLabel(self.tr("MQTT port :")), 1, 0)
		mqtt_box_layout.addWidget(self._mqttPortInput, 1, 1)

		mqtt_box_layout.addWidget(QLabel(self.tr("MQTT root topic :")), 2, 0)
		mqtt_box_layout.addWidget(self._mqttTopicInput, 2, 1)

		session_box = QGroupBox(self.tr("Session"))
		session_box_layout = QGridLayout(session_box)
		main_layout.addWidget(session_box)

		session_box_layout.addWidget(QLabel(self.tr("Current session :")), 0, 0)
		session_box_layout.addWidget(self._sessionNameInput, 0, 1)
		session_box_layout.addWidget(self._retrieveComboBox, 1, 0, 1, 2)
		session_box_layout.addWidget(self._deleteComboBox, 2, 0, 1, 2)

		main_layout.addSpacing(8)

		apply_button = QPushButton(self.tr("Apply"))
		ignore_button = QPushButton(self.tr("Ignore"))
		regex_button = QPushButton(self.tr("Correspondent..."))

		button_layout = QHBoxLayout()
		button_layout.addWidget(regex_button)
		button_layout.addStretch()
		button_layout.addWidget(apply_button)
		button_layout.addWidget(ignore_button)
		main_layout.addLayout(button_layout)

		self.setLayout(main_layout)

		apply_button.pressed.connect(self.apply)
		ignore_button.pressed.connect(self.accept)
		regex_button.pressed.connect(self.regex)

		ignore_button.setFocus()

	#__________________________________________________________________
	@pyqtSlot(int)
	def deleteSession(self, index):

		session = self._retrieveComboBox.itemData(index)
		
		if session:
			reg = QSettings()
			reg.remove(session)
			self.accept()

	#__________________________________________________________________
	@pyqtSlot()
	def regex(self):

		Timer(0, self.correspondentRegex.emit).start()
		
		self.accept()

	#__________________________________________________________________
	@pyqtSlot(int)
	def retrieveSession(self, index):

		session = self._retrieveComboBox.itemData(index)
		
		if session:
			reg = QSettings()
			reg.setValue("current session", session)
			Timer(0, self.reloadSession.emit).start()
			self.accept()
