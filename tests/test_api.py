import csv
import io
import json
from fastapi.testclient import TestClient
import pytest
from graphlab.api import app, save_run
from graphlab.engine import generate

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('GRAPHLAB_DATA_DIR',str(tmp_path))
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        yield client


def test_upload_analyze_path_export_and_history(client):
    upload=client.post('/api/import',files={'file':('graph.csv',b'source,target,weight\nA,B,2\nB,C,1\nA,C,8\n','text/csv')})
    assert upload.status_code==200
    graph=upload.json()
    result=client.post('/api/analyze',json={'graph':graph,'parameters':{'balance_lambda':8}})
    assert result.status_code==200
    data=result.json();run_id=data['id']
    route=client.post('/api/path',json={'graph':graph,'source':'A','target':'C','hops':2}).json()
    assert route['distance']==3 and route['path']==['A','B','C']
    assert route['semiring']['min_weight_up_to_hops']==3
    assert client.get('/api/runs').json()[0]['id']==run_id
    assert client.get('/api/runs/'+run_id).json()==data
    exported=client.get(f'/api/runs/{run_id}/export?format=json')
    assert exported.json()==data
    rows=list(csv.DictReader(io.StringIO(client.get(f'/api/runs/{run_id}/export?format=csv').text)))
    assert len(rows)==4 and rows[-1]['algorithm']=='HDRF'
    assert rows[0]['fingerprint']==data['fingerprint']


def test_validation_errors_and_origin_boundary(client):
    assert client.post('/api/import',files={'file':('bad.csv',b'source,target,weight\nA,B,-1\n')}).status_code==400
    assert 'Line 2' in client.post('/api/import',files={'file':('bad.csv',b'source,target,weight\nA,A,1\n')}).json()['detail']
    graph=generate().model_dump()
    assert client.post('/api/analyze',json={'graph':graph,'parameters':{'partitions':9}}).status_code==422
    assert client.post('/api/analyze',content=json.dumps({'graph':graph,'parameters':{'balance_lambda':float('inf')}}),headers={'Content-Type':'application/json'}).status_code==422
    assert client.post('/api/path',json={'graph':graph,'source':'missing','target':'0'}).status_code==400
    assert client.post('/api/analyze',json={'graph':graph},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/analyze',json={'graph':graph},headers={'Origin':'http://localhost:8000'}).status_code==200
    assert client.post('/api/import',content=b'x'*2_000_001).status_code==413
    assert client.get('/api/runs/missing').status_code==404


def test_benchmark_api_exports_measured_rows(client):
    response=client.post('/api/benchmark',json={'family':'grid','sizes':[8,32],'repeats':2})
    assert response.status_code==200
    result=response.json()
    assert len(result['rows'])==8
    rows=list(csv.DictReader(io.StringIO(client.get(f"/api/runs/{result['id']}/export?format=csv").text)))
    assert [row['vertices'] for row in rows]==['8']*4+['32']*4
    assert all(float(row['median_ms'])>=0 for row in rows)
    assert client.post('/api/benchmark',json={'sizes':[1000]}).status_code==422
    assert client.post('/api/benchmark',json={'repeats':100}).status_code==422


def test_history_retains_latest_50(client):
    for i in range(52):save_run({'rows':[]},'benchmark',str(i))
    runs=client.get('/api/runs').json()
    assert len(runs)==50
    assert runs[0]['label']=='51' and runs[-1]['label']=='2'
