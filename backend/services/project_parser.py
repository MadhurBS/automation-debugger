from __future__ import annotations

import asyncio
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class ProjectParser:
    """Parses RPA project files for UiPath, Power Automate, Blue Prism, and Automation Anywhere."""

    # File-name / extension signatures (order matters — first match wins)
    PLATFORM_SIGNATURES: list[tuple[str, list[str]]] = [
        ("uipath",              ["project.json", ".xaml", ".nupkg"]),
        ("blue_prism",          [".bprelease", ".bpprocess", ".bpobject"]),
        ("automation_anywhere", [".atmx", ".mbot", "taskbot.json"]),
        ("power_automate",      ["definition.json", "manifest.json", ".zip"]),
    ]

    # Content keywords inside JSON / XML files that reliably identify each platform
    CONTENT_SIGNALS: dict[str, list[str]] = {
        "uipath": [
            '"studioVersion"', '"projectVersion"', '"authoredBy"',
            '"runtimeOptions"', '"expressionLanguage"',
            'xmlns:uia="http://schemas.uipath.com',
            'xmlns:ui="clr-namespace:UiPath',
        ],
        "power_automate": [
            '"$schema": "https://schema.management.azure.com',
            '"connectionReferences"', '"workflowEntityId"',
            '"kind": "PowerAutomate"', '"flowScopeType"',
        ],
        "blue_prism": [
            '<process ', '<object ', '<subsheet ', '<stage ',
            'xmlns:bp="', 'Blue Prism', 'bpprocess',
        ],
        "automation_anywhere": [
            '"commandList"', '"taskVersion"', '"botVersion"',
            '"atcVersion"', '"commandType"', '"commandId"',
            '"packageName": "Email"',
        ],
    }

    async def parse(self, file_path: str, hint_platform: str = "unknown") -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_sync, file_path, hint_platform)

    async def detect_only(self, file_path: str) -> dict[str, Any]:
        """Quick detection without full parsing — returns {platform, confidence}."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._detect_only_sync, file_path)

    # ------------------------------------------------------------------
    # Sync helpers
    # ------------------------------------------------------------------

    def _detect_only_sync(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"platform": "unknown", "confidence": 0.0}

        # Extract into a sibling dir; caller (router) owns cleanup of the
        # whole tmp_dir, so we do NOT clean up here — that avoids a race
        # where rmtree runs before detection finishes reading the files.
        extract_dir = path.parent / f"_detected_{path.stem}"
        work_dir = self._prepare_work_dir(path, extract_dir)
        platform, confidence = self._detect_platform_with_confidence(work_dir)
        return {"platform": platform, "confidence": confidence}

    def _parse_sync(self, file_path: str, hint_platform: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"platform": hint_platform, "error": "File not found"}

        extract_dir = path.parent / f"_extracted_{path.stem}"
        work_dir = self._prepare_work_dir(path, extract_dir)

        platform = self._detect_platform(work_dir, hint_platform)

        if platform == "uipath":
            return self._parse_uipath(work_dir)
        elif platform == "power_automate":
            return self._parse_power_automate(work_dir)
        elif platform == "blue_prism":
            return self._parse_blue_prism(work_dir)
        elif platform == "automation_anywhere":
            return self._parse_automation_anywhere(work_dir)
        else:
            return {"platform": "unknown", "metadata": {}, "workflow_structure": {}, "dependencies": {}}

    def _prepare_work_dir(self, path: Path, extract_dir: Path) -> Path:
        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    zf.extractall(extract_dir)
            except Exception:
                return path.parent
            return extract_dir
        elif path.is_dir():
            return path
        else:
            return path.parent

    # ------------------------------------------------------------------
    # Platform detection
    # ------------------------------------------------------------------

    def _detect_platform(self, work_dir: Path, hint: str) -> str:
        if hint and hint not in ("unknown", ""):
            return hint
        platform, _ = self._detect_platform_with_confidence(work_dir)
        return platform

    def _detect_platform_with_confidence(self, work_dir: Path) -> tuple[str, float]:
        """Returns (platform, confidence 0‒1).  Checks filenames then content."""
        files = list(work_dir.rglob("*"))
        file_names = {f.name.lower() for f in files if f.is_file()}
        file_exts  = {f.suffix.lower() for f in files if f.is_file()}

        # ── Stage 1: unique file-name / extension signals ──────────────
        scores: dict[str, float] = {p: 0.0 for p in self.CONTENT_SIGNALS}

        for platform, sigs in self.PLATFORM_SIGNATURES:
            for sig in sigs:
                if sig.startswith("."):
                    if sig in file_exts:
                        scores[platform] += 1.0
                else:
                    if sig.lower() in file_names:
                        scores[platform] += 1.5   # exact filename match is stronger

        # ── Stage 2: content sniffing in text files ────────────────────
        readable_files = [
            f for f in files
            if f.is_file() and f.suffix.lower() in (".json", ".xml", ".xaml", ".txt", ".bprelease", ".atmx", ".mbot")
            and f.stat().st_size < 2 * 1024 * 1024  # skip files > 2 MB
        ]
        for fpath in readable_files[:20]:  # cap at 20 files
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for platform, signals in self.CONTENT_SIGNALS.items():
                for signal in signals:
                    if signal.lower() in text.lower():
                        scores[platform] += 0.8

        best_platform = max(scores, key=lambda p: scores[p])
        best_score    = scores[best_platform]

        if best_score == 0:
            return "unknown", 0.0

        # Normalise: score → 0..1 (cap at score=5 → 1.0)
        confidence = min(best_score / 5.0, 1.0)
        return best_platform, round(confidence, 2)

    # ------------------------------------------------------------------
    # Per-platform parsers (unchanged logic, just moved _prepare_work_dir out)
    # ------------------------------------------------------------------

    def _parse_uipath(self, work_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"platform": "uipath", "metadata": {}, "workflow_structure": {}, "dependencies": {}}

        project_json = work_dir / "project.json"
        if not project_json.exists():
            candidates = list(work_dir.rglob("project.json"))
            if candidates:
                project_json = candidates[0]

        if project_json.exists():
            try:
                with open(project_json, encoding="utf-8") as f:
                    pj = json.load(f)
                result["name"] = pj.get("name", "Unknown")
                result["metadata"] = {
                    "name": pj.get("name"),
                    "description": pj.get("description"),
                    "version": pj.get("projectVersion"),
                    "studio_version": pj.get("studioVersion"),
                    "author": pj.get("authoredBy"),
                    "main_workflow": pj.get("main"),
                    "runtime_options": pj.get("runtimeOptions", {}),
                }
                deps = pj.get("dependencies", {})
                result["dependencies"] = {
                    "packages": [{"name": k, "version": v} for k, v in deps.items()]
                }
            except Exception as e:
                result["metadata"]["parse_error"] = str(e)

        xaml_files = list(work_dir.rglob("*.xaml"))
        workflows = []
        for xaml_path in xaml_files[:50]:
            wf = self._parse_xaml(xaml_path)
            if wf:
                workflows.append(wf)

        result["workflow_structure"] = {"workflows": workflows, "total_workflows": len(workflows)}
        return result

    def _parse_xaml(self, xaml_path: Path) -> dict[str, Any] | None:
        try:
            tree = ET.parse(xaml_path)
            root = tree.getroot()

            def strip_ns(t: str) -> str:
                return t.split("}")[-1] if "}" in t else t

            activities = self._extract_activities(root, strip_ns, depth=0, max_depth=5)

            variables = []
            for elem in root.iter():
                if "Variable" in strip_ns(elem.tag):
                    variables.append({
                        "name": elem.get("x:Name") or elem.get("Name") or "",
                        "type": elem.get("TypeArgument") or elem.get("x:TypeArguments") or "",
                    })

            return {
                "filename": xaml_path.name,
                "display_name": xaml_path.stem,
                "activities": activities,
                "variables": variables[:50],
                "activity_count": len(activities),
            }
        except Exception:
            return None

    def _extract_activities(self, elem, strip_ns, depth: int, max_depth: int) -> list[dict]:
        if depth > max_depth:
            return []
        activities = []
        for child in elem:
            tag = strip_ns(child.tag)
            if tag in ("Members", "TextExpression.NamespacesForImplementation",
                       "TextExpression.ReferencesForImplementation",
                       "Variables", "Arguments"):
                continue

            activity: dict[str, Any] = {
                "name": tag,
                "display_name": child.get("DisplayName") or child.get("{http://schemas.microsoft.com/netfx/2009/xaml/activities}DisplayName") or tag,
                "type": child.get("{http://schemas.microsoft.com/winfx/2006/xaml}Class") or tag,
            }

            for attr_name in ["Selector", "Text", "FilePath", "URL", "Method"]:
                val = child.get(attr_name)
                if val:
                    activity[attr_name.lower()] = val[:200]

            children = self._extract_activities(child, strip_ns, depth + 1, max_depth)
            if children:
                activity["children"] = children

            activities.append(activity)
        return activities

    def _parse_power_automate(self, work_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"platform": "power_automate", "metadata": {}, "workflow_structure": {}, "dependencies": {}}
        def_file = next((f for f in work_dir.rglob("definition.json")), None)
        if def_file:
            try:
                with open(def_file, encoding="utf-8") as f:
                    defn = json.load(f)
                result["name"] = defn.get("name") or defn.get("properties", {}).get("displayName", "Unknown")
                result["metadata"] = {"name": result["name"], "trigger": defn.get("triggers", {}).get("type")}
                actions = defn.get("actions", {})
                result["workflow_structure"] = {
                    "actions": [{"name": k, "type": v.get("type")} for k, v in actions.items()]
                }
            except Exception as e:
                result["metadata"]["parse_error"] = str(e)
        return result

    def _parse_blue_prism(self, work_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"platform": "blue_prism", "metadata": {}, "workflow_structure": {}, "dependencies": {}}
        xml_files = list(work_dir.rglob("*.xml")) + list(work_dir.rglob("*.bprelease"))
        for xml_path in xml_files[:5]:
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                stages = [{"name": s.get("name"), "type": s.get("type")} for s in root.iter("stage")]
                result["workflow_structure"] = {"stages": stages[:100]}
                result["name"] = root.get("name") or xml_path.stem
                break
            except Exception:
                continue
        return result

    def _parse_automation_anywhere(self, work_dir: Path) -> dict[str, Any]:
        result: dict[str, Any] = {"platform": "automation_anywhere", "metadata": {}, "workflow_structure": {}, "dependencies": {}}
        bot_files = list(work_dir.rglob("*.json")) + list(work_dir.rglob("*.atmx"))
        for bot_file in bot_files[:3]:
            try:
                with open(bot_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "commandList" in data:
                    commands = data["commandList"][:50]
                    result["workflow_structure"] = {"commands": [{"type": c.get("command"), "name": c.get("name")} for c in commands]}
                    result["name"] = data.get("name", bot_file.stem)
                    break
            except Exception:
                continue
        return result
