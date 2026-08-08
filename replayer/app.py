from __future__ import annotations

import csv
import json
import os
import random
import signal
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from confluent_kafka import Producer
from pymongo import MongoClient, ReplaceOne


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


DATA_PATH = Path(os.getenv("DATA_PATH", "/data/paysim.csv"))
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "paysim.transactions")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "paysim")
MAX_EVENTS = env_int("MAX_EVENTS", 0)
EVENTS_PER_SECOND = env_float("EVENTS_PER_SECOND", 200.0)
START_ROW = env_int("START_ROW", 1)
DATASET_ROWS = env_int("DATASET_ROWS", 6_362_620)
LOOP_DATASET = env_bool("LOOP_DATASET", True)
RANDOM_SEED = env_int("RANDOM_SEED", 2026)
DUPLICATE_RATE = env_float("DUPLICATE_RATE", 0.0)
NULL_RATE = env_float("NULL_RATE", 0.0)
LATE_EVENT_RATE = env_float("LATE_EVENT_RATE", 0.0)
RUN_ID = os.getenv("RUN_ID", "").strip() or datetime.now(UTC).strftime(
    "run-%Y%m%d-%H%M%S"
)

BATCH_SIZE = 100
STOP_REQUESTED = False
DELIVERY_ERRORS = 0


def request_stop(_signum, _frame) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def delivery_report(error, _message) -> None:
    global DELIVERY_ERRORS
    if error is not None:
        DELIVERY_ERRORS += 1
        print(f"Kafka delivery error: {error}", flush=True)


def transaction_from_row(
    row: dict[str, str], source_row: int, cycle: int, event_number: int
) -> tuple[dict, dict]:
    event_time = datetime.now(UTC)
    injected_faults: list[str] = []

    if LATE_EVENT_RATE > 0 and random.random() < LATE_EVENT_RATE:
        event_time -= timedelta(hours=2)
        injected_faults.append("late_event")

    amount: float | None = float(row["amount"])
    if NULL_RATE > 0 and random.random() < NULL_RATE:
        amount = None
        injected_faults.append("null_amount")

    event_id = f"{RUN_ID}-c{cycle:03d}-e{event_number:012d}"
    transaction = {
        "event_id": event_id,
        "run_id": RUN_ID,
        "source_row": source_row,
        "source_cycle": cycle,
        "step": int(row["step"]),
        "type": row["type"],
        "amount": amount,
        "nameOrig": row["nameOrig"],
        "oldbalanceOrg": float(row["oldbalanceOrg"]),
        "newbalanceOrig": float(row["newbalanceOrig"]),
        "nameDest": row["nameDest"],
        "oldbalanceDest": float(row["oldbalanceDest"]),
        "newbalanceDest": float(row["newbalanceDest"]),
        "event_time": event_time.isoformat(),
        "emitted_at_ms": int(time.time() * 1000),
    }
    ground_truth = {
        "_id": event_id,
        "event_id": event_id,
        "run_id": RUN_ID,
        "source_row": source_row,
        "source_cycle": cycle,
        "isFraud": int(row["isFraud"]),
        "isFlaggedFraud": int(row["isFlaggedFraud"]),
        "injected_faults": injected_faults,
    }
    return transaction, ground_truth


def replay_batch(producer: Producer, labels: list[dict], transactions: list[dict]):
    database = mongo[MONGO_DATABASE]
    if labels:
        database.ground_truth.bulk_write(
            [ReplaceOne({"_id": item["_id"]}, item, upsert=True) for item in labels],
            ordered=False,
        )

    emitted = 0
    duplicates = 0
    batch_started = time.perf_counter()
    for transaction in transactions:
        payload = json.dumps(transaction, separators=(",", ":")).encode("utf-8")
        producer.produce(
            KAFKA_TOPIC,
            key=transaction["event_id"].encode("utf-8"),
            value=payload,
            callback=delivery_report,
        )
        producer.poll(0)
        emitted += 1

        if DUPLICATE_RATE > 0 and random.random() < DUPLICATE_RATE:
            producer.produce(
                KAFKA_TOPIC,
                key=transaction["event_id"].encode("utf-8"),
                value=payload,
                callback=delivery_report,
            )
            producer.poll(0)
            emitted += 1
            duplicates += 1

    if EVENTS_PER_SECOND > 0:
        expected_duration = emitted / EVENTS_PER_SECOND
        remaining = expected_duration - (time.perf_counter() - batch_started)
        if remaining > 0:
            time.sleep(remaining)
    producer.poll(0)
    elapsed = max(time.perf_counter() - batch_started, 0.001)
    return emitted, duplicates, elapsed


