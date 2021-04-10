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


# class for scrollable label
class ScrollLabel(QScrollArea):
    # constructor
    def __init__(self, *args, **kwargs):
        QScrollArea.__init__(self, *args, **kwargs)

        # making widget resizable
        self.setWidgetResizable(True)

        # making QWidget object
        content = QWidget(self)
        self.setWidget(content)

        # vertical box layout
        lay = QVBoxLayout(content)

        # creating label
        self.label = QLabel(content)

        # setting alignment to the text
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)

    # the setText method
    def setText(self, text):
        # setting text to the label
        self.label.setText(text)


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
        if self.p is None:  # No process running.
            global progress

            self.progress.setValue(0)

            source = self.filedir.toPlainText()

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
                    # self.p.readyReadStandardOutput.connect(self.handle_stdout)
                    self.p.readyReadStandardError.connect(self.handle_stderr)
                    # self.p.stateChanged.connect(self.handle_state)
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
        # print(stderr, end='')

    # def handle_stdout(self):
    #     data = self.p.readAllStandardOutput()
    #     stdout = bytes(data).decode("utf8")

    def filesearch(self):
        global progress, filedir

        datafile = self.filedialog.getOpenFileName(
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
        self.resize(400, 200)

        text = '''
            PineTime Flasher is a simple GUI software written in Python,\n
            using the xpack-openOCD tool for flashing the PineTime with\n
            either ST-Link, J-Link etc.\n\n
            When first using the software, it is recommended that you\n
            setup the configuration by choosing the appropriate flashing\n
            address and flashing interface\n\n
            The possible addresses are:\n
            0x00 (for the bootloader)\n
            0x00008000 (for mcuboot-app)\n\n
            For the interface, the options available are dependent on the\n
            (*.cfg) provided by the xpack-openOCD itself. For example:\n
            stlink.cfg or jlink.cfg'''

        self.label = ScrollLabel(self)

        # setting text to the label
        self.label.setText(text)

        # setting geometry
        self.label.setGeometry(0, 0, 500, 200)
        self.setWindowModality(Qt.ApplicationModal)


# Program entrypoint
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    qp = QPalette()
    qp.setColor(QPalette.ButtonText, Qt.white)
    qp.setColor(QPalette.Window, Qt.gray)
    qp.setColor(QPalette.Button, Qt.gray)
    app.setPalette(qp)

    win = ptflasher()
    win.show()
    sys.exit(app.exec_())
