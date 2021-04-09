import sys
import os
import shutil
import subprocess
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pickle


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


class ptflasher(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('PineTime Flasher')
        self.resize(300, 300)

        self.info = QLabel('Enter The Path Of The File To Be Flashed')

        self.filedir = QTextEdit()

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        self.flashbtn = QPushButton('Start Flashing')
        self.searchbtn = QPushButton('Search for File')
        self.confbtn = QPushButton('Configure flashing options...')

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

        self.setLayout(layout)
        self.setGeometry(300, 300, 300, 200)

        def startflash():
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

                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    ret = subprocess.call(command, startupinfo=si)

                    if ret == 0:
                        self.status.setText('Success!')
                    else:
                        self.status.setText('Something probably went wrong :(')

                    self.progress.setValue(100)
                else:
                    self.progress.setValue(0)
                    self.status.setText("OpenOCD not found in system path!")

            elif source == '':
                self.status.setText("Set location of file to be flashed!")
                self.progress.setValue(0)

            else:
                self.status.setText("File does not exist!")
                self.progress.setValue(0)

        def filesearch():
            global progress, filedir

            datafile = self.filedialog.getOpenFileName(
                filter="PineTime Firmware (*.bin *.hex)")

            if datafile[0] != "":
                self.filedir.setText(datafile[0])
                self.progress.setValue(0)

        def confdialog():
            d = QDialog()
            d.setWindowTitle('Flash Configuration')
            d.resize(300, 200)

            d.addrinfo = QLabel('Enter the Flash Address (default 0x00008000)')

            d.ifaceinfo = QLabel('Enter the Interface (default stlink)')

            d.addrbox = QTextEdit()
            d.ifacebox = QTextEdit()

            default_addr = "0x00008000"
            default_iface = "stlink.cfg"

            d.savebtn = QPushButton('Save configuration')
            d.infobtn = QPushButton('More info')

            d.status = QLabel('')

            conflayout = QVBoxLayout()
            confbuttonrow = QHBoxLayout()

            conflayout.addWidget(d.addrinfo)
            conflayout.addWidget(d.addrbox)
            conflayout.addWidget(d.ifaceinfo)
            conflayout.addWidget(d.ifacebox)

            confbuttonrow.addWidget(d.savebtn)
            confbuttonrow.addWidget(d.infobtn)

            conflayout.addLayout(confbuttonrow)

            conflayout.addWidget(d.status)

            d.setLayout(conflayout)

            try:
                with open('conf.dat', 'rb+') as f:
                    data = pickle.load(f)
                    default_addr = data[0]
                    default_iface = data[1]
                    d.addrbox.setText(default_addr)
                    d.ifacebox.setText(default_iface)

            except:
                d.addrbox.setText(default_addr)
                d.ifacebox.setText(default_iface)

            def saveconf():
                global addrbox, ifacebox, status
                addr = d.addrbox.toPlainText()
                iface = d.ifacebox.toPlainText()

                if addr == '' or iface == '':
                    if addr == '':
                        addr = '0x00008000'
                    if iface == '':
                        iface = 'stlink.cfg'

                if int(addr, 0) <= 479232 and int(addr, 0) >= 0:
                    with open('conf.dat', 'wb+') as f:
                        pickle.dump((addr, iface), f)
                    d.status.setText('Configuration Saved.')

                else:
                    d.status.setText('Flash address is out of range!')

            d.infobtn.clicked.connect(infodialog)
            d.savebtn.clicked.connect(saveconf)

            d.setWindowModality(Qt.ApplicationModal)
            d.exec_()

        def infodialog():
            d = QDialog()
            d.setWindowTitle('About PineTime Flasher')
            d.resize(400, 200)

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

            d.label = ScrollLabel(d)

            # setting text to the label
            d.label.setText(text)

            # setting geometry
            d.label.setGeometry(0, 0, 500, 200)

            d.setWindowModality(Qt.ApplicationModal)
            d.exec_()

        filedir = self.filedir.toPlainText()

        self.flashbtn.clicked.connect(startflash)
        self.searchbtn.clicked.connect(filesearch)
        self.confbtn.clicked.connect(confdialog)


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
