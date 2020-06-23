#!/usr/bin/env python


###############################################################################
##
## Observer filter dialog.
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


from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QGridLayout,
	QFrame, QLabel, QPushButton, QSizePolicy, QGroupBox, QLineEdit, QCheckBox, QWidget,
	QTabWidget, QComboBox, QRadioButton, QScrollArea)
from PyQt5.QtGui import QIcon, QPalette

from enum import Enum


class TopicDisplay(Enum):
	FLAT = 1
	EMPHASIZEDCORRESPONDENT = 2
	CORRESPONDENTONLY = 3
	NOTOPIC = 4
	def __int__(self):
		return self.value


class ObserverFilterDialog(QDialog):

	newFilterSettings = pyqtSignal(dict) # pyQt5 will interpret as QVariantMap (so keys musr be strings)

	#__________________________________________________________________
	def __init__(self, observation, session, logger, correspondents, topics, hiddenCorrespondents, hiddenTopics):

		super(ObserverFilterDialog, self).__init__()

		self._observation = observation
		self._session = session
		self._logger = logger
		self._correspondents = correspondents
		self._topics = topics
		self._hiddenCorrespondents = hiddenCorrespondents
		self._hiddenTopics = hiddenTopics

		self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
		self.setWindowTitle(self.tr("Observer filter"))
		self.setWindowIcon(QIcon(':/magnifier-black.svg'))

		self._nameInput = QLineEdit(self._observation)
		self._filter1Input = QLineEdit()
		self._filter2Input = QLineEdit()
		self._filter3Input = QLineEdit()
		self._filter4Input = QLineEdit()
		self._displayFlatButton = QRadioButton(self.tr("Show topic unformatted"))
		self._displayEmphasizedCorrespondentButton = QRadioButton(self.tr("Emphasize correspondent in topic"))
		self._displayCorrespondentOnlyBytton = QRadioButton(self.tr("Show correspondent instead of topic"))
		self._displayNoTopicButton = QRadioButton(self.tr("Don't show topic"))
		self._bufferSizeComboBox = QComboBox()
		self._correspondentsCheckboxes = []
		self._topicsCheckboxes = []

		self._tabWidget = QTabWidget()
		self._allCorrespondentsCheckbox = QCheckBox(self.tr("All"))
		self._allTopicsCheckbox = QCheckBox(self.tr("All"))

		self.buildUi()

		reg = QSettings()
		width = reg.value("filter width", 400)
		self.resize(width, self.size().height())

		self._bufferSizeComboBox.addItem(self.tr("50 kB"), 50000)
		self._bufferSizeComboBox.addItem(self.tr("100 kB"), 100000)
		self._bufferSizeComboBox.addItem(self.tr("200 kB"), 200000)
		self._bufferSizeComboBox.addItem(self.tr("500 kB"), 500000)
		self._bufferSizeComboBox.addItem(self.tr("1000 kB"), 1000000)

		reg.beginGroup(self._session)
		reg.beginGroup(self._observation)
		self._filter1Input.setText(reg.value("filter 1", ''))
		self._filter2Input.setText(reg.value("filter 2", ''))
		self._filter3Input.setText(reg.value("filter 3", ''))
		self._filter4Input.setText(reg.value("filter 4", ''))
		if reg.value("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT), type=int) == int(TopicDisplay.FLAT):
			self._displayFlatButton.setChecked(True)
		elif reg.value("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT), type=int) == int(TopicDisplay.EMPHASIZEDCORRESPONDENT):
			self._displayEmphasizedCorrespondentButton.setChecked(True)
		elif reg.value("display", int(TopicDisplay.EMPHASIZEDCORRESPONDENT), type=int) == int(TopicDisplay.CORRESPONDENTONLY):
			self._displayCorrespondentOnlyBytton.setChecked(True)
		else:
			self._displayNoTopicButton.setChecked(True)
		self._bufferSizeComboBox.setCurrentIndex(self._bufferSizeComboBox.findData(reg.value("buffer size", 50000, type=int)))
		reg.endGroup()
		reg.endGroup()

	#__________________________________________________________________
	@pyqtSlot()
	def accept(self):

		self.close()

	#__________________________________________________________________
	@pyqtSlot()
	def apply(self):

		filter = {}
		filter["observation"] = self._observation
		filter["name"] = self._nameInput.text()
		if self._displayFlatButton.isChecked():
			filter["display"] = int(TopicDisplay.FLAT)
		elif self._displayEmphasizedCorrespondentButton.isChecked():
			filter["display"] = int(TopicDisplay.EMPHASIZEDCORRESPONDENT)
		elif self._displayCorrespondentOnlyBytton.isChecked():
			filter["display"] = int(TopicDisplay.CORRESPONDENTONLY)
		else:
			filter["display"] = int(TopicDisplay.NOTOPIC)
		filter["filter 1"] = self._filter1Input.text().replace('/', '')
		filter["filter 2"] = self._filter2Input.text().replace('/', '')
		filter["filter 3"] = self._filter3Input.text().replace('/', '')
		filter["filter 4"] = self._filter4Input.text().replace('/', '')
		filter["buffer size"] = int(self._bufferSizeComboBox.currentData())

		filter["hidden correspondents"] = []
		for cb in self._correspondentsCheckboxes:
			if not cb.isChecked():
				filter["hidden correspondents"].append(cb.text())

		filter["hidden topics"] = []		
		for cb in self._topicsCheckboxes:
			if not cb.isChecked():
				filter["hidden topics"].append(cb.text())

		self.newFilterSettings.emit(filter)

		reg = QSettings()
		reg.beginGroup(self._session)
		reg.setValue("filter width", self.size().width())
		reg.sync()

		self.accept()

	#__________________________________________________________________
	def buildUi(self):	
	
		main_layout = QVBoxLayout()
		main_layout.addWidget(self._tabWidget)

		general_layout = QVBoxLayout()
		general_layout.setSpacing(12)
		general_widget = QWidget()
		general_widget.setLayout(general_layout)
		self._tabWidget.addTab(general_widget, self.tr("General"))

		general_layout.addSpacing(8)

		name_layout = QHBoxLayout()
		name_layout.addWidget(QLabel(self.tr("Observation name :")))
		name_layout.addWidget(self._nameInput)
		general_layout.addLayout(name_layout)

		mqtt_box = QGroupBox(self.tr("Message content filters"))
		mqtt_box_layout = QGridLayout(mqtt_box)
		general_layout.addWidget(mqtt_box)

		mqtt_box_layout.addWidget(QLabel(self.tr("Filter out messages starting with :")), 0, 0)
		mqtt_box_layout.addWidget(self._filter1Input, 0, 1)

		mqtt_box_layout.addWidget(QLabel(self.tr("Filter out messages starting with :")), 1, 0)
		mqtt_box_layout.addWidget(self._filter2Input, 1, 1)

		mqtt_box_layout.addWidget(QLabel(self.tr("Filter out messages starting with :")), 2, 0)
		mqtt_box_layout.addWidget(self._filter3Input, 2, 1)

		mqtt_box_layout.addWidget(QLabel(self.tr("Filter out messages starting with :")), 3, 0)
		mqtt_box_layout.addWidget(self._filter4Input, 3, 1)

		correspondents_layout = QVBoxLayout()
		correspondents_layout.setSpacing(0)
		correspondents_widget = QWidget()
		correspondents_widget.setStyleSheet("font-family:monospace,courier new,courier; white-space:pre; color:blue;")
		correspondents_widget.setLayout(correspondents_layout)
		correspondents_scrollArea = QScrollArea()
		correspondents_scrollArea.setWidgetResizable(True)
		correspondents_scrollArea.setBackgroundRole(QPalette.Base)
		correspondents_scrollArea.setFrameShape(QFrame.NoFrame)
		correspondents_scrollArea.setWidget(correspondents_widget)
		self._tabWidget.addTab(correspondents_scrollArea, self.tr("Correspondents"))

		if self._correspondents:
			correspondents_layout.addWidget(self._allCorrespondentsCheckbox)

			all = True
			none = True

			for correspondent in self._correspondents:
				check_box = QCheckBox(correspondent)
				check_box.setChecked(correspondent not in self._hiddenCorrespondents)
				check_box.clicked.connect(self.checkSomeCorrespondent)
				correspondents_layout.addWidget(check_box)
				self._correspondentsCheckboxes.append(check_box)
				if correspondent in self._hiddenCorrespondents:
					all = False
				else:
					none = False

			if all:
				self._allCorrespondentsCheckbox.setCheckState(Qt.Checked)
			elif none:
				self._allCorrespondentsCheckbox.setCheckState(Qt.Unchecked)
			else:
				self._allCorrespondentsCheckbox.setCheckState(Qt.PartiallyChecked)
		else:
			correspondents_layout.addWidget(QLabel(self.tr("No correspondent defined")))

		correspondents_layout.addStretch()

		topics_layout = QVBoxLayout()
		topics_layout.setSpacing(0)
		topics_widget = QWidget()
		topics_widget.setStyleSheet("font-family:monospace,courier new,courier; white-space:pre; color:blue;")
		topics_widget.setLayout(topics_layout)
		topics_scrollArea = QScrollArea()
		topics_scrollArea.setWidgetResizable(True)
		topics_scrollArea.setBackgroundRole(QPalette.Base)
		topics_scrollArea.setFrameShape(QFrame.NoFrame)
		topics_scrollArea.setWidget(topics_widget)
		self._tabWidget.addTab(topics_scrollArea, self.tr("Topics"))

		if self._topics:
			topics_layout.addWidget(self._allTopicsCheckbox)

			all = True
			none = True

			for topic in self._topics:
				check_box = QCheckBox(topic)
				check_box.setChecked(topic not in self._hiddenTopics)
				check_box.clicked.connect(self.checkSomeTopic)
				topics_layout.addWidget(check_box)
				self._topicsCheckboxes.append(check_box)
				if topic in self._hiddenTopics:
					all = False
				else:
					none = False

			if all:
				self._allTopicsCheckbox.setCheckState(Qt.Checked)
			elif none:
				self._allTopicsCheckbox.setCheckState(Qt.Unchecked)
			else:
				self._allTopicsCheckbox.setCheckState(Qt.PartiallyChecked)

			topics_layout.addStretch()
		else:
			topics_layout.addWidget(QLabel(self.tr("No topic defined")))
			topics_layout.addStretch()

		display_box = QGroupBox(self.tr("Display format"))
		display_box_layout = QVBoxLayout(display_box)
		general_layout.addWidget(display_box)

		display_box_layout.addWidget(self._displayFlatButton)
		display_box_layout.addWidget(self._displayEmphasizedCorrespondentButton)
		display_box_layout.addWidget(self._displayCorrespondentOnlyBytton)
		display_box_layout.addWidget(self._displayNoTopicButton)

		buffer_box = QGroupBox(self.tr("Display buffer"))
		buffer_box_layout = QGridLayout(buffer_box)
		general_layout.addWidget(buffer_box)

		label = QLabel(self.tr("Buffer maximum size :"))
		label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
		buffer_box_layout.addWidget(label, 0, 0)
		buffer_box_layout.addWidget(self._bufferSizeComboBox, 0, 1)

		general_layout.addSpacing(8)

		apply_button = QPushButton(self.tr("Apply"))
		ignore_button = QPushButton(self.tr("Ignore"))

		button_layout = QHBoxLayout()
		button_layout.addStretch(1)
		button_layout.addWidget(apply_button)
		button_layout.addWidget(ignore_button)
		general_layout.addLayout(button_layout)
		
		self.setLayout(main_layout)

		apply_button.pressed.connect(self.apply)
		ignore_button.pressed.connect(self.accept)
		self._allCorrespondentsCheckbox.clicked.connect(self.checkAllCorrespondents)
		self._allTopicsCheckbox.clicked.connect(self.checkAllTopics)

		ignore_button.setFocus()

	#__________________________________________________________________
	@pyqtSlot(bool)
	def checkAllCorrespondents(self, checked):
		
		if not checked:
			for cb in self._correspondentsCheckboxes:
				cb.setChecked(False)
		else:
			self._allCorrespondentsCheckbox.setCheckState(Qt.Checked) # tristate oblige
			for cb in self._correspondentsCheckboxes:
				cb.setChecked(True)

	#__________________________________________________________________
	@pyqtSlot(bool)
	def checkAllTopics(self, checked):

		if not checked:
			for cb in self._topicsCheckboxes:
				cb.setChecked(False)
		else:
			self._allTopicsCheckbox.setCheckState(Qt.Checked) # tristate oblige
			for cb in self._topicsCheckboxes:
				cb.setChecked(True)

	#__________________________________________________________________
	@pyqtSlot(bool)
	def checkSomeCorrespondent(self, checked):
		
		all = checked
		none = not checked

		for cb in self._correspondentsCheckboxes:
			if checked and not cb.isChecked():
				self._allCorrespondentsCheckbox.setCheckState(Qt.PartiallyChecked)
			elif not checked and cb.isChecked():
				self._allCorrespondentsCheckbox.setCheckState(Qt.PartiallyChecked)
			if cb.isChecked():
				none = False
			else:
				all = False

		if all:
			self._allCorrespondentsCheckbox.setCheckState(Qt.Checked)
		elif none:
			self._allCorrespondentsCheckbox.setCheckState(Qt.Unchecked)

	#__________________________________________________________________
	@pyqtSlot(bool)
	def checkSomeTopic(self, checked):

		all = checked
		none = not checked

		for cb in self._topicsCheckboxes:
			if checked and not cb.isChecked():
				self._allTopicsCheckbox.setCheckState(Qt.PartiallyChecked)
			elif not checked and cb.isChecked():
				self._allTopicsCheckbox.setCheckState(Qt.PartiallyChecked)
			if cb.isChecked():
				none = False
			else:
				all = False

		if all:
			self._allTopicsCheckbox.setCheckState(Qt.Checked)
		elif none:
			self._allTopicsCheckbox.setCheckState(Qt.Unchecked)

	#__________________________________________________________________
	def closeEvent(self, event):

		if self._tabWidget.currentIndex() == 0:
			reg = QSettings()
			reg.setValue("filter width", self.size().width())
			reg.sync()
		else:
			self._tabWidget.setCurrentIndex(0)
			event.ignore()