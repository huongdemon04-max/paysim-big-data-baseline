"""Capture all views against a running, frozen REAL MongoDB snapshot.
Usage: python tests/capture_dashboard.py --output docs/evidence/dashboard-ui
Requires: playwright install chromium; stop replayer/spark after finishing a batch.
Does not seed or modify MongoDB. Temporary entrypoints import the same view modules.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--views', nargs='+', default=['baseline', 'operations', 'report', 'studio'],
                    choices=['baseline', 'operations', 'report', 'studio'])
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
previous = args.output / 'browser-results.json'
report = [row for row in json.loads(previous.read_text()) if row['view'] not in args.views] if previous.exists() else []
with tempfile.TemporaryDirectory(prefix='paysim-capture-') as tmp, sync_playwright() as p:
    browser = p.chromium.launch()
    for view in args.views:
        entry = Path(tmp) / f'{view}.py'
        entry.write_text(f'import sys\nsys.path.insert(0, {str(ROOT / "dashboard")!r})\nfrom dashboard_core import render\n' +
                         ('render()\n' if view == 'baseline' else f'import view_{view} as view\nrender(view)\n'))
        log = open(Path(tmp) / f'{view}-server.log', 'w')
        proc = subprocess.Popen([os.sys.executable, '-m', 'streamlit', 'run', str(entry),
            '--server.port=8510', '--server.address=127.0.0.1', '--server.headless=true', '--browser.gatherUsageStats=false',
            '--theme.base=light'], env={**os.environ, 'MONGO_URI': os.environ.get('MONGO_URI', 'mongodb://127.0.0.1:27017')},
            stdout=log, stderr=subprocess.STDOUT)
        try:
            for attempt in range(100):
                try:
                    urllib.request.urlopen('http://127.0.0.1:8510/_stcore/health', timeout=1)
                    break
                except Exception: time.sleep(.2)
            page = browser.new_page(viewport={'width': 1600, 'height': 1600}, device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8510')
            page.get_by_text('Nguồn đã phát', exact=True).wait_for(timeout=30000)
            labels = ['📡 Live Control Room', '🎯 Metrics theo 10 tracks', '🛡️ Fraud & Business', '🔎 Dòng dữ liệu mới']
            for i, label in enumerate(labels):
                if view in ('baseline','operations'):
                    page.get_by_text(label, exact=True).click()
                elif view == 'report':
                    page.get_by_role('combobox').click()
                    page.get_by_role('option', name=label, exact=True).click()
                else:
                    page.get_by_role('button', name=label.split(' ', 1)[1], exact=False).click()
                expected=['Tốc độ ingest và xử lý','01. Ingestion','Rule baseline vs Spark MLlib','Giao dịch vừa đi qua Spark'][i]
                if i == 0 and view == 'operations': expected = 'Trung tâm vận hành'
                if i == 0 and view == 'report': expected = '03 / Chất lượng phát hiện'
                page.get_by_text(expected, exact=True).first.wait_for(timeout=15000)
                page.wait_for_timeout(900)
                assert page.locator('[data-testid="stException"]').count() == 0
                page.screenshot(path=str(args.output/f'{view}-{i+1}-desktop.png'), full_page=True)
                metrics=page.locator('[data-testid="stMetric"]').all_text_contents()
                report.append(dict(view=view, page=label, metrics=metrics, browser_errors=list(errors),
                                   screenshot=f'{view}-{i+1}-desktop.png'))
            # Mobile reopens overview; sidebar navigation expands when needed.
            page.set_viewport_size({'width':390,'height':844})
            page.reload()
            page.get_by_text('Nguồn đã phát',exact=True).wait_for(timeout=15000)
            collapse = page.locator('[data-testid="stSidebarCollapseButton"] button')
            if collapse.count() and collapse.is_visible(): collapse.click()
            page.wait_for_timeout(1200)
            assert page.locator('[data-testid="stException"]').count() == 0
            page.screenshot(path=str(args.output/f'{view}-mobile.png'),full_page=True)
            page.close()
        finally:
            proc.terminate(); proc.wait(timeout=15); log.close()
    browser.close()
(args.output/'browser-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(f'Recorded {len(report)} desktop pages; refreshed mobile overviews for {args.views}.')
