"""UI equivalence on a deterministic Mongo fixture (not a pipeline E2E test)."""
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import mongomock
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dashboard'))
import dashboard_core


def fixture_database():
    db = mongomock.MongoClient(tz_aware=True).paysim
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    db.runs.insert_one(dict(run_id='ui-test', started_at=now, status='completed', events_emitted=100,
                            instant_emission_rate=50, source_progress_pct=.5, source_row=100, dataset_rows=200))
    db.evaluation_totals.insert_one(dict(_id='ui-test', processed=100, updated_at=now,
        model=dict(tp=1, fp=1, tn=97, fn=1), rule=dict(tp=1, fp=0, tn=98, fn=1)))
    for i in range(3):
        db.pipeline_metrics.insert_one(dict(run_id='ui-test', batch_id=i, created_at=now,
            processing_throughput=25+i, ingest_throughput=50, consumer_lag=0,
            ingest_latency_p95_ms=10, latency_p95_ms=500+i, batch_duration_seconds=2+i,
            processed_rows=100, input_rows=100, aggregate_correctness=True, transformation_correctness=True))
    db.live_aggregates.insert_one(dict(run_id='ui-test', type='TRANSFER', transactions=100,
                                     model_alerts=2, rule_alerts=1, total_amount=15000))
    for i in range(2):
        row=dict(run_id='ui-test', event_id=f'e{i}', scored_at=now, type='TRANSFER', amount=100+i,
                 risk_score=.8, prediction=1, source_cycle=1, source_row=i, end_to_end_latency_ms=500)
        db.fraud_alerts.insert_one(row.copy()); db.recent_transactions.insert_one(row.copy())
    return db


def app_source(view):
    return ('from dashboard_core import render\n' +
            ('render()' if view == 'baseline' else f'import view_{view} as view\nrender(view)'))


def metrics(at):
    # Timing of the UI query and wall-clock freshness are not business results.
    exclude = {'Query latency', 'Snapshot response', 'Dashboard freshness'}
    return sorted((m.label, m.value, m.delta) for m in at.metric if m.label not in exclude)


@pytest.mark.parametrize('view', ['operations', 'report', 'studio'])
def test_all_four_pages_preserve_six_run_metrics(view):
    db = fixture_database()
    with patch.object(dashboard_core, 'get_database', return_value=db):
        before = AppTest.from_string(app_source('baseline')).run()
        after = AppTest.from_string(app_source(view)).run()
        assert not before.exception and not after.exception
        pages = before.radio[0].options
        for page in pages:
            before.radio[0].set_value(page).run()
            # The view switch stays active on the same fragment rerun path.
            if view == 'operations': after.radio[0].set_value(page).run()
            elif view == 'report': after.selectbox[0].set_value(page).run()
            else: after.button_group[0].set_value([page]).run()
            assert not before.exception and not after.exception
            labels = {'Nguồn đã phát','Spark đã xử lý','Fraud alerts','Ingest hiện tại',
                      'Processing throughput','End-to-end latency p95'}
            expected = [m for m in metrics(before) if m[0] in labels]
            actual = [m for m in metrics(after) if m[0] in labels]
            assert expected == actual
            # Core pages can be rearranged or enriched; six canonical run values stay identical.
            assert {m[0] for m in actual} == labels



@pytest.mark.parametrize('view', ['baseline', 'operations', 'report', 'studio'])
def test_empty_database_displays_waiting_message(view):
    db = mongomock.MongoClient().paysim
    with patch.object(dashboard_core, 'get_database', return_value=db):
        app = AppTest.from_string(app_source(view)).run()
        assert not app.exception
        assert 'Pipeline đang chuẩn bị' in app.info[0].value
