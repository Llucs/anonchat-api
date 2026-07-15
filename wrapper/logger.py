from datetime import datetime
from threading import Lock
from time import time


class Log:
    colours = {
        'SUCCESS': '\033[92m',
        'ERROR': '\033[91m',
        'INFO': '\033[97m',
    }

    lock = Lock()

    @staticmethod
    def _log(level, prefix, message):
        timestamp = datetime.fromtimestamp(time()).strftime("%H:%M:%S")
        reset = '\033[0m'
        grey = '\033[90m'
        magenta = '\033[95m'
        log_message = (
            f"{grey}[{magenta}{timestamp}{reset}{grey}]{reset} "
            f"{prefix} {message}"
        )
        with Log.lock:
            print(log_message)

    @staticmethod
    def Success(message, prefix="[+]", color=None):
        Log._log("SUCCESS", f"{Log.colours['SUCCESS']}{prefix}\033[0m", message)

    @staticmethod
    def Error(message, prefix="[!]", color=None):
        Log._log("ERROR", f"{Log.colours['ERROR']}{prefix}\033[0m", message)

    @staticmethod
    def Info(message, prefix="[!]", color=None):
        Log._log("INFO", f"{Log.colours['INFO']}{prefix}\033[0m", message)
