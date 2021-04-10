# PinetimeFlasher
[![Windows PyInstaller Builds](https://github.com/pfeerick/PinetimeFlasher/actions/workflows/pyinstaller-windows.yml/badge.svg?branch=dev)](https://github.com/pfeerick/PinetimeFlasher/actions/workflows/pyinstaller-windows.yml)

![PinetimeFlasher](/PinetimeFlasher.png "PinetimeFlasher")

A GUI app to help flash the PineTime with xpack-openOCD on Windows (but might also work on Linux and Mac), made with Python and PyQT5(for UI).

To run the script you need Python >3.6 and xpack-openOCD installed.

[How to install xpack-openOCD ?](https://xpack.github.io/openocd/install/#manual-install)

Make sure you have PyQT5 installed, it can be installed with
`pip install PyQT5`

It can also be made into an executable using PyInstaller:
```
pip install pyinstaller
pyinstaller --onefile --icon PinetimeFlasher.ico --add-data PinetimeFlasher.ico;. PinetimeFlasher.pyw
```

Note: Pre-made executable available in the [releases](releases) when a new version is published, as well as [automatic builds by Github Actions](actions/workflows/pyinstaller-windows.yml).
