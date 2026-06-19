"""Export the Yandaojie (研道街) study data from MongoDB for analysis.

Produces, for every run, a timestamped folder containing:

* ``raw/<collection>.jsonl`` — full-fidelity newline-delimited JSON, one document
  per line (datetimes as ISO-8601, Mongo ``_id`` stringified). This is the
  canonical archive and preserves nested structures (reflections, diagnoses,
  targeted_objectives, defense_turns, ...).
* ``csv/*.csv`` — flattened, analysis-friendly tables (one row per session, one
  row per defense turn, one row per reflection, etc.) for Excel / R / SPSS /
  pandas.
* ``manifest.json`` — counts and metadata for the export.

The Mongo instance is bound to ``127.0.0.1:27017`` on the Tencent Cloud server,
so run this either ON the server, or locally through an SSH tunnel:

    ssh -N -L 27017:127.0.0.1:27017 ubuntu@<TC_HOST>
    python scripts/export_yandaojie_data.py

By default the connection string is read from ``YANDAOJIE_MONGODB_URI`` (in
``backend/.env``) and falls back to ``mongodb://localhost:27017/yandaojie``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402

DEFAULT_URI = "mongodb://localhost:27017/yandaojie"

# Known collections written by YandaojiePersistenceService.
COLLECTIONS = (
    "sessions",
    "defense_questions",
    "defense_turns",
    "events",
    "errors",
)

# Real classroom students use purely numeric IDs (optionally suffixed with 号),
# e.g. "1", "42", "4号". Everything else ("test", "chenyu-*", ...) is dev/QA.
_REAL_STUDENT_RE = re.compile(r"^\d+号?$")


def _is_real_student(student_id: Any) -> bool:
    return bool(student_id) and bool(_REAL_STUDENT_RE.match(str(student_id)))


def _real_session_ids(db: Any) -> set[str]:
    """Session ids belonging to real (numbered) students."""
    return {
        s["session_id"]
        for s in db.sessions.find({}, {"session_id": 1, "student_id": 1})
        if _is_real_student(s.get("student_id"))
    }


def _jsonify(value: Any) -> Any:
    """Recursively convert Mongo/BSON values into JSON-serialisable Python."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    # bson.ObjectId and similar -> str
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def _clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return _jsonify(doc)


