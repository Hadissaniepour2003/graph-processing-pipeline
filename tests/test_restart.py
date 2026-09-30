"""Persistence across an actual server-process restart, using the public API."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

@contextmanager
def server(port, directory):
    env={**os.environ,'GRAPHLAB_DATA_DIR':str(directory)}
    process=subprocess.Popen([sys.executable,'run_lab.py','--port',str(port),'--no-browser'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(150):
            if process.poll() is not None:raise AssertionError('Server startup failed.')
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise AssertionError('Server startup timed out.')
        yield url
    finally:
        process.terminate();process.wait(timeout=10)


def test_history_survives_a_real_server_restart(tmp_path):
    with socket.socket() as handle:
        handle.bind(('127.0.0.1',0));port=handle.getsockname()[1]
    with server(port,tmp_path) as url:
        body=json.dumps({'graph':{'edges':[{'source':'A','target':'B','weight':2}]}}).encode()
        request=urllib.request.Request(url+'/api/analyze',data=body,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=10) as response:analysis=json.load(response)
    # Use a new free port: Windows may retain the previous socket briefly after exit.
    with socket.socket() as handle:
        handle.bind(('127.0.0.1',0));new_port=handle.getsockname()[1]
    with server(new_port,tmp_path) as url:
        with urllib.request.urlopen(url+'/api/runs/'+analysis['id'],timeout=10) as response:
            assert json.load(response)==analysis
