import os
import sys

def getAppDirectory():
    if getattr(sys, "frozen", False):
        # Nuitka & PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # Py
        return os.path.dirname(os.path.abspath(sys.argv[0]))
