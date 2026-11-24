import os
import sys
from datetime import datetime
from runtime_support import prepare_user_data, restart_command

if "--check-system" in sys.argv[1:]:
    from check_system import main as check_main
    try:
        check_main()
    except RuntimeError as error:
        sys.exit(str(error))
    sys.exit(0)
if "--configure-mango" in sys.argv[1:]:
    from configure_mango import main as configure_main
    sys.exit(configure_main())
if "--version" in sys.argv[1:]:
    from pathlib import Path
    resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    print((resource_root / 'VERSION').read_text().strip())
    sys.exit(0)

print("\n!!!!!!!! DO NOT CLOSE THIS WINDOW WITHOUT SAVING !!!!!!!!\n")

LOG_TITLE = "LPHK.log"

# Get platform information
PLATFORMS = [{"search_string": "win32", "name_string": "windows"},
             {"search_string": "linux", "name_string": "linux"},
             {"search_string": "darwin", "name_string": "macintosh"}]
PLATFORM = None
for plat in PLATFORMS:
    if sys.platform.startswith(plat["search_string"]):
        PLATFORM = plat["name_string"]
        break
if PLATFORM is None:
    PLATFORM = "other"

# Test if this is a PyInstaller executable or a .py file
if getattr(sys, 'frozen', False):
    IS_EXE = True
    PROG_FILE = sys.executable
    PROG_PATH = os.path.dirname(PROG_FILE)
    PATH = sys._MEIPASS
else:
    IS_EXE = False
    PROG_FILE = os.path.realpath(__file__)
    PROG_PATH = os.path.dirname(PROG_FILE)
    PATH = PROG_PATH


# Test if there is a user folder specified
def get_first_textfile_line(file_path):
    with open(file_path, "r") as f:
        file_lines = f.readlines()
    first_line = file_lines[0] if file_lines else ""
    return first_line.strip()


USERPATH_FILE = os.path.join(PATH, "USERPATH")
if os.path.exists(USERPATH_FILE):
    IS_PORTABLE = False
    USER_PATH = os.path.expanduser(os.path.expandvars(get_first_textfile_line(USERPATH_FILE)))
    if not USER_PATH:
        raise ValueError("USERPATH must contain a directory path")
    if not os.path.isabs(USER_PATH):
        USER_PATH = os.path.join(PROG_PATH, USER_PATH)
    os.makedirs(USER_PATH, exist_ok=True)
else:
    IS_PORTABLE = True
    USER_PATH = PROG_PATH

if os.environ.get("LPHK_USER_PATH"):
    USER_PATH = os.path.abspath(os.path.expanduser(os.environ["LPHK_USER_PATH"]))
    IS_PORTABLE = False
prepare_user_data(USER_PATH, PATH)

# Get program version
VERSION = get_first_textfile_line(os.path.join(PATH, "VERSION"))

# Setup dual logging/printing
LOG_PATH = os.path.join(USER_PATH, LOG_TITLE)

import logger

logger.start(LOG_PATH)


# Start printing output
def datetime_str():
    now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M:%S")


print("---------------- BEGIN LOG", datetime_str(), "----------------")
print("LPHK - LaunchPad HotKey - A Novation Launchpad Macro Scripting System")
print("Version:", VERSION)
print("Platform:", PLATFORM.capitalize())
print("Is compiled executable:", IS_EXE)
print("Is portable:", IS_PORTABLE)
print("Operating path:", PATH)
print("User path:", USER_PATH)
print("Program file path:", PROG_PATH)
print("Program file:", PROG_FILE)
print("Log file (this file):", LOG_PATH, end="\n\n")

# Try to import launchpad.py
try:
    import launchpad_py as launchpad
except ImportError:
    try:
        import launchpad
    except ImportError:
        sys.exit("[LPHK] Error loading launchpad.py")
print("")

import lp_events, scripts, files, sound, window
import kb
from input_backend import BACKEND
from utils import launchpad_connector

lp = launchpad.Launchpad()

EXIT_ON_WINDOW_CLOSE = True


def init():
    global EXIT_ON_WINDOW_CLOSE
    if len(sys.argv) > 1:
        if ("--debug" in sys.argv) or ("-d" in sys.argv):
            EXIT_ON_WINDOW_CLOSE = False
            print("[LPHK] Debugging mode active! Will not shut down on window close.")
            print("[LPHK] Run shutdown() to manually close the program correctly.")

        elif "--smoke-test" not in sys.argv and '--demo' not in sys.argv:
            print("[LPHK] Invalid argument: " + sys.argv[1] + ". Ignoring...")

    print("Input backend:", BACKEND)
    if BACKEND == "wayland":
        from system_apis.input_wayland import controller
        try:
            print(controller.check())
        except RuntimeError as error:
            print('[input] Macro input is not ready; soundtrack/demo editing remains available:', error)
    files.init(USER_PATH)
    sound.init(USER_PATH)


def shutdown():
    lp_events.stop()
    scripts.to_run = []
    for x in range(9):
        for y in range(9):
            if scripts.threads[x][y] is not None:
                scripts.threads[x][y].kill.set()
    for row in scripts.threads:
        for thread in row:
            if thread is not None and thread.is_alive():
                thread.join(timeout=1)
    sound.shutdown()
    try:
        kb.release_all()
    except Exception as error:
        print("[LPHK] Input cleanup failed:", error)
    if window.lp_connected:
        scripts.unbind_all()
        launchpad_connector.disconnect(lp)
        window.lp_connected = False
    logger.stop()
    if window.restart:
        if IS_EXE:
            os.environ["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        os.execv(sys.executable, restart_command(sys.executable, sys.argv, IS_EXE))
    print("[LPHK] Shutting down...")
    sys.exit(0)


def main():
    init()
    window.init(lp, launchpad, PATH, PROG_PATH, USER_PATH, VERSION, PLATFORM)
    if EXIT_ON_WINDOW_CLOSE:
        shutdown()


main()
