#!/usr/bin/env python3
import hashlib
import platform
import sys
import os
import shutil
import requests
import json
import wget
from pathlib import Path
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pickle
from typing import List

__version__ = "0.4.0"


def add_openocd_to_system_path():
    """
    Adds the directory 'openocd' to the path, relative to the app
    """
    openocd_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'openocd', 'bin')
    os.environ["PATH"] = os.environ["PATH"] + os.pathsep + openocd_path


def progress_parser(output):
    """
    Returns percentage progress value in response to key phrases from OpenOCD
    """
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


def read_config_file(status_notice: QLabel) -> (str, str):
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


class ptflasher(QMainWindow):
    """
    Main Program Class and UI
    """
    openocd_log = ""

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
        self.progress.setEnabled(False)

        self.flashbtn = QPushButton("Start flashing")
        self.searchbtn = QPushButton("Search for file")
        self.confbtn = QPushButton("Configure flashing options...")
        self.infobtn = QPushButton("More info")
        self.status = QLabel("")

        self.flashbtn.clicked.connect(self.startflash)
        self.searchbtn.clicked.connect(self.filesearch)
        self.confbtn.clicked.connect(self.confButton)
        self.filedir.textChanged.connect(self.update_control_statuses)
        self.infobtn.clicked.connect(self.info_button)
        self.flashbtn.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.info)
        layout.addWidget(self.filedir)
        layout.addWidget(self.progress)
        layout.addWidget(self.searchbtn)
        layout.addWidget(self.flashbtn)
        layout.addWidget(self.confbtn)
        layout.addWidget(self.infobtn)
        layout.addWidget(self.status)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

    def update_control_statuses(self):
        """
        Enable or disable buttons and update status messages as needed
        """
        def enable_buttons(enable: bool, reason: str):
            self.flashbtn.setEnabled(enable)
            self.progress.setEnabled(enable)
            self.status.setText(reason)

        firmware = self.filedir.toPlainText()

        if platform.system() == "Windows":
            if firmware[0:8] == "file:///":
                firmware = firmware[8:]
                self.filedir.setPlainText(firmware)
        else:
            if firmware[0:7] == "file://":
                firmware = firmware[7:]
                self.filedir.setPlainText(firmware)

        if not firmware:
            enable_buttons(False, "Set location of file to be flashed!")
        elif not os.path.exists(firmware):
            enable_buttons(False, "File does not exist!")
        elif not os.path.splitext(firmware)[-1] in (".bin", ".hex"):
            enable_buttons(False, "Not a supported file type (.bin, .hex)")
        elif not shutil.which("openocd"):
            enable_buttons(False, "OpenOCD not found in system path!")
        else:
            enable_buttons(True, "Ready to flash!")

    def startflash(self):
        """
        Start the actual flashing process
        """
        if self.p:  # don't continue if process already running
            return

        self.openocd_log = ""
        self.progress.setValue(0)

        source = self.filedir.toPlainText()
        address, interface = read_config_file(self.status)

        self.searchbtn.setEnabled(False)
        self.flashbtn.setEnabled(False)
        self.confbtn.setEnabled(False)

        self.progress.setValue(10)
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
        """
        Handle flash completion
        """
        if self.p.exitCode() == 0:
            self.status.setText("Success!")
        else:
            self.status.setText("Something probably went wrong :(")
            self.progress.setValue(0)
            dlg = LogViewDialog(self.openocd_log)
            dlg.exec()

        self.p = None

        self.searchbtn.setEnabled(True)
        self.flashbtn.setEnabled(True)
        self.confbtn.setEnabled(True)

    def handle_stderr(self):
        """
        Capture output during flashing and process it
        """
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.openocd_log = self.openocd_log + stderr
        progress = progress_parser(stderr)
        if progress:
            self.progress.setValue(progress)
            if progress == 70:
                self.status.setText("Verifying...")

    def filesearch(self):
        filedialog = QFileDialog()
        datafile = filedialog.getOpenFileName(
            caption="Select firmware file to flash...",
            directory=str(Path.home() / "Downloads"),
            filter="PineTime Firmware (*.bin *.hex)",
        )

        if datafile[0]:
            self.filedir.setPlainText(datafile[0])
            self.progress.setValue(0)

    def confButton(self, s):
        dlg = ConfDialog()
        dlg.exec()
        self.update_control_statuses()

    def info_button(self):
        dlg = InfoDialog()
        dlg.exec()


