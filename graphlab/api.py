"""Local FastAPI application with SQLite experiment history."""
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlparse
import uuid
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from .models import AnalysisRequest, PathRequest, BenchmarkRequest, MAX_UPLOAD, parse_csv
from .engine import analyze, generate, benchmark, shortest_path, semiring_query

WEB = Path(__file__).parent / 'web'
app = FastAPI(docs_url=None, redoc_url=None, title='Graph Processing Lab', version='2.0.0', description='A local simulation of graph storage and partitioning. No external API or cloud processing.')


@contextmanager
def connect():
    directory = Path(os.environ.get('GRAPHLAB_DATA_DIR', '.data'))
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / 'experiments.sqlite', timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, kind TEXT, label TEXT, result TEXT)')
    try:
        with db:
            yield db
    finally:
        db.close()


def save_run(result, kind, label):
    run_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    result.update({'id': run_id, 'created': created, 'type': kind})
    with connect() as db:
        db.execute('INSERT INTO runs VALUES (?, ?, ?, ?, ?)', (run_id, created, kind, label, json.dumps(result, allow_nan=False)))
        db.execute('DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY created DESC LIMIT 50)')
    return result


def get_run(run_id):
    with connect() as db:
        row = db.execute('SELECT result FROM runs WHERE id = ?', (run_id,)).fetchone()
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(404, 'Experiment not found. History keeps the latest 50 runs.')
    return json.loads(row[0])


@app.middleware('http')
async def local_boundary(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1') or parsed.port != request.url.port:
                return JSONResponse({'detail': 'Open this application from its local address.'}, status_code=403)
        chunks = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > 2_000_000:
                return JSONResponse({'detail': 'Request is too large. Maximum body size: 2 MB.'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    return await call_next(request)


@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=400)


@app.exception_handler(RequestValidationError)
async def input_error(request, exc):
    errors = ['.'.join(map(str, error['loc'][1:])) + ': ' + error['msg'] for error in exc.errors()]
    return JSONResponse({'detail': '; '.join(errors)}, status_code=422)


@app.get('/')
def home():
    return FileResponse(WEB / 'index.html')


@app.get('/docs', include_in_schema=False)
def api_docs():
    return FileResponse(WEB / 'docs.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '2.0.0'}


@app.get('/api/example')
def example(family: str = 'sample', size: int = 24, seed: int = 42):
    if not 0 <= seed <= 2**31-1:
        raise ValueError('Seed must be from 0 to 2147483647.')
    return generate(family, size, seed).model_dump()


@app.post('/api/import')
async def upload(file: UploadFile = File(...)):
    try:
        data = await file.read(MAX_UPLOAD + 1)
        return parse_csv(data).model_dump()
    finally:
        await file.close()


@app.post('/api/analyze')
def analysis(request: AnalysisRequest):
    result = analyze(request.graph, request.parameters)
    summary = result['summary']
    return save_run(result, 'analysis', f"{summary['vertices']} vertices · {summary['edges']} edges")


@app.post('/api/path')
def path(request: PathRequest):
    return {**shortest_path(request.graph, request.source, request.target),
            'semiring': semiring_query(request.graph, request.source, request.target, request.hops)}


@app.post('/api/benchmark')
def run_benchmark(request: BenchmarkRequest):
    return save_run(benchmark(request), 'benchmark', f"{request.family} · {', '.join(map(str, request.sizes))} vertices")


@app.get('/api/runs')
def runs():
    with connect() as db:
        rows = db.execute('SELECT id, created, kind, label FROM runs ORDER BY created DESC LIMIT 50').fetchall()
    return [{'id': row[0], 'created': row[1], 'type': row[2], 'label': row[3]} for row in rows]


@app.get('/api/runs/{run_id}')
def reopen(run_id: str):
    return get_run(run_id)


@app.get('/api/runs/{run_id}/export')
def export(run_id: str, format: str = 'json'):
    result = get_run(run_id)
    if format == 'json':
        data = json.dumps(result, indent=2, allow_nan=False)
        media_type = 'application/json'
    elif format == 'csv':
        if result['type'] == 'benchmark':
            rows = result['rows']
        else:
            rows = [{key: partition.get(key) for key in ('algorithm', 'kind', 'runtime_ms', 'loads', 'max_load_ratio', 'cut_edges', 'cut_fraction', 'replication_factor', 'used_partitions')}
                    for partition in result['partitions']]
            for row in rows:
                row.update({'vertices': result['summary']['vertices'], 'edges': result['summary']['edges'],
                            'seed': result['parameters']['seed'], 'balance_lambda': result['parameters']['balance_lambda'],
                            'capacity': result['parameters']['capacity'], 'fingerprint': result['fingerprint']})
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})
        data, media_type = output.getvalue(), 'text/csv'
    else:
        raise ValueError('Export format must be json or csv.')
    return Response(data, media_type=media_type, headers={'Content-Disposition': f'attachment; filename="graphlab-{run_id}.{format}"'})

app.mount('/static', StaticFiles(directory=WEB), name='static')
