"""Verify the actual .cmd bootstrap, including venv setup, on Windows CI."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import pytest

@pytest.mark.skipif(os.name!='nt',reason='The Windows .cmd launcher needs Windows.')
def test_windows_launcher_bootstraps_and_serves(tmp_path):
    root=Path(__file__).resolve().parents[1]
    with socket.socket() as handle:
        handle.bind(('127.0.0.1',0));port=handle.getsockname()[1]
    env={**os.environ,'GRAPHLAB_DATA_DIR':str(tmp_path/'history'),'PYTHONIOENCODING':'utf-8'}
    log_path=tmp_path/'launcher.log'
    with log_path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(['cmd','/c','Start-GraphLab.cmd','--no-browser','--port',str(port)],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        url=f'http://127.0.0.1:{port}'
        try:
            deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                if process.poll() is not None:raise AssertionError(log_path.read_text(encoding='utf-8'))
                try:
                    with urllib.request.urlopen(url+'/api/health',timeout=1) as response:
                        assert json.load(response)['status']=='ok'
                    break
                except OSError:time.sleep(.2)
            else:raise AssertionError('Launcher timed out: '+log_path.read_text(encoding='utf-8'))
            assert (root/'.venv'/'Scripts'/'python.exe').exists()
            with urllib.request.urlopen(url) as response:assert b'Graph Processing Lab' in response.read()
            payload=json.dumps({'graph':{'edges':[{'source':'A','target':'B','weight':2}]}}).encode()
            request=urllib.request.Request(url+'/api/analyze',data=payload,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request) as response:
                result=json.load(response)
                assert result['summary']['vertices']==2 and len(result['partitions'])==4
            assert (tmp_path/'history'/'experiments.sqlite').exists()
        finally:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            process.wait(timeout=15)
