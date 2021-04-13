#!/usr/bin/env python3

import sys
import os
import shutil
from pathlib import Path
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


def read_config_file(status_notice):
    """
    Return the (address, interface) as read from the config file.
    Returns default values for both if there are any file access errors.
    """
    try:
        with open("conf.dat", "rb+") as f:
            data = pickle.load(f)
            address = data[0]
            interface = data[1]
        return address, interface
    except OSError:
        status_notice.setText("Unable to read config file - using default values!")

    return "0x00008000", "stlink.cfg"


# Main Program Class and UI
class ptflasher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.p = None  # Default empty value.

        self.setWindowTitle("PineTime Flasher")
        self.resize(300, 200)

        self.info = QLabel("Enter the path of the file to be flashed")

        self.filedir = QPlainTextEdit()

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        self.flashbtn = QPushButton("Start flashing")
        self.searchbtn = QPushButton("Search for File")
        self.confbtn = QPushButton("Configure flashing options...")
        self.flashbtn.clicked.connect(self.startflash)
        self.searchbtn.clicked.connect(self.filesearch)
        self.confbtn.clicked.connect(self.confButton)

        self.status = QLabel("Ready.")

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
        if self.p:  # if process is already running
            return

        self.progress.setValue(0)

        source = self.filedir.toPlainText()
        address, interface = read_config_file(self.status)

        self.progress.setValue(10)

        if source == "":
            self.status.setText("Set location of file to be flashed!")
            self.progress.setValue(0)
            return

        if not os.path.exists(source):
            self.status.setText("File does not exist!")
            self.progress.setValue(0)
            return

        if not shutil.which("openocd"):
            self.status.setText("OpenOCD not found in system path!")
            self.progress.setValue(0)
            return

        self.status.setText("Flashing...")
        self.status.repaint()

        command = (
            'openocd -f "interface/{}" '
            '-f "target/nrf52.cfg" -c "init" '
            '-c "program {} {} verify reset exit"'
        ).format(interface, source, address)

        self.p = QProcess()  # Keep a reference while it's running
        self.p.finished.connect(self.flash_finished)  # Clean up
        self.p.readyReadStandardError.connect(self.handle_stderr)
        self.p.start(command)

    def flash_finished(self):
        if self.p.exitCode() == 0:
            self.status.setText("Success!")
        else:
            self.status.setText("Something probably went wrong :(")
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
        datafile = self.filedialog.getOpenFileName(
            caption="Select firmware file to flash...",
            directory=str(Path.home() / "Downloads"),
            filter="PineTime Firmware (*.bin *.hex)",
        )

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

        self.firmware_types = [
            {"name": "mcuboot-app", "address": "0x00008000"},
            {"name": "bootloader", "address": "0x00000000"}
        ]

        self.setWindowTitle("Flash Configuration")
        self.resize(300, 200)

        self.addrinfo = QLabel("Firmware type (used to determine address):")
        self.ifaceinfo = QLabel("Enter the interface (default: stlink.cfg)")

        self.addrbox = QComboBox()
        self.ifacebox = QPlainTextEdit()

        self.savebtn = QPushButton("Save configuration")
        self.infobtn = QPushButton("More info")

        self.status = QLabel("")

        conflayout = QVBoxLayout()
        confbuttonrow = QHBoxLayout()

        for firmware in self.firmware_types:
            self.addrbox.addItem(firmware["name"], firmware["address"])

        conflayout.addWidget(self.addrinfo)
        conflayout.addWidget(self.addrbox)
        conflayout.addWidget(self.ifaceinfo)
        conflayout.addWidget(self.ifacebox)

        confbuttonrow.addWidget(self.savebtn)
        confbuttonrow.addWidget(self.infobtn)

        conflayout.addLayout(confbuttonrow)

        conflayout.addWidget(self.status)

        self.setLayout(conflayout)

        address, interface = read_config_file(self.status)
        self.addrbox.setCurrentIndex(self.get_firmware_index(address))
        self.ifacebox.setPlainText(interface)

        self.infobtn.clicked.connect(self.infoButton)
        self.savebtn.clicked.connect(self.saveconf)

        self.setWindowModality(Qt.ApplicationModal)

    def get_firmware_index(self, address: str):
        for i, firmware in enumerate(self.firmware_types):
            if firmware["address"] == address:
                return i
        return 0

    def saveconf(self, s):
        addr = self.addrbox.currentData()
        iface = self.ifacebox.toPlainText() or "stlink.cfg"

        try:
            with open("conf.dat", "wb+") as f:
                pickle.dump((addr, iface), f)
            self.status.setText("Configuration Saved.")
        except OSError:
            self.status.setText("Unable to write configuration file!")

    def infoButton(self, s):
        dlg = InfoDialog()
        dlg.exec()


# Info screen class and UI
class InfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("About PineTime Flasher")
        self.resize(450, 200)

        vbox = QVBoxLayout()
        text = """
        PineTime Flasher is a simple GUI software written in Python,
        that uses the xpack-openOCD tool for flashing the PineTime
        with ST-Link, J-Link etc.

        When first using the software, it is recommended that you
        setup the configuration by choosing the appropriate firmware
        type and flashing interface.

        The possible firmware types are:
        * mcuboot-app
        * bootloader

        For the interface, the options available are dependent on the
        (*.cfg) provided by the xpack-openOCD itself. For example:
        stlink.cfg or jlink.cfg"""

        textView = QPlainTextEdit()
        textView.setPlainText(text)
        textView.setReadOnly(True)

        vbox.addWidget(textView)
        self.setLayout(vbox)

        self.setWindowModality(Qt.ApplicationModal)


# Program entrypoint
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    appDir = getattr(sys, "_MEIPASS",
                     os.path.abspath(os.path.dirname(__file__)))
    path_to_icon = os.path.abspath(os.path.join(appDir, "PinetimeFlasher.ico"))

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
