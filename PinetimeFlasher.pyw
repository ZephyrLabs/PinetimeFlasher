#!/usr/bin/env python3

import sys
import os
import shutil
import subprocess
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pickle


# Returns percentage progress value in response to key phrases from OpenOCD
def progress_parser(output):
    if "** Programming Started **" in output:
        return 30
    elif "** Programming Finished **" in output:
        return 50
    elif "** Verify Started **" in output:
        return 70
    elif "** Verified OK **" in output:
        return 90
    elif "** Resetting Target **" in output:
        return 100
    else:
        return None


# Source: https://stackoverflow.com/a/48706260/4914192
def get_download_path():
    """Returns the default downloads path for linux or windows"""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'downloads')


# Main Program Class and UI
class ptflasher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.p = None  # Default empty value.

        self.setWindowTitle('PineTime Flasher')
        self.resize(300, 200)

        self.info = QLabel('Enter The Path Of The File To Be Flashed')

        self.filedir = QTextEdit()
        filedir = self.filedir.toPlainText()

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        self.flashbtn = QPushButton('Start Flashing')
        self.searchbtn = QPushButton('Search for File')
        self.confbtn = QPushButton('Configure flashing options...')
        self.flashbtn.clicked.connect(self.startflash)
        self.searchbtn.clicked.connect(self.filesearch)
        self.confbtn.clicked.connect(self.confButton)

        self.status = QLabel('Ready.')

        self.filedialog = QFileDialog()

        layout = QVBoxLayout()

        layout.addWidget(self.info)
        layout.addWidget(self.filedir)
        layout.addWidget(self.progress)
        layout.addWidget(self.searchbtn)
        layout.addWidget(self.flashbtn)
        layout.addWidget(self.confbtn)
        layout.addWidget(self.status)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

    def startflash(self):
        if self.p is None:  # If process not already running
            global progress

            self.progress.setValue(0)

            source = self.filedir.toPlainText()

            try:
                if source[0:8] == "file:///":
                    source = source[8:]
            except:
                pass

            try:
                with open('conf.dat', 'rb+') as f:
                    data = pickle.load(f)
                    default_addr = data[0]
                    default_iface = data[1]
            except:
                default_addr = "0x00008000"
                default_iface = "stlink.cfg"

            self.progress.setValue(10)

            if os.path.exists(source):
                if shutil.which('openocd') is not None:
                    self.status.setText('Flashing...')
                    self.status.repaint()

                    command = ('openocd -f "interface/{}" '
                               '-f "target/nrf52.cfg" -c "init" '
                               '-c "program {} {} verify reset exit"').format(
                        default_iface, source, default_addr)

                    self.p = QProcess()  # Keep a reference while it's running
                    self.p.finished.connect(self.flash_finished)  # Clean up
                    self.p.readyReadStandardError.connect(self.handle_stderr)
                    self.p.start(command)

                else:
                    self.progress.setValue(0)
                    self.status.setText("OpenOCD not found in system path!")

            elif source == '':
                self.status.setText("Set location of file to be flashed!")
                self.progress.setValue(0)

            else:
                self.status.setText("File does not exist!")
                self.progress.setValue(0)

    def flash_finished(self, ):
        if (self.p.exitCode() == 0):
            self.status.setText('Success!')
        else:
            self.status.setText('Something probably went wrong :(')
            self.progress.setValue(0)
        self.p = None

    def handle_stderr(self):
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        progress = progress_parser(stderr)
        if progress:
            self.progress.setValue(progress)
            if progress == 70:
                self.status.setText("Verifying...")

    def filesearch(self):
        global progress, filedir

        downloadsFolder = get_download_path()

        datafile = self.filedialog.getOpenFileName(caption="Select firmware file to flash...",
                                                   directory=downloadsFolder,
                                                   filter="PineTime Firmware (*.bin *.hex)")

        if datafile[0] != "":
            self.filedir.setText(datafile[0])
            self.progress.setValue(0)

    def confButton(self, s):
        dlg = ConfDialog()
        dlg.exec()


