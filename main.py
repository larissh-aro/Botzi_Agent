# ================================
# main.py — FINAL VERSION (with Supervisor Agent)
# ================================

import os
import re
import json
import datetime
from typing import List, Dict, Any, Optional
from tools_layer import ToolsLayer
from tools import (
    create_note, list_notes, update_note, delete_note,
    add_checklist_item, check_checklist_item
)

# ======================================================
# IMPORT SUPERVISOR + AGENTS (NEW FILES YOU CREATED)
# ======================================================
from supervisor_agent import SupervisorAgent
from interpreter_agent import InterpreterAgent
from executor_agent import ExecutorAgent



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
        tm = re.search(r'(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?', t)
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2) or 0)
            ap = tm.group(3)
            if ap == "pm" and hour != 12:
                hour += 12
            if ap == "am" and hour == 12:
                hour = 0
            dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return int(dt.timestamp() * 1000)

    if "today" in t:
        dt = now
        tm = re.search(r'(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?', t)
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2) or 0)
            ap = tm.group(3)
            if ap == "pm" and hour != 12:
                hour += 12
            if ap == "am" and hour == 12:
                hour = 0
            dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return int(dt.timestamp() * 1000)

    num = re.search(r'\b(\d{10}|\d{13})\b', t)
    if num:
        v = int(num.group(1))
        if len(str(v)) == 10:
            v *= 1000
        return v

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
# Single command parser (unchanged)
# ======================================================
def local_parse_single(cmd: str) -> Optional[Dict[str, Any]]:
    t = cmd.strip()
    tl = t.lower()

    if tl in ("hi", "hello", "hey", "yo", "hii", "hiii"):
        return {"action": "greet"}

    if tl in ("show notes", "show all notes", "list notes", "display notes"):
        return {"action": "show_all"}

    m = re.match(r'^show\s+note\s+(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "show_one", "identifier": m.group(1).strip()}
    m = re.match(r'^show\s+(.+)$', t, flags=re.IGNORECASE)
    if m and m.group(1).lower() not in ("notes", "all notes"):
        return {"action": "show_one", "identifier": m.group(1).strip()}

    m = re.match(r'^(add|create)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "create", "fields": {"title": m.group(2).strip()}}

    m = re.match(r'^(delete|remove)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "delete", "identifier": m.group(2).strip()}

    m = re.match(r'^(rename|change name)\s+(?:note\s+)?(.+?)\s+to\s+(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "update", "identifier": m.group(2).strip(), "fields": {"title": m.group(3).strip()}}

    m = re.match(r'^paint\s+(?:note\s+)?(.+?)\s+(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "update", "identifier": m.group(1).strip(), "fields": {"color": normalize_color(m.group(2))}}

    m = re.match(r'^(pin|unpin)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "update", "identifier": m.group(2).strip(),
                "fields": {"isPinned": m.group(1).lower() == "pin"}}

    m = re.match(r'^(archive|unarchive)\s+(?:note\s+)?(.+)$', t, flags=re.IGNORECASE)
    if m:
        return {"action": "update", "identifier": m.group(2).strip(),
                "fields": {"isArchived": m.group(1).lower() == "archive"}}

    m = re.match(r'^update\s+(?:note\s+)?(.+?)\s+as\s+(archived|unarchived)$', tl)
    if m:
        return {"action": "update", "identifier": m.group(1).strip(),
                "fields": {"isArchived": m.group(2) == "archived"}}

    m = re.match(r'^update\s+(?:note\s+)?(.+?)\s+as\s+(pinned|unpinned)$', tl)
    if m:
        return {"action": "update", "identifier": m.group(1).strip(),
                "fields": {"isPinned": m.group(2) == "pinned"}}

    m = re.match(
        r'^update\s+(?:note\s+)?(.+?)\s+(title|content|color|reminder|category)\s+to\s+(.+)$',
        t, flags=re.IGNORECASE
    )
    if m:
        identifier = m.group(1).strip()
        field = m.group(2).lower()
        val = m.group(3).strip()
        fields: Dict[str, Any] = {}
        if field == "color":
            fields["color"] = normalize_color(val)
        elif field == "reminder":
            fields["reminderDate"] = parse_natural_date(val)
        else:
            fields[field] = val
        return {"action": "update", "identifier": identifier, "fields": fields}

    m = re.match(r'^update\s+(?:note\s+)?(.+?)\s+checklist\s+as\s+(completed|incomplete)$', tl)
    if m:
        return {"action": "update", "identifier": m.group(1).strip(),
                "fields": {"isChecklist": m.group(2) == "completed"}}

    m = re.match(r'^(update|mark)\s+(?:note\s+)?(.+?)\s+as\s+(completed|incomplete)$', tl)
    if m:
        return {"action": "update", "identifier": m.group(2).strip(),
                "fields": {"isChecklist": m.group(3) == "completed"}}

    return None


# ======================================================
# Multi command parser
# ======================================================
def local_parse_multiple(text: str) -> Optional[List[Dict[str, Any]]]:
    parts = split_commands(text)
    actions: List[Dict[str, Any]] = []
    for p in parts:
        parsed = local_parse_single(p)
        if parsed is None:
            return None
        actions.append(parsed)
    return actions


# ======================================================
# Executor function (unchanged)
# ======================================================
def execute_actions(actions: List[Dict[str, Any]]) -> List[str]:
    logs: List[str] = []
    for a in actions:
        act = a.get("action")
        identifier = a.get("identifier")
        fields = a.get("fields", {})

        try:
            if act == "greet":
                logs.append("Hello! How can I help you today? 🙂")
                continue

            if act == "show_all":
                notes = list_notes()
                if not isinstance(notes, list) or len(notes) == 0:
                    logs.append("No notes found.")
                else:
                    titles = ", ".join([n.get("title", "") for n in notes])
                    logs.append("Notes: " + titles)
                continue

            if act == "show_one":
                notes = list_notes()
                found = None
                for n in notes or []:
                    if n.get("title", "").lower() == (identifier or "").lower():
                        found = n
                        break
                if found:
                    logs.append(json.dumps(found, indent=2, default=str))
                else:
                    logs.append(f"note '{identifier}' not found")
                continue

            if act == "create":
                create_note(**fields)
                logs.append(f"note '{fields.get('title')}' is added")
                continue

            if act == "delete":
                delete_note(identifier)
                logs.append(f"note '{identifier}' is deleted")
                continue

            if act == "update":
                update_note(identifier, fields)
                logs.append(f"note '{identifier}' is updated")
                continue

            logs.append(f"Could not understand action: {a}")

        except Exception as e:
            logs.append(f"Error: {str(e)}")

    return logs


# ======================================================
# MAIN — NOW WITH SUPERVISOR AGENT
# ======================================================
def main():
    enable_llm_env = os.getenv("ENABLE_LLM", "true").lower()
    enable_llm = enable_llm_env in ("1", "true", "yes")
    model = os.getenv("LLM_MODEL", "llama3.2:latest")
    interpreter = InterpreterAgent(local_parse_multiple, enable_llm=enable_llm, model=model)
    executor = ExecutorAgent(ToolsLayer())
    supervisor = SupervisorAgent(interpreter, executor)

    print("\n=============================================")
    print("Hello! I am your KeepNotes assistant. botzi🤖")
    print("How can I help you today?\n")

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye👋, see u soon!")
            break

        if not user:
            continue

        if user.lower() in ("exit", "quit", "bye"):
            print("Goodbye👋, see u soon!")
            break

        responses = supervisor.handle(user)
        for resp in responses:
            print(resp)
        print()


if __name__ == "__main__":
    main()
