# PinetimeFlasher

![PinetimeFlasher](/PinetimeFlasher.png "PinetimeFlasher")

A GUI app to help flash the PineTime with xpack-openOCD on Windows (but might also work on Linux and Mac), made with Python and PyQT5(for UI).

To run the script you need Python >3.6 and xpack-openOCD installed.

[How to install xpack-openOCD ?](https://xpack.github.io/openocd/install/#manual-install)

Make sure you have PyQT5 installed, it can be installed with
`pip install PyQT5`

It can also be made into an executable using PyInstaller:
```
pip install pyinstaller
pyinstaller -w --onefile PinetimeFlasher.py
```

Note: Pre-made executable available in the [releases](https://github.com/ZephyrLabs/PinetimeFlasher/releases)!!!
