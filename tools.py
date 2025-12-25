# tools.py
import os
import requests
from typing import Optional, Dict, Any, List

# Allow overriding the backend URL via environment variable so the agent
# can target local development backend (default) or a remote host.
BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:5000/api/notes")


def safe_json(response):
    try:
        return response.json()
    except:
        return {
            "error": "Invalid JSON returned",
            "status": getattr(response, "status_code", None),
            "raw": getattr(response, "text", str(response))
        }


# -----------------------------
# Helpers
# -----------------------------
def _find_by_title(title: str) -> Optional[Dict[str, Any]]:
    r = requests.get(BASE_URL, timeout=30)
    try:
        notes = r.json()
    except:
        return None

    for n in notes:
        if n.get("title", "").lower() == title.lower():
            return n
    return None


def _resolve_id(identifier: str) -> Optional[str]:
    if identifier and len(identifier) == 24 and identifier.isalnum():
        return identifier

    note = _find_by_title(identifier)
    return note["id"] if note else None


# -----------------------------
# CREATE
# -----------------------------
def create_note(
    title: str,
    content: str = "",
    color: str = "default",
    labels: Optional[List[str]] = None,
    isPinned: bool = False,
    isArchived: bool = False,
    category: str = "general"
):
    payload = {
        "title": title,
        "content": content or "",
        "color": color or "default",
        "labels": labels or [],
        "isPinned": bool(isPinned),
        "isArchived": bool(isArchived),
        "isChecklist": False,
        "checklistItems": [],
        "reminderDate": None,
        "category": category or "general"
    }
    r = requests.post(BASE_URL, json=payload, timeout=30)
    return safe_json(r)


# -----------------------------
# LIST
# -----------------------------
def list_notes() -> Dict:
    r = requests.get(BASE_URL, timeout=30)
    return safe_json(r)


# -----------------------------
# DELETE
# -----------------------------
def delete_note(identifier: str):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    r = requests.delete(f"{BASE_URL}/{nid}", timeout=30)
    return safe_json(r)


# -----------------------------
# UPDATE
# -----------------------------
def update_note(identifier: str, fields: Dict[str, Any]):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    allowed = {
        "title", "content", "color", "labels",
        "isPinned", "isArchived",
        "isChecklist", "checklistItems",
        "reminderDate", "category"
    }

    body = {k: v for k, v in fields.items() if k in allowed and v is not None}

    if not body:
        return {"error": "No valid fields provided to update."}

    r = requests.patch(f"{BASE_URL}/{nid}", json=body, timeout=30)
    return safe_json(r)


# -----------------------------
# LABELS
# -----------------------------
def add_label(identifier: str, label: str):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    res = requests.get(f"{BASE_URL}/{nid}", timeout=30)
    try:
        obj = res.json()
    except:
        obj = {}

    labels = obj.get("labels", []) or []
    if label not in labels:
        labels.append(label)

    return update_note(nid, {"labels": labels})


def remove_label(identifier: str, label: str):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    res = requests.get(f"{BASE_URL}/{nid}", timeout=30)
    try:
        obj = res.json()
    except:
        obj = {}

    labels = [l for l in obj.get("labels", []) if l.lower() != label.lower()]
    return update_note(nid, {"labels": labels})


# -----------------------------
# PIN / ARCHIVE
# -----------------------------
def set_pin(identifier: str, value: bool = True):
    return update_note(identifier, {"isPinned": bool(value)})


def set_archive(identifier: str, value: bool = True):
    return update_note(identifier, {"isArchived": bool(value)})


# -----------------------------
# CHECKLIST
# -----------------------------
def add_checklist_item(identifier: str, text: str):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    res = requests.get(f"{BASE_URL}/{nid}", timeout=30)
    try:
        obj = res.json()
    except:
        obj = {}

    items = obj.get("checklistItems", []) or []
    item_id = f"{int(__import__('time').time() * 1000)}-{len(items)}"
    items.append({"id": item_id, "text": text, "checked": False})

    return update_note(nid, {"checklistItems": items, "isChecklist": True})


def check_checklist_item(identifier: str, item_text: str):
    nid = _resolve_id(identifier)
    if not nid:
        return {"error": f"No note found for '{identifier}'"}

    res = requests.get(f"{BASE_URL}/{nid}", timeout=30)
    try:
        obj = res.json()
    except:
        obj = {}

    items = obj.get("checklistItems", []) or []
    for it in items:
        if it.get("text", "").lower() == item_text.lower():
            it["checked"] = True

    return update_note(nid, {"checklistItems": items})


# -----------------------------
# COLOR
# -----------------------------
def set_color(identifier: str, color: str):
    return update_note(identifier, {"color": color})


# -----------------------------
# REMINDER
# -----------------------------
def set_reminder(identifier: str, timestamp_ms: int):
    return update_note(identifier, {"reminderDate": timestamp_ms})
