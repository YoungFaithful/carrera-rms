""" Carrera(R) Digital 124/132 race management system based on carreralib"""
""" Copyright 2017 Thomas Reich thomas@geekazoids.net """
""" V1.0 Initial release """
""" V1.0.1 Formatting of display, outputs and other display improvements """
#For webpage
from flask import (Flask, render_template)
PORT=5000

#For threading
from threading import Thread

from PyQt5.QtWidgets import (
     QApplication,
     QWidget,
     QLCDNumber,
     QProgressBar,
     QPushButton,
     QLabel,
     QFrame,
     QVBoxLayout,
     QHBoxLayout,
     QGroupBox,
     QTabWidget,
     QComboBox,
     QCheckBox,
     QLineEdit,
     QGridLayout,
     QShortcut,
     QInputDialog,
     QDialog,
     QListWidget,
     QSizePolicy,
     QTableWidget,
     QTableWidgetItem,
     QMainWindow
)

from PyQt5.QtCore import (
     QTimer,
     QTime,
     QObject,
     QByteArray,
     pyqtProperty,
     QPropertyAnimation,
     Qt,
     QThread
)

try:
    from PyQt5.QtBluetooth import (
         QBluetoothDeviceDiscoveryAgent
    )
except ImportError:
    QBluetoothDeviceDiscoveryAgent = None


from PyQt5.QtGui import (
     QKeySequence,
     QFont,
     QPainter,
     QPalette,
     QColor
)

from carreralib import ControlUnit
#Necessary for TimeoutErrorHandling
import carreralib
import sys, os
# For Sound
import vlc
# To wait
import time

#For audio output use the folder 'sounds'
class Audio:
    def __init__(self):
        self.list_songnames=os.listdir(os.path.realpath('sounds'))
        #Defines if audio was played in this handeling process
        self.played=False
        #setting up new directory for songs
        self.songs=dict()
        for song in self.list_songnames:
            #Input Name without ending as key and vlc Object as value
            self.songs[song.split('.')[0]]=vlc.MediaPlayer('file://'+os.path.realpath('sounds')+'/'+song)
    def play(self, songname):
        #Stop first to enable playing afterwards
        self.songs[songname].stop()
        self.songs[songname].play()


def posgetter(driver):
    return (-driver.lapcount, driver.time)
    
def CtrlNum(driver):
    return (driver.CtrlNum)

