#!/usr/bin/env python


###############################################################################
##
## Topics reset dialog.
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


from PyQt5.QtCore import QCoreApplication, Qt, pyqtSignal, pyqtSlot, QSettings, QSize, QPoint
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QVBoxLayout, QGridLayout,
	QFrame, QLabel, QPushButton, QSizePolicy, QGroupBox, QLineEdit, QCheckBox, QWidget,
	QTabWidget, QComboBox, QRadioButton, QScrollArea)
from PyQt5.QtGui import QIcon, QImage, QFont, QPalette

import logging


class ObserverWillsDialog(QDialog):

	resetWills = pyqtSignal(list)

	#__________________________________________________________________
	def __init__(self, observation, session, logger, topics):

		super(ObserverWillsDialog, self).__init__()

		self._observation = observation
		self._session = session
		self._logger = logger
		self._topics = topics

		self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
		self.setWindowTitle(self.tr("Topics will reset"))
		self.setWindowIcon(QIcon('settings.svg'))

		self._topicsCheckboxes = []

		self._tabWidget = QTabWidget()
		self._allTopicsCheckbox = QCheckBox(self.tr("All"))

		self.buildUi()

		reg = QSettings()
		width = reg.value("reset wills width", 400)
		self.resize(width, self.size().height())

	#__________________________________________________________________
	@pyqtSlot()
	def accept(self):

		self.close()

	#__________________________________________________________________
	@pyqtSlot()
	def apply(self):

		checked_topics = []		
		for cb in self._topicsCheckboxes:
			if cb.isChecked():
				checked_topics.append(cb.text())

		self.resetWills.emit(checked_topics)
		self.accept()

	#__________________________________________________________________
	def buildUi(self):	
	
		main_layout = QVBoxLayout()
		main_layout.addWidget(self._tabWidget)

		general_layout = QVBoxLayout()
		general_layout.setSpacing(12)
		general_widget = QWidget()
		general_widget.setLayout(general_layout)
		self._tabWidget.addTab(general_widget, self.tr("Topics"))

		general_layout.addSpacing(8)

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
		general_layout.addWidget(topics_scrollArea)

		if self._topics:
			topics_layout.addWidget(self._allTopicsCheckbox)

			for topic in self._topics:
				check_box = QCheckBox(topic)
				check_box.clicked.connect(self.checkSomeTopic)
				topics_layout.addWidget(check_box)
				self._topicsCheckboxes.append(check_box)

			topics_layout.addStretch()
		else:
			topics_layout.addWidget(QLabel(self.tr("No topic defined")))
			topics_layout.addStretch()	

		general_layout.addSpacing(8)

		apply_button = QPushButton(self.tr("Clear will for selected topics"))
		ignore_button = QPushButton(self.tr("Ignore"))

		button_layout = QHBoxLayout()
		button_layout.addWidget(apply_button, Qt.AlignLeft)
		button_layout.addWidget(ignore_button)
		general_layout.addLayout(button_layout)

		self.setLayout(main_layout)

		apply_button.pressed.connect(self.apply)
		ignore_button.pressed.connect(self.accept)
		self._allTopicsCheckbox.clicked.connect(self.checkAllTopics)

		ignore_button.setFocus()

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

		reg = QSettings()
		reg.setValue("reset wills width", self.size().width())
		reg.sync()
