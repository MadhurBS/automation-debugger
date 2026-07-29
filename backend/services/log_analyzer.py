from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


EXCEPTION_PATTERNS = {
    "NullReferenceException": r"(NullReferenceException|Object reference not set|null reference)",
    "SelectorNotFoundException": r"(SelectorNotFoundException|selector.*not found|element.*not found|Cannot find the UI element)",
    "TimeoutException": r"(TimeoutException|Timeout.*exceeded|activity timed out|operation timed out)",
    "MissingPackageException": r"(Could not load.*assembly|package.*not found|assembly.*not found|missing.*dependency)",
    "FileNotFoundException": r"(FileNotFoundException|File.*not found|path.*does not exist|cannot find.*file)",
    "ArgumentException": r"(ArgumentException|ArgumentNullException|Invalid.*argument|required argument.*missing)",
    "InvalidCredentialException": r"(credential.*invalid|authentication.*failed|unauthorized|access.*denied|password.*incorrect)",
    "NetworkException": r"(WebException|HttpRequestException|connection.*refused|network.*unreachable|API.*error|HTTP.*4[0-9]{2}|HTTP.*5[0-9]{2})",
    "QueueException": r"(queue.*empty|no.*transaction|queue.*failed|item.*already processed)",
    "ConfigurationException": r"(asset.*not found|configuration.*missing|environment.*variable.*not|config.*key.*missing)",
    "BusinessRuleException": r"(BusinessRuleException|business.*rule.*violation|validation.*failed)",
    "UnhandledException": r"(Unhandled.*exception|unexpected.*error|fatal.*error)",
}


