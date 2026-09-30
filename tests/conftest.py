"""HTTP API checks use the actual server, without an in-process ASGI client."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import pytest

@pytest.fixture
def api_server(tmp_path, monkeypatch):
    monkeypatch.setenv('GRAPHLAB_DATA_DIR',str(tmp_path/'api-history'))
    with socket.socket() as handle:
        handle.bind(('127.0.0.1',0));port=handle.getsockname()[1]
    root=Path(__file__).resolve().parents[1]
    process=subprocess.Popen([sys.executable,'run_lab.py','--port',str(port),'--no-browser'],cwd=root,env=os.environ.copy(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if process.poll() is not None:raise AssertionError('API server exited before becoming ready.')
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise AssertionError('API server did not become ready.')
        yield url
    finally:
        process.terminate();process.wait(timeout=10)
