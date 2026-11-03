"""Keep the official client available in this container without guessing login."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading


def running(executable):
    for path in Path('/proc').glob('[0-9]*'):
        try:
            if path.stat().st_uid==os.getuid() and (path/'exe').resolve()==executable:return True
        except OSError:continue
    return False


def main():
    executable=Path(sys.argv[1]).resolve()
    if not executable.is_file():raise SystemExit('Official client executable is missing')
    stop=threading.Event();child=None
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:stop.set())
    try:
        while not stop.is_set():
            if not running(executable):child=subprocess.Popen([str(executable)])
            stop.wait(5)
    finally:
        if child is not None and child.poll() is None:child.terminate()


if __name__=='__main__':main()