#Return Format and time
def formattime(time, longfmt):
    if time is None:
        return '--.---'
    s = time // 1000
    ms = time % 1000

    if not longfmt:
        return '%02d.%03d' % ( s % 60, ms)
    elif s < 3600:
        return '%d:%02d.%03d' % (s // 60, s % 60, ms)
    else:
        return '%d:%02d:%02d.%03d' % (s // 3600, (s // 60) % 60, s % 60, ms)

### Change to also use CU
class BtSelect(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Connect to Control Unit')
        self.initUI()
        

    def initUI(self):
        self.vLayout = QVBoxLayout(self)
        self.hBtnLayout = QHBoxLayout()
        if QBluetoothDeviceDiscoveryAgent != None:
            self.btList = QListWidget()
            self.vLayout.addWidget(self.btList)
            self.scanBtn = QPushButton('Scan')
            self.hBtnLayout.addWidget(self.scanBtn)
        else:
            self.cuAddressInput = QLineEdit()
            self.hCuAddressLayout = QHBoxLayout()
            self.hCuAddressLayout.addWidget(QLabel('Enter CU BT address or USB device'))
            self.hCuAddressLayout.addWidget(self.cuAddressInput)
            self.vLayout.addLayout(self.hCuAddressLayout)
        self.connectBtn = QPushButton('Connect')
        self.hBtnLayout.addWidget(self.connectBtn)
        self.rejectBtn = QPushButton('Cancel')
        self.hBtnLayout.addWidget(self.rejectBtn)
        self.vLayout.addLayout(self.hBtnLayout)
        self.connectBtn.clicked.connect(self.accept)
        self.rejectBtn.clicked.connect(self.reject)

class StartLight(QWidget):
    def __init__(self):
        super().__init__()
        self.onVal = False
        self.update()

    def setOn(self, on):
        self.onVal = on
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.onVal:
             painter.setBrush(QColor(40, 40, 40))
        else:
             painter.setBrush(Qt.red)
        painter.drawEllipse(0,0, self.width(), self.height())

class StartLights(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        hbox = QHBoxLayout(self)
        self.lightOne = StartLight()
        self.lightTwo = StartLight()
        self.lightThree = StartLight()
        self.lightFour = StartLight()
        self.lightFive = StartLight()
        hbox.addWidget(self.lightOne)
        hbox.addWidget(self.lightTwo)
        hbox.addWidget(self.lightThree)
        hbox.addWidget(self.lightFour)
        hbox.addWidget(self.lightFive)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        lightsPal = self.palette()
        lightsPal.setColor(lightsPal.Background, Qt.black)
        self.setPalette(lightsPal)
        self.spacekey = QShortcut(QKeySequence("Space"), self)
        
class Rms(QMainWindow):
    def __init__(self):
        super().__init__()

        self.shutdown = False
        # Counter for sleeping before exiting
        self.cuoffcounter=0
        if len(sys.argv) == 2:
            self.startRMS(sys.argv[1])
        else:
            self.btDialog = BtSelect()
            if QBluetoothDeviceDiscoveryAgent != None:
                self.discoverCU()
                self.btDialog.scanBtn.clicked.connect(self.discoverCU)
            if self.btDialog.exec_():
                if QBluetoothDeviceDiscoveryAgent != None:
                    if self.discoverBtDevice.isActive():
                        self.discoverBtDevice.stop()
                    BTdevice = self.btDialog.btList.selectedItems()
                    self.cuaddress = BTdevice[0].text().split(' -> ')[1]
                else:
                    self.cuaddress = self.btDialog.cuAddressInput.text()
                self.startRMS(self.cuaddress)
            else:
                sys.exit()

    def closeEvent(self, event):
        self.shutdown = True
        self.cu.close()
        event.accept()

    def discoverCU(self):
        self.btDialog.scanBtn.setEnabled(False)
        self.discoverBtDevice = QBluetoothDeviceDiscoveryAgent()
        self.discoverBtDevice.setLowEnergyDiscoveryTimeout(5000)
        self.discoverBtDevice.deviceDiscovered.connect(self.addBtDevice)
        self.discoverBtDevice.finished.connect(self.btScanFinished)
        self.discoverBtDevice.error.connect(self.btScanError)
        self.discoverBtDevice.start()

    def addBtDevice(self, btDevice):
        self.btDialog.btList.addItem(str(btDevice.name()) + ' -> ' + str(btDevice.address().toString()))
        if btDevice.name() == 'Control_Unit':
            self.btDialog.btList.setCurrentRow(self.btDialog.btList.count() - 1)

    def btScanFinished(self):
        self.btDialog.scanBtn.setEnabled(True)

    def btScanError(self):
        print('Bluetooth scan error')
        sys.exit()

    def startRMS(self, device):
        self.cu = ControlUnit(device, timeout = 1.0)
        self.cuVersion = self.cu.version()
        self.initUI()

    def initUI(self):
        self.startLights = StartLights()
        rectDesktop = app.desktop().availableGeometry()
        self.startLights.resize(rectDesktop.width()/2, (rectDesktop.width()/2)/5)
        self.setWindowTitle('Race Management System V1.0   CU Version:' + str(self.cuVersion, 'utf-8'))
        self.rmsframe = RmsFrame(self.cu)
        self.startLights.spacekey.activated.connect(self.rmsframe.racestart)
        self.setCentralWidget(self.rmsframe)
   
    def run(self):
        last = None
        while True:
            if self.shutdown:
                break
            try:
                data = self.cu.request()
                app.processEvents()
                if data == last:
                    continue
                elif isinstance(data, ControlUnit.Status):
                    self.handle_status(data)
                elif isinstance(data, ControlUnit.Timer):
                    self.handle_timer(data)
                else:
                    pass
                last = data
                #Reset sleepcounter if run worked
                self.cuoffcounter=0

#Handle Exception 
            except carreralib.connection.TimeoutError:
                if self.cuoffcounter ==0:
                    print('Missing signal from CU')
                if self.cuoffcounter < 30:
                    time.sleep(1)
                    self.cuoffcounter+=1
                    pass
                else:
                    raise
            except Exception:
                raise
        sys.exit()


    def handle_status(self, status):
        if status.start > 0 and status.start <= 7:
            self.startLights.show()
            if status.start == 1 or status.start == 2:
                self.startLights.lightOne.setOn(True)
            if status.start == 1 or status.start == 3:
                self.startLights.lightTwo.setOn(True)
                audio.play("beeplow")
            if status.start == 1 or status.start == 4:
                self.startLights.lightThree.setOn(True)
                audio.play("beeplow")
            if status.start == 1 or status.start == 5:
                self.startLights.lightFour.setOn(True)
                audio.play("beeplow")
            if status.start == 1 or status.start == 6:
                self.startLights.lightFive.setOn(True)
                audio.play("beeplow")
            if status.start == 2 or status.start == 7:
                if status.start == 7:
                    self.startLights.lightOne.setOn(False)
                self.startLights.lightTwo.setOn(False)
                self.startLights.lightThree.setOn(False)
                self.startLights.lightFour.setOn(False)
                self.startLights.lightFive.setOn(False)
                audio.play("beephigh")
        else:
            self.startLights.hide()
        for driver, fuel in zip(self.rmsframe.driverArr, status.fuel):
            if not driver.fuellevel == fuel and driver.pit:
                if fuel==15:
                    audio.play("last")
                else:
                    audio.play("tank")
            driver.fuellevel=fuel
        for driver, pit in zip(self.rmsframe.driverArr, status.pit):
            if pit and not driver.pit:
                driver.pitcount += 1
            driver.pit = pit
        self.binmode = "{0:04b}".format(status.mode)
        self.rmsframe.updateDisplay(self.binmode)
        self.status = status

    def handle_timer(self, timer):
        driver = self.rmsframe.driverArr[timer.address]
        driver.newlap(timer)
        if self.rmsframe.start is None:
            self.rmsframe.start = timer.timestamp
        self.rmsframe.updateDisplay(None)

class CtrlDialog(QDialog):
    def __init__(self, driverArr):
        super().__init__()
        self.driverArr = driverArr
        self.setWindowTitle('Assign Controller')
        self.vlayout = QVBoxLayout(self)
        self.table = QTableWidget(6,2)
        self.table.verticalHeader().hide()
        self.vlayout.addWidget(self.table)
        self.table.setHorizontalHeaderLabels(['Driver', 'Controller'])
        for idx, driverObj in enumerate(driverArr):
            if idx < 6:
                ctrlCombobox = QComboBox()
                for ctrlItem in range(1,7):
                    ctrlCombobox.addItem(str(ctrlItem))
                self.table.setItem(idx,0, QTableWidgetItem(driverObj.name))
                ctrlCombobox.setCurrentIndex(idx)
                self.table.setCellWidget(idx,1, ctrlCombobox)
        self.setCtrlBtn = QPushButton('Set Controllers')
        self.closeBtn = QPushButton('Cancel')
        self.hlayout = QHBoxLayout()
        self.vlayout.addLayout(self.hlayout)
        self.hlayout.addWidget(self.setCtrlBtn)
        self.hlayout.addWidget(self.closeBtn)
        self.setCtrlBtn.clicked.connect(self.setNewCtrl)
        self.closeBtn.clicked.connect(self.reject)

    def setNewCtrl(self):
        self.newDriverArr = [None] * 8
        for cellNum in range(0, 8):
            if cellNum < 6:
                self.newDriverArr[int(self.table.cellWidget(cellNum, 1).currentText()) - 1] = self.driverArr[cellNum]
                self.driverArr[cellNum].setCtrlNum(int(self.table.cellWidget(cellNum, 1).currentText()))
            else:
                self.newDriverArr[cellNum] = self.driverArr[cellNum]
        self.accept()
 
class RaceModeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Set Race Mode')
        self.labels = ['', 'Minutes', 'Laps']
        self.setupUI()
    
    def setupUI(self):
        self.vlayout = QVBoxLayout(self)
        self.selectRaceGroup = QGroupBox('Race')
        self.raceLayout = QHBoxLayout()
        self.selectRaceGroup.setLayout(self.raceLayout)
        self.selectRaceCombo = QComboBox()
        self.selectRaceCombo.addItems(['Timed', 'Laps'])
        self.selectRaceCombo.currentIndexChanged.connect(self.changeRaceMode)
        self.raceModeInput = QLineEdit()
        self.raceModeInput.setMaxLength(4)
        self.raceModeInput.setText('20')
        self.raceModeLabel = QLabel()
        self.vlayout.addWidget(self.selectRaceGroup)
        self.raceLayout.addWidget(self.selectRaceCombo)
        self.raceLayout.addWidget(self.raceModeInput)
        self.raceLayout.addStretch(1)
        self.raceLayout.addWidget(self.raceModeLabel)
        self.selectRaceCombo.setCurrentIndex(1)

        self.doPractice = QCheckBox('Practice')
        self.doPractice.setChecked(False)
        self.doPractice.stateChanged.connect(self.practiceEnable)
        self.practiceCombo = QComboBox()
        self.practiceCombo.addItems(['Open', 'Timed', 'Laps'])
        self.practiceCombo.currentIndexChanged.connect(self.changePracticeMode)
        self.practiceInput = QLineEdit()
        self.practiceInput.setMaxLength(4)
        self.practiceLabel = QLabel()
        self.practiceCombo.setCurrentIndex(1)

        self.doQuali = QCheckBox('Qualifying')
        self.doQuali.setChecked(False)
        self.doQuali.stateChanged.connect(self.qualiEnable)
        self.qualiCombo = QComboBox()
        self.qualiCombo.addItems(['Open', 'Timed', 'Laps'])
        self.qualiCombo.currentIndexChanged.connect(self.changeQualiMode)
        self.qualiInput = QLineEdit()       
        self.qualiInput.setMaxLength(4)
        self.qualiLabel = QLabel()
        self.qualiCombo.setCurrentIndex(1)

        self.checkBoxhlayout = QHBoxLayout()
        self.checkBoxhlayout.addWidget(self.doPractice)
        self.checkBoxhlayout.addWidget(self.doQuali)
        self.vlayout.addLayout(self.checkBoxhlayout)
        self.practicehbox = QHBoxLayout()
        self.practiceFrame = QGroupBox('Practice')
        self.practiceFrame.setLayout(self.practicehbox)
        self.qualihbox = QHBoxLayout()
        self.qualiFrame = QGroupBox('Qualifying')
        self.qualiFrame.setLayout(self.qualihbox)
        self.practicehbox.addWidget(self.practiceCombo)
        self.practicehbox.addWidget(self.practiceInput)
        self.practicehbox.addStretch(1)
        self.practicehbox.addWidget(self.practiceLabel)
        self.qualihbox.addWidget(self.qualiCombo)
        self.qualihbox.addWidget(self.qualiInput)
        self.qualihbox.addStretch(1)
        self.qualihbox.addWidget(self.qualiLabel)
        self.vlayout.addWidget(self.practiceFrame)
        self.vlayout.addStretch(1)
        self.vlayout.addWidget(self.qualiFrame)

        self.startRaceBtn = QPushButton('Start Race')
        self.startRaceBtn.clicked.connect(self.accept)
        self.cancelBtn = QPushButton('Cancel')
        self.cancelBtn.clicked.connect(self.close)
        self.buttonLayout = QHBoxLayout()
        self.vlayout.addLayout(self.buttonLayout)
        self.buttonLayout.addWidget(self.startRaceBtn)
        self.buttonLayout.addWidget(self.cancelBtn)
        
    def changeRaceMode(self, index):
        self.raceModeLabel.setText(self.labels[index + 1])

    def practiceEnable(self, state):
        if state == Qt.Checked:
            self.practiceFrame.show()
        else:
            self.practiceFrame.hide()

    def changePracticeMode(self, index):
        if index == 0:
            self.practiceInput.hide()
        else:
            self.practiceInput.show()
        self.practiceLabel.setText(self.labels[index])

    def qualiEnable(self, state):
        if state == Qt.Checked:
            self.qualiFrame.show()
        else:
            self.qualiFrame.hide()

    def changeQualiMode(self, index):
        if index == 0:
            self.qualiInput.hide()
        else:
            self.qualiInput.show()
        self.qualiLabel.setText(self.labels[index])

    def getRaceModeInfo(self):
        self.raceModeDict = {}
        if self.doPractice.isChecked():
            self.raceModeDict['Practice'] = {}
            self.raceModeDict['Practice']['amount'] = str(self.practiceInput.text())
            self.raceModeDict['Practice']['mode'] = self.practiceCombo.currentText()
        if self.doQuali.isChecked():
            self.raceModeDict['Qualification'] = {}
            self.raceModeDict['Qualification']['amount'] = str(self.qualiInput.text())
            self.raceModeDict['Qualification']['mode'] = self.qualiCombo.currentText()
        self.raceModeDict['Race'] = {}
        self.raceModeDict['Race']['amount'] = str(self.raceModeInput.text())
        self.raceModeDict['Race']['mode'] = self.selectRaceCombo.currentText()
        return self.raceModeDict

class RmsFrame(QFrame):
    def __init__(self, cu):
        super().__init__()
        self.cu = cu
        self.session = RaceSession()
        self.resetRMS()
        self.buildframe()
        self.nameBtn = {}
        self.driverPos = {}
        self.driverObj = {}
        self.lapcount = {}
        self.totalTime = {}
        self.laptime = {}
        self.bestlaptime = {}
        self.fuelbar = {}
        self.pits = {}
        self.audio=Audio()
#        QBAcolor = QByteArray()
#        QBAcolor.append('color')
#        self.animation = anim = QPropertyAnimation(self, QBAcolor, self)
#        anim.setDuration(250)
#        anim.setLoopCount(2)
#        anim.setStartValue(QColor(230,230, 0))
#        anim.setEndValue(QColor(0, 0, 0))
#        anim.setKeyValueAt(0.5, QColor(150,100,0))

    def buildframe(self):
        self.vLayout = QVBoxLayout(self)
        self.hBtnLayout = QHBoxLayout()
        self.vLayout.addLayout(self.hBtnLayout)
# Add driver to grid
        self.addDriverBtn = QPushButton('(A)dd Driver')
        self.addDriverKey = QShortcut(QKeySequence("a"), self)
        self.hBtnLayout.addWidget(self.addDriverBtn)
        self.addDriverBtn.clicked.connect(self.addDriver)
        self.addDriverKey.activated.connect(self.addDriver)
# Assign Controller
        self.assignCtrlBtn = QPushButton('Assign Controller')
        self.hBtnLayout.addWidget(self.assignCtrlBtn)
        self.assignCtrlBtn.clicked.connect(self.openCtrlDialog)
# Setup a race
        self.setupRace = QPushButton('Setup a Race')
        self.hBtnLayout.addWidget(self.setupRace)
        self.setupRace.clicked.connect(self.openRaceDlg)
# Code cars
        self.codeBtn = QPushButton('(C)ode')
        self.codeKey = QShortcut(QKeySequence("c"), self)
        self.hBtnLayout.addWidget(self.codeBtn)
        self.codeBtn.clicked.connect(self.pressCode)
        self.codeKey.activated.connect(self.pressCode)
# Start pace car
        self.paceBtn = QPushButton('(P)ace')
        self.paceKey = QShortcut(QKeySequence("p"), self)
        self.hBtnLayout.addWidget(self.paceBtn)
        self.paceBtn.clicked.connect(self.setPace)
        self.paceKey.activated.connect(self.setPace)
# set Speed
        self.setSpeedBtn = QPushButton('Set (S)peed')
        self.setSpeedKey = QShortcut(QKeySequence("s"), self)
        self.hBtnLayout.addWidget(self.setSpeedBtn)
        self.setSpeedBtn.clicked.connect(self.setSpeed)
        self.setSpeedKey.activated.connect(self.setSpeed)
# set Brakes
        self.setBrakeBtn = QPushButton('Set (B)rake')
        self.setBrakeKey = QShortcut(QKeySequence("b"), self)
        self.hBtnLayout.addWidget(self.setBrakeBtn)
        self.setBrakeBtn.clicked.connect(self.setBrake)
        self.setBrakeKey.activated.connect(self.setBrake)
# Set Fuel
        self.setFuelBtn = QPushButton('Set (F)uel')
        self.setFuelKey = QShortcut(QKeySequence("f"), self)
        self.hBtnLayout.addWidget(self.setFuelBtn)
        self.setFuelBtn.clicked.connect(self.setFuel)
        self.setFuelKey.activated.connect(self.setFuel)
# Reset CU
        self.resetBtn = QPushButton('(R)eset')
        self.resetKey = QShortcut(QKeySequence("r"), self)
        self.hBtnLayout.addWidget(self.resetBtn)
        self.resetBtn.clicked.connect(self.resetRMS)
        self.resetKey.activated.connect(self.resetRMS)
# Start Btn Layout
        self.hStartBtnLayout = QHBoxLayout()
# Session Info
        self.racemode = QLabel('No Race Started')
        self.racemode.setAlignment(Qt.AlignCenter)
        self.hStartBtnLayout.addWidget(self.racemode)
        self.hStartBtnLayout.addStretch(1)
# Start/Pause Race Enter
        self.startRaceBtn = QPushButton('Start Race or Enter changed Settings (Spacebar)')
        self.startRaceBtn.clicked.connect(self.racestart)
        self.spacekey = QShortcut(QKeySequence("Space"), self)
        self.spacekey.activated.connect(self.racestart)
        self.hStartBtnLayout.addWidget(self.startRaceBtn)
        self.hStartBtnLayout.setAlignment(self.startRaceBtn, Qt.AlignHCenter)
        self.hStartBtnLayout.addStretch(1)
# Hardware Info        
        self.pitLaneStatus = QLabel()
        self.hStartBtnLayout.addWidget(QLabel('Pitlane'))
        self.hStartBtnLayout.addWidget(self.pitLaneStatus)
        self.fuelmode = QLabel()
        self.hStartBtnLayout.addWidget(QLabel('Fuel Mode'))
        self.hStartBtnLayout.addWidget(self.fuelmode)
        self.lapCounter = QLabel()
        self.hStartBtnLayout.addWidget(QLabel('Lap Counter'))
        self.hStartBtnLayout.addWidget(self.lapCounter)

        self.vLayout.addLayout(self.hStartBtnLayout)
        self.vLayout.setAlignment(self.hStartBtnLayout, Qt.AlignTop)
#        self.sepline = QFrame()
#        self.sepline.setFrameShape(QFrame.HLine)
#        self.sepline.setFrameShadow(QFrame.Sunken)
#        self.vLayout.addWidget(self.sepline)
#        self.vLayout.setAlignment(self.sepline, Qt.AlignTop)
# Driver Grid
        self.vLayout.addLayout(self.buildGrid())
       # Session Info
       # self.racemode = QLabel('No Race Started')
        # self.racemode.setAlignment(Qt.AlignCenter)
        #self.racemode.setStyleSheet("QLabel{ border-radius: 10px; background-color: grey; center; color: blue; font: 30pt}")
        #self.vLayout.addWidget(self.racemode)
        #self.vLayout.setAlignment(self.racemode, Qt.AlignBottom)


    def buildGrid(self):
        self.mainLayout = QGridLayout()
        self.mainLayout.setSpacing(10)
        self.mainLayout.setHorizontalSpacing(10)
        self.headerFont = QFont()
        self.headerFont.setPointSize(14)
        self.headerFont.setBold(True)
        self.labelArr = [
        #'Pos', 
        'Position', 'Total', 'Name', 'Laps', 'Laptime', 'Best Lap', 'Fuel', 'Pits']
        for index, label in enumerate(self.labelArr):
            self.headerLabel = QLabel(label)
            self.headerLabel.setFont(self.headerFont)
            self.mainLayout.addWidget(self.headerLabel, 0 , index, Qt.AlignHCenter)
        self.mainLayout.setColumnStretch(1, 1)
        self.mainLayout.setColumnStretch(2, 1)
        self.mainLayout.setColumnStretch(3, 2)
        self.mainLayout.setColumnStretch(4, 3)
        self.mainLayout.setColumnStretch(5, 3)
        self.mainLayout.setColumnStretch(6, 2)
        self.mainLayout.setColumnStretch(7, 1)
        return self.mainLayout


    def openCtrlDialog(self):
        self.ctrlDialog = CtrlDialog(self.driverArr)
        if self.ctrlDialog.exec_():
            self.driverArr = self.ctrlDialog.newDriverArr
#Prepare Race and open dialog
    def openRaceDlg(self):
        # Refuel all cars to same amount
        self.setFuel()
        time.sleep(0.5)
        self.racestart()
        self.setupRaceDlg = RaceModeDialog()
        self.session.session = None
        self.session.type = None
        if self.setupRaceDlg.exec_():
            for driver in self.driverArr:
                driver.bestLapTime = None
                driver.time = None
                driver.lapcount = 0
                driver.pitcount = 0
            self.session.setRace(self.setupRaceDlg.getRaceModeInfo())
            self.racemode.setText(self.session.session + ' ' + str(self.session.amount) + ' ' + self.session.type)
            self.clearCU()
            self.cu.start()
        else:
            self.setupRaceDlg.close()

    def getColor(self):
        if self.mainLayout.itemAtPosition(1, 1):
            return self.mainLayout.itemAtPosition(1, 1).widget().palette().text()
        else:
            return None

    def setColor(self, color):
        PBwidget = self.mainLayout.itemAtPosition(1, 1).widget()
        palette = PBwidget.palette()
        palette.setColor(PBwidget.foregroundRole(), color)
        PBwidget.setFlat(True)
        PBwidget.setAutoFillBackground(True)
        PBwidget.setPalette(palette)

    color = pyqtProperty(QColor, getColor, setColor)

    def addDriver(self):
        driverRow = self.mainLayout.rowCount()
        if driverRow > 6:
            return
        driver = self.driverArr[driverRow - 1]
        self.posFont = QFont()
        self.posFont.setPointSize(25)
        self.posFont.setBold(True)
        self.driverPos[driverRow] = QLabel(driver.getName())
        self.driverPos[driverRow].setStyleSheet("QLabel{ border-radius: 10px; border-color: black; border: 5px solid black; background-color: white}")
        self.driverPos[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.driverPos[driverRow].setFont(self.posFont)
        self.mainLayout.addWidget(self.driverPos[driverRow], driverRow ,0)
        self.nameBtn[driverRow] = driver.getNameBtn()
        self.nameBtn[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.nameBtn[driverRow], driverRow ,2)
        #Object Driver
        self.driverObj[driverRow] = driver
        self.nameBtn[driverRow].clicked.connect(lambda: self.changeDriver(self.nameBtn[driverRow], self.driverObj[driverRow]))
        self.lapcount[driverRow] = driver.getLapCountLCD()
        self.lapcount[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.lapcount[driverRow], driverRow, 3)
        self.totalFont = QFont()
        self.totalFont.setPointSize(25)
        self.totalFont.setBold(True)
        self.totalTime[driverRow] = QLabel('00:00')
        self.totalTime[driverRow].setStyleSheet("QLabel{ border-radius: 10px; border-color: black; border: 5px solid black; background-color: white}")
        self.totalTime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.totalTime[driverRow].setFont(self.totalFont)
        self.mainLayout.addWidget(self.totalTime[driverRow], driverRow, 1)
        self.laptime[driverRow] = driver.getLapLCD()
        self.laptime[driverRow].setDigitCount(6)
        self.laptime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.laptime[driverRow], driverRow, 4)
        self.bestlaptime[driverRow] = driver.getBestLapLCD()
        self.bestlaptime[driverRow].setDigitCount(6)
        self.bestlaptime[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainLayout.addWidget(self.bestlaptime[driverRow], driverRow, 5)
        self.fuelbar[driverRow] = driver.getFuelBar()
        self.fuelbar[driverRow].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.mainLayout.addWidget(self.fuelbar[driverRow], driverRow, 6)
        self.pits[driverRow] = driver.getPits()
        self.pits[driverRow].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.mainLayout.addWidget(self.pits[driverRow], driverRow, 7)

    def racestart(self):
        self.cu.start()
#        self.mainLayout.itemAtPosition(1, 5).widget().setPits('Pit')
#        self.mainLayout.itemAtPosition(1, 5).widget().setPits('Track')

    def resetRMS(self):
        if hasattr(self, 'driverArr'):
            for driverObj in self.driverArr:
                driverObj.deleteLater()
        self.start = None
        #Setup of the table with Informations of the Drivers
        self.driverArr = [RmsDriver(num) for num in range(1, 9)]

        self.clearCU()

        if hasattr(self, 'mainLayout'):
            while True: 
                widgetToRemove = self.mainLayout.takeAt(0)
                if widgetToRemove == None:
                    break
                widgetToRemove.widget().deleteLater()
            racemode = self.vLayout.takeAt(3)
            mainItem = self.vLayout.takeAt(2)
            self.vLayout.removeItem(racemode)
            self.vLayout.removeItem(mainItem)
            mainItem.deleteLater()
            self.vLayout.addLayout(self.buildGrid())
            self.vLayout.addWidget(self.racemode)

    def clearCU(self):
        # discard remaining timer messages
        status = self.cu.request()
        while not isinstance(status, ControlUnit.Status):
            status = self.cu.request()
        self.status = status
        # reset cu timer
        self.cu.reset()


    def pressCode(self):
        print('press Code')
        self.cu.request(b'T8')

    def setFuel(self):
        print('set fuel')
        self.cu.request(b'T7')

    def setPace(self):
        print('pace car')
        self.cu.request(b'T1')

    def setSpeed(self):
        print('set speed')
        self.cu.request(b'T5')

    def setBrake(self):
        print('set brake')
        self.cu.request(b'T6')

    def changeDriver(self, driverButton, driverObj):
        self.driverChangeText = QInputDialog.getText(self, 'Change driver name', 'Driver Name', 0, driverButton.text().split('\n')[0])
        if self.driverChangeText[1] == True:
            driverButton.setText(self.driverChangeText[0])
            driverObj.name = self.driverChangeText[0]

    def updateDisplay(self, binMode):
        if binMode != None:
            if binMode[2] == '1':
                self.fuelmode.setText('Real')
            elif binMode[3] == '1':
                self.fuelmode.setText('On')
            elif binMode[3] == '0':
                self.fuelmode.setText('Off')
            if binMode[1] == '1':
                self.pitLaneStatus.setText('Exists')
            else:
                self.pitLaneStatus.setText('Missing')
            if binMode[0] == '1':
                self.lapCounter.setText('Exists')
            else:
                self.lapCounter.setText('Missing')

        driversInPlay = [driver for driver in self.driverArr if driver.time]
        ##### changed from +1 >
        if len(driversInPlay) +1 > self.mainLayout.rowCount():
            self.addDriver()
        # Refresh positions and leading time
        #Sorted by position
        for pos, driver in enumerate(sorted(driversInPlay, key=posgetter), start=1):
            #Calculate Position and Gap
            if pos == 1:
                if hasattr(self, 'leader') and self.leader != driver:
                    print('pos change')
#                self.animation.start()
                self.leader = driver
                t = formattime(driver.time - self.start, True)
            elif driver.lapcount == self.leader.lapcount:
                t = '+%ss' % formattime(driver.time - self.leader.time, False)
            else:
                gap = self.leader.lapcount - driver.lapcount
                t = '+%d Lap%s' % (gap, 's' if gap != 1 else '')
            #Position to qt app and web app
            self.driverPos[pos].setText('#'+str(pos)+'\n'+driver.name)
            web.position[driver.CtrlNum]='#'+str(pos)
            #Totaltime
            self.totalTime[pos].setText(t)
            web.totaltime[driver.CtrlNum]=t
        #Sorted by Controller number
        for pos, driver in enumerate(sorted(driversInPlay, key=CtrlNum), start=1):
            #Name
            self.nameBtn[pos].setText(driver.name + '\n' + str(driver.CtrlNum))
            web.name[driver.CtrlNum]=driver.name
            if self.session.lapcountup or self.session.amount == None:
                self.lapcount[pos].display(driver.lapcount)
                web.laps[driver.CtrlNum]=driver.lapcount
            else:
                self.lapcount[pos].display(self.session.amount-driver.lapcount)
                web.laps[driver.CtrlNum]=self.session.amount-driver.lapcount
            #Laptime to qt app and web app    
            self.laptime[pos].display(formattime(driver.lapTime, False))
            web.laptime[driver.CtrlNum]=formattime(driver.lapTime, True)
            #Best Lap time to qt app and web app
            self.bestlaptime[pos].display(formattime(driver.bestLapTime, False))            
            web.bestlaptime[driver.CtrlNum]=formattime(driver.bestLapTime, True)
            #Fuelbar
            self.fuelbar[pos].setValue(driver.fuellevel)
            #Make the dots for the web app
            if driver.fuellevel > 5:
                web.fuellevellights1[driver.CtrlNum]='⣿⣿⣿⣿⣿'
                web.fuellevellights2[driver.CtrlNum]='⣿'*(driver.fuellevel-5)
            else:
                web.fuellevellights1[driver.CtrlNum]='⣿'*driver.fuellevel
                web.fuellevellights2[driver.CtrlNum]=''
            web.fuellevel[driver.CtrlNum]=driver.fuellevel
            if driver.fuellevel > 0:
                self.fuelbar[pos].setStyleSheet("QProgressBar{ color: white; background-color: black; border: 5px solid black; border-radius: 10px; text-align: center}\
                                                QProgressBar::chunk { background: qlineargradient(x1: 1, y1: 0.5, x2: 0, y2: 0.5, stop: 0 #00AA00, stop: " + str(0.92 - (1 / (driver.fuellevel))) + " #22FF22, stop: " + str(0.921 - (1 / (driver.fuellevel))) + " #22FF22, stop: " + str(1.001 - (1 / (driver.fuellevel))) + " red, stop: 1 #550000); }")
            #Pitcount
            self.pits[pos].display(driver.pitcount)
            web.pits[driver.CtrlNum]=driver.pitcount
        #Race controlling
        if hasattr(self, 'leader') and self.session.session != None:
            # Check if race is over
            if self.session.type != None:
                self.racemode.setText(self.session.session + ' ' + str(self.session.amount) + ' ' + self.session.type)
            if self.session.type == 'Laps':
                self.session.lapcountup=False
                # Race ends after leading car finished and all other cars passed the start finish as well
                if self.leader.lapcount >= self.session.amount:
                    self.end=self.leader.time
                    self.racestop=True
                    for driver in self.driverArr:
                        if driver.time and driver.time < self.end:
                            self.racestop=False
                    if self.racestop:
                        self.racestart()
                        self.session.saveSessionData(driversInPlay)
                        self.clearCU()
                        self.session.sessionOver()
            elif self.session.type == 'Timed':
                if self.leader.time - self.start > self.session.amount * 60000:
                    self.end=self.leader.time
                    self.racestop=True
                    for driver in self.driverArr:
                        if driver.time and driver.time < self.end:
                            self.racestop=False
                    if self.racestop:
                        self.racestart()
                        self.session.saveSessionData(driversInPlay)
                        self.clearCU()
                        self.session.sessionOver()
            elif self.session.type == None:
                self.session.session = None
                self.showLeaderboard()
    #Show Leaderboard at the end
    def showLeaderboard(self):
        self.leaderBoard = LBDialog(self.session.leaderboard)
        self.leaderBoard.show()
      
class RaceSession(QObject):
    def __init__(self):
        super().__init__()
        self.amount = None
        self.session = None
        self.sessionSteps = ['Practice', 'Qualification', 'Race']
        # Just for displaying the remaining laps
        self.lapcountup=False

    def setRace(self, raceDict):
        self.leaderboard = {}
        self.raceDict = raceDict
        for stepIdx, step in enumerate(self.sessionSteps):
            if step in raceDict:
                self.type = raceDict[step]['mode']
                self.amount = int(raceDict[step]['amount'])
                self.session = step
                self.currentStep = stepIdx
                break

    def sessionOver(self):
        for step in self.sessionSteps:
            self.currentStep += 1
            if len(self.sessionSteps) > self.currentStep:
                if self.sessionSteps[self.currentStep] in self.raceDict:
                    self.session = self.sessionSteps[self.currentStep]
                    self.amount = int(self.raceDict[self.sessionSteps[self.currentStep]]['amount'])
                    self.type = self.raceDict[self.sessionSteps[self.currentStep]]['mode']
                    break
            else:
                self.type = None
                self.session = 'Race Finished'

    def saveSessionData(self, driverArr):
        if self.sessionSteps[self.currentStep] == 'Qualification':
            self.showStartRanking = StartRankDialog(driverArr)
            self.showStartRanking.exec_()

        self.leaderboard[self.sessionSteps[self.currentStep]] = []
        for driver in sorted(driverArr, key=posgetter):
            self.leaderboard[self.sessionSteps[self.currentStep]].append({'laps': driver.lapcount, 'total': driver.time,\
                     'best': driver.bestLapTime, 'pits': driver.pitcount, 'name': driver.name})
            driver.bestLapTime = None
            driver.time = None
            driver.lapcount = 0
            driver.pitcount = 0

class StartRankDialog(QDialog):
    def __init__(self, driverArr):
        super().__init__()
        self.driverArr = driverArr
        self.setWindowTitle('Starting Grid')
        self.setupUI()

    def setupUI(self):
        self.vlayout = QVBoxLayout(self)
        self.vlayout.addWidget(QLabel('Starting Grid'))
        self.table = QTableWidget(len(self.driverArr),3)
        self.vlayout.addWidget(self.table)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(['Grid Position', 'Driver', 'Best Lap'])
        for idx, driver in enumerate(sorted(self.driverArr, key = lambda x: (x.bestLapTime is None, x.bestLapTime))):
            self.table.setItem(idx,0, QTableWidgetItem(str(idx + 1)))
            self.table.setItem(idx,1, QTableWidgetItem(driver.name))
            self.table.setItem(idx,2, QTableWidgetItem(formattime(driver.bestLapTime, False)))
        self.okBtn = QPushButton('Ok')
        self.vlayout.addWidget(self.okBtn)
        self.okBtn.clicked.connect(self.accept)

class LBDialog(QTabWidget):
    def __init__(self, leaderboard):
        super().__init__()
        self.leaderboard = leaderboard
        self.setWindowTitle('Leaderboard')
        self.setWindowModality(Qt.ApplicationModal)
        self.setupUI()

    def setupUI(self):
        for session in sorted(self.leaderboard.keys()):
            self.table = QTableWidget(len(self.leaderboard[session]),6)
            self.table.verticalHeader().hide()
            self.tabWidget = QWidget()
            self.okBtn = QPushButton('Ok')
            self.okBtn.clicked.connect(self.close)
            self.addTab(self.tabWidget, session)
            self.widgetLayout = QVBoxLayout()
            self.widgetLayout.addWidget(self.table)
            self.widgetLayout.addWidget(self.okBtn)
            self.tabWidget.setLayout(self.widgetLayout)
            self.table.setHorizontalHeaderLabels(['Position', 'Driver', 'Time', 'Laps', 'Best Lap', 'Pitstops'])
            for idx, driverInfo in enumerate(self.leaderboard[session]):
                self.table.setItem(idx,0, QTableWidgetItem(str(idx + 1)))
                self.table.setItem(idx,1, QTableWidgetItem(driverInfo['name']))
                self.table.setItem(idx,2, QTableWidgetItem(formattime(driverInfo['total'], False)))
                self.table.setItem(idx,3, QTableWidgetItem(str(driverInfo['laps'])))
                self.table.setItem(idx,4, QTableWidgetItem(formattime(driverInfo['best'], False)))
                self.table.setItem(idx,5, QTableWidgetItem(str(driverInfo['pits'])))


class RmsDriver(QObject):
    def __init__(self, driverNum):
        super().__init__()
        self.CtrlNum = driverNum
        self.name = 'Driver ' + str(driverNum)
        self.lapcount = 0
        self.bestLapTime = None
        self.lapTime = None
        self.time = None
        self.fuellevel = 15
        self.pitcount = 0
        self.pit = False
        self.buildDriver()
        
    ### Reset Fuellevel after CU off
    
    def buildDriver(self):
        self.nameFont = QFont()
        self.nameFont.setPointSize(20)
        self.nameFont.setBold(True)
         
        self.nameBtn = QPushButton(self.name + '\n' + 'Ctrl: ' + str(self.CtrlNum))
        self.nameBtn.setToolTip('Click to change driver name')
        self.nameBtn.setFont(self.nameFont)
        self.nameBtn.setStyleSheet("QPushButton { border-radius: 10px; color: yellow; background-color: black}")


        self.lapCountLCD = QLCDNumber(3)
        self.lapCountLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.lapCountLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.lapCountLCD.setPalette(lcdPalette)
        self.lapCountLCD.display(self.lapcount)

        self.bestLapLCD = QLCDNumber()
        self.bestLapLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.bestLapLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.bestLapLCD.setPalette(lcdPalette)
        self.bestLapLCD.display(self.bestLapTime)

        self.lapLCD = QLCDNumber()
        self.lapLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.lapLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 255, 0))
        self.lapLCD.setPalette(lcdPalette)
        self.lapLCD.display(self.lapTime)

        self.fuelbar = QProgressBar()
        self.fuelbar.setOrientation(Qt.Horizontal)
        self.fuelbar.setStyleSheet("QProgressBar{ color: white; background-color: black; border: 5px solid black; border-radius: 10px; text-align: center}\
                                    QProgressBar::chunk { background: qlineargradient(x1: 1, y1: 0.5, x2: 0, y2: 0.5, stop: 0 #00AA00, stop: " + str(0.92 - (1 / (self.fuellevel))) + " #22FF22, stop: " + str(0.921 - (1 / (self.fuellevel))) + " #22FF22, stop: " + str(1.001 - (1 / (self.fuellevel))) + " red, stop: 1 #550000); }")
        self.fuelbar.setMinimum(0)
        self.fuelbar.setMaximum(15)
        self.fuelbar.setValue(self.fuellevel)

        self.pitCountLCD = QLCDNumber(2)
        self.pitCountLCD.setStyleSheet("QLCDNumber{ border-radius: 10px; background-color: black}")
        lcdPalette = self.pitCountLCD.palette()
        lcdPalette.setColor(lcdPalette.WindowText, QColor(255, 0, 0))
        self.pitCountLCD.setPalette(lcdPalette)
        self.pitCountLCD.display(self.pitcount)
   
    def getName(self):
        return self.name

    def getNameBtn(self):
        return self.nameBtn
    
    def getLapCountLCD(self):
        return self.lapCountLCD

    def getBestLapLCD(self):
        return self.bestLapLCD
    
    def getLapLCD(self):
        return self.lapLCD

    def getFuelBar(self):
        return self.fuelbar

    def setCtrlNum(self, num):
        self.CtrlNum = num
        self.nameBtn.setText(self.name + '\n' + 'Ctrl: ' + str(self.CtrlNum))

    def getPits(self):
        return self.pitCountLCD

    def newlap(self, timer):
    ### get last round
        #if self.lapcount == self.session:
        #    audio.play("last")
        #    audio.played=True
        audio.played=False
        if self.fuellevel <= 5:
            audio.play("fuellow")
            audio.played=True
                        
        if self.time is not None:
            self.lapTime = timer.timestamp - self.time
            if self.bestLapTime is None or self.lapTime < self.bestLapTime:
                self.bestLapTime = self.lapTime
                if not audio.played:
                    audio.play("beeplow")
                    audio.played=False
            elif not audio.played:
                audio.play("beephigh")
                audio.played=False
            self.lapcount += 1
        self.time = timer.timestamp
        
#~ class FlaskThread(QThread):
    #~ def __init__(self, application):
        #~ QThread.__init__(self)
        #~ self.application = application

    #~ def __del__(self):
        #~ self.wait()

    #~ def run(self):
        #~ self.application.run(port=PORT)
        
#~ def provide_GUI_for(w, qtapp, application):
    
    #~ #webapp = FlaskThread(application)


    #~ return qtapp.exec_()       
class Webpage:
    def __init__(self):
        self.app = Flask(__name__)
        self.position={}
        self.totaltime={}
        self.name={}
        self.laps={}
        self.laptime={}
        self.bestlaptime={}
        self.fuellevel={}
        self.fuellevellights1={}
        self.fuellevellights2={}
        self.pits={}
        for ctrl in range (1,7):
            self.position[ctrl]='#'+str(ctrl)
            self.totaltime[ctrl]='-.--'
            self.name[ctrl]='Driver'+str(ctrl)
            self.laps[ctrl]=0
            self.laptime[ctrl]='-.--'
            self.bestlaptime[ctrl]='-.--'
            self.fuellevel[ctrl]=15
            self.fuellevellights1[ctrl]='⣿⣿⣿⣿⣿'
            self.fuellevellights2[ctrl]='⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿'
            self.pits[ctrl]=0
            

        @self.app.route("/")
        def hello():
            return '''
            <html>
                <head>
                    <title>DriverCockpit</title>
                </head>
                <body>
                    <h1>Hello!</h1>
                </body>
            </html>'''
        @self.app.route('/<int:ctrl>')
        def show_controller(ctrl):
            # show the user profile for that user
            if 1<= ctrl <=6:
                return render_template('index.html', title='Home', ctrl=ctrl, position=self.position[ctrl], totaltime=self.totaltime[ctrl], name=self.name[ctrl], laps=self.laps[ctrl], laptime=self.laptime[ctrl], bestlaptime=self.bestlaptime[ctrl], fuellevel=self.fuellevel[ctrl],  fuellevellights1=self.fuellevellights1[ctrl], fuellevellights2=self.fuellevellights2[ctrl], pits=self.pits[ctrl])
            else:
                return  '''
            <html>
                <head>
                    <title>DriverCockpit</title>
                </head>
                <body>
                    <h1>No Website</h1>
                </body>
            </html>'''
            
        
if __name__ == '__main__':
    audio=Audio()
    
    app = QApplication(sys.argv)
        
    w = Rms()
    w.showMaximized()
    
    web=Webpage()
    webapp_thread=Thread(target=web.app.run, kwargs={'port':5000,'host':'0.0.0.0'})
    webapp_thread.start()
    
    w.run()
        
    app.aboutToQuit.connect(webapp_thread.stop)
    
    sys.exit(app.exec_())

#    sys.exit(provide_GUI_for(w, app, webapp)
#    startGUI(webapp_thread, qtapp_thread)
