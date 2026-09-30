"""Real UI tests; GRAPH_CHROMIUM may select a preinstalled Chromium binary."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import pytest
from playwright.sync_api import sync_playwright, expect

pytestmark=pytest.mark.browser
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def running_app(tmp_path_factory):
    with socket.socket() as socket_handle:
        socket_handle.bind(('127.0.0.1',0));port=socket_handle.getsockname()[1]
    env={**os.environ,'GRAPHLAB_DATA_DIR':str(tmp_path_factory.mktemp('browser-history'))}
    process=subprocess.Popen([sys.executable,'run_lab.py','--port',str(port),'--no-browser'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}'
    try:
        for _ in range(150):
            if process.poll() is not None:raise RuntimeError('The test server exited before becoming ready.')
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Test server did not become ready.')
        yield url
    finally:
        process.terminate();process.wait(timeout=10)

@pytest.fixture
def page(running_app):
    with sync_playwright() as playwright:
        options={'args':['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']}
        if os.environ.get('GRAPH_CHROMIUM'):options['executable_path']=os.environ['GRAPH_CHROMIUM']
        browser=playwright.chromium.launch(**options)
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        errors=[];context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
        page=context.new_page();page.goto(running_app);expect(page.locator('#comparison tbody tr')).to_have_count(4)
        expect(page.locator('#analyze')).to_be_enabled()
        yield page
        assert errors==[],errors
        browser.close()


def test_upload_shortest_path_and_bad_input_recovery(page):
    page.locator('#csv-file').set_input_files({'name':'cities.csv','mimeType':'text/csv','buffer':b'source,target,weight\nA,B,2\nB,C,1\nA,C,8\n'})
    expect(page.locator('#result-title')).to_have_text('3 vertices · 3 edges')
    expect(page.locator('#analyze')).to_be_enabled()
    page.get_by_role('button',name='Paths & semirings',exact=True).click()
    page.locator('#source').select_option('A');page.locator('#target').select_option('C');page.locator('#hops').fill('2')
    page.locator('#find-path').click()
    expect(page.locator('#path-result')).to_contain_text('A → B → C')
    expect(page.locator('#path-result')).to_contain_text('Total weight: 3.00')
    page.get_by_role('button',name='Show route on partition map →').click()
    expect(page.locator('#graph-note')).to_contain_text('highlighted in orange')
    page.locator('#csv-file').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'source,target,weight\nA,A,1\n'})
    expect(page.locator('#message')).to_contain_text('Line 2')
    expect(page.locator('#result-title')).to_have_text('3 vertices · 3 edges')
    expect(page.locator('#analyze')).to_be_enabled()
    page.locator('#analyze').click();expect(page.locator('#message')).to_be_hidden()


def test_lambda_capacity_trace_storage_and_download(page,tmp_path):
    hdrf=page.locator('#comparison tbody tr').filter(has_text='HDRF')
    expect(hdrf).to_contain_text('12 / 0')
    page.locator('#lambda').fill('8');page.locator('#analyze').click();expect(hdrf).to_contain_text('6 / 6')
    page.locator('#capacity').check();page.locator('#analyze').click()
    expect(page.locator('#result-meta')).to_contain_text('capacity constrained')
    expect(page.locator('#analyze')).to_be_enabled()
    page.get_by_role('button',name='Decisions',exact=True).click()
    expect(page.locator('#trace-context')).to_contain_text('Edge 0 — 1')
    page.locator('#trace-step').fill('3');page.locator('#trace-step').dispatch_event('input')
    expect(page.locator('#step-label')).to_have_text('4 / 12')
    expect(page.locator('#trace-table tbody tr')).to_have_count(2)
    page.get_by_role('button',name='Storage',exact=True).click()
    expect(page.locator('#storage-table')).to_contain_text('512 B')
    expect(page.locator('#storage-table')).to_contain_text('456 B')
    with page.expect_download() as download_info:page.locator('#export-json').click()
    path=tmp_path/'analysis.json';download_info.value.save_as(path)
    exported=json.loads(path.read_text())
    assert exported['parameters']['balance_lambda']==8
    assert exported['parameters']['capacity'] is True
    assert len(exported['partitions'])==4


def test_benchmark_export_and_persistent_history(page,tmp_path):
    page.get_by_role('button',name='Benchmarks',exact=True).click()
    page.locator('#bench-sizes').fill('8,32');page.locator('#repeats').fill('2');page.locator('#benchmark').click()
    expect(page.locator('#bench-table tbody tr')).to_have_count(8)
    expect(page.locator('#benchmark')).to_be_enabled()
    with page.expect_download() as info:page.locator('#export-csv').click()
    path=tmp_path/'benchmark.csv';info.value.save_as(path)
    assert 'median_ms' in path.read_text() and 'HDRF' in path.read_text()
    page.reload();expect(page.locator('#analyze')).to_be_enabled()
    page.get_by_role('button',name='History',exact=True).click()
    row=page.locator('.history-row').filter(has_text='hub · 8, 32 vertices').first
    expect(row).to_be_visible();expect(row.get_by_role('button',name='Reopen')).to_be_enabled()
    row.get_by_role('button',name='Reopen').click()
    expect(page.locator('#bench-table tbody tr')).to_have_count(8)
    expect(page.locator('#result-title')).to_have_text('Benchmark · hub')


def test_large_graph_mobile_and_offline_api_docs(page):
    page.locator('#family').select_option('grid');page.locator('#size').fill('160');page.locator('#load-example').click()
    expect(page.locator('#result-title')).to_have_text('160 vertices · 294 edges')
    expect(page.locator('#graph')).to_contain_text('Large graph')
    expect(page.locator('#load-example')).to_be_enabled()
    page.get_by_role('button',name='Paths & semirings',exact=True).click();page.locator('#find-path').click()
    expect(page.locator('#path-result')).to_contain_text('limited to 64 vertices')
    expect(page.locator('#find-path')).to_be_enabled()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth')<=390
    page.goto(page.url.split('/')[0]+'//'+page.url.split('/')[2]+'/docs')
    page.locator('#send').click();expect(page.locator('#response')).to_contain_text('"status": "ok"')
    expect(page.locator('#endpoints')).to_contain_text('/api/analyze')