def _csv_cell(value: Any) -> str:
    """Render a value for a flat CSV cell. Nested objects become JSON strings."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_cell(row.get(key)) for key in fieldnames})
    return len(rows)


def _keep_doc(doc: dict[str, Any], real_session_ids: set[str] | None) -> bool:
    """When filtering to real students, keep docs in a real session (or, lacking
    a session_id, docs whose student_id is numeric)."""
    if real_session_ids is None:
        return True
    sid = doc.get("session_id")
    if sid is not None:
        return sid in real_session_ids
    return _is_real_student(doc.get("student_id"))


def export_raw_jsonl(
    db: Any, output_dir: Path, real_session_ids: set[str] | None = None
) -> dict[str, int]:
    """Dump every collection as JSONL. Returns {collection: doc_count}."""
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    present = set(db.list_collection_names())
    collections = list(COLLECTIONS) + sorted(present - set(COLLECTIONS))

    counts: dict[str, int] = {}
    for name in collections:
        if name not in present:
            counts[name] = 0
            continue
        count = 0
        with (raw_dir / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for doc in db[name].find():
                if not _keep_doc(doc, real_session_ids):
                    continue
                handle.write(json.dumps(_clean_doc(doc), ensure_ascii=False) + "\n")
                count += 1
        counts[name] = count
    return counts


def export_csv_views(
    db: Any, output_dir: Path, real_session_ids: set[str] | None = None
) -> dict[str, int]:
    """Build flattened, analysis-friendly CSVs. Returns {file: row_count}."""
    csv_dir = output_dir / "csv"
    counts: dict[str, int] = {}

    keep = lambda d: _keep_doc(d, real_session_ids)  # noqa: E731
    sessions = [_clean_doc(d) for d in db.sessions.find() if keep(d)]
    questions = [_clean_doc(d) for d in db.defense_questions.find() if keep(d)]
    turns = [_clean_doc(d) for d in db.defense_turns.find() if keep(d)]
    events = [_clean_doc(d) for d in db.events.find() if keep(d)]
    errors = [_clean_doc(d) for d in db.errors.find() if keep(d)]

    # One row per session.
    session_rows = []
    reflection_rows = []
    for s in sessions:
        objectives = s.get("learning_objectives") or []
        reflections = s.get("reflections") or []
        session_rows.append(
            {
                "session_id": s.get("session_id"),
                "student_id": s.get("student_id"),
                "stage": s.get("stage"),
                "subject_id": s.get("subject_id"),
                "subject_label": s.get("subject_label"),
                "subject_topic": s.get("subject_topic"),
                "learning_objectives": " | ".join(objectives),
                "objective_count": len(objectives),
                "reflection_count": len(reflections),
                "current_round_index": s.get("current_round_index"),
                "completed_round_count": s.get("completed_round_count"),
                "defense_turn_count": len(s.get("defense_turns") or []),
                "started_at": s.get("started_at"),
                "last_seen_at": s.get("last_seen_at"),
                "completed_at": s.get("completed_at"),
            }
        )
        for r in reflections:
            idx = r.get("objective_index")
            objective_text = (
                objectives[idx] if isinstance(idx, int) and 0 <= idx < len(objectives) else None
            )
            reflection_rows.append(
                {
                    "session_id": s.get("session_id"),
                    "student_id": s.get("student_id"),
                    "subject_label": s.get("subject_label"),
                    "subject_topic": s.get("subject_topic"),
                    "objective_index": idx,
                    "objective_text": objective_text,
                    "learned": r.get("learned"),
                    "questions": r.get("questions"),
                }
            )

    # One row per generated question (with diagnoses unpacked).
    question_rows = []
    for q in questions:
        diagnoses = q.get("diagnoses") or {}
        question_rows.append(
            {
                "session_id": q.get("session_id"),
                "student_id": q.get("student_id"),
                "round_index": q.get("round_index"),
                "subject_id": q.get("subject_id"),
                "subject_label": q.get("subject_label"),
                "subject_topic": q.get("subject_topic"),
                "model": q.get("model"),
                "question": q.get("question"),
                "targeted_objectives": q.get("targeted_objectives"),
                "mastered": " | ".join(diagnoses.get("mastered") or []),
                "not_mastered": " | ".join(diagnoses.get("not_mastered") or []),
                "reasoning_content": q.get("reasoning_content"),
                "created_at": q.get("created_at"),
            }
        )

    # One row per completed defense turn (question + student's answer).
    turn_rows = [
        {
            "session_id": t.get("session_id"),
            "student_id": t.get("student_id"),
            "subject_id": t.get("subject_id"),
            "round_index": t.get("round_index"),
            "question": t.get("question"),
            "answer_text": t.get("answer_text"),
            "answered_at": t.get("answered_at"),
            "created_at": t.get("created_at"),
        }
        for t in turns
    ]

    event_rows = [
        {
            "event_id": e.get("event_id"),
            "session_id": e.get("session_id"),
            "student_id": e.get("student_id"),
            "event_type": e.get("event_type"),
            "stage": e.get("stage"),
            "round_index": e.get("round_index"),
            "client_timestamp": e.get("client_timestamp"),
            "recorded_at": e.get("recorded_at"),
            "payload": e.get("payload"),
        }
        for e in events
    ]

    error_rows = [
        {
            "error_id": e.get("error_id"),
            "session_id": e.get("session_id"),
            "student_id": e.get("student_id"),
            "stage": e.get("stage"),
            "error_scope": e.get("error_scope"),
            "error_message": e.get("error_message"),
            "raw_error": e.get("raw_error"),
            "round_index": e.get("round_index"),
            "metadata": e.get("metadata"),
            "recorded_at": e.get("recorded_at"),
        }
        for e in errors
    ]

    counts["sessions.csv"] = _write_csv(
        csv_dir / "sessions.csv",
        session_rows,
        [
            "session_id", "student_id", "stage", "subject_id", "subject_label",
            "subject_topic", "learning_objectives", "objective_count",
            "reflection_count", "current_round_index", "completed_round_count",
            "defense_turn_count", "started_at", "last_seen_at", "completed_at",
        ],
    )
    counts["reflections.csv"] = _write_csv(
        csv_dir / "reflections.csv",
        reflection_rows,
        [
            "session_id", "student_id", "subject_label", "subject_topic",
            "objective_index", "objective_text", "learned", "questions",
        ],
    )
    counts["defense_questions.csv"] = _write_csv(
        csv_dir / "defense_questions.csv",
        question_rows,
        [
            "session_id", "student_id", "round_index", "subject_id",
            "subject_label", "subject_topic", "model", "question",
            "targeted_objectives", "mastered", "not_mastered",
            "reasoning_content", "created_at",
        ],
    )
    counts["defense_turns.csv"] = _write_csv(
        csv_dir / "defense_turns.csv",
        turn_rows,
        [
            "session_id", "student_id", "subject_id", "round_index",
            "question", "answer_text", "answered_at", "created_at",
        ],
    )
    counts["events.csv"] = _write_csv(
        csv_dir / "events.csv",
        event_rows,
        [
            "event_id", "session_id", "student_id", "event_type", "stage",
            "round_index", "client_timestamp", "recorded_at", "payload",
        ],
    )
    counts["errors.csv"] = _write_csv(
        csv_dir / "errors.csv",
        error_rows,
        [
            "error_id", "session_id", "student_id", "stage", "error_scope",
            "error_message", "raw_error", "round_index", "metadata", "recorded_at",
        ],
    )
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Yandaojie MongoDB study data to JSONL + analysis CSVs.",
    )
    parser.add_argument(
        "--uri",
        default=None,
        help="MongoDB connection string. Defaults to YANDAOJIE_MONGODB_URI or "
        f"{DEFAULT_URI}.",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Database name. Defaults to YANDAOJIE_MONGODB_DATABASE or 'yandaojie'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to backend/exports/yandaojie/<timestamp>/.",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Only write the raw JSONL dump, skip the flattened CSVs.",
    )
    parser.add_argument(
        "--real-only",
        action="store_true",
        help="Exclude dev/QA accounts, keeping only real numbered students "
        "(IDs like '1', '42', '4号').",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    args = parse_args()
    settings = Settings()

    uri = args.uri or settings.yandaojie_mongodb_uri or DEFAULT_URI
    database = args.database or settings.yandaojie_mongodb_database or "yandaojie"

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_dir = args.output_dir or (BACKEND_DIR / "exports" / "yandaojie" / timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)

    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    try:
        client.admin.command("ping")
    except Exception as exc:  # pragma: no cover - connectivity guard
        print(
            f"Could not connect to MongoDB at {uri!r}: {exc}\n"
            "If the DB is on the Tencent Cloud server, open an SSH tunnel first:\n"
            "  ssh -N -L 27017:127.0.0.1:27017 ubuntu@<TC_HOST>",
            file=sys.stderr,
        )
        return 1

    db = client[database]
    real_session_ids = _real_session_ids(db) if args.real_only else None
    raw_counts = export_raw_jsonl(db, output_dir, real_session_ids)
    csv_counts = (
        {} if args.no_csv else export_csv_views(db, output_dir, real_session_ids)
    )

    manifest = {
        "exported_at": datetime.now().isoformat(),
        "database": database,
        "real_only": bool(args.real_only),
        "raw_jsonl_document_counts": raw_counts,
        "csv_row_counts": csv_counts,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    client.close()

    print(f"Export complete: {output_dir}")
    print(f"  raw JSONL: {raw_counts}")
    if csv_counts:
        print(f"  CSV rows:  {csv_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
