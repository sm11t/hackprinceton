"""Saved ventures: one JSON file per venture under playground/output/ventures/<user>/ (gitignored).

A venture is one workflow (e.g. "I have a budget"): the choices made, the stage reached, the shortlist,
the chosen pair, the checklist progress and a status. Demo accounts only: the user name is a label,
not an authenticated identity.
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "output" / "ventures"
KINDS = {"budget": "I have a budget", "idea": "I have an idea", "space": "I have a space"}
STAGES = ["budget", "scan", "opportunities", "shortlist", "investigate", "decide", "plan"]
STATUSES = ["exploring", "shortlisted", "investigating", "verifying", "ready", "paused", "dropped"]
FIELDS = {"name", "stage", "status", "inputs", "shortlist", "chosen", "checklist", "notes", "summary"}
MAX_BYTES = 200_000


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe(name, what):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
        raise ValueError(f"Invalid {what}.")
    return name


def folder(user):
    return ROOT / safe(user, "user")


def create(user, kind="budget", name=None):
    if kind not in KINDS:
        raise ValueError("Unknown venture kind.")
    vid = uuid.uuid4().hex[:12]
    venture = {"id": vid, "user": user, "kind": kind, "name": name or KINDS[kind], "stage": STAGES[0],
               "status": STATUSES[0], "inputs": {}, "shortlist": [], "chosen": None, "checklist": {}, "notes": "",
               "summary": None, "created_at": now(), "updated_at": now()}
    save(venture)
    return venture


def save(venture):
    path = folder(venture["user"]) / f"{safe(venture['id'], 'venture id')}.json"
    text = json.dumps(venture)
    if len(text) > MAX_BYTES:
        raise ValueError("Venture is too large.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return venture


def get(user, vid):
    path = folder(user) / f"{safe(vid, 'venture id')}.json"
    if not path.exists():
        raise KeyError("Venture not found.")
    return json.loads(path.read_text())


def update(user, vid, changes):
    venture = get(user, vid)
    if not isinstance(changes, dict) or set(changes) - FIELDS:
        raise ValueError(f"Only these fields can change: {', '.join(sorted(FIELDS))}.")
    if "stage" in changes and changes["stage"] not in STAGES:
        raise ValueError("Unknown stage.")
    if "status" in changes and changes["status"] not in STATUSES:
        raise ValueError("Unknown status.")
    venture.update(changes, updated_at=now())
    return save(venture)


def all_for(user):
    path = folder(user)
    items = [json.loads(p.read_text()) for p in path.glob("*.json")] if path.exists() else []
    return sorted(items, key=lambda v: v["updated_at"], reverse=True)


def delete(user, vid):
    path = folder(user) / f"{safe(vid, 'venture id')}.json"
    if path.exists():
        path.unlink()
