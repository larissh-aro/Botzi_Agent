# interpreter_agent.py
import json
import subprocess
from typing import Callable, List, Dict, Any, Optional

OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_TIMEOUT = 30  # seconds


class InterpreterAgent:
    """
    InterpreterAgent tries the local regex parser first (parser_fn).
    If regex returns None, it queries the local Ollama model to produce
    a JSON action list. Ollama output is strictly parsed as JSON.
    """

    def __init__(self, parser_fn: Callable[[str], Optional[List[Dict[str, Any]]]],
                 enable_llm: bool = True,
                 model: str = OLLAMA_MODEL):
        self.parser = parser_fn
        self.enable_llm = enable_llm
        self.model = model

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Calls the local ollama CLI `ollama run <model>` with prompt on stdin.
        Returns stdout string or None on error/timeouts.
        """
        try:
            proc = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                text=True,
                capture_output=True,
                timeout=OLLAMA_TIMEOUT
            )
            if proc.returncode != 0:
                return None
            return proc.stdout.strip()
        except Exception:
            return None

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Heuristically extract first JSON object/array from text and parse it.
        """
        if not text:
            return None
        # find first { or [
        start = None
        for i, ch in enumerate(text):
            if ch in ("{", "["):
                start = i
                break
        if start is None:
            return None
        # attempt to parse progressively until success or end
        for end in range(len(text), start, -1):
            candidate = text[start:end]
            try:
                return json.loads(candidate)
            except Exception:
                continue
        # last attempt: try full text
        try:
            return json.loads(text)
        except Exception:
            return None

    def _make_llm_prompt(self, user_text: str) -> str:
        """
        Prompt instructing Ollama to return a JSON array of action objects.
        Keep prompt deterministic and strict to help parsing.
        """
        system = (
            "You are an interpreter for a note-taking assistant. "
            "Output ONLY valid JSON (no extra text) that follows this schema:\n\n"
            "{ \"actions\": [ { \"action\": \"create|update|delete|show|show_all|pin|unpin|archive|unarchive|add_label|remove_label|add_check|check_item\", "
            "\"identifier\": \"optional note title or id\", \"fields\": { /* field:value pairs */ } }, ... ] }\n\n"
            "Examples:\n"
            "User: add note shopping and pin shopping\n"
            "JSON: {\"actions\":[{\"action\":\"create\",\"fields\":{\"title\":\"shopping\"}},{\"action\":\"update\",\"identifier\":\"shopping\",\"fields\":{\"isPinned\":true}}]}\n\n"
            "User: update todo reminder to tomorrow 6pm\n"
            "JSON: {\"actions\":[{\"action\":\"update\",\"identifier\":\"todo\",\"fields\":{\"reminderDate\":  /* unix ms or null if unknown */ }}]}\n\n"
            "Only produce parsable JSON. Use booleans true/false for flags. Use field names: title, content, color, reminderDate, category, isPinned, isArchived, isChecklist, checklistItems, labels.\n\n"
        )
        prompt = system + "\nUser: " + user_text + "\nJSON:"
        return prompt

    def run(self, text: str) -> Optional[List[Dict[str, Any]]]:
        # 1) Try deterministic local parser first
        try:
            parsed = self.parser(text)
            if parsed:
                return parsed
        except Exception:
            # if local parser crashes, fall through to LLM if enabled
            parsed = None

        # 2) If LLM disabled, return None
        if not self.enable_llm:
            return None

        # 3) Call Ollama for interpretation
        prompt = self._make_llm_prompt(text)
        out = self._call_ollama(prompt)
        if not out:
            return None

        # 4) Extract JSON from the model output
        parsed_json = self._extract_json(out)
        if not parsed_json or "actions" not in parsed_json:
            return None

        # 5) Validate / normalize actions (ensure expected keys)
        actions = parsed_json.get("actions", [])
        normalized: List[Dict[str, Any]] = []
        for a in actions:
            if not isinstance(a, dict):
                continue
            act = a.get("action")
            if not act:
                continue
            entry = {"action": act}
            if "identifier" in a:
                entry["identifier"] = a.get("identifier")
            if "fields" in a and isinstance(a.get("fields"), dict):
                entry["fields"] = a.get("fields")
            else:
                entry["fields"] = a.get("fields", {})
            normalized.append(entry)

        return normalized if normalized else None