# Configuration class and UI
class ConfDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        default_addr = "0x00008000"
        default_iface = "stlink.cfg"

        self.setWindowTitle('Flash Configuration')
        self.resize(300, 200)

        self.addrinfo = QLabel('Enter the Flash Address (default 0x00008000)')
        self.ifaceinfo = QLabel('Enter the Interface (default stlink)')

        self.addrbox = QTextEdit()
        self.ifacebox = QTextEdit()

        self.savebtn = QPushButton('Save configuration')
        self.infobtn = QPushButton('More info')

        self.status = QLabel('')

        conflayout = QVBoxLayout()
        confbuttonrow = QHBoxLayout()

        conflayout.addWidget(self.addrinfo)
        conflayout.addWidget(self.addrbox)
        conflayout.addWidget(self.ifaceinfo)
        conflayout.addWidget(self.ifacebox)

        confbuttonrow.addWidget(self.savebtn)
        confbuttonrow.addWidget(self.infobtn)

        conflayout.addLayout(confbuttonrow)

        conflayout.addWidget(self.status)

        self.setLayout(conflayout)

        try:
            with open('conf.dat', 'rb+') as f:
                data = pickle.load(f)
                default_addr = data[0]
                default_iface = data[1]
                self.addrbox.setText(default_addr)
                self.ifacebox.setText(default_iface)

        except:
            self.addrbox.setText(default_addr)
            self.ifacebox.setText(default_iface)

        self.infobtn.clicked.connect(self.infoButton)
        self.savebtn.clicked.connect(self.saveconf)

        self.setWindowModality(Qt.ApplicationModal)

    def saveconf(self, s):
        global addrbox, ifacebox, status
        addr = self.addrbox.toPlainText()
        iface = self.ifacebox.toPlainText()

        if addr == '' or iface == '':
            if addr == '':
                addr = '0x00008000'
            if iface == '':
                iface = 'stlink.cfg'

        if int(addr, 0) <= 479232 and int(addr, 0) >= 0:
            with open('conf.dat', 'wb+') as f:
                pickle.dump((addr, iface), f)
            self.status.setText('Configuration Saved.')

        else:
            self.status.setText('Flash address is out of range!')

    def infoButton(self, s):
        dlg = InfoDialog()
        dlg.exec()


# Info screen class and UI
class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        default_addr = "0x00008000"
        default_iface = "stlink.cfg"

        self.setWindowTitle('About PineTime Flasher')
        self.resize(450, 200)

        vbox = QVBoxLayout()
        text = '''
        PineTime Flasher is a simple GUI software written in Python,
        using the xpack-openOCD tool for flashing the PineTime with
        either ST-Link, J-Link etc.

        When first using the software, it is recommended that you
        setup the configuration by choosing the appropriate flashing
        address and flashing interface.

        The possible addresses are:
        0x00 (for the bootloader)
        0x00008000 (for mcuboot-app)

        For the interface, the options available are dependent on the
        (*.cfg) provided by the xpack-openOCD itself. For example:
        stlink.cfg or jlink.cfg'''

        textView = QPlainTextEdit()
        textView.setPlainText(text)
        textView.setReadOnly(True)

        vbox.addWidget(textView)
        self.setLayout(vbox)

        self.setWindowModality(Qt.ApplicationModal)


# Program entrypoint
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    appDir = getattr(sys, '_MEIPASS', os.path.abspath(
        os.path.dirname(__file__)))
    path_to_icon = os.path.abspath(os.path.join(appDir, 'PinetimeFlasher.ico'))

    app_icon = QIcon(path_to_icon)
    app.setWindowIcon(app_icon)

    qp = QPalette()
    qp.setColor(QPalette.ButtonText, Qt.white)
    qp.setColor(QPalette.Window, Qt.gray)
    qp.setColor(QPalette.Button, Qt.gray)
    app.setPalette(qp)

    win = ptflasher()
    win.show()
    sys.exit(app.exec_())