class ConfDialog(QDialog):
    """
    Configuration class and UI
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.firmware_types = [
            {"name": "mcuboot-app", "address": "0x00008000"},
            {"name": "bootloader", "address": "0x00000000"}
        ]

        self.setWindowTitle("Flash Configuration")
        self.resize(300, 220)

        self.addrinfo = QLabel("Firmware type (used to determine address):")
        self.addrbox = QComboBox()
        for firmware in self.firmware_types:
            self.addrbox.addItem(firmware["name"], firmware["address"])

        self.ifaceinfo = QLabel("Enter the interface (default: stlink.cfg)")
        self.ifacebox = QPlainTextEdit()

        self.savebtn = QPushButton("Save configuration")
        self.openocd_btn = QPushButton("Download OpenOCD")
        self.status = QLabel("")

        conflayout = QVBoxLayout()
        conflayout.addWidget(self.addrinfo)
        conflayout.addWidget(self.addrbox)
        conflayout.addWidget(self.ifaceinfo)
        conflayout.addWidget(self.ifacebox)
        conflayout.addWidget(self.savebtn)
        conflayout.addWidget(self.openocd_btn)
        conflayout.addWidget(self.status)
        self.setLayout(conflayout)

        address, interface = read_config_file(self.status)
        self.addrbox.setCurrentIndex(self.get_firmware_index(address))
        self.ifacebox.setPlainText(interface)

        self.savebtn.clicked.connect(self.saveconf)
        self.openocd_btn.clicked.connect(self.setup_openocd)

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

    def setup_openocd(self):
        """
        Download and unpack OpenOCD for the current platform, then add it to the system path.
        """
        self.status.setText("Finding latest OpenOCD release...")
        self.status.repaint()

        base_url = "https://api.github.com/repos"
        response = requests.get(f"{base_url}/xpack-dev-tools/openocd-xpack/releases/latest")

        details = response.content.decode('utf-8')
        content = json.loads(details)

        archive_file, hash_file = self.get_github_assets(content["assets"])
        if not archive_file or not hash_file:
            return

        if not self.compare_hashes(archive_file, hash_file):
            self.status.setText("Hashes do not match - corrupted download!")
            return

        self.unpack_archive(archive_file)
        self.status.setText("OpenOCD successfully downloaded.")
        os.remove(archive_file)
        os.remove(hash_file)

    def compare_hashes(self, archive_file, hash_file):
        self.status.setText("Computing hashes OpenOCD...")
        self.status.repaint()
        with open(archive_file, "rb") as fd:
            hasher = hashlib.sha256()
            hasher.update(fd.read())
            computed_hash = hasher.hexdigest()
        with open(hash_file, "r") as fd:
            provided_hash = fd.read().split(" ")[0]   # format: "<hash> <filename>"
        return computed_hash == provided_hash

    def unpack_archive(self, archive):
        """
        Unpack the archive and shift files so that the files can always be found
        under 'openocd/' (i.e. without a version number, which is how they are
        currently packed).
        """
        self.status.setText("Unpacking OpenOCD...")
        self.status.repaint()
        tmpdir_name = "openocd_tmp"
        shutil.unpack_archive(archive, extract_dir=tmpdir_name)
        tmpdir_contents = os.listdir(tmpdir_name)

        if len(tmpdir_contents) == 1:
            shutil.move(os.path.join(tmpdir_name, tmpdir_contents[0]), "openocd")
            os.rmdir(tmpdir_name)
        else:
            shutil.move(tmpdir_name, "openocd")

    def get_github_assets(self, assets: List[str]):
        """
        Determine which package needs to be downloaded for OS/architecture
        and attempt to download it.
        """
        plat = {
            "Windows": "win32",
            "Linux": "linux",
            "MacOS": "darwin",
        }.get(platform.system(), "")
        arch = {
            "AMD64": "x64",
            "x86_64": "x64",
            "i386": "ia32"
        }.get(platform.machine(), "")

        if not plat or not arch:
            self.status.setText("Unable to determine appropriate OpenOCD download.")
            return

        download_urls = [f["browser_download_url"] for f in assets if plat in f["name"] and arch in f["name"]]
        filenames = [f["name"] for f in assets if plat in f["name"] and arch in f["name"]]
        assert len(download_urls) == 2

        self.status.setText("Downloading OpenOCD from GitHub...")
        self.status.repaint()
        if not os.path.exists(filenames[0]) and not os.path.exists(filenames[1]):
            wget.download(download_urls[0])
            wget.download(download_urls[1])

        filenames.sort()
        return filenames


class InfoDialog(QDialog):
    """
    Info screen class and UI
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("About PineTime Flasher v{}".format(__version__))
        self.resize(300, 200)

        vbox = QVBoxLayout()
        textView = QLabel("""PineTime Flasher is a simple GUI software written in Python,
that uses the xpack-openOCD tool for flashing the PineTime
with SWD debuggers such as the ST-Link and J-Link.

When first using the software, it is recommended that you
setup the configuration by choosing the appropriate firmware
type and flashing interface.

The possible firmware types are:
* mcuboot-app
* bootloader

For the interface, the options available are dependent on the
(*.cfg) provided by the xpack-openOCD itself. For example:
stlink.cfg or jlink.cfg""")

        vbox.addWidget(textView)
        self.setLayout(vbox)

        self.setWindowModality(Qt.ApplicationModal)


class LogViewDialog(QDialog):
    """
    Log view class and UI
    """

    def __init__(self, openocd_log, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("OpenOCD Flash Output")
        self.resize(650, 300)

        vbox = QVBoxLayout()
        infoText = QLabel("The flash operation encounter an error. Read the below log to find out why.")
        logView = QPlainTextEdit(openocd_log)

        vbox.addWidget(infoText)
        vbox.addWidget(logView)
        self.setLayout(vbox)

        self.setWindowModality(Qt.ApplicationModal)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    appDir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    path_to_icon = os.path.abspath(os.path.join(appDir, "PinetimeFlasher.ico"))

    app_icon = QIcon(path_to_icon)
    app.setWindowIcon(app_icon)

    qp = QPalette()
    qp.setColor(QPalette.ButtonText, Qt.white)
    qp.setColor(QPalette.Window, Qt.gray)
    qp.setColor(QPalette.Button, Qt.gray)
    app.setPalette(qp)

    add_openocd_to_system_path()

    win = ptflasher()
    win.show()
    sys.exit(app.exec_())
