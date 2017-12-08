#!/usr/bin/env python


###############################################################################
##
## MQTT messages display with topics filter.
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


from PyQt5.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy,
		QTextEdit, QFrame, QSizePolicy, QLabel, QPushButton)
from PyQt5.QtGui import QIcon, QPalette, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QPoint, QSettings

from ObserverFilterDialog import ObserverFilterDialog, TopicDisplay
from ObserverWillsDialog import ObserverWillsDialog
import observer_rc

class ObserverDisplayWidget(QWidget):

	addObservation = pyqtSignal()
	delObservation = pyqtSignal()
	newFilterSettings = pyqtSignal(dict) # pyQt5 will interpret as QVariantMap (so keys musr be strings)
	resetWills = pyqtSignal(list)

	#__________________________________________________________________
	def __init__(self, title, logger, session, server, port, topic, remove=True, filter=True):

		super(ObserverDisplayWidget, self).__init__()
		
		self._observation = title

		self._displayFormat = int(TopicDisplay.EMPHASIZEDCORRESPONDENT)
		self._filter1 = None
		self._filter2 = None
		self._filter3 = None
		self._filter4 = None
		self._hiddenCorrespondents = []
		self._hiddenTopics = []
		self._logger = logger
		self._session = session

		self._mqttServerHost = server
		self._mqttServerPort = port
		self._mqttTopicRoot = topic

		self._bufferSize = 50000
		self._correspondents = []
		self._topics = []

		self._mainDisplay = QTextEdit()

		main_layout = QVBoxLayout()
		main_layout.setSpacing(12)
			
		self._mainDisplay.setFrameShape(QFrame.NoFrame)
		self._mainDisplay.setLineWrapMode(QTextEdit.NoWrap)
		self._mainDisplay.setReadOnly(True);
		main_layout.addWidget(self._mainDisplay)

		button_layout = QHBoxLayout()

		clear_button = QPushButton(self.tr("Erase"))
		button_layout.addWidget(clear_button)

		if filter:
			filter_button = QPushButton(self.tr("Observation..."))
			button_layout.addWidget(filter_button)
			filter_button.pressed.connect(self.filterSettings)
		else:
			clear_wills_button = QPushButton(self.tr("Wills..."))
			button_layout.addWidget(clear_wills_button)
			clear_wills_button.pressed.connect(self.clearWillselection)

		if remove:
			del_tab_button = QPushButton()
			del_tab_button.setIcon(QIcon(":/trash.svg"))
			del_tab_button.setFlat(True)
			del_tab_button.setToolTip(self.tr("Delete this observation"))
			del_tab_button.setIconSize(QSize(16, 16))
			del_tab_button.setFixedSize(QSize(24, 24))
			button_layout.addWidget(del_tab_button)
			del_tab_button.pressed.connect(self.delObservation)

		add_tab_button = QPushButton()
		add_tab_button.setIcon(QIcon(":/add.svg"))
		add_tab_button.setFlat(True)
		add_tab_button.setToolTip(self.tr("Add new observation"))
		add_tab_button.setIconSize(QSize(16, 16))
		add_tab_button.setFixedSize(QSize(24, 24))
		button_layout.addStretch(1)
		button_layout.addWidget(add_tab_button, Qt.AlignRight)
		main_layout.addLayout(button_layout)

		self.setLayout(main_layout)

		clear_button.pressed.connect(self.erase)
		add_tab_button.pressed.connect(self.addObservation)

		self._mainDisplay.setStyleSheet("font-family:monospace,courier new,courier; white-space:pre; color:black;")

		reg = QSettings()
		reg.beginGroup(self._session)
		reg.beginGroup(self._observation)
		self._displayFormat = reg.value("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT), type=int)
		self._filter1 = reg.value("filter 1", '')
		self._filter2 = reg.value("filter 2", '')
		self._filter3 = reg.value("filter 1", '')
		self._filter4 = reg.value("filter 4", '')
		self._bufferSize = reg.value("buffer size", 50000, type=int)
		if "Hidden correspondents" in reg.childGroups():
			reg.beginGroup("Hidden correspondents")
			for p in reg.childKeys():
				self._hiddenCorrespondents.append(p.replace('\\', '/'))				
			reg.endGroup()
		if "Hidden topics" in reg.childGroups():
			reg.beginGroup("Hidden topics")
			for t in reg.childKeys():
				self._hiddenTopics.append(t.replace('\\', '/'))				
			reg.endGroup()
		reg.endGroup()
		reg.endGroup()

		
	#__________________________________________________________________
	@pyqtSlot(str)
	def applyFilterSettings(self, name):

		if name == self._observation:
			reg = QSettings()
			reg.beginGroup(self._session)
			reg.beginGroup(self._observation)
			self._displayFormat = reg.value("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT), type=int)
			self._filter1 = reg.value("filter 1", '')
			self._filter2 = reg.value("filter 2", '')
			self._filter3 = reg.value("filter 1", '')
			self._filter4 = reg.value("filter 4", '')
			self._bufferSize = reg.value("buffer size", 50000, type=int)
			self._hiddenCorrespondents = []
			if "Hidden correspondents" in reg.childGroups():
				reg.beginGroup("Hidden correspondents")
				for p in reg.childKeys():
					self._hiddenCorrespondents.append(p.replace('\\', '/'))				
				reg.endGroup()
			self._hiddenTopics = []
			if "Hidden topics" in reg.childGroups():
				reg.beginGroup("Hidden topics")
				for t in reg.childKeys():
					self._hiddenTopics.append(t.replace('\\', '/'))				
				reg.endGroup()
			reg.endGroup()
			reg.endGroup()

	#__________________________________________________________________
	@pyqtSlot()
	def clearWillselection(self):

		reg = QSettings()
		pos = reg.value("position", QPoint(200, 200))

		dlg = ObserverWillsDialog(self._observation, self._session, self._logger, self._topics)
		dlg.move(pos + QPoint(20, 20))

		dlg.resetWills.connect(self.resetWills)
		dlg.resetWills.connect(self.removeTopics)
		
		dlg.exec()

	#__________________________________________________________________
	@pyqtSlot()
	def erase(self):

		self._mainDisplay.clear()

	#__________________________________________________________________
	@pyqtSlot()
	def filterSettings(self):

		reg = QSettings()
		pos = reg.value("position", QPoint(200, 200))

		dlg = ObserverFilterDialog(self._observation, self._session, self._logger, self._correspondents, self._topics, self._hiddenCorrespondents, self._hiddenTopics)
		dlg.move(pos + QPoint(20, 20))

		dlg.newFilterSettings.connect(self.newFilterSettings)
		
		dlg.exec()

	#__________________________________________________________________
	@pyqtSlot(str, str, str, str, str)
	def processMessage(self, correspondent, topic, message, timestamp, direction):

		if correspondent and correspondent not in self._correspondents:
			self._correspondents.append(correspondent)
			self._logger.info(self.tr("New correspondent in '") + self._observation + "' : " + correspondent)

		if topic and topic not in self._topics:
			self._topics.append(topic)
			self._logger.info(self.tr("New topic in ") + self._observation + " : " + topic)

		filter_out = False

		if correspondent and correspondent in self._hiddenCorrespondents:
			filter_out = True

		if topic and topic in self._hiddenTopics:
			filter_out = True

		if self._filter1 and message.startswith(self._filter1):
			filter_out = True

		if self._filter2 and message.startswith(self._filter2):
			filter_out = True

		if self._filter3 and message.startswith(self._filter3):
			filter_out = True

		if self._filter4 and message.startswith(self._filter4):
			filter_out = True

		if not filter_out:
			if len(self._mainDisplay.toPlainText()) > self._bufferSize:
				self._mainDisplay.clear()

			if self._displayFormat == int(TopicDisplay.NOTOPIC):
				self._mainDisplay.append("<span style='color:slategray'>{0}</span> {1}".format(timestamp, message))
			elif self._displayFormat == int(TopicDisplay.FLAT):
				self._mainDisplay.append("<span style='color:slategray'>{0}</span> {1} <span style='color:slategray'>{2}</span> <span style='color:blue'>{3}</span>".format(timestamp, message, direction, topic))
			elif self._displayFormat == int(TopicDisplay.CORRESPONDENTONLY):
				if correspondent:
					self._mainDisplay.append("<span style='color:slategray'>{0}</span> {1} <span style='color:slategray'>{2}</span> <span style='color:blue'>{3}</span>".format(timestamp, message, direction, correspondent))
				else:
					self._mainDisplay.append("<span style='color:slategray'>{0}</span> {1}".format(timestamp, message))
			else:
				self._mainDisplay.append("<span style='color:slategray'>{0}</span> {1} <span style='color:slategray'>{2}</span> <span style='color:mediumblue'>{3}</span>".format(timestamp, message, direction, topic.replace(correspondent, "<span style='color:dodgerblue'>{0}</span>".format(correspondent),1)))

	#__________________________________________________________________
	@pyqtSlot(list)
	def removeTopics(self, topics):

		for topic in topics:
			self._topics.remove(topic)

	#__________________________________________________________________
	@pyqtSlot()
	def reset(self):

		self._mainDisplay.clear()
		self._correspondents = []
		self._topics = []

	#__________________________________________________________________
	def setTitle(self, title):

		self._observation = title

	#__________________________________________________________________
	def title(self):

		return self._observation
