#!/usr/bin/env python


###############################################################################
##
## Observer regex settings dialog.
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
	QFrame, QLabel, QPushButton, QSizePolicy, QGroupBox, QLineEdit, QCheckBox, QSpacerItem)
from PyQt5.QtGui import QIcon, QImage, QFont

import logging, re
from threading import Timer


class ObserverRegexDialog(QDialog):

	#__________________________________________________________________
	def __init__(self, logger, session):

		super(ObserverRegexDialog, self).__init__()

		self._logger = logger
		self._session = session
		self._updatingOutbox = False
		
		reg = QSettings()

		self._count = QLabel()
		self._countLeftEstimated = QLabel()
		self._metersLeftEstimated = QLabel()

		self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
		self.setWindowTitle(self.tr("Correspondent in topic"))
		self.setWindowIcon(QIcon('settings.svg'))        
		self.setStyleSheet("QLineEdit { font-family: courier new, courier, monospace, lucinda console; }")

		reg.beginGroup(self._session)
		self._varRootInput = QLineEdit(reg.value("root topic", ''))
		reg.endGroup()
		self._varRootInput.setReadOnly(True)
		self._varInboxInput = QLineEdit()
		self._varOutboxInput = QLineEdit()
		self._regexInboxInput = QLineEdit()
		self._regexInbox = QLabel()
		self._regexInbox.setStyleSheet("QLabel { font-family: courier new, courier, monospace, lucinda console; }")
		self._regexOutboxInput = QLineEdit()
		self._regexOutbox = QLabel()
		self._regexOutbox.setStyleSheet("QLabel { font-family: courier new, courier, monospace, lucinda console; }")
		self._regexDefaultInput = QLineEdit()
		self._regexDefault = QLabel()
		self._regexDefault.setStyleSheet("QLabel { font-family: courier new, courier, monospace, lucinda console; }")
	
		self.buildUi()

		Timer(0, self.layoutLoadSettings).start()

		reg.beginGroup(self._session)
		rootTopic = reg.value("root topic", '')
		inbox = reg.value("param inbox", 'inbox')	
		outbox = reg.value("param outbox", 'outbox')	
		self._varInboxInput.setText(inbox)
		self._varOutboxInput.setText(outbox)
		self._regexInboxInput.setText(reg.value("regex inbox", r'^%ROOT%/(?P<correspondent>.+)/%INBOX%$'))
		self._regexOutboxInput.setText(reg.value("regex outbox", r'^%ROOT%/(?P<correspondent>.+)/%OUTBOX%$'))
		self._regexDefaultInput.setText(reg.value("regex default", r'.*/(?P<correspondent>[^/]+)/[^/]+$'))
		reg.endGroup()

		self._regexInbox.setText(self._regexInboxInput.text().replace("%ROOT%", rootTopic).replace("%INBOX%", inbox))
		self._regexOutbox.setText(self._regexOutboxInput.text().replace("%ROOT%", rootTopic).replace("%OUTBOX%", outbox))
		self._regexDefault.setText(self._regexDefaultInput.text())

		self._varInboxInput.textChanged.connect(self.updateInbox)
		self._regexInboxInput.textChanged.connect(self.updateInbox)
		self._regexOutboxInput.textChanged.connect(self.updateOutbox)
		self._regexOutboxInput.textChanged.connect(self.updateOutbox)
		self._regexDefaultInput.textChanged.connect(self.updateDefault)

	#__________________________________________________________________
	@pyqtSlot()
	def apply(self):

		reg = QSettings()
		
		reg.setValue("regex width", self.size().width())

		reg.beginGroup(self._session)

		reg.setValue("param inbox", self._varInboxInput.text().strip())
		reg.setValue("param outbox", self._varOutboxInput.text().strip())

		regex = self._regexInboxInput.text()
		try:
			re.compile(regex)
			reg.setValue("regex inbox", regex)
		except:
			self._logger.warning(self.tr("Can't apply regex inbox change (invalid) : ") + regex)

		regex = self._regexOutboxInput.text()
		try:
			re.compile(regex)
			reg.setValue("regex outbox", regex)
		except:
			self._logger.warning(self.tr("Can't apply regex outbox change (invalid) : ") + regex)

		regex = self._regexDefaultInput.text()
		try:
			re.compile(regex)
			reg.setValue("regex default", regex)
		except:
			self._logger.warning(self.tr("Can't apply regex default change (invalid) : ") + regex)

		reg.endGroup()
		reg.sync()

		self.accept()

	#__________________________________________________________________
	def buildUi(self):	
	
		main_layout = QVBoxLayout()
		main_layout.setSpacing(12)

		var_box = QGroupBox(self.tr("Variables"))
		var_box_layout = QGridLayout(var_box)
		main_layout.addWidget(var_box)

		var_box_layout.addWidget(QLabel(self.tr("%ROOT% (root topic) :")), 0, 0)
		var_box_layout.addWidget(self._varRootInput, 0, 1)

		var_box_layout.addWidget(QLabel(self.tr("%INBOX% (correspondent inbox) :")), 1, 0)
		var_box_layout.addWidget(self._varInboxInput, 1, 1)

		var_box_layout.addWidget(QLabel(self.tr("%OUTBOX% (correspondent outbox) :")), 2, 0)
		var_box_layout.addWidget(self._varOutboxInput, 2, 1)

		regex_box = QGroupBox(self.tr("Regex to extract correspondent from topic"))
		regex_box_layout = QGridLayout(regex_box)
		main_layout.addWidget(regex_box)

		regex_box_layout.addWidget(QLabel(self.tr("Inbox :")), 0, 0)
		regex_box_layout.addWidget(self._regexInboxInput, 0, 1)
		regex_box_layout.addWidget(self._regexInbox, 1, 1)

		regex_box_layout.addItem(QSpacerItem(12 , 12), 2, 0)

		regex_box_layout.addWidget(QLabel(self.tr("Outbox :")), 3, 0)
		regex_box_layout.addWidget(self._regexOutboxInput, 3, 1)
		regex_box_layout.addWidget(self._regexOutbox, 4, 1)

		regex_box_layout.addItem(QSpacerItem(12 , 12), 5, 0)

		regex_box_layout.addWidget(QLabel(self.tr("Default :")), 6, 0)
		regex_box_layout.addWidget(self._regexDefaultInput, 6, 1)
		regex_box_layout.addWidget(self._regexDefault, 7, 1)

		main_layout.addSpacing(8)

		apply_button = QPushButton(self.tr("Apply"))
		ignore_button = QPushButton(self.tr("Ignore"))
		reset_button = QPushButton(self.tr("Reset"))

		button_layout = QHBoxLayout()
		button_layout.addWidget(reset_button)
		button_layout.addStretch()
		button_layout.addWidget(apply_button)
		button_layout.addWidget(ignore_button)
		main_layout.addLayout(button_layout)

		self.setLayout(main_layout)

		apply_button.pressed.connect(self.apply)
		ignore_button.pressed.connect(self.accept)
		reset_button.pressed.connect(self.reset)

		ignore_button.setFocus()

	#__________________________________________________________________
	def closeEvent(self, event):

		reg = QSettings()
		reg.setValue("regex width", self.size().width())
		reg.sync()

	#__________________________________________________________________
	def layoutLoadSettings(self):

		reg = QSettings()
		width = reg.value("regex width", 400)
		self.resize(width, 0)

	#__________________________________________________________________
	@pyqtSlot()
	def reset(self):

		reg = QSettings()
		reg.beginGroup(self._session)
		self._varInboxInput.setText('inbox')
		self._varOutboxInput.setText('outbox')
		self._regexInboxInput.setText(r'^%ROOT%/(?P<correspondent>.+)/%INBOX%$')
		self._regexOutboxInput.setText(r'^%ROOT%/(?P<correspondent>.+)/%OUTBOX%$')
		self._regexDefaultInput.setText(r'.*/(?P<correspondent>[^/]+)/[^/]+$')
		reg.endGroup()

		rootTopic = reg.value("root topic", '')
		self._regexInbox.setText(self._regexInboxInput.text().replace("%ROOT%", rootTopic).replace("%INBOX%", 'inbox'))
		self._regexOutbox.setText(self._regexOutboxInput.text().replace("%ROOT%", rootTopic).replace("%OUTBOX%", 'outbox'))
		self._regexDefault.setText(self._regexDefaultInput.text())

	#__________________________________________________________________
	@pyqtSlot(str)
	def updateDefault(self, whatever):

		regex = self._regexDefaultInput.text()
		try:	
			re.compile(regex)
			self._regexDefault.setText(regex)
		except:
			self._regexDefault.setText(self.tr("Regular expression is not valid"))

	#__________________________________________________________________
	@pyqtSlot(str)
	def updateInbox(self, whatever):

		regex = self._regexInboxInput.text().replace("%ROOT%", self._varRootInput.text()).replace("%INBOX%", self._varInboxInput.text())
		try:	
			re.compile(regex)
			self._regexInbox.setText(regex)
		except:
			self._regexInbox.setText(self.tr("Regular expression is not valid"))

	#__________________________________________________________________
	@pyqtSlot(str)
	def updateOutbox(self, whatever):

		regex = self._regexOutboxInput.text().replace("%ROOT%", self._varRootInput.text()).replace("%OUTBOX%", self._varOutboxInput.text())
		try:	
			re.compile(regex)
			self._regexOutbox.setText(regex)
		except:
			self._regexOutbox.setText(self.tr("Regular expression is not valid"))
