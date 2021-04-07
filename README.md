# PinetimeFlasher
GUI based app to help flash the pinetime with xpack-openOCD on windows, made with python and PyQT(for UI)

to run the script you need Python >3.6 and xpack-openOCD installed

[how to install xpack-openOCD ?](https://xpack.github.io/openocd/install/#manual-install)

make sure you have PyQT5 installed, it can be installed with
`pip install PyQT5`

it can also be made into an executable using pyinstaller:
```
pip install pyinstaller
pyinstaller -w --onefile PinetimeFlasher.py
```

note: pre-made Executable available in the releases!!!