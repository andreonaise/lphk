"""Find bundled helper programs, falling back to installed tools for source runs."""
from pathlib import Path
import os
import shutil
import sys


def locate(name):
    if getattr(sys, 'frozen', False):
        candidate = Path(sys._MEIPASS) / 'tools' / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def command(name):
    return locate(name) or name


def external_environment(environment, executable):
    environment = environment.copy()
    if getattr(sys, 'frozen', False):
        tools = (Path(sys._MEIPASS) / 'tools').resolve()
        if Path(executable).resolve().parent != tools:
            original = environment.get('LD_LIBRARY_PATH_ORIG')
            if original is not None:
                environment['LD_LIBRARY_PATH'] = original
            else:
                environment.pop('LD_LIBRARY_PATH', None)
    return environment