def update_run(
    database,
    *,
    source_rows: int,
    emitted_total: int,
    duplicates_total: int,
    source_row: int,
    cycle: int,
    batch_emitted: int,
    batch_seconds: float,
    started: float,
) -> None:
    elapsed = max(time.perf_counter() - started, 0.001)
    database.runs.update_one(
        {"_id": RUN_ID},
        {
            "$set": {
                "status": "running",
                "source_rows": source_rows,
                "unique_events_emitted": source_rows,
                "events_emitted": emitted_total,
                "duplicates_injected": duplicates_total,
                "delivery_errors": DELIVERY_ERRORS,
                "source_row": source_row,
                "source_cycle": cycle,
                "source_progress_pct": source_row / DATASET_ROWS,
                "instant_emission_rate": batch_emitted / max(batch_seconds, 0.001),
                "actual_emission_rate": emitted_total / elapsed,
                "last_event_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        },
    )


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"PaySim file not found: {DATA_PATH}")

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    random.seed(RANDOM_SEED)
    database = mongo[MONGO_DATABASE]
    database.ground_truth.create_index([("run_id", 1), ("event_id", 1)], unique=True)
    database.runs.create_index("started_at")

    database.runs.replace_one(
        {"_id": RUN_ID},
        {
            "_id": RUN_ID,
            "run_id": RUN_ID,
            "status": "starting",
            "started_at": datetime.now(UTC),
            "source_file": DATA_PATH.name,
            "dataset_rows": DATASET_ROWS,
            "start_row": START_ROW,
            "max_events": MAX_EVENTS,
            "loop_dataset": LOOP_DATASET,
            "events_per_second": EVENTS_PER_SECOND,
            "random_seed": RANDOM_SEED,
            "duplicate_rate": DUPLICATE_RATE,
            "null_rate": NULL_RATE,
            "late_event_rate": LATE_EVENT_RATE,
            "source_rows": 0,
            "unique_events_emitted": 0,
            "events_emitted": 0,
            "duplicates_injected": 0,
            "delivery_errors": 0,
            "source_cycle": 1,
            "source_progress_pct": 0.0,
        },
        upsert=True,
    )

    producer = Producer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "paysim-replayer",
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": "snappy",
            "linger.ms": 20,
        }
    )

    limit_text = "continuous" if MAX_EVENTS <= 0 else f"max={MAX_EVENTS}"
    print(
        f"Live replay {DATA_PATH} -> {KAFKA_TOPIC}; run={RUN_ID}; "
        f"{limit_text}; rate={EVENTS_PER_SECOND:.0f}/s; loop={LOOP_DATASET}",
        flush=True,
    )

    source_rows = 0
    emitted_total = 0
    duplicates_total = 0
    cycle = 1
    started = time.perf_counter()

    try:
        while not STOP_REQUESTED and (MAX_EVENTS <= 0 or source_rows < MAX_EVENTS):
            labels: list[dict] = []
            transactions: list[dict] = []
            rows_in_cycle = 0
            last_source_row = 0

            with DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for source_row, row in enumerate(reader, start=1):
                    if STOP_REQUESTED:
                        break
                    if cycle == 1 and source_row < START_ROW:
                        continue
                    if MAX_EVENTS > 0 and source_rows >= MAX_EVENTS:
                        break

                    source_rows += 1
                    rows_in_cycle += 1
                    last_source_row = source_row
                    transaction, ground_truth = transaction_from_row(
                        row, source_row, cycle, source_rows
                    )
                    transactions.append(transaction)
                    labels.append(ground_truth)

                    if len(transactions) >= BATCH_SIZE:
                        emitted, duplicates, batch_seconds = replay_batch(
                            producer, labels, transactions
                        )
                        emitted_total += emitted
                        duplicates_total += duplicates
                        update_run(
                            database,
                            source_rows=source_rows,
                            emitted_total=emitted_total,
                            duplicates_total=duplicates_total,
                            source_row=source_row,
                            cycle=cycle,
                            batch_emitted=emitted,
                            batch_seconds=batch_seconds,
                            started=started,
                        )
                        labels.clear()
                        transactions.clear()

            if transactions:
                emitted, duplicates, batch_seconds = replay_batch(
                    producer, labels, transactions
                )
                emitted_total += emitted
                duplicates_total += duplicates
                update_run(
                    database,
                    source_rows=source_rows,
                    emitted_total=emitted_total,
                    duplicates_total=duplicates_total,
                    source_row=last_source_row,
                    cycle=cycle,
                    batch_emitted=emitted,
                    batch_seconds=batch_seconds,
                    started=started,
                )

            if STOP_REQUESTED or (MAX_EVENTS > 0 and source_rows >= MAX_EVENTS):
                break
            if not LOOP_DATASET or rows_in_cycle == 0:
                break
            cycle += 1
            print(f"Dataset cycle {cycle} started", flush=True)

        remaining = producer.flush(30)
        elapsed = max(time.perf_counter() - started, 0.001)
        if STOP_REQUESTED:
            status = "stopped"
        elif MAX_EVENTS > 0 or not LOOP_DATASET:
            status = "completed" if remaining == 0 else "completed_with_errors"
        else:
            status = "stopped"
        database.runs.update_one(
            {"_id": RUN_ID},
            {
                "$set": {
                    "status": status,
                    "source_rows": source_rows,
                    "unique_events_emitted": source_rows,
                    "events_emitted": emitted_total,
                    "duplicates_injected": duplicates_total,
                    "delivery_errors": DELIVERY_ERRORS + remaining,
                    "actual_emission_rate": emitted_total / elapsed,
                    "completed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        print(
            f"Replay {status}: rows={source_rows}, emitted={emitted_total}, "
            f"duplicates={duplicates_total}, elapsed={elapsed:.1f}s",
            flush=True,
        )
    except Exception as error:
        database.runs.update_one(
            {"_id": RUN_ID},
            {
                "$set": {
                    "status": "failed",
                    "error": str(error),
                    "completed_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        raise


mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30_000)


if __name__ == "__main__":
    main()
