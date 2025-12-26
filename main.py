# ================================
# main.py — FINAL VERSION (Render + FastAPI)
# ================================

import os
import re
import json
import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from tools_layer import ToolsLayer
from tools import (
    create_note, list_notes, update_note, delete_note,
    add_checklist_item, check_checklist_item
)

from supervisor_agent import SupervisorAgent
from interpreter_agent import InterpreterAgent
from executor_agent import ExecutorAgent


# ======================================================
# FASTAPI APP (REQUIRED BY RENDER)
# ======================================================
app = FastAPI(title="Botzi Agent Service")


# ======================================================
# Request Model
# ======================================================
class ChatRequest(BaseModel):
    message: str


# ======================================================
# Natural date parser
# ======================================================
def parse_natural_date(text: str) -> Optional[int]:
    if not text:
        return None

    t = text.lower().strip()
    now = datetime.datetime.now()

    m = re.match(r'in\s+(\d+)\s*(sec|secs|second|seconds|min|mins|minute|minutes|hour|hours|day|days)', t)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("sec"):
            dt = now + datetime.timedelta(seconds=num)
        elif unit.startswith("min"):
            dt = now + datetime.timedelta(minutes=num)
        elif unit.startswith("hour"):
            dt = now + datetime.timedelta(hours=num)
        else:
            dt = now + datetime.timedelta(days=num)
        return int(dt.timestamp() * 1000)

    if "tomorrow" in t:
        dt = now + datetime.timedelta(days=1)
        return int(dt.timestamp() * 1000)

    if "today" in t:
        return int(now.timestamp() * 1000)

    return None


# ======================================================
# Color normalizer
# ======================================================
COLOR_MAP = {
    "sky blue": "skyblue",
    "light blue": "lightblue",
    "dark blue": "darkblue",
    "light green": "lightgreen",
    "dark red": "darkred",
    "grey": "gray",
    "gray": "gray"
}

def normalize_color(t: str) -> str:
    if not t:
        return ""
    s = t.lower().strip()
    return COLOR_MAP.get(s, s.replace(" ", "_"))


# ======================================================
# Multi-command splitter
# ======================================================
def split_commands(text: str) -> List[str]:
    parts = [text]
    for d in [r'\s+and\s+', r'\s*;\s*', r'\s+then\s+']:
        new = []
        for p in parts:
            new += re.split(d, p, flags=re.IGNORECASE)
        parts = new
    return [p.strip() for p in parts if p.strip()]


# ======================================================
# Local command parser
# ======================================================
def local_parse_single(cmd: str) -> Optional[Dict[str, Any]]:
    t = cmd.strip()
    tl = t.lower()

    if tl in ("hi", "hello", "hey"):
        return {"action": "greet"}

    if tl in ("show notes", "list notes"):
        return {"action": "show_all"}

    m = re.match(r'^(add|create)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "create", "fields": {"title": m.group(2).strip()}}

    m = re.match(r'^(delete|remove)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "delete", "identifier": m.group(2).strip()}

    m = re.match(r'^(pin|unpin)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {
            "action": "update",
            "identifier": m.group(2).strip(),
            "fields": {"isPinned": m.group(1).lower() == "pin"}
        }

    return None


def local_parse_multiple(text: str) -> Optional[List[Dict[str, Any]]]:
    parts = split_commands(text)
    actions = []
    for p in parts:
        parsed = local_parse_single(p)
        if not parsed:
            return None
        actions.append(parsed)
    return actions


# ======================================================
# Action executor
# ======================================================
def execute_actions(actions: List[Dict[str, Any]]) -> List[str]:
    logs = []

    for a in actions:
        act = a.get("action")
        identifier = a.get("identifier")
        fields = a.get("fields", {})

        if act == "greet":
            logs.append("Hello! How can I help you today? 🤖")

        elif act == "show_all":
            notes = list_notes()
            logs.append(f"Found {len(notes)} notes" if notes else "No notes found")

        elif act == "create":
            create_note(**fields)
            logs.append(f"note '{fields.get('title')}' is added")

        elif act == "delete":
            delete_note(identifier)
            logs.append(f"note '{identifier}' is deleted")

        elif act == "update":
            update_note(identifier, fields)
            logs.append(f"note '{identifier}' is updated")

        else:
            logs.append("Action not supported")

    return logs


# ======================================================
# AGENT INITIALIZATION (ONCE)
# ======================================================
enable_llm = os.getenv("ENABLE_LLM", "true").lower() in ("1", "true", "yes")
model = os.getenv("LLM_MODEL", "gpt-4o-mini")

interpreter = InterpreterAgent(local_parse_multiple, enable_llm=enable_llm, model=model)
executor = ExecutorAgent(ToolsLayer())
supervisor = SupervisorAgent(interpreter, executor)


# ======================================================
# API ROUTES
# ======================================================
@app.get("/")
def health():
    return {"status": "Botzi Agent is running"}

@app.post("/chat")
def chat(req: ChatRequest):
    responses = supervisor.handle(req.message)
    return {"responses": responses}
