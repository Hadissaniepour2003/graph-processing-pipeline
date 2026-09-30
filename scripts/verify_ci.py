"""Bound the entire test process and return its diagnostic output on a stall."""
import argparse
import os
import signal
import subprocess
import sys

parser=argparse.ArgumentParser()
parser.add_argument('suite',choices=['unit','browser'])
args=parser.parse_args()
marker='not browser' if args.suite=='unit' else 'browser'
command=[sys.executable,'-m','pytest','-v','-m',marker,'-o','faulthandler_timeout=30']
print('Running:', ' '.join(command),flush=True)
process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=os.name!='nt')
try:
    output,_=process.communicate(timeout=240)
except subprocess.TimeoutExpired:
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        os.killpg(process.pid,signal.SIGKILL)
    output,_=process.communicate(timeout=15)
    print(output.decode('utf-8',errors='replace'),flush=True)
    print('The test process exceeded 240 seconds and was terminated.',flush=True)
    raise SystemExit(1)
print(output.decode('utf-8',errors='replace'),flush=True)
raise SystemExit(process.returncode)
