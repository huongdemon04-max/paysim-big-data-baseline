"""Copy UI inputs from a real pipeline into a NEW isolated evidence database.
No source writes/deletes. Snapshot consistency is checked against aggregate/alert totals
and the evaluation revision. For strict cross-collection freezing, pause producers first.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
from bson import json_util
from pymongo import MongoClient

parser=argparse.ArgumentParser()
parser.add_argument('--uri',default='mongodb://127.0.0.1:27017')
parser.add_argument('--database',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert args.database.startswith('paysim_ui_evidence_'), 'Use a new paysim_ui_evidence_... database'
client=MongoClient(args.uri,tz_aware=True)
assert args.database not in client.list_database_names(), 'Evidence database already exists; refusing to overwrite'
source=client.paysim
for attempt in range(60):
    run=source.runs.find_one(sort=[('started_at',-1)])
    if not run: time.sleep(1); continue
    run_id=run['run_id']; query={'run_id':run_id}
    evaluation=source.evaluation_totals.find_one({'_id':run_id})
    if not evaluation: time.sleep(1); continue
    rows={
        'runs':[run], 'evaluation_totals':[evaluation],
        'pipeline_metrics':list(source.pipeline_metrics.find(query).sort('batch_id',-1).limit(60)),
        'live_aggregates':list(source.live_aggregates.find(query)),
        'fraud_alerts':list(source.fraud_alerts.find(query)),
        'recent_transactions':list(source.recent_transactions.find(query).sort('scored_at',-1).limit(60)),
        'system_metrics':list(source.system_metrics.find({'_id':'spark'})),
    }
    processed=evaluation.get('processed',0); model=evaluation.get('model',{})
    if (processed and rows['pipeline_metrics'] and
        sum(x['transactions'] for x in rows['live_aggregates']) == processed and
        len(rows['fraud_alerts']) == model.get('tp',0)+model.get('fp',0) and
        rows['pipeline_metrics'][0].get('processed_total') == processed and
        source.evaluation_totals.find_one({'_id':run_id}) == evaluation):
        break
    time.sleep(1)
else: raise RuntimeError('No consistent completed batch snapshot available')
for collection,documents in rows.items():
    if documents: client[args.database][collection].insert_many(documents)
metadata=dict(captured_at=datetime.now(timezone.utc), source='real Kafka/Spark/HDFS/MongoDB pipeline',
              database=args.database, run_id=run_id, processed=processed, alerts=len(rows['fraud_alerts']),
              counts={k:len(v) for k,v in rows.items()}, collections=rows)
args.output.write_text(json_util.dumps(metadata,ensure_ascii=False,indent=2))
print(json_util.dumps({k:v for k,v in metadata.items() if k!='collections'},ensure_ascii=False,indent=2))
