"""Supervise only this container's setup worker; preserve send and pause state."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import urllib.request


def stale(health,now):
    if health.get('worker_busy'):
        return now-health.get('last_poll_started',now)>420
    return now-health.get('last_poll_finished',now)>90


def main():
    stop=threading.Event()
    for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:stop.set())
    base=Path(__file__).resolve().parents[1];runtime=Path(os.environ['BAGUETTE_RUNTIME'])
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    child=None;failures=0
    try:
        while not stop.is_set():
            if child is None or child.poll() is not None:
                child=subprocess.Popen([sys.executable,str(base/'app/local_setup.py')],start_new_session=True)
                failures=0
            state='starting'
            try:
                with op.open('http://127.0.0.1:8766/api/health',timeout=4) as r:h=json.load(r)
                if h.get('pid')!=child.pid:raise RuntimeError('Unexpected controller owner')
                failures=0;state='healthy'
                if stale(h,time.time()):
                    child.terminate()
                    try:child.wait(timeout=8)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    state='restarted_stalled_worker'
            except Exception:
                failures+=1
                if failures>=3 and child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=8)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    state='restarted_unresponsive_worker'
            path=runtime/'local-watchdog.json';tmp=path.with_suffix('.tmp')
            tmp.write_text(json.dumps({'checked_at':time.time(),'state':state,'worker_pid':child.pid}));tmp.replace(path)
            stop.wait(30)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait()


if __name__=='__main__':main()
