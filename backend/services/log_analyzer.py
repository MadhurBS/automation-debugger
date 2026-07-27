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

        content = path.read_text(encoding="utf-8", errors="ignore")

        # Detect format
        log_format = self._detect_format(content)
        entries = self._parse_entries(content, log_format)

        exceptions = self._extract_exceptions(entries, content)
        execution_trace = self._build_execution_trace(entries)
        exception_summary = self._build_exception_summary(exceptions)

        error_count = sum(1 for e in entries if (e.get("level") or "").upper() in ("ERROR", "FATAL"))
        warning_count = sum(1 for e in entries if (e.get("level") or "").upper() == "WARN")

        return {
            "format": log_format,
            "entries": entries[:500],
            "exceptions": exceptions,
            "execution_trace": execution_trace,
            "exception_summary": exception_summary,
            "error_count": error_count,
            "warning_count": warning_count,
        }

    def _detect_format(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("[") and '"level"' in stripped[:200]:
            return "uipath_json_array"
        if stripped.startswith("{") and '"level"' in stripped[:200]:
            return "json_lines"
        if re.search(r"\d{4}-\d{2}-\d{2}.*\|.*(INFO|WARN|ERROR|DEBUG|FATAL)", content[:500]):
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
        entries = []
        level_pattern = re.compile(r"\b(INFO|WARN|WARNING|ERROR|FATAL|DEBUG|CRITICAL)\b", re.IGNORECASE)
        ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")

        for line in content.splitlines()[:2000]:
            if not line.strip():
                continue
            level_match = level_pattern.search(line)
            ts_match = ts_pattern.search(line)
            entries.append({
                "timestamp": ts_match.group() if ts_match else None,
                "level": level_match.group().upper() if level_match else None,
                "message": line.strip(),
                "raw": line,
            })
        return entries

    def _extract_exceptions(self, entries: list[dict], raw_content: str) -> list[dict]:
        exceptions = []

        # Extract from structured entries
        for entry in entries:
            if entry.get("exception_type"):
                exceptions.append({
                    "type": entry["exception_type"],
                    "message": entry.get("exception_message") or entry.get("message") or "",
                    "timestamp": entry.get("timestamp"),
                    "workflow": entry.get("workflow"),
                    "activity": entry.get("activity"),
                    "stack_trace": entry.get("stack_trace"),
                })
            elif entry.get("level") in ("ERROR", "FATAL") and entry.get("message"):
                exc_type = self._guess_exception_type(entry["message"])
                if exc_type:
                    exceptions.append({
                        "type": exc_type,
                        "message": entry["message"],
                        "timestamp": entry.get("timestamp"),
                        "workflow": entry.get("workflow"),
                        "activity": entry.get("activity"),
                    })

        # Scan raw content for stack traces
        stack_blocks = re.findall(
            r"((?:\w+Exception|Exception)[^\n]{0,200}\n(?:\s+at [^\n]+\n){1,20})",
            raw_content,
        )
        for block in stack_blocks[:10]:
            exc_type = block.split(":")[0].strip().split()[-1]
            if not any(e["type"] == exc_type for e in exceptions):
                exceptions.append({
                    "type": exc_type,
                    "message": block.split("\n")[0][:300],
                    "stack_trace": block[:1000],
                })

        return exceptions

    def _guess_exception_type(self, message: str) -> str | None:
        for exc_type, pattern in EXCEPTION_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                return exc_type
        return None

    def _build_execution_trace(self, entries: list[dict]) -> list[dict]:
        """Build a condensed execution path from log entries."""
        trace = []
        for entry in entries:
            level = (entry.get("level") or "").upper()
            if level in ("ERROR", "FATAL", "WARN") or entry.get("exception_type"):
                trace.append({
                    "timestamp": entry.get("timestamp"),
                    "level": level,
                    "message": (entry.get("message") or "")[:200],
                    "workflow": entry.get("workflow"),
                    "activity": entry.get("activity"),
                    "is_error": level in ("ERROR", "FATAL"),
                })
        return trace[:100]

    def _build_exception_summary(self, exceptions: list[dict]) -> dict[str, Any]:
        if not exceptions:
            return {"total": 0, "by_type": {}, "most_common": None, "most_recent": None}

        by_type: dict[str, int] = {}
        for exc in exceptions:
            t = exc.get("type", "Unknown")
            by_type[t] = by_type.get(t, 0) + 1

        most_common = max(by_type, key=lambda k: by_type[k])
        most_recent = exceptions[-1] if exceptions else None

        return {
            "total": len(exceptions),
            "by_type": by_type,
            "most_common": most_common,
            "most_recent": most_recent,
            "primary_exception": exceptions[0] if exceptions else None,
        }