class LogAnalyzer:
    """Parses RPA execution logs and extracts exception/error details."""

    async def analyze(self, file_path: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._analyze_sync, file_path)

    def _analyze_sync(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"format": "unknown", "entries": [], "error_count": 0, "warning_count": 0}

        # Read the COMPLETE file — no size cap at read time
        content = path.read_text(encoding="utf-8", errors="ignore")

        # Detect format
        log_format = self._detect_format(content)

        # Parse ALL entries from the full content
        entries = self._parse_entries(content, log_format)

        # Extract ALL exceptions from ALL entries + raw content scan
        exceptions = self._extract_exceptions(entries, content)

        # Build execution trace from ALL entries (errors/warnings only)
        execution_trace = self._build_execution_trace(entries)

        # Build summary — includes ALL exceptions list
        exception_summary = self._build_exception_summary(exceptions)

        error_count   = sum(1 for e in entries if (e.get("level") or "").upper() in ("ERROR", "FATAL"))
        warning_count = sum(1 for e in entries if (e.get("level") or "").upper() == "WARN")

        return {
            "format":           log_format,
            "total_lines":      content.count("\n") + 1,
            "total_entries":    len(entries),
            "entries":          entries[:2000],   # store up to 2000 for display
            "exceptions":       exceptions,        # ALL exceptions, no cap here
            "execution_trace":  execution_trace,   # all error/warn entries
            "exception_summary": exception_summary,
            "error_count":      error_count,
            "warning_count":    warning_count,
        }

    def _detect_format(self, content: str) -> str:
        stripped = content.strip()

        # UiPath JSON array log
        if stripped.startswith("[") and ('"level"' in stripped[:500] or '"Level"' in stripped[:500]):
            return "uipath_json_array"

        # JSON Lines (one JSON object per line)
        if stripped.startswith("{"):
            first_line = stripped.split("\n")[0]
            try:
                import json as _json
                obj = _json.loads(first_line)
                if isinstance(obj, dict):
                    return "json_lines"
            except Exception:
                pass

        # NLog / structured text with timestamp | LEVEL | message pattern
        if re.search(
            r"\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}.{0,30}(INFO|WARN|WARNING|ERROR|DEBUG|FATAL|TRACE)",
            content[:2000],
            re.IGNORECASE,
        ):
            return "nlog"

        return "text"

    def _parse_entries(self, content: str, log_format: str) -> list[dict]:
        if log_format == "uipath_json_array":
            return self._parse_json_array(content)
        elif log_format == "json_lines":
            return self._parse_json_lines(content)
        elif log_format == "nlog":
            return self._parse_nlog(content)
        else:
            return self._parse_text(content)

    def _parse_json_array(self, content: str) -> list[dict]:
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                return []
            entries = []
            for item in data:
                entry = {
                    "timestamp": item.get("timeStamp") or item.get("timestamp"),
                    "level": item.get("level"),
                    "message": item.get("message") or item.get("Message") or "",
                    "workflow": item.get("workflowFilePath") or item.get("fileName"),
                    "activity": item.get("activityInfo", {}).get("Name") if isinstance(item.get("activityInfo"), dict) else None,
                    "exception_type": item.get("Exception", {}).get("ExceptionType") if isinstance(item.get("Exception"), dict) else None,
                    "exception_message": item.get("Exception", {}).get("Message") if isinstance(item.get("Exception"), dict) else None,
                    "stack_trace": item.get("Exception", {}).get("Source") if isinstance(item.get("Exception"), dict) else None,
                }
                entries.append(entry)
            return entries
        except json.JSONDecodeError:
            return []

    def _parse_json_lines(self, content: str) -> list[dict]:
        entries = []
        for line in content.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                entries.append({
                    "timestamp": item.get("@t") or item.get("timestamp"),
                    "level": item.get("@l") or item.get("level"),
                    "message": item.get("@m") or item.get("message") or "",
                    "exception_type": item.get("ExceptionType"),
                    "exception_message": item.get("ExceptionMessage"),
                    "stack_trace": item.get("@x"),
                })
            except json.JSONDecodeError:
                continue
        return entries

    def _parse_nlog(self, content: str) -> list[dict]:
        pattern = re.compile(
            r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*)\s*[|\s]+(?P<level>INFO|WARN|ERROR|DEBUG|FATAL|TRACE)\s*[|\s]+(?P<msg>.+)",
            re.IGNORECASE,
        )
        entries = []
        for match in pattern.finditer(content):
            entries.append({
                "timestamp": match.group("ts"),
                "level": match.group("level").upper(),
                "message": match.group("msg").strip(),
            })
        return entries

    def _parse_text(self, content: str) -> list[dict]:
        """Parse plain-text log — reads ALL lines, no cap."""
        entries = []
        level_pattern = re.compile(r"\b(INFO|WARN|WARNING|ERROR|FATAL|DEBUG|CRITICAL)\b", re.IGNORECASE)
        ts_pattern    = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")

        current_entry: dict | None = None

        for line in content.splitlines():   # NO [:2000] cap — read all lines
            stripped = line.strip()
            if not stripped:
                continue

            level_match = level_pattern.search(stripped)
            ts_match    = ts_pattern.search(stripped)

            # A new log line starts with a timestamp or a level keyword
            if ts_match or level_match:
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    "timestamp": ts_match.group() if ts_match else None,
                    "level":     level_match.group().upper() if level_match else None,
                    "message":   stripped,
                    "raw":       line,
                }
            elif current_entry:
                # Continuation line (stack trace, multi-line message) — append to current entry
                current_entry["message"] = current_entry["message"] + "\n" + stripped
                if stripped.startswith("at ") or stripped.startswith("--- "):
                    # Stack trace line — append to stack_trace field
                    current_entry.setdefault("stack_trace", "")
                    current_entry["stack_trace"] = (
                        current_entry["stack_trace"] + "\n" + stripped
                    )[:4000]
            else:
                # No timestamp/level, no current entry — treat as standalone message
                entries.append({
                    "timestamp": None,
                    "level":     None,
                    "message":   stripped,
                    "raw":       line,
                })

        if current_entry:
            entries.append(current_entry)

        return entries

    def _extract_exceptions(self, entries: list[dict], raw_content: str) -> list[dict]:
        """
        Extract ALL exceptions from ALL entries + raw stack-trace scan.
        No artificial cap on number of exceptions collected.
        """
        exceptions: list[dict] = []
        seen_keys: set[tuple] = set()

        def _add(exc: dict) -> None:
            key = (exc.get("type", ""), (exc.get("message") or "")[:120])
            if key not in seen_keys:
                seen_keys.add(key)
                exceptions.append(exc)

        # ── Pass 1: structured fields (JSON-based log formats) ─────────────
        for entry in entries:
            if entry.get("exception_type"):
                _add({
                    "type":       entry["exception_type"],
                    "message":    entry.get("exception_message") or entry.get("message") or "",
                    "timestamp":  entry.get("timestamp"),
                    "workflow":   entry.get("workflow"),
                    "activity":   entry.get("activity"),
                    "stack_trace": entry.get("stack_trace"),
                })

        # ── Pass 2: ERROR/FATAL entries in ALL formats ─────────────────────
        for entry in entries:
            if entry.get("level") in ("ERROR", "FATAL") and entry.get("message"):
                msg = entry["message"]
                exc_type = self._guess_exception_type(msg)
                # Also detect inline exception type from the message text
                inline_match = re.search(
                    r"([A-Z][a-zA-Z0-9]*(?:Exception|Error))", msg
                )
                if not exc_type and inline_match:
                    exc_type = inline_match.group(1)
                if exc_type or entry.get("level") == "FATAL":
                    _add({
                        "type":       exc_type or "RuntimeError",
                        "message":    msg[:1000],
                        "timestamp":  entry.get("timestamp"),
                        "workflow":   entry.get("workflow"),
                        "activity":   entry.get("activity"),
                        "stack_trace": entry.get("stack_trace"),
                    })

        # ── Pass 3: raw full-content stack-trace scan ──────────────────────
        # Scan the COMPLETE raw content (no line cap) for exception blocks
        stack_blocks = re.findall(
            r"((?:[A-Z][a-zA-Z0-9]*(?:Exception|Error))[^\n]{0,500}"
            r"(?:\n[ \t]+at [^\n]+){1,30})",
            raw_content,
            re.MULTILINE,
        )
        for block in stack_blocks:
            first_line = block.split("\n")[0]
            exc_match  = re.match(r"([A-Z][a-zA-Z0-9]*(?:Exception|Error))", first_line)
            exc_type   = exc_match.group(1) if exc_match else "UnknownException"
            _add({
                "type":        exc_type,
                "message":     first_line[:500],
                "stack_trace": block[:3000],
            })

        # ── Pass 4: scan every line for exception keywords (text logs) ─────
        for entry in entries:
            msg = entry.get("message") or ""
            inline = re.search(r"([A-Z][a-zA-Z0-9]*(?:Exception|Error))[\s:]+(.+)", msg)
            if inline:
                _add({
                    "type":      inline.group(1),
                    "message":   inline.group(2).strip()[:500],
                    "timestamp": entry.get("timestamp"),
                    "workflow":  entry.get("workflow"),
                    "activity":  entry.get("activity"),
                    "stack_trace": entry.get("stack_trace"),
                })

        return exceptions

    def _guess_exception_type(self, message: str) -> str | None:
        for exc_type, pattern in EXCEPTION_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                return exc_type
        return None

    def _build_execution_trace(self, entries: list[dict]) -> list[dict]:
        """
        Build execution trace from ALL entries — no cap on entries read.
        Includes every ERROR, FATAL, WARN, and exception-carrying entry.
        """
        trace = []
        for entry in entries:   # ALL entries, no slice
            level = (entry.get("level") or "").upper()
            if level in ("ERROR", "FATAL", "WARN") or entry.get("exception_type"):
                trace.append({
                    "timestamp":      entry.get("timestamp"),
                    "level":          level,
                    "message":        (entry.get("message") or "")[:500],
                    "workflow":       entry.get("workflow"),
                    "activity":       entry.get("activity"),
                    "exception_type": entry.get("exception_type"),
                    "stack_trace":    (entry.get("stack_trace") or "")[:2000],
                    "is_error":       level in ("ERROR", "FATAL"),
                })
        return trace   # return ALL — no [:100] cap

    def _build_exception_summary(self, exceptions: list[dict]) -> dict[str, Any]:
        """
        Build summary including ALL exceptions list so rca_engine can read them.
        Critical fix: 'all_exceptions' was missing — engine was reading it but
        it was never populated, causing empty exception data despite log content.
        """
        if not exceptions:
            return {
                "total": 0, "by_type": {}, "most_common": None,
                "most_recent": None, "primary_exception": None, "all_exceptions": [],
            }

        by_type: dict[str, int] = {}
        for exc in exceptions:
            t = exc.get("type", "Unknown")
            by_type[t] = by_type.get(t, 0) + 1

        most_common = max(by_type, key=lambda k: by_type[k])

        return {
            "total":             len(exceptions),
            "by_type":           by_type,
            "most_common":       most_common,
            "most_recent":       exceptions[-1],
            "primary_exception": exceptions[0],
            "all_exceptions":    exceptions,   # ← CRITICAL: full list for rca_engine
        }
